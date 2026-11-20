"""Scrape The Jungle Comedy Club English standup into `concerts` (city = Мюнхен)."""
from __future__ import annotations

import argparse
import json
from datetime import date

import requests
from bs4 import BeautifulSoup

from munich_common import MunichStore
from vienna_common import (
    ViennaShow,
    logged,
    parse_iso_datetime,
    parse_price,
    stable_id,
    strip_html,
)

HOME_URL = "https://thejunglecomedyclub.com/"
SOURCE_CHANNEL = "junglecomedy"
VENUE = "The Jungle Comedy Club"


class JungleComedyScraper:
    def __init__(self, dry: bool = False) -> None:
        self.store = MunichStore(SOURCE_CHANNEL, dry=dry)

    def event_payload(self, html: str) -> dict | None:
        soup = BeautifulSoup(html, "html.parser")
        for script in soup.select('script[type="application/ld+json"]'):
            try:
                data = json.loads(script.get_text())
            except json.JSONDecodeError:
                continue
            items = data if isinstance(data, list) else [data]
            for item in items:
                if isinstance(item, dict) and item.get("@type") == "Event":
                    return item
        return None

    def parse_event(self, url: str) -> ViennaShow | None:
        try:
            response = self.store.session.get(url, timeout=90)
        except requests.RequestException as exc:
            print(f"  skip {url}: {exc}", flush=True)
            return None
        if response.status_code != 200:
            return None
        payload = self.event_payload(response.text)
        if payload is None:
            return None
        name = strip_html(str(payload.get("name") or ""))
        if not name:
            return None
        start, start_time = parse_iso_datetime(str(payload.get("startDate") or ""))
        if start is not None and start < date.today():
            return None
        image = payload.get("image")
        image_src = image if isinstance(image, str) else None
        description = strip_html(str(payload.get("description") or ""))[:500]
        price_from, price_to = parse_price(description)
        location = payload.get("location") or {}
        venue = location.get("name") if isinstance(location, dict) else None
        return ViennaShow(
            description=description,
            image_src=image_src,
            name=name,
            price_from=price_from,
            price_to=price_to,
            source_channel=SOURCE_CHANNEL,
            source_message_id=stable_id(url, start, start_time),
            start=start,
            start_time=start_time,
            url=url,
            venue=(venue or VENUE)[:120],
        )

    def listing_urls(self, html: str) -> list[str]:
        soup = BeautifulSoup(html, "html.parser")
        urls: list[str] = []
        seen: set[str] = set()
        for node in soup.select('.evo_event_schema a[itemprop="url"], a[href*="/events/"]'):
            href = node.get("href") or ""
            if "/events/" not in href:
                continue
            if any(part in href for part in ("/events/list", "/events/month", "/events/today", "/events/category")):
                continue
            if href.rstrip("/") in {"https://thejunglecomedyclub.com/events", HOME_URL.rstrip("/") + "/events"}:
                continue
            if href in seen:
                continue
            seen.add(href)
            urls.append(href)
        return urls

    @logged
    def scrape(self) -> None:
        home = self.store.session.get(HOME_URL, timeout=90)
        home.raise_for_status()
        shows: list[ViennaShow] = []
        seen: set[str] = set()
        urls = self.listing_urls(home.text)
        print(f"urls={len(urls)}", flush=True)
        for url in urls:
            show = self.parse_event(url)
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
    JungleComedyScraper(dry=args.dry).scrape()
