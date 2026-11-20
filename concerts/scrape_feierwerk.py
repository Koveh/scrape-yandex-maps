"""Scrape Feierwerk Munich listings into `concerts` (city = Мюнхен)."""
from __future__ import annotations

import argparse
import re

from bs4 import BeautifulSoup

from vienna_common import (
    HtmlVenueScraper,
    MUNICH_CITY,
    ViennaShow,
    parse_listing_date,
    parse_start_time,
)

LISTING_URL = "https://www.feierwerk.de/konzert-kulturprogramm/kkp"
SKIP_RE = re.compile(r"\b(abgesagt)\b", re.I)
HALLS = ("Sunny Red", "Kranhalle", "Halle X", "Feierraum", "Westend", "Hansa 39", "Orangehouse")


class FeierwerkScraper(HtmlVenueScraper):
    city = MUNICH_CITY
    listing_url = LISTING_URL
    source_channel = "feierwerk"
    venue = "Feierwerk"

    def hall_name(self, text: str) -> str:
        for hall in HALLS:
            if hall.lower() in text.lower():
                return hall
        return self.venue

    def parse(self, soup: BeautifulSoup) -> list[ViennaShow]:
        shows: list[ViennaShow] = []
        seen: set[str] = set()
        for card in soup.select(".event-fullwidth-card"):
            text = re.sub(r"\s+", " ", card.get_text(" ", strip=True))
            if SKIP_RE.search(text):
                continue
            link = card.select_one("a[href]")
            href = (link.get("href") if link else "") or LISTING_URL
            title = card.select_one(".event-artist-name, h2, h3, .event-title")
            img = card.select_one("img[src]")
            name = title.get_text(" ", strip=True).split("|")[0] if title else ""
            if not name and img:
                name = img.get("alt") or ""
            start = parse_listing_date(href) or parse_listing_date(text)
            show = self.make_show(
                name=name,
                url=href,
                start=start,
                start_time=parse_start_time(text),
                venue=self.hall_name(text),
                image_src=img.get("src") if img else None,
            )
            if show is None or show.url in seen:
                continue
            seen.add(show.url)
            shows.append(show)
        return shows


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--dry", action="store_true")
    args = parser.parse_args()
    FeierwerkScraper(dry=args.dry).scrape()
