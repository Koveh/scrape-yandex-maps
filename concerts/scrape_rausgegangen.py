"""Scrape rausgegangen.de Vienna listings into `concerts`."""
from __future__ import annotations

import argparse
from urllib.parse import urljoin

from bs4 import BeautifulSoup
from bs4.element import Tag

from vienna_common import (
    HtmlVenueScraper,
    ViennaShow,
    logged,
    parse_listing_date,
    parse_price,
    parse_start_time,
    strip_html,
)

LISTINGS = (
    "https://rausgegangen.de/wien/",
    "https://rausgegangen.de/wien/kategorie/konzerte-und-musik/",
    "https://rausgegangen.de/wien/kategorie/theater/",
    "https://rausgegangen.de/wien/kategorie/shows-und-performances/",
    "https://rausgegangen.de/wien/kategorie/gesprochenes/",
    "https://rausgegangen.de/wien/kategorie/feste-und-festival/",
    "https://rausgegangen.de/wien/kategorie/ausstellung/",
    "https://rausgegangen.de/wien/kategorie/party/",
    "https://rausgegangen.de/wien/kategorie/film/",
    "https://rausgegangen.de/wien/kategorie/food-und-drinks/",
    "https://rausgegangen.de/wien/kategorie/kinder-und-familien/",
)


class RausgegangenWienScraper(HtmlVenueScraper):
    listing_url = LISTINGS[0]
    source_channel = "rausgegangen"
    venue = "Wien"

    def parse_tile(self, link: Tag) -> ViennaShow | None:
        href = link.get("href") or ""
        if "/events/" not in href:
            return None
        url = urljoin(self.listing_url, href)
        img = link.select_one("img")
        title = link.select_one("span.h5")
        name = strip_html(title.get_text(" ", strip=True) if title else "")
        if not name and img:
            name = strip_html(str(img.get("alt") or ""))
        if not name:
            return None
        text = link.get_text(" ", strip=True)
        place = link.select_one("p.text-sm.opacity-70")
        venue = strip_html(place.get_text(" ", strip=True) if place else "") or self.venue
        image_src = img.get("src") if img else None
        price_from, price_to = parse_price(text)
        return self.make_show(
            name=name,
            url=url,
            start=parse_listing_date(text),
            start_time=parse_start_time(text),
            venue=venue[:120],
            image_src=image_src if image_src and str(image_src).startswith("http") else None,
            price_from=price_from,
            price_to=price_to,
        )

    def parse(self, soup: BeautifulSoup) -> list[ViennaShow]:
        shows: list[ViennaShow] = []
        seen: set[str] = set()
        for link in soup.select('a[href*="/events/"]'):
            show = self.parse_tile(link)
            if show is None or show.url in seen:
                continue
            seen.add(show.url)
            shows.append(show)
        return shows

    @logged
    def scrape(self) -> None:
        shows: list[ViennaShow] = []
        seen: set[str] = set()
        for listing in LISTINGS:
            for page in range(1, 8):
                url = listing if page == 1 else f"{listing}{'&' if '?' in listing else '?'}page={page}"
                soup = self.fetch_soup(url)
                page_shows = self.parse(soup)
                print(f"  {url} cards={len(page_shows)}", flush=True)
                if not page_shows:
                    break
                added = 0
                for show in page_shows:
                    if show.url in seen:
                        continue
                    seen.add(show.url)
                    shows.append(show)
                    added += 1
                if added == 0:
                    break
        print(f"cards={len(shows)}", flush=True)
        self.store.persist(shows)


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--dry", action="store_true")
    args = parser.parse_args()
    RausgegangenWienScraper(dry=args.dry).scrape()
