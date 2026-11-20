"""Scrape Flucc Vienna listings into `concerts` (city = Вена)."""
from __future__ import annotations

import argparse
import re

from bs4 import BeautifulSoup

from vienna_common import HtmlVenueScraper, ViennaShow, parse_listing_date, parse_start_time

LISTING_URL = "https://flucc.at/"
SKIP_RE = re.compile(r"geschl\.?\s*veranstaltung|ausverkauft|abgesagt", re.I)
DATE_RE = re.compile(r"(?:Mo|Di|Mi|Do|Fr|Sa|So),?\s+\d{1,2}\.\d{1,2}\.\d{2,4}", re.I)


class FluccScraper(HtmlVenueScraper):
    listing_url = LISTING_URL
    source_channel = "flucc"
    venue = "Flucc"

    def hall_name(self, heading: str) -> str:
        if re.search(r"\bwanne\b", heading, re.I):
            return "Flucc Wanne"
        if re.search(r"\bdeck\b", heading, re.I):
            return "Flucc Deck"
        if re.search(r"\bwien\b", heading, re.I):
            return "Flucc Wien"
        return self.venue

    def parse(self, soup: BeautifulSoup) -> list[ViennaShow]:
        shows: list[ViennaShow] = []
        seen: set[str] = set()
        for card in soup.select("li.himmel-card"):
            title = card.select_one("h4, .title-dimension h4, .ticker h4")
            name = title.get_text(" ", strip=True) if title else ""
            if not name or SKIP_RE.search(card.get_text(" ", strip=True)):
                continue
            link = card.select_one("a[href]")
            loc = card.select_one(".location, .time-location-info")
            loc_text = loc.get_text(" ", strip=True) if loc else ""
            prev = str(card.find_previous(string=DATE_RE) or "")
            img = card.select_one("img[src]")
            show = self.make_show(
                name=name,
                url=(link.get("href") if link else "") or LISTING_URL,
                start=parse_listing_date(prev),
                start_time=parse_start_time(loc_text or prev),
                venue=self.hall_name(f"{prev} {loc_text}"),
                image_src=img.get("src") if img else None,
            )
            if show is None:
                continue
            key = f"{show.start}:{show.name.lower()}"
            if key in seen:
                continue
            seen.add(key)
            shows.append(show)
        return shows


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--dry", action="store_true")
    args = parser.parse_args()
    FluccScraper(dry=args.dry).scrape()
