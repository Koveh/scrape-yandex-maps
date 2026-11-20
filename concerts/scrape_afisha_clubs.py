"""Afisha.ru Moscow club place pages → concerts (kept).

Discovers clubs from /msk/club/ and scrapes Schedule.ConcertWidget (and siblings)
so Glavstandup / Gipsy / jazz halls / Stand-up rooms land even when official sites
are unreachable from the host.
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
CLUBS_INDEX = f"{BASE}/msk/club/"
# Always try these “people actually go” venues even if not on the first index page.
PRIORITY_SLUGS = (
    "16-tonn-12838",
    "16-tonn-arbat-63731",
    "gipsy-63658",
    "powerhouse-63659",
    "gazgolder-16053",
    "1930-moscow-63493",
    "glavstandup-hall-64131",
    "stand-up-store-moscow-200195",
    "standup-club-na-trubnoy-64020",
    "stand-up-patriki-64133",
    "stendap-import-na-taganke-200185",
    "stendap-klub-kosmos-200218",
    "glastonberry-16505",
    "kitayskiy-letchik-dzhao-da-12866",
    "klub-alekseya-kozlova-17780",
    "dzhaz-klub-igorya-butmana-v-moskve-20769",
    "soyuz-kompozitorov-13776",
    "ritm-blyuz-12853",
    "jam-club-64146",
    "live-stars-63662",
    "live-story-63976",
    "pravda-17462",
    "vysockiy-12261",
    # Glavclub / Stereo Hall / Red Club / Mumiy / Izvestia Hall: not on Afisha
    # club index from this host (DNS/official sites blocked) — covered via
    # schedule_concert + sibling club crawl when Afisha lists them.
)


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


class AfishaClubsScraper(HtmlVenueScraper):
    city = MOSCOW_CITY
    listing_url = CLUBS_INDEX
    source_channel = "afisha_clubs"
    venue = "Москва"

    def __init__(self, dry: bool = False, limit: int = 0) -> None:
        super().__init__(dry=dry)
        self.limit = limit

    def discover_slugs(self) -> list[str]:
        response = session_get(self.store.session, CLUBS_INDEX, timeout=90)
        slugs = set(PRIORITY_SLUGS)
        if response is not None:
            slugs.update(re.findall(r"/msk/club/([a-z0-9-]+-\d+)/", response.text))
        ordered = list(PRIORITY_SLUGS) + sorted(slugs - set(PRIORITY_SLUGS))
        if self.limit:
            return ordered[: self.limit]
        return ordered

    def parse_club(self, slug: str) -> list[ViennaShow]:
        url = f"{BASE}/msk/club/{slug}/"
        response = session_get(self.store.session, url, timeout=60)
        if response is None:
            return []
        root = _extract_root(response.text)
        model = root.get("model") or {}
        place_name = ((model.get("PlaceInfo") or {}).get("Name") or slug).strip()
        schedule = model.get("Schedule") or {}
        shows: list[ViennaShow] = []
        seen: set[str] = set()
        for widget in schedule.values():
            if not isinstance(widget, dict):
                continue
            for row in widget.get("Items") or []:
                concert = row.get("Concert") or row.get("Tile") or row
                if not isinstance(concert, dict) or concert.get("IsCanceled"):
                    continue
                name = (concert.get("Name") or "").strip()
                path = (concert.get("Url") or "").split("#", 1)[0]
                if not name or not path:
                    continue
                image = ((concert.get("Image16x9") or concert.get("Image1x1") or {}) or {}).get(
                    "Url"
                )
                sessions: list[dict] = []
                for place_block in row.get("PlaceSchedules") or []:
                    sessions.extend(place_block.get("Sessions") or [])
                if not sessions:
                    info = concert.get("ScheduleInfo") or {}
                    raw = info.get("MinScheduleDate")
                    if raw:
                        sessions = [{"DateTime": raw, "Url": path}]
                for session in sessions:
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
                        description=(concert.get("Description") or "")[:500],
                    )
                    if show:
                        shows.append(show)
        return shows

    def scrape(self) -> None:
        slugs = self.discover_slugs()
        print(f"clubs={len(slugs)}", flush=True)
        all_shows: list[ViennaShow] = []
        for slug in slugs:
            batch = self.parse_club(slug)
            if batch:
                print(f"  {slug} cards={len(batch)}", flush=True)
            all_shows.extend(batch)
        print(f"cards={len(all_shows)} source={self.source_channel}", flush=True)
        self.persist_shows(all_shows)


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--dry", action="store_true")
    parser.add_argument("--limit", type=int, default=0, help="max clubs (0=all)")
    args = parser.parse_args()
    AfishaClubsScraper(dry=args.dry, limit=args.limit).scrape()
