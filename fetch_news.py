#!/usr/bin/env python3
import os
import time
import psycopg2
import feedparser
import schedule
from datetime import datetime
from dotenv import load_dotenv
from dateutil.relativedelta import relativedelta

load_dotenv()

# Database connection parameters
DB_NAME = os.getenv('POSTGRES_DB', 'investments_koveh')
DB_USER = os.getenv('POSTGRES_USER', 'postgres')
DB_PASSWORD = os.getenv('POSTGRES_PASSWORD')
DB_HOST = os.getenv('POSTGRES_HOST', 'localhost')
DB_PORT = os.getenv('POSTGRES_PORT', '5432')

# RSS sources configuration
newsSources = [
    { 'id': 'rbc',        'url': 'https://rssexport.rbc.ru/rbcnews/news/30/full.rss',                         'active': True  },
    { 'id': 'techcrunch','url': 'https://techcrunch.com/feed/',                                               'active': True },
    { 'id': 'reuters',   'url': 'https://news.google.com/rss/search?q=Reuters+technology&hl=en-US&gl=US&ceid=US:en',    'active': True },
    { 'id': 'wsj',       'url': 'https://feeds.a.dj.com/rss/RSSWSJD.xml',                                     'active': True  },
    { 'id': 'rt',        'url': 'https://www.rt.com/rss/news/',                                                'active': True  },
]


def connect_db():
    return psycopg2.connect(
        dbname=DB_NAME,
        user=DB_USER,
        password=DB_PASSWORD,
        host=DB_HOST,
        port=DB_PORT
    )


def process_source(source):
    feed = feedparser.parse(source['url'])
    conn = connect_db()
    cur = conn.cursor()

    for entry in feed.entries:
        title = entry.get('title', '').strip()
        # choose content field
        if 'content' in entry and entry.content:
            content = entry.content[0].value
        else:
            content = entry.get('summary', '') or entry.get('description', '')

        # parse publish date/time
        published = None
        if hasattr(entry, 'published_parsed') and entry.published_parsed:
            published = datetime.fromtimestamp(time.mktime(entry.published_parsed))
        elif hasattr(entry, 'updated_parsed') and entry.updated_parsed:
            published = datetime.fromtimestamp(time.mktime(entry.updated_parsed))

        # check for duplicate title
        cur.execute(f"SELECT 1 FROM news.{source['id']} WHERE title = %s LIMIT 1", (title,))
        if cur.fetchone():
            continue
        try:
            cur.execute(
                f"INSERT INTO news.{source['id']} (title, content, published_at) VALUES (%s, %s, %s)",
                (title, content, published)
            )
            conn.commit()
            print(f"Inserted '{title}' into news.{source['id']}")
        except Exception as e:
            conn.rollback()
            print(f"Error inserting '{title}' into news.{source['id']}: {e}")

    cur.close()
    conn.close()


def fetch_all():
    for src in newsSources:
        if src.get('active'):
            process_source(src)


if __name__ == '__main__':
    # initial fetch
    fetch_all()
    # schedule every 2 minutes
    schedule.every(2).minutes.do(fetch_all)
    while True:
        schedule.run_pending()
        time.sleep(1) 