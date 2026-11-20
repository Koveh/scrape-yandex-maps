"""Shared Yeah-CMS calendar scraper for Munich comedy houses."""
from __future__ import annotations

import argparse
import re
from datetime import date

from bs4 import BeautifulSoup
from bs4.element import Tag

from munich_common import MunichStore, month_bounds
from vienna_common import (
    ViennaShow,
    is_cancelled,
    logged,
    occurrence_id,
    parse_listing_date,
    parse_price,
    parse_start_time,
    strip_html,
)

VENUES = {
    "vereinsheim": {
        "base": "https://vereinsheim.yeah.de",
        "source": "vereinsheim",
        "venue": "Vereinsheim",
    },
    "lachundschiess": {
        "base": "https://lachundschiess.de",
        "source": "lachundschiess",
        "venue": "Lach- und Schießgesellschaft",
    },
    "lustspielhaus": {
        "base": "https://lustspielhaus.yeah.de",
        "source": "lustspielhaus",
        "venue": "Lustspielhaus",
    },
}


class YeahCalendarScraper:
    def __init__(self, venue_key: str, dry: bool = False) -> None:
        config = VENUES[venue_key]
        self.base = config["base"]
        self.source = config["source"]
        self.store = MunichStore(self.source, dry=dry)
        self.venue = config["venue"]

    def parse_row(self, row: Tag) -> ViennaShow | None:
        inner = row.select_one(".event-row-inner") or row
        href = inner.get("data-link") or ""
        if not href:
            link = row.select_one("a[href*='/event/']")
            href = (link.get("href") if link else "") or ""
        if not href:
            return None
        text = row.get_text(" ", strip=True)
        if is_cancelled(text):
            return None
        artist_el = row.select_one(".event-row-artist")
        title_el = row.select_one(".event-row-title")
        artist = strip_html(artist_el.get_text(" ", strip=True) if artist_el else "")
        title = strip_html(title_el.get_text(" ", strip=True) if title_el else "")
        name = " – ".join(part for part in (artist, title) if part)
        if not name:
            return None
        date_el = row.select_one(".event-row-date-date")
        time_el = row.select_one(".event-row-date-time")
        start = parse_listing_date(date_el.get_text(" ", strip=True) if date_el else text)
        start_time = parse_start_time(time_el.get_text(" ", strip=True) if time_el else text)
        if start is not None and start < date.today():
            return None
        location = row.select_one(".event-row-location")
        venue = strip_html(location.get_text(" ", strip=True) if location else "") or self.venue
        show_id = re.search(r"/event/(\d+)", href)
        source_id = int(show_id.group(1)) if show_id else 0
        price_from, price_to = parse_price(text)
        return ViennaShow(
            name=name,
            price_from=price_from,
            price_to=price_to,
            source_channel=self.source,
            source_message_id=occurrence_id(source_id, start, start_time),
            start=start,
            start_time=start_time,
            url=href,
            venue=venue[:120],
        )

    def fetch_month(self, start: date, end: date) -> list[ViennaShow]:
        url = f"{self.base}/events/{start.isoformat()}/{end.isoformat()}/all/"
        response = self.store.session.get(url, timeout=60)
        response.raise_for_status()
        soup = BeautifulSoup(response.text, "html.parser")
        shows: list[ViennaShow] = []
        for row in soup.select(".event-row"):
            show = self.parse_row(row)
            if show is not None:
                shows.append(show)
        print(f"  {start.isoformat()} rows={len(shows)}", flush=True)
        return shows

    @logged
    def scrape(self) -> None:
        shows: list[ViennaShow] = []
        seen: set[str] = set()
        for offset in range(0, 8):
            start, end = month_bounds(offset)
            for show in self.fetch_month(start, end):
                key = f"{show.url}|{show.start}|{show.start_time}"
                if key in seen:
                    continue
                seen.add(key)
                shows.append(show)
        print(f"cards={len(shows)} source={self.source}", flush=True)
        self.store.persist(shows)


def run_venue(venue_key: str) -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--dry", action="store_true")
    args = parser.parse_args()
    YeahCalendarScraper(venue_key, dry=args.dry).scrape()
