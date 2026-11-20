"""Scrape Stadtsaal monthly spielplan into `concerts`."""
from __future__ import annotations

import argparse
import re
from datetime import date

from vienna_common import HtmlVenueScraper, ViennaShow, logged, parse_listing_date, parse_start_time

SKIP_RE = re.compile(r"\b(kein spielbetrieb|sommerpause|abgesagt)\b", re.I)


class StadtsaalScraper(HtmlVenueScraper):
    listing_url = "https://stadtsaal.com/spielplan"
    source_channel = "stadtsaal"
    venue = "Stadtsaal"

    def month_urls(self) -> list[str]:
        today = date.today()
        urls: list[str] = []
        year, month = today.year, today.month
        for _ in range(8):
            urls.append(f"{self.listing_url}/{month:02d}/{year}")
            if month == 12:
                month = 1
                year += 1
            else:
                month += 1
        return urls

    def parse(self, soup, year: int | None = None) -> list[ViennaShow]:
        shows: list[ViennaShow] = []
        seen: set[str] = set()
        for row in soup.select(".eventrow"):
            text = re.sub(r"\s+", " ", row.get_text(" ", strip=True))
            if not text or SKIP_RE.search(text):
                continue
            artist = row.select_one(".artistname")
            event = row.select_one(".eventname")
            name = " – ".join(
                part
                for part in (
                    artist.get_text(" ", strip=True) if artist else "",
                    event.get_text(" ", strip=True) if event else "",
                )
                if part
            )
            if not name:
                continue
            img = row.select_one("img[src]")
            day = row.select_one(".month")
            day_text = day.get_text(" ", strip=True) if day else ""
            start = parse_listing_date(f"{day_text}{year}" if year and day_text else text)
            href = f"{self.listing_url}#{day_text or name}"
            show = self.make_show(
                name=name,
                url=href,
                start=start,
                start_time=parse_start_time(text),
                image_src=(
                    f"https://stadtsaal.com{img.get('src')}"
                    if img and str(img.get("src") or "").startswith("/")
                    else (img.get("src") if img else None)
                ),
            )
            if show is None:
                continue
            key = f"{show.start}:{show.start_time}:{show.name.lower()}"
            if key in seen:
                continue
            seen.add(key)
            shows.append(show)
        return shows

    @logged
    def scrape(self) -> None:
        shows: list[ViennaShow] = []
        seen: set[str] = set()
        for url in self.month_urls():
            year = int(url.rstrip("/").split("/")[-1])
            page_shows = self.parse(self.fetch_soup(url), year=year)
            print(f"  {url} cards={len(page_shows)}", flush=True)
            for show in page_shows:
                key = f"{show.start}:{show.start_time}:{show.name.lower()}"
                if key in seen:
                    continue
                seen.add(key)
                shows.append(show)
        print(f"cards={len(shows)}", flush=True)
        self.store.persist(shows)


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--dry", action="store_true")
    args = parser.parse_args()
    StadtsaalScraper(dry=args.dry).scrape()
