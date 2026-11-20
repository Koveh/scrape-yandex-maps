"""Scrape Escape Metalcorner listings into `concerts`."""
from __future__ import annotations

import argparse
import re
from datetime import date

from bs4 import BeautifulSoup

from vienna_common import HtmlVenueScraper, ViennaShow, parse_start_time

LISTING_URL = "https://www.escape-metalcorner.at/de/events"
SKIP_RE = re.compile(r"\b(abgesagt|cancelled)\b", re.I)
DATE_IN_HREF = re.compile(r"/(\d{4})_(\d{2})_(\d{2})-")


class EscapeScraper(HtmlVenueScraper):
    listing_url = LISTING_URL
    source_channel = "escape"
    venue = "Escape Metalcorner"

    def parse(self, soup: BeautifulSoup) -> list[ViennaShow]:
        shows: list[ViennaShow] = []
        seen: set[str] = set()
        for item in soup.select(".event"):
            link = item.select_one("a[href]")
            href = (link.get("href") if link else "") or ""
            name_el = item.select_one(".name")
            head_el = item.select_one(".head")
            name = (name_el.get_text(" ", strip=True) if name_el else "")
            kind = (head_el.get_text(" ", strip=True) if head_el else "")
            if kind and name and kind.lower() not in name.lower():
                name = f"{kind}: {name}"
            if not name or SKIP_RE.search(item.get_text(" ", strip=True)):
                continue
            dated = DATE_IN_HREF.search(href)
            start = date(int(dated.group(1)), int(dated.group(2)), int(dated.group(3))) if dated else None
            if href.startswith("./"):
                href = href[2:]
            if href.startswith("de/"):
                href = "/" + href
            img = item.select_one("img[src]")
            show = self.make_show(
                name=name,
                url=href or LISTING_URL,
                start=start,
                start_time=parse_start_time(item.get_text(" ", strip=True)),
                image_src=img.get("src") if img else None,
            )
            if show is None or show.url in seen:
                continue
            seen.add(show.url)
            shows.append(show)
        return shows


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--dry", action="store_true")
    args = parser.parse_args()
    EscapeScraper(dry=args.dry).scrape()
