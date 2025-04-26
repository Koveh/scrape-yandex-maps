import yfinance as yf

TICKER = "OZON"

ticker = yf.Ticker(TICKER)
data = ticker.history(period="1d")
if data.empty:
    print("Not found")
else:
    last_row = data.iloc[-1]
    print({"ticker": TICKER, "close": float(last_row['Close']), "date": str(last_row.name)}) 