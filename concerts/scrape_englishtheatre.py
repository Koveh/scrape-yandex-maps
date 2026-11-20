"""Scrape Vienna's English Theatre season into `concerts`."""
from __future__ import annotations

import argparse
import re

from bs4 import BeautifulSoup

from vienna_common import HtmlVenueScraper, ViennaShow, logged, parse_listing_date, parse_start_time

LISTING_URL = "https://www.englishtheatre.at/english/season-26/27"
SKIP_RE = re.compile(r"\b(abgesagt|cancelled)\b", re.I)


class EnglishTheatreScraper(HtmlVenueScraper):
    listing_url = LISTING_URL
    source_channel = "englishtheatre"
    venue = "Vienna's English Theatre"

    def parse(self, soup: BeautifulSoup) -> list[ViennaShow]:
        shows: list[ViennaShow] = []
        for link in soup.select("a[href*='/english/season-26/27/']"):
            href = link.get("href") or ""
            if href.rstrip("/").endswith("season-26/27"):
                continue
            name = link.get_text(" ", strip=True)
            if name.lower() in {"more info", "tickets", "info", "mehr"}:
                name = href.rstrip("/").split("/")[-1].replace("-", " ").title()
            text = link.get_text(" ", strip=True)
            parent = link.parent
            for _ in range(4):
                if parent is None:
                    break
                parent = parent.parent
            block = parent.get_text(" ", strip=True) if parent else text
            if not name or SKIP_RE.search(block):
                continue
            show = self.make_show(
                name=name,
                url=href,
                start=parse_listing_date(block) or parse_listing_date(text),
                start_time=parse_start_time(block) or parse_start_time("19:30"),
            )
            if show:
                shows.append(show)
        return shows

    @logged
    def scrape(self) -> None:
        soup = self.fetch_soup()
        shows = self.parse(soup)
        # Season page lists date ranges in body copy — also pull play pages for a start date.
        if not shows:
            text = soup.get_text(" ", strip=True)
            for href in {
                a.get("href")
                for a in soup.select("a[href*='/english/season-26/27/']")
                if a.get("href") and not a.get("href").rstrip("/").endswith("season-26/27")
            }:
                name = href.rstrip("/").split("/")[-1].replace("-", " ").title()
                show = self.make_show(
                    name=name,
                    url=href,
                    start=parse_listing_date(text),
                    start_time=parse_start_time("19:30"),
                )
                if show:
                    shows.append(show)
        self.persist_shows(shows)


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--dry", action="store_true")
    args = parser.parse_args()
    EnglishTheatreScraper(dry=args.dry).scrape()
