"""Scrape Kosmos Theater spielplan into `concerts`."""
from __future__ import annotations

import argparse
import re

from bs4 import BeautifulSoup

from vienna_common import HtmlVenueScraper, ViennaShow, parse_listing_date, parse_start_time

LISTING_URL = "https://kosmostheater.at/spielplan/"
SKIP_RE = re.compile(r"\b(abgesagt)\b", re.I)


class KosmosScraper(HtmlVenueScraper):
    listing_url = LISTING_URL
    source_channel = "kosmos"
    venue = "Kosmos Theater"

    def parse(self, soup: BeautifulSoup) -> list[ViennaShow]:
        shows: list[ViennaShow] = []
        for row in soup.select(".js-wpv-view-layout .row"):
            cols = row.select(":scope > div")
            if len(cols) < 2:
                continue
            date_text = cols[0].get_text(" ", strip=True)
            link = cols[1].select_one("a[href]")
            name = (link.get_text(" ", strip=True) if link else cols[1].get_text(" ", strip=True))
            time_text = cols[2].get_text(" ", strip=True) if len(cols) > 2 else ""
            if not name or name.upper() == "TITEL" or SKIP_RE.search(name):
                continue
            show = self.make_show(
                name=name,
                url=(link.get("href") if link else "") or LISTING_URL,
                start=parse_listing_date(date_text),
                start_time=parse_start_time(time_text or date_text),
            )
            if show:
                shows.append(show)
        return shows


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--dry", action="store_true")
    args = parser.parse_args()
    KosmosScraper(dry=args.dry).scrape()
