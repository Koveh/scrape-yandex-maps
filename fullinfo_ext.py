from dotenv import load_dotenv
import os
import psycopg2
from datetime import datetime
from tinkoff.invest import Client, SecurityTradingStatus
from concurrent.futures import ThreadPoolExecutor, as_completed
import yfinance as yf

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

def create_fullinfo_ext_table():
    conn = connect_db()
    cur = conn.cursor()
    cur.execute(f"""
        CREATE TABLE IF NOT EXISTS {DB_SCHEMA}.fullinfo_ext (
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
            issue_size_plan BIGINT,
            nominal FLOAT,
            trading_status TEXT,
            buy_available BOOLEAN,
            sell_available BOOLEAN,
            short_enabled BOOLEAN,
            api_trade_available BOOLEAN,
            min_price_increment FLOAT,
            risk_level TEXT,
            for_qual_investor BOOLEAN,
            last_price FLOAT,
            market_cap BIGINT,
            pe_ratio FLOAT,
            forward_pe FLOAT,
            beta FLOAT,
            eps FLOAT,
            pb_ratio FLOAT,
            dividend_yield FLOAT,
            roe FLOAT,
            roa FLOAT,
            debt_to_equity FLOAT,
            revenue BIGINT,
            net_income BIGINT,
            employees BIGINT,
            target_price FLOAT,
            analyst_rating TEXT,
            industry TEXT,
            website TEXT,
            updated_at TIMESTAMP
        );
    """)
    conn.commit()
    cur.close()
    conn.close()

def safe_get(obj, attr, default=None):
    return getattr(obj, attr, default)

def get_all_shares():
    with Client(TINKOFF_TOKEN) as client:
        return {share.ticker: share for share in client.instruments.shares().instruments}

def get_last_prices(figis):
    with Client(TINKOFF_TOKEN) as client:
        prices = client.market_data.get_last_prices(figi=figis).last_prices
        return {p.figi: float(p.price.units) + p.price.nano / 1e9 for p in prices}

def get_yahoo_metrics(ticker):
    try:
        t = yf.Ticker(ticker + ".ME")
        info = t.info
        return {
            "market_cap": info.get("marketCap"),
            "pe_ratio": info.get("trailingPE"),
            "forward_pe": info.get("forwardPE"),
            "beta": info.get("beta"),
            "eps": info.get("trailingEps"),
            "pb_ratio": info.get("priceToBook"),
            "dividend_yield": info.get("dividendYield"),
            "roe": info.get("returnOnEquity"),
            "roa": info.get("returnOnAssets"),
            "debt_to_equity": info.get("debtToEquity"),
            "revenue": info.get("totalRevenue"),
            "net_income": info.get("netIncomeToCommon"),
            "employees": info.get("fullTimeEmployees"),
            "target_price": info.get("targetMeanPrice"),
            "analyst_rating": info.get("recommendationKey"),
            "industry": info.get("industry"),
            "website": info.get("website"),
        }
    except Exception as e:
        print(f"Yahoo error for {ticker}: {e}")
        return {}

def insert_fullinfo_ext(share, last_price=None):
    try:
        yahoo = get_yahoo_metrics(share.ticker)
        conn = connect_db()
        cur = conn.cursor()
        values = (
            share.ticker,
            share.figi,
            share.name,
            safe_get(share, 'isin'),
            safe_get(share, 'lot'),
            safe_get(share, 'currency'),
            safe_get(share, 'sector'),
            safe_get(share, 'country_of_risk_name'),
            safe_get(share, 'exchange'),
            share.ipo_date.date() if safe_get(share, 'ipo_date') else None,
            safe_get(share, 'issue_size'),
            safe_get(share, 'issue_size_plan'),
            float(safe_get(share, 'nominal').units) + safe_get(share, 'nominal').nano / 1e9 if safe_get(share, 'nominal') else None,
            SecurityTradingStatus(safe_get(share, 'trading_status')).name if safe_get(share, 'trading_status') else None,
            safe_get(share, 'buy_available_flag'),
            safe_get(share, 'sell_available_flag'),
            safe_get(share, 'short_enabled_flag'),
            safe_get(share, 'api_trade_available_flag'),
            float(safe_get(share, 'min_price_increment').units) + safe_get(share, 'min_price_increment').nano / 1e9 if safe_get(share, 'min_price_increment') else None,
            safe_get(share, 'risk_level'),
            safe_get(share, 'for_qual_investor'),
            last_price,
            yahoo.get("market_cap"),
            yahoo.get("pe_ratio"),
            yahoo.get("forward_pe"),
            yahoo.get("beta"),
            yahoo.get("eps"),
            yahoo.get("pb_ratio"),
            yahoo.get("dividend_yield"),
            yahoo.get("roe"),
            yahoo.get("roa"),
            yahoo.get("debt_to_equity"),
            yahoo.get("revenue"),
            yahoo.get("net_income"),
            yahoo.get("employees"),
            yahoo.get("target_price"),
            yahoo.get("analyst_rating"),
            yahoo.get("industry"),
            yahoo.get("website"),
            datetime.now()
        )
        if len(values) != 40:
            print(f"[DEBUG] {share.ticker}: values count = {len(values)}")
            for i, v in enumerate(values):
                print(f"  {i+1}: {v}")
            raise Exception(f"Values count mismatch: {len(values)} != 40")
        cur.execute(
            f"""INSERT INTO {DB_SCHEMA}.fullinfo_ext
            (ticker, figi, name, isin, lot, currency, sector, country, exchange, ipo_date, issue_size, issue_size_plan,
             nominal, trading_status, buy_available, sell_available, short_enabled, api_trade_available, min_price_increment,
             risk_level, for_qual_investor, last_price, market_cap, pe_ratio, forward_pe, beta, eps, pb_ratio, dividend_yield,
             roe, roa, debt_to_equity, revenue, net_income, employees, target_price, analyst_rating, industry, website, updated_at)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)""",
            values
        )
        conn.commit()
        cur.close()
        conn.close()
        print(f'Inserted EXT full info for {share.ticker}')
    except Exception as e:
        print(f'Error for {share.ticker}: {e}')

def update_all_fullinfo_ext():
    shares = get_all_shares()
    figis = [share.figi for share in shares.values() if share]
    last_prices = get_last_prices(figis)
    with ThreadPoolExecutor(max_workers=8) as executor:
        futures = []
        for ticker in TICKERS:
            share = shares.get(ticker)
            if not share:
                print(f'No share for {ticker}')
                continue
            price = last_prices.get(share.figi)
            futures.append(executor.submit(insert_fullinfo_ext, share, price))
        for future in as_completed(futures):
            future.result()

if __name__ == '__main__':
    create_schema_if_not_exists()
    create_fullinfo_ext_table()
    update_all_fullinfo_ext() 