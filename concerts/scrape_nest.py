"""Scrape NEST (Staatsoper studio stage) calendar into `concerts`."""
from __future__ import annotations

import argparse

from scrape_staatsoper import MONTHS, StaatsoperScraper


class NestScraper(StaatsoperScraper):
    listing_url = "https://www.nest.at/kalender/"
    source_channel = "nest"
    venue = "NEST"

    def scrape(self) -> None:
        from datetime import date

        from bs4 import BeautifulSoup

        today = date.today()
        shows = []
        seen: set[str] = set()
        for offset in range(0, 8):
            month = today.month + offset
            year = today.year + (month - 1) // 12
            month = (month - 1) % 12 + 1
            slug = MONTHS[month - 1]
            url = f"https://www.nest.at/kalender/{year}/{slug}/"
            response = self.store.session.get(url, timeout=90)
            if response.status_code == 404:
                print(f"  {year}-{month:02d} skip 404", flush=True)
                continue
            response.raise_for_status()
            soup = BeautifulSoup(response.content.decode("utf-8", errors="replace"), "html.parser")
            page_shows = self.parse(soup)
            print(f"  {year}-{month:02d} cards={len(page_shows)}", flush=True)
            for show in page_shows:
                key = f"{show.url}|{show.start}"
                if key in seen:
                    continue
                seen.add(key)
                shows.append(show)
        print(f"cards={len(shows)}", flush=True)
        self.store.persist(shows)


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--dry", action="store_true")
    args = parser.parse_args()
    NestScraper(dry=args.dry).scrape()
