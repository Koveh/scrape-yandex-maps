import os
from tinkoff.invest import Client
from dotenv import load_dotenv

load_dotenv()
TOKEN = os.getenv("TINKOFF_INVEST_TOKEN")
TICKER = "OZON"

if not TOKEN:
    print("TINKOFF_INVEST_TOKEN not set")
    exit(1)

with Client(TOKEN) as client:
    instruments = client.instruments.find_instrument(query=TICKER)
    figi = None
    for instrument in instruments.instruments:
        if instrument.ticker.upper() == TICKER:
            figi = instrument.figi
            break
    if not figi:
        print("Not found")
        exit(1)
    last_price = client.market_data.get_last_prices(figi=[figi]).last_prices[0]
    price = float(last_price.price.units) + float(last_price.price.nano) / 1_000_000_000
    print({"figi": figi, "price": price, "time": str(last_price.time)}) 