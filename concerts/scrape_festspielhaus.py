"""Scrape Festspielhaus St. Pölten into `concerts` (city = Нижняя Австрия)."""
from __future__ import annotations

import argparse

from noeku import NoekuScraper
from vienna_common import NOE_CITY


class FestspielhausScraper(NoekuScraper):
    city = NOE_CITY
    listing_url = "https://www.festspielhaus.at/de/programm"
    source_channel = "festspielhaus"
    venue = "Festspielhaus St. Pölten"


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--dry", action="store_true")
    args = parser.parse_args()
    FestspielhausScraper(dry=args.dry).scrape()
