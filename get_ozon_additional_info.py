import os
import json
import pandas as pd
import requests
from bs4 import BeautifulSoup
from datetime import datetime, timedelta
from dotenv import load_dotenv
from tinkoff.invest import Client, InstrumentIdType, CandleInterval
import yfinance as yf

# Загрузка переменных окружения
load_dotenv()

# Получение токена из переменных окружения
TOKEN = os.getenv("TINKOFF_INVEST_TOKEN")
TICKER = "OZON"

def get_tinkoff_data():
    """Получение расширенных данных из Tinkoff API"""
    try:
        with Client(TOKEN) as client:
            # Сначала найдем инструмент по тикеру
            instruments = client.instruments.find_instrument(query=TICKER)
            
            instrument = None
            for instr in instruments.instruments:
                if instr.ticker.upper() == TICKER.upper():
                    instrument = instr
                    break
            
            if not instrument:
                print(f"Инструмент {TICKER} не найден")
                return None
            
            # Получим инструмент по FIGI
            figi = instrument.figi
            
            # Получение всех доступных облигаций компании
            bonds = []
            try:
                all_bonds = client.instruments.bonds().instruments
                company_bonds = [bond for bond in all_bonds if TICKER.lower() in bond.name.lower()]
                
                for bond in company_bonds:
                    bonds.append({
                        'name': bond.name,
                        'ticker': bond.ticker,
                        'figi': bond.figi,
                        'currency': bond.currency,
                        'nominal': float(bond.nominal.units) + float(bond.nominal.nano) / 1_000_000_000 if bond.nominal else None,
                        'maturity_date': bond.maturity_date if bond.maturity_date else None
                    })
            except Exception as e:
                print(f"Ошибка при получении облигаций: {e}")
            
            # Получение расширенной информации о торгах
            trading_info = {}
            try:
                trading_schedules = client.instruments.trading_schedules(
                    exchange=instrument.exchange,
                    from_=datetime.utcnow(),
                    to=datetime.utcnow() + timedelta(days=7)
                )
                
                for schedule in trading_schedules.exchanges:
                    trading_days = []
                    for day in schedule.days:
                        trading_days.append({
                            'date': day.date,
                            'is_trading_day': day.is_trading_day,
                            'start_time': day.start_time if day.start_time else None,
                            'end_time': day.end_time if day.end_time else None,
                            'opening_auction_start_time': day.opening_auction_start_time if day.opening_auction_start_time else None,
                            'closing_auction_end_time': day.closing_auction_end_time if day.closing_auction_end_time else None
                        })
                    
                    trading_info[schedule.exchange] = trading_days
            except Exception as e:
                print(f"Ошибка при получении расписания торгов: {e}")
            
            return {
                'bonds': bonds,
                'trading_schedule': trading_info
            }
            
    except Exception as e:
        print(f"Ошибка при работе с Tinkoff API: {e}")
        return None

def get_yahoo_finance_data():
    """Получение данных о компании из Yahoo Finance"""
    try:
        # OZON торгуется на NASDAQ под тикером OZON
        ticker = yf.Ticker("OZON")
        
        # Основная информация
        info = ticker.info
        
        # Календарь событий
        calendar = ticker.calendar
        
        # Рекомендации аналитиков
        recommendations = ticker.recommendations
        
        # Основные держатели акций
        major_holders = ticker.major_holders
        institutional_holders = ticker.institutional_holders
        
        # Финансовые показатели
        balance_sheet = ticker.balance_sheet
        income_stmt = ticker.income_stmt
        cash_flow = ticker.cashflow
        
        # Оценки аналитиков
        earnings_estimates = ticker.earnings_estimates
        revenue_estimates = ticker.revenue_estimates
        
        # Преобразуем в словарь
        yahoo_data = {
            'info': info,
            'calendar': calendar.to_dict() if calendar is not None else None,
            'recommendations': recommendations.to_dict('records') if recommendations is not None else None,
            'major_holders': major_holders.to_dict('records') if major_holders is not None else None,
            'institutional_holders': institutional_holders.to_dict('records') if institutional_holders is not None else None,
            'balance_sheet': balance_sheet.to_dict() if balance_sheet is not None else None,
            'income_stmt': income_stmt.to_dict() if income_stmt is not None else None,
            'cash_flow': cash_flow.to_dict() if cash_flow is not None else None,
            'earnings_estimates': earnings_estimates.to_dict() if earnings_estimates is not None else None,
            'revenue_estimates': revenue_estimates.to_dict() if revenue_estimates is not None else None
        }
        
        return yahoo_data
    except Exception as e:
        print(f"Ошибка при получении данных из Yahoo Finance: {e}")
        return None

def get_moex_data():
    """Получение данных о компании с Московской биржи"""
    try:
        # URL для API Московской Биржи
        url = f"https://iss.moex.com/iss/engines/stock/markets/shares/securities/{TICKER}.json"
        
        response = requests.get(url)
        if response.status_code == 200:
            data = response.json()
            
            # Получаем информацию о торгах
            securities = pd.DataFrame(data['securities']['data'], 
                                     columns=data['securities']['columns'])
            
            # Получаем информацию о котировках
            marketdata = pd.DataFrame(data['marketdata']['data'], 
                                     columns=data['marketdata']['columns'])
            
            return {
                'securities': securities.to_dict('records'),
                'marketdata': marketdata.to_dict('records')
            }
        else:
            print(f"Ошибка при получении данных с Московской биржи. Код: {response.status_code}")
            return None
    except Exception as e:
        print(f"Ошибка при получении данных с Московской биржи: {e}")
        return None

def get_news_data():
    """Получение новостей о компании"""
    try:
        # Получение новостей с Investing.com
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
        }
        
        # Поиск новостей по запросу "Ozon"
        url = f"https://www.investing.com/search/?q={TICKER}"
        response = requests.get(url, headers=headers)
        
        news = []
        if response.status_code == 200:
            soup = BeautifulSoup(response.text, 'html.parser')
            
            # Извлечение новостей (этот код может нуждаться в корректировке в зависимости от структуры сайта)
            news_items = soup.select('.js-article-item')
            
            for item in news_items[:10]:  # Ограничиваем 10 новостями
                try:
                    title_elem = item.select_one('.js-article-item-title')
                    link_elem = item.select_one('a.js-article-item-title')
                    date_elem = item.select_one('.js-article-item-date')
                    
                    if title_elem and link_elem and date_elem:
                        title = title_elem.text.strip()
                        link = 'https://www.investing.com' + link_elem['href'] if link_elem.has_attr('href') else None
                        date = date_elem.text.strip()
                        
                        news.append({
                            'title': title,
                            'link': link,
                            'date': date
                        })
                except Exception as e:
                    print(f"Ошибка при обработке новости: {e}")
        
        return {
            'investing_news': news
        }
    except Exception as e:
        print(f"Ошибка при получении новостей: {e}")
        return None

def main():
    """Получение и сохранение всей доступной информации о компании OZON"""
    print(f"Получение дополнительной информации о компании {TICKER}...")
    
    # Получаем данные из разных источников
    print("Получение данных из Tinkoff API...")
    tinkoff_data = get_tinkoff_data()
    
    print("Получение данных из Yahoo Finance...")
    yahoo_data = get_yahoo_finance_data()
    
    print("Получение данных с Московской биржи...")
    moex_data = get_moex_data()
    
    print("Получение новостей...")
    news_data = get_news_data()
    
    # Объединяем все данные
    all_data = {
        'tinkoff_additional': tinkoff_data,
        'yahoo_finance': yahoo_data,
        'moex': moex_data,
        'news': news_data
    }
    
    # Сохраняем данные в JSON-файл
    output_file = f"{TICKER}_additional_info.json"
    with open(output_file, 'w', encoding='utf-8') as f:
        json.dump(all_data, f, ensure_ascii=False, indent=2, default=str)
    
    print(f"Дополнительная информация о компании {TICKER} сохранена в файл {output_file}")
    
    # Для удобства вывода, распечатаем часть информации
    print("\nКраткая сводка:")
    
    if tinkoff_data and 'bonds' in tinkoff_data:
        bonds_count = len(tinkoff_data['bonds'])
        print(f"Найдено облигаций: {bonds_count}")
    
    if yahoo_data and 'info' in yahoo_data and yahoo_data['info']:
        info = yahoo_data['info']
        print("\nОсновная информация из Yahoo Finance:")
        print(f"Полное название: {info.get('longName', 'Н/Д')}")
        print(f"Сектор: {info.get('sector', 'Н/Д')}")
        print(f"Индустрия: {info.get('industry', 'Н/Д')}")
        print(f"Сотрудников: {info.get('fullTimeEmployees', 'Н/Д')}")
        print(f"Страна: {info.get('country', 'Н/Д')}")
        print(f"Вебсайт: {info.get('website', 'Н/Д')}")
        
        print("\nФинансовые показатели:")
        print(f"Рыночная капитализация: {info.get('marketCap', 'Н/Д')}")
        print(f"P/E (прямой): {info.get('trailingPE', 'Н/Д')}")
        print(f"P/E (прогнозный): {info.get('forwardPE', 'Н/Д')}")
        print(f"PEG Ratio: {info.get('pegRatio', 'Н/Д')}")
        print(f"Прибыль на акцию (EPS): {info.get('trailingEps', 'Н/Д')}")
        print(f"Квартальный рост выручки: {info.get('revenueQuarterlyGrowth', 'Н/Д')}")
        print(f"Квартальный рост прибыли: {info.get('earningsQuarterlyGrowth', 'Н/Д')}")
    
    if moex_data and 'securities' in moex_data and moex_data['securities']:
        print("\nДанные Московской биржи:")
        print(f"Количество записей: {len(moex_data['securities'])}")

    if news_data and 'investing_news' in news_data and news_data['investing_news']:
        print("\nПоследние новости:")
        for i, news in enumerate(news_data['investing_news'][:3], 1):
            print(f"{i}. {news.get('title', 'Н/Д')} ({news.get('date', 'Н/Д')})")

if __name__ == "__main__":
    main() 