"""Scrape MuseumsQuartier Wien events into `concerts` (city = Вена)."""
from __future__ import annotations

import argparse
import re
from datetime import date, time

from bs4 import BeautifulSoup
from requests import HTTPError

from vienna_common import HtmlVenueScraper, ViennaShow, logged, parse_listing_date, parse_start_time

SKIP_RE = re.compile(r"(kurzführung|mq tours|stadtführung|schulklasse)", re.I)
PATH_DATE = re.compile(r"/(\d{4})(\d{2})(\d{2})-(\d{2})(\d{2})/")


class MqwScraper(HtmlVenueScraper):
    listing_url = "https://www.mqw.at/de/programm/events/"
    source_channel = "mqw"
    venue = "MuseumsQuartier"
    max_pages = 12

    def start_from_href(self, href: str) -> tuple[date | None, time | None]:
        match = PATH_DATE.search(href or "")
        if not match:
            return None, None
        start = date(int(match.group(1)), int(match.group(2)), int(match.group(3)))
        clock = time(int(match.group(4)), int(match.group(5)))
        return start, clock

    def parse(self, soup: BeautifulSoup) -> list[ViennaShow]:
        shows: list[ViennaShow] = []
        for card in soup.select("article.card-wrapper, article.card"):
            text = re.sub(r"\s+", " ", card.get_text(" ", strip=True))
            if SKIP_RE.search(text):
                continue
            title = card.select_one("h2, h3, .card-title, .headline")
            name = title.get_text(" ", strip=True) if title else ""
            if not name:
                continue
            link = card.select_one("a[href*='/programm/events/'], a[href]")
            href = (link.get("href") if link else "") or ""
            start, clock = self.start_from_href(href)
            img = card.select_one("img[src]")
            info = card.select_one("p.card-text--info, .card-text--info")
            info_text = info.get_text(" ", strip=True) if info else ""
            place = ""
            if " Uhr " in info_text:
                place = info_text.split(" Uhr ", 1)[-1].strip()
            subtitle = card.select_one(".card-title-area")
            extra = ""
            if subtitle:
                extra = subtitle.get_text(" ", strip=True)
                if name and extra.startswith(name):
                    extra = extra[len(name) :].strip()
            show = self.make_show(
                name=name,
                url=href or self.listing_url,
                start=start or parse_listing_date(text),
                start_time=clock or parse_start_time(text),
                venue=place or self.venue,
                image_src=img.get("src") if img else None,
                description=(extra or text)[:240],
            )
            if show is not None:
                shows.append(show)
        return shows

    def page_url(self, page: int) -> str:
        if page <= 1:
            return self.listing_url
        return f"{self.listing_url}?page={page}"

    @logged
    def scrape(self) -> None:
        shows: list[ViennaShow] = []
        seen: set[str] = set()
        empty = 0
        for page in range(1, self.max_pages + 1):
            try:
                soup = self.fetch_soup(self.page_url(page))
            except HTTPError as exc:
                print(f"  page={page} stop={exc.response.status_code if exc.response else exc}", flush=True)
                break
            page_shows = self.parse(soup)
            print(f"  page={page} cards={len(page_shows)}", flush=True)
            if not page_shows:
                empty += 1
                if empty >= 2:
                    break
                continue
            empty = 0
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
    MqwScraper(dry=args.dry).scrape()
