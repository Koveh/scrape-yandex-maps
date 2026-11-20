"""One-time deterministic seed curation for the concerts table.

Parses event link / name / date / time / price / venue / short description from
raw_text, classifies concert-vs-not, rejects past events, dedups, and sets status
on every pending row. The daily cloud `concerts-daily-curation` routine owns
ongoing curation; this just guarantees correct content immediately.
"""
from __future__ import annotations

import os
import re
from datetime import date

import psycopg2

DSN = os.getenv("CONCERTS_DSN", "postgresql://koveh:Daniil77Daniil@65.109.88.77:5432/koveh")
TODAY = date.today()

MONTHS = {"янв": 1, "фев": 2, "мар": 3, "апр": 4, "мая": 5, "май": 5, "июн": 6,
          "июл": 7, "авг": 8, "сен": 9, "окт": 10, "ноя": 11, "дек": 12}
DATE_RE = re.compile(r"(\d{1,2})\s*(янв|фев|мар|апр|мая|май|июн|июл|авг|сен|окт|ноя|дек)", re.I)
TIME_RE = re.compile(r"\b([01]?\d|2[0-3]):([0-5]\d)\b")
PRICE_RE = re.compile(r"(\d[\d\s]{1,7})\s*(?:₽|руб)", re.I)
MD_LINK = re.compile(r"\[([^\]]+)\]\((https?://[^)]+)\)")
URL_RE = re.compile(r"https?://\S+|\b[\w-]+\.(?:ru|com|net|org|me|io|cc|events)\b\S*", re.I)

CONCERT = ["концерт", "concert", "выступлен", "гастрол", "сольник", "шоу", "клабшоу",
           "open air", "рейв", "живой звук", "музык", "фест", "tour", "тур "]
NONCONCERT = ["выставк", "спектакл", "экскурс", "особняк", "музей", "лекци", "маркет",
              "ярмарк", "иммерсив", " сад", "парк ", "балет", "опера"]


def clean_md(s: str) -> str:
    s = MD_LINK.sub(r"\1", s)          # [text](url) -> text
    s = URL_RE.sub(" ", s)             # bare urls
    s = re.sub(r"[*_`>#|]+", " ", s)    # markdown emphasis / noise
    s = re.sub(r"[ \t]+", " ", s)
    s = re.sub(r"\n{2,}", "\n", s)
    return s.strip()


JUNK = ("подписаться", "подписка", "источник", "канал", "перейти", "купить", "билет",
        "забронир", "регистрац", "читать", "t.me", "vk", "telegram", "ещё", "подробнее")


def good_name(t: str) -> bool:
    if not t or len(t) < 3:
        return False
    low = t.lower()
    if any(low.startswith(j) for j in JUNK):
        return False
    if re.fullmatch(r"[\d\s]+", t):
        return False
    if DATE_RE.match(t.strip()) and len(t) < 16:  # bare "15 июня"
        return False
    return True


def pick_event(text: str, fallback: str):
    """(display name, event url) — first non-junk markdown link, else first clean line."""
    name = url = None
    for m in MD_LINK.finditer(text):
        t = re.sub(r"[*_`]+", "", m.group(1)).strip(" \n🔥⚡️•-")
        if good_name(t):
            name, url = t[:160], m.group(2)
            break
        if url is None and not any(t.lower().startswith(j) for j in JUNK):
            url = m.group(2)
    if name is None:
        for ln in clean_md(text).split("\n"):
            ln = ln.strip()
            if good_name(ln):
                name = ln[:160]
                break
    return (name or fallback), url


def parse_date(text: str):
    """Nearest upcoming DD-month date (rolls to next year when needed)."""
    m = DATE_RE.search(text)
    if not m:
        return None
    day, mon = int(m.group(1)), MONTHS[m.group(2).lower()[:3]]
    try:
        parsed = date(TODAY.year, mon, day)
    except ValueError:
        return None
    if parsed < TODAY:
        try:
            parsed = date(TODAY.year + 1, mon, day)
        except ValueError:
            return None
    return parsed


def parse_time(text: str):
    m = TIME_RE.search(text)
    return f"{int(m.group(1)):02d}:{m.group(2)}" if m else None


def parse_prices(text: str):
    vals = sorted({int(re.sub(r"\s", "", g)) for g in PRICE_RE.findall(text) if int(re.sub(r"\s", "", g)) >= 50})
    if not vals:
        return None, None
    return vals[0], (vals[-1] if len(vals) > 1 else None)


def parse_venue(text: str):
    clean = URL_RE.sub(" ", text.replace("\n", " "))
    for seg in re.split(r"[/·]", clean, maxsplit=6)[1:]:
        s = re.sub(r"[*_`#\[\]()]", "", seg).strip()
        if 2 < len(s) < 40 and re.search(r"[A-Za-zА-Яа-я]", s) and "₽" not in s \
                and "." not in s and not DATE_RE.search(s) and not TIME_RE.search(s):
            return s
    return None


PROMO = ("билет", "соцсет", "наши соц", "подпис", "tiktok", "youtube", "instagram",
         "vk.com", "vk музык", "концерты в москве", "репост", "reels", "канал",
         "ссылка в", "🎫", "🎥", "📲", "➡️", "👉", "❤️")


def is_promo(ln: str) -> bool:
    return any(p in ln.lower() for p in PROMO)


def short_desc(text: str, name: str | None) -> str | None:
    body = clean_md(text)
    lines = [ln.strip() for ln in body.split("\n") if ln.strip()]
    kept = []
    for ln in lines:
        if name and ln.lower().startswith(name.lower()[:20]):
            continue
        if DATE_RE.search(ln) and ("₽" in ln or "/" in ln or "вход" in ln.lower()):
            continue
        if is_promo(ln):                              # ads/socials footer — drop
            continue
        if not re.search(r"[А-Яа-яA-Za-z]{3}", ln):   # emoji/symbol-only line
            continue
        kept.append(ln)
    out = " ".join(kept).strip()
    return (out[:277] + "…") if len(out) > 280 else (out or None)


def is_concert(channel: str, text: str) -> bool:
    low = text.lower()
    if channel == "concerts_moscow":
        return True
    if any(n in low for n in NONCONCERT) and "концерт" not in low:
        return False
    return any(c in low for c in CONCERT)


def norm(name: str) -> str:
    return re.sub(r"[^a-zа-я0-9]", "", (name or "").lower())


def main() -> None:
    conn = psycopg2.connect(DSN)
    cur = conn.cursor()
    cur.execute("SELECT id, source_channel, name, raw_text, image_url "
                "FROM concerts WHERE status='pending' ORDER BY id")
    rows = cur.fetchall()

    kept = rejected = dups = 0
    groups: dict[tuple, int] = {}
    for rid, channel, name, raw, image_url in rows:
        text = raw or ""
        if not is_concert(channel, text):
            cur.execute("UPDATE concerts SET status='rejected', updated_at=now() WHERE id=%s", (rid,))
            rejected += 1
            continue
        d = parse_date(text)
        if d is not None and d < TODAY:  # past event in a recent repost -> not upcoming
            cur.execute("UPDATE concerts SET status='rejected', updated_at=now() WHERE id=%s", (rid,))
            rejected += 1
            continue
        display_name, website = pick_event(text, name)
        key = (norm(display_name), d)
        if key[0] and key in groups:
            cur.execute("UPDATE concerts SET status='duplicate', canonical_id=%s, updated_at=now() WHERE id=%s",
                        (groups[key], rid))
            dups += 1
            continue
        groups[key] = rid
        cur.execute(
            "UPDATE concerts SET status='kept', name=%s, website_url=%s, start_date=%s, start_time=%s, "
            "venue=%s, price_from=%s, price_to=%s, description=%s, updated_at=now() WHERE id=%s",
            (display_name, website, d, parse_time(text), parse_venue(text),
             *parse_prices(text), short_desc(text, display_name), rid))
        kept += 1

    conn.commit()
    cur.close()
    conn.close()
    print(f"kept={kept} duplicates={dups} rejected={rejected}")


if __name__ == "__main__":
    main()
