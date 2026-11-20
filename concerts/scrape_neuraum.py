"""Scrape neuraum Munich club nights into `concerts`."""
from __future__ import annotations

import argparse
import re

from bs4 import BeautifulSoup

from vienna_common import HtmlVenueScraper, MUNICH_CITY, ViennaShow, parse_listing_date, parse_start_time

LISTING_URL = "https://neuraum.de/"
DATE_RE = re.compile(
    r"(Montag|Dienstag|Mittwoch|Donnerstag|Freitag|Samstag|Sonntag),?\s+(\d{1,2})\.(\d{1,2})\.(20\d{2})",
    re.I,
)
SKIP_RE = re.compile(r"abendkasse|reservierung|^infos$|^tickets$", re.I)


class NeuraumScraper(HtmlVenueScraper):
    city = MUNICH_CITY
    listing_url = LISTING_URL
    source_channel = "neuraum"
    venue = "neuraum"

    def parse(self, soup: BeautifulSoup) -> list[ViennaShow]:
        shows: list[ViennaShow] = []
        lines = [line.strip() for line in soup.get_text("\n", strip=True).splitlines() if line.strip()]
        current = None
        for index, line in enumerate(lines):
            dated = DATE_RE.search(line)
            if dated:
                current = parse_listing_date(line)
                continue
            if current is None or SKIP_RE.search(line) or len(line) < 6:
                continue
            name = re.sub(r"\s+", " ", line)
            extra = " ".join(lines[index : index + 3])
            slug = re.sub(r"[^a-z0-9]+", "-", name.lower())[:60].strip("-")
            show = self.make_show(
                name=name[:180],
                url=f"{LISTING_URL}#{current.isoformat()}-{slug}",
                start=current,
                start_time=parse_start_time(extra),
                description=extra[:400],
            )
            if show:
                shows.append(show)
            current = None
        return shows


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--dry", action="store_true")
    args = parser.parse_args()
    NeuraumScraper(dry=args.dry).scrape()
