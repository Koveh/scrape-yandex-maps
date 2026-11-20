"""Scrape Chelsea Vienna listings into `concerts` (city = Вена)."""
from __future__ import annotations

import argparse
import re

from bs4 import BeautifulSoup

from vienna_common import (
    HtmlVenueScraper,
    ViennaShow,
    day_month_date,
    german_month,
    parse_start_time,
)

LISTING_URL = "https://www.chelsea.co.at/concerts.php"
SKIP_RE = re.compile(r"\b(ausverkauft|abgesagt)\b", re.I)


class ChelseaScraper(HtmlVenueScraper):
    listing_url = LISTING_URL
    source_channel = "chelsea"
    venue = "Chelsea"

    def parse(self, soup: BeautifulSoup) -> list[ViennaShow]:
        shows: list[ViennaShow] = []
        seen: set[str] = set()
        for table in soup.select("table"):
            rows = table.select("tr")
            if len(rows) < 2:
                continue
            header = rows[0].get_text(" ", strip=True)
            months = re.findall(r"([A-Za-zÄäÖöÜüß]+)\s+(20\d{2})", header)
            if not months:
                continue
            left_month, left_year = months[0]
            right_month, right_year = months[1] if len(months) > 1 else months[0]
            columns = (
                (0, 1, german_month(left_month), int(left_year)),
                (2, 3, german_month(right_month), int(right_year)),
            )
            for row in rows[1:]:
                cells = row.find_all(["td", "th"])
                for day_i, name_i, month, year in columns:
                    if month is None or name_i >= len(cells):
                        continue
                    name_cell = cells[name_i]
                    link = name_cell.select_one("a[href]")
                    name = (link.get_text(" ", strip=True) if link else name_cell.get_text(" ", strip=True))
                    if not name or SKIP_RE.search(name):
                        continue
                    day_text = cells[day_i].get_text(" ", strip=True) if day_i < len(cells) else ""
                    day_match = re.search(r"(\d{1,2})", day_text)
                    if not day_match:
                        continue
                    href = (link.get("href") if link else "") or f"{LISTING_URL}#concert_{day_match.group(1)}"
                    if href.startswith("#"):
                        href = LISTING_URL + href
                    start = day_month_date(int(day_match.group(1)), month, year)
                    show = self.make_show(
                        name=name,
                        url=href,
                        start=start,
                        start_time=parse_start_time(name_cell.get_text(" ", strip=True)),
                    )
                    if show is None or show.url in seen:
                        continue
                    seen.add(show.url)
                    shows.append(show)
        return shows


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--dry", action="store_true")
    args = parser.parse_args()
    ChelseaScraper(dry=args.dry).scrape()
