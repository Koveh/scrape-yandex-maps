"""Scrape Wiener Symphoniker concert calendar into `concerts`."""
from __future__ import annotations

import argparse

from bs4 import BeautifulSoup

from vienna_common import HtmlVenueScraper, ViennaShow, logged, parse_iso_datetime, parse_listing_date, parse_start_time

LISTING_URL = "https://www.wienersymphoniker.at/kalender"


class WienerSymphonikerScraper(HtmlVenueScraper):
    listing_url = LISTING_URL
    source_channel = "wienersymphoniker"
    venue = "Wiener Symphoniker"
    max_pages = 8

    def parse(self, soup: BeautifulSoup) -> list[ViennaShow]:
        shows: list[ViennaShow] = []
        for item in soup.select(".s-clickable-teaser"):
            title = item.select_one(".s-clickable-teaser__link a")
            name = title.get_text(" ", strip=True) if title else ""
            href = (title.get("href") if title else "") or ""
            stamp = item.select_one("time[datetime]")
            start, start_time = parse_iso_datetime(str(stamp.get("datetime") if stamp else ""))
            if start is None:
                start = parse_listing_date(item.get_text(" ", strip=True))
                start_time = parse_start_time(item.get_text(" ", strip=True))
            hall = ""
            for line in item.select("div.s-copy-s"):
                raw = line.get_text(" ", strip=True)
                if "·" in raw or "Saal" in raw or "Center" in raw:
                    hall = raw
                    break
            img = item.select_one("img[src], img[srcset]")
            image_src = img.get("src") if img else None
            show = self.make_show(
                name=name,
                url=href or LISTING_URL,
                start=start,
                start_time=start_time or parse_start_time(item.get_text(" ", strip=True)),
                venue=hall or self.venue,
                image_src=image_src,
            )
            if show:
                shows.append(show)
        return shows

    @logged
    def scrape(self) -> None:
        shows: list[ViennaShow] = []
        seen: set[str] = set()
        for page in range(0, self.max_pages):
            url = LISTING_URL if page == 0 else f"{LISTING_URL}?page={page}"
            page_shows = self.parse(self.fetch_soup(url))
            print(f"  page={page} cards={len(page_shows)}", flush=True)
            if not page_shows:
                break
            added = 0
            for show in page_shows:
                key = f"{show.url}|{show.start}|{show.start_time}"
                if key in seen:
                    continue
                seen.add(key)
                shows.append(show)
                added += 1
            if added == 0:
                break
        self.persist_shows(shows)


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--dry", action="store_true")
    args = parser.parse_args()
    WienerSymphonikerScraper(dry=args.dry).scrape()
