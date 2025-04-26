import os
import requests

API_KEY = os.getenv("FINNHUB_KEY")
TICKER = "OZON"
if not API_KEY:
    print("FINNHUB_KEY not set")
    exit(1)
url = f"https://finnhub.io/api/v1/quote?symbol={TICKER}&token={API_KEY}"
resp = requests.get(url)
if resp.status_code != 200:
    print("Request error")
    exit(1)
data = resp.json()
if "c" in data and data["c"]:
    print({"ticker": TICKER, "close": data["c"]})
else:
    print("Not found or error") 