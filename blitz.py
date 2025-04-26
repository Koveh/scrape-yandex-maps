from dotenv import load_dotenv
import os
import time
import psycopg2
import schedule
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
    'BANEP', 'BSPB', 'CBOM', 'ENPG', 'FEES',  'LSRG', 'MVID', 'OGKB',
    'QIWI', 'RNFT', 'RASP', 'SIBN', 'TGKA', 'UNAC', 'YAKG',
    'EURRUB', 'MOEX', 'USD000UTSTOM', 'EUR_RUB__TOM', 'USDRUB'
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

def create_table_if_not_exists(ticker):
    conn = connect_db()
    cur = conn.cursor()
    cur.execute(f"""
        CREATE TABLE IF NOT EXISTS {DB_SCHEMA}.{ticker.lower()} (
            id SERIAL PRIMARY KEY,
            price FLOAT,
            name TEXT,
            currency TEXT,
            updated_at TIMESTAMP
        );
    """)
    conn.commit()
    cur.close()
    conn.close()

def get_all_shares_and_currencies():
    with Client(TINKOFF_TOKEN) as client:
        shares = client.instruments.shares().instruments
        currencies = client.instruments.currencies().instruments
        return shares, currencies

def get_share_by_ticker_variants(ticker, shares):
    variants = [
        ticker,
        ticker.replace('RUB', '_RUB__TOM'),
        ticker.replace('EUR', 'EUR_RUB__TOM'),
        ticker.replace('USD', 'USD000UTSTOM'),
        ticker + '_TOM',
        ticker + '.ME',
        ticker.replace('_', ''),
        ticker.replace('-', ''),
        ticker.upper(),
        ticker.lower(),
        ticker.capitalize(),
    ]
    if ticker == 'MOEX':
        variants += ['IMOEX', 'IMOEX.ME']
    if ticker == 'EURRUB':
        variants += ['EUR_RUB__TOM', 'EURRUB_TOM', 'EUR_RUB_TOM', 'USD000UTSTOM']
    if ticker == 'SBER':
        variants += ['SBERP', 'SBER.ME']
    for v in variants:
        for share in shares:
            if share.ticker.upper() == v.upper():
                return share
    for share in shares:
        if ticker.lower() in share.name.lower():
            return share
    return None

def get_currency_by_ticker_variants(ticker, currencies):
    variants = [
        ticker,
        ticker.replace('RUB', '_RUB__TOM'),
        ticker.replace('EUR', 'EUR_RUB__TOM'),
        ticker.replace('USD', 'USD000UTSTOM'),
        ticker + '_TOM',
        ticker + '.ME',
        ticker.replace('_', ''),
        ticker.replace('-', ''),
        ticker.upper(),
        ticker.lower(),
        ticker.capitalize(),
        'USD000UTSTOM', 'EUR_RUB__TOM', 'USDRUB_TOM', 'EURRUB_TOM'
    ]
    for v in variants:
        for cur in currencies:
            if cur.ticker.upper() == v.upper():
                return cur
    for cur in currencies:
        if ticker.lower() in cur.name.lower():
            return cur
    return None

def get_last_price(figi):
    with Client(TINKOFF_TOKEN) as client:
        prices = client.market_data.get_last_prices(figi=[figi]).last_prices
        if prices:
            price = prices[0].price
            return float(price.units) + price.nano / 1e9
    return None

def insert_to_blitz_table(ticker, price):
    blitz_map = {
        'SBER': 'sber_tinkoff',
        'EURRUB': 'eurrub_tinkoff',
        'USDRUB': 'usdrub_tinkoff',
        'MOEX': 'moex_tinkoff',
    }
    table = blitz_map.get(ticker.upper())
    if not table:
        return
    conn = connect_db()
    cur = conn.cursor()
    cur.execute(f"""
        CREATE TABLE IF NOT EXISTS blitz.{table} (
            id SERIAL PRIMARY KEY,
            value NUMERIC,
            source VARCHAR(64),
            timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );
    """)
    cur.execute(f"INSERT INTO blitz.{table} (value, source) VALUES (%s, %s)", (price, 'tinkoff'))
    conn.commit()
    cur.close()
    conn.close()

def update_company(ticker, instrument):
    create_table_if_not_exists(ticker)
    figi, name, currency = instrument.figi, instrument.name, instrument.currency
    price = get_last_price(figi)
    if price is None:
        print(f'No price for {ticker}')
        return
    conn = connect_db()
    cur = conn.cursor()
    cur.execute(
        f"INSERT INTO {DB_SCHEMA}.{ticker.lower()} (price, name, currency, updated_at) VALUES (%s, %s, %s, %s)",
        (price, name, currency, datetime.now())
    )
    conn.commit()
    cur.close()
    conn.close()
    print(f'Updated {ticker}')
    insert_to_blitz_table(ticker, price)

def update_all():
    shares, currencies = get_all_shares_and_currencies()
    with ThreadPoolExecutor(max_workers=4) as executor:
        futures = []
        for ticker in TICKERS:
            instrument = get_share_by_ticker_variants(ticker, shares)
            if not instrument:
                instrument = get_currency_by_ticker_variants(ticker, currencies)
            if not instrument:
                print(f'No instrument found for {ticker}')
                continue
            futures.append(executor.submit(update_company, ticker, instrument))
        for future in as_completed(futures):
            future.result()

if __name__ == '__main__':
    create_schema_if_not_exists()
    update_all()
    schedule.every(1).hours.do(update_all)
    while True:
        schedule.run_pending()
        time.sleep(10) 