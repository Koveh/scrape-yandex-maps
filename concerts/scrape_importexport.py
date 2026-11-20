"""Scrape Import Export München programm into `concerts` (city = Мюнхен)."""
from __future__ import annotations

import argparse
from datetime import date, timedelta

from bs4 import BeautifulSoup
from bs4.element import Tag

from munich_common import MunichStore
from vienna_common import (
    ViennaShow,
    logged,
    parse_listing_date,
    parse_start_time,
    stable_id,
    strip_html,
)

LISTING_URL = "https://import-export.cc/programm/"
SOURCE_CHANNEL = "importexport"
VENUE = "Import Export"


class ImportExportScraper:
    def __init__(self, dry: bool = False) -> None:
        self.store = MunichStore(SOURCE_CHANNEL, dry=dry)

    def parse_item(self, item: Tag) -> ViennaShow | None:
        parent = item.parent
        href = parent.get("href") if parent is not None and parent.name == "a" else None
        if not href:
            return None
        name_el = item.select_one(".io-title")
        name = strip_html(name_el.get_text(" ", strip=True) if name_el else "")
        if not name:
            return None
        day_el = item.select_one(".io-big")
        start = parse_listing_date(
            day_el.get_text(" ", strip=True) if day_el else "",
            bump_past=False,
        )
        if start is not None and start < date.today():
            return None
        info = item.select_one(".event-infos")
        info_text = strip_html(info.get_text(" ", strip=True) if info else "")
        return ViennaShow(
            description=info_text[:500],
            name=name,
            source_channel=SOURCE_CHANNEL,
            source_message_id=stable_id(href, start, parse_start_time(info_text)),
            start=start,
            start_time=parse_start_time(info_text),
            url=href,
            venue=VENUE,
        )

    @logged
    def scrape(self) -> None:
        response = self.store.session.get(LISTING_URL, timeout=60)
        response.raise_for_status()
        soup = BeautifulSoup(response.text, "html.parser")
        shows: list[ViennaShow] = []
        seen: set[str] = set()
        last_start: date | None = None
        for item in soup.select(".event"):
            show = self.parse_item(item)
            if show is None or show.url in seen:
                continue
            if last_start and show.start and show.start < last_start - timedelta(days=21):
                break
            if show.start:
                last_start = show.start
            seen.add(show.url)
            shows.append(show)
        print(f"cards={len(shows)}", flush=True)
        self.store.persist(shows)


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--dry", action="store_true")
    args = parser.parse_args()
    ImportExportScraper(dry=args.dry).scrape()
