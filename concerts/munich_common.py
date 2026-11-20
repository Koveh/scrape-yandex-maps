"""Munich concert upsert — same table as Vienna, city = Мюнхен."""
from __future__ import annotations

from calendar import monthrange
from datetime import date

from vienna_common import MUNICH_CITY, ViennaShow, ViennaStore


class MunichStore(ViennaStore):
    def __init__(self, source_channel: str, dry: bool = False) -> None:
        super().__init__(source_channel, dry=dry, city=MUNICH_CITY)


def month_bounds(offset: int) -> tuple[date, date]:
    today = date.today()
    month = today.month + offset
    year = today.year + (month - 1) // 12
    month = (month - 1) % 12 + 1
    start = date(year, month, 1)
    return start, date(year, month, monthrange(year, month)[1])
