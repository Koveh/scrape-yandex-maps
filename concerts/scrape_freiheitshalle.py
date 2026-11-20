"""Scrape Freiheitshalle Munich party nights into `concerts`."""
from __future__ import annotations

import argparse
import re
from datetime import date

from bs4 import BeautifulSoup

from vienna_common import HtmlVenueScraper, MUNICH_CITY, ViennaShow, parse_listing_date, parse_start_time

LISTING_URL = "https://www.freiheitshalle-munich.com/events-1"
URL_DATE = re.compile(r"(20\d{2})-(\d{2})-(\d{2})")
CLEAN_RE = re.compile(r"[🎁❤★❗🪩].*$")


class FreiheitshalleScraper(HtmlVenueScraper):
    city = MUNICH_CITY
    listing_url = LISTING_URL
    source_channel = "freiheitshalle"
    venue = "Freiheitshalle"

    def start_from(self, href: str, text: str) -> date | None:
        match = URL_DATE.search(href or "")
        if match:
            return date(int(match.group(1)), int(match.group(2)), int(match.group(3)))
        return parse_listing_date(f"{text} {href}")

    def clean_name(self, raw: str) -> str:
        name = re.sub(r"^[★❤🎁❗🪩\s]+", "", raw or "")
        name = re.split(r"\s+I\s+Freiheitshalle", name, maxsplit=1)[0]
        name = re.sub(r"[🎁❤★❗🪩].*", "", name)
        return re.sub(r"\s+", " ", name).strip(" -|")

    def parse(self, soup: BeautifulSoup) -> list[ViennaShow]:
        shows: list[ViennaShow] = []
        seen: set[str] = set()
        for link in soup.select("a[href*='/events/']"):
            href = link.get("href") or ""
            if href in seen or href.rstrip("/").endswith("/events-1"):
                continue
            seen.add(href)
            text = link.get_text(" ", strip=True)
            name = self.clean_name(text)
            start_time = parse_start_time(text)
            tail = re.search(r"(\d{2})-(\d{2})$", href.split("?")[0])
            if start_time is None and tail:
                start_time = parse_start_time(f"{tail.group(1)}:{tail.group(2)}")
            show = self.make_show(
                name=name,
                url=href,
                start=self.start_from(href, text),
                start_time=start_time,
            )
            if show:
                shows.append(show)
        return shows


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--dry", action="store_true")
    args = parser.parse_args()
    FreiheitshalleScraper(dry=args.dry).scrape()
