"""Scrape MAK Wien calendar into `concerts` (city = Вена)."""
from __future__ import annotations

import argparse
import json
import re

from bs4 import BeautifulSoup

from vienna_common import HtmlVenueScraper, ViennaShow, parse_iso_datetime, parse_listing_date, parse_start_time

SKIP_RE = re.compile(r"\b(geschlossen|abgesagt|cancelled)\b", re.I)


class MakScraper(HtmlVenueScraper):
    listing_url = "https://www.mak.at/programm/kalender"
    source_channel = "mak"
    venue = "MAK"

    def parse(self, soup: BeautifulSoup) -> list[ViennaShow]:
        shows: list[ViennaShow] = []
        for block in soup.select('script[type="application/ld+json"]'):
            raw = block.string or ""
            if not raw.strip():
                continue
            data = json.loads(raw)
            rows = data if isinstance(data, list) else [data]
            for row in rows:
                if not isinstance(row, dict) or row.get("@type") != "Event":
                    continue
                name = str(row.get("name") or "").strip()
                if not name or SKIP_RE.search(name):
                    continue
                start, start_time = parse_iso_datetime(str(row.get("startDate") or ""))
                if start is None:
                    start = parse_listing_date(name)
                    start_time = parse_start_time(name)
                place = row.get("location")
                venue = self.venue
                if isinstance(place, dict):
                    venue = str(place.get("name") or venue)
                image = row.get("image")
                image_src = image[0] if isinstance(image, list) and image else image if isinstance(image, str) else None
                show = self.make_show(
                    name=name,
                    url=str(row.get("url") or self.listing_url),
                    start=start,
                    start_time=start_time,
                    venue=venue,
                    image_src=image_src,
                    description=str(row.get("description") or "")[:240],
                )
                if show is not None:
                    shows.append(show)
        return shows


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--dry", action="store_true")
    args = parser.parse_args()
    MakScraper(dry=args.dry).scrape()
