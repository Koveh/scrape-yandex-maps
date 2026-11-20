"""Afisha.ru Moscow theatre / hall place pages → concerts (kept).

Covers Taganka, Sovremennik, MXAT, Vakhtangov stages, Pushkin, Helikon,
House of Music and siblings when official sites are JS-heavy or unreachable.
"""
from __future__ import annotations

import argparse
import json
import re
from datetime import datetime
from urllib.parse import urljoin

from moscow_common import MOSCOW_CITY
from vienna_common import HtmlVenueScraper, ViennaShow, session_get

BASE = "https://www.afisha.ru"
THEATRE_INDEX = f"{BASE}/msk/theatre/"

# Always scrape these — people actually go.
PRIORITY_PATHS = (
    "/msk/theatre/teatr-na-taganke-15878132/",
    "/msk/theatre/teatr-na-taganke-scena-na-fakelnom-15926282/",
    "/msk/theatre/sovremennik-osnovnaya-scena-15878493/",
    "/msk/theatre/sovremennik-drugaya-scena-15926274/",
    "/msk/theatre/teatr-im-pushkina-15877719/",
    "/msk/theatre/filial-teatra-im-pushkina-15878150/",
    "/msk/theatre/teatr-im-vahtangova-15878827/",
    "/msk/theatre/teatr-im-vahtangova-simonovskaya-scena-15878138/",
    "/msk/theatre/mht-im-chehova-15877720/",
    "/msk/theatre/mht-imeni-a-p-chehova-15877720/",
    "/msk/theatre/lenkom-marka-zaharova-15877722/",
    "/msk/schedule_theatre/place-gelikon-opera-15879450/",
    "/msk/schedule_theatre/place-dom-muzyki-4759/",
    "/msk/schedule_theatre/place-mhat-gorkogo-15878492/",
    "/msk/schedule_theatre/place-teatr-im-vahtangova-15878827/",
    "/msk/schedule_theatre/place-teatr-na-taganke-15878132/",
    "/msk/schedule_theatre/place-sovremennik-osnovnaya-scena-15878493/",
)

# Schedule place pages omit PlaceInfo — map slug → display venue.
SCHEDULE_VENUE_LABELS = {
    "place-gelikon-opera-15879450": "Геликон-опера",
    "place-dom-muzyki-4759": "Дом музыки",
    "place-mhat-gorkogo-15878492": "МХАТ Горького",
    "place-teatr-im-vahtangova-15878827": "Театр им. Вахтангова",
    "place-teatr-na-taganke-15878132": "Театр на Таганке",
    "place-sovremennik-osnovnaya-scena-15878493": "Современник. Основная сцена",
}


def _extract_root(html: str) -> dict:
    match = re.search(r"\['root'\]\s*=\s*(\{)", html)
    if not match:
        return {}
    start = match.end(1) - 1
    depth = 0
    for index, char in enumerate(html[start:], start):
        if char == "{":
            depth += 1
        elif char == "}":
            depth -= 1
            if depth == 0:
                return json.loads(html[start : index + 1])
    return {}


class AfishaTheatresScraper(HtmlVenueScraper):
    city = MOSCOW_CITY
    listing_url = THEATRE_INDEX
    source_channel = "afisha_theatres"
    venue = "Москва"

    def __init__(self, dry: bool = False, limit: int = 0) -> None:
        super().__init__(dry=dry)
        self.limit = limit

    def discover_paths(self) -> list[str]:
        response = session_get(self.store.session, THEATRE_INDEX, timeout=90)
        paths = set(PRIORITY_PATHS)
        if response is not None:
            for slug in re.findall(r"/msk/theatre/([a-z0-9-]+-\d+)/", response.text):
                paths.add(f"/msk/theatre/{slug}/")
        ordered = list(PRIORITY_PATHS) + sorted(paths - set(PRIORITY_PATHS))
        if self.limit:
            return ordered[: self.limit]
        return ordered

    def _sessions_from_row(self, row: dict, fallback_path: str) -> list[dict]:
        sessions: list[dict] = []
        for place_block in row.get("PlaceSchedules") or []:
            sessions.extend(place_block.get("Sessions") or [])
        if sessions:
            return sessions
        tile = row.get("Tile") or row.get("Concert") or row.get("Performance") or {}
        info = tile.get("ScheduleInfo") or {}
        raw = info.get("MinScheduleDate")
        if raw:
            return [{"DateTime": raw, "Url": fallback_path}]
        return []

    def _shows_from_items(
        self, items: list, place_name: str, seen: set[str]
    ) -> list[ViennaShow]:
        shows: list[ViennaShow] = []
        for row in items:
            if not isinstance(row, dict):
                continue
            tile = (
                row.get("Tile")
                or row.get("Concert")
                or row.get("Performance")
                or row.get("Exhibition")
                or row
            )
            if not isinstance(tile, dict) or tile.get("IsCanceled"):
                continue
            name = (tile.get("Name") or "").strip()
            path = (tile.get("Url") or "").split("#", 1)[0]
            if not name or not path:
                continue
            image = ((tile.get("Image16x9") or tile.get("Image1x1") or {}) or {}).get("Url")
            for session in self._sessions_from_row(row, path):
                start_raw = session.get("DateTime")
                if not start_raw:
                    continue
                try:
                    parsed = datetime.fromisoformat(str(start_raw))
                except ValueError:
                    continue
                start = parsed.date()
                start_time = parsed.time().replace(second=0, microsecond=0)
                href = urljoin(BASE, session.get("Url") or path)
                key = f"{href}|{start}|{name.lower()}"
                if key in seen:
                    continue
                seen.add(key)
                show = self.make_show(
                    name=name,
                    url=href,
                    start=start,
                    start_time=start_time,
                    venue=place_name,
                    image_src=image,
                    description=(tile.get("Description") or "")[:500],
                )
                if show:
                    shows.append(show)
        return shows

    def parse_place(self, path: str) -> list[ViennaShow]:
        url = urljoin(BASE, path)
        response = session_get(self.store.session, url, timeout=60)
        if response is None:
            return []
        root = _extract_root(response.text)
        model = root.get("model") or {}
        slug = path.rstrip("/").split("/")[-1]
        place_name = (
            ((model.get("PlaceInfo") or {}).get("Name") or "")
            or SCHEDULE_VENUE_LABELS.get(slug, "")
            or slug
        ).strip()
        seen: set[str] = set()
        shows: list[ViennaShow] = []

        schedule = model.get("Schedule") or {}
        for widget in schedule.values():
            if isinstance(widget, dict):
                shows.extend(self._shows_from_items(widget.get("Items") or [], place_name, seen))

        schedule_widget = model.get("ScheduleWidget") or {}
        if isinstance(schedule_widget, dict):
            shows.extend(
                self._shows_from_items(schedule_widget.get("Items") or [], place_name, seen)
            )
        return shows

    def scrape(self) -> None:
        paths = self.discover_paths()
        print(f"theatres={len(paths)}", flush=True)
        all_shows: list[ViennaShow] = []
        for path in paths:
            batch = self.parse_place(path)
            if batch:
                print(f"  {path.rstrip('/').split('/')[-1]} cards={len(batch)}", flush=True)
            all_shows.extend(batch)
        print(f"cards={len(all_shows)} source={self.source_channel}", flush=True)
        self.persist_shows(all_shows)


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--dry", action="store_true")
    parser.add_argument("--limit", type=int, default=0, help="max places (0=all)")
    args = parser.parse_args()
    AfishaTheatresScraper(dry=args.dry, limit=args.limit).scrape()
