import requests
import json
from datetime import datetime

TICKER = "SBER"  # Используем SBER как один из самых ликвидных инструментов

def get_basic_info():
    """Получение основной информации об инструменте"""
    url = f"https://iss.moex.com/iss/securities/{TICKER}.json"
    resp = requests.get(url)
    if resp.status_code != 200:
        print(f"Error fetching basic info: {resp.status_code}")
        return {"error": "Request error"}
    
    data = resp.json()
    print(f"Basic info data keys: {data.keys()}")
    
    try:
        if 'description' not in data or 'securities' not in data:
            print("Missing expected data sections")
            return {"error": "Missing data sections"}
            
        description = data['description']['data']
        securities = data['securities']['data']
        
        print(f"Description items: {len(description)}")
        
        # Найдем нужный инструмент (с типом акция)
        result = {}
        for item in description:
            if item[0] == "SECID":
                result["secid"] = item[2]
            elif item[0] == "NAME":
                result["name"] = item[2]
            elif item[0] == "ISIN":
                result["isin"] = item[2]
        
        print(f"Securities items: {len(securities)}")
        for item in securities:
            if len(item) > 1 and item[1] == "TQBR":  # Основной рынок акций
                result["board"] = item[1]
                if len(item) > 5:
                    result["market"] = item[5]
                if len(item) > 7:
                    result["engine"] = item[7]
                break
        
        print(f"Basic result: {result}")
        return result
    except Exception as e:
        print(f"Error in basic info: {str(e)}")
        return {"error": str(e)}

def get_last_price():
    """Получение последней цены"""
    try:
        info = get_basic_info()
        if "error" in info:
            print("Error from basic info, skipping price")
            return info
        
        board = info.get("board", "TQBR")
        print(f"Using board: {board}")
        
        url = f"https://iss.moex.com/iss/engines/stock/markets/shares/boards/{board}/securities/{TICKER}.json"
        print(f"Price URL: {url}")
        
        resp = requests.get(url)
        if resp.status_code != 200:
            print(f"Error fetching price: {resp.status_code}")
            return {"error": f"Request error for price data: {resp.status_code}"}
        
        data = resp.json()
        print(f"Price data keys: {data.keys()}")
        
        if 'marketdata' not in data:
            print("Missing marketdata section")
            return {"error": "Missing marketdata"}
        
        marketdata = data['marketdata']['data']
        print(f"Marketdata rows: {len(marketdata)}")
        
        # Найдем последнюю цену в данных
        col_idx = {col: idx for idx, col in enumerate(data['marketdata']['columns'])}
        print(f"Column indices: {col_idx}")
        
        price_data = {}
        for row in marketdata:
            if row[0] == TICKER:
                # Получим последнюю цену и другие данные
                price_data["last"] = row[col_idx.get("LAST", -1)] if "LAST" in col_idx else None
                price_data["open"] = row[col_idx.get("OPEN", -1)] if "OPEN" in col_idx else None
                price_data["high"] = row[col_idx.get("HIGH", -1)] if "HIGH" in col_idx else None
                price_data["low"] = row[col_idx.get("LOW", -1)] if "LOW" in col_idx else None
                price_data["volume"] = row[col_idx.get("VOLTODAY", -1)] if "VOLTODAY" in col_idx else None
                price_data["time"] = str(datetime.now())
                break
        
        print(f"Price data: {price_data}")
        return price_data
    except Exception as e:
        print(f"Error in price data: {str(e)}")
        return {"error": str(e)}

def main():
    """Основная функция получения данных"""
    result = {}
    
    # Получаем основную информацию
    basic_info = get_basic_info()
    if "error" not in basic_info:
        result["basic_info"] = basic_info
    
    # Получаем информацию о цене
    price_info = get_last_price()
    if "error" not in price_info:
        result["price_info"] = price_info
    
    print("\nFinal result:")
    print(json.dumps(result))

if __name__ == "__main__":
    main()