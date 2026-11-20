"""Scrape Volksoper Wien spielplan into `concerts`."""
from __future__ import annotations

import argparse
import re
from urllib.parse import urljoin

from bs4 import BeautifulSoup

from vienna_common import (
    HtmlVenueScraper,
    ViennaShow,
    listing_image_src,
    parse_iso_datetime,
    parse_listing_date,
    parse_start_time,
)

LISTING_URL = "https://www.volksoper.at/spielplan/saison-2026-2027.de.html"
SKIP_RE = re.compile(r"keine vorstellung|abgesagt|geschlossen", re.I)


class VolksoperScraper(HtmlVenueScraper):
    listing_url = LISTING_URL
    source_channel = "volksoper"
    venue = "Volksoper"

    def __init__(self, dry: bool = False) -> None:
        super().__init__(dry=dry)
        self.produktion_posters: dict[str, str | None] = {}

    def parse(self, soup: BeautifulSoup) -> list[ViennaShow]:
        shows: list[ViennaShow] = []
        for item in soup.select("article.event"):
            name_el = item.select_one("h2.event-title, h2[itemprop='name']")
            name = name_el.get_text(" ", strip=True) if name_el else ""
            text = item.get_text(" ", strip=True)
            if not name or SKIP_RE.search(name) or SKIP_RE.search(text):
                continue
            stamp = item.select_one("time[datetime]")
            start, start_time = parse_iso_datetime(stamp.get("datetime") if stamp else "")
            if start is None:
                start = parse_listing_date(text)
                start_time = parse_start_time(text)
            tickets = item.select_one("a[href*='tickets.']")
            spielplan = item.select_one("a[href*='/spielplan/']")
            produktion = item.select_one("a[href*='/produktion/']")
            url = (
                (tickets.get("href") if tickets else "")
                or (spielplan.get("href") if spielplan else "")
                or LISTING_URL
            )
            hall = item.select_one(".event-location")
            image_src = listing_image_src(item)
            if not image_src and produktion:
                image_src = self.produktion_poster(produktion.get("href") or "")
            show = self.make_show(
                name=name,
                url=url,
                start=start,
                start_time=start_time or parse_start_time(text),
                venue=(hall.get_text(" ", strip=True) if hall else "") or self.venue,
                image_src=image_src,
            )
            if show:
                shows.append(show)
        return shows

    def produktion_poster(self, href: str) -> str | None:
        if not href:
            return None
        url = urljoin(LISTING_URL, href)
        if url not in self.produktion_posters:
            self.produktion_posters[url] = self.store.page_image(url)
        return self.produktion_posters[url]


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--dry", action="store_true")
    args = parser.parse_args()
    VolksoperScraper(dry=args.dry).scrape()
