"""Scrape Theater Drachengasse concerts/impro into `concerts` (city = Вена)."""
from __future__ import annotations

import argparse
import re
from urllib.parse import urljoin

from bs4 import BeautifulSoup

from vienna_common import HtmlVenueScraper, ViennaShow, parse_listing_date

LISTING_URLS = (
    "https://www.drachengasse.at/spielplan_kategorie.asp?id=2",
    "https://www.drachengasse.at/spielplan_kategorie.asp?id=3",
    "https://www.drachengasse.at/spielplan_kategorie.asp?id=4",
)
SKIP_RE = re.compile(r"(jurypreis|abgesagt)", re.I)


class DrachengasseScraper(HtmlVenueScraper):
    listing_url = LISTING_URLS[0]
    source_channel = "drachengasse"
    venue = "Theater Drachengasse"

    def parse(self, soup: BeautifulSoup) -> list[ViennaShow]:
        shows: list[ViennaShow] = []
        for link in soup.select('a[href*="spielplan_detail.asp"]'):
            name = re.sub(r"\s+", " ", link.get_text(" ", strip=True))
            href = urljoin(self.listing_url, link.get("href") or "")
            if not name or SKIP_RE.search(name):
                continue
            detail = self.fetch_soup(href)
            text = detail.get_text(" ", strip=True)
            start = parse_listing_date(text)
            if start is None:
                continue
            show = self.make_show(name=name, url=href, start=start, description=text[:300])
            if show:
                shows.append(show)
        return shows

    def scrape(self) -> None:
        shows: list[ViennaShow] = []
        for url in LISTING_URLS:
            shows.extend(self.parse(self.fetch_soup(url)))
        self.persist_shows(shows)


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--dry", action="store_true")
    args = parser.parse_args()
    DrachengasseScraper(dry=args.dry).scrape()
