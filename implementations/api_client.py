import os
import json
import time
import logging
from abc import ABC, abstractmethod
from datetime import datetime, timedelta
import requests
from tinkoff.invest import Client, InstrumentIdType, HistoricCandle, CandleInterval
from dotenv import load_dotenv

# Настройка логирования
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger("api_client")

# Загрузка переменных окружения
load_dotenv()


class StockApiClient(ABC):
    """Абстрактный базовый класс для работы с API акций"""
    
    def __init__(self, ticker):
        self.ticker = ticker
        
    @abstractmethod
    def get_current_price(self):
        """Получение текущей цены акции"""
        pass
    
    @abstractmethod
    def get_daily_data(self, days=30):
        """Получение исторических данных за указанное количество дней"""
        pass
    
    @abstractmethod
    def get_instrument_info(self):
        """Получение информации об инструменте"""
        pass


class TinkoffApiClient(StockApiClient):
    """Клиент для работы с Tinkoff Invest API"""
    
    def __init__(self, ticker):
        super().__init__(ticker)
        self.token = os.getenv("TINKOFF_INVEST_TOKEN")
        if not self.token:
            raise ValueError("TINKOFF_INVEST_TOKEN not set")
        
        # Кэшированные данные
        self._figi = None
        self._instrument_info = None
        
    def _format_money(self, money_value):
        """Форматирование денежных значений из API"""
        if not money_value:
            return None
        return float(money_value.units) + float(money_value.nano) / 1_000_000_000
        
    def _get_figi(self):
        """Получение FIGI инструмента"""
        if self._figi:
            return self._figi
            
        with Client(self.token) as client:
            instruments = client.instruments.find_instrument(query=self.ticker)
            for instrument in instruments.instruments:
                if instrument.ticker.upper() == self.ticker.upper():
                    self._figi = instrument.figi
                    return self._figi
        
        raise ValueError(f"Ticker {self.ticker} not found")
    
    def get_current_price(self):
        """Получение текущей цены акции"""
        try:
            figi = self._get_figi()
            with Client(self.token) as client:
                last_price = client.market_data.get_last_prices(figi=[figi]).last_prices[0]
                return {
                    "ticker": self.ticker,
                    "price": self._format_money(last_price.price),
                    "time": str(last_price.time),
                    "figi": figi,
                    "currency": self.get_instrument_info().get("currency", "RUB"),
                    "source": "tinkoff"
                }
        except Exception as e:
            logger.error(f"Error getting current price for {self.ticker}: {str(e)}")
            return {"error": str(e)}
    
    def get_daily_data(self, days=30):
        """Получение исторических данных за указанное количество дней"""
        try:
            figi = self._get_figi()
            now = datetime.utcnow()
            from_date = now - timedelta(days=days)
            
            with Client(self.token) as client:
                candles = client.market_data.get_candles(
                    figi=figi,
                    from_=from_date,
                    to=now,
                    interval=CandleInterval.CANDLE_INTERVAL_DAY
                )
                
                result = []
                for candle in candles.candles:
                    result.append({
                        "date": str(candle.time),
                        "open": self._format_money(candle.open),
                        "high": self._format_money(candle.high),
                        "low": self._format_money(candle.low),
                        "close": self._format_money(candle.close),
                        "volume": candle.volume
                    })
                
                return {
                    "ticker": self.ticker,
                    "currency": self.get_instrument_info().get("currency", "RUB"),
                    "source": "tinkoff",
                    "interval": "day",
                    "data": result
                }
        except Exception as e:
            logger.error(f"Error getting daily data for {self.ticker}: {str(e)}")
            return {"error": str(e)}
    
    def get_instrument_info(self):
        """Получение информации об инструменте"""
        if self._instrument_info:
            return self._instrument_info
            
        try:
            figi = self._get_figi()
            with Client(self.token) as client:
                instrument = client.instruments.get_instrument_by(
                    id_type=InstrumentIdType.INSTRUMENT_ID_TYPE_FIGI, 
                    id=figi
                ).instrument
                
                self._instrument_info = {
                    "ticker": instrument.ticker,
                    "figi": instrument.figi,
                    "name": instrument.name,
                    "currency": instrument.currency,
                    "exchange": instrument.exchange,
                    "country": instrument.country_of_risk,
                    "sector": getattr(instrument, "sector", None),
                    "isin": getattr(instrument, "isin", None)
                }
                
                return self._instrument_info
        except Exception as e:
            logger.error(f"Error getting instrument info for {self.ticker}: {str(e)}")
            return {"error": str(e)}


class AlphaVantageApiClient(StockApiClient):
    """Клиент для работы с Alpha Vantage API"""
    
    def __init__(self, ticker):
        super().__init__(ticker)
        self.api_key = os.getenv("ALPHA_VANTAGE_KEY")
        if not self.api_key:
            raise ValueError("ALPHA_VANTAGE_KEY not set")
        self.base_url = "https://www.alphavantage.co/query"
        
        # Кэшированные данные
        self._instrument_info = None
        
    def get_current_price(self):
        """Получение текущей цены акции"""
        try:
            # Используем функцию GLOBAL_QUOTE для получения текущей цены
            params = {
                "function": "GLOBAL_QUOTE",
                "symbol": self.ticker,
                "apikey": self.api_key
            }
            
            response = requests.get(self.base_url, params=params)
            if response.status_code != 200:
                return {"error": f"Request failed with status code {response.status_code}"}
            
            data = response.json()
            
            if "Global Quote" not in data or not data["Global Quote"]:
                return {"error": "Stock not found or no data available"}
            
            quote = data["Global Quote"]
            
            return {
                "ticker": self.ticker,
                "price": float(quote["05. price"]),
                "change": float(quote["09. change"]),
                "change_percent": quote["10. change percent"].strip("%"),
                "volume": int(quote["06. volume"]),
                "time": quote["07. latest trading day"],
                "currency": "USD",  # Alpha Vantage обычно возвращает цены в USD
                "source": "alpha_vantage"
            }
        except Exception as e:
            logger.error(f"Error getting current price for {self.ticker}: {str(e)}")
            return {"error": str(e)}
    
    def get_daily_data(self, days=30):
        """Получение исторических данных за указанное количество дней"""
        try:
            params = {
                "function": "TIME_SERIES_DAILY",
                "symbol": self.ticker,
                "outputsize": "compact" if days <= 100 else "full",
                "apikey": self.api_key
            }
            
            response = requests.get(self.base_url, params=params)
            if response.status_code != 200:
                return {"error": f"Request failed with status code {response.status_code}"}
            
            data = response.json()
            
            if "Time Series (Daily)" not in data:
                return {"error": "Stock not found or no data available"}
            
            time_series = data["Time Series (Daily)"]
            all_dates = sorted(time_series.keys(), reverse=True)
            # Ограничиваем только нужным количеством дней
            dates = all_dates[:days]
            
            result = []
            for date in dates:
                day_data = time_series[date]
                result.append({
                    "date": date,
                    "open": float(day_data["1. open"]),
                    "high": float(day_data["2. high"]),
                    "low": float(day_data["3. low"]),
                    "close": float(day_data["4. close"]),
                    "volume": int(day_data["5. volume"])
                })
            
            return {
                "ticker": self.ticker,
                "currency": "USD",
                "source": "alpha_vantage",
                "interval": "day",
                "data": result
            }
        except Exception as e:
            logger.error(f"Error getting daily data for {self.ticker}: {str(e)}")
            return {"error": str(e)}
    
    def get_instrument_info(self):
        """Получение информации об инструменте"""
        if self._instrument_info:
            return self._instrument_info
            
        try:
            # Используем OVERVIEW для получения информации о компании
            params = {
                "function": "OVERVIEW",
                "symbol": self.ticker,
                "apikey": self.api_key
            }
            
            response = requests.get(self.base_url, params=params)
            if response.status_code != 200:
                return {"error": f"Request failed with status code {response.status_code}"}
            
            data = response.json()
            
            if not data or "Symbol" not in data:
                return {"error": "Stock not found or no data available"}
            
            self._instrument_info = {
                "ticker": data.get("Symbol"),
                "name": data.get("Name"),
                "exchange": data.get("Exchange"),
                "currency": "USD",
                "country": data.get("Country"),
                "sector": data.get("Sector"),
                "industry": data.get("Industry"),
                "description": data.get("Description")
            }
            
            return self._instrument_info
        except Exception as e:
            logger.error(f"Error getting instrument info for {self.ticker}: {str(e)}")
            return {"error": str(e)}


def get_stock_data(ticker, sources=None):
    """
    Получение данных о котировках из разных источников
    
    Args:
        ticker (str): Тикер акции
        sources (list): Список источников ['tinkoff', 'alpha_vantage']
        
    Returns:
        dict: Результаты из разных источников
    """
    if sources is None:
        sources = ['tinkoff', 'alpha_vantage']
    
    results = {
        "ticker": ticker,
        "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "sources": {}
    }
    
    for source in sources:
        try:
            if source == 'tinkoff':
                client = TinkoffApiClient(ticker)
            elif source == 'alpha_vantage':
                client = AlphaVantageApiClient(ticker)
            else:
                logger.warning(f"Unknown source: {source}")
                continue
                
            price_data = client.get_current_price()
            
            if "error" not in price_data:
                results["sources"][source] = {
                    "price": price_data,
                    "status": "success"
                }
            else:
                results["sources"][source] = {
                    "error": price_data["error"],
                    "status": "error"
                }
        except Exception as e:
            logger.error(f"Error with {source} API for {ticker}: {str(e)}")
            results["sources"][source] = {
                "error": str(e),
                "status": "error"
            }
    
    return results


# Пример использования
if __name__ == "__main__":
    for ticker in ["SBER", "EURRUB", "ET"]:
        print(f"\n=== {ticker} ===")
        try:
            tinkoff_client = TinkoffApiClient(ticker)
            daily = tinkoff_client.get_daily_data(days=10)
            if "error" in daily:
                print(f"Tinkoff daily data for {ticker} (error):", daily["error"])
            else:
                print(f"Tinkoff daily data for {ticker} (count={len(daily['data'])}):")
                for c in daily['data']:
                    print(f"  {c['date']} O:{c['open']} H:{c['high']} L:{c['low']} C:{c['close']} V:{c['volume']}")
        except Exception as e:
            print(f"Error for {ticker}: {e}")
    
    print("\n" + "-"*50 + "\n")
    
    # Затем через Alpha Vantage
    try:
        alpha_client = AlphaVantageApiClient(ticker)
        price = alpha_client.get_current_price()
        print(f"Alpha Vantage price for {ticker}:", json.dumps(price, indent=2))
        
        info = alpha_client.get_instrument_info()
        print(f"Alpha Vantage info for {ticker}:", json.dumps(info, indent=2))
        
        daily = alpha_client.get_daily_data(days=5)
        print(f"Alpha Vantage daily data for {ticker} (5 days):", json.dumps(daily, indent=2))
    except Exception as e:
        print(f"Error with Alpha Vantage API: {str(e)}")
    
    print("\n" + "-"*50 + "\n")
    
    # Используем функцию для получения данных из всех источников
    all_data = get_stock_data(ticker)
    print(f"All sources data for {ticker}:", json.dumps(all_data, indent=2)) 