import os
import json
import time
import random
import requests
from bs4 import BeautifulSoup
from datetime import datetime
from dotenv import load_dotenv
from tinkoff.invest import Client

# Загрузка переменных окружения
load_dotenv()

# Получение токена из переменных окружения
TOKEN = os.getenv("TINKOFF_INVEST_TOKEN")
TICKER = "OZON"

# Заголовки для имитации браузера
USER_AGENTS = [
    'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
    'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/92.0.4515.107 Safari/537.36',
    'Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:90.0) Gecko/20100101 Firefox/90.0',
    'Mozilla/5.0 (Macintosh; Intel Mac OS X 11.5; rv:90.0) Gecko/20100101 Firefox/90.0'
]

headers = {
    'User-Agent': random.choice(USER_AGENTS),
    'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
    'Accept-Language': 'ru-RU,ru;q=0.8,en-US;q=0.5,en;q=0.3',
    'Connection': 'keep-alive',
    'Upgrade-Insecure-Requests': '1',
    'Cache-Control': 'max-age=0'
}

def save_to_json(filename, data):
    """Сохранение данных в JSON файл"""
    with open(filename, 'w', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False, indent=2, default=str)
    print(f"Данные сохранены в файл {filename}")

def get_tinkoff_data():
    """Получение данных из Tinkoff Invest API"""
    print("\n=== Получение данных из Tinkoff API ===")
    
    with Client(TOKEN) as client:
        try:
            # Поиск инструмента
            instruments = client.instruments.find_instrument(query=TICKER)
            
            # Ищем точное совпадение по тикеру
            figi = None
            for instrument in instruments.instruments:
                if instrument.ticker.upper() == TICKER.upper():
                    figi = instrument.figi
                    instrument_info = {
                        'ticker': instrument.ticker,
                        'figi': instrument.figi,
                        'name': instrument.name,
                        'class_code': getattr(instrument, 'class_code', 'Н/Д'),
                        'lot': getattr(instrument, 'lot', 0),
                        'currency': getattr(instrument, 'currency', 'Н/Д'),
                        'exchange': getattr(instrument, 'exchange', 'Н/Д'),
                        'isin': getattr(instrument, 'isin', 'Н/Д')
                    }
                    break
            
            if not figi:
                print(f"Инструмент {TICKER} не найден в Tinkoff API")
                return None
            
            # Получаем последнюю цену
            last_prices = client.market_data.get_last_prices(figi=[figi])
            
            price_info = None
            if last_prices and last_prices.last_prices:
                price = last_prices.last_prices[0]
                price_value = float(price.price.units) + float(price.price.nano) / 1_000_000_000
                price_info = {
                    'price': price_value,
                    'time': price.time
                }
            
            result = {
                'source': 'Tinkoff',
                'timestamp': datetime.now().isoformat(),
                'instrument_info': instrument_info,
                'price_info': price_info
            }
            
            print(f"Данные из Tinkoff API успешно получены")
            return result
        
        except Exception as e:
            print(f"Ошибка при получении данных из Tinkoff API: {e}")
            return None

def get_moex_data():
    """Получение данных с Московской биржи"""
    print("\n=== Получение данных с Московской биржи ===")
    
    try:
        # Базовая информация о инструменте
        url = f"https://iss.moex.com/iss/engines/stock/markets/shares/securities/{TICKER}.json"
        response = requests.get(url)
        
        if response.status_code != 200:
            print(f"Ошибка при получении данных с МосБиржи: {response.status_code}")
            return None
        
        data = response.json()
        
        # Преобразуем данные
        security_info = {}
        market_data = {}
        
        if 'securities' in data and 'data' in data['securities'] and 'columns' in data['securities']:
            columns = data['securities']['columns']
            if data['securities']['data']:
                row = data['securities']['data'][0]
                security_info = dict(zip(columns, row))
        
        if 'marketdata' in data and 'data' in data['marketdata'] and 'columns' in data['marketdata']:
            columns = data['marketdata']['columns']
            if data['marketdata']['data']:
                row = data['marketdata']['data'][0]
                market_data = dict(zip(columns, row))
        
        result = {
            'source': 'MOEX',
            'timestamp': datetime.now().isoformat(),
            'security_info': security_info,
            'market_data': market_data
        }
        
        print(f"Данные с МосБиржи успешно получены")
        return result
    
    except Exception as e:
        print(f"Ошибка при получении данных с МосБиржи: {e}")
        return None

def get_smartlab_data():
    """Получение данных с Smart-lab.ru"""
    print("\n=== Получение данных со Smart-lab.ru ===")
    
    try:
        # Страница компании на Smart-lab
        url = f"https://smart-lab.ru/q/{TICKER}/"
        response = requests.get(url, headers=headers, timeout=10)
        
        if response.status_code != 200:
            print(f"Ошибка при получении данных со Smart-lab: {response.status_code}")
            return None
        
        soup = BeautifulSoup(response.text, 'html.parser')
        
        # Извлечение данных
        company_info = {}
        
        # Название компании
        company_name = soup.select_one('h1.head')
        if company_name:
            company_info['name'] = company_name.text.strip()
        
        # Основные показатели
        metrics_table = soup.select_one('table.simple-little-table')
        if metrics_table:
            rows = metrics_table.select('tr')
            for row in rows:
                cells = row.select('td')
                if len(cells) >= 2:
                    key = cells[0].text.strip().replace(':', '')
                    value = cells[1].text.strip()
                    company_info[key] = value
        
        # Информация о торгах
        trading_info = {}
        trading_div = soup.select_one('div.quotes-block')
        if trading_div:
            last_price = trading_div.select_one('big')
            if last_price:
                trading_info['last_price'] = last_price.text.strip()
            
            change = trading_div.select_one('span.price-change')
            if change:
                trading_info['change'] = change.text.strip()
        
        # Мультипликаторы и показатели
        multiples = {}
        multiples_table = soup.select('table.simple-little-table')
        if len(multiples_table) > 1:
            rows = multiples_table[1].select('tr')
            for row in rows:
                cells = row.select('td')
                if len(cells) >= 2:
                    key = cells[0].text.strip().replace(':', '')
                    value = cells[1].text.strip()
                    multiples[key] = value
        
        result = {
            'source': 'Smart-lab',
            'timestamp': datetime.now().isoformat(),
            'company_info': company_info,
            'trading_info': trading_info,
            'multiples': multiples
        }
        
        print(f"Данные со Smart-lab успешно получены")
        return result
    
    except Exception as e:
        print(f"Ошибка при получении данных со Smart-lab: {e}")
        return None

def get_finam_data():
    """Получение данных с Финам"""
    print("\n=== Получение данных с Финам ===")
    
    try:
        # Поиск идентификатора компании
        search_url = f"https://www.finam.ru/api/search/instruments/?query={TICKER}"
        response = requests.get(search_url, headers=headers, timeout=10)
        
        if response.status_code != 200:
            print(f"Ошибка при поиске идентификатора компании на Финам: {response.status_code}")
            return None
        
        search_data = response.json()
        company_id = None
        company_name = None
        
        if search_data.get('data', {}).get('items'):
            for item in search_data['data']['items']:
                if item.get('ticker') == TICKER:
                    company_id = item.get('id')
                    company_name = item.get('name')
                    break
        
        if not company_id:
            print(f"Компания {TICKER} не найдена на Финам")
            return None
        
        # Получение страницы компании
        url = f"https://www.finam.ru/profile/moex-akcii/{company_name}/{company_id}/"
        response = requests.get(url, headers=headers, timeout=10)
        
        if response.status_code != 200:
            print(f"Ошибка при получении данных о компании на Финам: {response.status_code}")
            return None
        
        soup = BeautifulSoup(response.text, 'html.parser')
        
        # Извлечение цены и изменения
        trading_info = {}
        price_container = soup.select_one('span.PriceInformation__price--26G')
        if price_container:
            trading_info['last_price'] = price_container.text.strip()
        
        change_container = soup.select_one('span.PriceInformation__change--2Gt')
        if change_container:
            trading_info['change'] = change_container.text.strip()
        
        # Дополнительная информация
        company_details = {}
        detail_items = soup.select('div.company-profile-widget__item')
        
        for item in detail_items:
            label = item.select_one('div.company-profile-widget__item-label')
            value = item.select_one('div.company-profile-widget__item-value')
            
            if label and value:
                key = label.text.strip().rstrip(':')
                company_details[key] = value.text.strip()
        
        result = {
            'source': 'Финам',
            'timestamp': datetime.now().isoformat(),
            'company_id': company_id,
            'company_name': company_name,
            'trading_info': trading_info,
            'company_details': company_details
        }
        
        print(f"Данные с Финам успешно получены")
        return result
    
    except Exception as e:
        print(f"Ошибка при получении данных с Финам: {e}")
        return None

def get_bcs_data():
    """Получение данных с БКС"""
    print("\n=== Получение данных с БКС ===")
    
    try:
        # Страница компании на БКС
        url = f"https://bcs.ru/catalog/shares/{TICKER}"
        response = requests.get(url, headers=headers, timeout=10)
        
        if response.status_code != 200:
            print(f"Ошибка при получении данных с БКС: {response.status_code}")
            return None
        
        soup = BeautifulSoup(response.text, 'html.parser')
        
        # Извлечение данных
        trading_info = {}
        
        # Цена и изменение
        price_container = soup.select_one('div.quotesListing__priceZone')
        if price_container:
            price = price_container.select_one('div.quotesListing__price')
            if price:
                trading_info['last_price'] = price.text.strip()
            
            change = price_container.select_one('div.quotesListing__change')
            if change:
                trading_info['change'] = change.text.strip()
        
        # Основная информация о компании
        company_info = {}
        info_items = soup.select('div.detailInfo__item')
        
        for item in info_items:
            label = item.select_one('div.detailInfo__label')
            value = item.select_one('div.detailInfo__value')
            
            if label and value:
                key = label.text.strip()
                company_info[key] = value.text.strip()
        
        result = {
            'source': 'БКС',
            'timestamp': datetime.now().isoformat(),
            'trading_info': trading_info,
            'company_info': company_info
        }
        
        print(f"Данные с БКС успешно получены")
        return result
    
    except Exception as e:
        print(f"Ошибка при получении данных с БКС: {e}")
        return None

def get_spb_exchange_data():
    """Получение данных с СПБ Биржи"""
    print("\n=== Получение данных с СПБ Биржи ===")
    
    try:
        # Поиск идентификатора инструмента
        search_url = f"https://spbexchange.ru/ru/market-data/search-results.aspx?search={TICKER}"
        response = requests.get(search_url, headers=headers, timeout=10)
        
        if response.status_code != 200:
            print(f"Ошибка при поиске на СПБ Бирже: {response.status_code}")
            return None
        
        soup = BeautifulSoup(response.text, 'html.parser')
        
        # Поиск ссылки на страницу инструмента
        instrument_link = None
        link_elements = soup.select('a')
        
        for link in link_elements:
            if link.text.strip() == TICKER:
                instrument_link = link.get('href')
                break
        
        if not instrument_link:
            print(f"Инструмент {TICKER} не найден на СПБ Бирже")
            return None
        
        # Получение страницы инструмента
        instrument_url = f"https://spbexchange.ru{instrument_link}"
        response = requests.get(instrument_url, headers=headers, timeout=10)
        
        if response.status_code != 200:
            print(f"Ошибка при получении данных инструмента на СПБ Бирже: {response.status_code}")
            return None
        
        soup = BeautifulSoup(response.text, 'html.parser')
        
        # Извлечение данных
        instrument_info = {}
        
        # Название и тикер
        instrument_name = soup.select_one('h1.spc-mainheading')
        if instrument_name:
            instrument_info['name'] = instrument_name.text.strip()
        
        # Данные о торгах
        trading_info = {}
        price_element = soup.select_one('div.price')
        if price_element:
            trading_info['last_price'] = price_element.text.strip()
        
        # Дополнительная информация
        additional_info = {}
        info_elements = soup.select('dl.info_dl')
        
        for element in info_elements:
            terms = element.select('dt')
            values = element.select('dd')
            
            for i in range(min(len(terms), len(values))):
                key = terms[i].text.strip()
                value = values[i].text.strip()
                additional_info[key] = value
        
        result = {
            'source': 'СПБ Биржа',
            'timestamp': datetime.now().isoformat(),
            'instrument_info': instrument_info,
            'trading_info': trading_info,
            'additional_info': additional_info
        }
        
        print(f"Данные с СПБ Биржи успешно получены")
        return result
    
    except Exception as e:
        print(f"Ошибка при получении данных с СПБ Биржи: {e}")
        return None

def get_conomy_data():
    """Получение данных с Conomy.ru"""
    print("\n=== Получение данных с Conomy.ru ===")
    
    try:
        # Страница компании на Conomy.ru
        url = f"https://www.conomy.ru/search/companies/by-ticker/{TICKER}"
        response = requests.get(url, headers=headers, timeout=10)
        
        if response.status_code != 200:
            print(f"Ошибка при получении данных с Conomy.ru: {response.status_code}")
            return None
        
        soup = BeautifulSoup(response.text, 'html.parser')
        
        # Извлечение данных
        company_info = {}
        
        # Название компании
        company_name = soup.select_one('h1.head_title')
        if company_name:
            company_info['name'] = company_name.text.strip()
        
        # Финансовые показатели
        financial_data = {}
        fin_blocks = soup.select('div.fin_block')
        
        for block in fin_blocks:
            title = block.select_one('div.title')
            value = block.select_one('div.value')
            
            if title and value:
                key = title.text.strip()
                financial_data[key] = value.text.strip()
        
        # Мультипликаторы
        multiples = {}
        multiple_blocks = soup.select('div.multiple_block')
        
        for block in multiple_blocks:
            title = block.select_one('div.title')
            value = block.select_one('div.value')
            
            if title and value:
                key = title.text.strip()
                multiples[key] = value.text.strip()
        
        result = {
            'source': 'Conomy.ru',
            'timestamp': datetime.now().isoformat(),
            'company_info': company_info,
            'financial_data': financial_data,
            'multiples': multiples
        }
        
        print(f"Данные с Conomy.ru успешно получены")
        return result
    
    except Exception as e:
        print(f"Ошибка при получении данных с Conomy.ru: {e}")
        return None

def get_cbr_data():
    """Получение данных с сайта ЦБ РФ"""
    print("\n=== Получение данных с ЦБ РФ ===")
    
    try:
        # Поиск на сайте ЦБ
        search_url = f"https://www.cbr.ru/search/?text={TICKER}"
        response = requests.get(search_url, headers=headers, timeout=10)
        
        if response.status_code != 200:
            print(f"Ошибка при поиске на сайте ЦБ РФ: {response.status_code}")
            return None
        
        soup = BeautifulSoup(response.text, 'html.parser')
        
        # Извлекаем результаты поиска
        search_results = []
        results = soup.select('div.search-results__item')
        
        for result in results:
            title = result.select_one('a.search-results__link')
            snippet = result.select_one('div.search-results__text')
            
            if title and title.get('href'):
                item = {
                    'title': title.text.strip(),
                    'url': f"https://www.cbr.ru{title.get('href')}",
                    'snippet': snippet.text.strip() if snippet else None
                }
                search_results.append(item)
        
        result = {
            'source': 'ЦБ РФ',
            'timestamp': datetime.now().isoformat(),
            'search_results': search_results
        }
        
        print(f"Данные с ЦБ РФ успешно получены")
        return result
    
    except Exception as e:
        print(f"Ошибка при получении данных с ЦБ РФ: {e}")
        return None

def get_investfunds_data():
    """Получение данных с Investfunds.ru"""
    print("\n=== Получение данных с Investfunds.ru ===")
    
    try:
        # Поиск компании
        search_url = f"https://investfunds.ru/search/?query={TICKER}"
        response = requests.get(search_url, headers=headers, timeout=10)
        
        if response.status_code != 200:
            print(f"Ошибка при поиске на Investfunds.ru: {response.status_code}")
            return None
        
        soup = BeautifulSoup(response.text, 'html.parser')
        
        # Поиск ссылки на страницу с данными
        stock_link = None
        search_results = soup.select('div.search_res_block')
        
        for result in search_results:
            title = result.select_one('a')
            if title and TICKER.lower() in title.text.lower():
                stock_link = title.get('href')
                break
        
        if not stock_link:
            print(f"Компания {TICKER} не найдена на Investfunds.ru")
            return None
        
        # Получение страницы с данными
        stock_url = f"https://investfunds.ru{stock_link}"
        response = requests.get(stock_url, headers=headers, timeout=10)
        
        if response.status_code != 200:
            print(f"Ошибка при получении данных с Investfunds.ru: {response.status_code}")
            return None
        
        soup = BeautifulSoup(response.text, 'html.parser')
        
        # Извлечение данных
        company_info = {}
        
        # Название компании
        company_name = soup.select_one('h1')
        if company_name:
            company_info['name'] = company_name.text.strip()
        
        # Данные о цене
        price_info = {}
        price_block = soup.select_one('div.if_qarea')
        
        if price_block:
            price = price_block.select_one('span.if_curr_quote')
            if price:
                price_info['last_price'] = price.text.strip()
            
            change = price_block.select_one('span.if_quote_delta')
            if change:
                price_info['change'] = change.text.strip()
        
        # Дополнительная информация
        additional_info = {}
        info_rows = soup.select('table.if_data_table tr')
        
        for row in info_rows:
            cells = row.select('td')
            if len(cells) >= 2:
                key = cells[0].text.strip()
                value = cells[1].text.strip()
                additional_info[key] = value
        
        result = {
            'source': 'Investfunds.ru',
            'timestamp': datetime.now().isoformat(),
            'company_info': company_info,
            'price_info': price_info,
            'additional_info': additional_info
        }
        
        print(f"Данные с Investfunds.ru успешно получены")
        return result
    
    except Exception as e:
        print(f"Ошибка при получении данных с Investfunds.ru: {e}")
        return None

def get_quorom_data():
    """Получение данных с Quoram.ru"""
    print("\n=== Получение данных с Quoram.ru ===")
    
    try:
        # Страница с данными о дивидендах
        url = f"https://www.quorum.guru/stocks/{TICKER}/dividends/"
        response = requests.get(url, headers=headers, timeout=10)
        
        if response.status_code != 200:
            print(f"Ошибка при получении данных с Quoram.ru: {response.status_code}")
            return None
        
        soup = BeautifulSoup(response.text, 'html.parser')
        
        # Извлечение данных
        company_info = {}
        
        # Название компании
        company_name = soup.select_one('h1.stock-header__title')
        if company_name:
            company_info['name'] = company_name.text.strip()
        
        # Данные о цене
        price_info = {}
        price_block = soup.select_one('div.stock-header__price')
        
        if price_block:
            price = price_block.select_one('span.price__value')
            if price:
                price_info['last_price'] = price.text.strip()
            
            change = price_block.select_one('span.price__percent')
            if change:
                price_info['change'] = change.text.strip()
        
        # Данные о дивидендах
        dividend_info = []
        dividend_rows = soup.select('table.table tr')
        
        for row in dividend_rows[1:]:  # Пропускаем заголовок
            cells = row.select('td')
            if len(cells) >= 5:
                dividend = {
                    'period': cells[0].text.strip(),
                    'dividend': cells[1].text.strip(),
                    'record_date': cells[2].text.strip(),
                    'payment_date': cells[3].text.strip(),
                    'yield': cells[4].text.strip()
                }
                dividend_info.append(dividend)
        
        result = {
            'source': 'Quoram.ru',
            'timestamp': datetime.now().isoformat(),
            'company_info': company_info,
            'price_info': price_info,
            'dividend_info': dividend_info
        }
        
        print(f"Данные с Quoram.ru успешно получены")
        return result
    
    except Exception as e:
        print(f"Ошибка при получении данных с Quoram.ru: {e}")
        return None

def get_tradingview_data():
    """Получение данных с TradingView"""
    print("\n=== Получение данных с TradingView ===")
    
    try:
        # Поиск тикера на TradingView
        moex_ticker = f"MOEX:{TICKER}"
        us_ticker = f"NASDAQ:{TICKER}"
        
        # Пробуем сначала российский рынок, затем американский
        tickers_to_try = [moex_ticker, us_ticker]
        
        for ticker_symbol in tickers_to_try:
            # Страница с информацией о компании
            url = f"https://ru.tradingview.com/symbols/{ticker_symbol}/"
            response = requests.get(url, headers=headers, timeout=15)
            
            if response.status_code == 200:
                soup = BeautifulSoup(response.text, 'html.parser')
                
                # Извлечение данных
                stock_data = {}
                
                # Название компании и тикер
                title = soup.select_one('h1.tv-symbol-header__first-line')
                if title:
                    stock_data['name'] = title.text.strip()
                
                # Цена и изменение
                price_info = {}
                price_element = soup.select_one('div.tv-symbol-price-quote__value')
                if price_element:
                    price_info['last_price'] = price_element.text.strip()
                
                change_element = soup.select_one('div.tv-symbol-price-quote__change')
                if change_element:
                    price_info['change'] = change_element.text.strip()
                
                # Данные из боковой панели (Overview, Performance, etc.)
                overview_data = {}
                technicals_data = {}
                
                # Извлечение данных из виджетов
                widgets = soup.select('div.tv-widget-fundamentals')
                for widget in widgets:
                    widget_title = widget.select_one('div.tv-widget-fundamentals__title')
                    widget_type = widget_title.text.strip() if widget_title else "Unknown"
                    
                    rows = widget.select('tr.tv-widget-fundamentals__row')
                    for row in rows:
                        cells = row.select('td')
                        if len(cells) >= 2:
                            key = cells[0].text.strip()
                            value = cells[1].text.strip()
                            
                            if widget_type.lower() == 'обзор':
                                overview_data[key] = value
                            elif widget_type.lower() == 'технические показатели':
                                technicals_data[key] = value
                
                result = {
                    'source': 'TradingView',
                    'timestamp': datetime.now().isoformat(),
                    'ticker_symbol': ticker_symbol,
                    'name': stock_data.get('name'),
                    'price_info': price_info,
                    'overview': overview_data,
                    'technicals': technicals_data
                }
                
                print(f"Данные с TradingView успешно получены для {ticker_symbol}")
                return result
        
        print(f"Акция {TICKER} не найдена на TradingView")
        return None
    
    except Exception as e:
        print(f"Ошибка при получении данных с TradingView: {e}")
        return None

def get_investing_com_data():
    """Получение данных с Investing.com"""
    print("\n=== Получение данных с Investing.com ===")
    
    # Расширенные заголовки для Investing.com
    investing_headers = headers.copy()
    investing_headers.update({
        'Host': 'ru.investing.com',
        'Referer': 'https://ru.investing.com/',
        'X-Requested-With': 'XMLHttpRequest'
    })
    
    try:
        # Поиск инструмента на Investing.com
        search_url = f"https://ru.investing.com/search/?q={TICKER}"
        response = requests.get(search_url, headers=investing_headers, timeout=15)
        
        if response.status_code != 200:
            print(f"Ошибка при поиске на Investing.com: {response.status_code}")
            return None
        
        soup = BeautifulSoup(response.text, 'html.parser')
        
        # Поиск ссылки на страницу акции
        stock_link = None
        search_results = soup.select('a.js-inner-all-results-quote-item')
        
        for link in search_results:
            if 'акции' in link.text.lower() and TICKER.lower() in link.text.lower():
                stock_link = link.get('href')
                break
        
        if not stock_link:
            print(f"Акция {TICKER} не найдена на Investing.com")
            return None
        
        # Получение страницы с данными
        stock_url = f"https://ru.investing.com{stock_link}"
        response = requests.get(stock_url, headers=investing_headers, timeout=15)
        
        if response.status_code != 200:
            print(f"Ошибка при получении данных с Investing.com: {response.status_code}")
            return None
        
        soup = BeautifulSoup(response.text, 'html.parser')
        
        # Извлечение данных
        stock_data = {}
        
        # Название компании
        name_element = soup.select_one('h1.text-2xl')
        if name_element:
            stock_data['name'] = name_element.text.strip()
        
        # Цена и изменение
        price_info = {}
        last_price = soup.select_one('div.instrument-price_instrument-price__3uw25 span')
        if last_price:
            price_info['last_price'] = last_price.text.strip()
        
        change_elements = soup.select('span.instrument-price_change-value__3GgCt, span.instrument-price_change-percent__19cas')
        if len(change_elements) >= 2:
            price_info['change'] = change_elements[0].text.strip()
            price_info['change_percent'] = change_elements[1].text.strip()
        
        # Данные о компании
        company_info = {}
        info_rows = soup.select('div.flex.justify-between.border-b.py-2')
        
        for row in info_rows:
            label = row.select_one('span:first-child')
            value = row.select_one('span.font-bold')
            
            if label and value:
                key = label.text.strip().rstrip(':')
                company_info[key] = value.text.strip()
        
        # Технические показатели
        technical_data = {}
        technical_section = soup.select_one('div#technical')
        
        if technical_section:
            tech_rows = technical_section.select('tr')
            for row in tech_rows:
                cells = row.select('td')
                if len(cells) >= 2:
                    key = cells[0].text.strip()
                    value = cells[1].text.strip()
                    technical_data[key] = value
        
        result = {
            'source': 'Investing.com',
            'timestamp': datetime.now().isoformat(),
            'name': stock_data.get('name'),
            'price_info': price_info,
            'company_info': company_info,
            'technical_data': technical_data,
            'url': stock_url
        }
        
        print(f"Данные с Investing.com успешно получены")
        return result
    
    except Exception as e:
        print(f"Ошибка при получении данных с Investing.com: {e}")
        return None

def get_marketwatch_data():
    """Получение данных с MarketWatch"""
    print("\n=== Получение данных с MarketWatch ===")
    
    try:
        # Страница компании на MarketWatch
        url = f"https://www.marketwatch.com/investing/stock/{TICKER.lower()}"
        response = requests.get(url, headers=headers, timeout=15)
        
        if response.status_code != 200:
            # Пробуем искать на российском рынке
            url = f"https://www.marketwatch.com/investing/stock/{TICKER.lower()}?countrycode=ru"
            response = requests.get(url, headers=headers, timeout=15)
            
            if response.status_code != 200:
                print(f"Ошибка при получении данных с MarketWatch: {response.status_code}")
                return None
        
        soup = BeautifulSoup(response.text, 'html.parser')
        
        # Извлечение данных
        stock_data = {}
        
        # Название компании
        company_name = soup.select_one('h1.company__name')
        if company_name:
            stock_data['name'] = company_name.text.strip()
        
        # Цена и изменение
        price_info = {}
        price_element = soup.select_one('bg-quote.value')
        if price_element:
            price_info['last_price'] = price_element.text.strip()
        
        change_element = soup.select_one('bg-quote.change--percent--q')
        if change_element:
            price_info['change_percent'] = change_element.text.strip()
        
        # Основные показатели
        key_metrics = {}
        metrics_section = soup.select('div.element.element--list.key-stats li')
        
        for metric in metrics_section:
            label = metric.select_one('small')
            value = metric.select_one('span.primary')
            
            if label and value:
                key = label.text.strip()
                key_metrics[key] = value.text.strip()
        
        # Финансовые показатели из таблицы
        financial_data = {}
        financial_tables = soup.select('table.table.table--primary.align--right')
        
        for table in financial_tables:
            table_title = table.select_one('caption')
            table_type = table_title.text.strip() if table_title else "Unknown"
            
            rows = table.select('tr')
            table_data = {}
            
            for row in rows:
                cells = row.select('td, th')
                if len(cells) >= 2:
                    key = cells[0].text.strip()
                    value = cells[1].text.strip()
                    table_data[key] = value
            
            financial_data[table_type] = table_data
        
        result = {
            'source': 'MarketWatch',
            'timestamp': datetime.now().isoformat(),
            'name': stock_data.get('name'),
            'price_info': price_info,
            'key_metrics': key_metrics,
            'financial_data': financial_data,
            'url': url
        }
        
        print(f"Данные с MarketWatch успешно получены")
        return result
    
    except Exception as e:
        print(f"Ошибка при получении данных с MarketWatch: {e}")
        return None

def get_yahoo_finance_data():
    """Получение данных с Yahoo Finance"""
    print("\n=== Получение данных с Yahoo Finance ===")
    
    try:
        # Страница компании на Yahoo Finance
        url = f"https://finance.yahoo.com/quote/{TICKER}"
        response = requests.get(url, headers=headers, timeout=15)
        
        if response.status_code != 200:
            print(f"Ошибка при получении данных с Yahoo Finance: {response.status_code}")
            return None
        
        soup = BeautifulSoup(response.text, 'html.parser')
        
        # Извлечение данных
        stock_data = {}
        
        # Название компании
        company_name = soup.select_one('h1')
        if company_name:
            stock_data['name'] = company_name.text.strip()
        
        # Цена и изменение
        price_info = {}
        price_element = soup.select_one('fin-streamer[data-test="qsp-price"]')
        if price_element:
            price_info['last_price'] = price_element.text.strip()
        
        change_elements = soup.select('fin-streamer[data-test="qsp-price-change"]')
        if change_elements:
            price_info['change'] = change_elements[0].text.strip()
        
        change_percent_element = soup.select_one('fin-streamer[data-test="qsp-price-change"] span')
        if change_percent_element:
            price_info['change_percent'] = change_percent_element.text.strip().strip('()')
        
        # Основные показатели из правой колонки
        key_statistics = {}
        stats_rows = soup.select('div[data-test="right-summary-table"] tr')
        
        for row in stats_rows:
            cells = row.select('td')
            if len(cells) >= 2:
                key = cells[0].text.strip()
                value = cells[1].text.strip()
                key_statistics[key] = value
        
        # Дополнительные показатели
        additional_info = {}
        modules = soup.select('div[data-test="qsp-statistics"] tr')
        
        for module in modules:
            cells = module.select('td')
            if len(cells) >= 2:
                key = cells[0].text.strip()
                value = cells[1].text.strip()
                additional_info[key] = value
        
        result = {
            'source': 'Yahoo Finance',
            'timestamp': datetime.now().isoformat(),
            'name': stock_data.get('name'),
            'price_info': price_info,
            'key_statistics': key_statistics,
            'additional_info': additional_info,
            'url': url
        }
        
        print(f"Данные с Yahoo Finance успешно получены")
        return result
    
    except Exception as e:
        print(f"Ошибка при получении данных с Yahoo Finance: {e}")
        return None

def main():
    """Сбор данных об акции OZON из разных источников"""
    print(f"Начинаем сбор данных о компании {TICKER} из различных источников...")
    
    all_sources_data = {
        'ticker': TICKER,
        'timestamp': datetime.now().isoformat(),
        'sources': {}
    }
    
    # Получение данных из разных источников
    sources = [
        ('tinkoff', get_tinkoff_data),
        ('moex', get_moex_data),
        ('smartlab', get_smartlab_data),
        ('finam', get_finam_data),
        ('bcs', get_bcs_data),
        ('spb_exchange', get_spb_exchange_data),
        ('conomy', get_conomy_data),
        ('cbr', get_cbr_data),
        ('investfunds', get_investfunds_data),
        ('quorom', get_quorom_data),
        ('tradingview', get_tradingview_data),
        ('investing_com', get_investing_com_data),
        ('marketwatch', get_marketwatch_data),
        ('yahoo_finance', get_yahoo_finance_data)
    ]
    
    for source_name, get_data_func in sources:
        try:
            # Делаем паузу между запросами, чтобы не перегружать сервера
            time.sleep(1)
            data = get_data_func()
            if data:
                all_sources_data['sources'][source_name] = data
        except Exception as e:
            print(f"Ошибка при получении данных из источника {source_name}: {e}")
    
    # Сохраняем все данные в один JSON файл
    output_file = f"{TICKER}_all_sources_data.json"
    save_to_json(output_file, all_sources_data)
    
    # Сводка о результатах
    sources_count = len(all_sources_data['sources'])
    print(f"\n=== Сводка ===")
    print(f"Удалось получить данные из {sources_count} из {len(sources)} источников.")
    for source_name in all_sources_data['sources'].keys():
        print(f"- {source_name}")
    
    print(f"\nВсе данные сохранены в файл {output_file}")

if __name__ == "__main__":
    main()
    print("Работа скрипта завершена.") 