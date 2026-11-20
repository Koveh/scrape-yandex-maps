"""Scrape Schauspielhaus Wien calendar into `concerts`."""
from __future__ import annotations

import argparse

from bs4 import BeautifulSoup

from vienna_common import HtmlVenueScraper, ViennaShow, parse_listing_date, parse_start_time

LISTING_URL = "https://www.schauspielhaus.at/spielplan"


class SchauspielhausScraper(HtmlVenueScraper):
    listing_url = LISTING_URL
    source_channel = "schauspielhaus"
    venue = "Schauspielhaus"

    def parse(self, soup: BeautifulSoup) -> list[ViennaShow]:
        shows: list[ViennaShow] = []
        for item in soup.select(".kalender-eintrag"):
            title = item.select_one("h2, h3, .kalender-titel, a")
            name = ""
            href = LISTING_URL
            for heading in item.select("h2, h3"):
                raw = heading.get_text(" ", strip=True)
                if raw and raw.lower() not in {"aktuelle termine"}:
                    name = raw
                    break
            link = item.select_one("a[href]")
            if link:
                href = link.get("href") or LISTING_URL
                if not name:
                    name = link.get_text(" ", strip=True)
            text = item.get_text(" ", strip=True)
            show = self.make_show(
                name=name,
                url=href,
                start=parse_listing_date(text),
                start_time=parse_start_time(text),
            )
            if show:
                shows.append(show)
        return shows


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--dry", action="store_true")
    args = parser.parse_args()
    SchauspielhausScraper(dry=args.dry).scrape()
