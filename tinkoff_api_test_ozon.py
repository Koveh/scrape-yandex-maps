import os
import json
from datetime import datetime, timedelta
from dotenv import load_dotenv
from tinkoff.invest import Client, InstrumentIdType, InstrumentStatus, CandleInterval, HistoricCandle
from tinkoff.invest.utils import now

# Загрузка переменных окружения
load_dotenv()

# Получение токена из переменных окружения
TOKEN = os.getenv("TINKOFF_INVEST_TOKEN")
TICKER = "OZON"

def format_money(money_value):
    """Форматирование денежных значений из API"""
    if not money_value:
        return None
    return float(money_value.units) + float(money_value.nano) / 1_000_000_000

def save_to_json(filename, data):
    """Сохранение данных в JSON файл"""
    with open(filename, 'w', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False, indent=2, default=str)
    print(f"Данные сохранены в файл {filename}")

def get_accounts():
    """Получение информации о счетах пользователя"""
    print("\n=== Получение счетов пользователя ===")
    with Client(TOKEN) as client:
        accounts = client.users.get_accounts()
        accounts_info = []
        
        for account in accounts.accounts:
            account_info = {
                'id': account.id,
                'name': account.name,
                'type': str(account.type),
                'status': str(account.status),
                'opened_date': account.opened_date,
                'closed_date': account.closed_date,
                'access_level': str(account.access_level)
            }
            accounts_info.append(account_info)
            print(f"Счет: {account.name} (ID: {account.id}), тип: {account.type}, статус: {account.status}")
        
        return accounts_info

def search_by_ticker(ticker):
    """Поиск инструмента по тикеру"""
    print(f"\n=== Поиск инструмента по тикеру {ticker} ===")
    with Client(TOKEN) as client:
        instruments = client.instruments.find_instrument(query=ticker)
        
        instrument_data = []
        for instrument in instruments.instruments:
            data = {
                'figi': instrument.figi,
                'ticker': instrument.ticker,
                'class_code': instrument.class_code,
                'isin': getattr(instrument, 'isin', None),
                'name': instrument.name,
                'currency': getattr(instrument, 'currency', None),
                'country_of_risk': getattr(instrument, 'country_of_risk', None),
                'country_of_risk_name': getattr(instrument, 'country_of_risk_name', None),
                'instrument_type': str(getattr(instrument, 'instrument_type', None)),
            }
            
            # Безопасное получение атрибутов, которые могут отсутствовать
            if hasattr(instrument, 'trading_status'):
                data['trading_status'] = str(instrument.trading_status)
            if hasattr(instrument, 'real_exchange'):
                data['real_exchange'] = str(instrument.real_exchange)
            if hasattr(instrument, 'exchange'):
                data['exchange'] = instrument.exchange
            if hasattr(instrument, 'sector'):
                data['sector'] = instrument.sector
            if hasattr(instrument, 'lot'):
                data['lot'] = instrument.lot
            if hasattr(instrument, 'otc_flag'):
                data['otc_flag'] = instrument.otc_flag
            if hasattr(instrument, 'buy_available_flag'):
                data['buy_available_flag'] = instrument.buy_available_flag
            if hasattr(instrument, 'sell_available_flag'):
                data['sell_available_flag'] = instrument.sell_available_flag
            if hasattr(instrument, 'min_price_increment'):
                data['min_price_increment'] = format_money(instrument.min_price_increment)
            if hasattr(instrument, 'api_trade_available_flag'):
                data['api_trade_available_flag'] = instrument.api_trade_available_flag
            if hasattr(instrument, 'uid'):
                data['uid'] = instrument.uid
            
            instrument_data.append(data)
            print(f"Найден инструмент: {instrument.name} ({instrument.ticker}), FIGI: {instrument.figi}")
        
        return instrument_data

def get_instrument_by_ticker(ticker):
    """Получение детальной информации об инструменте по тикеру"""
    instruments = search_by_ticker(ticker)
    if not instruments:
        print(f"Инструмент с тикером {ticker} не найден")
        return None
    
    # Находим точное совпадение по тикеру
    for instrument in instruments:
        if instrument['ticker'].upper() == ticker.upper():
            return instrument
    
    # Если точного совпадения нет, возвращаем первый инструмент из списка
    return instruments[0] if instruments else None

def get_instrument_by_figi(figi):
    """Получение детальной информации об инструменте по FIGI"""
    print(f"\n=== Получение информации об инструменте по FIGI {figi} ===")
    with Client(TOKEN) as client:
        try:
            instrument = client.instruments.get_instrument_by(id_type=InstrumentIdType.INSTRUMENT_ID_TYPE_FIGI, id=figi)
            
            data = {
                'figi': instrument.instrument.figi,
                'ticker': instrument.instrument.ticker,
                'class_code': instrument.instrument.class_code,
                'isin': instrument.instrument.isin,
                'name': instrument.instrument.name,
                'exchange': instrument.instrument.exchange,
                'currency': instrument.instrument.currency,
                'country_of_risk': instrument.instrument.country_of_risk,
                'country_of_risk_name': instrument.instrument.country_of_risk_name,
                'instrument_type': str(instrument.instrument.instrument_type),
                'trading_status': str(instrument.instrument.trading_status),
                'otc_flag': instrument.instrument.otc_flag,
                'buy_available_flag': instrument.instrument.buy_available_flag,
                'sell_available_flag': instrument.instrument.sell_available_flag,
                'min_price_increment': format_money(instrument.instrument.min_price_increment),
                'api_trade_available_flag': instrument.instrument.api_trade_available_flag,
                'lot': instrument.instrument.lot,
                'uid': instrument.instrument.uid
            }
            
            # Безопасное получение атрибутов, которые могут отсутствовать
            if hasattr(instrument.instrument, 'sector'):
                data['sector'] = instrument.instrument.sector
            
            print(f"Информация об инструменте: {instrument.instrument.name} ({instrument.instrument.ticker})")
            return data
        except Exception as e:
            print(f"Ошибка при получении инструмента по FIGI {figi}: {e}")
            return None

def get_last_prices(figi):
    """Получение последней цены по FIGI"""
    print(f"\n=== Получение последней цены для FIGI {figi} ===")
    with Client(TOKEN) as client:
        try:
            response = client.market_data.get_last_prices(figi=[figi])
            
            prices_data = []
            for price_data in response.last_prices:
                data = {
                    'figi': price_data.figi,
                    'price': format_money(price_data.price),
                    'time': price_data.time
                }
                prices_data.append(data)
                print(f"Последняя цена: {data['price']}, время: {data['time']}")
            
            return prices_data[0] if prices_data else None
        except Exception as e:
            print(f"Ошибка при получении последней цены для {figi}: {e}")
            return None

def get_candles(figi, from_date, to_date, interval=CandleInterval.CANDLE_INTERVAL_DAY):
    """Получение свечей по FIGI за период"""
    interval_name = str(interval).split('_')[-1].lower()
    print(f"\n=== Получение {interval_name}-свечей для {figi} с {from_date} по {to_date} ===")
    
    with Client(TOKEN) as client:
        try:
            candles = client.market_data.get_candles(
                figi=figi,
                from_=from_date,
                to=to_date,
                interval=interval
            )
            
            candles_data = []
            for candle in candles.candles:
                data = {
                    'open': format_money(candle.open),
                    'high': format_money(candle.high),
                    'low': format_money(candle.low),
                    'close': format_money(candle.close),
                    'volume': candle.volume,
                    'time': candle.time
                }
                candles_data.append(data)
            
            print(f"Получено {len(candles_data)} свечей")
            return candles_data
        except Exception as e:
            print(f"Ошибка при получении свечей для {figi}: {e}")
            return None

def get_orderbook(figi, depth=20):
    """Получение стакана по FIGI"""
    print(f"\n=== Получение стакана глубиной {depth} для {figi} ===")
    with Client(TOKEN) as client:
        try:
            orderbook = client.market_data.get_order_book(figi=figi, depth=depth)
            
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
                'limit_down': format_money(orderbook.limit_down),
                'time': orderbook.time
            }
            
            print(f"Стакан получен. Бидов: {len(bids)}, Асков: {len(asks)}")
            return data
        except Exception as e:
            print(f"Ошибка при получении стакана для {figi}: {e}")
            return None

def get_trading_status(figi):
    """Получение торгового статуса инструмента"""
    print(f"\n=== Получение торгового статуса для {figi} ===")
    with Client(TOKEN) as client:
        try:
            response = client.market_data.get_trading_status(figi=figi)
            
            data = {
                'figi': response.figi,
                'trading_status': str(response.trading_status),
                'limit_order_available_flag': response.limit_order_available_flag,
                'market_order_available_flag': response.market_order_available_flag,
                'api_trade_available_flag': response.api_trade_available_flag,
                'time': response.time
            }
            
            print(f"Торговый статус: {data['trading_status']}")
            return data
        except Exception as e:
            print(f"Ошибка при получении торгового статуса для {figi}: {e}")
            return None

def get_portfolio(account_id):
    """Получение портфеля по счету"""
    print(f"\n=== Получение портфеля для счета {account_id} ===")
    with Client(TOKEN) as client:
        try:
            portfolio = client.operations.get_portfolio(account_id=account_id)
            
            positions = []
            for position in portfolio.positions:
                pos_data = {
                    'figi': position.figi,
                    'instrument_type': str(position.instrument_type),
                    'quantity': format_money(position.quantity),
                    'average_position_price': format_money(position.average_position_price),
                    'expected_yield': format_money(position.expected_yield),
                    'current_nkd': format_money(position.current_nkd),
                    'average_position_price_pt': format_money(position.average_position_price_pt),
                    'current_price': format_money(position.current_price),
                    'var_margin': format_money(position.var_margin),
                    'blocked': position.blocked,
                }
                positions.append(pos_data)
            
            data = {
                'account_id': account_id,
                'total_amount_shares': format_money(portfolio.total_amount_shares),
                'total_amount_bonds': format_money(portfolio.total_amount_bonds),
                'total_amount_etf': format_money(portfolio.total_amount_etf),
                'total_amount_currencies': format_money(portfolio.total_amount_currencies),
                'total_amount_futures': format_money(portfolio.total_amount_futures),
                'expected_yield': format_money(portfolio.expected_yield),
                'positions': positions
            }
            
            print(f"Портфель получен. Позиций: {len(positions)}")
            return data
        except Exception as e:
            print(f"Ошибка при получении портфеля для счета {account_id}: {e}")
            return None

def get_operations(account_id, from_date, to_date, figi=None):
    """Получение операций по счету за период"""
    print(f"\n=== Получение операций для счета {account_id} с {from_date} по {to_date} ===")
    with Client(TOKEN) as client:
        try:
            response = client.operations.get_operations(
                account_id=account_id,
                from_=from_date,
                to=to_date,
                figi=figi
            )
            
            operations = []
            for operation in response.operations:
                op_data = {
                    'id': operation.id,
                    'parent_operation_id': operation.parent_operation_id,
                    'currency': operation.currency,
                    'payment': format_money(operation.payment),
                    'price': format_money(operation.price),
                    'state': str(operation.state),
                    'quantity': operation.quantity,
                    'quantity_rest': operation.quantity_rest,
                    'figi': operation.figi,
                    'instrument_type': str(operation.instrument_type),
                    'date': operation.date,
                    'type': str(operation.type),
                    'operation_type': str(operation.operation_type)
                }
                operations.append(op_data)
            
            print(f"Получено {len(operations)} операций")
            return operations
        except Exception as e:
            print(f"Ошибка при получении операций для счета {account_id}: {e}")
            return None

def get_positions(account_id):
    """Получение позиций по счету"""
    print(f"\n=== Получение позиций для счета {account_id} ===")
    with Client(TOKEN) as client:
        try:
            positions = client.operations.get_positions(account_id=account_id)
            
            # Денежные средства
            money = []
            for m in positions.money:
                money.append({
                    'currency': m.currency,
                    'available': format_money(m.available),
                    'blocked': format_money(m.blocked)
                })
            
            # Ценные бумаги
            securities = []
            for sec in positions.securities:
                securities.append({
                    'figi': sec.figi,
                    'balance': sec.balance,
                    'blocked': sec.blocked,
                    'position_uid': sec.position_uid
                })
            
            # Фьючерсы
            futures = []
            for fut in positions.futures:
                futures.append({
                    'figi': fut.figi,
                    'balance': fut.balance,
                    'blocked': fut.blocked,
                    'position_uid': fut.position_uid
                })
            
            data = {
                'account_id': account_id,
                'money': money,
                'securities': securities,
                'futures': futures
            }
            
            print(f"Позиции получены. Деньги: {len(money)}, Ценные бумаги: {len(securities)}, Фьючерсы: {len(futures)}")
            return data
        except Exception as e:
            print(f"Ошибка при получении позиций для счета {account_id}: {e}")
            return None

def get_all_info_for_ozon():
    """Получение всей доступной информации о компании OZON через Tinkoff API"""
    result = {}
    
    # Получение счетов пользователя
    accounts = get_accounts()
    result['accounts'] = accounts
    
    # Поиск инструмента OZON
    instrument = get_instrument_by_ticker(TICKER)
    if not instrument:
        print(f"Инструмент {TICKER} не найден. Завершение работы.")
        return
    
    result['basic_info'] = instrument
    figi = instrument['figi']
    
    # Получение дополнительной информации об инструменте по FIGI
    instrument_details = get_instrument_by_figi(figi)
    if instrument_details:
        result['instrument_details'] = instrument_details
    
    # Получение последней цены
    last_price = get_last_prices(figi)
    if last_price:
        result['current_price'] = last_price
    
    # Получение торгового статуса
    trading_status = get_trading_status(figi)
    if trading_status:
        result['trading_status'] = trading_status
    
    # Получение стакана
    orderbook = get_orderbook(figi, depth=20)
    if orderbook:
        result['orderbook'] = orderbook
    
    # Получение свечей разных таймфреймов
    now_dt = now()
    
    # Дневные свечи за 30 дней
    from_date_30d = now_dt - timedelta(days=30)
    daily_candles = get_candles(figi, from_date_30d, now_dt, CandleInterval.CANDLE_INTERVAL_DAY)
    if daily_candles:
        result['daily_prices_30d'] = daily_candles
    
    # Часовые свечи за 7 дней
    from_date_7d = now_dt - timedelta(days=7)
    hourly_candles = get_candles(figi, from_date_7d, now_dt, CandleInterval.CANDLE_INTERVAL_HOUR)
    if hourly_candles:
        result['hourly_prices_7d'] = hourly_candles
    
    # 15-минутные свечи за 2 дня
    from_date_2d = now_dt - timedelta(days=2)
    min15_candles = get_candles(figi, from_date_2d, now_dt, CandleInterval.CANDLE_INTERVAL_15_MIN)
    if min15_candles:
        result['min15_prices_2d'] = min15_candles
    
    # Если есть счета, получим информацию по ним
    if accounts:
        account_id = accounts[0]['id']  # Используем первый счет для примера
        
        # Получение портфеля
        portfolio = get_portfolio(account_id)
        if portfolio:
            result['portfolio'] = portfolio
        
        # Получение позиций
        positions = get_positions(account_id)
        if positions:
            result['positions'] = positions
        
        # Получение операций за последние 30 дней
        from_date_ops = now_dt - timedelta(days=30)
        operations = get_operations(account_id, from_date_ops, now_dt, figi)
        if operations:
            result['operations'] = operations
    
    # Сохраняем результаты в JSON файл
    save_to_json(f"{TICKER}_info.json", result)
    
    return result

if __name__ == "__main__":
    if not TOKEN:
        print("Ошибка: не найден токен Tinkoff API. Проверьте файл .env")
    else:
        print(f"Начинаем получение данных о компании {TICKER} через Tinkoff API")
        get_all_info_for_ozon()
        print("Работа скрипта завершена.") 