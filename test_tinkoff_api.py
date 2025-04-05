import os
from dotenv import load_dotenv
from tinkoff.invest import Client
import pandas as pd
from datetime import datetime, timedelta

# Загрузка переменных окружения из файла .env
load_dotenv()

# Получение токена из переменных окружения
TOKEN = os.getenv("TINKOFF_INVEST_TOKEN")

def main():
    # Проверка наличия токена
    if not TOKEN:
        print("Ошибка: Токен Tinkoff API не найден в переменных окружения")
        return
    
    try:
        with Client(TOKEN) as client:
            # Получаем информацию о счетах
            accounts = client.users.get_accounts()
            print("Счета:")
            for account in accounts.accounts:
                print(f"- {account.id}: {account.name} (тип: {account.type.name})")
            
            # Получаем список акций
            instruments = client.instruments.shares().instruments
            
            # Преобразуем информацию об акциях в DataFrame для удобного просмотра
            shares_data = []
            for instrument in instruments[:10]:  # Возьмем только первые 10 для примера
                shares_data.append({
                    'figi': instrument.figi,
                    'ticker': instrument.ticker,
                    'name': instrument.name,
                    'currency': instrument.currency,
                    'sector': instrument.sector
                })
            
            print("\nПервые 10 акций:")
            shares_df = pd.DataFrame(shares_data)
            print(shares_df)
            
            # Получим последние цены для этих акций
            if shares_data:
                figis = [share['figi'] for share in shares_data]
                last_prices = client.market_data.get_last_prices(figi=figis)
                
                print("\nПоследние цены:")
                for price_info in last_prices.last_prices:
                    figi = price_info.figi
                    price = price_info.price.units + price_info.price.nano / 1_000_000_000
                    ticker = next((share['ticker'] for share in shares_data if share['figi'] == figi), 'Unknown')
                    name = next((share['name'] for share in shares_data if share['figi'] == figi), 'Unknown')
                    print(f"{ticker} ({name}): {price} {next((share['currency'] for share in shares_data if share['figi'] == figi), '')}")
    
    except Exception as e:
        print(f"Произошла ошибка при работе с Tinkoff API: {e}")

if __name__ == "__main__":
    main() 