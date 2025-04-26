import requests
import json
import pandas as pd
import os
from datetime import datetime, timedelta
from dotenv import load_dotenv
import yfinance as yf

# Загрузка переменных окружения
load_dotenv()

# Константы
TICKER = "OZON"
OUTPUT_FILE = f"{TICKER}_moex_data.json"

def get_moex_security_info():
    """Получение основной информации о ценной бумаге с Московской биржи"""
    print("\n=== Получение данных о ценной бумаге с MOEX ===")
    url = f"https://iss.moex.com/iss/securities/{TICKER}.json"
    
    try:
        response = requests.get(url)
        if response.status_code == 200:
            data = response.json()
            
            # Преобразование данных из ответа в удобный формат
            securities = pd.DataFrame(data['securities']['data'], 
                                     columns=data['securities']['columns'])
            
            # Конвертация DataFrame в список словарей
            securities_list = securities.to_dict('records')
            
            print(f"Получена информация о ценной бумаге {TICKER} с MOEX")
            return securities_list
        else:
            print(f"Ошибка при получении данных: {response.status_code}")
            return None
    except Exception as e:
        print(f"Ошибка при получении информации о ценной бумаге: {e}")
        return None

def get_moex_market_data():
    """Получение рыночных данных о ценной бумаге с Московской биржи"""
    print("\n=== Получение рыночных данных с MOEX ===")
    url = f"https://iss.moex.com/iss/engines/stock/markets/shares/securities/{TICKER}.json"
    
    try:
        response = requests.get(url)
        if response.status_code == 200:
            data = response.json()
            
            # Преобразование данных из ответа в удобный формат
            securities = pd.DataFrame(data['securities']['data'], 
                                     columns=data['securities']['columns'])
            marketdata = pd.DataFrame(data['marketdata']['data'], 
                                     columns=data['marketdata']['columns'])
            
            # Конвертация DataFrame в список словарей
            securities_list = securities.to_dict('records')
            marketdata_list = marketdata.to_dict('records')
            
            print(f"Получены рыночные данные по {TICKER} с MOEX")
            return {
                'securities': securities_list,
                'marketdata': marketdata_list
            }
        else:
            print(f"Ошибка при получении данных: {response.status_code}")
            return None
    except Exception as e:
        print(f"Ошибка при получении рыночных данных: {e}")
        return None

def get_moex_orderbook():
    """Получение стакана заявок с Московской биржи"""
    print("\n=== Получение стакана заявок с MOEX ===")
    url = f"https://iss.moex.com/iss/engines/stock/markets/shares/securities/{TICKER}/orderbook.json?depth=20"
    
    try:
        response = requests.get(url)
        if response.status_code == 200:
            data = response.json()
            
            # Преобразование данных из ответа в удобный формат
            orderbook = pd.DataFrame(data['orderbook']['data'], 
                                    columns=data['orderbook']['columns'])
            
            # Конвертация DataFrame в список словарей
            orderbook_list = orderbook.to_dict('records')
            
            print(f"Получен стакан заявок по {TICKER} с MOEX")
            return orderbook_list
        else:
            print(f"Ошибка при получении данных: {response.status_code}")
            return None
    except Exception as e:
        print(f"Ошибка при получении стакана заявок: {e}")
        return None

def get_moex_historical_data(from_date=None):
    """Получение исторических данных с Московской биржи"""
    print("\n=== Получение исторических данных с MOEX ===")
    
    if from_date is None:
        # По умолчанию берем данные за последние 30 дней
        from_date = (datetime.now() - timedelta(days=30)).strftime('%Y-%m-%d')
    
    url = f"https://iss.moex.com/iss/history/engines/stock/markets/shares/securities/{TICKER}/candles.json"
    params = {
        'from': from_date,
        'interval': 24  # дневные свечи
    }
    
    try:
        response = requests.get(url, params=params)
        if response.status_code == 200:
            data = response.json()
            
            # Преобразование данных из ответа в удобный формат
            candles = pd.DataFrame(data['candles']['data'], 
                                  columns=data['candles']['columns'])
            
            # Конвертация DataFrame в список словарей
            candles_list = candles.to_dict('records')
            
            print(f"Получены исторические данные по {TICKER} с MOEX")
            return candles_list
        else:
            print(f"Ошибка при получении данных: {response.status_code}")
            return None
    except Exception as e:
        print(f"Ошибка при получении исторических данных: {e}")
        return None

def get_yahoo_finance_data():
    """Получение данных о компании из Yahoo Finance"""
    print("\n=== Получение данных из Yahoo Finance ===")
    
    try:
        # OZON торгуется на NASDAQ под тикером OZON
        ticker = yf.Ticker("OZON")
        
        # Основная информация
        info = ticker.info
        
        # Получаем исторические данные
        hist = ticker.history(period="1mo")
        hist_dict = hist.reset_index().to_dict('records')
        
        # Получаем рекомендации аналитиков
        recommendations = ticker.recommendations
        
        # Получаем основных держателей акций
        major_holders = ticker.major_holders
        institutional_holders = ticker.institutional_holders
        
        # Получаем финансовые показатели
        financials = ticker.financials
        balance_sheet = ticker.balance_sheet
        cash_flow = ticker.cashflow
        
        # Собираем все данные в один словарь
        yahoo_data = {
            'info': info,
            'history': hist_dict,
            'recommendations': recommendations.to_dict('records') if recommendations is not None else None,
            'major_holders': major_holders.to_dict('records') if major_holders is not None else None,
            'institutional_holders': institutional_holders.to_dict('records') if institutional_holders is not None else None,
            'financials': financials.to_dict() if financials is not None else None,
            'balance_sheet': balance_sheet.to_dict() if balance_sheet is not None else None,
            'cash_flow': cash_flow.to_dict() if cash_flow is not None else None
        }
        
        print(f"Получены данные о компании {TICKER} из Yahoo Finance")
        return yahoo_data
    except Exception as e:
        print(f"Ошибка при получении данных из Yahoo Finance: {e}")
        return None

def get_investing_com_data():
    """
    Получение данных с Investing.com 
    (Примечание: scraping может не работать, т.к. Investing.com часто меняет структуру и блокирует скрейперы)
    """
    print("\n=== Попытка получения данных с Investing.com ===")
    
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
    }
    
    # Ищем страницу компании
    search_url = f"https://www.investing.com/search/?q={TICKER}"
    
    try:
        response = requests.get(search_url, headers=headers)
        if response.status_code == 200:
            # Для scraping обычно используется библиотека BeautifulSoup, 
            # но в данном случае, я просто отметаю, что это запрос выполнен и 
            # можно было бы извлечь нужные данные
            print(f"Данные с Investing.com доступны (требуется парсинг HTML)")
            return {"status": "Требуется парсинг HTML для извлечения данных"}
        else:
            print(f"Ошибка при получении данных: {response.status_code}")
            return None
    except Exception as e:
        print(f"Ошибка при получении данных с Investing.com: {e}")
        return None

def save_to_json(data):
    """Сохранение данных в JSON файл"""
    with open(OUTPUT_FILE, 'w', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False, indent=2, default=str)
    print(f"Данные сохранены в файл {OUTPUT_FILE}")

def main():
    """Основная функция для сбора всех данных"""
    print(f"Начинаем сбор данных о компании {TICKER}")
    
    # Сбор всех данных
    all_data = {
        'timestamp': datetime.now().isoformat(),
        'ticker': TICKER
    }
    
    # Получение данных с Московской биржи
    security_info = get_moex_security_info()
    if security_info:
        all_data['moex_security_info'] = security_info
    
    market_data = get_moex_market_data()
    if market_data:
        all_data['moex_market_data'] = market_data
    
    orderbook = get_moex_orderbook()
    if orderbook:
        all_data['moex_orderbook'] = orderbook
    
    historical_data = get_moex_historical_data()
    if historical_data:
        all_data['moex_historical_data'] = historical_data
    
    # Получение данных из Yahoo Finance
    yahoo_data = get_yahoo_finance_data()
    if yahoo_data:
        all_data['yahoo_finance'] = yahoo_data
    
    # Получение данных с Investing.com (опционально)
    investing_data = get_investing_com_data()
    if investing_data:
        all_data['investing_com'] = investing_data
    
    # Сохранение всех собранных данных
    save_to_json(all_data)
    
    print(f"Сбор данных о компании {TICKER} завершен")
    
    # Распечатка короткой сводки
    print("\n=== Сводка собранных данных ===")
    sections = [section for section in all_data.keys() if section not in ['timestamp', 'ticker']]
    for section in sections:
        print(f"- {section}: данные получены")

if __name__ == "__main__":
    main() 