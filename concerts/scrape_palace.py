"""Scrape Schloss Schönbrunn / Palace Concerts dates into `concerts`."""
from __future__ import annotations

import argparse
import re

from bs4 import BeautifulSoup

from vienna_common import HtmlVenueScraper, ViennaShow, parse_listing_date, parse_start_time

LISTING_URL = "https://www.palaceconcertsvienna.com/de/spielort/termine"
SKIP_RE = re.compile(r"\b(abgesagt)\b", re.I)


class PalaceScraper(HtmlVenueScraper):
    listing_url = LISTING_URL
    source_channel = "palace"
    venue = "Schloss Schönbrunn Konzerte"

    def parse(self, soup: BeautifulSoup) -> list[ViennaShow]:
        shows: list[ViennaShow] = []
        for row in soup.select(".eventcalendartable tbody tr"):
            text = row.get_text(" ", strip=True)
            if not text or SKIP_RE.search(text):
                continue
            place = row.select_one(".produkt a, .produkt")
            hall = place.get_text(" ", strip=True) if place else self.venue
            time_el = row.select_one(".zeit")
            href = place.get("href") if place is not None and place.name == "a" else LISTING_URL
            start = parse_listing_date(text, bump_past=False)
            show = self.make_show(
                name=f"Schloss Schönbrunn Konzert — {hall}",
                url=href or LISTING_URL,
                start=start,
                start_time=parse_start_time(time_el.get_text(" ", strip=True) if time_el else text),
                venue=hall or self.venue,
            )
            if show:
                shows.append(show)
        return shows


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--dry", action="store_true")
    args = parser.parse_args()
    PalaceScraper(dry=args.dry).scrape()
