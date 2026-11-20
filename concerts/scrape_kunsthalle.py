"""Scrape Kunsthalle Wien program into `concerts` (city = Вена)."""
from __future__ import annotations

import argparse
import re

from bs4 import BeautifulSoup

from vienna_common import HtmlVenueScraper, ViennaShow, parse_listing_date, parse_start_time

SKIP_RE = re.compile(
    r"(artist consultation|qma artist|freier sonntag|geschlossen)",
    re.I,
)


class KunsthalleScraper(HtmlVenueScraper):
    listing_url = "https://kunsthallewien.at/programm"
    source_channel = "kunsthalle"
    venue = "Kunsthalle Wien"

    def parse(self, soup: BeautifulSoup) -> list[ViennaShow]:
        shows: list[ViennaShow] = []
        for row in soup.select("article.event-table-row, article.event"):
            text = re.sub(r"\s+", " ", row.get_text(" ", strip=True))
            if SKIP_RE.search(text):
                continue
            title = row.select_one("h2, h3, .event-title, .card-title")
            name = title.get_text(" ", strip=True) if title else ""
            if not name:
                continue
            link = row.select_one("a[href*='veranstaltung'], a[href]")
            href = (link.get("href") if link else "") or ""
            image_src = None
            for node in row.select("source[data-srcset], img[data-src], img[src]"):
                raw = node.get("data-srcset") or node.get("data-src") or node.get("src") or ""
                first = raw.split(",")[0].strip().split(" ")[0]
                if first.startswith("/") or first.startswith("http"):
                    image_src = first
                    break
            show = self.make_show(
                name=name,
                url=href or self.listing_url,
                start=parse_listing_date(text),
                start_time=parse_start_time(text),
                image_src=image_src,
                description=text[:240],
            )
            if show is not None:
                shows.append(show)
        return shows


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--dry", action="store_true")
    args = parser.parse_args()
    KunsthalleScraper(dry=args.dry).scrape()
