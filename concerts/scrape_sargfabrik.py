"""Scrape Sargfabrik Kulturhaus into `concerts` (city = Вена)."""
from __future__ import annotations

import argparse
import re

from bs4 import BeautifulSoup

from vienna_common import HtmlVenueScraper, ViennaShow, parse_listing_date, parse_start_time

LISTING_URL = "https://sargfabrik.at/veranstaltungen"
SKIP_RE = re.compile(r"(dialogforum|abgesagt)", re.I)


class SargfabrikScraper(HtmlVenueScraper):
    listing_url = LISTING_URL
    source_channel = "sargfabrik"
    venue = "Sargfabrik"

    def parse(self, soup: BeautifulSoup) -> list[ViennaShow]:
        shows: list[ViennaShow] = []
        for item in soup.select(".event-calendar-item"):
            title = item.select_one("a.title")
            name = title.get_text(" ", strip=True) if title else ""
            href = title.get("href") if title else ""
            text = item.get_text(" ", strip=True)
            if not name or SKIP_RE.search(name):
                continue
            img = item.select_one("img[src]")
            show = self.make_show(
                name=name,
                url=href or LISTING_URL,
                start=parse_listing_date(text),
                start_time=parse_start_time(text),
                image_src=img.get("src") if img else None,
                description=(item.select_one("a.subtitle") or item).get_text(" ", strip=True)[:300],
            )
            if show:
                shows.append(show)
        return shows


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--dry", action="store_true")
    args = parser.parse_args()
    SargfabrikScraper(dry=args.dry).scrape()
