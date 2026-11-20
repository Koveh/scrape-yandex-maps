"""Scrape Wiener Konzerthaus listings into `concerts`."""
from __future__ import annotations

import argparse
import re

from vienna_common import HtmlVenueScraper, ViennaShow, logged, parse_listing_date, parse_start_time

SKIP_RE = re.compile(r"\b(abgesagt|cancelled|backstage führung|führung in)\b", re.I)


class KonzerthausScraper(HtmlVenueScraper):
    listing_url = "https://konzerthaus.at/de/programm-und-karten"
    source_channel = "konzerthaus"
    venue = "Wiener Konzerthaus"

    def parse(self, soup) -> list[ViennaShow]:
        shows: list[ViennaShow] = []
        seen: set[str] = set()
        for item in soup.select(".event-item"):
            text = re.sub(r"\s+", " ", item.get_text(" ", strip=True))
            if SKIP_RE.search(text):
                continue
            link = item.select_one("a.event-item__link[href]")
            title = item.select_one(".event-item__title")
            desc = item.select_one(".event-item__description")
            hall = ""
            for span in item.select(".text-body-small"):
                raw = span.get_text(" ", strip=True)
                if "Saal" in raw or "saal" in raw:
                    hall = raw.replace("∙", "").strip()
            name = (title.get_text(" ", strip=True) if title else "")
            subtitle = desc.get_text(" ", strip=True) if desc else ""
            if subtitle and subtitle not in name:
                name = f"{name} — {subtitle}".strip(" —")
            show = self.make_show(
                name=name,
                url=(link.get("href") if link else "") or self.listing_url,
                start=parse_listing_date(text),
                start_time=parse_start_time(text),
                venue=hall or self.venue,
            )
            if show is None or show.url in seen:
                continue
            seen.add(show.url)
            shows.append(show)
        return shows

    @logged
    def scrape(self) -> None:
        shows: list[ViennaShow] = []
        seen: set[str] = set()
        for page in range(1, 16):
            soup = self.fetch_soup(f"{self.listing_url}?page={page}")
            page_shows = self.parse(soup)
            print(f"  page={page} cards={len(page_shows)}", flush=True)
            if not page_shows:
                break
            for show in page_shows:
                if show.url in seen:
                    continue
                seen.add(show.url)
                shows.append(show)
        print(f"cards={len(shows)}", flush=True)
        self.store.persist(shows)


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--dry", action="store_true")
    args = parser.parse_args()
    KonzerthausScraper(dry=args.dry).scrape()
