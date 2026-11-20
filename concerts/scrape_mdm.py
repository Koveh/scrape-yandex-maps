"""МДМ (Московский дворец молодёжи) afisha -> concerts (Москва, kept)."""
from __future__ import annotations

import argparse
import re

from bs4 import BeautifulSoup

from moscow_common import MOSCOW_CITY, parse_ru_date, parse_ru_time
from vienna_common import HtmlVenueScraper, ViennaShow

LISTING_URL = "https://mdmpalace.ru/afisha/"
MONTH_FIX = {
    "января": "января",
    "февраля": "февраля",
    "марта": "марта",
    "апреля": "апреля",
    "мая": "мая",
    "июня": "июня",
    "июля": "июля",
    "августа": "августа",
    "сентября": "сентября",
    "октября": "октября",
    "ноября": "ноября",
    "декабря": "декабря",
}


class MdmScraper(HtmlVenueScraper):
    city = MOSCOW_CITY
    listing_url = LISTING_URL
    source_channel = "mdm"
    venue = "МДМ"

    def parse(self, soup: BeautifulSoup) -> list[ViennaShow]:
        shows: list[ViennaShow] = []
        for item in soup.select(".afisha__item__wrap"):
            text = item.get_text(" ", strip=True)
            name_node = item.select_one(".afisha__item__name, .afisha__item__info a, h2, h3")
            name = name_node.get_text(" ", strip=True) if name_node else ""
            if not name:
                continue
            day = item.select_one(".afisha__item__date__day")
            month = item.select_one(".afisha__item__date__month")
            date_label = ""
            if day and month:
                mon_raw = month.get_text(" ", strip=True).lower()
                mon = next((full for full in MONTH_FIX if full.startswith(mon_raw[:3])), mon_raw)
                date_label = f"{day.get_text(strip=True)} {mon}"
            start = parse_ru_date(date_label or text)
            meta_time = item.select_one(".afisha__item__meta__time")
            time_text = meta_time.get_text(" ", strip=True) if meta_time else ""
            # Prefer "19:00 | …" head; ignore duration-only fragments.
            start_time = parse_ru_time(time_text.split("|", 1)[0] if time_text else text)
            place = item.select_one(".afisha__item__meta__place")
            hall = place.get_text(" ", strip=True) if place else ""
            link = item.select_one('a[href*="/show/"]') or item.select_one("a[href]")
            href = (link.get("href") if link else "") or LISTING_URL
            img = item.select_one("img[data-src], img[data-lazy-src], img[src]")
            image_src = None
            if img:
                image_src = (
                    img.get("data-src")
                    or img.get("data-lazy-src")
                    or img.get("data-original")
                    or img.get("src")
                )
                if image_src and image_src.startswith("data:"):
                    image_src = img.get("data-src") or img.get("data-lazy-src")
            show = self.make_show(
                name=name,
                url=href,
                start=start,
                start_time=start_time,
                venue=hall or self.venue,
                image_src=image_src,
                description=text[:500],
            )
            if show:
                shows.append(show)
        return shows


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--dry", action="store_true")
    args = parser.parse_args()
    MdmScraper(dry=args.dry).scrape()
