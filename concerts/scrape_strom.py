"""Scrape Strom Munich listings into `concerts` (city = Мюнхен)."""
from __future__ import annotations

import argparse
import re

from bs4 import BeautifulSoup

from vienna_common import (
    HtmlVenueScraper,
    MUNICH_CITY,
    ViennaShow,
    parse_listing_date,
    parse_start_time,
)

LISTING_URL = "https://strom-muc.de/"


class StromScraper(HtmlVenueScraper):
    city = MUNICH_CITY
    listing_url = LISTING_URL
    source_channel = "strom"
    venue = "Strom"

    def parse(self, soup: BeautifulSoup) -> list[ViennaShow]:
        shows: list[ViennaShow] = []
        seen: set[str] = set()
        for item in soup.select(".gdlr-event-item"):
            text = re.sub(r"\s+", " ", item.get_text(" ", strip=True))
            link = item.select_one("a[href]")
            title = item.select_one("h3, h2, .gdlr-event-title, a")
            img = item.select_one("img[src]")
            show = self.make_show(
                name=(title.get_text(" ", strip=True) if title else ""),
                url=(link.get("href") if link else "") or LISTING_URL,
                start=parse_listing_date(text),
                start_time=parse_start_time(text),
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
    StromScraper(dry=args.dry).scrape()
