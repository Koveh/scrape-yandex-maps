"""Scrape Prater Dome club nights into `concerts` (city = Вена)."""
from __future__ import annotations

import argparse
import re
from datetime import date
from urllib.parse import urljoin

from bs4 import BeautifulSoup

from vienna_common import HtmlVenueScraper, ViennaShow, parse_listing_date

SLUG_DATE = re.compile(r"(\d{2})-(\d{2})-(20\d{2})")


class PraterDomeScraper(HtmlVenueScraper):
    listing_url = "https://praterdome.at/en/events"
    source_channel = "praterdome"
    venue = "Prater Dome"

    def start_from_href(self, href: str) -> date | None:
        match = SLUG_DATE.search(href or "")
        if not match:
            return parse_listing_date(href)
        return date(int(match.group(3)), int(match.group(2)), int(match.group(1)))

    def parse(self, soup: BeautifulSoup) -> list[ViennaShow]:
        shows: list[ViennaShow] = []
        seen: set[str] = set()
        for card in soup.select("a[href*='/events/']"):
            href = card.get("href") or ""
            if any(href.endswith(suffix) for suffix in ("#tickets", "#lounges")):
                continue
            path = href.split("#")[0]
            if path.rstrip("/").endswith("/events") or path in seen:
                continue
            name = re.sub(r"\s+", " ", card.get_text(" ", strip=True))
            if not name or name.lower() in {"tickets", "vip upgrade"}:
                continue
            seen.add(path)
            url = urljoin(self.listing_url, path)
            img = card.select_one("img[src]")
            show = self.make_show(
                name=name,
                url=url,
                start=self.start_from_href(path),
                image_src=img.get("src") if img else None,
            )
            if show is not None:
                shows.append(show)
        return shows


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--dry", action="store_true")
    args = parser.parse_args()
    PraterDomeScraper(dry=args.dry).scrape()
