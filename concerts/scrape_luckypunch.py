"""Scrape Lucky Punch Comedy Club Wien into `concerts` (city = Вена)."""
from __future__ import annotations

import argparse
import re

from bs4 import BeautifulSoup

from vienna_common import HtmlVenueScraper, ViennaShow, parse_listing_date, parse_price, parse_start_time

LISTING_URL = "https://www.luckypunch-comedyclub.at/"
SKIP_RE = re.compile(r"\b(workshop|abgesagt)\b", re.I)
SHOW_RE = re.compile(
    r"(?P<name>Stand-up Comedy Mixed Show|Open Mic|Stand-up Comedy Open Mic)"
    r".{0,40}?(?P<date>\d{1,2}\.\d{1,2}\.20\d{2})",
    re.I,
)


class LuckyPunchScraper(HtmlVenueScraper):
    listing_url = LISTING_URL
    source_channel = "luckypunch"
    venue = "Lucky Punch Comedy Club Wien"

    def parse(self, soup: BeautifulSoup) -> list[ViennaShow]:
        shows: list[ViennaShow] = []
        seen: set[str] = set()
        for link in soup.select("a[href]"):
            text = re.sub(r"\s+", " ", link.get_text(" ", strip=True))
            href = link.get("href") or ""
            if SKIP_RE.search(text) or not re.search(r"20\d{2}", text):
                continue
            if not re.search(r"(mixed show|open mic|stand-up comedy)", text, re.I):
                continue
            name = "Stand-up Comedy Mixed Show"
            if re.search(r"open mic", text, re.I):
                name = "Open Mic"
            price_from, price_to = parse_price(text)
            show = self.make_show(
                name=name,
                url=href if href.startswith("http") else LISTING_URL,
                start=parse_listing_date(text),
                start_time=parse_start_time(text) or parse_start_time("20:00"),
                price_from=price_from,
                price_to=price_to,
            )
            if show is None or f"{show.start}|{show.name}" in seen:
                continue
            seen.add(f"{show.start}|{show.name}")
            shows.append(show)
        text = re.sub(r"\s+", " ", soup.get_text(" ", strip=True))
        for match in SHOW_RE.finditer(text):
            name = match.group("name")
            if SKIP_RE.search(name):
                continue
            show = self.make_show(
                name=name,
                url=LISTING_URL,
                start=parse_listing_date(match.group("date")),
                start_time=parse_start_time("20:00"),
            )
            if show is None or f"{show.start}|{show.name}" in seen:
                continue
            seen.add(f"{show.start}|{show.name}")
            shows.append(show)
        return shows


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--dry", action="store_true")
    args = parser.parse_args()
    LuckyPunchScraper(dry=args.dry).scrape()
