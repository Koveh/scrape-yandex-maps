"""Scrape Arena Wien listings into `concerts` (city = Вена)."""
from __future__ import annotations

import argparse
from typing import Any

from vienna_common import HtmlVenueScraper, ViennaShow, is_cancelled, logged, parse_iso_datetime

API = "https://arena.wien/DesktopModules/WebAPI/API/Event/Search"
LISTING_URL = "https://arena.wien/Home/Programm"


class ArenaScraper(HtmlVenueScraper):
    listing_url = LISTING_URL
    source_channel = "arena"
    venue = "Arena Wien"

    def parse_concert(self, payload: dict[str, Any]) -> ViennaShow | None:
        name = str(payload.get("Title") or "").strip()
        if not name or is_cancelled(name) or "ausverkauft" in name.lower():
            return None
        start, start_time = parse_iso_datetime(str(payload.get("DateBegin") or ""))
        url = str(payload.get("DetailUrl") or LISTING_URL)
        location = str(payload.get("Location") or "").strip()
        return self.make_show(
            name=name,
            url=url,
            start=start,
            start_time=start_time,
            venue=location or self.venue,
            description=str(payload.get("Subtitle") or ""),
        )

    def parse_payload(self, payload: Any) -> list[ViennaShow]:
        concerts = payload.get("concerts") if isinstance(payload, dict) else []
        shows: list[ViennaShow] = []
        seen: set[str] = set()
        for concert in concerts or []:
            if not isinstance(concert, dict):
                continue
            show = self.parse_concert(concert)
            if show is None or show.url in seen:
                continue
            seen.add(show.url)
            shows.append(show)
        return shows

    @logged
    def scrape(self) -> None:
        payload = self.fetch_json(
            f"{API}?searchTerm=&day=1&month=-1&year=-1&page=0&pageSize=10000"
            "&eventCategory=-1&abonnement=-1&cultureCode=de-AT&locationId=0"
        )
        shows = self.parse_payload(payload)
        print(f"cards={len(shows)}", flush=True)
        self.store.persist(shows)


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--dry", action="store_true")
    args = parser.parse_args()
    ArenaScraper(dry=args.dry).scrape()
