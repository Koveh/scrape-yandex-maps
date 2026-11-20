"""Shared Vienna concert upsert + helpers for venue scrapers."""
from __future__ import annotations

import hashlib
import os
import re
import sys
from datetime import date, time, timedelta
from functools import wraps
from pathlib import Path
from typing import Any, Callable, TypeVar
from urllib.parse import urljoin, urlparse

import psycopg2
import requests
from bs4 import BeautifulSoup

AUTOMATION_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(AUTOMATION_ROOT))
sys.path.insert(0, str(Path(__file__).resolve().parent))
from events_image import create_minio_client, upload_avif_bytes  # noqa: E402
from concert_tags import ConcertTagger  # noqa: E402
from concert_dedupe import ConcertDedupe  # noqa: E402

BUCKET = "concerts"
MUNICH_CITY = "Мюнхен"
NOE_CITY = "Нижняя Австрия"
CITY = "Вена"
DSN = os.getenv("CONCERTS_DSN", "postgresql://koveh:Daniil77Daniil@65.109.88.77:5432/koveh")
GERMAN_MONTHS = {
    "jan": 1,
    "jän": 1,
    "feb": 2,
    "mär": 3,
    "mar": 3,
    "apr": 4,
    "mai": 5,
    "may": 5,
    "jun": 6,
    "jul": 7,
    "aug": 8,
    "sep": 9,
    "okt": 10,
    "oct": 10,
    "nov": 11,
    "dez": 12,
    "dec": 12,
}
HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
        "(KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36"
    ),
    "Accept": "text/html,application/json",
    "Accept-Language": "de-DE,de;q=0.9,en;q=0.8",
}
SKIPPABLE_HTTP = {403, 404, 408, 410, 429, 500, 502, 503, 504}
IMAGE_HEADERS = {
    "Accept": "image/avif,image/webp,image/*,*/*;q=0.8",
}
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


def absolute_url(base: str, href: str) -> str:
    return urljoin(base, href)


def listing_image_src(node: Any) -> str | None:
    if node is None:
        return None
    img = node if getattr(node, "name", None) == "img" else None
    if img is None and hasattr(node, "select_one"):
        img = node.select_one("img")
    if img is None:
        return None
    for attr in ("src", "data-src", "data-lazy-src", "data-original", "data-lz-original-src"):
        src = img.get(attr)
        if src and not str(src).startswith("data:"):
            return str(src)
    srcset = img.get("srcset") or img.get("data-srcset")
    if not srcset:
        return None
    first = str(srcset).split(",")[0].strip().split(" ")[0]
    return first or None


GENERIC_IMAGE_RE = re.compile(
    r"default[_-]?og|og[_-]?default|favicon|apple-touch|logo|sprite|\bicon\b|icon_fb|"
    r"arrow-down|opengraph-image|/bth_seo/|default\.jpg|designmark|placeholder|pixel\.gif|"
    r"menu-second|glamofthefuture|werkraum_logo|habibi_logo|mk_habibi|mk_musik_logo|"
    r"/portals/_default/skins/",
    re.I,
)


def first_content_image(html: str) -> str | None:
    src = og_image(html)
    if src and not is_generic_image_url(src):
        return src
    soup = BeautifulSoup(html, "html.parser")
    for img in soup.select("img"):
        candidate = listing_image_src(img)
        if not candidate or candidate.startswith("data:"):
            continue
        classes = " ".join(img.get("class") or [])
        if is_generic_image_url(candidate) or GENERIC_IMAGE_RE.search(classes):
            continue
        path = candidate.lower().split("?", 1)[0]
        if path.endswith(".svg"):
            continue
        if path.endswith((".jpg", ".jpeg", ".png", ".webp", ".avif", ".gif")):
            return candidate
        if "/uploads/" in path or "/media/" in path or "/event" in path or "/files/" in path:
            return candidate
    return None


def is_generic_image_url(src: str | None) -> bool:
    if not src:
        return True
    return bool(GENERIC_IMAGE_RE.search(src))


def is_venue_homepage(url: str) -> bool:
    if not url:
        return True
    path = (urlparse(url).path or "/").rstrip("/") or "/"
    return path.lower() in {"/", "/en", "/de", "/home", "/index.html", "/index.php"}


def background_image_url(style: str) -> str | None:
    match = re.search(r"url\(['\"]?([^)'\"]+)['\"]?\)", style or "")
    if not match:
        return None
    return match.group(1)


def day_month_date(
    day: int,
    month: int,
    year: int | None = None,
    bump_past: bool = True,
) -> date | None:
    if not (1 <= day <= 31 and 1 <= month <= 12):
        return None
    today = date.today()
    use_year = year or today.year
    candidate = date(use_year, month, day)
    if year is None and bump_past and candidate < today - timedelta(days=14):
        candidate = date(today.year + 1, month, day)
    return candidate


def german_date(raw: str) -> date | None:
    text = re.sub(r"^[A-Za-zÄäÖöÜüß]{2}\s+", "", (raw or "").strip())
    match = re.search(r"(\d{1,2})\.\s*([A-Za-zÄäÖöÜüß]+)\s+(\d{4})", text)
    if not match:
        return None
    month = GERMAN_MONTHS.get(match.group(2)[:3].lower())
    if month is None:
        return None
    return date(int(match.group(3)), month, int(match.group(1)))


def german_month(raw: str) -> int | None:
    return GERMAN_MONTHS.get((raw or "").strip()[:3].lower())


def euro_amount(token: str) -> int | None:
    text = (token or "").strip().replace(" ", "")
    if not text:
        return None
    if re.fullmatch(r"\d+", text):
        return int(text)
    if re.fullmatch(r"\d{1,3}(\.\d{3})+(,\d{1,2})?", text):
        return int(text.split(",")[0].replace(".", ""))
    if re.fullmatch(r"\d+,\d{1,2}", text):
        return int(float(text.replace(",", ".")))
    if re.fullmatch(r"\d{1,3}(,\d{3})+(\.\d{1,2})?", text):
        return int(text.split(".")[0].replace(",", ""))
    if re.fullmatch(r"\d+\.\d{1,2}", text):
        return int(float(text))
    digits = re.sub(r"[^\d]", "", text)
    return int(digits) if digits else None


def http_status_is_skippable(status_code: int) -> bool:
    return status_code in SKIPPABLE_HTTP or status_code >= 500


def is_cancelled(raw: str) -> bool:
    return bool(re.search(r"\b(abgesagt|cancelled|canceled)\b", raw or "", re.I))


def session_get(session: requests.Session, url: str, timeout: int) -> requests.Response | None:
    response = session.get(url, timeout=timeout)
    if http_status_is_skippable(response.status_code):
        print(f"skip HTTP {response.status_code} {url}", flush=True)
        return None
    response.raise_for_status()
    return response


def logged(fn: Callable[..., T]) -> Callable[..., T]:
    @wraps(fn)
    def wrapper(*args: Any, **kwargs: Any) -> T:
        print(f"{fn.__name__}", flush=True)
        return fn(*args, **kwargs)

    return wrapper


def occurrence_id(source_id: int, start: date | None, start_time: time | None) -> int:
    if start is None:
        return source_id
    hhmm = start_time.hour * 100 + start_time.minute if start_time else 0
    return source_id * 10**10 + int(start.strftime("%Y%m%d")) * 10000 + hhmm


def og_image(html: str) -> str | None:
    soup = BeautifulSoup(html, "html.parser")
    tag = soup.select_one('meta[property="og:image"]')
    src = str(tag.get("content") or "").strip() if tag else ""
    if not src:
        return None
    if src.startswith("http://"):
        return "https://" + src[len("http://") :]
    return src


def parse_listing_date(raw: str, bump_past: bool = True) -> date | None:
    text = (raw or "").replace("•", ".").replace("|", " ")
    text = re.sub(r"\s+", " ", text).strip()
    iso = re.search(r"(20\d{2})-(\d{2})-(\d{2})", text)
    if iso:
        return date(int(iso.group(1)), int(iso.group(2)), int(iso.group(3)))
    dotted = re.search(r"(\d{1,2})\.(\d{1,2})\.(20\d{2}|\d{2})\b", text)
    if dotted:
        year = int(dotted.group(3))
        if year < 100:
            year += 2000
        return day_month_date(int(dotted.group(1)), int(dotted.group(2)), year)
    comma_dotted = re.search(r"(\d{1,2}),(\d{1,2})\.(20\d{2}|\d{2})\b", text)
    if comma_dotted:
        year = int(comma_dotted.group(3))
        if year < 100:
            year += 2000
        return day_month_date(int(comma_dotted.group(1)), int(comma_dotted.group(2)), year)
    slashed = re.search(r"(\d{1,2})/(\d{1,2})/(20\d{2}|\d{2})\b", text)
    if slashed:
        year = int(slashed.group(3))
        if year < 100:
            year += 2000
        return day_month_date(int(slashed.group(1)), int(slashed.group(2)), year)
    dotted_space_year = re.search(r"(\d{1,2})\.(\d{1,2})\s+(20\d{2}|\d{2})\b", text)
    if dotted_space_year:
        year = int(dotted_space_year.group(3))
        if year < 100:
            year += 2000
        return day_month_date(int(dotted_space_year.group(1)), int(dotted_space_year.group(2)), year)
    spaced_numeric = re.search(r"(\d{1,2})\s+(\d{1,2})\s+(20\d{2})\b", text)
    if spaced_numeric:
        return day_month_date(int(spaced_numeric.group(1)), int(spaced_numeric.group(2)), int(spaced_numeric.group(3)))
    if re.search(r"\bheute\b", text, re.I):
        return date.today()
    dashed = re.search(r"(\d{1,2})-(\d{1,2})-(20\d{2})", text)
    if dashed:
        return day_month_date(int(dashed.group(1)), int(dashed.group(2)), int(dashed.group(3)))
    named = re.search(r"(\d{1,2})\.?\s+([A-Za-zÄäÖöÜüß]{3,})\.?\s+(20\d{2})", text)
    if named:
        month = GERMAN_MONTHS.get(named.group(2)[:3].lower())
        if month:
            return date(int(named.group(3)), month, int(named.group(1)))
    named_no_year = re.search(r"(\d{1,2})\.\s*([A-Za-zÄäÖöÜüß]{3,})", text)
    if named_no_year:
        month = GERMAN_MONTHS.get(named_no_year.group(2)[:3].lower())
        if month:
            return day_month_date(int(named_no_year.group(1)), month, bump_past=bump_past)
    spaced = re.search(r"(\d{1,2})\s+([A-Za-zÄäÖöÜüß]{3,})(?:\s+(20\d{2}))?", text)
    if spaced:
        month = GERMAN_MONTHS.get(spaced.group(2)[:3].lower())
        if month:
            year = int(spaced.group(3)) if spaced.group(3) else None
            return day_month_date(int(spaced.group(1)), month, year, bump_past=bump_past)
    slash_month = re.search(r"(\d{1,2})\s*/\s*([A-Za-zÄäÖöÜüß]{3,})", text)
    if slash_month:
        month = GERMAN_MONTHS.get(slash_month.group(2)[:3].lower())
        if month:
            return day_month_date(int(slash_month.group(1)), month, bump_past=bump_past)
    day_month = re.search(r"(\d{1,2})\.(\d{1,2})\.(?!\d)", text)
    if day_month:
        return day_month_date(int(day_month.group(1)), int(day_month.group(2)), bump_past=bump_past)
    return german_date(text)


def parse_iso_datetime(raw: str) -> tuple[date | None, time | None]:
    match = re.search(r"(20\d{2})-(\d{1,2})-(\d{1,2})(?:[ T](\d{1,2}):(\d{2}))?", raw or "")
    if not match:
        return parse_listing_date(raw), parse_start_time(raw)
    start = date(int(match.group(1)), int(match.group(2)), int(match.group(3)))
    if match.group(4) is None:
        return start, parse_start_time(raw)
    return start, time(int(match.group(4)), int(match.group(5)))


def parse_price(raw: str) -> tuple[int | None, int | None]:
    text = re.sub(r"\s+", " ", raw or "").strip()
    if not text:
        return None, None
    if re.search(r"\b(free|gratis|eintritt frei|kostenlos)\b", text, re.I):
        return 0, 0
    ranged = re.search(
        r"(\d[\d.,]*)\s*(?:bis|–|-|to)\s*(\d[\d.,]*)\s*€|€\s*(\d[\d.,]*)\s*(?:bis|–|-|to)\s*(\d[\d.,]*)",
        text,
        re.I,
    )
    if ranged:
        left = euro_amount(ranged.group(1) or ranged.group(3) or "")
        right = euro_amount(ranged.group(2) or ranged.group(4) or "")
        if left is not None and right is not None:
            return left, right
    tokens = [group[0] or group[1] for group in re.findall(r"(\d[\d.,]*)\s*€|€\s*(\d[\d.,]*)", text)]
    euros = [euro_amount(token) for token in tokens]
    euros = [value for value in euros if value is not None]
    if len(euros) >= 2:
        return euros[0], euros[1]
    if len(euros) == 1:
        return euros[0], euros[0]
    return None, None


TIME_COLON_RE = re.compile(r"\b([01]?\d|2[0-3]):([0-5]\d)\s*(AM|PM)?\b", re.I)
TIME_UHR_RE = re.compile(r"\b([01]?\d|2[0-3])\.([0-5]\d)\s*Uhr\b", re.I)
DATE_DM_RE = re.compile(r"\b(\d{1,2})\.(\d{1,2})(?:\.\d{2,4})?")


def _clock_from_match(match: re.Match[str]) -> time | None:
    hour = int(match.group(1))
    minute = int(match.group(2))
    meridiem = ""
    if match.lastindex and match.lastindex >= 3:
        meridiem = (match.group(3) or "").upper()
    if meridiem == "PM" and hour < 12:
        hour += 12
    if meridiem == "AM" and hour == 12:
        hour = 0
    if hour > 23:
        return None
    return time(hour, minute)


def _looks_like_listing_date(clock: time, text: str) -> bool:
    if clock.minute < 1 or clock.minute > 12 or clock.hour < 1 or clock.hour > 31:
        return False
    for match in DATE_DM_RE.finditer(text):
        if int(match.group(1)) == clock.hour and int(match.group(2)) == clock.minute:
            return True
    return False


def parse_start_time(raw: str) -> time | None:
    text = (raw or "").replace("••", ":").replace("•", ":")
    for pattern in (TIME_COLON_RE, TIME_UHR_RE):
        for match in pattern.finditer(text):
            clock = _clock_from_match(match)
            if clock is not None and not _looks_like_listing_date(clock, text):
                return clock
    return None


def strip_html(raw: str) -> str:
    text = raw or ""
    if "<" not in text:
        return re.sub(r"\s+", " ", text).strip()
    text = BeautifulSoup(text, "html.parser").get_text(" ", strip=True)
    return re.sub(r"\s+", " ", text).strip()


def stable_id(url: str, start: date | None, start_time: time | None = None) -> int:
    stamp = start.isoformat() if start else ""
    clock = start_time.strftime("%H:%M") if start_time else ""
    digest = hashlib.sha1(f"{url}|{stamp}|{clock}".encode("utf-8")).digest()[:8]
    return int.from_bytes(digest, "big") % (2**63)


def url_message_id(url: str) -> int:
    digest = hashlib.sha1(url.encode("utf-8")).digest()[:8]
    return int.from_bytes(digest, "big") % (2**63)


class ViennaShow:
    def __init__(
        self,
        name: str,
        source_channel: str,
        source_message_id: int,
        url: str,
        venue: str,
        description: str = "",
        image_src: str | None = None,
        price_from: int | None = None,
        price_to: int | None = None,
        start: date | None = None,
        start_time: time | None = None,
        tags: list[str] | None = None,
    ) -> None:
        self.description = description
        self.image_src = image_src
        self.name = name[:255]
        self.price_from = price_from
        self.price_to = price_to
        self.source_channel = source_channel
        self.source_message_id = source_message_id
        self.start = start
        self.start_time = start_time
        self.tags = tags
        self.url = url
        self.venue = venue

    @property
    def raw_text(self) -> str:
        bits = [self.name, self.venue, self.description]
        if self.start:
            bits.append(self.start.isoformat())
        if self.start_time:
            bits.append(self.start_time.strftime("%H:%M"))
        return " · ".join(part for part in bits if part)


class ViennaStore:
    def __init__(self, source_channel: str, dry: bool = False, city: str = CITY) -> None:
        self.city = city
        self.dry = dry
        self.session = requests.Session()
        self.session.headers.update(HEADERS)
        self.source_channel = source_channel

    def download_image(self, src: str | None, key: int) -> str | None:
        if not src:
            return None
        if src.startswith("//"):
            src = f"https:{src}"
        if not src.startswith("http"):
            print(f"  img skip url {src}", flush=True)
            return None
        try:
            response = self.session.get(src, timeout=30, headers=IMAGE_HEADERS)
        except requests.RequestException as exc:
            print(f"  img skip {exc}", flush=True)
            return None
        if response.status_code != 200 or not response.content:
            print(f"  img skip http {response.status_code} {src}", flush=True)
            return None
        ctype = (response.headers.get("content-type") or "").lower()
        head = response.content[:24].lstrip().lower()
        if "text/html" in ctype or head.startswith(b"<!doctype") or head.startswith(b"<html"):
            print(f"  img skip html {src}", flush=True)
            return None
        return self._safe_avif(key, response.content)

    def page_image(self, url: str) -> str | None:
        if not url or not url.startswith("http"):
            return None
        try:
            response = self.session.get(url, timeout=20)
        except requests.RequestException as exc:
            print(f"  img skip page {exc}", flush=True)
            return None
        if response.status_code != 200 or not response.text:
            print(f"  img skip page {response.status_code} {url}", flush=True)
            return None
        src = first_content_image(response.text)
        if not src or is_generic_image_url(src):
            return None
        if src.startswith("//"):
            src = f"https:{src}"
        elif src.startswith("/"):
            src = urljoin(url, src)
        if not src.startswith("http") or is_generic_image_url(src):
            return None
        return src

    def persist(self, shows: list[ViennaShow]) -> int:
        if self.dry:
            for show in shows:
                print(
                    f"  {show.start} {show.start_time} {show.name[:70]} "
                    f"{show.price_from}-{show.price_to} {show.url}"
                )
            print(f"DONE dry source={self.source_channel} seen={len(shows)}")
            return 0
        conn = psycopg2.connect(DSN)
        conn.autocommit = True
        inserted = 0
        tagger = ConcertTagger()
        avif_by_src: dict[str, str | None] = {}
        page_images: dict[str, str | None] = {}

        def cached_avif(src: str | None, key: int) -> str | None:
            if not src or is_generic_image_url(src):
                return None
            if src not in avif_by_src:
                avif_by_src[src] = self.download_image(src, key)
            return avif_by_src[src]

        for show in shows:
            image_url = cached_avif(show.image_src, show.source_message_id)
            if image_url is None and show.url and not is_venue_homepage(show.url):
                if show.url not in page_images:
                    page_images[show.url] = self.page_image(show.url)
                image_url = cached_avif(page_images[show.url], show.source_message_id)
            tags = show.tags or tagger.classify(
                show.source_channel, show.name, show.venue, show.description
            )
            with conn.cursor() as cur:
                cur.execute(
                    UPSERT,
                    (
                        show.source_channel,
                        show.source_message_id,
                        show.url,
                        show.url,
                        show.name,
                        show.description or None,
                        show.raw_text,
                        image_url,
                        self.city,
                        show.venue,
                        show.start,
                        show.start_time,
                        show.price_from,
                        show.price_to,
                        tags,
                    ),
                )
                inserted += cur.rowcount
        groups, marked = ConcertDedupe().apply(conn, city=self.city)
        conn.close()
        print(
            f"DONE source={self.source_channel} seen={len(shows)} upserted={inserted} "
            f"dedupe_groups={groups} duplicates={marked}"
        )
        return inserted

    def _safe_avif(self, key: int, payload: bytes) -> str | None:
        try:
            return upload_avif_bytes(
                create_minio_client(),
                BUCKET,
                f"{self.source_channel}/{key}.avif",
                payload,
            )
        except Exception as exc:  # noqa: BLE001 — one bad poster must not stop the listing
            print(f"  img skip avif {key}: {exc}", flush=True)
            return None


class HtmlVenueScraper:
    city: str = CITY
    listing_url: str = ""
    source_channel: str = ""
    venue: str = ""

    def __init__(self, dry: bool = False) -> None:
        self.store = ViennaStore(self.source_channel, dry=dry, city=self.city)

    def fetch_json(self, url: str | None = None) -> Any:
        response = session_get(self.store.session, url or self.listing_url, timeout=90)
        if response is None:
            return {}
        return response.json()

    def fetch_soup(self, url: str | None = None) -> BeautifulSoup:
        self.active_url = url or self.listing_url
        response = session_get(self.store.session, self.active_url, timeout=90)
        if response is None:
            return BeautifulSoup("", "html.parser")
        html = response.content.decode("utf-8", errors="replace")
        return BeautifulSoup(html, "html.parser")

    def persist_shows(self, shows: list[ViennaShow]) -> None:
        unique: list[ViennaShow] = []
        seen: set[str] = set()
        for show in shows:
            key = f"{show.url}|{show.start}|{show.start_time}"
            if key in seen:
                continue
            seen.add(key)
            unique.append(show)
        print(f"cards={len(unique)}", flush=True)
        self.store.persist(unique)

    def make_show(
        self,
        name: str,
        url: str,
        start: date | None,
        start_time: time | None = None,
        venue: str | None = None,
        image_src: str | None = None,
        description: str = "",
        price_from: int | None = None,
        price_to: int | None = None,
    ) -> ViennaShow | None:
        name = re.sub(r"\s+", " ", (name or "")).strip()
        url = (url or "").strip()
        if not name or len(name) < 3 or not url or start is None:
            return None
        if start < date.today():
            return None
        if not url.startswith("http"):
            url = urljoin(self.listing_url, url)
        if image_src:
            if image_src.startswith("//"):
                image_src = f"https:{image_src}"
            elif image_src.startswith("/"):
                image_src = urljoin(self.listing_url, image_src)
        return ViennaShow(
            description=(description or "")[:500],
            image_src=image_src,
            name=name,
            price_from=price_from,
            price_to=price_to,
            source_channel=self.source_channel,
            source_message_id=stable_id(url, start),
            start=start,
            start_time=start_time,
            url=url,
            venue=venue or self.venue,
        )

    def parse(self, soup: BeautifulSoup) -> list[ViennaShow]:
        raise NotImplementedError

    @logged
    def scrape(self) -> None:
        try:
            soup = self.fetch_soup()
        except requests.HTTPError as exc:
            status = int(exc.response.status_code) if exc.response is not None else 0
            if status >= 500:
                print(f"skip {self.source_channel} http {status} {self.listing_url}", flush=True)
                return
            raise
        except requests.RequestException as exc:
            print(f"skip {self.source_channel} {exc}", flush=True)
            return
        self.persist_shows(self.parse(soup))

