"""Scrape Milla Club Munich via KULTURpur month listings (official site is Cloudflare)."""
from __future__ import annotations

import argparse
from datetime import date

from bs4 import BeautifulSoup

from vienna_common import HtmlVenueScraper, MUNICH_CITY, ViennaShow, logged, parse_listing_date, parse_start_time

LISTING_URL = "https://www.kulturpur.de/buehnen/milla"


class MillaScraper(HtmlVenueScraper):
    city = MUNICH_CITY
    listing_url = LISTING_URL
    source_channel = "milla_kulturpur"
    venue = "Milla"

    def month_urls(self) -> list[str]:
        today = date.today()
        urls = [LISTING_URL]
        year, month = today.year, today.month
        for offset in range(0, 8):
            stamp = date(year + (month + offset - 1) // 12, (month + offset - 1) % 12 + 1, 1)
            urls.append(f"https://www.kulturpur.de/buehnen/milla/spielplan/{stamp.strftime('%Y-%m')}")
        return urls

    def parse(self, soup: BeautifulSoup) -> list[ViennaShow]:
        shows: list[ViennaShow] = []
        for row in soup.select(".eventlistrowinfotext a.bold"):
            name = row.get_text(" ", strip=True)
            href = row.get("href") or LISTING_URL
            block = row.find_parent("div")
            parent = block.parent if block else row.parent
            text = parent.get_text(" ", strip=True) if parent else name
            show = self.make_show(
                name=name,
                url=href,
                start=parse_listing_date(f"{text} {href}"),
                start_time=parse_start_time(text),
            )
            if show:
                shows.append(show)
        return shows

    @logged
    def scrape(self) -> None:
        shows: list[ViennaShow] = []
        seen: set[str] = set()
        for url in self.month_urls():
            soup = self.fetch_soup(url)
            page_shows = self.parse(soup)
            print(f"  {url} cards={len(page_shows)}", flush=True)
            for show in page_shows:
                key = f"{show.url}|{show.start}|{show.start_time}"
                if key in seen:
                    continue
                seen.add(key)
                shows.append(show)
        self.persist_shows(shows)


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--dry", action="store_true")
    args = parser.parse_args()
    MillaScraper(dry=args.dry).scrape()
