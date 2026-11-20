"""Scrape WUK Vienna listings into `concerts` (city = Вена)."""
from __future__ import annotations

import argparse
import re

from bs4 import BeautifulSoup

from vienna_common import HtmlVenueScraper, ViennaShow, parse_listing_date, parse_start_time

LISTING_URL = "https://www.wuk.at/programm/"
SKIP_RE = re.compile(r"\b(ausverkauft|abgesagt|ausstellung|installation)\b", re.I)


class WukScraper(HtmlVenueScraper):
    listing_url = LISTING_URL
    source_channel = "wuk"
    venue = "WUK"

    def parse(self, soup: BeautifulSoup) -> list[ViennaShow]:
        shows: list[ViennaShow] = []
        seen: set[str] = set()
        for item in soup.select(".event-list-item"):
            themes = " ".join(el.get_text(" ", strip=True) for el in item.select(".theme-list-item"))
            if not re.search(r"konzert|musik", themes, re.I):
                continue
            meta = item.select_one(".event-list-item-meta-info")
            meta_text = meta.get_text(" ", strip=True) if meta else ""
            if re.search(r"\bbis\b", meta_text, re.I):
                continue
            name_el = item.select_one("h2 a") or item.select_one("h2")
            link = item.select_one('h2 a[href*="/programm/"]') or item.select_one('a[href*="/programm/"]')
            img = item.select_one("img[src]")
            show = self.make_show(
                name=(name_el.get_text(" ", strip=True) if name_el else ""),
                url=(link.get("href") if link else "") or LISTING_URL,
                start=parse_listing_date(meta_text),
                start_time=parse_start_time(meta_text),
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
    WukScraper(dry=args.dry).scrape()
