"""Scrape Kabarett Niedermair into `concerts` (city = Вена)."""
from __future__ import annotations

import argparse
import re
from urllib.parse import urljoin

from bs4 import BeautifulSoup

from vienna_common import (
    HtmlVenueScraper,
    ViennaShow,
    listing_image_src,
    parse_listing_date,
    parse_price,
    parse_start_time,
)

LISTING_URL = "https://www.niedermair.at/kabarett/09/2026"
SKIP_RE = re.compile(r"\b(abgesagt|ausverkauft)\b", re.I)


class NiedermairScraper(HtmlVenueScraper):
    listing_url = LISTING_URL
    source_channel = "niedermair"
    venue = "Kabarett Niedermair"

    def month_urls(self, soup: BeautifulSoup) -> list[str]:
        urls = [LISTING_URL]
        for link in soup.select('a[href*="/kabarett/"]'):
            href = urljoin(LISTING_URL, link.get("href") or "")
            if re.search(r"/kabarett/\d{2}/20\d{2}", href):
                urls.append(href.split("?")[0])
        return list(dict.fromkeys(urls))

    def parse(self, soup: BeautifulSoup) -> list[ViennaShow]:
        shows: list[ViennaShow] = []
        for row in soup.select("a.eventrow"):
            href = row.get("href") or ""
            name_el = row.select_one(".artistname")
            name = name_el.get_text(" ", strip=True) if name_el else ""
            text = row.get_text(" ", strip=True)
            if SKIP_RE.search(text) or not name:
                continue
            show = self.make_show(
                name=name,
                url=href or LISTING_URL,
                start=parse_listing_date(href) or parse_listing_date(text),
                start_time=parse_start_time(text),
                image_src=listing_image_src(row),
                description=(row.select_one(".rowDetails") or row).get_text(" ", strip=True)[:500],
                price_from=parse_price(text)[0],
                price_to=parse_price(text)[1],
            )
            if show:
                shows.append(show)
        return shows

    def scrape(self) -> None:
        first = self.fetch_soup(LISTING_URL)
        shows: list[ViennaShow] = []
        for url in self.month_urls(first):
            soup = first if url == LISTING_URL else self.fetch_soup(url)
            shows.extend(self.parse(soup))
        self.persist_shows(shows)


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--dry", action="store_true")
    args = parser.parse_args()
    NiedermairScraper(dry=args.dry).scrape()
