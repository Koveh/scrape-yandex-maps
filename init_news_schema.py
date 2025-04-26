#!/usr/bin/env python3
import psycopg2
from dotenv import load_dotenv
import os

load_dotenv()

def list_databases():
    try:
        conn = psycopg2.connect(
            dbname='postgres',
            user=os.getenv('POSTGRES_USER', 'postgres'),
            password=os.getenv('POSTGRES_PASSWORD'),
            host=os.getenv('POSTGRES_HOST', 'localhost'),
            port=os.getenv('POSTGRES_PORT', '5432')
        )
        cur = conn.cursor()
        cur.execute("SELECT datname FROM pg_database;")
        dbs = [row[0] for row in cur.fetchall()]
        print("Available databases:", dbs)
    except Exception as e:
        print("Error listing databases:", e)
    finally:
        if 'cur' in locals():
            cur.close()
        if 'conn' in locals():
            conn.close()


def init_news_schema():
    db_name = os.getenv('POSTGRES_DB', 'investments_koveh')
    try:
        conn = psycopg2.connect(
            dbname=db_name,
            user=os.getenv('POSTGRES_USER', 'postgres'),
            password=os.getenv('POSTGRES_PASSWORD'),
            host=os.getenv('POSTGRES_HOST', 'localhost'),
            port=os.getenv('POSTGRES_PORT', '5432')
        )
        cur = conn.cursor()
        # create schema
        cur.execute("CREATE SCHEMA IF NOT EXISTS news;")
        # create tables for each source
        sources = [
            ('rbc', 'RBC'),
            ('techcrunch', 'TechCrunch'),
            ('reuters', 'Reuters Tech'),
            ('wsj', 'WSJ Tech'),
        ]
        for table, source_name in sources:
            cur.execute(f"""
                CREATE TABLE IF NOT EXISTS news.{table} (
                    id SERIAL PRIMARY KEY,
                    title TEXT NOT NULL,
                    content TEXT,
                    source_name VARCHAR(255) NOT NULL DEFAULT '{source_name}',
                    published_at TIMESTAMP
                );
            """)
        conn.commit()
        print(f"Schema 'news' and tables created in database '{db_name}'.")
    except Exception as e:
        print("Error initializing news schema:", e)
    finally:
        if 'cur' in locals():
            cur.close()
        if 'conn' in locals():
            conn.close()


if __name__ == '__main__':
    list_databases()
    init_news_schema() 