"""Zaryadye Concert Hall (Moscow) afisha."""
from __future__ import annotations

import argparse

from bs4 import BeautifulSoup

from moscow_common import MOSCOW_CITY, parse_ru_date, parse_ru_time
from vienna_common import HtmlVenueScraper, ViennaShow

LISTING_URL = "https://www.zaryadyehall.ru/afisha/"


class ZaryadyeScraper(HtmlVenueScraper):
    city = MOSCOW_CITY
    listing_url = LISTING_URL
    source_channel = "zaryadye"
    venue = "Зарядье"

    def parse(self, soup: BeautifulSoup) -> list[ViennaShow]:
        shows: list[ViennaShow] = []
        seen: set[str] = set()
        current_date = None
        root = soup.select_one(".events__list, .events__content, .events") or soup
        for node in root.descendants:
            if getattr(node, "name", None) is None:
                continue
            classes = " ".join(node.get("class") or [])
            if "events__date" in classes and "events__item" not in classes:
                current_date = parse_ru_date(node.get_text(" ", strip=True))
                continue
            if "events__item" not in classes:
                continue
            title = node.select_one(".events__item_title")
            name = (title.get_text(" ", strip=True) if title else "").strip()
            if len(name) < 3:
                continue
            link = node.select_one("a[href*='/events/']") or node.select_one("a[href]")
            href = (link.get("href") if link else "") or LISTING_URL
            text = node.get_text(" ", strip=True)
            start = parse_ru_date(text) or current_date
            if start is None:
                continue
            key = f"{href}|{start}|{name.lower()}"
            if key in seen:
                continue
            seen.add(key)
            img = node.select_one("img[src], img[data-src]")
            image_src = None
            if img:
                image_src = img.get("src") or img.get("data-src")
            show = self.make_show(
                name=name,
                url=href,
                start=start,
                start_time=parse_ru_time(text),
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
    ZaryadyeScraper(dry=args.dry).scrape()
