"""Scrape B72 Vienna listings into `concerts` (city = Вена)."""
from __future__ import annotations

import argparse
import re
from urllib.parse import urljoin

from bs4 import BeautifulSoup
from bs4.element import Tag

from vienna_common import (
    ViennaShow,
    ViennaStore,
    background_image_url,
    day_month_date,
    logged,
    occurrence_id,
)

LISTING_URL = "https://www.b72.at/program"
SOURCE_CHANNEL = "b72"
VENUE = "B72"


class B72Scraper:
    def __init__(self, dry: bool = False) -> None:
        self.store = ViennaStore(SOURCE_CHANNEL, dry=dry)

    def parse_card(self, item: Tag) -> ViennaShow | None:
        title_link = item.select_one("a[href*='/program/']")
        if title_link is None:
            return None
        href = title_link.get("href") or ""
        bits = [part.strip() for part in item.get_text("|", strip=True).split("|") if part.strip()]
        bits = [bit for bit in bits if bit.lower() != "tickets"]
        if len(bits) < 2 or not href:
            return None
        dated = re.match(r"(\d{1,2})\.(\d{1,2})", bits[0])
        if not dated:
            return None
        name = bits[1]
        start = day_month_date(int(dated.group(1)), int(dated.group(2)))
        img = item.select_one(".bg-image")
        program_id = re.search(r"/program/(\d+)/", href)
        source_id = int(program_id.group(1)) if program_id else 0
        return ViennaShow(
            image_src=background_image_url(img.get("style") or "") if img else None,
            name=name,
            source_channel=SOURCE_CHANNEL,
            source_message_id=occurrence_id(source_id, start, None),
            start=start,
            url=urljoin(LISTING_URL, href),
            venue=VENUE,
        )

    @logged
    def scrape(self) -> None:
        response = self.store.session.get(LISTING_URL, timeout=60)
        response.raise_for_status()
        html = response.content.decode("utf-8", errors="replace")
        soup = BeautifulSoup(html, "html.parser")
        shows: list[ViennaShow] = []
        seen: set[str] = set()
        for item in soup.select(".coming-up"):
            show = self.parse_card(item)
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
    B72Scraper(dry=args.dry).scrape()
