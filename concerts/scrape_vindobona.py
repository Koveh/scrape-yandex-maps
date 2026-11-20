"""Scrape Das Vindobona listings into `concerts` (city = Вена)."""
from __future__ import annotations

import argparse
import re

from bs4 import BeautifulSoup

from vienna_common import HtmlVenueScraper, ViennaShow, parse_listing_date, parse_start_time

LISTING_URL = "https://vindobona.wien/events"
SKIP_RE = re.compile(r"\b(abgesagt|cancelled)\b", re.I)


class VindobonaScraper(HtmlVenueScraper):
    listing_url = LISTING_URL
    source_channel = "vindobona"
    venue = "Das Vindobona"

    def parse(self, soup: BeautifulSoup) -> list[ViennaShow]:
        shows: list[ViennaShow] = []
        seen: set[str] = set()
        for item in soup.select("li.event"):
            link = item.select_one('a[href*="/events/"]')
            title = item.select_one("h3 a, h3")
            name = (title.get_text(" ", strip=True) if title else "")
            if not name or SKIP_RE.search(item.get_text(" ", strip=True)):
                continue
            date_el = item.select_one(".datetime .date")
            time_el = item.select_one(".datetime .time")
            desc = item.select_one(".item-details")
            img = item.select_one("img[src]")
            show = self.make_show(
                name=name,
                url=(link.get("href") if link else "") or LISTING_URL,
                start=parse_listing_date(date_el.get_text(" ", strip=True) if date_el else item.get_text(" ", strip=True)),
                start_time=parse_start_time(time_el.get_text(" ", strip=True) if time_el else ""),
                description=(desc.get_text(" ", strip=True) if desc else "")[:500],
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
    VindobonaScraper(dry=args.dry).scrape()
