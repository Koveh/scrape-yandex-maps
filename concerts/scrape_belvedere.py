"""Scrape Belvedere program into `concerts` (city = Вена)."""
from __future__ import annotations

import argparse
import re

from bs4 import BeautifulSoup

from vienna_common import HtmlVenueScraper, ViennaShow, logged, parse_listing_date, parse_start_time

SKIP_RE = re.compile(r"\b(geschlossen|abgesagt)\b", re.I)


class BelvedereScraper(HtmlVenueScraper):
    listing_url = "https://www.belvedere.at/programm"
    max_pages = 8
    source_channel = "belvedere"
    venue = "Belvedere"

    def parse(self, soup: BeautifulSoup) -> list[ViennaShow]:
        shows: list[ViennaShow] = []
        for card in soup.select("article.teaser__base__item"):
            text = re.sub(r"\s+", " ", card.get_text(" ", strip=True))
            if SKIP_RE.search(text):
                continue
            title = card.select_one("h2, h3")
            name = title.get_text(" ", strip=True) if title else ""
            if not name:
                continue
            link = card.select_one("a[href*='/event/']")
            href = (link.get("href") if link else "") or self.listing_url
            place = card.select_one(".event-location")
            kind = card.select_one(".event-type")
            img = card.select_one("img[src]")
            extra = kind.get_text(" ", strip=True) if kind else ""
            show = self.make_show(
                name=name,
                url=href,
                start=parse_listing_date(text),
                start_time=parse_start_time(text),
                venue=place.get_text(" ", strip=True) if place else self.venue,
                image_src=img.get("src") if img else None,
                description=extra,
            )
            if show is not None:
                shows.append(show)
        return shows

    @logged
    def scrape(self) -> None:
        shows: list[ViennaShow] = []
        for page in range(0, self.max_pages):
            url = self.listing_url if page == 0 else f"{self.listing_url}?page={page}"
            page_shows = self.parse(self.fetch_soup(url))
            print(f"  page={page} cards={len(page_shows)}", flush=True)
            if not page_shows:
                break
            before = len(shows)
            shows.extend(page_shows)
            if len(shows) == before:
                break
        self.persist_shows(shows)


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--dry", action="store_true")
    args = parser.parse_args()
    BelvedereScraper(dry=args.dry).scrape()
