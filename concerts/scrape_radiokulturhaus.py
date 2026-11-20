"""Scrape ORF Radiokulturhaus into `concerts` (city = Вена)."""
from __future__ import annotations

import argparse
from datetime import date

from bs4 import BeautifulSoup

from vienna_common import HtmlVenueScraper, ViennaShow, parse_listing_date, parse_start_time

LISTING_URL = "https://radiokulturhaus.orf.at/programm"


class RadiokulturhausScraper(HtmlVenueScraper):
    listing_url = LISTING_URL
    source_channel = "radiokulturhaus"
    venue = "ORF Radiokulturhaus"

    def month_urls(self) -> list[str]:
        today = date.today()
        urls = [LISTING_URL]
        year, month = today.year, today.month
        for _ in range(6):
            urls.append(f"{LISTING_URL}?filter={year}{month:02d}")
            month += 1
            if month > 12:
                month = 1
                year += 1
        return list(dict.fromkeys(urls))

    def parse(self, soup: BeautifulSoup) -> list[ViennaShow]:
        shows: list[ViennaShow] = []
        for item in soup.select(".listItem"):
            title = item.select_one("h2 a")
            name = title.get_text(" ", strip=True) if title else ""
            href = title.get("href") if title else ""
            date_el = item.select_one(".listDate")
            date_text = date_el.get_text(" ", strip=True) if date_el else ""
            img = item.select_one("img[src]")
            show = self.make_show(
                name=name,
                url=href or LISTING_URL,
                start=parse_listing_date(date_text),
                start_time=parse_start_time(date_text),
                image_src=img.get("src") if img else None,
            )
            if show:
                shows.append(show)
        return shows

    def scrape(self) -> None:
        shows: list[ViennaShow] = []
        for url in self.month_urls():
            shows.extend(self.parse(self.fetch_soup(url)))
        self.persist_shows(shows)


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--dry", action="store_true")
    args = parser.parse_args()
    RadiokulturhausScraper(dry=args.dry).scrape()
