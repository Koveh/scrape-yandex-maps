"""Scrape rausgegangen.de Munich listings into `concerts`."""
from __future__ import annotations

import argparse

from scrape_rausgegangen import RausgegangenWienScraper
from vienna_common import MUNICH_CITY, logged

LISTINGS = (
    "https://rausgegangen.de/muenchen/",
    "https://rausgegangen.de/muenchen/kategorie/konzerte-und-musik/",
    "https://rausgegangen.de/muenchen/kategorie/theater/",
    "https://rausgegangen.de/muenchen/kategorie/shows-und-performances/",
    "https://rausgegangen.de/muenchen/kategorie/gesprochenes/",
    "https://rausgegangen.de/muenchen/kategorie/feste-und-festival/",
    "https://rausgegangen.de/muenchen/kategorie/ausstellung/",
    "https://rausgegangen.de/muenchen/kategorie/party/",
    "https://rausgegangen.de/muenchen/kategorie/film/",
    "https://rausgegangen.de/muenchen/kategorie/food-und-drinks/",
    "https://rausgegangen.de/muenchen/kategorie/kinder-und-familien/",
)


class RausgegangenMunichScraper(RausgegangenWienScraper):
    city = MUNICH_CITY
    listing_url = LISTINGS[0]
    source_channel = "rausgegangen_munich"
    venue = "München"

    @logged
    def scrape(self) -> None:
        listings = LISTINGS
        shows = []
        seen: set[str] = set()
        for listing in listings:
            for page in range(1, 8):
                url = listing if page == 1 else f"{listing}{'&' if '?' in listing else '?'}page={page}"
                soup = self.fetch_soup(url)
                page_shows = self.parse(soup)
                print(f"  {url} cards={len(page_shows)}", flush=True)
                if not page_shows:
                    break
                added = 0
                for show in page_shows:
                    if show.url in seen:
                        continue
                    seen.add(show.url)
                    shows.append(show)
                    added += 1
                if added == 0:
                    break
        print(f"cards={len(shows)}", flush=True)
        self.store.persist(shows)


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--dry", action="store_true")
    args = parser.parse_args()
    RausgegangenMunichScraper(dry=args.dry).scrape()
