import os
from dotenv import load_dotenv
from tinkoff.invest import Client
import pandas as pd
import time
from datetime import datetime, timedelta

# Загрузка переменных окружения из файла .env
load_dotenv()

# Получение токена из переменных окружения
TOKEN = os.getenv("TINKOFF_INVEST_TOKEN")

def get_russian_stocks():
    """Получение списка российских акций с МосБиржи"""
    
    with Client(TOKEN) as client:
        # Получаем список всех акций
        shares = client.instruments.shares().instruments
        
        # Фильтруем только российские акции (торгуемые в рублях и на MOEX)
        russian_shares = [
            share for share in shares 
            if share.currency == "rub" and "MOEX" in share.exchange
        ]
        
        # Создаем DataFrame с данными акций
        data = []
        for share in russian_shares:
            data.append({
                'figi': share.figi,
                'ticker': share.ticker,
                'name': share.name,
                'sector': share.sector,
                'lot': share.lot,
                'min_price_increment': float(share.min_price_increment.units) + float(share.min_price_increment.nano) / 1_000_000_000 if share.min_price_increment else None,
                'trading_status': share.trading_status.name,
                'api_trade_available': share.api_trade_available_flag
            })
        
        return pd.DataFrame(data)

def get_stock_prices(figis):
    """Получение текущих цен для списка акций"""
    
    with Client(TOKEN) as client:
        # Получаем последние цены
        last_prices = client.market_data.get_last_prices(figi=figis)
        
        prices_data = []
        for price_info in last_prices.last_prices:
            # Объединяем units и nano в одну цену
            price = float(price_info.price.units) + float(price_info.price.nano) / 1_000_000_000
            
            prices_data.append({
                'figi': price_info.figi,
                'price': price,
                'time': price_info.time.replace(tzinfo=None)  # Удаляем информацию о часовом поясе
            })
        
        return pd.DataFrame(prices_data)

def main():
    try:
        # Получаем список российских акций
        print("Получение списка российских акций...")
        russian_stocks = get_russian_stocks()
        print(f"Найдено {len(russian_stocks)} российских акций")
        
        # Выводим первые 10 акций
        print("\nПервые 10 российских акций:")
        print(russian_stocks.head(10))
        
        # Получаем текущие цены для первых 20 акций
        if not russian_stocks.empty:
            sample_figis = russian_stocks['figi'].head(20).tolist()
            
            print("\nПолучение текущих цен для 20 российских акций...")
            prices = get_stock_prices(sample_figis)
            
            # Объединяем данные акций с ценами
            stocks_with_prices = pd.merge(
                russian_stocks.head(20), 
                prices, 
                on='figi', 
                how='left'
            )
            
            # Выводим результат
            print("\nРоссийские акции с текущими ценами:")
            print(stocks_with_prices[['ticker', 'name', 'price', 'sector', 'time']])
            
            # Сохраняем результаты в CSV
            stocks_with_prices.to_csv('russian_stocks_prices.csv', index=False, encoding='utf-8')
            print("\nДанные сохранены в файл russian_stocks_prices.csv")
            
    except Exception as e:
        print(f"Произошла ошибка: {e}")

if __name__ == "__main__":
    main() 