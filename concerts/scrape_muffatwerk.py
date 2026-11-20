"""Scrape Muffatwerk Munich listings into `concerts` (city = Мюнхен)."""
from __future__ import annotations

import argparse
import re

from bs4 import BeautifulSoup

from vienna_common import (
    HtmlVenueScraper,
    MUNICH_CITY,
    ViennaShow,
    listing_image_src,
    parse_listing_date,
    parse_start_time,
)

LISTING_URL = "https://www.muffatwerk.de/de/events"
SKIP_RE = re.compile(r"biergarten|heute geöffnet", re.I)


class MuffatwerkScraper(HtmlVenueScraper):
    city = MUNICH_CITY
    listing_url = LISTING_URL
    source_channel = "muffatwerk"
    venue = "Muffatwerk"

    def hall_name(self, text: str) -> str:
        if re.search(r"muffathalle", text, re.I):
            return "Muffathalle"
        if re.search(r"ampere", text, re.I):
            return "Ampere"
        if re.search(r"muffatcafé|muffatcafe", text, re.I):
            return "Muffatcafé"
        return self.venue

    def parse(self, soup: BeautifulSoup) -> list[ViennaShow]:
        shows: list[ViennaShow] = []
        seen: set[str] = set()
        for item in soup.select(".event"):
            text = re.sub(r"\s+", " ", item.get_text(" ", strip=True))
            if SKIP_RE.search(text) and not re.search(r"konzert|live", text, re.I):
                continue
            href = ""
            link = item.select_one('a[href*="/events/view/"]')
            if link:
                href = link.get("href") or ""
            if not href:
                go = re.search(r"go\(['\"](/de/events/view/\d+/[^'\"]+)['\"]\)", str(item))
                href = go.group(1) if go else ""
            if not href:
                continue
            center = item.select_one(".entry-data.center")
            bits = [part.strip() for part in (center.get_text("\n", strip=True) if center else "").split("\n") if part.strip()]
            skip_names = {"ausverkauft", "tickets", "info", "mehr", "heute geöffnet", "heute"}
            name = next((part for part in reversed(bits) if part.lower() not in skip_names), "")
            if not name or name.lower() in skip_names:
                name = href.rstrip("/").split("/")[-1].replace("-", " ").strip()
            img = item.select_one("img")
            show = self.make_show(
                name=name,
                url=href or LISTING_URL,
                start=parse_listing_date(text),
                start_time=parse_start_time(text),
                venue=self.hall_name(text),
                image_src=listing_image_src(item) or (img.get("src") if img else None),
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
    MuffatwerkScraper(dry=args.dry).scrape()
