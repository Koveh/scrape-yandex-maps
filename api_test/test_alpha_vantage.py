import os
import requests

API_KEY = os.getenv("ALPHA_VANTAGE_KEY")
TICKER = "OZON"
if not API_KEY:
    print("ALPHA_VANTAGE_KEY not set")
    exit(1)
url = f"https://www.alphavantage.co/query?function=TIME_SERIES_DAILY&symbol={TICKER}&apikey={API_KEY}"
resp = requests.get(url)
if resp.status_code != 200:
    print("Request error")
    exit(1)
data = resp.json()
try:
    ts = data["Time Series (Daily)"]
    last_date = sorted(ts.keys())[-1]
    close = ts[last_date]["4. close"]
    print({"ticker": TICKER, "close": close, "date": last_date})
except Exception as e:
    print("Not found or error", e) 