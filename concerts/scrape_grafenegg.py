"""Scrape Grafenegg festival calendar into `concerts` (city = Нижняя Австрия)."""
from __future__ import annotations

import argparse

from noeku import NoekuScraper
from vienna_common import NOE_CITY


class GrafeneggScraper(NoekuScraper):
    city = NOE_CITY
    listing_url = "https://www.grafenegg.com/de/programm-karten"
    source_channel = "grafenegg"
    venue = "Grafenegg"


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--dry", action="store_true")
    args = parser.parse_args()
    GrafeneggScraper(dry=args.dry).scrape()
