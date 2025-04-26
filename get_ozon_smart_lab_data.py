import requests
import json
import pandas as pd
from bs4 import BeautifulSoup
from datetime import datetime

# Константы
TICKER = "OZON"
OUTPUT_FILE = f"{TICKER}_smart_lab_data.json"

def get_smart_lab_company_page():
    """Получение страницы компании с Smart-Lab"""
    print("\n=== Получение данных с Smart-Lab ===")
    
    # Smart-Lab может использовать другие идентификаторы для тикеров
    # Для OZON используем прямой URL
    url = f"https://smart-lab.ru/q/{TICKER}/"
    
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
    }
    
    try:
        response = requests.get(url, headers=headers)
        if response.status_code == 200:
            return response.text
        else:
            print(f"Ошибка при получении данных: {response.status_code}")
            return None
    except Exception as e:
        print(f"Ошибка при получении данных со Smart-Lab: {e}")
        return None

def extract_company_info(html):
    """Извлечение основной информации о компании из HTML"""
    if not html:
        return None
    
    try:
        soup = BeautifulSoup(html, 'html.parser')
        company_info = {}
        
        # Название компании
        title = soup.select_one('h1.t-h1')
        if title:
            company_info['name'] = title.text.strip()
        
        # Основные показатели
        info_blocks = soup.select('.quote-info .quote_info_cap1')
        for block in info_blocks:
            label = block.select_one('.quote-info-caption')
            value = block.select_one('.quote-info-value')
            
            if label and value:
                label_text = label.text.strip()
                value_text = value.text.strip()
                company_info[label_text] = value_text
        
        return company_info
    except Exception as e:
        print(f"Ошибка при извлечении информации о компании: {e}")
        return None

def extract_financial_indicators(html):
    """Извлечение финансовых показателей из HTML"""
    if not html:
        return None
    
    try:
        soup = BeautifulSoup(html, 'html.parser')
        financial_data = {}
        
        # Поиск таблицы с финансовыми показателями
        tables = soup.select('.simple-little-table')
        
        for table in tables:
            # Определяем тип таблицы по заголовку
            header = table.select_one('thead tr')
            if not header:
                continue
            
            header_text = header.text.strip()
            if 'Финансовые показатели' in header_text:
                # Извлекаем данные из таблицы
                rows = table.select('tbody tr')
                table_data = []
                
                for row in rows:
                    cols = row.select('td')
                    if not cols:
                        continue
                    
                    row_data = {}
                    for i, col in enumerate(cols):
                        header_cols = header.select('th')
                        if i < len(header_cols):
                            header_col_text = header_cols[i].text.strip()
                            row_data[header_col_text] = col.text.strip()
                    
                    table_data.append(row_data)
                
                financial_data['financial_indicators'] = table_data
        
        return financial_data
    except Exception as e:
        print(f"Ошибка при извлечении финансовых показателей: {e}")
        return None

def extract_technical_indicators(html):
    """Извлечение технических показателей из HTML"""
    if not html:
        return None
    
    try:
        soup = BeautifulSoup(html, 'html.parser')
        technical_data = {}
        
        # Поиск блока с техническими индикаторами
        tech_block = soup.select_one('.technical-indicators-block')
        if tech_block:
            indicators = tech_block.select('.indicator')
            indicator_data = {}
            
            for indicator in indicators:
                name = indicator.select_one('.name')
                value = indicator.select_one('.value')
                
                if name and value:
                    indicator_data[name.text.strip()] = value.text.strip()
            
            technical_data['technical_indicators'] = indicator_data
        
        return technical_data
    except Exception as e:
        print(f"Ошибка при извлечении технических показателей: {e}")
        return None

def extract_news(html):
    """Извлечение новостей из HTML"""
    if not html:
        return None
    
    try:
        soup = BeautifulSoup(html, 'html.parser')
        news_data = []
        
        # Поиск блока с новостями
        news_block = soup.select_one('.company-news')
        if news_block:
            news_items = news_block.select('.news-item')
            
            for item in news_items:
                news_item = {}
                
                title = item.select_one('.news-title a')
                if title:
                    news_item['title'] = title.text.strip()
                    news_item['url'] = title.get('href', '')
                
                date = item.select_one('.news-date')
                if date:
                    news_item['date'] = date.text.strip()
                
                snippet = item.select_one('.news-snippet')
                if snippet:
                    news_item['snippet'] = snippet.text.strip()
                
                news_data.append(news_item)
        
        return {'news': news_data}
    except Exception as e:
        print(f"Ошибка при извлечении новостей: {e}")
        return None

def extract_recommendations(html):
    """Извлечение рекомендаций аналитиков из HTML"""
    if not html:
        return None
    
    try:
        soup = BeautifulSoup(html, 'html.parser')
        recommendations_data = []
        
        # Поиск таблицы с рекомендациями аналитиков
        recommendations_table = None
        tables = soup.select('.simple-little-table')
        
        for table in tables:
            header = table.select_one('thead tr')
            if not header:
                continue
            
            header_text = header.text.strip()
            if 'Рекомендации аналитиков' in header_text:
                recommendations_table = table
                break
        
        if recommendations_table:
            rows = recommendations_table.select('tbody tr')
            
            for row in rows:
                cols = row.select('td')
                if not cols or len(cols) < 4:
                    continue
                
                rec_data = {
                    'date': cols[0].text.strip(),
                    'analyst': cols[1].text.strip(),
                    'recommendation': cols[2].text.strip(),
                    'target_price': cols[3].text.strip()
                }
                
                recommendations_data.append(rec_data)
        
        return {'analyst_recommendations': recommendations_data}
    except Exception as e:
        print(f"Ошибка при извлечении рекомендаций аналитиков: {e}")
        return None

def extract_dividend_info(html):
    """Извлечение информации о дивидендах из HTML"""
    if not html:
        return None
    
    try:
        soup = BeautifulSoup(html, 'html.parser')
        dividend_data = []
        
        # Поиск таблицы с дивидендами
        dividend_table = None
        tables = soup.select('.simple-little-table')
        
        for table in tables:
            header = table.select_one('thead tr')
            if not header:
                continue
            
            header_text = header.text.strip()
            if 'Дивиденды' in header_text:
                dividend_table = table
                break
        
        if dividend_table:
            rows = dividend_table.select('tbody tr')
            
            for row in rows:
                cols = row.select('td')
                if not cols or len(cols) < 4:
                    continue
                
                div_data = {
                    'year': cols[0].text.strip(),
                    'period': cols[1].text.strip(),
                    'amount': cols[2].text.strip(),
                    'yield': cols[3].text.strip()
                }
                
                # Если есть дополнительные столбцы с датами
                if len(cols) > 4:
                    div_data['record_date'] = cols[4].text.strip()
                
                if len(cols) > 5:
                    div_data['ex_dividend_date'] = cols[5].text.strip()
                
                dividend_data.append(div_data)
        
        return {'dividends': dividend_data}
    except Exception as e:
        print(f"Ошибка при извлечении информации о дивидендах: {e}")
        return None

def save_to_json(data):
    """Сохранение данных в JSON файл"""
    with open(OUTPUT_FILE, 'w', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
    print(f"Данные сохранены в файл {OUTPUT_FILE}")

def main():
    """Основная функция для сбора всех данных"""
    print(f"Начинаем сбор данных о компании {TICKER} с Smart-Lab")
    
    # Получаем HTML страницу
    html = get_smart_lab_company_page()
    
    if not html:
        print("Не удалось получить данные с Smart-Lab")
        return
    
    # Инициализируем словарь для всех данных
    all_data = {
        'timestamp': datetime.now().isoformat(),
        'ticker': TICKER
    }
    
    # Извлекаем данные из HTML
    company_info = extract_company_info(html)
    if company_info:
        all_data['company_info'] = company_info
        print("Получена основная информация о компании")
    
    financial_data = extract_financial_indicators(html)
    if financial_data:
        all_data.update(financial_data)
        print("Получены финансовые показатели")
    
    technical_data = extract_technical_indicators(html)
    if technical_data:
        all_data.update(technical_data)
        print("Получены технические индикаторы")
    
    news_data = extract_news(html)
    if news_data:
        all_data.update(news_data)
        print("Получены новости")
    
    recommendations_data = extract_recommendations(html)
    if recommendations_data:
        all_data.update(recommendations_data)
        print("Получены рекомендации аналитиков")
    
    dividend_data = extract_dividend_info(html)
    if dividend_data:
        all_data.update(dividend_data)
        print("Получена информация о дивидендах")
    
    # Сохраняем все данные
    save_to_json(all_data)
    
    print(f"Сбор данных о компании {TICKER} с Smart-Lab завершен")

if __name__ == "__main__":
    main() 