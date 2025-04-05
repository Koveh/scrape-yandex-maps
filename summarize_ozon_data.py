import json
import os
import pandas as pd
from datetime import datetime
from collections import defaultdict

# Имена файлов с данными
JSON_FILES = [
    "OZON_info.json",
    "OZON_additional_info.json"
]

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

def extract_basic_info(data_files):
    """Извлечение основной информации о компании из всех источников данных"""
    basic_info = {}
    
    # Базовая информация из Tinkoff API
    tinkoff_data = data_files.get("OZON_info.json", {})
    if tinkoff_data and 'basic_info' in tinkoff_data:
        basic_info['tinkoff'] = tinkoff_data['basic_info']
    
    # Информация с MOEX
    additional_data = data_files.get("OZON_additional_info.json", {})
    if additional_data and 'moex' in additional_data and additional_data['moex']:
        basic_info['moex'] = additional_data['moex'].get('securities', [])
    
    return basic_info

def extract_price_data(data_files):
    """Извлечение данных о ценах акций из всех источников данных"""
    price_data = defaultdict(list)
    
    # Текущая цена из Tinkoff API
    tinkoff_data = data_files.get("OZON_info.json", {})
    if tinkoff_data and 'current_price' in tinkoff_data:
        price_data['current'].append({
            'source': 'tinkoff',
            'price': tinkoff_data['current_price'].get('price'),
            'time': tinkoff_data['current_price'].get('time'),
            'currency': tinkoff_data.get('basic_info', {}).get('currency')
        })
    
    # Исторические цены (дневные) из Tinkoff API
    if tinkoff_data and 'daily_prices_30d' in tinkoff_data:
        price_data['daily'] = tinkoff_data['daily_prices_30d']
    
    # Исторические цены (часовые) из Tinkoff API
    if tinkoff_data and 'hourly_prices_7d' in tinkoff_data:
        price_data['hourly'] = tinkoff_data['hourly_prices_7d']
    
    # Исторические цены (15-минутные) из Tinkoff API
    if tinkoff_data and 'min15_prices_2d' in tinkoff_data:
        price_data['min15'] = tinkoff_data['min15_prices_2d']
    
    # Стакан заявок
    if tinkoff_data and 'orderbook' in tinkoff_data:
        price_data['orderbook'] = tinkoff_data['orderbook']
    
    return price_data

def extract_financial_data(data_files):
    """Извлечение финансовых показателей из всех источников данных"""
    financial_data = {}
    
    # Yahoo Finance данные
    additional_data = data_files.get("OZON_additional_info.json", {})
    if additional_data and 'yahoo_finance' in additional_data and additional_data['yahoo_finance']:
        yahoo_data = additional_data['yahoo_finance']
        
        # Основная информация
        if 'info' in yahoo_data and yahoo_data['info']:
            financial_data['info'] = yahoo_data['info']
        
        # Финансовая отчетность
        financial_statements = {}
        if 'balance_sheet' in yahoo_data and yahoo_data['balance_sheet']:
            financial_statements['balance_sheet'] = yahoo_data['balance_sheet']
        
        if 'income_stmt' in yahoo_data and yahoo_data['income_stmt']:
            financial_statements['income_statement'] = yahoo_data['income_stmt']
        
        if 'cash_flow' in yahoo_data and yahoo_data['cash_flow']:
            financial_statements['cash_flow'] = yahoo_data['cash_flow']
        
        if financial_statements:
            financial_data['financial_statements'] = financial_statements
    
    return financial_data

def extract_news_data(data_files):
    """Извлечение новостей из всех источников данных"""
    news_data = []
    
    # Новости Investing.com
    additional_data = data_files.get("OZON_additional_info.json", {})
    if additional_data and 'news' in additional_data and additional_data['news']:
        investing_news = additional_data['news'].get('investing_news', [])
        for news in investing_news:
            news['source'] = 'investing.com'
            news_data.append(news)
    
    # Новости РБК
    rbc_data = data_files.get("OZON_rbc_info.json", {})
    if rbc_data and 'news' in rbc_data and rbc_data['news']:
        for news in rbc_data['news']:
            news['source'] = 'rbc.ru'
            news_data.append(news)
    
    # Сортировка новостей по дате (если возможно)
    if news_data:
        # Это примерная сортировка, может потребоваться доработка в зависимости от формата дат
        news_data.sort(key=lambda x: x.get('date', ''), reverse=True)
    
    return news_data

def summarize_data(basic_info, price_data, financial_data, news_data):
    """Создание сводной информации о компании"""
    summary = {
        'company_name': "Ozon Holdings PLC",
        'ticker': "OZON",
        'summary_date': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
    }
    
    # Базовая информация
    if basic_info and 'tinkoff' in basic_info:
        tinkoff_info = basic_info['tinkoff']
        summary.update({
            'name': tinkoff_info.get('name'),
            'isin': tinkoff_info.get('isin'),
            'currency': tinkoff_info.get('currency'),
            'exchange': tinkoff_info.get('exchange'),
            'country': tinkoff_info.get('country_of_risk_name'),
            'sector': tinkoff_info.get('sector'),
        })
    
    # Цены
    if price_data:
        if 'current' in price_data and price_data['current']:
            current_price = price_data['current'][0]
            summary['current_price'] = {
                'price': current_price.get('price'),
                'time': current_price.get('time'),
                'currency': current_price.get('currency')
            }
        
        # Статистика по ценам
        if 'daily' in price_data and price_data['daily']:
            daily_df = pd.DataFrame(price_data['daily'])
            if not daily_df.empty:
                summary['price_statistics'] = {
                    'max_price_30d': daily_df['high'].max(),
                    'min_price_30d': daily_df['low'].min(),
                    'avg_price_30d': daily_df['close'].mean(),
                    'total_volume_30d': daily_df['volume'].sum(),
                    'price_volatility_30d': daily_df['close'].std() / daily_df['close'].mean() * 100  # в процентах
                }
    
    # Финансовые показатели
    if financial_data and 'info' in financial_data:
        info = financial_data['info']
        financial_metrics = {
            'market_cap': info.get('marketCap'),
            'trailing_pe': info.get('trailingPE'),
            'forward_pe': info.get('forwardPE'),
            'revenue_growth': info.get('revenueGrowth'),
            'profit_margins': info.get('profitMargins'),
            'eps': info.get('trailingEps'),
            'dividend_yield': info.get('dividendYield', 0),
        }
        summary['financial_metrics'] = financial_metrics
    
    # Последние новости
    if news_data:
        summary['latest_news'] = news_data[:5]  # Только последние 5 новостей
    
    return summary

def main():
    """Основная функция для обработки и обобщения данных о компании OZON"""
    print("Загрузка и обобщение данных о компании OZON...")
    
    # Загружаем данные из всех JSON файлов
    data_files = {}
    for filename in JSON_FILES:
        data = load_json_data(filename)
        if data:
            data_files[filename] = data
    
    # Если нет данных, завершаем работу
    if not data_files:
        print("Не удалось загрузить данные. Убедитесь, что файлы с данными существуют.")
        return
    
    # Извлекаем и обобщаем данные
    basic_info = extract_basic_info(data_files)
    price_data = extract_price_data(data_files)
    financial_data = extract_financial_data(data_files)
    news_data = extract_news_data(data_files)
    
    # Создаем сводную информацию
    summary = summarize_data(basic_info, price_data, financial_data, news_data)
    
    # Сохраняем сводную информацию в JSON
    output_file = "OZON_summary.json"
    with open(output_file, 'w', encoding='utf-8') as f:
        json.dump(summary, f, ensure_ascii=False, indent=2, default=str)
    
    print(f"Сводная информация о компании OZON сохранена в файл {output_file}")
    
    # Выводим краткую сводку
    print("\nКраткая сводка о компании OZON:")
    print(f"Название: {summary.get('name', 'Н/Д')}")
    print(f"Тикер: {summary.get('ticker', 'Н/Д')}")
    print(f"Биржа: {summary.get('exchange', 'Н/Д')}")
    
    if 'current_price' in summary:
        current_price = summary['current_price']
        print(f"Текущая цена: {current_price.get('price')} {current_price.get('currency')}")
    
    if 'price_statistics' in summary:
        stats = summary['price_statistics']
        print("\nСтатистика цен за 30 дней:")
        print(f"Максимум: {stats.get('max_price_30d')}")
        print(f"Минимум: {stats.get('min_price_30d')}")
        print(f"Средняя: {stats.get('avg_price_30d'):.2f}")
        print(f"Волатильность: {stats.get('price_volatility_30d'):.2f}%")
    
    if 'financial_metrics' in summary:
        metrics = summary['financial_metrics']
        print("\nФинансовые показатели:")
        print(f"Рыночная капитализация: {metrics.get('market_cap')}")
        print(f"P/E: {metrics.get('trailing_pe')}")
        print(f"EPS: {metrics.get('eps')}")
    
    if 'latest_news' in summary and summary['latest_news']:
        print("\nПоследние новости:")
        for i, news in enumerate(summary['latest_news'][:3], 1):
            print(f"{i}. {news.get('title')} ({news.get('date')}) - {news.get('source')}")

if __name__ == "__main__":
    main() 