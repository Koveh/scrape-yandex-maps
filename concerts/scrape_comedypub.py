"""Scrape The Comedy Pub Vienna listings into `concerts` (city = Вена).

Source: https://www.thecomedypub.at/events/ (WordPress plugin comedy-pub-events).
Rows are structured venue listings, so they land as status=kept (no Telegram curation).
Idempotent via UNIQUE(source_channel, source_message_id). Add more Vienna venues
as sibling scripts and a new Airflow task — see README.md.
"""
from __future__ import annotations

import argparse
import hashlib
import os
import re
import sys
from datetime import date, time, timedelta
from functools import wraps
from pathlib import Path
from typing import Any, Callable, TypeVar
from urllib.parse import urljoin

import psycopg2
import requests
from bs4 import BeautifulSoup
from bs4.element import Tag

AUTOMATION_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(AUTOMATION_ROOT))
sys.path.insert(0, str(Path(__file__).resolve().parent))
from events_image import create_minio_client, upload_avif_bytes  # noqa: E402
from concert_tags import ConcertTagger  # noqa: E402

ARCHIVE_URL = "https://www.thecomedypub.at/events/"
AJAX_URL = "https://www.thecomedypub.at/wp-admin/admin-ajax.php"
BUCKET = "concerts"
CITY = "Вена"
DSN = os.getenv("CONCERTS_DSN", "postgresql://koveh:Daniil77Daniil@65.109.88.77:5432/koveh")
HEADERS = {
    "User-Agent": "Mozilla/5.0 (compatible; koveh-concerts/1.0; +https://koveh.com/concerts)",
    "Accept": "text/html,application/json",
    "Origin": "https://www.thecomedypub.at",
    "Referer": ARCHIVE_URL,
    "X-Requested-With": "XMLHttpRequest",
}
MONTHS = {
    "jan": 1,
    "feb": 2,
    "mar": 3,
    "apr": 4,
    "may": 5,
    "jun": 6,
    "jul": 7,
    "aug": 8,
    "sep": 9,
    "oct": 10,
    "nov": 11,
    "dec": 12,
}
SOURCE_CHANNEL = "thecomedypub"
UPSERT = """
    INSERT INTO concerts (
        source_channel, source_message_id, source_url, website_url, name,
        description, raw_text, image_url, city, venue, start_date, start_time,
        price_from, price_to, status, tags
    )
    VALUES (
        %s, %s, %s, %s, %s,
        %s, %s, %s, %s, %s, %s, %s,
        %s, %s, 'kept', %s
    )
    ON CONFLICT (source_channel, source_message_id) DO UPDATE SET
        source_url = EXCLUDED.source_url,
        website_url = EXCLUDED.website_url,
        name = EXCLUDED.name,
        description = EXCLUDED.description,
        raw_text = EXCLUDED.raw_text,
        image_url = COALESCE(EXCLUDED.image_url, concerts.image_url),
        city = EXCLUDED.city,
        venue = EXCLUDED.venue,
        start_date = EXCLUDED.start_date,
        start_time = EXCLUDED.start_time,
        price_from = EXCLUDED.price_from,
        price_to = EXCLUDED.price_to,
        status = CASE
            WHEN concerts.status IN ('rejected', 'duplicate') THEN concerts.status
            ELSE 'kept'
        END,
        tags = CASE
            WHEN cardinality(concerts.tags) = 0 THEN EXCLUDED.tags
            ELSE concerts.tags
        END,
        updated_at = now()
"""
T = TypeVar("T")


def _safe_avif(minio: Any, key: int, payload: bytes) -> str | None:
    try:
        return upload_avif_bytes(minio, BUCKET, f"thecomedypub/{key}.avif", payload)
    except Exception as exc:  # noqa: BLE001 — one bad poster must not stop the listing
        print(f"  img skip avif {key}: {exc}", flush=True)
        return None


def logged(fn: Callable[..., T]) -> Callable[..., T]:
    @wraps(fn)
    def wrapper(*args: Any, **kwargs: Any) -> T:
        print(f"{fn.__name__}", flush=True)
        return fn(*args, **kwargs)

    return wrapper


def message_id(show_id: str, start: date | None, start_time: time | None, url: str) -> int:
    if show_id.isdigit() and start is not None:
        hhmm = start_time.hour * 100 + start_time.minute if start_time else 0
        return int(show_id) * 10**10 + int(start.strftime("%Y%m%d")) * 10000 + hhmm
    digest = hashlib.sha1(url.encode("utf-8")).digest()[:8]
    return int.from_bytes(digest, "big") % (2**63)


def parse_price(raw: str) -> tuple[int | None, int | None]:
    text = re.sub(r"\s+", " ", raw).strip()
    if not text or re.search(r"\bfree\b", text, re.I):
        return 0, 0
    nums = [int(n.replace(".", "").replace(",", "")) for n in re.findall(r"(\d[\d.,]*)", text)]
    if len(nums) >= 2:
        return nums[0], nums[1]
    if len(nums) == 1:
        return nums[0], nums[0]
    return None, None


def parse_start_date(url: str, day_text: str, month_text: str) -> date | None:
    dated = re.search(r"/(\d{4}-\d{2}-\d{2})/?(?:$|\?)", url)
    if dated:
        return date.fromisoformat(dated.group(1))
    month = MONTHS.get(month_text.strip()[:3].lower())
    if month is None or not day_text.isdigit():
        return None
    day = int(day_text)
    today = date.today()
    candidate = date(today.year, month, day)
    if candidate < today - timedelta(days=14):
        candidate = date(today.year + 1, month, day)
    return candidate


def parse_start_time(raw: str) -> time | None:
    match = re.search(r"\b([01]?\d|2[0-3]):([0-5]\d)\b", raw)
    if not match:
        return None
    return time(int(match.group(1)), int(match.group(2)))


def pick_image_url(img: Tag | None) -> str | None:
    if img is None:
        return None
    srcset = img.get("bv-orig-srcset") or img.get("srcset") or ""
    if srcset:
        first = srcset.split(",")[0].strip().split(" ")[0]
        if first.startswith("http"):
            return first
    src = img.get("src") or ""
    if src.startswith("http"):
        return src
    return None


class ComedyPubCard:
    def __init__(
        self,
        description: str,
        image_src: str | None,
        language: str,
        name: str,
        price_from: int | None,
        price_to: int | None,
        show_id: str,
        show_type: str,
        start: date | None,
        start_time: time | None,
        url: str,
        venue: str,
    ) -> None:
        self.description = description
        self.image_src = image_src
        self.language = language
        self.name = name
        self.price_from = price_from
        self.price_to = price_to
        self.show_id = show_id
        self.show_type = show_type
        self.start = start
        self.start_time = start_time
        self.url = url
        self.venue = venue

    @property
    def occurrence_key(self) -> int:
        return message_id(self.show_id, self.start, self.start_time, self.url)

    @property
    def raw_text(self) -> str:
        bits = [self.name, self.show_type, self.language, self.venue]
        if self.start:
            bits.append(self.start.isoformat())
        if self.start_time:
            bits.append(self.start_time.strftime("%H:%M"))
        return " · ".join(part for part in bits if part)


class ComedyPubScraper:
    def __init__(self, dry: bool = False) -> None:
        self.dry = dry
        self.session = requests.Session()
        self.session.headers.update(HEADERS)

    def download_image(self, src: str | None, key: int) -> str | None:
        if not src:
            return None
        response = self.session.get(src, timeout=30)
        if response.status_code != 200 or not response.content:
            print(f"  img skip http {response.status_code} {src}", flush=True)
            return src
        minio = create_minio_client()
        uploaded = _safe_avif(minio, key, response.content)
        return uploaded or src

    def extract_nonce(self, html: str) -> str:
        block = re.search(r"var CPE = (\{.*?\});", html)
        if not block:
            raise RuntimeError("CPE nonce block missing on listing page")
        nonce = re.search(r'"nonce":"([^"]+)"', block.group(1))
        if not nonce:
            raise RuntimeError("CPE nonce missing")
        return nonce.group(1)

    def fetch_page_html(self, nonce: str, paged: int, fallback_html: str) -> tuple[str, int]:
        response = self.session.post(
            AJAX_URL,
            data={
                "action": "cpe_filter_events",
                "nonce": nonce,
                "lang": "",
                "show_type": "",
                "price": "",
                "range": "",
                "s": "",
                "sort": "date_asc",
                "paged": str(paged),
            },
            timeout=60,
        )
        if response.status_code == 403:
            print("ajax 403, using listing HTML", flush=True)
            return fallback_html, 1
        response.raise_for_status()
        payload = response.json()
        if not payload.get("success"):
            raise RuntimeError(f"cpe_filter_events failed on page {paged}: {payload}")
        data = payload["data"]
        return str(data.get("html") or ""), int(data.get("max_pages") or paged)

    def parse_card(self, article: Tag) -> ComedyPubCard | None:
        title_link = article.select_one(".cpe-card-title a") or article.select_one("a.cpe-view-link")
        if title_link is None:
            return None
        name = title_link.get_text(strip=True)
        href = title_link.get("href") or ""
        if not name or not href:
            return None
        url = urljoin(ARCHIVE_URL, href)
        date_block = article.select_one(".cpe-date-block")
        day_text = date_block.select_one(".dom").get_text(strip=True) if date_block and date_block.select_one(".dom") else ""
        month_text = date_block.select_one(".mon").get_text(strip=True) if date_block and date_block.select_one(".mon") else ""
        info_bits = [span.get_text(strip=True) for span in article.select(".cpe-card-info span")]
        time_raw = next((bit for bit in info_bits if re.search(r"\d:\d{2}", bit)), "")
        venue = next((bit for bit in info_bits if bit and ":" not in bit and bit.lower() not in {"english", "german"}), "The Comedy Pub")
        price_el = article.select_one(".cpe-price")
        price_from, price_to = parse_price(price_el.get_text(" ", strip=True) if price_el else "")
        language = str(article.get("data-language") or "")
        show_type = str(article.get("data-show-type") or "")
        sold_out = article.select_one(".cpe-card-tag--status-soldout") is not None
        parts = [p for p in (show_type, language) if p]
        if sold_out:
            parts.append("Sold out")
        return ComedyPubCard(
            description=" · ".join(parts),
            image_src=pick_image_url(article.select_one("img")),
            language=language,
            name=name[:255],
            price_from=price_from,
            price_to=price_to,
            show_id=str(article.get("data-show-id") or ""),
            show_type=show_type,
            start=parse_start_date(url, day_text, month_text),
            start_time=parse_start_time(time_raw),
            url=url,
            venue=venue or "The Comedy Pub",
        )

    def parse_cards(self, html: str) -> list[ComedyPubCard]:
        soup = BeautifulSoup(html, "html.parser")
        cards: list[ComedyPubCard] = []
        seen: set[str] = set()
        for article in soup.select("article.cpe-card"):
            card = self.parse_card(article)
            if card is None or card.url in seen:
                continue
            seen.add(card.url)
            cards.append(card)
        return cards

    @logged
    def scrape(self) -> None:
        listing = self.session.get(ARCHIVE_URL, timeout=60)
        listing.raise_for_status()
        nonce = self.extract_nonce(listing.text)
        all_cards: list[ComedyPubCard] = []
        seen: set[str] = set()
        paged = 1
        max_pages = 1
        while paged <= max_pages:
            html, max_pages = self.fetch_page_html(nonce, paged, listing.text)
            for card in self.parse_cards(html):
                if card.url in seen:
                    continue
                seen.add(card.url)
                all_cards.append(card)
            print(f"page={paged}/{max_pages} cards={len(all_cards)}", flush=True)
            paged += 1

        if self.dry:
            for card in all_cards:
                print(
                    f"  {card.start} {card.start_time} {card.name[:70]} "
                    f"{card.price_from}-{card.price_to} {card.url}"
                )
            print(f"DONE dry seen={len(all_cards)}")
            return

        conn = psycopg2.connect(DSN)
        conn.autocommit = True
        inserted = 0
        tagger = ConcertTagger()
        for card in all_cards:
            image_url = None
            if card.image_src:
                image_url = self.download_image(card.image_src, card.occurrence_key)
            tags = tagger.classify(SOURCE_CHANNEL, card.name, card.venue, card.description)
            with conn.cursor() as cur:
                cur.execute(
                    UPSERT,
                    (
                        SOURCE_CHANNEL,
                        card.occurrence_key,
                        card.url,
                        card.url,
                        card.name,
                        card.description,
                        card.raw_text,
                        image_url,
                        CITY,
                        card.venue,
                        card.start,
                        card.start_time,
                        card.price_from,
                        card.price_to,
                        tags,
                    ),
                )
                inserted += cur.rowcount
        conn.close()
        print(f"DONE seen={len(all_cards)} upserted={inserted}")


def run_scrape() -> None:
    ComedyPubScraper(dry=False).scrape()


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--dry", action="store_true")
    args = parser.parse_args()
    ComedyPubScraper(dry=args.dry).scrape()
