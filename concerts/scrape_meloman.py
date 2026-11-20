"""Московская филармония (meloman.ru) — Tchaikovsky Hall & sibling stages."""
from __future__ import annotations

import argparse

from bs4 import BeautifulSoup

from moscow_common import MOSCOW_CITY, parse_ru_date, parse_ru_time
from vienna_common import HtmlVenueScraper, ViennaShow

LISTING_URL = "https://www.meloman.ru/"


class MelomanScraper(HtmlVenueScraper):
    city = MOSCOW_CITY
    listing_url = LISTING_URL
    source_channel = "meloman"
    venue = "Филармония"

    def fetch_soup(self, url: str | None = None) -> BeautifulSoup:
        # meloman.ru serves an expired cert from some networks — still scrape HTML.
        response = self.store.session.get(
            url or self.listing_url, timeout=90, verify=False
        )
        response.raise_for_status()
        return BeautifulSoup(response.text, "html.parser")

    def parse(self, soup: BeautifulSoup) -> list[ViennaShow]:
        shows: list[ViennaShow] = []
        seen: set[str] = set()
        for item in soup.select(".article-afisha"):
            title = item.select_one(".article-afisha__title, a")
            name = (title.get_text(" ", strip=True) if title else "").strip()
            link = item.select_one('a[href*="/concert/"]') or (
                title if title and title.name == "a" else None
            )
            href = (link.get("href") if link else "") or LISTING_URL
            text = item.get_text(" ", strip=True)
            time_node = item.select_one(".article-afisha__time")
            start = parse_ru_date(time_node.get_text(" ", strip=True) if time_node else text)
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
            place = item.select_one(".article-afisha__toolbar-cell, .article-afisha__footer")
            venue = (place.get_text(" ", strip=True) if place else "")[:80] or self.venue
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
    MelomanScraper(dry=args.dry).scrape()
