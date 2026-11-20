"""Afisha.ru Moscow concert (+ theater) schedules -> concerts (kept)."""
from __future__ import annotations

import argparse
import json
import re
from datetime import datetime
from urllib.parse import urljoin

from moscow_common import MOSCOW_CITY
from vienna_common import HtmlVenueScraper, ViennaShow, session_get

PAGES = (
    ("afisha_concerts", "https://www.afisha.ru/msk/schedule_concert/", "concert"),
    ("afisha_theatre", "https://www.afisha.ru/msk/schedule_theatre/", "event"),
)
BASE = "https://www.afisha.ru"


def _extract_root(html: str) -> dict:
    match = re.search(r"\['root'\]\s*=\s*(\{)", html)
    if not match:
        return {}
    start = match.end(1) - 1
    depth = 0
    for index, char in enumerate(html[start:], start):
        if char == "{":
            depth += 1
        elif char == "}":
            depth -= 1
            if depth == 0:
                return json.loads(html[start : index + 1])
    return {}


class AfishaMoscowScraper(HtmlVenueScraper):
    city = MOSCOW_CITY
    listing_url = PAGES[0][1]
    source_channel = "afisha_concerts"
    venue = "Москва"

    def __init__(self, source: str, url: str, dry: bool = False) -> None:
        self.source_channel = source
        self.listing_url = url
        super().__init__(dry=dry)

    def scrape(self) -> None:
        response = session_get(self.store.session, self.listing_url, timeout=90)
        if response is None:
            print(f"skip {self.source_channel} empty response", flush=True)
            return
        root = _extract_root(response.text)
        items = (((root.get("model") or {}).get("ScheduleWidget") or {}).get("Items")) or []
        shows: list[ViennaShow] = []
        for row in items:
            tile = row.get("Tile") or {}
            if tile.get("IsCanceled"):
                continue
            name = (tile.get("Name") or "").strip()
            path = (tile.get("Url") or "").split("#", 1)[0]
            if not name or not path:
                continue
            schedule = tile.get("ScheduleInfo") or {}
            notice = tile.get("Notice") or {}
            place = (notice.get("Place") or {}).get("Name") or self.venue
            start_raw = schedule.get("MinScheduleDate")
            start = start_time = None
            if start_raw:
                try:
                    parsed = datetime.fromisoformat(start_raw)
                    start = parsed.date()
                    start_time = parsed.time().replace(second=0, microsecond=0)
                except ValueError:
                    start = None
            image = ((tile.get("Image16x9") or tile.get("Image1x1") or {}).get("Url"))
            price = schedule.get("MinPrice")
            price_from = int(price) if isinstance(price, (int, float)) and price >= 50 else None
            show = self.make_show(
                name=name,
                url=urljoin(BASE, path),
                start=start,
                start_time=start_time,
                venue=place,
                image_src=image,
                description=(tile.get("Description") or "")[:500],
                price_from=price_from,
            )
            if show:
                shows.append(show)
        print(f"cards={len(shows)} source={self.source_channel}", flush=True)
        self.persist_shows(shows)


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--dry", action="store_true")
    args = parser.parse_args()
    for source, url, _kind in PAGES:
        AfishaMoscowScraper(source, url, dry=args.dry).scrape()
