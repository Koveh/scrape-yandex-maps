from dotenv import load_dotenv
import os
import time
import psycopg2
from datetime import datetime
from tinkoff.invest import Client
from concurrent.futures import ThreadPoolExecutor, as_completed

load_dotenv()

DB_NAME = os.getenv('POSTGRES_DB', 'investments_koveh')
DB_USER = os.getenv('POSTGRES_USER', 'postgres')
DB_PASSWORD = os.getenv('POSTGRES_PASSWORD')
DB_HOST = os.getenv('POSTGRES_HOST', 'localhost')
DB_PORT = os.getenv('POSTGRES_PORT', '5432')
DB_SCHEMA = 'russian_stocks'
TINKOFF_TOKEN = os.getenv('TINKOFF_TOKEN')

TICKERS = [
    'GAZP', 'SBER', 'LKOH', 'TATN', 'PIKK', 'MGNT', 'ROSN', 'NVTK', 'PLZL',
    'ALRS', 'GMKN', 'MTSS', 'MOEX', 'PHOR', 'SNGS', 'SNGSP', 'VTBR', 'AFLT', 'CHMF',
    'X5', 'IRAO', 'MAGN', 'RUAL', 'RTKM', 'RTKMP', 'TRNFP', 'UPRO', 'VSMO',
    'BANEP', 'BSPB', 'CBOM', 'ENPG', 'FEES', 'LSRG', 'MVID', 'OGKB',
    'QIWI', 'RNFT', 'RASP', 'SIBN', 'TGKA', 'UNAC', 'YAKG'
]

def connect_db():
    return psycopg2.connect(
        dbname=DB_NAME,
        user=DB_USER,
        password=DB_PASSWORD,
        host=DB_HOST,
        port=DB_PORT
    )

def create_schema_if_not_exists():
    conn = connect_db()
    cur = conn.cursor()
    cur.execute(f"CREATE SCHEMA IF NOT EXISTS {DB_SCHEMA};")
    conn.commit()
    cur.close()
    conn.close()

def create_fullinfo_table():
    conn = connect_db()
    cur = conn.cursor()
    cur.execute(f"""
        CREATE TABLE IF NOT EXISTS {DB_SCHEMA}.fullinfo (
            id SERIAL PRIMARY KEY,
            ticker TEXT,
            figi TEXT,
            name TEXT,
            isin TEXT,
            lot BIGINT,
            currency TEXT,
            sector TEXT,
            country TEXT,
            exchange TEXT,
            ipo_date DATE,
            issue_size BIGINT,
            updated_at TIMESTAMP
        );
    """)
    conn.commit()
    cur.close()
    conn.close()

def get_all_shares():
    with Client(TINKOFF_TOKEN) as client:
        return {share.ticker: share for share in client.instruments.shares().instruments}

def insert_fullinfo(share):
    conn = connect_db()
    cur = conn.cursor()
    cur.execute(
        f"""INSERT INTO {DB_SCHEMA}.fullinfo
        (ticker, figi, name, isin, lot, currency, sector, country, exchange, ipo_date, issue_size, updated_at)
        VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)""",
        (
            share.ticker,
            share.figi,
            share.name,
            share.isin,
            share.lot,
            share.currency,
            share.sector,
            share.country_of_risk_name,
            share.exchange,
            share.ipo_date.date() if share.ipo_date else None,
            share.issue_size,
            datetime.now()
        )
    )
    conn.commit()
    cur.close()
    conn.close()
    print(f'Inserted full info for {share.ticker}')

def update_all_fullinfo():
    shares = get_all_shares()
    with ThreadPoolExecutor(max_workers=8) as executor:
        futures = []
        for ticker in TICKERS:
            share = shares.get(ticker)
            if not share:
                print(f'No share for {ticker}')
                continue
            futures.append(executor.submit(insert_fullinfo, share))
        for future in as_completed(futures):
            future.result()

if __name__ == '__main__':
    create_schema_if_not_exists()
    create_fullinfo_table()
    update_all_fullinfo() 