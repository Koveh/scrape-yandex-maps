"""Scrape Bühne Baden calendar into `concerts` (city = Нижняя Австрия)."""
from __future__ import annotations

import argparse

from noeku import NoekuScraper
from vienna_common import NOE_CITY


class BuehneBadenScraper(NoekuScraper):
    city = NOE_CITY
    listing_url = "https://www.buehnebaden.at/de/kalender"
    source_channel = "buehnebaden"
    venue = "Bühne Baden"


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--dry", action="store_true")
    args = parser.parse_args()
    BuehneBadenScraper(dry=args.dry).scrape()
