"""Scrape Volkstheater Wien spielplan into `concerts` (city = Вена)."""
from __future__ import annotations

import argparse
import re

from bs4 import BeautifulSoup

from vienna_common import (
    HtmlVenueScraper,
    ViennaShow,
    parse_listing_date,
    parse_price,
    parse_start_time,
)

LISTING_URL = "https://www.volkstheater.at/spielplan/"
SKIP_RE = re.compile(r"\b(abgesagt)\b", re.I)


class VolkstheaterScraper(HtmlVenueScraper):
    listing_url = LISTING_URL
    source_channel = "volkstheater"
    venue = "Volkstheater"

    def parse(self, soup: BeautifulSoup) -> list[ViennaShow]:
        shows: list[ViennaShow] = []
        for item in soup.select("article.event"):
            text = item.get_text(" ", strip=True)
            if SKIP_RE.search(text):
                continue
            link = item.select_one('a[href*="/produktion/"], a[href*="/event/"]')
            name = (link.get_text(" ", strip=True) if link else "") or (
                item.select_one("h2, h3").get_text(" ", strip=True) if item.select_one("h2, h3") else ""
            )
            hall = item.select_one(".location, .spielstaette")
            img = item.select_one("img[data-src], img[src]")
            image_src = (img.get("data-src") if img else None) or (img.get("src") if img else None)
            if image_src and image_src.startswith("data:"):
                image_src = img.get("data-src") if img else None
            price_from, price_to = parse_price(text)
            show = self.make_show(
                name=name,
                url=(link.get("href") if link else "") or LISTING_URL,
                start=parse_listing_date(text),
                start_time=parse_start_time(text),
                venue=hall.get_text(" ", strip=True) if hall else self.venue,
                image_src=image_src,
                price_from=price_from,
                price_to=price_to,
            )
            if show:
                shows.append(show)
        return shows


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--dry", action="store_true")
    args = parser.parse_args()
    VolkstheaterScraper(dry=args.dry).scrape()
