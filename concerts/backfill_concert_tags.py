"""Fill empty concerts.tags from source + title. Keeps non-empty tags."""
from __future__ import annotations

import os
from functools import wraps
from typing import Callable, TypeVar

import psycopg2

from concert_tags import SOURCE_EXTRAS, SOURCE_KIND, ConcertTagger

T = TypeVar("T")
DSN = os.getenv("CONCERTS_DSN", "postgresql://koveh:Daniil77Daniil@65.109.88.77:5432/koveh")


def logged(fn: Callable[..., T]) -> Callable[..., T]:
    @wraps(fn)
    def wrapper(*args: object, **kwargs: object) -> T:
        print(f"{fn.__name__}", flush=True)
        return fn(*args, **kwargs)

    return wrapper


class ConcertTagsBackfill:
    def __init__(self, dsn: str = DSN) -> None:
        self.dsn = dsn
        self.tagger = ConcertTagger()

    @logged
    def run(self) -> int:
        conn = psycopg2.connect(self.dsn)
        conn.autocommit = True
        updated = 0
        with conn.cursor() as cur:
            cur.execute(
                """
                SELECT id, source_channel, name, COALESCE(venue, ''), COALESCE(description, '')
                FROM concerts
                WHERE cardinality(tags) = 0
                """,
            )
            rows = cur.fetchall()
            for row_id, source, name, venue, description in rows:
                tags = self.tagger.classify(source, name, venue, description)
                cur.execute(
                    "UPDATE concerts SET tags = %s, updated_at = now() WHERE id = %s AND cardinality(tags) = 0",
                    (tags, row_id),
                )
                updated += cur.rowcount
        conn.close()
        print(f"DONE empty_tagged={updated}")
        return updated

    @logged
    def merge_house_tags(self) -> int:
        sources = sorted(set(SOURCE_KIND) | set(SOURCE_EXTRAS))
        conn = psycopg2.connect(self.dsn)
        conn.autocommit = True
        updated = 0
        with conn.cursor() as cur:
            cur.execute(
                """
                SELECT id, source_channel, COALESCE(tags, '{}')
                FROM concerts
                WHERE source_channel = ANY(%s)
                """,
                (sources,),
            )
            for row_id, source, tags in cur.fetchall():
                missing = [tag for tag in self.tagger.house_tags(source) if tag not in tags]
                if not missing:
                    continue
                merged = list(tags) + missing
                cur.execute(
                    "UPDATE concerts SET tags = %s, updated_at = now() WHERE id = %s",
                    (merged, row_id),
                )
                updated += cur.rowcount
        conn.close()
        print(f"DONE house_merged={updated}")
        return updated


if __name__ == "__main__":
    fill = ConcertTagsBackfill()
    fill.run()
    fill.merge_house_tags()
