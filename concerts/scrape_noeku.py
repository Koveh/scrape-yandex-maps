"""NÖ Kultur calendars that share the .event-item card (Grafenegg, Festspielhaus, Baden)."""
from __future__ import annotations

import re

from vienna_common import HtmlVenueScraper, ViennaShow, logged, parse_listing_date, parse_price, parse_start_time

SKIP_RE = re.compile(r"\b(abgesagt|cancelled|bustransfer)\b", re.I)


class NoekuCalendarScraper(HtmlVenueScraper):
    max_pages = 12

    def parse(self, soup) -> list[ViennaShow]:
        shows: list[ViennaShow] = []
        for item in soup.select(".event-item"):
            text = re.sub(r"\s+", " ", item.get_text(" ", strip=True))
            if SKIP_RE.search(text):
                continue
            title = item.select_one(".card-headline__title")
            subtitle = item.select_one(".card-headline__subtitle, .event-item__description")
            name = title.get_text(" ", strip=True) if title else ""
            extra = subtitle.get_text(" ", strip=True) if subtitle else ""
            if extra and extra.lower() not in name.lower():
                name = f"{name} — {extra}".strip(" —")
            link = None
            for anchor in item.select("a[href]"):
                href = anchor.get("href") or ""
                if href.startswith("/") or "/programm" in href or "/kalender" in href:
                    if href.startswith("data:"):
                        continue
                    link = href
                    break
            hall = ""
            for span in item.select(".text-body-small, .event-item__info"):
                raw = span.get_text(" ", strip=True)
                if any(token in raw for token in ("Saal", "Wolke", "Bühne", "Domplatz", "Auditorium")):
                    hall = raw.replace("∙", "").strip()
                    break
            img = item.select_one("img[src]")
            price_from, price_to = parse_price(text)
            show = self.make_show(
                name=name,
                url=link or self.listing_url,
                start=parse_listing_date(text),
                start_time=parse_start_time(text),
                venue=hall or self.venue,
                image_src=img.get("src") if img else None,
                price_from=price_from,
                price_to=price_to,
            )
            if show:
                shows.append(show)
        return shows

    @logged
    def scrape(self) -> None:
        shows: list[ViennaShow] = []
        seen: set[str] = set()
        for page in range(1, self.max_pages + 1):
            url = self.listing_url if page == 1 else f"{self.listing_url}{'&' if '?' in self.listing_url else '?'}page={page}"
            soup = self.fetch_soup(url)
            page_shows = self.parse(soup)
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
