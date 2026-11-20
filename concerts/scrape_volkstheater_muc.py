"""Scrape Münchner Volkstheater spielplan into `concerts`."""
from __future__ import annotations

import argparse
import re

from bs4 import BeautifulSoup

from vienna_common import HtmlVenueScraper, MUNICH_CITY, ViennaShow, parse_listing_date, parse_start_time

LISTING_URL = "https://www.muenchner-volkstheater.de/programm/spielplan"
SKIP_RE = re.compile(r"abgesagt|ausgefallen", re.I)


class VolkstheaterMucScraper(HtmlVenueScraper):
    city = MUNICH_CITY
    listing_url = LISTING_URL
    source_channel = "volkstheater_muc"
    venue = "Münchner Volkstheater"

    def parse(self, soup: BeautifulSoup) -> list[ViennaShow]:
        shows: list[ViennaShow] = []
        for title in soup.select(".schedule--title a"):
            name = title.get_text(" ", strip=True)
            block = title
            for _ in range(10):
                if block is None:
                    break
                if block.select_one(".schedule--day"):
                    break
                block = block.parent
            text = block.get_text(" ", strip=True) if block else name
            if not name or SKIP_RE.search(text):
                continue
            hall = block.select_one(".field-event-location") if block else None
            show = self.make_show(
                name=name,
                url=title.get("href") or LISTING_URL,
                start=parse_listing_date(text),
                start_time=parse_start_time(text),
                venue=(hall.get_text(" ", strip=True) if hall else "") or self.venue,
            )
            if show:
                shows.append(show)
        return shows


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--dry", action="store_true")
    args = parser.parse_args()
    VolkstheaterMucScraper(dry=args.dry).scrape()
