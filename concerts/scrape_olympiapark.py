"""Scrape Olympiapark / Olympiahalle concerts from the official listing JSON-LD."""
from __future__ import annotations

import argparse
import json
from datetime import date

from bs4 import BeautifulSoup

from munich_common import MunichStore
from vienna_common import ViennaShow, logged, parse_iso_datetime, stable_id, strip_html

LISTING_URL = "https://www.olympiapark.de/de/veranstaltungen/konzerte"
SOURCE_CHANNEL = "olympiapark"


class OlympiaparkScraper:
    def __init__(self, dry: bool = False) -> None:
        self.store = MunichStore(SOURCE_CHANNEL, dry=dry)

    def parse_event(self, payload: dict) -> ViennaShow | None:
        name = strip_html(str(payload.get("name") or ""))
        if not name:
            return None
        start, start_time = parse_iso_datetime(str(payload.get("startDate") or ""))
        if start is not None and start < date.today():
            return None
        location = payload.get("location") or {}
        venue = location.get("name") if isinstance(location, dict) else None
        image = payload.get("image")
        image_src = image if isinstance(image, str) else None
        url = str(payload.get("url") or LISTING_URL)
        key = f"{name}|{start}|{venue}"
        return ViennaShow(
            image_src=image_src,
            name=name,
            source_channel=SOURCE_CHANNEL,
            source_message_id=stable_id(key, start, start_time),
            start=start,
            start_time=start_time,
            url=url,
            venue=(venue or "Olympiapark")[:120],
        )

    @logged
    def scrape(self) -> None:
        response = self.store.session.get(LISTING_URL, timeout=60)
        response.raise_for_status()
        soup = BeautifulSoup(response.text, "html.parser")
        shows: list[ViennaShow] = []
        seen: set[str] = set()
        for script in soup.select('script[type="application/ld+json"]'):
            try:
                data = json.loads(script.get_text())
            except json.JSONDecodeError:
                continue
            items = data.get("itemListElement") if isinstance(data, dict) else None
            if not items:
                continue
            for item in items:
                if not isinstance(item, dict) or item.get("@type") != "Event":
                    continue
                show = self.parse_event(item)
                if show is None or show.name in seen:
                    continue
                seen.add(show.name)
                shows.append(show)
        print(f"cards={len(shows)}", flush=True)
        self.store.persist(shows)


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--dry", action="store_true")
    args = parser.parse_args()
    OlympiaparkScraper(dry=args.dry).scrape()
