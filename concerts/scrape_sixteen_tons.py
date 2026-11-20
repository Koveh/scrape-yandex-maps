"""16 Tons club (Moscow) playbill — posters + real event titles."""
from __future__ import annotations

import argparse
import re
from datetime import datetime

from bs4 import BeautifulSoup

from moscow_common import MOSCOW_CITY, parse_ru_date, parse_ru_price, parse_ru_time
from vienna_common import HtmlVenueScraper, ViennaShow

LISTING_URL = "https://16tons.ru/"


class SixteenTonsScraper(HtmlVenueScraper):
    city = MOSCOW_CITY
    listing_url = LISTING_URL
    source_channel = "sixteen_tons"
    venue = "16 Тонн"

    def parse(self, soup: BeautifulSoup) -> list[ViennaShow]:
        shows: list[ViennaShow] = []
        seen: set[str] = set()
        current_date = None
        for block in soup.select(".bill-day, .bill-farther, .event"):
            heading = block.select_one("h2, h3, .day-title, [class*=day]")
            if heading:
                parsed = parse_ru_date(heading.get_text(" ", strip=True))
                if parsed:
                    current_date = parsed
            for event in block.select(".event") if "event" not in (block.get("class") or []) else [block]:
                if "event" not in (event.get("class") or []):
                    continue
                title = event.select_one(".info h3, .info h2, .info .title, .info [class*=name], h3, h2")
                name = (title.get_text(" ", strip=True) if title else "").strip()
                if len(name) < 3:
                    continue
                link = event.select_one('a[href*="qtickets.ru/event"], a[href*="/event"]')
                href = (link.get("href") if link else "") or LISTING_URL
                text = event.get_text(" ", strip=True)
                start = parse_ru_date(text) or current_date
                if start is None:
                    # posters like 260908_… → yyMMdd
                    img = event.select_one("img[src], img[data-src]")
                    src = (img.get("src") or img.get("data-src") or "") if img else ""
                    m = re.search(r"(?<!\d)(\d{2})(\d{2})(\d{2})_", src)
                    if m:
                        try:
                            start = datetime.strptime(m.group(0)[:6], "%y%m%d").date()
                        except ValueError:
                            start = None
                if start is None:
                    continue
                key = f"{href}|{start}|{name.lower()}"
                if key in seen:
                    continue
                seen.add(key)
                img = event.select_one("img[src], img[data-src]")
                image_src = None
                if img:
                    image_src = img.get("src") or img.get("data-src")
                price_from, price_to = parse_ru_price(text)
                show = self.make_show(
                    name=name,
                    url=href,
                    start=start,
                    start_time=parse_ru_time(text),
                    venue=self.venue,
                    image_src=image_src,
                    description=text[:500],
                    price_from=price_from,
                    price_to=price_to,
                )
                if show:
                    shows.append(show)
        return shows


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--dry", action="store_true")
    args = parser.parse_args()
    SixteenTonsScraper(dry=args.dry).scrape()
