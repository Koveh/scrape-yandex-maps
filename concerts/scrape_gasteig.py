"""Scrape Gasteig Munich JSON listings into `concerts` (city = Мюнхен)."""
from __future__ import annotations

import argparse
import re
from typing import Any

from vienna_common import HtmlVenueScraper, MUNICH_CITY, ViennaShow, logged, parse_iso_datetime

LISTING_URL = "https://www.gasteig.de/wp-json/api/events/upcoming"
SKIP_TYPES = {"ausstellung", "exhibition", "führung", "workshop"}
KEEP_HALL = re.compile(
    r"isarphilharmonie|saal x|kleiner saal|black box|carl-orff",
    re.I,
)
KEEP_NAME = re.compile(
    r"konzert|concert|orchester|philharmon|sinfonie|jazz|recital|oper|"
    r"klavierabend|dunkelkonzert|quartett|trio|ensemble",
    re.I,
)
SKIP_NAME = re.compile(
    r"sprachcafé|leseclub|rallye|ehrenamt|crafternoon|nadel-treff|"
    r"zeichentreff|pen and paper|gaming|workshop|führung|ausstellung|"
    r"konzertführer",
    re.I,
)


class GasteigScraper(HtmlVenueScraper):
    city = MUNICH_CITY
    listing_url = LISTING_URL
    source_channel = "gasteig"
    venue = "Gasteig"

    def event_start(self, payload: dict[str, Any]):
        return parse_iso_datetime(
            str(payload.get("startDate") or payload.get("start") or payload.get("date") or "")
        )

    def event_end(self, payload: dict[str, Any]):
        return parse_iso_datetime(str(payload.get("endDate") or payload.get("end") or ""))

    def hall_name(self, payload: dict[str, Any]) -> str:
        location = payload.get("location") or payload.get("venue") or {}
        if isinstance(location, dict):
            name = str(location.get("name") or location.get("title") or "").strip()
            if name:
                return name
        if isinstance(location, str) and location.strip():
            return location.strip()
        return self.venue

    def parse_payload(self, payload: Any) -> list[ViennaShow]:
        events = payload.get("events") if isinstance(payload, dict) else payload
        if not isinstance(events, list):
            events = []
        shows: list[ViennaShow] = []
        seen: set[str] = set()
        for event in events:
            if not isinstance(event, dict):
                continue
            kind = str(event.get("type") or event.get("category") or "").lower()
            if any(skip in kind for skip in SKIP_TYPES):
                continue
            start, start_time = self.event_start(event)
            end, _end_time = self.event_end(event)
            if start and end and (end - start).days > 3:
                continue
            name = str(event.get("title") or event.get("name") or "").strip()
            venue = self.hall_name(event)
            if SKIP_NAME.search(f"{name} {venue}"):
                continue
            if not KEEP_HALL.search(venue) and not KEEP_NAME.search(name):
                continue
            url = str(event.get("url") or event.get("link") or event.get("permalink") or LISTING_URL)
            image = event.get("image") or event.get("thumbnail")
            image_src = image.get("url") if isinstance(image, dict) else image
            show = self.make_show(
                name=name,
                url=url,
                start=start,
                start_time=start_time,
                venue=venue,
                image_src=str(image_src) if image_src else None,
                description=str(event.get("excerpt") or event.get("description") or "")[:500],
            )
            if show is None or show.url in seen:
                continue
            seen.add(show.url)
            shows.append(show)
        return shows

    @logged
    def scrape(self) -> None:
        shows = self.parse_payload(self.fetch_json())
        print(f"cards={len(shows)}", flush=True)
        self.store.persist(shows)


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--dry", action="store_true")
    args = parser.parse_args()
    GasteigScraper(dry=args.dry).scrape()
