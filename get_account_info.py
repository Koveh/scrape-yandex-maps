import os
from dotenv import load_dotenv
from tinkoff.invest import Client
import pandas as pd
from datetime import datetime, timedelta

# Загрузка переменных окружения из файла .env
load_dotenv()

# Получение токена из переменных окружения
TOKEN = os.getenv("TINKOFF_INVEST_TOKEN")

def get_accounts_info():
    """Получение информации о счетах"""
    
    with Client(TOKEN) as client:
        # Получаем список счетов
        accounts = client.users.get_accounts()
        
        # Собираем информацию по каждому счету
        accounts_data = []
        for account in accounts.accounts:
            # Получаем позиции по счету
            positions = client.operations.get_positions(account_id=account.id)
            
            # Получаем портфолио по счету
            portfolio = client.operations.get_portfolio(account_id=account.id)
            
            accounts_data.append({
                'id': account.id,
                'name': account.name,
                'type': account.type.name,
                'status': account.status.name,
                'opened_date': account.opened_date.replace(tzinfo=None) if account.opened_date else None,
                'closed_date': account.closed_date.replace(tzinfo=None) if account.closed_date else None,
                'money_balance': sum(m.units + m.nano / 1_000_000_000 for m in positions.money),
                'securities_count': len(positions.securities),
                'portfolio_value': portfolio.total_amount_portfolio.units + portfolio.total_amount_portfolio.nano / 1_000_000_000,
                'expected_yield': portfolio.expected_yield.units + portfolio.expected_yield.nano / 1_000_000_000
            })
        
        return pd.DataFrame(accounts_data)

def get_positions_for_account(account_id):
    """Получение позиций по конкретному счету"""
    
    with Client(TOKEN) as client:
        # Получаем позиции по счету
        positions = client.operations.get_positions(account_id=account_id)
        
        # Получаем портфолио по счету для дополнительной информации
        portfolio = client.operations.get_portfolio(account_id=account_id)
        
        # Собираем информацию о деньгах на счете
        money_data = []
        for money in positions.money:
            money_data.append({
                'currency': money.currency,
                'balance': money.units + money.nano / 1_000_000_000
            })
        
        # Собираем информацию о ценных бумагах
        securities_data = []
        for security in positions.securities:
            # Ищем соответствующую позицию в портфолио для получения доп. информации
            portfolio_position = next(
                (pos for pos in portfolio.positions if pos.figi == security.figi), 
                None
            )
            
            securities_data.append({
                'figi': security.figi,
                'balance': security.balance,
                'blocked': security.blocked,
                'position_uid': security.position_uid,
                'instrument_type': security.instrument_type,
                'current_price': portfolio_position.current_price.units + portfolio_position.current_price.nano / 1_000_000_000 if portfolio_position else None,
                'average_buy_price': portfolio_position.average_position_price.units + portfolio_position.average_position_price.nano / 1_000_000_000 if portfolio_position and portfolio_position.average_position_price else None,
                'expected_yield': portfolio_position.expected_yield.units + portfolio_position.expected_yield.nano / 1_000_000_000 if portfolio_position else None
            })
        
        return {
            'money': pd.DataFrame(money_data),
            'securities': pd.DataFrame(securities_data)
        }

def main():
    try:
        # Получаем информацию о всех счетах
        print("Получение информации о счетах...")
        accounts_info = get_accounts_info()
        print("\nИнформация о счетах:")
        print(accounts_info)
        
        # Если есть счета, получаем детальную информацию по первому счету
        if not accounts_info.empty:
            account_id = accounts_info.iloc[0]['id']
            
            print(f"\nПолучение детальной информации по счету {account_id}...")
            positions = get_positions_for_account(account_id)
            
            print("\nДенежные средства:")
            print(positions['money'])
            
            print("\nЦенные бумаги:")
            print(positions['securities'])
            
            # Сохраняем результаты в CSV
            accounts_info.to_csv('accounts_info.csv', index=False, encoding='utf-8')
            positions['money'].to_csv(f'account_{account_id}_money.csv', index=False, encoding='utf-8')
            positions['securities'].to_csv(f'account_{account_id}_securities.csv', index=False, encoding='utf-8')
            
            print("\nДанные сохранены в CSV файлы")
            
    except Exception as e:
        print(f"Произошла ошибка: {e}")

if __name__ == "__main__":
    main() 