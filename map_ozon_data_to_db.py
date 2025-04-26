import json
import os
from datetime import datetime

def load_json_data(filename):
    """Загрузка данных из JSON файла"""
    try:
        if not os.path.exists(filename):
            print(f"Файл {filename} не найден")
            return None
        
        with open(filename, 'r', encoding='utf-8') as f:
            data = json.load(f)
        
        return data
    except Exception as e:
        print(f"Ошибка при чтении файла {filename}: {e}")
        return None

def generate_sql_for_stock(data):
    """Генерация SQL для вставки основной информации о компании в таблицу stocks"""
    if not data:
        return None
    
    basic_info = data.get('basic_info', {})
    
    # Базовые данные для stocks
    ticker = basic_info.get('ticker')
    isin = basic_info.get('isin') or 'NULL'
    name = basic_info.get('name')
    sector_id = 'NULL'  # Требуется определить ID сектора из таблицы sectors
    industry_id = 'NULL'  # Требуется определить ID индустрии из таблицы industries
    exchange_id = 'NULL'  # Требуется определить ID биржи из таблицы exchanges
    currency = basic_info.get('currency')
    country = basic_info.get('country_of_risk') or 'NULL'
    
    # Защита от SQL-инъекций и форматирование данных
    if name:
        name = name.replace("'", "''")
    
    # SQL запрос
    sql = f"""
-- Вставка данных о компании OZON в таблицу stocks
INSERT INTO stocks 
(ticker, isin, name, sector_id, industry_id, exchange_id, currency, country, is_active, created_at, updated_at)
VALUES 
('{ticker}', '{isin}', '{name}', {sector_id}, {industry_id}, {exchange_id}, '{currency}', '{country}', TRUE, NOW(), NOW());
"""
    
    return sql

def generate_sql_for_stock_prices(data):
    """Генерация SQL для вставки текущих цен в таблицу stock_prices"""
    if not data or 'current_price' not in data:
        return None
    
    current_price = data.get('current_price', {})
    price = current_price.get('price')
    timestamp = current_price.get('time')
    
    # SQL для получения stock_id и source_id
    sql = f"""
-- Вставка текущей цены акции OZON в таблицу stock_prices
WITH stock_data AS (
    SELECT id FROM stocks WHERE ticker = 'OZON' LIMIT 1
),
source_data AS (
    SELECT id FROM sources WHERE name = 'Tinkoff' LIMIT 1
)
INSERT INTO stock_prices 
(stock_id, source_id, price, price_change, price_change_percent, volume, timestamp)
SELECT 
    (SELECT id FROM stock_data),
    (SELECT id FROM source_data),
    {price},
    NULL, -- Для price_change требуются предыдущие данные
    NULL, -- Для price_change_percent требуются предыдущие данные
    NULL, -- Нет данных о текущем объеме
    '{timestamp}'::TIMESTAMP;
"""
    
    return sql

def generate_sql_for_stock_intraday(data):
    """Генерация SQL для вставки внутридневных данных в таблицу stock_intraday"""
    if not data or 'hourly_prices_7d' not in data:
        return None
    
    hourly_prices = data.get('hourly_prices_7d', [])
    
    # Заготовка SQL запроса
    sql = f"""
-- Вставка внутридневных данных для акции OZON в таблицу stock_intraday
WITH stock_data AS (
    SELECT id FROM stocks WHERE ticker = 'OZON' LIMIT 1
),
source_data AS (
    SELECT id FROM sources WHERE name = 'Tinkoff' LIMIT 1
)
INSERT INTO stock_intraday 
(stock_id, source_id, open_price, high_price, low_price, close_price, volume, interval_minutes, timestamp)
VALUES
"""
    
    # Добавление данных для каждого временного интервала
    for i, price_data in enumerate(hourly_prices):
        time = price_data.get('time')
        open_price = price_data.get('open')
        high_price = price_data.get('high')
        low_price = price_data.get('low')
        close_price = price_data.get('close')
        volume = price_data.get('volume')
        
        # Интервал в минутах (для часовых данных = 60)
        interval_minutes = 60
        
        value_line = f"""(
    (SELECT id FROM stock_data),
    (SELECT id FROM source_data),
    {open_price},
    {high_price},
    {low_price},
    {close_price},
    {volume},
    {interval_minutes},
    '{time}'::TIMESTAMP)"""
        
        sql += value_line
        
        # Добавляем запятую между записями, кроме последней
        if i < len(hourly_prices) - 1:
            sql += ",\n"
        else:
            sql += ";"
    
    return sql

def generate_sql_for_stock_daily_performance(data):
    """Генерация SQL для вставки ежедневных данных в таблицу stock_daily_performance"""
    if not data or 'daily_prices_30d' not in data:
        return None
    
    daily_prices = data.get('daily_prices_30d', [])
    
    # Заготовка SQL запроса
    sql = f"""
-- Вставка ежедневных данных для акции OZON в таблицу stock_daily_performance
WITH stock_data AS (
    SELECT id FROM stocks WHERE ticker = 'OZON' LIMIT 1
),
source_data AS (
    SELECT id FROM sources WHERE name = 'Tinkoff' LIMIT 1
)
INSERT INTO stock_daily_performance 
(stock_id, source_id, date, open_price, high_price, low_price, close_price, adjusted_close, volume, effective_date, is_actual)
VALUES
"""
    
    # Добавление данных для каждого дня
    for i, price_data in enumerate(daily_prices):
        time = price_data.get('time')
        date = time.split()[0]  # Берем только дату из временной метки
        open_price = price_data.get('open')
        high_price = price_data.get('high')
        low_price = price_data.get('low')
        close_price = price_data.get('close')
        volume = price_data.get('volume')
        
        value_line = f"""(
    (SELECT id FROM stock_data),
    (SELECT id FROM source_data),
    '{date}'::DATE,
    {open_price},
    {high_price},
    {low_price},
    {close_price},
    {close_price}, -- adjusted_close (равен close для простоты)
    {volume},
    NOW(), -- effective_date
    TRUE)""" # is_actual
        
        sql += value_line
        
        # Добавляем запятую между записями, кроме последней
        if i < len(daily_prices) - 1:
            sql += ",\n"
        else:
            sql += ";"
    
    return sql

def generate_sql_for_stock_orderbook(data):
    """Генерация SQL для вставки стакана заявок в таблицу stock_orderbook"""
    if not data or 'orderbook' not in data:
        return None
    
    orderbook = data.get('orderbook', {})
    
    # SQL запрос
    sql = f"""
-- Вставка стакана заявок для акции OZON в таблицу stock_orderbook
WITH stock_data AS (
    SELECT id FROM stocks WHERE ticker = 'OZON' LIMIT 1
),
source_data AS (
    SELECT id FROM sources WHERE name = 'Tinkoff' LIMIT 1
)
INSERT INTO stock_orderbook 
(stock_id, source_id, timestamp, data)
SELECT 
    (SELECT id FROM stock_data),
    (SELECT id FROM source_data),
    NOW(),
    '{json.dumps(orderbook)}'::JSONB;
"""
    
    return sql

def main():
    """Основная функция для создания SQL запросов для вставки данных OZON в БД"""
    print("Создание SQL запросов для вставки данных OZON в базу данных...")
    
    # Загружаем данные из файлов JSON
    ozon_data = load_json_data("OZON_info.json")
    ozon_summary = load_json_data("OZON_summary.json")
    
    # Если нет данных, завершаем работу
    if not ozon_data:
        print("Не удалось загрузить данные о компании OZON.")
        return
    
    # Генерируем SQL запросы
    sql_statements = []
    
    # 1. SQL для вставки основной информации о компании
    stock_sql = generate_sql_for_stock(ozon_data)
    if stock_sql:
        sql_statements.append(stock_sql)
    
    # 2. SQL для вставки текущих цен
    price_sql = generate_sql_for_stock_prices(ozon_data)
    if price_sql:
        sql_statements.append(price_sql)
    
    # 3. SQL для вставки внутридневных данных
    intraday_sql = generate_sql_for_stock_intraday(ozon_data)
    if intraday_sql:
        sql_statements.append(intraday_sql)
    
    # 4. SQL для вставки ежедневных данных
    daily_sql = generate_sql_for_stock_daily_performance(ozon_data)
    if daily_sql:
        sql_statements.append(daily_sql)
    
    # 5. SQL для вставки стакана заявок
    orderbook_sql = generate_sql_for_stock_orderbook(ozon_data)
    if orderbook_sql:
        sql_statements.append(orderbook_sql)
    
    # Сохраняем SQL запросы в файл
    output_file = "ozon_db_insert.sql"
    with open(output_file, 'w', encoding='utf-8') as f:
        f.write(f"-- SQL запросы для вставки данных OZON в базу данных\n")
        f.write(f"-- Сгенерировано: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n\n")
        
        for sql in sql_statements:
            f.write(sql)
            f.write("\n\n")
    
    print(f"SQL запросы сохранены в файл {output_file}")
    
    # Создаем отображение данных OZON в схему БД (только для справки)
    output_mapping_file = "ozon_db_mapping.txt"
    with open(output_mapping_file, 'w', encoding='utf-8') as f:
        f.write("Отображение данных OZON в схему базы данных\n")
        f.write("=============================================\n\n")
        
        f.write("1. Таблица stocks (основная информация о компании)\n")
        f.write("   - ticker: OZON\n")
        f.write(f"   - isin: {ozon_data.get('basic_info', {}).get('isin', 'Н/Д')}\n")
        f.write(f"   - name: {ozon_data.get('basic_info', {}).get('name', 'Н/Д')}\n")
        f.write(f"   - sector_id: Требуется определить из таблицы sectors\n")
        f.write(f"   - industry_id: Требуется определить из таблицы industries\n")
        f.write(f"   - exchange_id: Требуется определить из таблицы exchanges\n")
        f.write(f"   - currency: {ozon_data.get('basic_info', {}).get('currency', 'Н/Д')}\n")
        f.write(f"   - country: {ozon_data.get('basic_info', {}).get('country_of_risk', 'Н/Д')}\n\n")
        
        f.write("2. Таблица stock_prices (текущие цены)\n")
        if 'current_price' in ozon_data:
            f.write(f"   - price: {ozon_data['current_price'].get('price', 'Н/Д')}\n")
            f.write(f"   - timestamp: {ozon_data['current_price'].get('time', 'Н/Д')}\n\n")
        
        f.write("3. Таблица stock_intraday (внутридневные данные)\n")
        f.write(f"   - Доступно записей: {len(ozon_data.get('hourly_prices_7d', []))}\n")
        f.write(f"   - interval_minutes: 60 (часовые данные)\n\n")
        
        f.write("4. Таблица stock_daily_performance (ежедневные данные)\n")
        f.write(f"   - Доступно записей: {len(ozon_data.get('daily_prices_30d', []))}\n\n")
        
        f.write("5. Таблица stock_orderbook (стакан заявок)\n")
        if 'orderbook' in ozon_data:
            orderbook = ozon_data['orderbook']
            f.write(f"   - depth: {orderbook.get('depth', 'Н/Д')}\n")
            f.write(f"   - last_price: {orderbook.get('last_price', 'Н/Д')}\n")
            f.write(f"   - close_price: {orderbook.get('close_price', 'Н/Д')}\n")
    
    print(f"Отображение данных OZON в схему БД сохранено в файл {output_mapping_file}")

if __name__ == "__main__":
    main() 