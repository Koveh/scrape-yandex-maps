"""Scrape VBW / musicalvienna.at Spielplan (Ronacher, Raimund) into `concerts`."""
from __future__ import annotations

import argparse
import re

from bs4 import BeautifulSoup

from datetime import date

from vienna_common import HtmlVenueScraper, ViennaShow, parse_listing_date, parse_start_time

LISTING_URL = "https://www.musicalvienna.at/de/spielplan"
SKIP_RE = re.compile(r"gutschein|archiv|zum spielplan", re.I)


class MusicalViennaScraper(HtmlVenueScraper):
    listing_url = LISTING_URL
    source_channel = "musicalvienna"
    venue = "Vereinigte Bühnen Wien"

    def parse(self, soup: BeautifulSoup) -> list[ViennaShow]:
        shows: list[ViennaShow] = []
        for item in soup.select(".eventItem"):
            text = item.get_text(" ", strip=True)
            if SKIP_RE.search(text):
                continue
            link = item.select_one("a[href*='/de/spielplan/']")
            href = (link.get("href") if link else "") or LISTING_URL
            if "/archiv" in href or "/gutscheine" in href or href.rstrip("/").endswith("/spielplan"):
                continue
            name = re.sub(r"\s+", " ", text)
            name = re.split(r"\d{2}\.\d{2}\.\d{4}", name, maxsplit=1)[0]
            name = re.sub(r"^(Ronacher|Raimund Theater|Raimund|Theater an der Wien)\s+", "", name).strip()
            name = name.replace("Mehr Info", "").strip(" -–")
            hall = "Ronacher" if "ronacher" in text.lower() else (
                "Raimund Theater" if "raimund" in text.lower() else self.venue
            )
            dates = re.findall(r"(\d{1,2}\.\d{1,2}\.\d{4})", text)
            start = parse_listing_date(dates[0]) if dates else parse_listing_date(text)
            end = parse_listing_date(dates[-1]) if len(dates) > 1 else start
            if start and start < date.today() and end and end >= date.today():
                start = date.today()
            show = self.make_show(
                name=name or (link.get_text(" ", strip=True) if link else hall),
                url=href,
                start=start,
                start_time=parse_start_time(text),
                venue=hall,
            )
            if show:
                shows.append(show)
        return shows


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--dry", action="store_true")
    args = parser.parse_args()
    MusicalViennaScraper(dry=args.dry).scrape()
