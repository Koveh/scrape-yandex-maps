"""Shared Bitrix “cards-19” playbill scraper (Lenkom, Satire, similar theaters)."""
from __future__ import annotations

import argparse
from urllib.parse import unquote, urljoin

from bs4 import BeautifulSoup

from moscow_common import MOSCOW_CITY, parse_ru_date, parse_ru_time
from vienna_common import HtmlVenueScraper, ViennaShow

THEATERS = (
    ("lenkom", "https://lenkom.ru/", "Ленком"),
    ("satire", "https://satire.ru/", "Театр Сатиры"),
)


def bitrix_lazy_image(img) -> str | None:
    if img is None:
        return None
    path = img.get("data-bc-lazy-path")
    filename = img.get("data-bc-lazy-filename")
    if path and filename:
        # Relative Bitrix path; caller urljoins with listing host.
        return f"{path.rstrip('/')}/{unquote(filename)}"
    src = img.get("data-src") or img.get("src")
    if src and not str(src).startswith("data:"):
        return str(src)
    return None


class BitrixAfishaScraper(HtmlVenueScraper):
    city = MOSCOW_CITY

    def __init__(self, source: str, url: str, venue: str, dry: bool = False) -> None:
        self.source_channel = source
        self.listing_url = url
        self.venue = venue
        super().__init__(dry=dry)

    def parse(self, soup: BeautifulSoup) -> list[ViennaShow]:
        shows: list[ViennaShow] = []
        seen: set[str] = set()
        for item in soup.select(".cards-19-item"):
            title = item.select_one(".cards-19-item__title, [class*='title']")
            name = (title.get_text(" ", strip=True) if title else "").strip()
            # Age badge alone is not a title
            if name in {"12+", "16+", "18+", "6+", "0+"} or len(name) < 3:
                text = item.get_text(" ", strip=True)
                name = text
                for token in ("Билеты", "Актёрский состав", "12+", "16+", "18+"):
                    name = name.replace(token, " ")
                name = " ".join(name.split())
            text = item.get_text(" ", strip=True)
            # Playbill rows mention tickets / cast; skip press-clipping cards.
            if "Билет" not in text and "билет" not in text and "Актёр" not in text:
                continue
            start = parse_ru_date(text)
            if start is None or len(name) < 3:
                continue
            link = item.select_one("a[href]")
            href = (link.get("href") if link else "") or self.listing_url
            # Prefer on-site / ticket links — drop external news domains.
            host = (self.listing_url or "").split("/")[2] if "://" in (self.listing_url or "") else ""
            if href.startswith("http") and host and host not in href:
                if not any(token in href for token in ("ticket", "biletx", "afisha", "kassy")):
                    continue
            key = f"{href}|{start}|{name.lower()}"
            if key in seen:
                continue
            seen.add(key)
            img = item.select_one("img")
            image_src = bitrix_lazy_image(img)
            if image_src and self.listing_url:
                image_src = urljoin(self.listing_url, image_src)
            show = self.make_show(
                name=name[:180],
                url=href,
                start=start,
                start_time=parse_ru_time(text),
                venue=self.venue,
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
    for source, url, venue in THEATERS:
        BitrixAfishaScraper(source, url, venue, dry=args.dry).scrape()
