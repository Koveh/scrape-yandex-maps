"""Scrape Reigen Live into `concerts` (city = Вена)."""
from __future__ import annotations

import argparse
from datetime import date, datetime
from html import unescape

from vienna_common import (
    ViennaShow,
    ViennaStore,
    logged,
    occurrence_id,
    parse_price,
    strip_html,
    url_message_id,
)

API = "https://www.reigen.at/wp-json/tribe/events/v1/events"
SOURCE_CHANNEL = "reigen"
VENUE = "Reigen"


class ReigenScraper:
    def __init__(self, dry: bool = False) -> None:
        self.store = ViennaStore(SOURCE_CHANNEL, dry=dry)

    def fetch_page(self, page: int, start: str) -> dict:
        response = self.store.session.get(
            API,
            params={"per_page": 50, "page": page, "start_date": start},
            timeout=60,
        )
        response.raise_for_status()
        return response.json()

    def parse_event(self, payload: dict) -> ViennaShow | None:
        name = unescape(str(payload.get("title") or "")).strip()
        url = str(payload.get("url") or "")
        if not name or not url:
            return None
        start_raw = str(payload.get("start_date") or "")
        start_dt = datetime.fromisoformat(start_raw) if start_raw else None
        start = start_dt.date() if start_dt else None
        start_time = start_dt.time().replace(second=0, microsecond=0) if start_dt else None
        if start is not None and start < date.today():
            return None
        image = payload.get("image") or {}
        image_src = image.get("url") if isinstance(image, dict) else None
        description = strip_html(str(payload.get("description") or ""))[:500]
        price_from, price_to = parse_price(description)
        source_id = int(payload.get("id") or 0) or url_message_id(url)
        return ViennaShow(
            description=description,
            image_src=image_src,
            name=name,
            price_from=price_from,
            price_to=price_to,
            source_channel=SOURCE_CHANNEL,
            source_message_id=occurrence_id(source_id, start, start_time),
            start=start,
            start_time=start_time,
            url=url,
            venue=VENUE,
        )

    @logged
    def scrape(self) -> None:
        start = date.today().isoformat()
        page = 1
        pages = 1
        shows: list[ViennaShow] = []
        seen: set[str] = set()
        while page <= pages:
            payload = self.fetch_page(page, start)
            pages = int(payload.get("total_pages") or page)
            for event in payload.get("events") or []:
                show = self.parse_event(event)
                if show is None or show.url in seen:
                    continue
                seen.add(show.url)
                shows.append(show)
            print(f"page={page}/{pages} cards={len(shows)}", flush=True)
            page += 1
        self.store.persist(shows)


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--dry", action="store_true")
    args = parser.parse_args()
    ReigenScraper(dry=args.dry).scrape()
