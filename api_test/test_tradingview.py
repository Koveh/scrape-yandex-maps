import requests
import time
import json

TICKER = "OZON"

def get_tradingview_data():
    """Получение данных о цене акции через TradingView API"""
    try:
        # Базовый URL для запросов
        url = "https://scanner.tradingview.com/russia/scan"
        
        # Формируем запрос для конкретного тикера
        payload = {
            "symbols": {
                "tickers": [f"MOEX:{TICKER}"],
                "query": {
                    "types": []
                }
            },
            "columns": [
                "close",
                "change",
                "change_abs",
                "high",
                "low",
                "volume",
                "Recommend.All",
                "description"
            ]
        }
        
        headers = {
            "User-Agent": "Mozilla/5.0",
            "Content-Type": "application/json"
        }
        
        response = requests.post(url, headers=headers, data=json.dumps(payload))
        
        if response.status_code != 200:
            return {"error": f"Request failed with status code {response.status_code}"}
        
        data = response.json()
        
        if "data" not in data or not data["data"]:
            # Если MOEX не сработал, попробуем NASDAQ
            url = "https://scanner.tradingview.com/america/scan"
            payload["symbols"]["tickers"] = [f"NASDAQ:{TICKER}"]
            
            response = requests.post(url, headers=headers, data=json.dumps(payload))
            
            if response.status_code != 200:
                return {"error": f"Second request failed with status code {response.status_code}"}
            
            data = response.json()
            
            if "data" not in data or not data["data"]:
                return {"error": "Stock not found on TradingView"}
        
        # Извлекаем данные
        result = {
            "ticker": TICKER,
            "exchange": data["data"][0]["s"].split(":")[0],
            "close": data["data"][0]["d"][0],
            "change_percent": data["data"][0]["d"][1],
            "change_abs": data["data"][0]["d"][2],
            "high": data["data"][0]["d"][3],
            "low": data["data"][0]["d"][4],
            "volume": data["data"][0]["d"][5],
            "recommendation": data["data"][0]["d"][6] if len(data["data"][0]["d"]) > 6 else None,
            "description": data["data"][0]["d"][7] if len(data["data"][0]["d"]) > 7 else None,
            "timestamp": int(time.time())
        }
        
        return result
        
    except Exception as e:
        return {"error": str(e)}

if __name__ == "__main__":
    result = get_tradingview_data()
    print(json.dumps(result)) 