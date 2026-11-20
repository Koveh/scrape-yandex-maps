"""Театр им. Вахтангова — Moscow afisha."""
from __future__ import annotations

import argparse
import re
from datetime import datetime

from bs4 import BeautifulSoup

from moscow_common import MOSCOW_CITY, parse_ru_date, parse_ru_time
from vienna_common import HtmlVenueScraper, ViennaShow

LISTING_URL = "https://www.vakhtangov.ru/afisha/"
TICKET_DT = re.compile(r"datetime=(\d{4}-\d{2}-\d{2})-(\d{2})-(\d{2})")


class VakhtangovScraper(HtmlVenueScraper):
    city = MOSCOW_CITY
    listing_url = LISTING_URL
    source_channel = "vakhtangov"
    venue = "Вахтангова"

    def parse(self, soup: BeautifulSoup) -> list[ViennaShow]:
        shows: list[ViennaShow] = []
        seen: set[str] = set()
        for item in soup.select(".afisha-item"):
            show_link = item.select_one('a[href*="/show/"]')
            if not show_link:
                continue
            name = show_link.get_text(" ", strip=True)
            href = show_link.get("href") or LISTING_URL
            ticket = item.select_one('a[href*="datetime="]')
            start = start_time = None
            if ticket:
                match = TICKET_DT.search(ticket.get("href") or "")
                if match:
                    try:
                        start = datetime.strptime(match.group(1), "%Y-%m-%d").date()
                        start_time = datetime.strptime(
                            f"{match.group(2)}:{match.group(3)}", "%H:%M"
                        ).time()
                    except ValueError:
                        start = None
            text = item.get_text(" ", strip=True)
            if start is None:
                start = parse_ru_date(text)
                start_time = parse_ru_time(text)
            if start is None:
                continue
            key = f"{href}|{start}|{name.lower()}"
            if key in seen:
                continue
            seen.add(key)
            img = item.select_one("img[src], img[data-src]")
            image_src = None
            if img:
                image_src = img.get("src") or img.get("data-src")
            show = self.make_show(
                name=name,
                url=href,
                start=start,
                start_time=start_time,
                venue=self.venue,
                image_src=image_src,
                description=text[:500],
            )
            if show:
                shows.append(show)
        return shows


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--dry", action="store_true")
    args = parser.parse_args()
    VakhtangovScraper(dry=args.dry).scrape()
