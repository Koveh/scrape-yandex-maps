import os
from dotenv import load_dotenv
from tinkoff.invest import Client, InstrumentIdType, CandleInterval
import pandas as pd
from datetime import datetime, timedelta
import json

# Загрузка переменных окружения из файла .env
load_dotenv()

# Получение токена из переменных окружения
TOKEN = os.getenv("TINKOFF_INVEST_TOKEN")

def search_instrument_by_ticker(ticker):
    """Поиск инструмента по тикеру"""
    with Client(TOKEN) as client:
        try:
            # Поиск по тикеру среди всех инструментов
            instruments = client.instruments.find_instrument(query=ticker)
            
            # Ищем точное совпадение по тикеру
            for instrument in instruments.instruments:
                if instrument.ticker.upper() == ticker.upper():
                    return instrument
            
            return None
        except Exception as e:
            print(f"Ошибка при поиске инструмента {ticker}: {e}")
            return None

def get_company_by_figi(figi):
    """Получение информации о компании по FIGI"""
    with Client(TOKEN) as client:
        try:
            # Получаем информацию о компании по FIGI
            instrument = client.instruments.get_instrument_by(
                id_type=InstrumentIdType.INSTRUMENT_ID_TYPE_FIGI,
                id=figi
            )
            return instrument.instrument
        except Exception as e:
            print(f"Ошибка при получении информации о компании по FIGI {figi}: {e}")
            return None

def get_company_prices(figi, days=30, interval=CandleInterval.CANDLE_INTERVAL_DAY):
    """Получение исторических цен для акции"""
    with Client(TOKEN) as client:
        try:
            # Определяем временной интервал
            now = datetime.utcnow()
            from_date = now - timedelta(days=days)
            
            # Получаем исторические данные
            candles = client.market_data.get_candles(
                figi=figi,
                from_=from_date,
                to=now,
                interval=interval
            )
            
            # Преобразуем данные в DataFrame
            candles_data = []
            for candle in candles.candles:
                candles_data.append({
                    'time': candle.time.replace(tzinfo=None),
                    'open': candle.open.units + candle.open.nano / 1_000_000_000,
                    'high': candle.high.units + candle.high.nano / 1_000_000_000,
                    'low': candle.low.units + candle.low.nano / 1_000_000_000,
                    'close': candle.close.units + candle.close.nano / 1_000_000_000,
                    'volume': candle.volume,
                    'is_complete': candle.is_complete
                })
            
            return pd.DataFrame(candles_data)
        except Exception as e:
            print(f"Ошибка при получении исторических цен для {figi}: {e}")
            return pd.DataFrame()

def get_last_price(figi):
    """Получение текущей цены акции"""
    with Client(TOKEN) as client:
        try:
            # Получаем последнюю цену
            response = client.market_data.get_last_prices(figi=[figi])
            if response.last_prices:
                price_info = response.last_prices[0]
                price = price_info.price.units + price_info.price.nano / 1_000_000_000
                return {
                    'price': price,
                    'time': price_info.time.replace(tzinfo=None)
                }
            else:
                return None
        except Exception as e:
            print(f"Ошибка при получении текущей цены для {figi}: {e}")
            return None

def get_orderbook(figi, depth=20):
    """Получение стакана заявок"""
    with Client(TOKEN) as client:
        try:
            # Получаем стакан заявок
            orderbook = client.market_data.get_order_book(figi=figi, depth=depth)
            
            # Преобразуем данные в словарь
            orderbook_data = {
                'figi': orderbook.figi,
                'depth': orderbook.depth,
                'bids': [{'price': bid.price.units + bid.price.nano / 1_000_000_000, 
                          'quantity': bid.quantity} 
                         for bid in orderbook.bids],
                'asks': [{'price': ask.price.units + ask.price.nano / 1_000_000_000, 
                          'quantity': ask.quantity} 
                         for ask in orderbook.asks],
                'last_price': orderbook.last_price.units + orderbook.last_price.nano / 1_000_000_000 if orderbook.last_price else None,
                'close_price': orderbook.close_price.units + orderbook.close_price.nano / 1_000_000_000 if orderbook.close_price else None,
                'limit_up': orderbook.limit_up.units + orderbook.limit_up.nano / 1_000_000_000 if orderbook.limit_up else None,
                'limit_down': orderbook.limit_down.units + orderbook.limit_down.nano / 1_000_000_000 if orderbook.limit_down else None
            }
            
            return orderbook_data
        except Exception as e:
            print(f"Ошибка при получении стакана заявок для {figi}: {e}")
            return None

def safe_get_attr(obj, attr_name, default=None):
    """Безопасное получение атрибута объекта"""
    try:
        return getattr(obj, attr_name)
    except (AttributeError, TypeError):
        return default

def get_all_company_info(ticker):
    """Получение всей доступной информации о компании"""
    
    # Поиск инструмента по тикеру
    instrument = search_instrument_by_ticker(ticker)
    if not instrument:
        print(f"Компания с тикером {ticker} не найдена")
        return
    
    # Получаем полную информацию о компании по FIGI
    company = get_company_by_figi(instrument.figi)
    if not company:
        print(f"Не удалось получить полную информацию о компании {ticker}")
        return
    
    # Создаем словарь для хранения всей информации
    company_info = {
        'basic_info': {
            'figi': company.figi,
            'ticker': company.ticker,
            'name': company.name,
            'class_code': company.class_code,
            'isin': safe_get_attr(company, 'isin'),
            'lot': company.lot,
            'currency': company.currency,
            'exchange': company.exchange,
            'country_of_risk': safe_get_attr(company, 'country_of_risk'),
            'country_of_risk_name': safe_get_attr(company, 'country_of_risk_name'),
            'sector': safe_get_attr(company, 'sector'),
            'issue_size': safe_get_attr(company, 'issue_size'),
            'issue_size_plan': safe_get_attr(company, 'issue_size_plan'),
            'trading_status': company.trading_status.name,
            'otc_flag': safe_get_attr(company, 'otc_flag'),
            'buy_available_flag': safe_get_attr(company, 'buy_available_flag'),
            'sell_available_flag': safe_get_attr(company, 'sell_available_flag'),
            'div_yield_flag': safe_get_attr(company, 'div_yield_flag'),
            'api_trade_available_flag': safe_get_attr(company, 'api_trade_available_flag'),
        }
    }
    
    # Получаем текущую цену
    last_price = get_last_price(company.figi)
    if last_price:
        company_info['current_price'] = last_price
    
    # Получаем исторические цены за разные периоды
    # Дневные свечи за последний месяц
    daily_prices = get_company_prices(company.figi, days=30, interval=CandleInterval.CANDLE_INTERVAL_DAY)
    if not daily_prices.empty:
        company_info['daily_prices_30d'] = daily_prices.to_dict('records')
    
    # Часовые свечи за последние 7 дней
    hourly_prices = get_company_prices(company.figi, days=7, interval=CandleInterval.CANDLE_INTERVAL_HOUR)
    if not hourly_prices.empty:
        company_info['hourly_prices_7d'] = hourly_prices.to_dict('records')
    
    # 15-минутные свечи за последние 2 дня
    min15_prices = get_company_prices(company.figi, days=2, interval=CandleInterval.CANDLE_INTERVAL_15_MIN)
    if not min15_prices.empty:
        company_info['min15_prices_2d'] = min15_prices.to_dict('records')
    
    # Стакан заявок
    orderbook = get_orderbook(company.figi)
    if orderbook:
        company_info['orderbook'] = orderbook
    
    return company_info

def main():
    # Проверка наличия токена
    if not TOKEN:
        print("Ошибка: Токен Tinkoff API не найден в переменных окружения")
        return
    
    try:
        # Запрашиваем тикер у пользователя
        ticker = input("Введите тикер компании (например, SBER, GAZP, OZON): ").upper()
        
        print(f"Получение информации о компании {ticker}...")
        company_info = get_all_company_info(ticker)
        
        if company_info:
            # Выводим полные данные в JSON формате
            print("\nПолная информация о компании в формате JSON:")
            print(json.dumps(company_info, ensure_ascii=False, indent=2, default=str))
            
            # Сохраняем всю информацию в JSON-файл
            output_file = f"{ticker}_info.json"
            with open(output_file, 'w', encoding='utf-8') as f:
                json.dump(company_info, f, ensure_ascii=False, indent=2, default=str)
            print(f"\nВся информация сохранена в файл {output_file}")
            
    except Exception as e:
        print(f"Произошла ошибка: {e}")

if __name__ == "__main__":
    main() 