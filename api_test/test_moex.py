import requests

TICKER = "OZON"
url = f"https://iss.moex.com/iss/engines/stock/markets/shares/securities/{TICKER}.json"
resp = requests.get(url)
if resp.status_code != 200:
    print("Request error")
    exit(1)
data = resp.json()
try:
    secdata = data['marketdata']['data'][0]
    last = secdata[12]  # LAST
    print({"ticker": TICKER, "last": last})
except Exception as e:
    print("Not found", e) 