"""Scrape Substanz Munich club nights into `concerts`."""
from __future__ import annotations

import argparse
import re

from bs4 import BeautifulSoup

from vienna_common import HtmlVenueScraper, MUNICH_CITY, ViennaShow, parse_listing_date, parse_start_time

LISTING_URL = "https://substanz-club.com/alle-events"
DATE_RE = re.compile(
    r"(Montag|Dienstag|Mittwoch|Donnerstag|Freitag|Samstag|Sonntag),?\s+(\d{1,2})[.,](\d{1,2})\.(20\d{2})",
    re.I,
)
SKIP_RE = re.compile(r"sommerpause|geschlossen", re.I)


class SubstanzScraper(HtmlVenueScraper):
    city = MUNICH_CITY
    listing_url = LISTING_URL
    source_channel = "substanz"
    venue = "Substanz"

    def parse(self, soup: BeautifulSoup) -> list[ViennaShow]:
        shows: list[ViennaShow] = []
        text = soup.get_text("\n", strip=True)
        lines = [line.strip() for line in text.splitlines() if line.strip()]
        current_date = None
        for index, line in enumerate(lines):
            dated = DATE_RE.search(line)
            if dated:
                current_date = parse_listing_date(line)
                continue
            if current_date is None or SKIP_RE.search(line) or len(line) < 4:
                continue
            if line.isupper() and len(line) < 8:
                continue
            if re.fullmatch(r"(tickets?|tisch reservieren|team anmelden|platz reservieren)", line, re.I):
                continue
            if DATE_RE.search(line):
                continue
            name = re.sub(r"\s+", " ", line)
            if name != name.upper() and not re.search(r"[A-Za-zÄÖÜäöüß]", name):
                continue
            # Title sits on the line after the weekday date; skip host/einlass blurbs.
            if re.search(r"^(host|einlass|beginn|eintritt|mit dj|der substanzielle)", name, re.I):
                continue
            extra = " ".join(lines[index : index + 4])
            slug = re.sub(r"[^a-z0-9]+", "-", name.lower())[:60].strip("-")
            show = self.make_show(
                name=name[:180],
                url=f"{LISTING_URL}#{current_date.isoformat()}-{slug}",
                start=current_date,
                start_time=parse_start_time(extra),
                description=extra[:400],
            )
            if show:
                shows.append(show)
            current_date = None
        return shows


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--dry", action="store_true")
    args = parser.parse_args()
    SubstanzScraper(dry=args.dry).scrape()
