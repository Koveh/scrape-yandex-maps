"""Scrape Circus Krone Bau Munich programm into `concerts`."""
from __future__ import annotations

import argparse
import re

from bs4 import BeautifulSoup

from vienna_common import HtmlVenueScraper, MUNICH_CITY, ViennaShow, parse_listing_date, parse_start_time

LISTING_URL = "https://bau.circus-krone.com/programm/"
SKIP_RE = re.compile(r"sommerpause|keine veranstaltung", re.I)
PREFIX_RE = re.compile(r"^(achtung!?[- ]*verlegung!?[- ]*)", re.I)


class CircusKroneScraper(HtmlVenueScraper):
    city = MUNICH_CITY
    listing_url = LISTING_URL
    source_channel = "circuskron"
    venue = "Circus Krone Bau"

    def parse(self, soup: BeautifulSoup) -> list[ViennaShow]:
        shows: list[ViennaShow] = []
        for item in soup.select("article.fusion-portfolio-post"):
            name_el = item.select_one("h2")
            name = PREFIX_RE.sub("", name_el.get_text(" ", strip=True) if name_el else "").strip()
            text = re.sub(r"20\d{2}-\d{2}-\d{2}T[\d:+-]+", " ", item.get_text(" ", strip=True))
            if not name or SKIP_RE.search(name) or SKIP_RE.search(text):
                continue
            link = item.select_one("h2 a[href], a[href*='/veranstaltungen/']")
            img = item.select_one("img[src]")
            show = self.make_show(
                name=name,
                url=(link.get("href") if link else "") or LISTING_URL,
                start=parse_listing_date(text),
                start_time=parse_start_time(text),
                image_src=img.get("src") if img else None,
            )
            if show:
                shows.append(show)
        return shows


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--dry", action="store_true")
    args = parser.parse_args()
    CircusKroneScraper(dry=args.dry).scrape()
