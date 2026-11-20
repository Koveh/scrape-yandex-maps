"""NÖKU calendars share `/de/api/events/` JSON (Grafenegg, Festspielhaus, …)."""
from __future__ import annotations

import re
from datetime import datetime, timezone
from urllib.parse import urlparse

from vienna_common import (
    HtmlVenueScraper,
    ViennaShow,
    logged,
    parse_iso_datetime,
    strip_html,
)

SKIP_TITLE = re.compile(
    r"\b(bustransfer|shuttle|schlossführung|einführung|schulvorstellung|stadtspaziergang)\b",
    re.I,
)


class NoekuScraper(HtmlVenueScraper):
    api_path = "/de/api/events/"
    max_pages = 20
    page_size = 50

    def api_origin(self) -> str:
        parsed = urlparse(self.listing_url)
        return f"{parsed.scheme}://{parsed.netloc}"

    def api_url(self, page: int) -> str:
        stamp = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%S.000Z")
        return (
            f"{self.api_origin()}{self.api_path}"
            f"?date={stamp}&page={page}&page_size={self.page_size}"
        )

    def event_url(self, event: dict) -> str:
        slug = event.get("slug") or ""
        if isinstance(slug, dict):
            slug = slug.get("de") or slug.get("en") or ""
        event_id = event.get("id")
        if slug and event_id:
            return f"{self.listing_url.rstrip('/')}/{slug}/{event_id}"
        return self.listing_url

    def event_prices(self, event: dict) -> tuple[int | None, int | None]:
        euros: list[int] = []
        for row in event.get("prices") or []:
            if not isinstance(row, dict):
                continue
            raw = row.get("price")
            if raw in (None, ""):
                continue
            euros.append(int(float(str(raw))))
        if not euros:
            return None, None
        return min(euros), max(euros)

    def event_room(self, event: dict) -> str:
        room = event.get("room")
        if isinstance(room, dict):
            return str(room.get("name") or room.get("title") or "")
        return str(room or "")

    def parse_event(self, event: dict) -> ViennaShow | None:
        name = (event.get("name") or "").strip()
        extra = strip_html(event.get("subtitle") or event.get("description_short") or "")
        if extra and extra.lower() not in name.lower():
            name = f"{name} — {extra}"
        if not name or SKIP_TITLE.search(name):
            return None
        start, start_time = parse_iso_datetime(event.get("date_start") or "")
        thumbs = event.get("header_image_thumbnails") or {}
        image_src = thumbs.get("medium") or thumbs.get("card")
        price_from, price_to = self.event_prices(event)
        return self.make_show(
            name=name,
            url=self.event_url(event),
            start=start,
            start_time=start_time,
            venue=self.event_room(event) or self.venue,
            image_src=image_src,
            description=extra,
            price_from=price_from,
            price_to=price_to,
        )

    def parse_payload(self, payload: dict) -> list[ViennaShow]:
        shows: list[ViennaShow] = []
        for event in payload.get("results") or []:
            if not isinstance(event, dict):
                continue
            show = self.parse_event(event)
            if show is not None:
                shows.append(show)
        return shows

    @logged
    def scrape(self) -> None:
        shows: list[ViennaShow] = []
        seen: set[str] = set()
        empty_pages = 0
        for page in range(1, self.max_pages + 1):
            payload = self.fetch_json(self.api_url(page))
            page_shows = self.parse_payload(payload if isinstance(payload, dict) else {})
            total = payload.get("count") if isinstance(payload, dict) else None
            print(f"  page={page} cards={len(page_shows)} total={total}", flush=True)
            if not page_shows:
                empty_pages += 1
                if empty_pages >= 2:
                    break
                continue
            empty_pages = 0
            added = 0
            for show in page_shows:
                key = f"{show.url}|{show.start}|{show.start_time}"
                if key in seen:
                    continue
                seen.add(key)
                shows.append(show)
                added += 1
            if added == 0:
                break
            if isinstance(payload, dict) and not payload.get("next"):
                break
        print(f"cards={len(shows)}", flush=True)
        self.store.persist(shows)
