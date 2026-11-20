"""Scrape Münchner Kammerspiele spielplan into `concerts`."""
from __future__ import annotations

import argparse
from datetime import date

from bs4 import BeautifulSoup

from vienna_common import HtmlVenueScraper, MUNICH_CITY, ViennaShow, listing_image_src, parse_start_time

LISTING_URL = "https://www.muenchner-kammerspiele.de/de/programm/"


class KammerspieleScraper(HtmlVenueScraper):
    city = MUNICH_CITY
    listing_url = LISTING_URL
    source_channel = "kammerspiele"
    venue = "Münchner Kammerspiele"

    def hall_name(self, text: str) -> str:
        for token in ("Schauspielhaus", "Therese-Giehse-Halle", "Werkraum", "Habibi Kiosk", "Stadtraum"):
            if token.lower() in text.lower():
                return token
        return self.venue

    def parse(self, soup: BeautifulSoup) -> list[ViennaShow]:
        shows: list[ViennaShow] = []
        for group in soup.select(".events-group[data-date]"):
            raw = str(group.get("data-date") or "")
            try:
                start = date.fromisoformat(raw)
            except ValueError:
                continue
            for item in group.select("li.preview-event"):
                title = item.select_one(".preview-event__title")
                name = title.get_text(" ", strip=True) if title else ""
                href = str(item.get("data-href") or (title.get("href") if title else "") or "")
                text = item.get_text(" ", strip=True)
                show = self.make_show(
                    name=name,
                    url=href or LISTING_URL,
                    start=start,
                    start_time=parse_start_time(text),
                    venue=self.hall_name(text),
                    description=text[:400],
                    image_src=listing_image_src(item),
                )
                if show:
                    shows.append(show)
        return shows


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--dry", action="store_true")
    args = parser.parse_args()
    KammerspieleScraper(dry=args.dry).scrape()
