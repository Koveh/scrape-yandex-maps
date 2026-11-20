"""Scrape Globe Wien into `concerts` (city = Вена)."""
from __future__ import annotations

import argparse
import re

from bs4 import BeautifulSoup

from vienna_common import HtmlVenueScraper, ViennaShow, parse_iso_datetime, parse_start_time

LISTING_URL = "https://www.globe.wien/programm-und-tickets"
SKIP_RE = re.compile(r"\b(abgesagt|workshop)\b", re.I)


class GlobeScraper(HtmlVenueScraper):
    listing_url = LISTING_URL
    source_channel = "globe"
    venue = "Globe Wien"

    def parse(self, soup: BeautifulSoup) -> list[ViennaShow]:
        shows: list[ViennaShow] = []
        for item in soup.select("li.item[data-attr-date]"):
            artist = item.select_one(".termine-artist")
            title = item.select_one(".termine-title")
            name = " · ".join(
                part
                for part in [
                    artist.get_text(" ", strip=True) if artist else "",
                    title.get_text(" ", strip=True) if title else "",
                ]
                if part
            )
            text = item.get_text(" ", strip=True)
            if SKIP_RE.search(text) or not name:
                continue
            link = item.select_one('a[href*="/programm/"]')
            href = (link.get("href") if link else "") or LISTING_URL
            start, _ = parse_iso_datetime(item.get("data-attr-date") or "")
            img = item.select_one("img[src]")
            show = self.make_show(
                name=name,
                url=href.split("#")[0],
                start=start,
                start_time=parse_start_time(text),
                image_src=img.get("src") if img else None,
            )
            if show:
                shows.append(show)
        return shows


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--dry", action="store_true")
    args = parser.parse_args()
    GlobeScraper(dry=args.dry).scrape()
