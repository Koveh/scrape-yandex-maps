"""
Скрипт для сопоставления схемы БД из instruction.md с данными, 
получаемыми из Tinkoff API. Показывает какие данные куда можно сохранять.
"""

SCHEMA_TO_TINKOFF_MAPPING = {
    # Справочные таблицы
    "stocks": {
        "описание": "Основная информация о акциях",
        "данные_tinkoff": [
            "company.ticker - ticker",
            "company.name - name",
            "company.isin - isin",
            "company.sector - sector_id (через связь с sectors)",
            "company.class_code - связь с industry",
            "company.exchange - exchange_id (через связь с exchanges)",
            "company.currency - currency",
            "company.country_of_risk - country"
        ]
    },
    
    # Таблицы данных с высокой частотой обновления (каждую минуту)
    "stock_prices": {
        "описание": "Цены акций (высокочастотные обновления)",
        "данные_tinkoff": [
            "get_last_price - получение текущей цены для stock_id",
            "last_price['price'] - price",
            "last_price['price'] - close_price из предыдущей записи - price_change",
            "(last_price['price'] - close_price) / close_price * 100 - price_change_percent",
            "company_info['current_price']['time'] - timestamp"
        ]
    },
    "stock_intraday": {
        "описание": "Внутридневные данные",
        "данные_tinkoff": [
            "get_company_prices с interval=CandleInterval.CANDLE_INTERVAL_15_MIN - 15-минутные свечи",
            "get_company_prices с interval=CandleInterval.CANDLE_INTERVAL_HOUR - часовые свечи",
            "candle.open - open_price",
            "candle.high - high_price",
            "candle.low - low_price",
            "candle.close - close_price",
            "candle.volume - volume",
            "interval_minutes = 15, 60 и т.д.",
            "candle.time - timestamp"
        ]
    },
    
    # Таблицы данных со средней частотой обновления (10 минут, 1 час)
    "stock_metrics_hourly": {
        "описание": "Ключевые метрики, обновляемые ежечасно",
        "данные_tinkoff": [
            "last_price['price'] - price",
            "Для market_cap и других метрик требуются дополнительные расчеты",
            "Часть этих данных недоступна напрямую через API",
            "Для volume_avg_30min можно использовать усреднение из stock_intraday"
        ]
    },
    "stock_orderbook": {
        "описание": "Стакан заявок (обновление каждые 10 минут)",
        "данные_tinkoff": [
            "get_orderbook - получение стакана заявок",
            "orderbook_data - полный стакан в JSON формате",
            "orderbook['bids'] и orderbook['asks'] - заявки на покупку и продажу"
        ]
    },
    
    # Таблицы данных с низкой частотой обновления (ежедневно или реже)
    "stock_daily_performance": {
        "описание": "Ежедневные показатели эффективности",
        "данные_tinkoff": [
            "get_company_prices с interval=CandleInterval.CANDLE_INTERVAL_DAY - дневные свечи",
            "candle.open - open_price",
            "candle.high - high_price",
            "candle.low - low_price",
            "candle.close - close_price",
            "candle.close - adjusted_close (без учета дивидендов и сплитов)",
            "candle.volume - volume",
            "Для dividend и split_coefficient требуются дополнительные запросы",
            "candle.time - для получения date"
        ]
    },
    
    # Таблицы с недостаточными данными из Tinkoff API
    "stock_financial_ratios": {
        "описание": "Финансовые коэффициенты",
        "данные_tinkoff": [
            "Данные недоступны напрямую через Tinkoff API",
            "Требуется использование дополнительных источников данных"
        ]
    },
    "stock_dividend_info": {
        "описание": "Информация о дивидендах",
        "данные_tinkoff": [
            "Частично доступно через company.div_yield_flag (флаг выплаты дивидендов)",
            "Для детальной информации требуются другие источники данных"
        ]
    },
    "stock_ownership": {
        "описание": "Структура собственности",
        "данные_tinkoff": [
            "Не доступно через Tinkoff API",
            "Требуется использование дополнительных источников данных"
        ]
    },
}

def main():
    """Вывод информации о сопоставлении схемы БД и Tinkoff API"""
    print("\nСОПОСТАВЛЕНИЕ СХЕМЫ БАЗЫ ДАННЫХ И ДАННЫХ ИЗ TINKOFF API\n")
    
    for table_name, info in SCHEMA_TO_TINKOFF_MAPPING.items():
        print(f"Таблица: {table_name}")
        print(f"Описание: {info['описание']}")
        print("Данные из Tinkoff API:")
        
        if info['данные_tinkoff']:
            for data_item in info['данные_tinkoff']:
                print(f"  - {data_item}")
        else:
            print("  - Данные недоступны через Tinkoff API")
        
        print()

if __name__ == "__main__":
    main() 