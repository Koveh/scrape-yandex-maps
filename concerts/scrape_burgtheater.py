"""Scrape Burgtheater / Akademietheater spielplan into `concerts`."""
from __future__ import annotations

import argparse
import re

from bs4 import BeautifulSoup

from vienna_common import HtmlVenueScraper, ViennaShow, parse_iso_datetime, parse_listing_date, parse_start_time

LISTING_URL = "https://www.burgtheater.at/spielplan"
SKIP_RE = re.compile(r"\b(abgesagt)\b", re.I)


class BurgtheaterScraper(HtmlVenueScraper):
    listing_url = LISTING_URL
    source_channel = "burgtheater"
    venue = "Burgtheater"

    def hall_name(self, text: str) -> str:
        for hall in ("Akademietheater", "Kasino", "Vestibül", "Burgtheater"):
            if hall.lower() in text.lower():
                return hall
        return self.venue

    def parse(self, soup: BeautifulSoup) -> list[ViennaShow]:
        shows: list[ViennaShow] = []
        for item in soup.select(".s-event"):
            title = item.select_one(".s-event__title")
            name = title.get_text(" ", strip=True) if title else ""
            text = item.get_text(" ", strip=True)
            if not name or SKIP_RE.search(text):
                continue
            link = item.select_one("a[href]")
            href = (link.get("href") if link else "") or LISTING_URL
            start, start_time = parse_iso_datetime(href)
            if start is None:
                start = parse_listing_date(text)
                start_time = parse_start_time(text)
            show = self.make_show(
                name=name,
                url=href,
                start=start,
                start_time=start_time,
                venue=self.hall_name(text),
            )
            if show:
                shows.append(show)
        return shows


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--dry", action="store_true")
    args = parser.parse_args()
    BurgtheaterScraper(dry=args.dry).scrape()
