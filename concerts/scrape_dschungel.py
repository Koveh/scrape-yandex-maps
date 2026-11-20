"""Scrape Dschungel Wien spielplan into `concerts`."""
from __future__ import annotations

import argparse
import re

from bs4 import BeautifulSoup

from vienna_common import HtmlVenueScraper, ViennaShow, listing_image_src, parse_iso_datetime

LISTING_URL = "https://www.dschungelwien.at/spielplan"
SKIP_RE = re.compile(r"\b(abgesagt|cancelled)\b", re.I)


class DschungelScraper(HtmlVenueScraper):
    listing_url = LISTING_URL
    source_channel = "dschungel"
    venue = "Dschungel Wien"

    def parse(self, soup: BeautifulSoup) -> list[ViennaShow]:
        shows: list[ViennaShow] = []
        seen: set[str] = set()
        for item in soup.select(".event-week"):
            text = re.sub(r"\s+", " ", item.get_text(" ", strip=True))
            if SKIP_RE.search(text):
                continue
            title = item.select_one(".event-week__title a, .event-week__title")
            name = title.get_text(" ", strip=True) if title else ""
            subtitle = item.select_one(".event-week__subtitle")
            if subtitle:
                extra = subtitle.get_text(" ", strip=True)
                if extra and extra.lower() not in name.lower():
                    name = f"{name} — {extra}"
            href = ""
            if title and title.name == "a":
                href = title.get("href") or ""
            elif title:
                link = title.select_one("a[href]")
                href = (link.get("href") if link else "") or ""
            time_el = item.select_one("time[datetime]")
            start, start_time = parse_iso_datetime(time_el.get("datetime") if time_el else text)
            hall = item.select_one(".event-week__location")
            show = self.make_show(
                name=name,
                url=href or LISTING_URL,
                start=start,
                start_time=start_time,
                venue=(hall.get_text(" ", strip=True) if hall else "") or self.venue,
                image_src=listing_image_src(item),
            )
            if show is None:
                continue
            key = f"{show.start}:{show.start_time}:{show.name.lower()}"
            if key in seen:
                continue
            seen.add(key)
            shows.append(show)
        return shows


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--dry", action="store_true")
    args = parser.parse_args()
    DschungelScraper(dry=args.dry).scrape()
