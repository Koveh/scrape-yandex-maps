"""Лужники events afisha (halls around the stadium complex)."""
from __future__ import annotations

import argparse

from bs4 import BeautifulSoup

from moscow_common import MOSCOW_CITY, parse_ru_date, parse_ru_time
from vienna_common import HtmlVenueScraper, ViennaShow

LISTING_URL = "https://www.luzhniki.ru/afisha/"


class LuzhnikiScraper(HtmlVenueScraper):
    city = MOSCOW_CITY
    listing_url = LISTING_URL
    source_channel = "luzhniki"
    venue = "Лужники"

    def fetch_soup(self, url: str | None = None) -> BeautifulSoup:
        response = self.store.session.get(
            url or self.listing_url, timeout=90, verify=False
        )
        response.raise_for_status()
        return BeautifulSoup(response.text, "html.parser")

    def parse(self, soup: BeautifulSoup) -> list[ViennaShow]:
        shows: list[ViennaShow] = []
        seen: set[str] = set()
        for card in soup.select(".card_event, .card.card_event"):
            title = card.select_one(".card__link, .card__label")
            name = (title.get_text(" ", strip=True) if title else "").strip()
            if len(name) < 3:
                continue
            link = card.select_one("a[href]")
            href = (link.get("href") if link else "") or LISTING_URL
            text = card.get_text(" ", strip=True)
            start = parse_ru_date(text)
            if start is None:
                continue
            key = f"{href}|{start}|{name.lower()}"
            if key in seen:
                continue
            seen.add(key)
            place = card.select_one(".card__place")
            venue = (place.get_text(" ", strip=True) if place else "") or self.venue
            img = card.select_one("img[src], img[data-src]")
            image_src = None
            if img:
                image_src = img.get("src") or img.get("data-src")
            show = self.make_show(
                name=name,
                url=href,
                start=start,
                start_time=parse_ru_time(text),
                venue=venue,
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
    LuzhnikiScraper(dry=args.dry).scrape()
