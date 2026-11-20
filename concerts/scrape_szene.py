"""Scrape Szene Wien calendar into `concerts`."""
from __future__ import annotations

import argparse
import re

from bs4 import BeautifulSoup

from vienna_common import HtmlVenueScraper, ViennaShow, parse_listing_date, parse_start_time

LISTING_URL = "https://szene.wien/"
SKIP_RE = re.compile(r"soundgarden|facebook|anmeldeformular|newsletter|events$", re.I)


class SzeneScraper(HtmlVenueScraper):
    listing_url = LISTING_URL
    source_channel = "szene"
    venue = "Szene Wien"

    def parse(self, soup: BeautifulSoup) -> list[ViennaShow]:
        shows: list[ViennaShow] = []
        for heading in soup.select("h2, h3"):
            name = heading.get_text(" ", strip=True)
            name = re.sub(r"[\(\)]+", " ", name)
            name = re.sub(r"\s+", " ", name).strip(" |")
            if not name or SKIP_RE.search(name) or len(name) < 6:
                continue
            block = heading.parent
            text = block.get_text(" ", strip=True) if block else name
            start = parse_listing_date(text)
            if start is None:
                continue
            slug = re.sub(r"[^a-z0-9]+", "-", name.lower())[:60].strip("-")
            link = f"{LISTING_URL}#{start.isoformat()}-{slug}"
            if block:
                for anchor in block.select("a[href]"):
                    href = anchor.get("href") or ""
                    if href.startswith("http") and "facebook" not in href and "instagram" not in href and "szene.wien" not in href:
                        link = href
                        break
            img = block.select_one("img[src]") if block else None
            show = self.make_show(
                name=name,
                url=link or LISTING_URL,
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
    SzeneScraper(dry=args.dry).scrape()
