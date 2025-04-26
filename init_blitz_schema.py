#!/usr/bin/env python3
import psycopg2
from dotenv import load_dotenv
import os

load_dotenv()

def init_blitz_schema():
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
        cur.execute("CREATE SCHEMA IF NOT EXISTS blitz;")
        tickers = [
            'sp500_yahoo', 'sp500_tinkoff',
            'eurrub_yahoo', 'eurrub_tinkoff',
            'moex_yahoo', 'moex_tinkoff',
            'sber_tinkoff',
            'usdrub', 'brent', 'urals'
        ]
        for ticker in tickers:
            cur.execute(f"""
                CREATE TABLE IF NOT EXISTS blitz.{ticker} (
                    id SERIAL PRIMARY KEY,
                    value NUMERIC,
                    source VARCHAR(64),
                    timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                );
            """)
        conn.commit()
        print("Blitz schema and tables created.")
    except Exception as e:
        print("Error initializing blitz schema:", e)
    finally:
        if 'cur' in locals():
            cur.close()
        if 'conn' in locals():
            conn.close()

if __name__ == '__main__':
    init_blitz_schema() 