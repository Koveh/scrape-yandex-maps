"""Scrape P1 Club Munich nights into `concerts`."""
from __future__ import annotations

import argparse
import re

from bs4 import BeautifulSoup

from vienna_common import HtmlVenueScraper, MUNICH_CITY, ViennaShow, parse_listing_date, parse_start_time

LISTING_URL = "https://www.p1-club.de/"
DATEISH = re.compile(r"^(FR|SA|SO|MO|DI|MI|DO)/\d{1,2}/\d{2}$", re.I)


class P1Scraper(HtmlVenueScraper):
    city = MUNICH_CITY
    listing_url = LISTING_URL
    source_channel = "p1"
    venue = "P1"

    def parse(self, soup: BeautifulSoup) -> list[ViennaShow]:
        shows: list[ViennaShow] = []
        for item in soup.select(".teaser-item"):
            link = item.select_one("a[href]")
            heading = item.select_one("h2")
            sub = item.select_one("p")
            name = heading.get_text(" ", strip=True) if heading else ""
            extra = sub.get_text(" ", strip=True) if sub else ""
            if DATEISH.match(name) and extra:
                name = extra
            text = item.get_text(" ", strip=True)
            img = item.select_one("img[src]")
            show = self.make_show(
                name=name,
                url=(link.get("href") if link else "") or LISTING_URL,
                start=parse_listing_date(text),
                start_time=parse_start_time(text),
                description=extra[:300],
                image_src=img.get("src") if img else None,
            )
            if show:
                shows.append(show)
        return shows


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--dry", action="store_true")
    args = parser.parse_args()
    P1Scraper(dry=args.dry).scrape()
