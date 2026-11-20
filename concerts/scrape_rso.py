"""Scrape RSO Wien concert calendar into `concerts` (Vienna halls only)."""
from __future__ import annotations

import argparse
import re

from bs4 import BeautifulSoup

from vienna_common import HtmlVenueScraper, ViennaShow, parse_iso_datetime, parse_listing_date, parse_start_time

LISTING_URL = "https://rso.orf.at/programm"
SKIP_PLACE = re.compile(r"graz|brno|salzburg|linz|innsbruck|klagenfurt", re.I)


class RsoScraper(HtmlVenueScraper):
    listing_url = LISTING_URL
    source_channel = "rso"
    venue = "RSO Wien"

    def parse(self, soup: BeautifulSoup) -> list[ViennaShow]:
        shows: list[ViennaShow] = []
        for item in soup.select("article[role='article']"):
            title = item.select_one("h3.title, h2, h3")
            name = title.get_text(" ", strip=True) if title else ""
            text = item.get_text(" ", strip=True)
            if SKIP_PLACE.search(text):
                continue
            stamp = item.select_one("time[datetime]")
            start, _utc_time = parse_iso_datetime(str(stamp.get("datetime") if stamp else ""))
            if start is None:
                start = parse_listing_date(text)
            start_time = parse_start_time(text)
            hall = ""
            place = item.select_one("p.text")
            if place:
                hall = place.get_text(" ", strip=True).split("  ")[0].strip()
                hall = re.sub(r"\d{1,2}:\d{2}.*", "", hall).strip()
            link = item.select_one("a.mehr, a[href*='/programm/']")
            show = self.make_show(
                name=name,
                url=(link.get("href") if link else "") or LISTING_URL,
                start=start,
                start_time=start_time or parse_start_time(text),
                venue=hall or self.venue,
            )
            if show:
                shows.append(show)
        return shows


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--dry", action="store_true")
    args = parser.parse_args()
    RsoScraper(dry=args.dry).scrape()
