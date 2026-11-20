"""Scrape Bahnwärter Thiel Munich listings into `concerts` (city = Мюнхен)."""
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

LISTING_URL = "https://bahnwaerterthiel.de/"


class BahnwaerterScraper(HtmlVenueScraper):
    city = MUNICH_CITY
    listing_url = LISTING_URL
    source_channel = "bahnwaerter"
    venue = "Bahnwärter Thiel"

    def parse(self, soup: BeautifulSoup) -> list[ViennaShow]:
        shows: list[ViennaShow] = []
        seen: set[str] = set()
        for wrap in soup.select(".bmt-wrap, .bmt-collapsible"):
            text = re.sub(r"\s+", " ", wrap.get_text(" ", strip=True))
            if re.search(r"vorverkauf", text, re.I) and len(text) < 40:
                continue
            name_match = re.search(
                r"\d{1,2}\.\d{1,2}\.\d{2,4}.{0,40}?(?:Uhr\s+)?(.+)$",
                text,
            )
            name = (name_match.group(1) if name_match else text)[:120].strip()
            name = re.sub(r"^(Einlass:\s*\d{1,2}:\d{2}\s*/\s*)?", "", name)
            if name.lower() in {"vorverkauf", "tickets"}:
                continue
            link = wrap.select_one("a[href]")
            href = (link.get("href") if link else "") or LISTING_URL
            show = self.make_show(
                name=name,
                url=href,
                start=parse_listing_date(text),
                start_time=parse_start_time(text),
            )
            if show is None:
                continue
            key = f"{show.start}:{show.name.lower()}"
            if key in seen:
                continue
            seen.add(key)
            shows.append(show)
        return shows


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--dry", action="store_true")
    args = parser.parse_args()
    BahnwaerterScraper(dry=args.dry).scrape()
