"""Scrape Grelle Forelle club nights into `concerts` (city = Вена)."""
from __future__ import annotations

import argparse
import re

from bs4 import BeautifulSoup
from bs4.element import Tag

from vienna_common import ViennaShow, ViennaStore, day_month_date, logged, occurrence_id

LISTING_URL = "https://www.grelleforelle.com/programm/"
SOURCE_CHANNEL = "grelleforelle"
VENUE = "Grelle Forelle"


class GrelleForelleScraper:
    def __init__(self, dry: bool = False) -> None:
        self.store = ViennaStore(SOURCE_CHANNEL, dry=dry)

    def parse_item(self, item: Tag) -> ViennaShow | None:
        title_link = item.select_one("h2 a")
        if title_link is None:
            return None
        raw_name = title_link.get_text(strip=True)
        href = title_link.get("href") or ""
        dated = re.match(r"(\d{2})/(\d{2})\s+(.+)", raw_name)
        if not dated or not href:
            return None
        classes = " ".join(item.get("class") or [])
        year_match = re.search(r"project_category_?(20\d{2})", classes)
        year = int(year_match.group(1)) if year_match else None
        start = day_month_date(int(dated.group(1)), int(dated.group(2)), year)
        img = item.select_one("img")
        post_id = re.search(r"post-(\d+)", item.get("id") or "")
        source_id = int(post_id.group(1)) if post_id else 0
        return ViennaShow(
            description="Club",
            image_src=img.get("src") if img else None,
            name=dated.group(3).strip(),
            source_channel=SOURCE_CHANNEL,
            source_message_id=occurrence_id(source_id, start, None),
            start=start,
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
        for item in soup.select(".et_pb_portfolio_item"):
            show = self.parse_item(item)
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
    GrelleForelleScraper(dry=args.dry).scrape()
