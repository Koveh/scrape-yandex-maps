"""Scrape Kabarett Simpl into `concerts` (city = Вена)."""
from __future__ import annotations

import argparse
import re

from bs4 import BeautifulSoup

from vienna_common import HtmlVenueScraper, ViennaShow, listing_image_src, parse_iso_datetime, parse_start_time

LISTING_URL = "https://simpl.at/tickets"
SKIP_RE = re.compile(r"\b(abgesagt|ausverkauft)\b", re.I)


class SimplScraper(HtmlVenueScraper):
    listing_url = LISTING_URL
    source_channel = "simpl"
    venue = "Kabarett Simpl"

    def parse(self, soup: BeautifulSoup) -> list[ViennaShow]:
        shows: list[ViennaShow] = []
        for item in soup.select("article.tickets"):
            text = item.get_text(" ", strip=True)
            if SKIP_RE.search(text):
                continue
            title = item.select_one(".show-title a") or item.select_one(".show-title")
            name = title.get_text(" ", strip=True) if title else ""
            href = ""
            if title and title.name == "a":
                href = title.get("href") or ""
            elif title:
                inner = title.select_one("a[href]")
                href = inner.get("href") if inner else ""
            subtitle = item.select_one("h4")
            start, start_time = parse_iso_datetime(item.get("data-attr-date") or "")
            show = self.make_show(
                name=name,
                url=href or LISTING_URL,
                start=start,
                start_time=start_time or parse_start_time(text),
                description=subtitle.get_text(" ", strip=True) if subtitle else "",
                image_src=listing_image_src(item),
            )
            if show:
                shows.append(show)
        return shows


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--dry", action="store_true")
    args = parser.parse_args()
    SimplScraper(dry=args.dry).scrape()
