"""Scrape Das Werk industrial nights into `concerts` (city = Вена)."""
from __future__ import annotations

import argparse
import re

from bs4 import BeautifulSoup

from vienna_common import HtmlVenueScraper, ViennaShow, parse_listing_date, parse_start_time

DATE_RE = re.compile(r"(Mo|Di|Mi|Do|Fr|Sa|So)\.?\s+\d{1,2}\.\d{1,2}\.", re.I)
SKIP_RE = re.compile(r"\b(abgesagt|cancelled)\b", re.I)


class DasWerkScraper(HtmlVenueScraper):
    listing_url = "https://www.daswerk.org/program"
    source_channel = "daswerk"
    venue = "Das Werk"

    def parse(self, soup: BeautifulSoup) -> list[ViennaShow]:
        shows: list[ViennaShow] = []
        seen: set[str] = set()
        for date_p in soup.find_all("p"):
            date_text = date_p.get_text(" ", strip=True)
            if not DATE_RE.search(date_text):
                continue
            card = date_p.parent
            if card is None:
                continue
            title_p = date_p.find_next_sibling("p")
            name = title_p.get_text(" ", strip=True) if title_p else ""
            if not name or SKIP_RE.search(name):
                continue
            blob = f"{date_text} {card.get_text(' ', strip=True)}"
            link = None
            for anchor in card.select("a[href]"):
                href = str(anchor.get("href") or "")
                if href.startswith("http") or href.startswith("/"):
                    link = href
                    break
            img = card.select_one("img[src]")
            show = self.make_show(
                name=name,
                url=link or self.listing_url,
                start=parse_listing_date(date_text),
                start_time=parse_start_time(blob),
                image_src=img.get("src") if img else None,
                description=date_text,
            )
            if show is None:
                continue
            key = f"{show.start}|{show.start_time}|{show.name.lower()}"
            if key in seen:
                continue
            seen.add(key)
            shows.append(show)
        return shows


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--dry", action="store_true")
    args = parser.parse_args()
    DasWerkScraper(dry=args.dry).scrape()
