import os
import requests
from dotenv import load_dotenv

load_dotenv()

# Извлекаем токен из переменной окружения
CRYPTO_TOKEN = os.getenv("CRYPTO_TOKEN")
API_KEY = os.getenv("CMC_TOKEN")
currencies = ["TON", "TRON", "SOL", "ETH", "BNB", "USDT"]

def get_pay_link(amount, asset:str):
    headers = {"Crypto-Pay-API-Token": CRYPTO_TOKEN}
    data = {"asset": asset, "amount": amount}
    response = requests.post('https://pay.crypt.bot/api/createInvoice', headers=headers, json=data)
    if response.ok:
        response_data = response.json()
        return response_data['result']['pay_url'], response_data['result']['invoice_id']
    return None, None


def check_payment_status(invoice_id):
    headers = {
        "Crypto-Pay-API-Token": CRYPTO_TOKEN,
        "Content-Type": "application/json"
    }
    response = requests.post('https://pay.crypt.bot/api/getInvoices', headers=headers, json={})

    if response.ok:
        return response.json()
    else:
        print(f"Ошибка при запросе к API: {response.status_code}, {response.text}")
        return None


def get_crypto_price(crypto_currency):
    url = f'https://pro-api.coinmarketcap.com/v1/cryptocurrency/quotes/latest'
    parameters = {
        'symbol': crypto_currency,  # Символ криптовалюты (например, "TON", "ETH")
        'convert': 'USD',  # Конвертация в доллары США
    }

    headers = {
        'X-CMC_PRO_API_KEY': API_KEY,
        'Accept': 'application/json',
    }

    try:
        # Отправляем запрос к API CoinMarketCap
        response = requests.get(url, headers=headers, params=parameters)
        data = response.json()

        # Проверяем наличие данных для нужной криптовалюты
        if 'data' in data and crypto_currency in data['data']:
            crypto_data = data['data'][crypto_currency]  # Получаем данные для первой криптовалюты
            return crypto_data['quote']['USD']['price']  # Возвращаем цену в долларах
        else:
            return None
    except Exception as e:
        print(f"Ошибка при получении курса криптовалюты: {e}")
        return None

