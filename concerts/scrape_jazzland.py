"""Scrape Jazzland Wien via rausgegangen.de location feed into `concerts`."""
from __future__ import annotations

import argparse

from requests import HTTPError

from scrape_rausgegangen import RausgegangenWienScraper


class JazzlandScraper(RausgegangenWienScraper):
    listing_url = "https://rausgegangen.de/locations/jazzland/"
    source_channel = "jazzland"
    venue = "Jazzland"

    def scrape(self) -> None:
        self.listing_url = type(self).listing_url
        try:
            soup = self.fetch_soup()
        except HTTPError as exc:
            print(f"skip jazzland {exc}", flush=True)
            return
        self.persist_shows(self.parse(soup))


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--dry", action="store_true")
    args = parser.parse_args()
    JazzlandScraper(dry=args.dry).scrape()
