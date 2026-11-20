"""Scrape Landestheater Niederösterreich into `concerts`."""
from __future__ import annotations

import argparse

from noeku import NoekuScraper
from vienna_common import NOE_CITY


class LandestheaterScraper(NoekuScraper):
    city = NOE_CITY
    listing_url = "https://www.landestheater.net/de/spielplan"
    source_channel = "landestheater"
    venue = "Landestheater Niederösterreich"


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--dry", action="store_true")
    args = parser.parse_args()
    LandestheaterScraper(dry=args.dry).scrape()
