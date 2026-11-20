"""Scrape Wiener Metropol into `concerts` (city = Вена)."""
from __future__ import annotations

import argparse
import re

from bs4 import BeautifulSoup

from vienna_common import HtmlVenueScraper, ViennaShow, parse_listing_date, parse_start_time

LISTING_URL = "https://www.wiener-metropol.at/spielplan/karten"
SKIP_RE = re.compile(r"\b(abgesagt)\b", re.I)


class MetropolScraper(HtmlVenueScraper):
    listing_url = LISTING_URL
    source_channel = "metropol"
    venue = "Wiener Metropol"

    def parse(self, soup: BeautifulSoup) -> list[ViennaShow]:
        shows: list[ViennaShow] = []
        for item in soup.select(".event"):
            text = item.get_text(" ", strip=True)
            if SKIP_RE.search(text):
                continue
            day = item.select_one(".schedule-day")
            month = item.select_one(".schedule-month")
            date_text = " ".join(
                part
                for part in [
                    day.get_text(" ", strip=True) if day else "",
                    month.get_text(" ", strip=True) if month else "",
                ]
                if part
            )
            title_bits = [
                el.get_text(" ", strip=True)
                for el in item.select("h2, h3, h4, strong")
                if el.get_text(" ", strip=True)
            ]
            name = title_bits[0] if title_bits else ""
            if not name:
                name = re.sub(r"^(Montag|Dienstag|Mittwoch|Donnerstag|Freitag|Samstag|Sonntag).{0,40}", "", text)
                name = re.sub(r"\s+", " ", name).strip()[:120]
            link = item.select_one("a[href]")
            img = item.select_one("img[src]")
            hall = item.select_one(".badge + br")
            venue = self.venue
            if "Großer Saal" in text:
                venue = "Wiener Metropol Großer Saal"
            elif "Studio" in text:
                venue = "Wiener Metropol Studio"
            show = self.make_show(
                name=name,
                url=(link.get("href") if link else "") or LISTING_URL,
                start=parse_listing_date(date_text or text),
                start_time=parse_start_time(text),
                venue=venue,
                image_src=img.get("src") if img else None,
                description=text[:300],
            )
            if show:
                shows.append(show)
        return shows


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--dry", action="store_true")
    args = parser.parse_args()
    MetropolScraper(dry=args.dry).scrape()
