"""Scrape Moscow concert Telegram channels into the `concerts` table as pending rows.

Photos -> AVIF (MinIO `concerts` bucket) via the shared events_image pipeline.
Curation/dedup is done downstream by the cloud `concerts-daily-curation` routine,
so this script only collects raw rows. Idempotent via UNIQUE(source_channel, source_message_id).
"""
from __future__ import annotations

import argparse
import asyncio
import os
import re
import sys
from pathlib import Path

import psycopg2
from dotenv import load_dotenv
from telethon import TelegramClient

AUTOMATION_ROOT = Path(__file__).resolve().parent.parent  # /root/automation or /opt/airflow/automation
sys.path.insert(0, str(AUTOMATION_ROOT))  # for events_image
sys.path.insert(0, str(Path(__file__).resolve().parent))
from events_image import create_minio_client, upload_avif_bytes  # noqa: E402
from concert_tags import ConcertTagger  # noqa: E402

TG_DIR = AUTOMATION_ROOT / "telegram_channel_scraper"
load_dotenv(TG_DIR / ".env")

SESSION = str(TG_DIR / "scraper_session")
CHANNELS = ["sobytiyami", "concerts_moscow", "mskevents_ru"]
DSN = os.getenv("CONCERTS_DSN", "postgresql://koveh:Daniil77Daniil@65.109.88.77:5432/koveh")
BUCKET = "concerts"

INSERT = """
    INSERT INTO concerts (source_channel, source_message_id, source_url, name,
                          description, raw_text, image_url, city, status, tags)
    VALUES (%s, %s, %s, %s, %s, %s, %s, 'Москва', 'pending', %s)
    ON CONFLICT (source_channel, source_message_id) DO NOTHING
"""


def clean_name(text: str) -> str:
    """First meaningful line, stripped of markdown, as a display name."""
    for line in text.splitlines():
        line = re.sub(r"[*_`>#\[\]]", "", line)            # markdown
        line = re.sub(r"\((?:https?|tg)://[^)]*\)", "", line)  # md link targets
        line = line.strip(" -—•|")
        if len(line) >= 3:
            return line[:255]
    return text.strip()[:255] or "Концерт"


async def scrape(limit: int, dry: bool) -> None:
    api_id = int(os.environ["TELEGRAM_API_ID"])
    api_hash = os.environ["TELEGRAM_API_HASH"]
    minio = create_minio_client()
    tagger = ConcertTagger()
    conn = psycopg2.connect(DSN)
    conn.autocommit = True

    client = TelegramClient(SESSION, api_id, api_hash)
    await client.connect()
    if not await client.is_user_authorized():
        raise SystemExit("Telegram session not authorized")

    total_new = total_seen = total_img = 0
    for ch in CHANNELS:
        ent = await client.get_entity(ch)
        new = seen = 0
        async for msg in client.iter_messages(ent, limit=limit):
            text = msg.text or ""
            if not text.strip():
                continue
            seen += 1
            url = f"https://t.me/{ch}/{msg.id}"
            image_url = None
            if msg.photo:
                try:
                    raw = await msg.download_media(file=bytes)
                    if raw:
                        image_url = upload_avif_bytes(minio, BUCKET, f"{ch}/{msg.id}.avif", raw)
                        total_img += 1
                except Exception as e:  # noqa: BLE001 - one bad image must not stop the run
                    print(f"  img skip {ch}/{msg.id}: {e}", flush=True)
            if dry:
                print(f"  [{ch}/{msg.id}] img={bool(image_url)} {clean_name(text)[:70]}")
                continue
            with conn.cursor() as cur:
                name = clean_name(text)
                tags = tagger.classify(ch, name, "", text)
                cur.execute(INSERT, (ch, msg.id, url, name, text, text, image_url, tags))
                new += cur.rowcount
        print(f"{ch}: seen={seen} inserted={new}", flush=True)
        total_new += new
        total_seen += seen

    await client.disconnect()
    conn.close()
    print(f"DONE seen={total_seen} inserted={total_new} images={total_img}")


def run_scrape(limit: int = 200) -> None:
    """Sync entry point for Airflow PythonOperator / subprocess."""
    asyncio.run(scrape(limit, dry=False))


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--limit", type=int, default=200, help="messages per channel")
    ap.add_argument("--dry", action="store_true", help="don't write, just print")
    a = ap.parse_args()
    asyncio.run(scrape(a.limit, a.dry))
