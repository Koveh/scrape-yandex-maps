#!/usr/bin/env python3
import os
import time
import psycopg2
import schedule
from datetime import datetime
from dotenv import load_dotenv

# Для Yahoo Finance
import yfinance as yf
# Для Tinkoff (используем requests, если нет официального SDK)
import requests

load_dotenv()

DB_NAME = os.getenv('POSTGRES_DB', 'investments_koveh')
DB_USER = os.getenv('POSTGRES_USER', 'postgres')
DB_PASSWORD = os.getenv('POSTGRES_PASSWORD')
DB_HOST = os.getenv('POSTGRES_HOST', 'localhost')
DB_PORT = os.getenv('POSTGRES_PORT', '5432')

# Tinkoff API токен (если есть)
TINKOFF_TOKEN = os.getenv('TINKOFF_TOKEN', '')

# Маппинг тикеров и источников
TICKERS = [
    # (table, source, fetch_func)
    ('sp500_yahoo', 'yahoo', lambda: get_yahoo_price('^GSPC')),
    ('eurrub_yahoo', 'yahoo', lambda: get_yahoo_price('EURRUB=X')),
    ('moex_yahoo', 'yahoo', lambda: get_yahoo_price('IMOEX.ME')),
    ('usdrub', 'yahoo', lambda: get_yahoo_price('USDRUB=X')),
    ('brent', 'yahoo', lambda: get_yahoo_price('BZ=F')),
    ('urals', 'yahoo', lambda: get_yahoo_price('URALS.ICE')),
    # Tinkoff
    ('sp500_tinkoff', 'tinkoff', lambda: get_tinkoff_price('SPYF')),
    ('eurrub_tinkoff', 'tinkoff', lambda: get_tinkoff_price('EUR_RUB__TOM')),
    ('moex_tinkoff', 'tinkoff', lambda: get_tinkoff_price('IMOEX')),
    ('sber_tinkoff', 'tinkoff', lambda: get_tinkoff_price('SBER')),
]

def connect_db():
    return psycopg2.connect(
        dbname=DB_NAME,
        user=DB_USER,
        password=DB_PASSWORD,
        host=DB_HOST,
        port=DB_PORT
    )

def get_yahoo_price(ticker):
    try:
        data = yf.Ticker(ticker).history(period='1d')
        if not data.empty:
            return float(data['Close'].iloc[-1])
    except Exception as e:
        print(f"Yahoo error {ticker}: {e}")
    return None

def get_tinkoff_price(ticker):
    # Пример для публичного API tinkoff.ru/invest (можно заменить на официальный SDK)
    try:
        url = f'https://invest-public-api.tinkoff.ru/rest/market/candles?figi={ticker}&interval=1min&from=2024-01-01T00:00:00Z&to=2025-01-01T00:00:00Z'
        headers = {'Authorization': f'Bearer {TINKOFF_TOKEN}'} if TINKOFF_TOKEN else {}
        r = requests.get(url, headers=headers)
        if r.ok:
            js = r.json()
            if 'payload' in js and 'candles' in js['payload'] and js['payload']['candles']:
                return float(js['payload']['candles'][-1]['c'])
    except Exception as e:
        print(f"Tinkoff error {ticker}: {e}")
    return None

def fetch_and_store():
    conn = connect_db()
    cur = conn.cursor()
    for table, source, fetch_func in TICKERS:
        value = fetch_func()
        if value is not None:
            try:
                cur.execute(f"INSERT INTO blitz.{table} (value, source) VALUES (%s, %s)", (value, source))
                conn.commit()
                print(f"Inserted {value} into blitz.{table} from {source}")
            except Exception as e:
                conn.rollback()
                print(f"DB error {table}: {e}")
    cur.close()
    conn.close()

if __name__ == '__main__':
    import sys
    if 'once' in sys.argv:
        fetch_and_store()
    else:
        schedule.every(2).minutes.do(fetch_and_store)
        while True:
            schedule.run_pending()
            time.sleep(1) 