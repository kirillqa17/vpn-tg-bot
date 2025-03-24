import os
import telebot
from telebot import types
from dotenv import load_dotenv
import requests
import uuid
from datetime import datetime

load_dotenv()

# Конфигурация
TOKEN = str(os.getenv("BOT_TOKEN"))
API_ENDPOINT = "https://your-vpn-api.com/activate"
STRIPE_TOKEN = "your-stripe-token"
NOWPAYMENTS_API_KEY = os.getenv("NOWPAYMENTS_API_KEY")
CRYPTO_API_URL = "https://api.nowpayments.io/v1/"

bot = telebot.TeleBot(TOKEN)
transactions = {}


# Клавиатура выбора способа оплаты
def payment_keyboard():
    markup = types.InlineKeyboardMarkup()
    markup.row(
        types.InlineKeyboardButton("💳 Банковская карта", callback_data="card"),
        types.InlineKeyboardButton("Криптовалюта", callback_data="crypto")
    )
    markup.row(
        types.InlineKeyboardButton("⭐️ Telegram Stars", callback_data="stars")
    )
    return markup


@bot.message_handler(commands=['start'])
def send_welcome(message):
    bot.send_message(
        message.chat.id,
        "🎛 Выберите способ оплаты для доступа к VPN:",
        reply_markup=payment_keyboard()
    )


@bot.callback_query_handler(func=lambda call: True)
def handle_payment_selection(call):
    if call.data == "card":
        handle_card_payment(call)
    elif call.data == "crypto":
        handle_crypto_payment(call)
    elif call.data == "stars":
        handle_telegram_stars(call)


def handle_card_payment(call):
    bot.edit_message_text(
        chat_id=call.message.chat.id,
        message_id=call.message.message_id,
        text="💳 Оплата банковской картой:\n"
             "Сумма: $5.00\n"
             "Перейдите по ссылке для оплаты: https://your-stripe-link.com"
    )
    # Логика обработки платежа через Stripe API


def handle_telegram_stars(call):
    prices = [types.LabeledPrice("VPN доступ", 500)]  # 500 = $5.00

    bot.send_invoice(
        chat_id=call.message.chat.id,
        title="VPN доступ",
        description="Премиум доступ к VPN на 1 месяц",
        invoice_payload="vpn-premium-month",
        provider_token=STRIPE_TOKEN,
        currency="USD",
        prices=prices,
        start_parameter="vpn-payment"
    )


@bot.pre_checkout_query_handler(func=lambda query: True)
def process_pre_checkout(pre_checkout_query):
    if pre_checkout_query.invoice_payload != "vpn-premium-month":
        bot.answer_pre_checkout_query(pre_checkout_query.id, ok=False, error_message="Ошибка платежа")
    else:
        bot.answer_pre_checkout_query(pre_checkout_query.id, ok=True)


def generate_crypto_address(user_id, amount=5.0):
    headers = {"x-api-key": NOWPAYMENTS_API_KEY}
    data = {
        "price_amount": amount,
        "price_currency": "usd",
        "pay_currency": "btc",  # можно сделать выбор валюты
        "ipn_callback_url": "https://your-domain.com/crypto-webhook",
        "order_id": str(uuid.uuid4()),
        "order_description": "VPN Access"
    }

    response = requests.post(f"{CRYPTO_API_URL}invoice", json=data, headers=headers)
    if response.status_code == 201:
        payment_data = response.json()
        transactions[payment_data['id']] = {
            'user_id': user_id,
            'status': 'pending',
            'created': datetime.now(),
            'amount': amount,
            'address': payment_data['pay_address']
        }
        return payment_data['pay_address'], payment_data['id']
    return None, None


@bot.message_handler(commands=['check_payment'])
def check_payment(message):
    user_id = message.from_user.id
    for payment_id, data in transactions.items():
        if data['user_id'] == user_id and data['status'] == 'pending':
            headers = {"x-api-key": NOWPAYMENTS_API_KEY}
            response = requests.get(f"{CRYPTO_API_URL}payment/{payment_id}", headers=headers)

            if response.status_code == 200:
                status = response.json()['payment_status']
                if status == 'confirmed':
                    bot.send_message(message.chat.id, "✅ Платеж подтвержден! Доступ активирован!")
                    return

    bot.send_message(message.chat.id, "⚠️ Платеж не найден или еще не подтвержден")

def handle_crypto_payment(call):
    user_id = call.from_user.id
    address, payment_id = generate_crypto_address(user_id)

    if address:
        bot.edit_message_text(
            chat_id=call.message.chat.id,
            message_id=call.message.message_id,
            text=f" Криптоплатеж:\n"
                 f"Сумма: $5.00\n"
                 f"Адрес для оплаты: `{address}`\n"
                 f"ID платежа: `{payment_id}`\n"
                 "После оплаты нажмите /check_payment",
        )
    else:
        bot.send_message(call.message.chat.id, "🚨 Ошибка генерации адреса")


@bot.message_handler(content_types=['successful_payment'])
def handle_successful_payment(message):
    payment = message.successful_payment
    user = message.from_user

    data = {
        "user_id": user.id,
        "username": user.username,
        "amount": payment.total_amount,
        "currency": payment.currency,
        "payment_method": "telegram_stars"
    }

    try:
        response = requests.post(API_ENDPOINT, json=data)
        if response.status_code == 200:
            bot.send_message(message.chat.id, "✅ Платеж успешно обработан! Доступ активирован!")
        else:
            bot.send_message(message.chat.id, "⚠️ Ошибка активации. Свяжитесь с поддержкой.")
    except Exception as e:
        bot.send_message(message.chat.id, "🚨 Ошибка соединения. Попробуйте позже.")

if __name__ == "__main__":
    bot.polling(none_stop=True)