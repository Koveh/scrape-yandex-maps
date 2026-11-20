"""Scrape planet.tt halls (Gasometer, Szene, SimmCity) into `concerts`."""
from __future__ import annotations

import argparse
import re

from bs4 import BeautifulSoup

from vienna_common import (
    HtmlVenueScraper,
    ViennaShow,
    parse_listing_date,
    parse_start_time,
)

LISTING_URL = "https://planet.tt/"
HALLS = {
    "gasometer": "Gasometer",
    "szene": "Szene Wien",
    "simmcity": "SimmCity",
    "simm city": "SimmCity",
}


class PlanetScraper(HtmlVenueScraper):
    listing_url = LISTING_URL
    source_channel = "planet"
    venue = "planet.tt"

    def hall_name(self, location: str) -> str:
        key = re.sub(r"\s+", " ", (location or "").lower())
        for needle, name in HALLS.items():
            if needle in key:
                return name
        return self.venue

    def parse(self, soup: BeautifulSoup) -> list[ViennaShow]:
        shows: list[ViennaShow] = []
        seen: set[str] = set()
        for card in soup.select(".pl-card[data-postid]"):
            location = card.get("data-location") or ""
            post_id = card.get("data-postid") or ""
            date_el = card.select_one(".pl-date")
            title = card.select_one("p.pl-small.pl-title") or card.select_one(".pl-title")
            name = title.get_text(" ", strip=True) if title else ""
            url = f"https://planet.tt/?p={post_id}"
            date_text = date_el.get_text(" ", strip=True) if date_el else card.get_text(" ", strip=True)
            img = card.select_one("img[src]")
            show = self.make_show(
                name=name,
                url=url,
                start=parse_listing_date(date_text),
                start_time=parse_start_time(card.get_text(" ", strip=True)),
                venue=self.hall_name(location),
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
    PlanetScraper(dry=args.dry).scrape()
