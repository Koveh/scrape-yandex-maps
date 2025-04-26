import requests
import re

TICKER = "OZON"
url = f"https://quote.rbc.ru/ticker/{TICKER}"  # URL для карточки акции
resp = requests.get(url)
if resp.status_code != 200:
    print("Request error")
    exit(1)
m = re.search(r'"currentPrice":\s*([\d.]+)', resp.text)
if m:
    print({"ticker": TICKER, "price": float(m.group(1))})
else:
    print("Not found") 