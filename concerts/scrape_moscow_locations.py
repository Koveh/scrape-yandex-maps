"""Seed Moscow venues: leftover official playbills not covered by dedicated scrapers.

Dedicated scrapers (prefer these):
- StandUp Store, Malaya Bronnaya, Mossovet, MDM, 16 Tons, Zaryadye
- Vakhtangov, Meloman (philharmonic / Tchaikovsky), Luzhniki, Pushkin
- Lenkom + Satire via scrape_bitrix_afisha.py
- Afisha schedule + Afisha clubs + Afisha theatres (Taganka, Sovremennik,
  MXAT/MXT, Helikon, Dom Muzyki, …)

This seed list keeps Helikon / MXAT / Sovremennik homepage probes for future
HTML that gains stable dates. Official Glavclub / Stereo Hall / Red Club /
Mumiy Troll / Izvestia Hall are DNS-blocked from Hetzner — rely on Afisha
when those places reappear in /msk/club/.
"""
from __future__ import annotations

import argparse
import re
from datetime import datetime

from bs4 import BeautifulSoup

from moscow_common import MOSCOW_CITY, parse_ru_date, parse_ru_time
from vienna_common import HtmlVenueScraper, ViennaShow, absolute_url, listing_image_src

# (source_channel, listing_url, venue_label, css_item, name_sel, link_sel)
LOCATIONS = (
    (
        "mxat",
        "https://mxat.ru/afisha/",
        "МХАТ",
        ".afisha__item, .event, article, a[href*='/performance'], a[href*='/afisha']",
        None,
        None,
    ),
    (
        "helikon",
        "https://www.helikon.ru/",
        "Геликон-опера",
        "a[href*='/performances/'], .afisha-item, .event, article",
        None,
        None,
    ),
    (
        "sovremennik",
        "https://www.sovremennik.ru/",
        "Современник",
        "a[href*='/plays/'], .afisha-item, .event, article",
        None,
        None,
    ),
)


class MoscowLocationScraper(HtmlVenueScraper):
    city = MOSCOW_CITY

    def __init__(self, source: str, url: str, venue: str, item_sel: str, dry: bool = False) -> None:
        self.source_channel = source
        self.listing_url = url
        self.venue = venue
        self.item_sel = item_sel
        super().__init__(dry=dry)

    def parse(self, soup: BeautifulSoup) -> list[ViennaShow]:
        shows: list[ViennaShow] = []
        seen: set[str] = set()
        for item in soup.select(self.item_sel):
            link = item if item.name == "a" else item.select_one("a[href]")
            href = (link.get("href") if link else "") or ""
            if not href or href.startswith("#") or href.startswith("mailto:"):
                continue
            href = absolute_url(self.listing_url, href)
            text = item.get_text(" ", strip=True)
            name = re.sub(r"\s+", " ", (link.get_text(" ", strip=True) if link else text)).strip()
            if len(name) < 3 or len(name) > 180:
                continue
            start = parse_ru_date(text)
            if start is None:
                iso = re.search(r"(20\d{2})-(\d{2})-(\d{2})", href + " " + text)
                if iso:
                    try:
                        start = datetime.strptime(iso.group(0)[:10], "%Y-%m-%d").date()
                    except ValueError:
                        start = None
            if start is None:
                continue
            key = f"{href}|{start}|{name.lower()}"
            if key in seen:
                continue
            seen.add(key)
            image_src = listing_image_src(item)
            if not image_src:
                img = item.select_one("img[data-src], img[src]")
                if img:
                    image_src = img.get("data-src") or img.get("src")
            show = self.make_show(
                name=name,
                url=href,
                start=start,
                start_time=parse_ru_time(text),
                venue=self.venue,
                image_src=image_src,
                description=text[:500],
            )
            if show:
                shows.append(show)
        return shows


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--dry", action="store_true")
    args = parser.parse_args()
    for source, url, venue, item_sel, _name_sel, _link_sel in LOCATIONS:
        MoscowLocationScraper(source, url, venue, item_sel, dry=args.dry).scrape()
