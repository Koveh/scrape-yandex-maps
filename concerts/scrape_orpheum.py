"""Scrape Orpheum Vienna into `concerts` (city = Вена)."""
from __future__ import annotations

import argparse
import re
from datetime import date

from bs4 import BeautifulSoup

from vienna_common import (
    HtmlVenueScraper,
    ViennaShow,
    german_month,
    parse_listing_date,
    parse_price,
    parse_start_time,
)

LISTING_URL = "https://orpheum.at/programm/"
SKIP_RE = re.compile(r"\b(kassa|kartenkassa|geöffnet|geschlossen|abgesagt)\b", re.I)


class OrpheumScraper(HtmlVenueScraper):
    listing_url = LISTING_URL
    source_channel = "orpheum"
    venue = "Orpheum Wien"

    def month_urls(self) -> list[str]:
        today = date.today()
        urls = [LISTING_URL]
        year, month = today.year, today.month
        for _ in range(8):
            urls.append(f"{LISTING_URL}?monat={month}&y={year}")
            month += 1
            if month > 12:
                month = 1
                year += 1
        return list(dict.fromkeys(urls))

    def product_by_date(self, soup: BeautifulSoup) -> dict[str, str]:
        found: dict[str, str] = {}
        for link in soup.select('a[href*="/produkt/"]'):
            href = link.get("href") or ""
            match = re.search(r"(\d{2})-(\d{2})-(20\d{2})", href)
            if match:
                found[f"{match.group(3)}-{match.group(2)}-{match.group(1)}"] = href
        return found

    def parse(self, soup: BeautifulSoup) -> list[ViennaShow]:
        products = self.product_by_date(soup)
        year_match = re.search(r"y=(\d{4})", getattr(self, "active_url", "") or "")
        year = int(year_match.group(1)) if year_match else date.today().year
        shows: list[ViennaShow] = []
        for item in soup.select(".event-item"):
            text = re.sub(r"\s+", " ", item.get_text(" ", strip=True))
            if SKIP_RE.search(text):
                continue
            name = ""
            for heading in item.select("p.h4.fw-bold, p.h3"):
                candidate = heading.get_text(" ", strip=True)
                if candidate and not re.fullmatch(r"\d{1,2}\s+[A-Za-zÄäÖöÜüß]+", candidate):
                    name = candidate
                    break
            if not name:
                continue
            start = parse_listing_date(f"{text} {year}")
            if start is None:
                day_month = re.search(r"(\d{1,2})\s+([A-Za-zÄäÖöÜüß]{3})", text)
                if day_month:
                    month = german_month(day_month.group(2))
                    if month:
                        start = date(year, month, int(day_month.group(1)))
            key = start.isoformat() if start else ""
            href = products.get(key, "") or LISTING_URL
            img = item.select_one("img[src]")
            price_from, price_to = parse_price(text)
            show = self.make_show(
                name=name,
                url=href,
                start=start,
                start_time=parse_start_time(text),
                image_src=img.get("src") if img else None,
                price_from=price_from,
                price_to=price_to,
            )
            if show:
                shows.append(show)
        return shows

    def scrape(self) -> None:
        shows: list[ViennaShow] = []
        for url in self.month_urls():
            shows.extend(self.parse(self.fetch_soup(url)))
        self.persist_shows(shows)


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--dry", action="store_true")
    args = parser.parse_args()
    OrpheumScraper(dry=args.dry).scrape()
