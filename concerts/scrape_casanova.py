"""Scrape Casanova Vienna kabarett into `concerts` (city = Вена)."""
from __future__ import annotations

import argparse
import re
from datetime import datetime

from bs4 import BeautifulSoup

from vienna_common import (
    HtmlVenueScraper,
    ViennaShow,
    parse_iso_datetime,
    parse_listing_date,
    parse_price,
    parse_start_time,
)

LISTING_URL = "https://casanova-vienna.at/tickets/"
SKIP_RE = re.compile(r"(tageskassa|kassa geöffnet|abgesagt)", re.I)


class CasanovaScraper(HtmlVenueScraper):
    listing_url = LISTING_URL
    source_channel = "casanova"
    venue = "Casanova Vienna"

    def parse(self, soup: BeautifulSoup) -> list[ViennaShow]:
        shows: list[ViennaShow] = []
        for item in soup.select(".eventon_list_event"):
            title = item.select_one(".evcal_event_title, [itemprop='name']")
            name = title.get_text(" ", strip=True) if title else ""
            schema_url = item.select_one('a[itemprop="url"]')
            href = (schema_url.get("href") if schema_url else "") or (
                item.select_one("a[href*='/events/']").get("href")
                if item.select_one("a[href*='/events/']")
                else ""
            )
            start_meta = item.select_one('meta[itemprop="startDate"]')
            start_raw = start_meta.get("content") if start_meta else ""
            if not start_raw:
                start_raw = item.get_text(" ", strip=True)
            start, start_time = parse_iso_datetime(start_raw.replace("+1:00", "+01:00"))
            if start is None:
                start = parse_listing_date(start_raw)
            if start is None:
                epoch = re.search(r"(\d{10})", item.get("data-time") or "")
                if epoch:
                    start = datetime.fromtimestamp(int(epoch.group(1))).date()
            text = item.get_text(" ", strip=True)
            if SKIP_RE.search(name) or SKIP_RE.search(text):
                continue
            img = item.select_one('meta[itemprop="image"]')
            price_from, price_to = parse_price(text)
            show = self.make_show(
                name=name,
                url=href or LISTING_URL,
                start=start,
                start_time=start_time or parse_start_time(text),
                image_src=img.get("content") if img else None,
                price_from=price_from,
                price_to=price_to,
            )
            if show:
                shows.append(show)
        return shows


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--dry", action="store_true")
    args = parser.parse_args()
    CasanovaScraper(dry=args.dry).scrape()
