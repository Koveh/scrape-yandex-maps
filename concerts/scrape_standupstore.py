"""StandUp Store Moscow schedule -> concerts (city = Москва, status kept)."""
from __future__ import annotations

import argparse
import re

from bs4 import BeautifulSoup

from moscow_common import MOSCOW_CITY, parse_ru_date, parse_ru_price, parse_ru_time
from vienna_common import HtmlVenueScraper, ViennaShow

LISTING_URL = "https://standupstore.ru/"
EVENT_HREF = re.compile(r"^/events/[^/]+/?$")
SLUG_DATE = re.compile(
    r"(\d{1,2})-(yanvarya|fevralya|marta|aprelya|maya|iyunya|iyulya|avgusta|"
    r"sentyabrya|oktyabrya|noyabrya|dekabrya)-(\d{4})",
    re.I,
)
SLUG_MONTH = {
    "yanvarya": 1,
    "fevralya": 2,
    "marta": 3,
    "aprelya": 4,
    "maya": 5,
    "iyunya": 6,
    "iyulya": 7,
    "avgusta": 8,
    "sentyabrya": 9,
    "oktyabrya": 10,
    "noyabrya": 11,
    "dekabrya": 12,
}
SLUG_TIME = re.compile(r"v-(\d{1,2})-(\d{2})", re.I)


class StandUpStoreScraper(HtmlVenueScraper):
    city = MOSCOW_CITY
    listing_url = LISTING_URL
    source_channel = "standupstore"
    venue = "StandUp Store"

    def parse(self, soup: BeautifulSoup) -> list[ViennaShow]:
        shows: list[ViennaShow] = []
        seen: set[str] = set()
        for link in soup.select('a[href*="/events/"]'):
            href = (link.get("href") or "").strip()
            if not EVENT_HREF.match(href):
                continue
            if href in seen:
                continue
            seen.add(href)
            text = link.get_text(" ", strip=True)
            name = self._name_from_slug(href, text)
            start = self._date_from_slug(href) or parse_ru_date(text)
            start_time = self._time_from_slug(href) or parse_ru_time(text)
            price_from, price_to = parse_ru_price(text)
            img = link.select_one("img[src], img[data-src]")
            if img is None and link.parent:
                img = link.parent.select_one("img[src], img[data-src]")
            image_src = None
            if img:
                image_src = img.get("src") or img.get("data-src")
            show = self.make_show(
                name=name,
                url=href,
                start=start,
                start_time=start_time,
                venue=self.venue,
                image_src=image_src,
                description=text[:500],
                price_from=price_from,
                price_to=price_to,
            )
            if show:
                shows.append(show)
        return shows

    def _name_from_slug(self, href: str, text: str) -> str:
        chunks = [re.sub(r"\s+", " ", part).strip() for part in re.split(r"\s{2,}|\n", text) if part.strip()]
        if not chunks:
            chunks = [re.sub(r"\s+", " ", text).strip()]
        skip = ("места", "есть", "₽", "пятниц", "суббот", "воскресен", "понедельник", "вторник", "сред", "четверг")
        for clean in chunks:
            low = clean.lower()
            if len(clean) < 3 or re.match(r"^\d", clean):
                continue
            if any(token in low for token in skip):
                continue
            if parse_ru_date(clean) and len(clean) < 28:
                continue
            if "₽" in clean:
                continue
            return clean[:160]
        slug = href.strip("/").split("/")[-1]
        slug = re.sub(r"-\d{1,2}-[a-z]+-\d{4}.*$", "", slug, flags=re.I)
        slug = re.sub(r"-v-\d{1,2}-\d{2}$", "", slug, flags=re.I)
        return slug.replace("-", " ").strip().title()[:160] or "StandUp Store"

    def _date_from_slug(self, href: str):
        match = SLUG_DATE.search(href)
        if not match:
            return None
        from datetime import date

        day = int(match.group(1))
        month = SLUG_MONTH[match.group(2).lower()]
        year = int(match.group(3))
        try:
            return date(year, month, day)
        except ValueError:
            return None

    def _time_from_slug(self, href: str):
        match = SLUG_TIME.search(href)
        if not match:
            return None
        from datetime import time

        return time(int(match.group(1)), int(match.group(2)))


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--dry", action="store_true")
    args = parser.parse_args()
    StandUpStoreScraper(dry=args.dry).scrape()
