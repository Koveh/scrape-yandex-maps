"""Scrape MARX HALLE events into `concerts` (city = Вена)."""
from __future__ import annotations

import argparse
import re
from datetime import date
from html import unescape

from vienna_common import (
    ViennaShow,
    ViennaStore,
    logged,
    parse_listing_date,
    strip_html,
    url_message_id,
)

API = "https://marxhalle.at/wp-json/wp/v2/events"
SOURCE_CHANNEL = "marxhalle"
VENUE = "MARX HALLE"


class MarxhalleScraper:
    def __init__(self, dry: bool = False) -> None:
        self.store = ViennaStore(SOURCE_CHANNEL, dry=dry)

    def parse_event(self, payload: dict) -> ViennaShow | None:
        title = payload.get("title") or {}
        name = unescape(strip_html(str(title.get("rendered") if isinstance(title, dict) else title)))
        url = str(payload.get("link") or "")
        content = strip_html(str((payload.get("content") or {}).get("rendered") or ""))
        yoast = str(payload.get("yoast_head") or "")
        start = parse_listing_date(content) or parse_listing_date(yoast) or parse_listing_date(name)
        if not name or not url or start is None or start < date.today():
            return None
        if re.search(r"\b(jobmesse|selfcare|coffee festival|sports world|designmarkt|depot)\b", name, re.I):
            return None
        return ViennaShow(
            description=content[:500],
            name=name,
            source_channel=SOURCE_CHANNEL,
            source_message_id=int(payload.get("id") or 0) or url_message_id(url),
            start=start,
            url=url,
            venue=VENUE,
        )

    @logged
    def scrape(self) -> None:
        shows: list[ViennaShow] = []
        page = 1
        while page <= 6:
            response = self.store.session.get(API, params={"per_page": 20, "page": page}, timeout=60)
            if response.status_code != 200:
                break
            rows = response.json()
            if not rows:
                break
            for payload in rows:
                show = self.parse_event(payload)
                if show:
                    shows.append(show)
            page += 1
        print(f"cards={len(shows)}", flush=True)
        self.store.persist(shows)


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--dry", action="store_true")
    args = parser.parse_args()
    MarxhalleScraper(dry=args.dry).scrape()
