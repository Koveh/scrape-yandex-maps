"""Scrape Rabenhof Theater into `concerts` (city = Вена)."""
from __future__ import annotations

import argparse
import re

from bs4 import BeautifulSoup

from vienna_common import HtmlVenueScraper, ViennaShow, parse_listing_date

LISTING_URL = "https://www.rabenhoftheater.com/"
SKIP_RE = re.compile(r"\b(abgesagt)\b", re.I)


class RabenhofScraper(HtmlVenueScraper):
    listing_url = LISTING_URL
    source_channel = "rabenhof"
    venue = "Rabenhof Theater"

    def parse(self, soup: BeautifulSoup) -> list[ViennaShow]:
        shows: list[ViennaShow] = []
        seen: set[str] = set()
        for link in soup.select('a[href*="/programm/"]'):
            href = (link.get("href") or "").strip()
            text = re.sub(r"\s+", " ", link.get_text(" ", strip=True))
            if not href or not text or SKIP_RE.search(text):
                continue
            start = parse_listing_date(text)
            name = re.split(r"\bPremiere:", text, maxsplit=1)[0].strip(" -–·")
            if not name:
                continue
            show = self.make_show(name=name, url=href, start=start, description=text[:300])
            if show is None or show.url in seen:
                continue
            seen.add(show.url)
            shows.append(show)
        return shows


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--dry", action="store_true")
    args = parser.parse_args()
    RabenhofScraper(dry=args.dry).scrape()
