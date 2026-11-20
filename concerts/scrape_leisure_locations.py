"""Rausgegangen location feeds for palace/hotel-adjacent and museum leisure."""
from __future__ import annotations

import argparse

from scrape_rausgegangen import RausgegangenWienScraper
from vienna_common import ViennaShow

LOCATIONS = (
    ("palaisauersperg", "https://rausgegangen.de/locations/palais-auersperg/", "Palais Auersperg"),
    ("albertina", "https://rausgegangen.de/locations/albertina/", "Albertina"),
    ("albertinamodern", "https://rausgegangen.de/locations/albertina-modern/", "Albertina Modern"),
    ("secession", "https://rausgegangen.de/locations/secession/", "Secession"),
    ("leopoldmuseum", "https://rausgegangen.de/locations/leopold-museum/", "Leopold Museum"),
    ("clubu", "https://rausgegangen.de/locations/club-u/", "Club U"),
    ("stadtkino", "https://rausgegangen.de/locations/stadtkino-wien/", "Stadtkino"),
)


class LeisureLocationScraper(RausgegangenWienScraper):
    def __init__(self, source: str, url: str, venue: str, dry: bool = False) -> None:
        self.listing_url = url
        self.source_channel = source
        self.venue = venue
        super().__init__(dry=dry)

    def belongs_here(self, show: ViennaShow) -> bool:
        needle = self.venue.lower()
        place = (show.venue or "").lower()
        return needle in place or place in needle

    def scrape(self) -> None:
        shows = [show for show in self.parse(self.fetch_soup(self.listing_url)) if self.belongs_here(show)]
        self.persist_shows(shows)


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--dry", action="store_true")
    args = parser.parse_args()
    for source, url, venue in LOCATIONS:
        LeisureLocationScraper(source, url, venue, dry=args.dry).scrape()
