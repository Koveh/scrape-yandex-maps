import requests
from bs4 import BeautifulSoup
import json
import pandas as pd
from datetime import datetime

def get_rbc_profile():
    """Получение профиля компании OZON с сайта РБК"""
    
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
    }
    
    # URL страницы профиля OZON на РБК
    url = "https://quote.rbc.ru/company/169751"
    
    try:
        response = requests.get(url, headers=headers)
        if response.status_code != 200:
            print(f"Ошибка при получении данных: {response.status_code}")
            return None
        
        soup = BeautifulSoup(response.text, 'html.parser')
        
        # Парсинг основной информации
        company_info = {}
        
        # Название компании
        name_elem = soup.select_one('h1.company-profile__title')
        if name_elem:
            company_info['name'] = name_elem.text.strip()
        
        # Блок с детальной информацией
        info_blocks = soup.select('.company-profile__info-block')
        for block in info_blocks:
            # Названия полей и их значения
            field_names = [item.text.strip() for item in block.select('.company-profile__info-block-title')]
            field_values = [item.text.strip() for item in block.select('.company-profile__info-block-value')]
            
            # Соединяем названия и значения
            for i in range(min(len(field_names), len(field_values))):
                company_info[field_names[i]] = field_values[i]
        
        # Ключевые показатели
        key_metrics = {}
        metrics_blocks = soup.select('.company-profile__column')
        for block in metrics_blocks:
            title_elem = block.select_one('.company-profile__column-title')
            value_elem = block.select_one('.company-profile__column-value')
            if title_elem and value_elem:
                key_metrics[title_elem.text.strip()] = value_elem.text.strip()
        
        if key_metrics:
            company_info['key_metrics'] = key_metrics
        
        # Описание компании
        descr_elem = soup.select_one('.company-profile__description')
        if descr_elem:
            company_info['description'] = descr_elem.text.strip()
        
        return company_info
        
    except Exception as e:
        print(f"Ошибка при получении данных с РБК: {e}")
        return None

def get_rbc_quotes():
    """Получение котировок акций OZON с сайта РБК"""
    
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
    }
    
    # URL страницы котировок OZON на РБК
    url = "https://quote.rbc.ru/ticker/169751"
    
    try:
        response = requests.get(url, headers=headers)
        if response.status_code != 200:
            print(f"Ошибка при получении котировок: {response.status_code}")
            return None
        
        soup = BeautifulSoup(response.text, 'html.parser')
        
        # Данные о котировках
        quotes_info = {}
        
        # Текущая цена
        price_elem = soup.select_one('.chart__info__sum')
        if price_elem:
            quotes_info['current_price'] = price_elem.text.strip()
        
        # Изменение цены
        change_elem = soup.select_one('.chart__info__change')
        if change_elem:
            quotes_info['price_change'] = change_elem.text.strip()
        
        # Время обновления
        time_elem = soup.select_one('.chart__info__update')
        if time_elem:
            quotes_info['update_time'] = time_elem.text.strip()
        
        # Дополнительная информация о котировках
        quote_items = soup.select('.quotes-info__item')
        for item in quote_items:
            label_elem = item.select_one('.quotes-info__item__label')
            value_elem = item.select_one('.quotes-info__item__value')
            if label_elem and value_elem:
                quotes_info[label_elem.text.strip()] = value_elem.text.strip()
        
        return quotes_info
        
    except Exception as e:
        print(f"Ошибка при получении котировок с РБК: {e}")
        return None

def get_rbc_news():
    """Получение новостей о OZON с сайта РБК"""
    
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
    }
    
    # URL страницы новостей OZON на РБК
    url = "https://quote.rbc.ru/company/169751/news"
    
    try:
        response = requests.get(url, headers=headers)
        if response.status_code != 200:
            print(f"Ошибка при получении новостей: {response.status_code}")
            return None
        
        soup = BeautifulSoup(response.text, 'html.parser')
        
        # Сбор новостей
        news_items = []
        
        # Новостные блоки
        news_blocks = soup.select('.news-feed__item')
        for block in news_blocks:
            news_item = {}
            
            # Заголовок и ссылка
            title_elem = block.select_one('.news-feed__item__title a')
            if title_elem:
                news_item['title'] = title_elem.text.strip()
                news_item['url'] = title_elem['href'] if title_elem.has_attr('href') else None
            
            # Дата публикации
            date_elem = block.select_one('.news-feed__item__date')
            if date_elem:
                news_item['date'] = date_elem.text.strip()
            
            # Теги
            tags_elems = block.select('.news-feed__item__tag a')
            if tags_elems:
                news_item['tags'] = [tag.text.strip() for tag in tags_elems]
            
            news_items.append(news_item)
        
        return news_items
        
    except Exception as e:
        print(f"Ошибка при получении новостей с РБК: {e}")
        return None

def main():
    """Получение информации о компании OZON с сайта РБК"""
    
    print("Получение информации о компании OZON с сайта РБК...")
    
    # Получаем профиль компании
    print("Получение профиля компании...")
    company_profile = get_rbc_profile()
    
    # Получаем котировки
    print("Получение котировок...")
    quotes = get_rbc_quotes()
    
    # Получаем новости
    print("Получение новостей...")
    news = get_rbc_news()
    
    # Объединяем все данные
    rbc_data = {
        'profile': company_profile,
        'quotes': quotes,
        'news': news,
        'timestamp': datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    }
    
    # Сохраняем информацию в JSON-файл
    output_file = "OZON_rbc_info.json"
    with open(output_file, 'w', encoding='utf-8') as f:
        json.dump(rbc_data, f, ensure_ascii=False, indent=2)
    
    print(f"Информация о компании OZON с сайта РБК сохранена в файл {output_file}")
    
    # Выводим краткую информацию
    print("\nКраткая информация о компании OZON:")
    
    if company_profile:
        print(f"Название: {company_profile.get('name', 'Н/Д')}")
        print(f"Описание: {company_profile.get('description', 'Н/Д')[:150]}..." if company_profile.get('description') else "Описание: Н/Д")
    
    if quotes:
        print(f"\nТекущая цена: {quotes.get('current_price', 'Н/Д')}")
        print(f"Изменение: {quotes.get('price_change', 'Н/Д')}")
        print(f"Обновлено: {quotes.get('update_time', 'Н/Д')}")
    
    if news:
        print("\nПоследние новости:")
        for i, item in enumerate(news[:3], 1):
            print(f"{i}. {item.get('title', 'Н/Д')} ({item.get('date', 'Н/Д')})")

if __name__ == "__main__":
    main() 