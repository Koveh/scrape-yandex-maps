"""Театр на Малой Бронной playbill -> concerts (Москва, kept)."""
from __future__ import annotations

import argparse
import re

from bs4 import BeautifulSoup

from moscow_common import MOSCOW_CITY, parse_ru_date, parse_ru_time
from vienna_common import HtmlVenueScraper, ViennaShow

LISTING_URL = "https://mbronnaya.ru/playbill/"


class MbronnayaScraper(HtmlVenueScraper):
    city = MOSCOW_CITY
    listing_url = LISTING_URL
    source_channel = "mbronnaya"
    venue = "Театр на Малой Бронной"

    def parse(self, soup: BeautifulSoup) -> list[ViennaShow]:
        shows: list[ViennaShow] = []
        current_date = None
        root = soup.select_one(".main-playbill, .playbill, body")
        if root is None:
            return shows
        for node in root.descendants:
            if getattr(node, "name", None) != "div":
                continue
            classes = set(node.get("class") or [])
            if "playbill--item-buyBlock-date" in classes:
                current_date = parse_ru_date(node.get_text(" ", strip=True))
                continue
            if "playbill--item" not in classes:
                continue
            title = node.select_one(".playbill--item-content-title, h3")
            name = title.get_text(" ", strip=True) if title else ""
            name = re.sub(r"\s+", " ", name).strip()
            if not name:
                continue
            link = node.select_one('a[href*="/performances/"]')
            href = (link.get("href") if link else "") or LISTING_URL
            text = node.get_text(" ", strip=True)
            time_node = node.select_one(".playbill--item-buyBlock-time")
            start_time = parse_ru_time(time_node.get_text(" ", strip=True) if time_node else text)
            hall = self._hall(text)
            show = self.make_show(
                name=name,
                url=href,
                start=current_date,
                start_time=start_time,
                venue=hall or self.venue,
                description=text[:500],
            )
            if show:
                shows.append(show)
        return shows

    def _hall(self, text: str) -> str | None:
        low = text.lower()
        for needle, label in (
            ("малая сцена на бронной", "Малая сцена на Бронной"),
            ("сцена на бронной", "Сцена на Бронной"),
            ("мельников", "Сцена «Мельников» на Стромынке"),
            ("стромынке", "Сцена «Мельников» на Стромынке"),
        ):
            if needle in low:
                return f"{self.venue} · {label}"
        return None


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--dry", action="store_true")
    args = parser.parse_args()
    MbronnayaScraper(dry=args.dry).scrape()
