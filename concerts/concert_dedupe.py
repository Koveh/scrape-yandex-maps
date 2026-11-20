"""Collapse the same gig stored twice (venue site + aggregator, VIP vs GA, date-as-time)."""
from __future__ import annotations

import argparse
import os
import re
import unicodedata
from dataclasses import dataclass
from datetime import date, time
from functools import wraps
from typing import Callable, TypeVar
from urllib.parse import urlparse

import psycopg2
from psycopg2.extensions import connection as PgConnection

T = TypeVar("T")

DSN = os.getenv("CONCERTS_DSN", "postgresql://koveh:Daniil77Daniil@65.109.88.77:5432/koveh")
GENERIC_VENUES = {
    "lower austria",
    "moscow",
    "munchen",
    "munich",
    "münchen",
    "niederösterreich",
    "niederoesterreich",
    "vienna",
    "wien",
    "москва",
    "нижняя австрия",
}
TITLE_NOISE = re.compile(
    r"\b(20\d{2}|concert|konzert|tour|live|vip|packages|presented by|tickets|einlass|doors)\b",
    re.I,
)
WEAK_TITLE_TOKENS = {
    "band",
    "club",
    "food",
    "indie",
    "jazz",
    "live",
    "munich",
    "night",
    "open",
    "party",
    "rebels",
    "rock",
    "show",
    "the",
    "tour",
    "walking",
    "wine",
}


def logged(fn: Callable[..., T]) -> Callable[..., T]:
    @wraps(fn)
    def wrapper(*args: object, **kwargs: object) -> T:
        print(f"{fn.__name__}", flush=True)
        return fn(*args, **kwargs)

    return wrapper


def parent_of(parents: list[int], index: int) -> int:
    cursor = index
    while parents[cursor] != cursor:
        parents[cursor] = parents[parents[cursor]]
        cursor = parents[cursor]
    return cursor


def title_head(title: str) -> str:
    tokens = [part for part in title.split(" ") if part]
    if not tokens:
        return ""
    if len(tokens[0]) >= 4 and tokens[0] not in WEAK_TITLE_TOKENS:
        return tokens[0]
    if len(tokens) >= 2:
        return f"{tokens[0]} {tokens[1]}"
    return ""


def titles_match(left: str, right: str) -> bool:
    if not left or not right:
        return False
    if left == right:
        return True
    shorter, longer = (left, right) if len(left) <= len(right) else (right, left)
    head = title_head(shorter)
    if not head or title_head(longer) != head:
        return False
    if longer.startswith(shorter) and (len(longer) == len(shorter) or longer[len(shorter)] == " "):
        return True
    short_rest = set(shorter[len(head) :].split())
    long_rest = set(longer[len(head) :].split())
    if not short_rest:
        return True
    return short_rest.issubset(long_rest)


@dataclass(frozen=True)
class ConcertRow:
    id: int
    name: str
    start_date: date | None
    start_time: time | None
    venue: str | None
    price_from: int | None
    website_url: str | None
    source_url: str | None
    source_channel: str | None

    def event_url_key(self) -> str:
        url = self.website_url or self.source_url or ""
        if not url:
            return ""
        parsed = urlparse(url)
        path = (parsed.path or "").rstrip("/")
        path = re.sub(r"-\d+$", "", path)
        host = (parsed.netloc or "").lower()
        if host:
            return f"{host}{path.lower()}"
        return url.lower().rstrip("/")

    def title_key(self) -> str:
        text = unicodedata.normalize("NFKD", self.name or "")
        text = "".join(ch for ch in text if not unicodedata.combining(ch))
        text = text.lower().replace("$", "")
        text = TITLE_NOISE.sub(" ", text)
        text = re.sub(r"[^a-z0-9+]+", " ", text)
        return " ".join(text.split())

    def is_aggregator(self) -> bool:
        channel = (self.source_channel or "").lower()
        if channel in {"rausgegangen", "rausgegangen_munich"} or channel.endswith("_rg"):
            return True
        url = f"{self.website_url or ''} {self.source_url or ''}".lower()
        return "rausgegangen.de" in url

    def score(self) -> float:
        value = self.id / 1_000_000
        if self.start_time is not None and not self.is_fake_time():
            value += 25
        if not self.is_generic_venue():
            value += 35
        if not self.is_aggregator():
            value += 20
        if self.price_from is not None:
            value += 8
        value += min(len(self.name), 80) / 20
        return value

    def is_fake_time(self) -> bool:
        if self.start_date is None or self.start_time is None:
            return False
        return (
            self.start_time.hour == self.start_date.day
            and self.start_time.minute == self.start_date.month
        )

    def is_generic_venue(self) -> bool:
        return (self.venue or "").strip().lower() in GENERIC_VENUES or not (self.venue or "").strip()

    def score(self) -> float:
        value = self.id / 1_000_000
        if self.start_time is not None and not self.is_fake_time():
            value += 50
        if not self.is_generic_venue():
            value += 20
        if not self.is_aggregator():
            value += 15
        if self.price_from is not None:
            value += 8
        value += min(len(self.name), 80) / 20
        return value


class ConcertDedupe:
    def apply(self, conn: PgConnection, city: str | None = None, dry: bool = False) -> tuple[int, int]:
        rows = self.load(conn, city)
        winner_of = self.winners(rows)
        marked = 0
        if not dry:
            marked = self.mark(conn, winner_of)
            self.clear_fake_times(conn, city)
        print(f"kept_groups={len(set(winner_of.values()))} duplicates={len(winner_of)} dry={dry}", flush=True)
        return len(set(winner_of.values())), marked

    def clear_fake_times(self, conn: PgConnection, city: str | None) -> int:
        sql = (
            "UPDATE concerts SET start_time = NULL, updated_at = now() "
            "WHERE status = 'kept' AND hidden = false "
            "AND start_date IS NOT NULL AND start_time IS NOT NULL "
            "AND extract(hour from start_time) = extract(day from start_date) "
            "AND extract(minute from start_time) = extract(month from start_date)"
        )
        params: tuple[object, ...] = ()
        if city:
            sql += " AND city = %s"
            params = (city,)
        with conn.cursor() as cur:
            cur.execute(sql, params)
            return cur.rowcount or 0

    def load(self, conn: PgConnection, city: str | None) -> list[ConcertRow]:
        sql = (
            "SELECT id, name, start_date, start_time, venue, price_from, "
            "website_url, source_url, source_channel "
            "FROM concerts WHERE status = 'kept' AND hidden = false "
            "AND (start_date IS NULL OR start_date >= CURRENT_DATE)"
        )
        params: tuple[object, ...] = ()
        if city:
            sql += " AND city = %s"
            params = (city,)
        sql += " ORDER BY start_date NULLS LAST, id"
        with conn.cursor() as cur:
            cur.execute(sql, params)
            return [ConcertRow(*row) for row in cur.fetchall()]

    def mark(self, conn: PgConnection, winner_of: dict[int, int]) -> int:
        updated = 0
        with conn.cursor() as cur:
            for row_id, canonical_id in winner_of.items():
                if row_id == canonical_id:
                    continue
                cur.execute(
                    "UPDATE concerts SET status = 'duplicate', canonical_id = %s, updated_at = now() "
                    "WHERE id = %s AND status = 'kept'",
                    (canonical_id, row_id),
                )
                updated += cur.rowcount or 0
        return updated

    def winners(self, rows: list[ConcertRow]) -> dict[int, int]:
        if len(rows) < 2:
            return {}
        parents = list(range(len(rows)))
        url_index: dict[str, int] = {}
        title_index: dict[str, list[int]] = {}
        for i, row in enumerate(rows):
            day = row.start_date.isoformat() if row.start_date else "tbd"
            url_key = row.event_url_key()
            if url_key:
                key = f"{day}|{url_key}"
                seen = url_index.get(key)
                if seen is not None:
                    parents[parent_of(parents, i)] = parent_of(parents, seen)
                else:
                    url_index[key] = i
            title = row.title_key()
            if not title:
                continue
            bucket = title_index.setdefault(day, [])
            for other in bucket:
                if titles_match(title, rows[other].title_key()):
                    parents[parent_of(parents, i)] = parent_of(parents, other)
            bucket.append(i)
        groups: dict[int, list[ConcertRow]] = {}
        for i, row in enumerate(rows):
            groups.setdefault(parent_of(parents, i), []).append(row)
        winner_of: dict[int, int] = {}
        for group in groups.values():
            winner = max(group, key=lambda item: item.score())
            for row in group:
                if row.id != winner.id:
                    winner_of[row.id] = winner.id
        return winner_of


def is_date_as_time(hour: int, minute: int, text: str) -> bool:
    if minute < 1 or minute > 12 or hour < 1 or hour > 31:
        return False
    pattern = re.compile(rf"\b{hour}\.{minute:02d}\b|\b{hour}\.{minute}\.")
    return bool(pattern.search(text or ""))


@logged
def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--city", default="")
    parser.add_argument("--dry", action="store_true")
    args = parser.parse_args()
    conn = psycopg2.connect(DSN)
    conn.autocommit = True
    groups, marked = ConcertDedupe().apply(conn, city=args.city or None, dry=args.dry)
    print(f"groups={groups} marked={marked}", flush=True)
    conn.close()


if __name__ == "__main__":
    main()
