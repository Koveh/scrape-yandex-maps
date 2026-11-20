"""Театр имени Пушкина — calendar afisha."""
from __future__ import annotations

import argparse
from datetime import date

from bs4 import BeautifulSoup

from moscow_common import MOSCOW_CITY, parse_ru_time
from vienna_common import HtmlVenueScraper, ViennaShow, day_month_date

LISTING_URL = "https://teatrpushkin.ru/afisha/"


class PushkinTheatreScraper(HtmlVenueScraper):
    city = MOSCOW_CITY
    listing_url = LISTING_URL
    source_channel = "pushkin"
    venue = "Театр Пушкина"

    def parse(self, soup: BeautifulSoup) -> list[ViennaShow]:
        shows: list[ViennaShow] = []
        seen: set[str] = set()
        # Month label near calendar (Ноябрь / Декабрь …)
        month = None
        month_map = (
            ("январ", 1),
            ("феврал", 2),
            ("март", 3),
            ("апрел", 4),
            ("май", 5),
            ("мая", 5),
            ("июн", 6),
            ("июл", 7),
            ("август", 8),
            ("сентябр", 9),
            ("октябр", 10),
            ("ноябр", 11),
            ("декабр", 12),
        )
        for label in soup.select(".calendar-wrapper, .calendar-section, h1, h2, h3"):
            text = label.get_text(" ", strip=True).lower()
            for name, num in month_map:
                if name in text:
                    month = num
                    break
            if month:
                break
        month = month or date.today().month
        for day_node in soup.select(".calendar-day"):
            if "past" in (day_node.get("class") or []):
                # keep scraping past-marked cells if they still hold future times after month roll
                pass
            day_num = day_node.select_one(".calendar-day-num")
            try:
                day = int((day_num.get_text(strip=True) if day_num else "") or "0")
            except ValueError:
                continue
            start = day_month_date(day, month)
            if start is None:
                continue
            for item in day_node.select(".day-program-item"):
                text = item.get_text(" ", strip=True)
                # "19:00 Основная сцена Опера нищих"
                name = text
                for prefix in ("Основная сцена", "Филиал", "Малая сцена"):
                    if prefix in text:
                        name = text.split(prefix, 1)[-1].strip()
                        break
                # strip leading time
                parts = name.split(" ", 1)
                if parts and ":" in parts[0] and len(parts) > 1:
                    name = parts[1]
                name = name.strip()
                if len(name) < 3:
                    continue
                link = item.select_one("a[href]")
                href = (link.get("href") if link else "") or LISTING_URL
                key = f"{href}|{start}|{name.lower()}"
                if key in seen:
                    continue
                seen.add(key)
                show = self.make_show(
                    name=name,
                    url=href,
                    start=start,
                    start_time=parse_ru_time(text),
                    venue=self.venue,
                    description=text[:500],
                )
                if show:
                    shows.append(show)
        return shows


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--dry", action="store_true")
    args = parser.parse_args()
    PushkinTheatreScraper(dry=args.dry).scrape()
