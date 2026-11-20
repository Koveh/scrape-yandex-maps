"""Scrape SASS Vienna listings into `concerts` (city = Вена)."""
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

LISTING_URL = "https://sassvienna.com/en/events"
SKIP_RE = re.compile(r"\b(sold out|cancelled|ausverkauft|abgesagt)\b", re.I)


class SassScraper(HtmlVenueScraper):
    listing_url = LISTING_URL
    source_channel = "sass"
    venue = "SASS Vienna"

    def parse(self, soup: BeautifulSoup) -> list[ViennaShow]:
        shows: list[ViennaShow] = []
        seen: set[str] = set()
        for item in soup.select(".event"):
            text = re.sub(r"\s+", " ", item.get_text(" ", strip=True))
            if SKIP_RE.search(text):
                continue
            link = item.select_one('a[href*="/events/"]')
            title = item.select_one(".title h3, h3, h2")
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
    SassScraper(dry=args.dry).scrape()
