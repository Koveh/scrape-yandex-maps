"""Shared event image pipeline: download, resize, convert to AVIF, upload to MinIO."""

from __future__ import annotations

import io
import logging
import os
import re
from hashlib import sha1
from pathlib import Path
from typing import Any
from urllib.parse import unquote, urlparse

import psycopg2
import requests
from minio import Minio
from minio.error import S3Error
from PIL import Image, ImageOps

try:
    import pillow_avif  # noqa: F401 — registers AVIF save handler for Pillow
except ImportError:
    pillow_avif = None  # type: ignore[assignment]

PUBLIC_BASE_URL = "https://files.koveh.com"
EVENTS_BUCKET = "events"
ADMIN_BUCKET = "events-images"
_RAW_MINIO_ENDPOINT = os.environ.get("MINIO_ENDPOINT", "65.109.88.77:9000")
_MINIO_PORT = os.environ.get("MINIO_PORT", "9000")
MINIO_ACCESS_KEY = os.environ.get("MINIO_ACCESS_KEY") or os.environ.get("MINIO_ROOT_USER", "koveh")
MINIO_SECRET_KEY = (
    os.environ.get("MINIO_SECRET_KEY")
    or os.environ.get("MINIO_ROOT_PASSWORD", "Kodex8910838853")
)
# matches the old sharp settings: inside-fit 640x360, no enlargement, AVIF q62
AVIF_MAX_SIZE = (640, 360)
AVIF_QUALITY = 62

logger = logging.getLogger(__name__)


def _normalize_minio_endpoint(endpoint: str, port: str = "9000") -> str:
    """Host-only MINIO_ENDPOINT (from koveh .env) must keep :9000 — bare host hits :80."""
    value = (endpoint or "").strip()
    if not value:
        return f"65.109.88.77:{port}"
    if "://" in value:
        value = value.split("://", 1)[1]
    value = value.rstrip("/")
    if ":" not in value:
        return f"{value}:{port}"
    return value


MINIO_ENDPOINT = _normalize_minio_endpoint(_RAW_MINIO_ENDPOINT, _MINIO_PORT)


def backfill_event_images(dsn: str | None = None) -> int:
    connection_dsn = dsn or os.environ.get("POSTGRES_URL") or os.environ.get("DATABASE_URL")
    if not connection_dsn:
        raise RuntimeError("POSTGRES_URL or DATABASE_URL must be set")

    client = create_minio_client()
    updated = 0
    query = """
        SELECT id, image_url
        FROM events
        WHERE image_url IS NOT NULL
          AND image_url <> ''
          AND NOT (
            image_url LIKE 'https://files.koveh.com/%'
            AND image_url LIKE '%.avif'
          )
          AND hidden = false
        ORDER BY CASE WHEN image_url LIKE 'https://files.koveh.com/%' THEN 0 ELSE 1 END, id
    """
    with psycopg2.connect(connection_dsn) as conn:
        with conn.cursor() as cur:
            cur.execute(query)
            rows = cur.fetchall()

        for event_id, image_url in rows:
            try:
                new_url = ensure_event_image_url(client, image_url)
            except (OSError, S3Error, ValueError, requests.RequestException) as error:
                logger.warning("skip event %s: %s", event_id, error)
                continue
            if not new_url or new_url == image_url:
                continue
            with conn.cursor() as cur:
                cur.execute(
                    "UPDATE events SET image_url = %s, updated_at = CURRENT_TIMESTAMP WHERE id = %s",
                    (new_url, event_id),
                )
                cur.execute(
                    """
                    UPDATE events_normalized
                    SET image_url = %s, updated_at = CURRENT_TIMESTAMP
                    WHERE source_event_id = %s
                    """,
                    (new_url, event_id),
                )
            conn.commit()
            updated += 1
            print(f"   ♻️ {event_id}: {os.path.basename(image_url)} -> {os.path.basename(new_url)}", flush=True)

    print(f"✅ Backfilled {updated} event image URLs to AVIF")
    return updated


def convert_bytes_to_avif(image_bytes: bytes) -> bytes:
    if pillow_avif is None:
        raise RuntimeError("pillow-avif-plugin is not installed in this environment")
    if not image_bytes:
        raise ValueError("empty image payload")
    with Image.open(io.BytesIO(image_bytes)) as img:
        img = ImageOps.exif_transpose(img)  # honor EXIF orientation, like sharp.rotate()
        if img.mode not in ("RGB", "RGBA"):
            img = img.convert("RGBA" if "A" in img.getbands() else "RGB")
        img.thumbnail(AVIF_MAX_SIZE)  # inside-fit, never enlarges
        out = io.BytesIO()
        img.save(out, format="AVIF", quality=AVIF_QUALITY)
    payload = out.getvalue()
    if not payload:
        raise ValueError("AVIF conversion returned empty output")
    return payload


def create_minio_client() -> Minio:
    # Re-read env each call: dotenv may load after import with host-only MINIO_ENDPOINT.
    endpoint = _normalize_minio_endpoint(
        os.environ.get("MINIO_ENDPOINT", MINIO_ENDPOINT),
        os.environ.get("MINIO_PORT", _MINIO_PORT),
    )
    access = (
        os.environ.get("MINIO_ACCESS_KEY")
        or os.environ.get("MINIO_ROOT_USER")
        or MINIO_ACCESS_KEY
    )
    secret = (
        os.environ.get("MINIO_SECRET_KEY")
        or os.environ.get("MINIO_ROOT_PASSWORD")
        or MINIO_SECRET_KEY
    )
    return Minio(endpoint, access_key=access, secret_key=secret, secure=False)


def ensure_event_image_url(
    client: Minio,
    source_url: str | None,
    object_prefix: str | None = None,
    object_name: str | None = None,
) -> str | None:
    normalized = (source_url or "").strip()
    if not normalized:
        return None
    if is_display_image_url(normalized):
        return normalized

    try:
        payload = fetch_image_bytes(client, normalized)
        if object_name:
            target_name = object_name
        else:
            prefix = object_prefix or infer_object_prefix(normalized)
            target_name = build_avif_object_name(prefix, normalized)
        return upload_avif_object(client, EVENTS_BUCKET, target_name, payload)
    except Exception as exc:
        # AVIF optimization is best-effort (needs node+sharp, absent in the Airflow worker).
        # Don't let it abort the events DB sync — fall back to the original image URL.
        print(f"   ⚠️ image optimize failed ({type(exc).__name__}: {exc}); using original URL", flush=True)
        return normalized


def fetch_image_bytes(client: Minio, source_url: str) -> bytes:
    object_name = object_name_from_public_url(source_url, EVENTS_BUCKET)
    if object_name:
        response = client.get_object(EVENTS_BUCKET, object_name)
        try:
            return response.read()
        finally:
            response.close()
            response.release_conn()

    admin_object = object_name_from_public_url(source_url, ADMIN_BUCKET)
    if admin_object:
        response = client.get_object(ADMIN_BUCKET, admin_object)
        try:
            return response.read()
        finally:
            response.close()
            response.release_conn()

    response = requests.get(source_url, timeout=15)
    response.raise_for_status()
    return response.content


def build_avif_object_name(prefix: str, source_url: str) -> str:
    canonical = source_url.split("?", 1)[0]
    digest = sha1(canonical.encode("utf-8")).hexdigest()[:16]
    slug_source = Path(unquote(urlparse(canonical).path)).stem or "event"
    slug = re.sub(r"[^a-z0-9]+", "-", slug_source.lower()).strip("-")[:80] or "event"
    return f"{prefix.rstrip('/')}/{slug}-{digest}.avif"


def infer_object_prefix(source_url: str) -> str:
    object_name = object_name_from_public_url(source_url, EVENTS_BUCKET)
    if object_name and "/" in object_name:
        return object_name.rsplit("/", 1)[0]
    host = urlparse(source_url).netloc.lower()
    if "networkly" in host:
        return "networkly/imported"
    if "luma" in host:
        return "luma/imported"
    if "it-event-hub" in host:
        return "it-event-hub/imported"
    return "imported"


def is_display_image_url(source_url: str) -> bool:
    normalized = source_url.lower().split("?", 1)[0]
    return normalized.endswith(".avif") and normalized.startswith(PUBLIC_BASE_URL.lower())


def object_name_from_public_url(source_url: str, bucket_name: str) -> str | None:
    marker = f"{PUBLIC_BASE_URL}/{bucket_name}/"
    if marker not in source_url:
        return None
    tail = source_url.split(marker, 1)[1]
    return unquote(tail.split("?", 1)[0])


def upload_avif_bytes(
    client: Minio,
    bucket_name: str,
    object_name: str,
    image_bytes: bytes,
) -> str:
    payload = convert_bytes_to_avif(image_bytes)
    return upload_avif_object(client, bucket_name, object_name, payload)


def upload_avif_object(
    client: Minio,
    bucket_name: str,
    object_name: str,
    source_bytes: bytes,
) -> str:
    if not client.bucket_exists(bucket_name):
        client.make_bucket(bucket_name)

    try:
        stat = client.stat_object(bucket_name, object_name)
        if stat:
            return f"{PUBLIC_BASE_URL}/{bucket_name}/{object_name}"
    except S3Error:
        pass

    payload = convert_bytes_to_avif(source_bytes)
    client.put_object(
        bucket_name,
        object_name,
        data=io.BytesIO(payload),
        length=len(payload),
        content_type="image/avif",
    )
    return f"{PUBLIC_BASE_URL}/{bucket_name}/{object_name}"


def upload_local_file_as_avif(
    client: Minio,
    bucket_name: str,
    object_name: str,
    local_file: str,
) -> str:
    with open(local_file, "rb") as file:
        source_bytes = file.read()
    return upload_avif_bytes(client, bucket_name, object_name, source_bytes)


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    backfill_event_images()
