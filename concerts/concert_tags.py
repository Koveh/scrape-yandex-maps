"""Stable /concerts tags: kind slugs + extra searchable slugs."""
from __future__ import annotations

from functools import wraps
from typing import Callable, TypeVar

T = TypeVar("T")

EXTRA_KEYWORDS: dict[str, tuple[str, ...]] = {
    "art": ("vernissage", "finissage", "ausstellung", "kunsthalle", "kunst ", "art opening", "выставк"),
    "classical": (
        "klassik",
        "classical",
        "orchester",
        "philharmon",
        "sinfonie",
        "symphony",
        "kammermusik",
        "классичик",
        "симфон",
        "филармон",
        "оркестр",
    ),
    "club": ("clubnacht", "club night", "dj set", "dj-set", "rave", "клуб"),
    "industrial": ("industrial", "warehouse", "industriehalle", "das werk"),
    "comedy": ("comedy", "comedian", "open mic", "open-mic", "openmic", "стендап", "stand-up", "standup"),
    "electronic": ("techno", "electro", "electronic", "house", "dnb", "drum & bass", "drum and bass"),
    "festival": ("festival", "фестив"),
    "jazz": ("jazz", "blues", "джаз"),
    "kabarett": ("kabarett", "кабаре"),
    "kids": ("kinder", "kids", "family", "familie", "jugend", "детск", "семейный"),
    "metal": ("metal", "hardcore", "death metal"),
    "party": ("party", "tanznacht", "вечеринка"),
    "talk": ("lesung", "talk", "vortrag", "discussion", "gespräch", "diskussion", "лекци"),
    "theater": (
        "theater",
        "theatre",
        "schauspiel",
        "ballett",
        "ballet",
        "oper",
        "opera",
        "musical",
        "театр",
        "спектакл",
        "мюзикл",
        "опера",
        "балет",
    ),
}

KIND_KEYWORDS: dict[str, tuple[str, ...]] = {
    "concert": (
        "konzert",
        "concert",
        "концерт",
        "live act",
        "live-act",
        "gig",
        "band",
        "dj ",
        "album",
        "tournee",
        "tour ",
        "metal",
        "punk",
        "jazz",
        "techno",
        "indie",
        "rock",
        "hip-hop",
        "hiphop",
        "orchester",
        "philharmon",
        "sinfonie",
        "symphony",
        "симфон",
        "филармон",
    ),
    "event": (
        "theater",
        "theatre",
        "театр",
        "спектакл",
        "schauspiel",
        "tanz",
        "ballett",
        "ballet",
        "балет",
        "oper",
        "opera",
        "опера",
        "musical",
        "мюзикл",
        "lesung",
        "vortrag",
        "workshop",
        "führung",
        "fuehrung",
        "kinder",
        "zirkus",
        "circus",
        "vernissage",
        "ausstellung",
        "performance",
        "festival",
        "фестив",
    ),
    "standup": (
        "stand-up",
        "standup",
        "stand up",
        "стендап",
        "comedy",
        "comedian",
        "open mic",
        "open-mic",
        "kabarett",
        "improvis",
        "improv",
        "satire",
        "punchline",
        "открытый микрофон",
    ),
}

SOURCE_KIND: dict[str, str] = {
    "arena": "concert",
    "b72": "concert",
    "backstage": "concert",
    "albertina": "event",
    "albertinamodern": "event",
    "bahnwaerter": "event",
    "belvedere": "event",
    "buehnebaden": "event",
    "clubu": "concert",
    "casanova": "event",
    "chelsea": "concert",
    "concerts_moscow": "concert",
    "drachengasse": "event",
    "daswerk": "concert",
    "dschungel": "event",
    "escape": "concert",
    "festspielhaus": "concert",
    "grafenegg": "concert",
    "feierwerk": "concert",
    "flex": "concert",
    "flucc": "concert",
    "gasteig": "concert",
    "globe": "standup",
    "grelleforelle": "concert",
    "importexport": "concert",
    "jazzland": "concert",
    "junglecomedy": "standup",
    "konzerthaus": "concert",
    "leopoldmuseum": "event",
    "kunsthalle": "event",
    "landestheater": "event",
    "lachundschiess": "standup",
    "luckypunch": "standup",
    "lustspielhaus": "standup",
    "mak": "event",
    "marxhalle": "concert",
    "metropol": "concert",
    "mqw": "event",
    "mskevents_ru": "event",
    "muffatwerk": "concert",
    "niedermair": "standup",
    "olympiapark": "concert",
    "orpheum": "standup",
    "planet": "concert",
    "porgy": "concert",
    "praterdome": "concert",
    "rabenhof": "event",
    "radiokulturhaus": "concert",
    "rausgegangen": "event",
    "reigen": "concert",
    "rotesonne": "concert",
    "sargfabrik": "event",
    "sass": "concert",
    "schallaburg": "event",
    "secession": "event",
    "simpl": "standup",
    "sobytiyami": "event",
    "stadthalle": "concert",
    "stadtsaal": "standup",
    "strom": "concert",
    "theaterimpark": "event",
    "theaterwien": "event",
    "thecomedypub": "standup",
    "tonkuenstler": "concert",
    "unterfahrt": "concert",
    "vereinsheim": "standup",
    "vindobona": "concert",
    "viper": "concert",
    "volkstheater": "event",
    "wuk": "event",
    "volksoper": "event",
    "burgtheater": "event",
    "staatsoper": "event",
    "muth": "concert",
    "kosmos": "event",
    "palace": "concert",
    "palaisauersperg": "event",
    "englishtheatre": "event",
    "musicalvienna": "event",
    "nest": "event",
    "standupstore": "standup",
    "mbronnaya": "event",
    "mossovet": "event",
    "mdm": "event",
    "afisha_concerts": "concert",
    "afisha_theatre": "event",
    "afisha_clubs": "concert",
    "afisha_theatres": "event",
    "yandex_afisha": "concert",
    "lenkom": "event",
    "satire": "event",
    "mxat": "event",
    "helikon": "event",
    "zaryadye": "concert",
    "sixteen_tons": "concert",
    "vakhtangov": "event",
    "meloman": "concert",
    "luzhniki": "concert",
    "pushkin": "event",
}

SOURCE_EXTRAS: dict[str, tuple[str, ...]] = {
    "burgtheater": ("theater",),
    "albertina": ("art",),
    "albertinamodern": ("art",),
    "belvedere": ("art",),
    "buehnebaden": ("theater",),
    "clubu": ("club", "electronic"),
    "daswerk": ("club", "electronic", "industrial"),
    "drachengasse": ("theater",),
    "festspielhaus": ("classical",),
    "grafenegg": ("classical", "festival"),
    "dschungel": ("kids", "theater"),
    "englishtheatre": ("theater",),
    "jazzland": ("jazz",),
    "kosmos": ("theater",),
    "kunsthalle": ("art",),
    "landestheater": ("theater",),
    "leopoldmuseum": ("art",),
    "mak": ("art",),
    "mqw": ("art",),
    "praterdome": ("club", "electronic", "industrial"),
    "schallaburg": ("art", "festival"),
    "secession": ("art",),
    "musicalvienna": ("theater",),
    "muth": ("classical",),
    "nest": ("theater",),
    "palace": ("classical",),
    "palaisauersperg": ("classical",),
    "staatsoper": ("classical", "theater"),
    "theaterimpark": ("theater",),
    "theaterwien": ("theater",),
    "tonkuenstler": ("classical",),
    "volksoper": ("classical", "theater"),
    "volkstheater": ("theater",),
    "mbronnaya": ("theater",),
    "mossovet": ("theater",),
    "mdm": ("theater",),
    "afisha_theatre": ("theater",),
    "afisha_clubs": ("club",),
    "afisha_theatres": ("theater",),
    "lenkom": ("theater",),
    "satire": ("theater",),
    "mxat": ("theater",),
    "helikon": ("theater", "classical"),
    "zaryadye": ("classical",),
    "sixteen_tons": ("club",),
    "vakhtangov": ("theater",),
    "meloman": ("classical",),
    "luzhniki": ("concert",),
    "pushkin": ("theater",),
    "standupstore": ("comedy",),
}


def logged(fn: Callable[..., T]) -> Callable[..., T]:
    @wraps(fn)
    def wrapper(*args: object, **kwargs: object) -> T:
        print(f"{fn.__name__}", flush=True)
        return fn(*args, **kwargs)

    return wrapper


class ConcertTagger:
    def classify(self, source: str, name: str, venue: str = "", description: str = "") -> list[str]:
        text = " ".join(part for part in (name, venue, description) if part).lower()
        kinds = {SOURCE_KIND.get(source, "event")}
        kinds.update(self.kinds_from_text(text))
        extras = set(self.extra_tags(text))
        extras.update(SOURCE_EXTRAS.get(source, ()))
        ordered_kinds = [kind for kind in ("concert", "standup", "event") if kind in kinds]
        extras_sorted = sorted(tag for tag in extras if tag not in ordered_kinds)
        return ordered_kinds + extras_sorted

    def house_tags(self, source: str) -> list[str]:
        kind = SOURCE_KIND.get(source)
        extras = SOURCE_EXTRAS.get(source, ())
        tags: list[str] = []
        if kind:
            tags.append(kind)
        tags.extend(tag for tag in extras if tag not in tags)
        return tags

    def extra_tags(self, text: str) -> list[str]:
        found: list[str] = []
        for slug, needles in EXTRA_KEYWORDS.items():
            if any(needle in text for needle in needles):
                found.append(slug)
        return found

    def kinds_from_text(self, text: str) -> set[str]:
        matched: set[str] = set()
        for kind, needles in KIND_KEYWORDS.items():
            if any(needle in text for needle in needles):
                matched.add(kind)
        return matched
