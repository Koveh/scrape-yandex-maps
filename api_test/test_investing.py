try:
    import investpy
except ImportError:
    print("investpy not installed")
    exit(1)

TICKER = "OZON"
try:
    data = investpy.get_stock_recent_data(stock=TICKER, country='russia')
    last_row = data.iloc[-1]
    print({"ticker": TICKER, "close": float(last_row['Close']), "date": str(last_row.name)})
except Exception as e:
    print("Not found or error", e) 