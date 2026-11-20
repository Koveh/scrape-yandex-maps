"""Scrape MuTh Konzertsaal calendar into `concerts`."""
from __future__ import annotations

import argparse
import re

from bs4 import BeautifulSoup

from vienna_common import HtmlVenueScraper, ViennaShow, parse_iso_datetime, parse_listing_date, parse_start_time

LISTING_URL = "https://muth.at/kalender/"
SKIP_RE = re.compile(r"\b(abgesagt)\b", re.I)


class MuthScraper(HtmlVenueScraper):
    listing_url = LISTING_URL
    source_channel = "muth"
    venue = "MuTh"

    def parse(self, soup: BeautifulSoup) -> list[ViennaShow]:
        shows: list[ViennaShow] = []
        for link in soup.select("a.programm-link[href]"):
            href = link.get("href") or ""
            title = link.select_one(".programm-title")
            name = title.get_text(" ", strip=True) if title else ""
            subtitle = link.select_one(".programm-subtitle")
            if subtitle:
                extra = subtitle.get_text(" ", strip=True)
                if extra and extra.lower() not in name.lower():
                    name = f"{name} — {extra}".strip(" —")
            text = link.get_text(" ", strip=True)
            if not name or SKIP_RE.search(text):
                continue
            row = link.parent
            for _ in range(4):
                if row is None:
                    break
                if row.select_one(".programm-date_start_converted"):
                    break
                row = row.parent
            row_text = row.get_text(" ", strip=True) if row else text
            start, start_time = parse_iso_datetime(href)
            if start is None:
                start = parse_listing_date(row_text)
                start_time = parse_start_time(row_text)
            img = link.select_one("img[src]")
            show = self.make_show(
                name=name,
                url=href,
                start=start,
                start_time=start_time,
                image_src=img.get("src") if img else None,
            )
            if show:
                shows.append(show)
        return shows


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--dry", action="store_true")
    args = parser.parse_args()
    MuthScraper(dry=args.dry).scrape()
