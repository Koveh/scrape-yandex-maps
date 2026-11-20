"""Fill missing concerts.image_url with AVIF posters. Never overwrites existing photos."""
from __future__ import annotations

import argparse
import os
import re
from functools import wraps
from typing import Callable, TypeVar
from urllib.parse import urljoin

import psycopg2
from bs4 import BeautifulSoup

from scrape_volksoper import LISTING_URL as VOLKSOPER_LISTING
from vienna_common import (
    DSN,
    ViennaStore,
    is_generic_image_url,
    is_venue_homepage,
    url_message_id,
)

T = TypeVar("T")
SKIP_FETCH_CHANNELS = frozenset({"staatsoper", "luckypunch"})
YEAH_HOST_MARK = "yeah.de"


def logged(fn: Callable[..., T]) -> Callable[..., T]:
    @wraps(fn)
    def wrapper(*args: object, **kwargs: object) -> T:
        print(f"{fn.__name__}", flush=True)
        return fn(*args, **kwargs)

    return wrapper


class ConcertImageBackfill:
    def __init__(
        self,
        channels: list[str] | None = None,
        dry: bool = False,
        dsn: str = DSN,
        limit: int | None = None,
    ) -> None:
        self.avif_by_src: dict[str, str | None] = {}
        self.channels = channels
        self.dry = dry
        self.dsn = dsn
        self.limit = limit
        self.page_images: dict[str, str | None] = {}
        self.stores: dict[str, ViennaStore] = {}
        self._volksoper_map: dict[str, str] | None = None

    def apply_group(self, channel: str, website_url: str, ids: list[int]) -> int:
        image_url = self.poster_url(channel, website_url)
        if not image_url:
            print(f"  skip {channel} n={len(ids)} {website_url[:80]}", flush=True)
            return 0
        if self.dry:
            print(f"  dry {channel} n={len(ids)} {image_url}", flush=True)
            return 0
        updated = self.update_ids(ids, image_url)
        print(f"  ok {channel} n={updated}/{len(ids)} {image_url}", flush=True)
        return updated

    def load_groups(self) -> list[tuple[str, str, list[int]]]:
        conn = psycopg2.connect(self.dsn)
        with conn.cursor() as cur:
            sql = """
                SELECT source_channel, website_url, array_agg(id ORDER BY id)
                FROM concerts
                WHERE status = 'kept'
                  AND start_date >= CURRENT_DATE
                  AND (image_url IS NULL OR btrim(image_url) = '')
                  AND website_url IS NOT NULL
                  AND btrim(website_url) <> ''
                  AND NOT (source_channel = ANY(%s))
            """
            params: list[object] = [list(SKIP_FETCH_CHANNELS)]
            if self.channels:
                sql += " AND source_channel = ANY(%s)"
                params.append(self.channels)
            sql += """
                GROUP BY source_channel, website_url
                ORDER BY count(*) DESC
            """
            if self.limit:
                sql += " LIMIT %s"
                params.append(self.limit)
            cur.execute(sql, params)
            rows = [(str(channel), str(url), [int(row_id) for row_id in ids]) for channel, url, ids in cur.fetchall()]
        conn.close()
        return rows

    def poster_url(self, channel: str, website_url: str) -> str | None:
        if self.skip_url(channel, website_url):
            return None
        page = website_url
        if channel == "volksoper":
            mapped = self.volksoper_image_page(website_url)
            if mapped:
                page = mapped
            elif "tickets.volksoper.at" in website_url or "filter[production]" in website_url:
                return None
        store = self.store_for(channel)
        if page not in self.page_images:
            self.page_images[page] = store.page_image(page)
        src = self.page_images[page]
        if not src or is_generic_image_url(src):
            return None
        if src not in self.avif_by_src:
            self.avif_by_src[src] = store.download_image(src, url_message_id(src))
        return self.avif_by_src[src]

    @logged
    def run(self) -> int:
        groups = self.load_groups()
        print(f"groups={len(groups)}", flush=True)
        updated = 0
        for channel, website_url, ids in groups:
            updated += self.apply_group(channel, website_url, ids)
        print(f"DONE image_filled={updated}", flush=True)
        return updated

    def skip_url(self, channel: str, website_url: str) -> bool:
        if channel in SKIP_FETCH_CHANNELS:
            return True
        if YEAH_HOST_MARK in website_url:
            return True
        return is_venue_homepage(website_url)

    def store_for(self, channel: str) -> ViennaStore:
        if channel not in self.stores:
            self.stores[channel] = ViennaStore(channel, dry=False)
        return self.stores[channel]

    def update_ids(self, ids: list[int], image_url: str) -> int:
        conn = psycopg2.connect(self.dsn)
        conn.autocommit = True
        with conn.cursor() as cur:
            cur.execute(
                """
                UPDATE concerts
                SET image_url = %s, updated_at = now()
                WHERE id = ANY(%s)
                  AND status = 'kept'
                  AND (image_url IS NULL OR btrim(image_url) = '')
                """,
                (image_url, ids),
            )
            updated = cur.rowcount
        conn.close()
        return updated

    def volksoper_image_page(self, website_url: str) -> str | None:
        mapping = self.volksoper_produktion_map()
        if website_url in mapping:
            return mapping[website_url]
        for pattern in (r"filter\[production\]=(\d+)", r"[?&](?:event|toevent)=(\d+)"):
            match = re.search(pattern, website_url)
            if match and match.group(1) in mapping:
                return mapping[match.group(1)]
        return None

    def volksoper_produktion_map(self) -> dict[str, str]:
        if self._volksoper_map is not None:
            return self._volksoper_map
        store = self.store_for("volksoper")
        response = store.session.get(VOLKSOPER_LISTING, timeout=90)
        response.raise_for_status()
        soup = BeautifulSoup(response.text, "html.parser")
        mapping: dict[str, str] = {}
        for item in soup.select("article.event"):
            prod = item.select_one("a[href*='/produktion/']")
            if not prod:
                continue
            prod_url = urljoin(VOLKSOPER_LISTING, prod.get("href") or "")
            if not prod_url:
                continue
            hrefs = [link.get("href") or "" for link in item.select("a[href]")]
            for href in hrefs:
                if not href:
                    continue
                mapping[urljoin(VOLKSOPER_LISTING, href)] = prod_url
                mapping[href] = prod_url
                for pattern in (r"filter\[production\]=(\d+)", r"[?&](?:event|toevent)=(\d+)"):
                    match = re.search(pattern, href)
                    if match:
                        mapping[match.group(1)] = prod_url
        self._volksoper_map = mapping
        print(f"volksoper_map={len(mapping)}", flush=True)
        return mapping


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--channels", default="")
    parser.add_argument("--dry", action="store_true")
    parser.add_argument("--limit", type=int, default=0)
    args = parser.parse_args()
    channels = [item.strip() for item in args.channels.split(",") if item.strip()]
    ConcertImageBackfill(
        channels=channels or None,
        dry=args.dry,
        dsn=os.getenv("CONCERTS_DSN", DSN),
        limit=args.limit or None,
    ).run()
