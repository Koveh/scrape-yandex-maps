"""Scrape Viper Room Vienna listings into `concerts` (city = Вена)."""
from __future__ import annotations

import argparse
import re

from bs4 import BeautifulSoup

from vienna_common import HtmlVenueScraper, ViennaShow, parse_listing_date, parse_start_time

LISTING_URL = "https://www.viper-room.at/"


class ViperScraper(HtmlVenueScraper):
    listing_url = LISTING_URL
    source_channel = "viper"
    venue = "Viper Room"

    def parse(self, soup: BeautifulSoup) -> list[ViennaShow]:
        shows: list[ViennaShow] = []
        seen: set[str] = set()
        for item in soup.select("li.event_item"):
            link = item.select_one("a[href]")
            name_el = item.select_one(".event_name, .event_title")
            date_el = item.select_one(".event_date_monthyear")
            text = re.sub(r"\s+", " ", item.get_text(" ", strip=True))
            show = self.make_show(
                name=(name_el.get_text(" ", strip=True) if name_el else ""),
                url=(link.get("href") if link else "") or LISTING_URL,
                start=parse_listing_date((date_el.get_text(" ", strip=True) if date_el else "") or text),
                start_time=parse_start_time(text),
                image_src=None,
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
    ViperScraper(dry=args.dry).scrape()
