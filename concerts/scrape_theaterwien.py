"""Scrape Theater an der Wien into `concerts` (city = Вена)."""
from __future__ import annotations

import argparse
import re

from bs4 import BeautifulSoup

from vienna_common import HtmlVenueScraper, ViennaShow, parse_listing_date

LISTING_URL = "https://www.theater-wien.at/de/spielplan"
SKIP_RE = re.compile(r"(backstageführung|führung|abgesagt)", re.I)


class TheaterWienScraper(HtmlVenueScraper):
    listing_url = LISTING_URL
    source_channel = "theaterwien"
    venue = "Theater an der Wien"

    def parse(self, soup: BeautifulSoup) -> list[ViennaShow]:
        shows: list[ViennaShow] = []
        for item in soup.select("li.box"):
            link = item.select_one("a[href][title]")
            name = (link.get("title") if link else "") or (
                item.select_one(".eventc_title").get_text(" ", strip=True)
                if item.select_one(".eventc_title")
                else ""
            )
            text = item.get_text(" ", strip=True)
            if SKIP_RE.search(name) or SKIP_RE.search(text) or not name:
                continue
            dates = re.findall(r"(\d{1,2}\.\d{1,2}\.20\d{2})", text)
            start = parse_listing_date(dates[0]) if dates else parse_listing_date(text)
            img = item.select_one("img[src]")
            show = self.make_show(
                name=name,
                url=(link.get("href") if link else "") or LISTING_URL,
                start=start,
                image_src=img.get("src") if img else None,
                description=text[:300],
            )
            if show:
                shows.append(show)
        return shows


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--dry", action="store_true")
    args = parser.parse_args()
    TheaterWienScraper(dry=args.dry).scrape()
