"""Yandex Afisha Moscow concert listing -> concerts (kept).

Uses public HTML cards; skips when the page is a hard SPA shell with no events.
"""
from __future__ import annotations

import argparse
import json
import re
from datetime import datetime
from urllib.parse import urljoin

from bs4 import BeautifulSoup

from moscow_common import MOSCOW_CITY, parse_ru_date, parse_ru_time
from vienna_common import HtmlVenueScraper, ViennaShow, session_get

LISTING_URL = "https://afisha.yandex.ru/moscow/concert"
BASE = "https://afisha.yandex.ru"


class YandexAfishaMoscowScraper(HtmlVenueScraper):
    city = MOSCOW_CITY
    listing_url = LISTING_URL
    source_channel = "yandex_afisha"
    venue = "Москва"

    def scrape(self) -> None:
        response = session_get(self.store.session, self.listing_url, timeout=90)
        if response is None:
            print("skip yandex_afisha empty", flush=True)
            return
        shows = self.parse_json_ld(response.text) or self.parse(BeautifulSoup(response.text, "html.parser"))
        print(f"cards={len(shows)}", flush=True)
        self.persist_shows(shows)

    def parse_json_ld(self, html: str) -> list[ViennaShow]:
        shows: list[ViennaShow] = []
        for match in re.finditer(
            r'<script[^>]*type="application/ld\+json"[^>]*>(.*?)</script>',
            html,
            re.S | re.I,
        ):
            try:
                payload = json.loads(match.group(1))
            except json.JSONDecodeError:
                continue
            nodes = payload if isinstance(payload, list) else [payload]
            for node in nodes:
                if not isinstance(node, dict):
                    continue
                graph = node.get("@graph") if isinstance(node.get("@graph"), list) else [node]
                for item in graph:
                    if not isinstance(item, dict):
                        continue
                    types = item.get("@type")
                    type_list = types if isinstance(types, list) else [types]
                    if not any(t in {"Event", "MusicEvent", "TheaterEvent"} for t in type_list if t):
                        continue
                    name = (item.get("name") or "").strip()
                    url = (item.get("url") or "").strip()
                    start_raw = item.get("startDate") or ""
                    if not name or not url or not start_raw:
                        continue
                    try:
                        parsed = datetime.fromisoformat(start_raw.replace("Z", "+00:00"))
                        start = parsed.date()
                        start_time = parsed.timetz().replace(tzinfo=None, second=0, microsecond=0)
                    except ValueError:
                        continue
                    location = item.get("location") or {}
                    venue = ""
                    if isinstance(location, dict):
                        venue = (location.get("name") or "").strip()
                    image = item.get("image")
                    if isinstance(image, list) and image:
                        image = image[0]
                    if not isinstance(image, str):
                        image = None
                    show = self.make_show(
                        name=name,
                        url=urljoin(BASE, url),
                        start=start,
                        start_time=start_time,
                        venue=venue or self.venue,
                        image_src=image,
                    )
                    if show:
                        shows.append(show)
        return shows

    def parse(self, soup: BeautifulSoup) -> list[ViennaShow]:
        shows: list[ViennaShow] = []
        for link in soup.select('a[href*="/moscow/"]'):
            href = (link.get("href") or "").strip()
            if "/concert/" not in href and "/theatre/" not in href and "/events/" not in href:
                continue
            text = link.get_text(" ", strip=True)
            name = re.sub(r"\s+", " ", text).strip()
            if len(name) < 3:
                continue
            start = parse_ru_date(text)
            if start is None:
                continue
            show = self.make_show(
                name=name[:160],
                url=urljoin(BASE, href),
                start=start,
                start_time=parse_ru_time(text),
                venue=self.venue,
                description=text[:500],
            )
            if show:
                shows.append(show)
        return shows


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--dry", action="store_true")
    args = parser.parse_args()
    YandexAfishaMoscowScraper(dry=args.dry).scrape()
