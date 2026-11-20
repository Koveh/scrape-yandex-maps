"""Scrape Wiener Stadthalle listings into `concerts` (city = Вена)."""
from __future__ import annotations

import argparse
import re

from bs4 import BeautifulSoup

from vienna_common import (
    HtmlVenueScraper,
    ViennaShow,
    parse_listing_date,
    parse_start_time,
)

LISTING_URL = "https://www.stadthalle.com/de/events"
SKIP_RE = re.compile(r"\b(ausverkauft|abgesagt)\b", re.I)


class StadthalleScraper(HtmlVenueScraper):
    listing_url = LISTING_URL
    source_channel = "stadthalle"
    venue = "Wiener Stadthalle"

    def parse(self, soup: BeautifulSoup) -> list[ViennaShow]:
        shows: list[ViennaShow] = []
        seen: set[str] = set()
        for item in soup.select(".event-item"):
            text = re.sub(r"\s+", " ", item.get_text(" ", strip=True))
            if SKIP_RE.search(text):
                continue
            link = item.select_one('a[href*="/events/"]')
            title = item.select_one("h2, h3, .event-item__title")
            name = re.sub(r"^Detailinfos zu\s+", "", title.get_text(" ", strip=True) if title else "", flags=re.I)
            img = item.select_one("img[src]")
            hall = self.venue
            hall_match = re.search(r"(Halle\s+[A-Z0-9]+)", text, re.I)
            if hall_match:
                hall = f"{self.venue} {hall_match.group(1)}"
            show = self.make_show(
                name=name,
                url=(link.get("href") if link else "") or LISTING_URL,
                start=parse_listing_date(text),
                start_time=parse_start_time(text),
                venue=hall,
                image_src=img.get("src") if img else None,
            )
            if show is None or show.url in seen:
                continue
            seen.add(show.url)
            shows.append(show)
        return shows


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--dry", action="store_true")
    args = parser.parse_args()
    StadthalleScraper(dry=args.dry).scrape()
