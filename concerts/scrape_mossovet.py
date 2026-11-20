"""Театр Моссовета timetable -> concerts (Москва, kept)."""
from __future__ import annotations

import argparse
import re
from datetime import date

from bs4 import BeautifulSoup

from moscow_common import MOSCOW_CITY, RU_MONTHS, parse_ru_time
from vienna_common import HtmlVenueScraper, ViennaShow

LISTING_URL = "https://mossoveta.ru/timetable/"


class MossovetScraper(HtmlVenueScraper):
    city = MOSCOW_CITY
    listing_url = LISTING_URL
    source_channel = "mossovet"
    venue = "Театр Моссовета"

    def parse(self, soup: BeautifulSoup) -> list[ViennaShow]:
        shows: list[ViennaShow] = []
        for item in soup.select(".event"):
            title = item.select_one(".info .title a, .title a")
            name = title.get_text(" ", strip=True) if title else ""
            if not name or name.lower() in {"подробнее", "купить билет"}:
                continue
            day_num = item.select_one(".dt-photo big, big")
            month_span = None
            spans = item.select(".dt-photo span")
            for span in spans:
                text = span.get_text(" ", strip=True).lower()
                if text[:3] in RU_MONTHS:
                    month_span = span
                    break
            start = None
            if day_num is not None and month_span is not None:
                try:
                    day = int(re.sub(r"\D", "", day_num.get_text()) or "0")
                    mon = RU_MONTHS[month_span.get_text(" ", strip=True).lower()[:3]]
                    today = date.today()
                    start = date(today.year, mon, day)
                    if start < today:
                        start = date(today.year + 1, mon, day)
                except ValueError:
                    start = None
            text = item.get_text(" ", strip=True)
            start_time = parse_ru_time(text)
            href = (title.get("href") if title else "") or LISTING_URL
            if href.startswith("/"):
                href = f"https://mossoveta.ru{href}"
            img = None
            figure = item.select_one("figure[style*='background-image']")
            if figure and figure.get("style"):
                match = re.search(r"url\(['\"]?(.*?)['\"]?\)", figure["style"])
                if match:
                    img = match.group(1)
                    if img.startswith("//"):
                        img = f"https:{img}"
            hall = ""
            low = text.lower()
            if "основн" in low:
                hall = "Основная сцена"
            elif "крыш" in low:
                hall = "Сцена «Под крышей»"
            elif "малая" in low:
                hall = "Малая сцена"
            show = self.make_show(
                name=name,
                url=href,
                start=start,
                start_time=start_time,
                venue=f"{self.venue} · {hall}" if hall else self.venue,
                image_src=img,
                description=text[:500],
            )
            if show:
                shows.append(show)
        return shows


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--dry", action="store_true")
    args = parser.parse_args()
    MossovetScraper(dry=args.dry).scrape()
