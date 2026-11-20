"""Scrape U4 Club Vienna EventON listings into `concerts`."""
from __future__ import annotations

import argparse
from datetime import datetime, timezone
from zoneinfo import ZoneInfo

from bs4 import BeautifulSoup

from vienna_common import HtmlVenueScraper, ViennaShow, parse_iso_datetime, parse_listing_date, parse_start_time

LISTING_URL = "https://www.u4.at/events-veranstaltungen/"
VIENNA = ZoneInfo("Europe/Vienna")


class U4Scraper(HtmlVenueScraper):
    listing_url = LISTING_URL
    source_channel = "u4"
    venue = "U4"

    def start_from_event(self, item) -> tuple:
        meta = item.select_one("meta[itemprop='startDate']")
        if meta:
            start, start_time = parse_iso_datetime(str(meta.get("content") or ""))
            if start is not None:
                return start, start_time
        stamp = str(item.get("data-time") or "").split("-")[0]
        if stamp.isdigit():
            local = datetime.fromtimestamp(int(stamp), tz=timezone.utc).astimezone(VIENNA)
            return local.date(), local.time()
        text = item.get_text(" ", strip=True)
        return parse_listing_date(text), parse_start_time(text)

    def parse(self, soup: BeautifulSoup) -> list[ViennaShow]:
        shows: list[ViennaShow] = []
        for item in soup.select(".eventon_list_event"):
            title = item.select_one(".evcal_event_title, span[itemprop='name'], .evo_event_title")
            name = title.get_text(" ", strip=True) if title else ""
            if name.lower() in {"u4 club", "u4"}:
                subtitle = item.select_one(".evcal_event_subtitle, .event_subtitle")
                extra = item.get_text(" ", strip=True)
                name = (subtitle.get_text(" ", strip=True) if subtitle else "") or extra[:80]
            link = item.select_one("a[itemprop='url'], a[href*='/events/']")
            start, start_time = self.start_from_event(item)
            img = item.select_one("meta[itemprop='image']")
            show = self.make_show(
                name=name,
                url=(link.get("href") if link else "") or LISTING_URL,
                start=start,
                start_time=start_time,
                image_src=img.get("content") if img else None,
            )
            if show:
                shows.append(show)
        return shows


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--dry", action="store_true")
    args = parser.parse_args()
    U4Scraper(dry=args.dry).scrape()
