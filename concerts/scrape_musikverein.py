"""Scrape Musikverein Wien WP `konzerte` into `concerts`."""
from __future__ import annotations

import argparse
from html import unescape

from bs4 import BeautifulSoup

from vienna_common import HtmlVenueScraper, ViennaShow, logged, parse_listing_date, parse_start_time, strip_html

LISTING_URL = "https://musikverein.at/wp-json/wp/v2/konzerte?per_page=100"


class MusikvereinScraper(HtmlVenueScraper):
    listing_url = LISTING_URL
    source_channel = "musikverein"
    venue = "Musikverein"

    def hall_name(self, text: str) -> str:
        for token in ("Großer Saal", "Gläserner Saal", "Brahms-Saal", "Magna Auditorium", "Metallener Saal"):
            if token.lower() in text.lower():
                return token
        return self.venue

    def parse_payload(self, payload: list) -> list[ViennaShow]:
        shows: list[ViennaShow] = []
        for item in payload:
            if not isinstance(item, dict):
                continue
            name = unescape(strip_html(str((item.get("title") or {}).get("rendered") or "")))
            if name.lower() in {"copy this", "template"}:
                continue
            html = str((item.get("content") or {}).get("rendered") or "")
            text = BeautifulSoup(html, "html.parser").get_text(" ", strip=True)
            url = str(item.get("link") or LISTING_URL)
            show = self.make_show(
                name=name,
                url=url,
                start=parse_listing_date(text),
                start_time=parse_start_time(text),
                venue=self.hall_name(text),
                description=text[:400],
            )
            if show:
                shows.append(show)
        return shows

    @logged
    def scrape(self) -> None:
        payload = self.fetch_json()
        shows = self.parse_payload(payload if isinstance(payload, list) else [])
        self.persist_shows(shows)


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--dry", action="store_true")
    args = parser.parse_args()
    MusikvereinScraper(dry=args.dry).scrape()
