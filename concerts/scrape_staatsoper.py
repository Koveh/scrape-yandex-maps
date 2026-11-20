"""Scrape Wiener Staatsoper monthly calendar into `concerts`."""
from __future__ import annotations

import argparse
import re

from bs4 import BeautifulSoup

from vienna_common import HtmlVenueScraper, ViennaShow, logged, parse_iso_datetime, parse_start_time

SKIP_RE = re.compile(r"\b(abgesagt|geschlossen|keine vorstellung)\b", re.I)
MONTHS = (
    "januar",
    "februar",
    "maerz",
    "april",
    "mai",
    "juni",
    "juli",
    "august",
    "september",
    "oktober",
    "november",
    "dezember",
)


class StaatsoperScraper(HtmlVenueScraper):
    listing_url = "https://www.wiener-staatsoper.at/kalender/"
    source_channel = "staatsoper"
    venue = "Wiener Staatsoper"

    def parse(self, soup) -> list[ViennaShow]:
        shows: list[ViennaShow] = []
        for link in soup.select('a[href*="/kalender/detail/"]'):
            href = link.get("href") or ""
            title = link.select_one(".event-title, h2")
            name = title.get_text(" ", strip=True) if title else link.get_text(" ", strip=True)
            if not name or SKIP_RE.search(name):
                continue
            start, _ = parse_iso_datetime(href)
            block = link.parent
            for _ in range(5):
                if block is None:
                    break
                if block.select_one(".event-room, .event-genre"):
                    break
                block = block.parent
            text = block.get_text(" ", strip=True) if block else name
            hall = ""
            room = block.select_one(".event-room") if block else None
            if room:
                hall = room.get_text(" ", strip=True)
            lead = block.select_one(".event-lead") if block else None
            if lead:
                composer = lead.get_text(" ", strip=True)
                if composer and composer.lower() not in name.lower():
                    name = f"{name} — {composer}"
            show = self.make_show(
                name=name,
                url=href,
                start=start,
                start_time=parse_start_time(text),
                venue=hall or self.venue,
            )
            if show:
                shows.append(show)
        return shows

    @logged
    def scrape(self) -> None:
        from datetime import date

        today = date.today()
        shows: list[ViennaShow] = []
        seen: set[str] = set()
        for offset in range(0, 8):
            month = today.month + offset
            year = today.year + (month - 1) // 12
            month = (month - 1) % 12 + 1
            slug = MONTHS[month - 1]
            url = f"https://www.wiener-staatsoper.at/kalender/{year}/{slug}/"
            response = self.store.session.get(url, timeout=90)
            if response.status_code == 404:
                print(f"  {year}-{month:02d} skip 404", flush=True)
                continue
            response.raise_for_status()
            soup = BeautifulSoup(response.content.decode("utf-8", errors="replace"), "html.parser")
            page_shows = self.parse(soup)
            print(f"  {year}-{month:02d} cards={len(page_shows)}", flush=True)
            for show in page_shows:
                key = f"{show.url}|{show.start}"
                if key in seen:
                    continue
                seen.add(key)
                shows.append(show)
        print(f"cards={len(shows)}", flush=True)
        self.store.persist(shows)


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--dry", action="store_true")
    args = parser.parse_args()
    StaatsoperScraper(dry=args.dry).scrape()
