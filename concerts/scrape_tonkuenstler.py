"""Scrape Tonkünstler-Orchester NÖ concerts into `concerts`."""
from __future__ import annotations

import argparse

from noeku import NoekuScraper
from vienna_common import NOE_CITY


class TonkuenstlerScraper(NoekuScraper):
    city = NOE_CITY
    listing_url = "https://www.tonkuenstler.at/de/konzerte"
    source_channel = "tonkuenstler"
    venue = "Tonkünstler-Orchester"


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--dry", action="store_true")
    args = parser.parse_args()
    TonkuenstlerScraper(dry=args.dry).scrape()
