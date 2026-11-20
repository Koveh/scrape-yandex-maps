"""Scrape Unterfahrt Munich jazz listings into `concerts` (city = Мюнхен)."""
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

LISTING_URL = "https://www.unterfahrt.de/"


class UnterfahrtScraper(HtmlVenueScraper):
    city = MUNICH_CITY
    listing_url = LISTING_URL
    source_channel = "unterfahrt"
    venue = "Unterfahrt"

    def parse(self, soup: BeautifulSoup) -> list[ViennaShow]:
        shows: list[ViennaShow] = []
        seen: set[str] = set()
        for item in soup.select(".b-events__el"):
            title = item.select_one(".b-events__el-title")
            date_el = item.select_one(".b-events__el-date")
            date_text = (date_el.get_text(" ", strip=True) if date_el else "").replace("•", ".")
            link = item.select_one('a[href*="dateID"]')
            img = item.select_one("img[src]")
            show = self.make_show(
                name=(title.get_text(" ", strip=True) if title else ""),
                url=(link.get("href") if link else "") or LISTING_URL,
                start=parse_listing_date(date_text),
                start_time=parse_start_time(date_text),
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
    UnterfahrtScraper(dry=args.dry).scrape()
