import os
import json
import requests
import pandas as pd
from datetime import datetime, timedelta
from dotenv import load_dotenv
import yfinance as yf
from tinkoff.invest import Client, CandleInterval

# Загрузка переменных окружения
load_dotenv()

# Получение токена из переменных окружения
TOKEN = os.getenv("TINKOFF_INVEST_TOKEN")
TICKER = "OZON"

def safe_json_response(response):
    """Безопасное получение JSON из ответа API"""
    try:
        if response.status_code == 200 and response.content:
            return response.json()
        else:
            print(f"Ошибка в ответе API: статус {response.status_code}")
            return None
    except Exception as e:
        print(f"Ошибка при разборе JSON ответа: {e}")
        return None

def save_to_json(filename, data):
    """Сохранение данных в JSON файл"""
    with open(filename, 'w', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False, indent=2, default=str)
    print(f"Данные сохранены в файл {filename}")

def format_money(money_value):
    """Форматирование денежных значений из API Tinkoff"""
    if not money_value:
        return None
    return float(money_value.units) + float(money_value.nano) / 1_000_000_000

def get_moex_data():
    """Получение данных о компании OZON с Московской биржи"""
    print("\n=== Получение данных с Московской биржи ===")
    
    # Базовая информация о инструменте
    url_securities = f"https://iss.moex.com/iss/engines/stock/markets/shares/securities/{TICKER}.json"
    resp_securities = requests.get(url_securities)
    
    # Данные о стакане заявок (лучшая цена покупки и продажи)
    url_orderbook = f"https://iss.moex.com/iss/engines/stock/markets/shares/securities/{TICKER}/orderbook.json?depth=20"
    resp_orderbook = requests.get(url_orderbook)
    
    # Исторические данные
    url_history = f"https://iss.moex.com/iss/engines/stock/markets/shares/securities/{TICKER}/candles.json?interval=24&from={datetime.now().date() - timedelta(days=30)}&till={datetime.now().date()}"
    resp_history = requests.get(url_history)
    
    # Агрегированные финансовые показатели
    url_aggr = f"https://iss.moex.com/iss/statistics/engines/stock/markets/shares/securities/{TICKER}/aggregates.json"
    resp_aggr = requests.get(url_aggr)
    
    moex_data = {
        'timestamp': datetime.now().isoformat(),
        'ticker': TICKER
    }
    
    # Обработка ответа по базовой информации
    data = safe_json_response(resp_securities)
    if data:
        # Преобразуем данные в DataFrame
        if 'securities' in data and 'data' in data['securities'] and 'columns' in data['securities']:
            securities = pd.DataFrame(data['securities']['data'], columns=data['securities']['columns'])
            moex_data['securities'] = securities.to_dict('records')
            print(f"Получены базовые данные: {len(securities)} записей")
            
        # Преобразуем данные торгов
        if 'marketdata' in data and 'data' in data['marketdata'] and 'columns' in data['marketdata']:
            marketdata = pd.DataFrame(data['marketdata']['data'], columns=data['marketdata']['columns'])
            moex_data['marketdata'] = marketdata.to_dict('records')
            print(f"Получены данные торгов: {len(marketdata)} записей")
    else:
        print(f"Ошибка при получении данных о ценной бумаге.")
    
    # Обработка ответа по стакану заявок
    data = safe_json_response(resp_orderbook)
    if data:
        if 'orderbook' in data and 'data' in data['orderbook'] and 'columns' in data['orderbook']:
            orderbook = pd.DataFrame(data['orderbook']['data'], columns=data['orderbook']['columns'])
            moex_data['orderbook'] = orderbook.to_dict('records')
            print(f"Получены данные стакана заявок: {len(orderbook)} записей")
    else:
        print(f"Ошибка при получении данных стакана заявок.")
    
    # Обработка ответа по историческим данным
    data = safe_json_response(resp_history)
    if data:
        if 'candles' in data and 'data' in data['candles'] and 'columns' in data['candles']:
            candles = pd.DataFrame(data['candles']['data'], columns=data['candles']['columns'])
            moex_data['candles'] = candles.to_dict('records')
            print(f"Получены исторические данные: {len(candles)} записей")
    else:
        print(f"Ошибка при получении исторических данных.")
    
    # Обработка ответа по агрегированным показателям
    data = safe_json_response(resp_aggr)
    if data:
        if 'aggregates' in data and 'data' in data['aggregates'] and 'columns' in data['aggregates']:
            aggregates = pd.DataFrame(data['aggregates']['data'], columns=data['aggregates']['columns'])
            moex_data['aggregates'] = aggregates.to_dict('records')
            print(f"Получены агрегированные показатели: {len(aggregates)} записей")
    else:
        print(f"Ошибка при получении агрегированных показателей.")
    
    return moex_data

def get_yahoo_finance_data():
    """Получение данных о компании OZON из Yahoo Finance"""
    print("\n=== Получение данных из Yahoo Finance ===")
    
    try:
        # Получаем данные по OZON. Тикер OZON торгуется на NASDAQ
        ticker = yf.Ticker("OZON")
        
        # Базовая информация о компании
        info = ticker.info
        
        # Исторические данные за последний месяц
        history = ticker.history(period="1mo")
        
        # Основные финансовые показатели
        financials = {
            "income_statement": ticker.income_stmt.to_dict() if hasattr(ticker, 'income_stmt') and ticker.income_stmt is not None else None,
            "balance_sheet": ticker.balance_sheet.to_dict() if hasattr(ticker, 'balance_sheet') and ticker.balance_sheet is not None else None,
            "cash_flow": ticker.cashflow.to_dict() if hasattr(ticker, 'cashflow') and ticker.cashflow is not None else None
        }
        
        # Рекомендации аналитиков
        recommendations = ticker.recommendations.to_dict() if hasattr(ticker, 'recommendations') and ticker.recommendations is not None else None
        
        # Крупные держатели акций
        major_holders = ticker.major_holders.to_dict() if hasattr(ticker, 'major_holders') and ticker.major_holders is not None else None
        institutional_holders = ticker.institutional_holders.to_dict() if hasattr(ticker, 'institutional_holders') and ticker.institutional_holders is not None else None
        
        # Опционы
        options = ticker.options
        option_chain = {}
        for option_date in options[:3]:  # Берем только первые 3 даты опционов
            option_chain[option_date] = ticker.option_chain(option_date).to_dict()
        
        yahoo_data = {
            'timestamp': datetime.now().isoformat(),
            'ticker': TICKER,
            'info': info,
            'history': history.to_dict(),
            'financials': financials,
            'recommendations': recommendations,
            'major_holders': major_holders,
            'institutional_holders': institutional_holders,
            'options': option_chain
        }
        
        print(f"Данные из Yahoo Finance успешно получены")
        return yahoo_data
    
    except Exception as e:
        print(f"Ошибка при получении данных из Yahoo Finance: {e}")
        return None

def get_tinkoff_orderbook():
    """Получение стакана заявок по OZON из Tinkoff Invest API"""
    print("\n=== Получение стакана заявок из Tinkoff API ===")
    
    with Client(TOKEN) as client:
        try:
            # Сначала найдем инструмент
            instruments = client.instruments.find_instrument(query=TICKER)
            
            # Ищем точное совпадение по тикеру
            figi = None
            for instrument in instruments.instruments:
                if instrument.ticker.upper() == TICKER.upper():
                    figi = instrument.figi
                    break
            
            if not figi:
                print(f"Инструмент {TICKER} не найден")
                return None
            
            # Получаем стакан заявок
            orderbook = client.market_data.get_order_book(figi=figi, depth=50)
            
            # Форматируем ответ
            bids = []
            for bid in orderbook.bids:
                bids.append({
                    'price': format_money(bid.price),
                    'quantity': bid.quantity
                })
            
            asks = []
            for ask in orderbook.asks:
                asks.append({
                    'price': format_money(ask.price),
                    'quantity': ask.quantity
                })
            
            data = {
                'figi': orderbook.figi,
                'depth': orderbook.depth,
                'bids': bids,
                'asks': asks,
                'last_price': format_money(orderbook.last_price),
                'close_price': format_money(orderbook.close_price),
                'limit_up': format_money(orderbook.limit_up),
                'limit_down': format_money(orderbook.limit_down)
            }
            
            print(f"Стакан получен. Бидов: {len(bids)}, Асков: {len(asks)}")
            return data
        
        except Exception as e:
            print(f"Ошибка при получении стакана заявок: {e}")
            return None

def calculate_beta(ozon_prices, moex_prices):
    """Расчет бета-коэффициента OZON относительно индекса MOEX"""
    print("\n=== Расчет бета-коэффициента ===")
    
    try:
        # Если у нас есть исторические данные и из Yahoo Finance и из MOEX
        if ozon_prices is not None and moex_prices is not None:
            # Конвертируем в pandas DataFrame для удобства
            ozon_df = pd.DataFrame(ozon_prices)
            moex_df = pd.DataFrame(moex_prices)
            
            # Вычисляем дневные доходности
            if 'Close' in ozon_df.columns:
                ozon_returns = ozon_df['Close'].pct_change().dropna()
            elif 'close' in ozon_df.columns:
                ozon_returns = ozon_df['close'].pct_change().dropna()
            else:
                print("Не найдены цены закрытия для OZON")
                return None
            
            if 'Close' in moex_df.columns:
                moex_returns = moex_df['Close'].pct_change().dropna()
            elif 'close' in moex_df.columns:
                moex_returns = moex_df['close'].pct_change().dropna()
            else:
                print("Не найдены цены закрытия для индекса MOEX")
                return None
            
            # Выравниваем периоды
            common_index = ozon_returns.index.intersection(moex_returns.index)
            if len(common_index) < 10:  # Нужно хотя бы 10 точек для надежной оценки
                print("Недостаточно данных для расчета бета-коэффициента")
                return None
            
            ozon_returns = ozon_returns.loc[common_index]
            moex_returns = moex_returns.loc[common_index]
            
            # Вычисляем бета по формуле: cov(r_i, r_m) / var(r_m)
            covariance = ozon_returns.cov(moex_returns)
            variance = moex_returns.var()
            
            beta = covariance / variance
            
            print(f"Рассчитанный бета-коэффициент: {beta:.2f}")
            return {
                "beta": beta,
                "periods": len(common_index),
                "covariance": covariance,
                "market_variance": variance
            }
        else:
            print("Нет данных для расчета бета-коэффициента")
            return None
    except Exception as e:
        print(f"Ошибка при расчете бета-коэффициента: {e}")
        return None

def get_imoex_data():
    """Получение данных по индексу IMOEX (Индекс МосБиржи)"""
    print("\n=== Получение данных по индексу МосБиржи ===")
    
    url = "https://iss.moex.com/iss/engines/stock/markets/index/securities/IMOEX/candles.json"
    params = {
        'from': (datetime.now().date() - timedelta(days=30)).isoformat(),
        'till': datetime.now().date().isoformat(),
        'interval': 24  # Дневной интервал
    }
    
    try:
        response = requests.get(url, params=params)
        data = safe_json_response(response)
        
        if data and 'candles' in data and 'data' in data['candles'] and 'columns' in data['candles']:
            candles = pd.DataFrame(data['candles']['data'], columns=data['candles']['columns'])
            print(f"Получены данные по индексу IMOEX: {len(candles)} записей")
            return candles.to_dict('records')
        else:
            print("Ошибка в структуре ответа при получении данных по индексу IMOEX")
            return None
    except Exception as e:
        print(f"Ошибка при получении данных по индексу IMOEX: {e}")
        return None

def main():
    """Основная функция для получения данных о компании OZON из разных источников"""
    result = {
        'timestamp': datetime.now().isoformat(),
        'ticker': TICKER
    }
    
    # Получение данных с Московской биржи
    moex_data = get_moex_data()
    if moex_data:
        result['moex'] = moex_data
    
    # Получение данных из Yahoo Finance
    try:
        yahoo_data = get_yahoo_finance_data()
        if yahoo_data:
            result['yahoo'] = yahoo_data
    except Exception as e:
        print(f"Ошибка при получении данных из Yahoo Finance: {e}")
    
    # Получение стакана заявок из Tinkoff API
    try:
        tinkoff_orderbook = get_tinkoff_orderbook()
        if tinkoff_orderbook:
            result['tinkoff_orderbook'] = tinkoff_orderbook
    except Exception as e:
        print(f"Ошибка при получении стакана заявок из Tinkoff API: {e}")
    
    # Получение данных по индексу IMOEX для расчета бета
    try:
        imoex_data = get_imoex_data()
        if imoex_data:
            result['imoex'] = imoex_data
    except Exception as e:
        print(f"Ошибка при получении данных по индексу IMOEX: {e}")
    
    # Расчет бета-коэффициента
    ozon_prices = None
    if 'yahoo' in result and 'history' in result['yahoo']:
        ozon_prices = result['yahoo']['history']
    elif 'moex' in result and 'candles' in result['moex']:
        ozon_prices = result['moex']['candles']
    
    try:
        beta_info = calculate_beta(ozon_prices, imoex_data)
        if beta_info:
            result['beta'] = beta_info
    except Exception as e:
        print(f"Ошибка при расчете бета-коэффициента: {e}")
    
    # Сохраняем все данные в один JSON файл
    output_file = f"{TICKER}_market_data.json"
    save_to_json(output_file, result)
    
    # Вывести краткую сводку
    print("\n=== Краткая сводка ===")
    if 'moex' in result and 'marketdata' in result['moex'] and len(result['moex']['marketdata']) > 0:
        market_data = result['moex']['marketdata'][0]
        print(f"Последняя цена на MOEX: {market_data.get('LAST', 'Н/Д')}")
        print(f"Изменение цены: {market_data.get('CHANGE', 'Н/Д')} ({market_data.get('PRICEMINUSPREVWAPRICE', 'Н/Д')}%)")
    
    if 'yahoo' in result and 'info' in result['yahoo']:
        info = result['yahoo']['info']
        print(f"Рыночная капитализация: {info.get('marketCap', 'Н/Д')}")
        print(f"P/E: {info.get('trailingPE', 'Н/Д')}")
        print(f"Целевая цена: {info.get('targetMeanPrice', 'Н/Д')}")
    
    if 'beta' in result:
        print(f"Бета относительно IMOEX: {result['beta'].get('beta', 'Н/Д')}")
    
    if 'tinkoff_orderbook' in result:
        ob = result['tinkoff_orderbook']
        top_bid = ob['bids'][0]['price'] if ob['bids'] else 'Н/Д'
        top_ask = ob['asks'][0]['price'] if ob['asks'] else 'Н/Д'
        print(f"Лучшая цена покупки: {top_bid}")
        print(f"Лучшая цена продажи: {top_ask}")
        print(f"Спред: {float(top_ask) - float(top_bid) if top_bid != 'Н/Д' and top_ask != 'Н/Д' else 'Н/Д'}")

if __name__ == "__main__":
    print(f"Начинаем сбор рыночных данных о компании {TICKER}")
    main()
    print("Работа скрипта завершена.") 