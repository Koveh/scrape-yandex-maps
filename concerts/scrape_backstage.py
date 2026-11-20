"""Scrape Backstage München via rausgegangen.de location feed into `concerts`."""
from __future__ import annotations

import argparse
from datetime import date
from urllib.parse import urljoin

from bs4 import BeautifulSoup
from bs4.element import Tag

from munich_common import MunichStore
from vienna_common import (
    ViennaShow,
    logged,
    parse_listing_date,
    parse_price,
    parse_start_time,
    session_get,
    stable_id,
    strip_html,
)

LISTING_URL = "https://rausgegangen.de/locations/backstage/"
SOURCE_CHANNEL = "backstage"
VENUE = "Backstage"


class BackstageScraper:
    def __init__(self, dry: bool = False) -> None:
        self.store = MunichStore(SOURCE_CHANNEL, dry=dry)

    def parse_tile(self, link: Tag) -> ViennaShow | None:
        href = link.get("href") or ""
        if "/events/" not in href:
            return None
        url = urljoin(LISTING_URL, href)
        img = link.select_one("img")
        name = strip_html((img.get("alt") if img else "") or "")
        text = link.get_text(" ", strip=True)
        if not name:
            bits = [part.strip() for part in text.split("|") if part.strip()]
            name = next((bit for bit in bits if bit and not bit[0].isdigit() and "€" not in bit), "")
        if not name:
            return None
        start = parse_listing_date(text)
        if start is not None and start < date.today():
            return None
        image_src = img.get("src") if img else None
        price_from, price_to = parse_price(text)
        return ViennaShow(
            image_src=image_src if image_src and str(image_src).startswith("http") else None,
            name=name,
            price_from=price_from,
            price_to=price_to,
            source_channel=SOURCE_CHANNEL,
            source_message_id=stable_id(url, start, parse_start_time(text)),
            start=start,
            start_time=parse_start_time(text),
            url=url,
            venue=VENUE,
        )

    @logged
    def scrape(self) -> None:
        response = session_get(self.store.session, LISTING_URL, timeout=60)
        soup = BeautifulSoup(response.text if response is not None else "", "html.parser")
        shows: list[ViennaShow] = []
        seen: set[str] = set()
        for link in soup.select('.tile a[href*="/events/"]'):
            show = self.parse_tile(link)
            if show is None or show.url in seen:
                continue
            seen.add(show.url)
            shows.append(show)
        print(f"cards={len(shows)}", flush=True)
        self.store.persist(shows)


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--dry", action="store_true")
    args = parser.parse_args()
    BackstageScraper(dry=args.dry).scrape()
