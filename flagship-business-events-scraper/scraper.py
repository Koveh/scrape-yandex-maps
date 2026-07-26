#!/usr/bin/env python3
"""Curated flagship business events: IT/data engineering + real estate / proptech.

Hand-maintained anchors for media-significant conferences and trade fairs
relevant to IT services, data engineering, software, and real estate /
digital construction in Vienna, DACH and nearby EU hubs.
"""
from __future__ import annotations

import argparse
import json
from datetime import datetime
from pathlib import Path
from typing import Any

SOURCE_NAME = "flagship_business"
SOURCE_LABEL = "Flagship Business Events"
SOURCE_URL = "https://koveh.com/events"

# Keep this list short and high-signal. Prefer ticketed congresses / fairs with press.
FLAGSHIP_EVENTS: list[dict[str, Any]] = [
    # --- Vienna / Austria: IT & data ---
    {
        "title": "TEDAI 2026 — TED Conference on AI",
        "start_at": "2026-10-28",
        "end_at": "2026-10-30",
        "location": "Hofburg Palace, Vienna",
        "city": "Vienna",
        "country": "Austria",
        "url": "https://tedai-vienna.ted.com/",
        "category": "AI / Media / Thought Leadership",
        "description": (
            "Official TED Conference on AI in Vienna (Hofburg). High media density — "
            "talks, panels, discovery day. Strong brand / networking, less deep engineering than DSC DACH."
        ),
        "tags": ["AI", "TED", "Vienna", "Media", "Flagship"],
    },
    {
        "title": "Meet 2026 (Austria mobility / tech expo)",
        "start_at": "2026-11-18",
        "end_at": "2026-11-18",
        "location": "VIECON / Messe Wien, Vienna",
        "city": "Vienna",
        "country": "Austria",
        "url": "https://meet-austria.at/de/",
        "category": "Mobility / Tech Exhibition",
        "description": "Austrian mobility & tech meetup/expo at Messe Wien.",
        "tags": ["Mobility", "Vienna", "Exhibition", "Flagship"],
    },
    {
        "title": "ECR-Tag 2026",
        "start_at": "2026-11-04",
        "end_at": "2026-11-04",
        "location": "VIECON / Messe Wien, Vienna",
        "city": "Vienna",
        "country": "Austria",
        "url": "https://ecr-austria.at/ecrtag2026/",
        "category": "Retail / Supply Chain",
        "description": "Efficient Consumer Response Austria day — retail, data and supply-chain practitioners.",
        "tags": ["Retail", "Data", "Vienna", "Flagship"],
    },
    {
        "title": "DSC DACH 2026 — AI Builders Conference",
        "start_at": "2026-10-13",
        "end_at": "2026-10-15",
        "location": "Vienna, Austria",
        "city": "Vienna",
        "country": "Austria",
        "url": "https://dscdach.com/",
        "category": "AI / Data / Engineering",
        "description": (
            "AI builders conference for DACH: data & ML infrastructure, data science, "
            "executive forums. High relevance for data engineering and AI delivery teams."
        ),
        "tags": ["AI", "DataEngineering", "Vienna", "DACH", "Flagship"],
    },
    {
        "title": "DevFest Vienna 2026",
        "start_at": "2026-11-07",
        "end_at": "2026-11-07",
        "location": "Vienna, Austria",
        "city": "Vienna",
        "country": "Austria",
        "url": "https://www.devfest.at/",
        "category": "Software / Community",
        "description": "Google Developer Groups DevFest Vienna — large community tech conference.",
        "tags": ["Software", "GDG", "Vienna", "Flagship"],
    },
    {
        "title": "SoCraTes Austria 2026",
        "start_at": "2026-09-25",
        "end_at": "2026-09-26",
        "location": "Austria",
        "city": "Austria",
        "country": "Austria",
        "url": "https://www.socrates-conference.at/",
        "category": "Software Craftsmanship",
        "description": "Software Craft and Testing unconference — strong developer / engineering culture event.",
        "tags": ["Software", "Engineering", "Austria", "Flagship"],
    },
    {
        "title": "Digital Days 2026 (Digital City Wien)",
        "start_at": "2026-11-16",
        "end_at": "2026-11-18",
        "location": "Vienna, Austria",
        "city": "Vienna",
        "country": "Austria",
        "url": "https://digitalcity.wien/event/digital-days-2026/",
        "category": "Digital / City / Media",
        "description": "City of Vienna digitalisation festival — DigiStreet, public + industry formats, media coverage.",
        "tags": ["Digital", "Vienna", "City", "Flagship"],
    },
    {
        "title": "IT Futures — Karriere-Festival",
        "start_at": "2026-11-26",
        "end_at": "2026-11-26",
        "location": "Vienna, Austria",
        "city": "Vienna",
        "country": "Austria",
        "url": "https://www.digitalaustria.gv.at/wissenswertes/events.html",
        "category": "IT Careers / Talent",
        "description": "National IT careers festival in Vienna — useful for hiring / employer branding in AT tech.",
        "tags": ["IT", "Talent", "Vienna", "Flagship"],
    },
    # --- Vienna: real estate × digital / AI ---
    {
        "title": "CEE Property Forum & Awards Gala 2026",
        "start_at": "2026-11-23",
        "end_at": "2026-11-24",
        "location": "Palais Niederösterreich / Hyatt Regency, Vienna",
        "city": "Vienna",
        "country": "Austria",
        "url": "https://www.property-forum.eu/forums/conference-property/cee-property-forum-awards-gala-2026-vienna-austria/2039",
        "category": "Real Estate / Investment / Media",
        "description": (
            "Leading CEE real-estate conference in Vienna: investment, financing, ESG, "
            "AI in real estate, awards gala. Strong press and decision-maker density."
        ),
        "tags": ["RealEstate", "CEE", "Vienna", "Investment", "Flagship"],
    },
    {
        "title": "ÖVI Bauträgertag 2026",
        "start_at": "2026-11-26",
        "end_at": "2026-11-26",
        "location": "Erste Campus (12. Stock), Vienna",
        "city": "Vienna",
        "country": "Austria",
        "url": "https://www.ovi.at/veranstaltungen",
        "category": "Real Estate / Developers",
        "description": (
            "Österreichischer Verband der Immobilienwirtschaft — developers' day. "
            "Association calendar also lists ImmoZert Bewertungssymposium Wien/Kufstein "
            "(2026 dates TBA; 2025 editions were mid-October). Contact office@ovi.at."
        ),
        "tags": ["RealEstate", "Developers", "Vienna", "Association", "Flagship"],
    },
    {
        "title": "Innovationskongress | Digitales Planen, Bauen & Betreiben",
        "start_at": "2026-09-17",
        "end_at": "2026-09-17",
        "location": "CAPE10, Vienna",
        "city": "Vienna",
        "country": "Austria",
        "url": "https://www.wirtschaftsagentur.at/termine-events-workshops/innovationskongress-digitales-planen-bauen-betreiben-1/",
        "category": "PropTech / Digital Construction",
        "description": (
            "Vienna Business Agency + Digital Findet Stadt congress on digital planning, "
            "construction and operations — startup pitches to ~200 industry guests."
        ),
        "tags": ["PropTech", "BIM", "Vienna", "Construction", "Flagship"],
    },
    # --- DACH / EU mega fairs (travel-worth for RE + tech) ---
    {
        "title": "EXPO REAL 2026",
        "start_at": "2026-10-05",
        "end_at": "2026-10-07",
        "location": "Messe München, Munich, Germany",
        "city": "Munich",
        "country": "Germany",
        "url": "https://www.exporeal.net/en/",
        "category": "Real Estate Trade Fair",
        "description": (
            "Europe's leading B2B real-estate investment fair (~40k+ participants). "
            "New Transform & Beyond area: AI, smart buildings, decarbonisation."
        ),
        "tags": ["RealEstate", "Munich", "TradeFair", "Investment", "Flagship"],
    },
    {
        "title": "BAU 2027",
        "start_at": "2027-01-11",
        "end_at": "2027-01-15",
        "location": "Messe München, Munich, Germany",
        "city": "Munich",
        "country": "Germany",
        "url": "https://bau-muenchen.com/en/",
        "category": "Architecture / Construction Trade Fair",
        "description": "World's leading trade fair for architecture, materials and systems.",
        "tags": ["Construction", "Architecture", "Munich", "TradeFair", "Flagship"],
    },
    {
        "title": "WeAreDevelopers World Congress 2027",
        "start_at": "2027-07-14",
        "end_at": "2027-07-16",
        "location": "Berlin, Germany",
        "city": "Berlin",
        "country": "Germany",
        "url": "https://www.wearedevelopers.com/world-congress",
        "category": "Software / Developer Festival",
        "description": (
            "Europe's large developer congress. 2026 Berlin edition (Jul 14–16 2026) already passed; "
            "next announced window Jul 14–16 2027. partners@wearedevelopers.com."
        ),
        "tags": ["Software", "Developers", "Berlin", "Flagship"],
    },
    {
        "title": "MIPIM 2027 — The Global Urban Festival",
        "start_at": "2027-03-16",
        "end_at": "2027-03-19",
        "location": "Palais des Festivals, Cannes, France",
        "city": "Cannes",
        "country": "France",
        "url": "https://www.mipim.com/",
        "category": "Real Estate / Urban Investment",
        "description": (
            "Global real-estate investment festival. MIPIM 2026 (Mar 2026) already passed; "
            "next Cannes edition targeted March 2027 — confirm dates closer to launch."
        ),
        "tags": ["RealEstate", "MIPIM", "Investment", "Flagship"],
    },
    {
        "title": "MAPIC 2026",
        "start_at": "2026-11-03",
        "end_at": "2026-11-04",
        "location": "Cannes, France",
        "city": "Cannes",
        "country": "France",
        "url": "https://www.mapic.com/",
        "category": "Retail Real Estate",
        "description": "International retail real-estate and leasing hub — brands, landlords, investors.",
        "tags": ["RealEstate", "Retail", "MAPIC", "Flagship"],
    },
    {
        "title": "digitalBAU 2028",
        "start_at": "2028-03-21",
        "end_at": "2028-03-23",
        "location": "Koelnmesse, Cologne, Germany",
        "city": "Cologne",
        "country": "Germany",
        "url": "https://www.digital-bau.com/",
        "category": "Digital Construction Trade Fair",
        "description": "Trade fair for digital solutions in construction (BIM, AI on site, software).",
        "tags": ["PropTech", "BIM", "Construction", "Germany", "Flagship"],
    },
    # --- Vienna exhibitions already strong for infra/tech (cross-check VIECON) ---
    {
        "title": "Network X 2026 (VIECON / Messe Wien)",
        "start_at": "2026-10-13",
        "end_at": "2026-10-15",
        "location": "VIECON / Messe Wien, Vienna",
        "city": "Vienna",
        "country": "Austria",
        "url": "https://networkxevent.com/",
        "category": "Telecom / Connectivity Trade Fair",
        "description": "Major European connectivity / telco expo at Messe Wien.",
        "tags": ["Telecom", "Vienna", "Exhibition", "Flagship"],
    },
    {
        "title": "Data Center World Europe 2026",
        "start_at": "2026-10-13",
        "end_at": "2026-10-14",
        "location": "VIECON / Messe Wien, Vienna",
        "city": "Vienna",
        "country": "Austria",
        "url": "https://datacenterworldeurope.com/",
        "category": "Data Centers / Infrastructure",
        "description": (
            "Data-centre industry fair (Informa) — co-located week with Network X. "
            "Sales: DCWSales@informa.com."
        ),
        "tags": ["DataCenters", "Infrastructure", "Vienna", "Flagship"],
    },
    {
        "title": "Enlit Europe 2026",
        "start_at": "2026-11-10",
        "end_at": "2026-11-12",
        "location": "VIECON / Messe Wien, Vienna",
        "city": "Vienna",
        "country": "Austria",
        "url": "https://www.enlit-europe.com/",
        "category": "Energy / Utilities Trade Fair",
        "description": "European energy transition congress & expo at Messe Wien — utilities, grids, digital energy.",
        "tags": ["Energy", "Vienna", "Exhibition", "Flagship"],
    },
    {
        "title": "Bits & Pretzels 2026",
        "start_at": "2026-09-28",
        "end_at": "2026-09-30",
        "location": "Munich, Germany (during Oktoberfest)",
        "city": "Munich",
        "country": "Germany",
        "url": "https://www.bitsandpretzels.com/",
        "category": "Founders / Startup Festival",
        "description": (
            "Europe's founders festival in Munich during Oktoberfest — startups, investors, "
            "corporate innovation. Strong matchmaking; hello@bitsandpretzels.com."
        ),
        "tags": ["Startup", "Founders", "Munich", "Networking", "Flagship"],
    },
    {
        "title": "Slush 2026",
        "start_at": "2026-11-18",
        "end_at": "2026-11-19",
        "location": "Helsinki, Finland",
        "city": "Helsinki",
        "country": "Finland",
        "url": "https://slush.org/",
        "category": "Startup / Investor Festival",
        "description": "Major European startup & investor gathering. hello@slush.org / tickets@slush.org.",
        "tags": ["Startup", "Investor", "Europe", "Flagship"],
    },
    {
        "title": "Smart City Expo World Congress 2026",
        "start_at": "2026-11-03",
        "end_at": "2026-11-05",
        "location": "Fira Barcelona, Spain",
        "city": "Barcelona",
        "country": "Spain",
        "url": "https://www.smartcityexpo.com/",
        "category": "Smart City / Urban Tech",
        "description": (
            "Leading smart-city congress — urban data, mobility, energy, digital government. "
            "Organizer Fira Barcelona; press smartcityexpo.comms@firabarcelona.com."
        ),
        "tags": ["SmartCity", "Urban", "Data", "Flagship"],
    },
    {
        "title": "Big Data Conference Europe 2026",
        "start_at": "2026-11-24",
        "end_at": "2026-11-27",
        "location": "Vilnius & Online",
        "city": "Vilnius",
        "country": "Lithuania",
        "url": "https://bigdataconference.eu/",
        "category": "Data Engineering / Analytics",
        "description": "Practitioner big-data / analytics conference. info@bigdataconference.eu.",
        "tags": ["DataEngineering", "Analytics", "Europe", "Flagship"],
    },
    # --- Hamburg / North Germany ---
    {
        "title": "LogiNext Germany 2026",
        "start_at": "2026-09-02",
        "end_at": "2026-09-03",
        "location": "Hamburg Messe, Hamburg",
        "city": "Hamburg",
        "country": "Germany",
        "url": "https://www.loginext.de/en/",
        "category": "Digital Logistics / Tech Exhibition",
        "description": (
            "Digital logistics innovation meetup at Hamburg Messe — software, data and "
            "automation for supply chains. Co-located week with SMM maritime fair."
        ),
        "tags": ["Logistics", "Data", "Hamburg", "Exhibition", "Flagship"],
    },
    {
        "title": "WindEnergy Hamburg 2026",
        "start_at": "2026-09-22",
        "end_at": "2026-09-25",
        "location": "Hamburg Messe, Hamburg",
        "city": "Hamburg",
        "country": "Germany",
        "url": "https://www.windenergyhamburg.com/",
        "category": "Energy / Infrastructure Trade Fair",
        "description": (
            "Global onshore & offshore wind trade fair in Hamburg — useful for energy-data, "
            "infra and industrial-software adjacency (not pure IT)."
        ),
        "tags": ["Energy", "Infrastructure", "Hamburg", "TradeFair", "Flagship"],
    },
    {
        "title": "OMR Festival 2027",
        "start_at": "2027-05-03",
        "end_at": "2027-05-05",
        "location": "Hamburg Messe, Hamburg",
        "city": "Hamburg",
        "country": "Germany",
        "url": "https://omr.com/en/events/festival/",
        "category": "Digital / Marketing Festival",
        "description": (
            "Europe's large digital-economy festival (~70k in 2026). Strong media and brand "
            "density; AI/ecommerce stages. hello@omr.com / become-an-exhibitor."
        ),
        "tags": ["Digital", "Marketing", "Hamburg", "Media", "Flagship"],
    },
    {
        "title": "REA — Real Estate Arena 2027",
        "start_at": "2027-06-09",
        "end_at": "2027-06-10",
        "location": "Hannover Messe / Deutsche Messe, Hannover",
        "city": "Hannover",
        "country": "Germany",
        "url": "https://www.real-estate-arena.com/",
        "category": "Real Estate Trade Fair",
        "description": (
            "Germany's property fair & future conference (rebranded REA). Not Hamburg — "
            "north-German RE hub ~1.5h from Hamburg; 2026 edition early June already passed."
        ),
        "tags": ["RealEstate", "Hannover", "Germany", "TradeFair", "Flagship"],
    },
    # --- Prague / Czechia ---
    {
        "title": "FOR ARCH 2026",
        "start_at": "2026-09-16",
        "end_at": "2026-09-19",
        "location": "PVA EXPO PRAHA, Prague",
        "city": "Prague",
        "country": "Czechia",
        "url": "https://forarch.cz/",
        "category": "Construction / Architecture Trade Fair",
        "description": (
            "Largest Czech construction fair (~39k visitors). Smart/sustainable buildings; "
            "new Fórum Stavebnictví. Organizer ABF — kontakty on forarch.cz."
        ),
        "tags": ["Construction", "Prague", "TradeFair", "PropTech", "Flagship"],
    },
    {
        "title": "Construction Connect Prague 2026",
        "start_at": "2026-09-17",
        "end_at": "2026-09-19",
        "location": "PVA EXPO PRAHA (with FOR ARCH), Prague",
        "city": "Prague",
        "country": "Czechia",
        "url": "https://www.b2match.com/e/construction-connect-prague-2026",
        "category": "Construction B2B Matchmaking",
        "description": (
            "B2B matchmaking alongside FOR ARCH — investors and construction/tech partners. "
            "Free registration via b2match."
        ),
        "tags": ["Construction", "B2B", "Prague", "Matchmaking", "Flagship"],
    },
    {
        "title": "Machine Learning Prague 2027",
        "start_at": "2027-05-03",
        "end_at": "2027-05-05",
        "location": "O2 Universum, Prague",
        "city": "Prague",
        "country": "Czechia",
        "url": "https://www.mlprague.com/",
        "category": "AI / Machine Learning",
        "description": (
            "12th ML/AI practitioner conference (~800+). Strong engineering depth. "
            "info@mlprague.com — note same dates as OMR Hamburg 2027."
        ),
        "tags": ["AI", "ML", "Prague", "Engineering", "Flagship"],
    },
    {
        "title": "WebExpo 2027",
        "start_at": "2027-05-26",
        "end_at": "2027-05-28",
        "location": "Prague, Czechia",
        "city": "Prague",
        "country": "Czechia",
        "url": "https://webexpo.net/",
        "category": "Web / Product / Software",
        "description": "Major CEE web/product conference. info@webexpo.net; partners via eva@ / sarka@.",
        "tags": ["Software", "Web", "Prague", "Product", "Flagship"],
    },
    # --- Bratislava / Slovakia ---
    {
        "title": "Jesenná ITAPA 2026",
        "start_at": "2026-11-24",
        "end_at": "2026-11-26",
        "location": "Crowne Plaza Bratislava",
        "city": "Bratislava",
        "country": "Slovakia",
        "url": "https://www.itapa.sk/jesenna-itapa-2026/",
        "category": "Digitalisation / GovTech / IT",
        "description": (
            "Slovakia's leading tech & digitalisation conference (autumn edition). "
            "Public sector + vendors. Partner: itapa@itapa.sk."
        ),
        "tags": ["Digital", "GovTech", "Bratislava", "IT", "Flagship"],
    },
]


def build_events(after_date: datetime | None) -> list[dict[str, Any]]:
    out: list[dict[str, Any]] = []
    for raw in FLAGSHIP_EVENTS:
        start_dt = datetime.fromisoformat(raw["start_at"])
        end_dt = datetime.fromisoformat(raw["end_at"])
        if after_date and start_dt.date() <= after_date.date():
            continue
        out.append(
            {
                "source_name": SOURCE_NAME,
                "source_label": SOURCE_LABEL,
                "title": raw["title"][:255],
                "start_at": start_dt.isoformat(),
                "end_at": end_dt.isoformat(),
                "date_text": f"{raw['start_at']} – {raw['end_at']}",
                "location": raw["location"],
                "city": raw["city"],
                "country": raw["country"],
                "url": raw["url"],
                "image_url": "",
                "organizer": SOURCE_LABEL,
                "category": raw["category"],
                "description": raw["description"],
                "attendees_count": None,
                "source_url": SOURCE_URL,
                "tags": raw["tags"],
            }
        )
    out.sort(key=lambda e: e["start_at"])
    return out


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--after-date", default="")
    parser.add_argument("--output", required=True)
    args = parser.parse_args()
    after = datetime.fromisoformat(args.after_date) if args.after_date else None
    events = build_events(after)
    payload = {
        "source_name": SOURCE_NAME,
        "source_label": SOURCE_LABEL,
        "source_url": SOURCE_URL,
        "scraped_at": datetime.now().isoformat(),
        "total_events": len(events),
        "events": events,
        "errors": [],
        "meta": {"mode": "curated_flagship", "status": "ok" if events else "no_future_events_after_filter"},
    }
    path = Path(args.output)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"Source: {SOURCE_LABEL}")
    print(f"Events extracted: {len(events)}")
    for event in events:
        print(f" - {event['start_at'][:10]} [{event['city']}] {event['title']}")


if __name__ == "__main__":
    main()
