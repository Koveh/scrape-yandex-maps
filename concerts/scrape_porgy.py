"""Scrape Porgy & Bess jazz listings into `concerts` (city = Вена)."""
from __future__ import annotations

import argparse
import re
from urllib.parse import urljoin

from bs4 import BeautifulSoup
from bs4.element import Tag

from vienna_common import (
    ViennaShow,
    ViennaStore,
    german_date,
    logged,
    occurrence_id,
    og_image,
    parse_start_time,
)

LISTING_URL = "https://www.porgy.at/events/upcoming"
SOURCE_CHANNEL = "porgy"
VENUE = "Porgy & Bess"


class PorgyScraper:
    def __init__(self, dry: bool = False) -> None:
        self.store = ViennaStore(SOURCE_CHANNEL, dry=dry)

    def fill_image(self, show: ViennaShow) -> None:
        if show.image_src:
            return
        response = self.store.session.get(show.url, timeout=30)
        if response.status_code != 200:
            return
        show.image_src = og_image(response.text)

    def parse_row(self, row: Tag, last_date_text: str) -> tuple[ViennaShow | None, str]:
        title_link = row.select_one(".title a[href*='/events/']")
        if title_link is None:
            return None, last_date_text
        name = title_link.get_text(strip=True)
        href = title_link.get("href") or ""
        if not name or not href:
            return None, last_date_text
        date_text = row.select_one(".date")
        date_raw = date_text.get_text(strip=True) if date_text else ""
        if date_raw:
            last_date_text = date_raw
        time_el = row.select_one(".time")
        floor = row.select_one(".floor")
        show_id = re.search(r"/events/(\d+)/", href)
        start = german_date(last_date_text)
        start_time = parse_start_time(time_el.get_text(strip=True) if time_el else "")
        source_id = int(show_id.group(1)) if show_id else 0
        return (
            ViennaShow(
                description=(floor.get_text(" ", strip=True) if floor else "")[:500],
                name=name,
                source_channel=SOURCE_CHANNEL,
                source_message_id=occurrence_id(source_id, start, start_time),
                start=start,
                start_time=start_time,
                url=urljoin(LISTING_URL, href),
                venue=VENUE,
            ),
            last_date_text,
        )

    @logged
    def scrape(self) -> None:
        response = self.store.session.get(LISTING_URL, timeout=60)
        response.raise_for_status()
        soup = BeautifulSoup(response.text, "html.parser")
        shows: list[ViennaShow] = []
        seen: set[str] = set()
        last_date_text = ""
        for row in soup.select("div.row.event_list"):
            show, last_date_text = self.parse_row(row, last_date_text)
            if show is None or show.url in seen:
                continue
            seen.add(show.url)
            if not self.store.dry:
                self.fill_image(show)
            shows.append(show)
        print(f"cards={len(shows)}", flush=True)
        self.store.persist(shows)


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--dry", action="store_true")
    args = parser.parse_args()
    PorgyScraper(dry=args.dry).scrape()
