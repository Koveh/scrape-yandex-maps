"""Moscow concert upsert — same `concerts` table, city = Москва."""
from __future__ import annotations

import re
from calendar import monthrange
from datetime import date, time

from vienna_common import ViennaShow, ViennaStore

MOSCOW_CITY = "Москва"

RU_MONTHS = {
    "янв": 1,
    "фев": 2,
    "мар": 3,
    "апр": 4,
    "мая": 5,
    "май": 5,
    "июн": 6,
    "июл": 7,
    "авг": 8,
    "сен": 9,
    "окт": 10,
    "ноя": 11,
    "дек": 12,
}
DATE_RE = re.compile(
    r"(\d{1,2})\s*(января|янв|февраля|фев|марта|мар|апреля|апр|мая|май|"
    r"июня|июн|июля|июл|августа|авг|сентября|сен|октября|окт|ноября|ноя|декабря|дек)",
    re.I,
)
TIME_RE = re.compile(r"\b([01]?\d|2[0-3]):([0-5]\d)\b")
PRICE_RE = re.compile(r"(\d[\d\s]{1,7})\s*(?:₽|руб)", re.I)


class MoscowStore(ViennaStore):
    def __init__(self, source_channel: str, dry: bool = False) -> None:
        super().__init__(source_channel, dry=dry, city=MOSCOW_CITY)


def month_bounds(offset: int) -> tuple[date, date]:
    today = date.today()
    month = today.month + offset
    year = today.year + (month - 1) // 12
    month = (month - 1) % 12 + 1
    start = date(year, month, 1)
    return start, date(year, month, monthrange(year, month)[1])


def parse_ru_date(text: str, *, allow_next_year: bool = True) -> date | None:
    match = DATE_RE.search(text or "")
    if not match:
        return None
    day = int(match.group(1))
    mon = RU_MONTHS[match.group(2).lower()[:3]]
    today = date.today()
    try:
        parsed = date(today.year, mon, day)
    except ValueError:
        return None
    if parsed < today and allow_next_year:
        try:
            parsed = date(today.year + 1, mon, day)
        except ValueError:
            return None
    return parsed


def parse_ru_time(text: str) -> time | None:
    match = TIME_RE.search(text or "")
    if not match:
        return None
    return time(int(match.group(1)), int(match.group(2)))


def parse_ru_price(text: str) -> tuple[int | None, int | None]:
    vals = sorted(
        {
            int(re.sub(r"\s", "", group))
            for group in PRICE_RE.findall(text or "")
            if int(re.sub(r"\s", "", group)) >= 50
        }
    )
    if not vals:
        return None, None
    return vals[0], (vals[-1] if len(vals) > 1 else None)
