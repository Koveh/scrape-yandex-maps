"""Scrape Residenztheater München spielplan into `concerts`."""
from __future__ import annotations

import argparse
import re

from bs4 import BeautifulSoup

from vienna_common import HtmlVenueScraper, MUNICH_CITY, ViennaShow, parse_listing_date, parse_start_time

LISTING_URL = "https://www.residenztheater.de/spielplan"
SKIP_RE = re.compile(r"abgesagt|keine vorstellung", re.I)


class ResidenztheaterScraper(HtmlVenueScraper):
    city = MUNICH_CITY
    listing_url = LISTING_URL
    source_channel = "residenztheater"
    venue = "Residenztheater"

    def parse(self, soup: BeautifulSoup) -> list[ViennaShow]:
        shows: list[ViennaShow] = []
        for item in soup.select("article.schedule-act"):
            if "schedule-act--inactive" in (item.get("class") or []):
                continue
            title = item.select_one(".schedule-act__title a, h3 a")
            name = title.get_text(" ", strip=True) if title else ""
            name = re.sub(r"\s+-\s+\d+\s+\w+\s*$", "", name).strip()
            text = item.get_text(" ", strip=True)
            if not name or SKIP_RE.search(name) or SKIP_RE.search(text):
                continue
            hall = item.select_one(".schedule-act__location, .schedule-act__venue")
            show = self.make_show(
                name=name,
                url=(title.get("href") if title else "") or LISTING_URL,
                start=parse_listing_date(text),
                start_time=parse_start_time(text),
                venue=(hall.get_text(" ", strip=True) if hall else "") or self.venue,
            )
            if show:
                shows.append(show)
        return shows


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--dry", action="store_true")
    args = parser.parse_args()
    ResidenztheaterScraper(dry=args.dry).scrape()
