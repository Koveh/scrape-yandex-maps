"""Rausgegangen location feeds for Munich halls, clubs, and theatres."""
from __future__ import annotations

import argparse

from scrape_rausgegangen import RausgegangenWienScraper
from vienna_common import MUNICH_CITY, ViennaShow

LOCATIONS = (
    ("zenith", "https://rausgegangen.de/locations/zenith/", "Zenith"),
    ("circuskron_rg", "https://rausgegangen.de/locations/circus-krone/", "Circus Krone"),
    ("substanz_rg", "https://rausgegangen.de/locations/substanz/", "Substanz"),
    ("kammerspiele_rg", "https://rausgegangen.de/locations/muenchner-kammerspiele/", "Kammerspiele"),
    ("residenztheater_rg", "https://rausgegangen.de/locations/residenztheater/", "Residenztheater"),
    ("volkstheater_muc_rg", "https://rausgegangen.de/locations/volkstheater/", "Volkstheater"),
    ("olympiahalle", "https://rausgegangen.de/locations/olympiahalle/", "Olympiahalle"),
    ("isarphilharmonie", "https://rausgegangen.de/locations/isarphilharmonie/", "Isarphilharmonie"),
    ("herkulessaal", "https://rausgegangen.de/locations/herkulessaal/", "Herkulessaal"),
    ("milla", "https://rausgegangen.de/locations/milla/", "Milla"),
    ("prinzregententheater", "https://rausgegangen.de/locations/prinzregententheater/", "Prinzregententheater"),
    ("bar089", "https://rausgegangen.de/locations/089-bar/", "089"),
    ("harryklein", "https://rausgegangen.de/locations/harry-klein/", "Harry Klein"),
    ("blitzclub", "https://rausgegangen.de/locations/blitz-club/", "BLITZ"),
    ("cordclub", "https://rausgegangen.de/locations/cord-club/", "Cord"),
    ("callmedrella", "https://rausgegangen.de/locations/call-me-drella/", "Drella"),
    ("neuraum", "https://rausgegangen.de/locations/neuraum/", "Neuraum"),
    ("bmwwelt", "https://rausgegangen.de/locations/bmw-welt/", "BMW Welt"),
    ("tollwood", "https://rausgegangen.de/locations/tollwood-festival/", "Tollwood"),
)


class MunichLocationScraper(RausgegangenWienScraper):
    city = MUNICH_CITY

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
        MunichLocationScraper(source, url, venue, dry=args.dry).scrape()
