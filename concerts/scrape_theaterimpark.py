"""Scrape Theater im Park into `concerts` (city = Вена)."""
from __future__ import annotations

import argparse
import re

from bs4 import BeautifulSoup

from vienna_common import HtmlVenueScraper, ViennaShow, listing_image_src, parse_listing_date, parse_start_time

LISTING_URL = "https://theaterimpark.at/programm-tickets"
SKIP_RE = re.compile(r"\b(abgesagt)\b", re.I)


class TheaterImParkScraper(HtmlVenueScraper):
    listing_url = LISTING_URL
    source_channel = "theaterimpark"
    venue = "Theater im Park"

    def parse(self, soup: BeautifulSoup) -> list[ViennaShow]:
        shows: list[ViennaShow] = []
        for item in soup.select(".card"):
            artist = item.select_one(".artist")
            title = item.select_one("h4.title, .title")
            name = " · ".join(
                part
                for part in [
                    artist.get_text(" ", strip=True) if artist else "",
                    title.get_text(" ", strip=True) if title else "",
                ]
                if part
            )
            text = item.get_text(" ", strip=True)
            if SKIP_RE.search(text) or not name:
                continue
            link = item.select_one('a[href*="/programm/"]')
            show = self.make_show(
                name=name,
                url=(link.get("href") if link else "") or LISTING_URL,
                start=parse_listing_date(text),
                start_time=parse_start_time(text),
                image_src=listing_image_src(item),
            )
            if show:
                shows.append(show)
        return shows


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--dry", action="store_true")
    args = parser.parse_args()
    TheaterImParkScraper(dry=args.dry).scrape()
