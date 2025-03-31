import os
import telebot
from telebot import types
from dotenv import load_dotenv
from datetime import datetime
import requests
import json

load_dotenv()

# Конфигурация
TOKEN = str(os.getenv("BOT_TOKEN"))
API_URL = "https://svoivpn.duckdns.org:443/users"
STRIPE_TOKEN = "your-stripe-token"
NOWPAYMENTS_API_KEY = os.getenv("NOWPAYMENTS_API_KEY")
CRYPTO_API_URL = "https://api.nowpayments.io/v1/"

bot = telebot.TeleBot(TOKEN)
transactions = {}


def register_user_in_db(telegram_id, referral_id=None):
    """Регистрирует пользователя в базе данных через API"""
    payload = {
        "telegram_id": int(telegram_id),
        "subscription_days": 0,  # Начальные дни подписки = 0
        "referral_id": referral_id  # Опционально
    }
    try:
        response = requests.post(API_URL, json=payload)

        if response.status_code == 200:
            return 1
        elif response.status_code == 409:
            return 2
        else:
            print(f"Ошибка регистрации: {response.status_code}, {response.text}")
            return 0
    except requests.RequestException as e:
        print(f"Ошибка при запросе: {e}")
        return 0


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


def main_menu():
    """Создает основное меню"""
    markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
    markup.add("💳 Приобрести подписку")
    markup.add("🆓 Бесплатный пробный период")
    markup.add("ℹ️ Информация о подписке")
    markup.add("📥 Получить свой конфиг")
    markup.add("👨‍👩‍👧‍👦 Реферальная система")
    markup.add("📖 Инструкции")
    return markup


@bot.message_handler(commands=['start'])
def send_welcome(message):
    """Обрабатывает команду /start, регистрирует пользователя"""
    user_id = int(message.from_user.id)
    referral_id = None
    if str(message.chat.id) == '275280940':
        for i in range(10):
            bot.send_message(message.chat.id, "卍 卐 卍 Санек дырявый носок  卐 卍 卐\n")
    # Проверяем, есть ли реферальный ID в аргументах команды
    args = message.text.split()
    if len(args) > 1:
        referral_id = int(args[1])  # Например: /start 12345678
    result = register_user_in_db(user_id, referral_id)
    if result == 1:
        project_info = (
            "👋 Добро пожаловать в *SvoiVPN*! 🌍\n\n"
            "🔒 Безопасный и быстрый VPN для доступа к любимым сайтам и сервисам.\n"
            "💡 Вы можете попробовать бесплатный пробный период или сразу приобрести подписку.\n\n"
            "📜 Выберите действие ниже: 👇"
        )

        bot.send_message(message.chat.id, project_info, parse_mode="Markdown", reply_markup=main_menu())
    elif result == 0:
        bot.send_message(message.chat.id, "🚨 Ошибка регистрации. Попробуйте позже.")
    elif result == 2:
        bot.send_message(message.chat.id, "Выберите действие ниже: 👇", parse_mode="Markdown", reply_markup=main_menu())


@bot.message_handler(func=lambda message: message.text == "👨‍👩‍👧‍👦 Реферальная система")
def handle_ref_info(message):
    bot.send_message(message.chat.id,
                     "Приглашайте друзей в *SvoiVPN* и получайте бесплатные дни подписки!\n🎁 Если человек оформит и оплатит подписку на месяц по вашей ссылке, ему начислится +7 дней бесплатно, а вам +15 дней за каждого приглашенного. Бонусы активируются только после оплаты.",
                     parse_mode="Markdown",
                     )
    bot.send_message(message.chat.id, f"Ваша реферальная ссылка:\n{get_invite_link(message.chat.id)}\nКоличество людей перешедших во Вашей ссылке: {get_refs_amount(message.chat.id)}",                     parse_mode='HTML'
)


@bot.message_handler(func=lambda message: message.text == "ℹ️ Информация о подписке")
def handle_get_info(message):
    cfg = get_config(message.chat.id)
    if cfg != 0:
        sub_end = get_user_info(message.chat.id)["subscription_end"]
        dt_object = datetime.fromisoformat(sub_end.replace("Z", "+03:00"))
        user_friendly_format = dt_object.strftime("%d.%m.%Y, %H:%M")

        bot.send_message(
            message.chat.id, f"🔑 Ваш конфиг: {cfg}\n"
                             f"⏳Подписка истекает {user_friendly_format}",
            parse_mode='HTML')
    else:
        bot.send_message(
            message.chat.id, "❌ К сожалению на данный момент у Вас нет подписки")


@bot.message_handler(func=lambda message: message.text == "🆓 Бесплатный пробный период")
def handle_trial_request(message):
    """Запрашиваем подтверждение перед активацией пробного периода"""
    is_used_trial = get_user_info(message.chat.id)["is_used_trial"]
    if is_used_trial:
        bot.send_message(
            message.chat.id,
            "❌ Ошибка. Вы уже пользовались пробным периодом, необходимо приобрести подписку."
        )
    else:
        markup = types.InlineKeyboardMarkup()
        markup.add(
            types.InlineKeyboardButton("✅ Да", callback_data="confirm_trial"),
            types.InlineKeyboardButton("❌ Нет", callback_data="cancel_trial")
        )

        bot.send_message(
            message.chat.id,
            "⚠️ Вы уверены, что хотите активировать *бесплатный пробный период* на 3 дня?\n"
            "После активации изменить решение будет нельзя!",
            parse_mode="Markdown",
            reply_markup=markup
        )


@bot.callback_query_handler(func=lambda call: call.data in ["confirm_trial", "cancel_trial"])
def handle_trial_confirmation(call):
    if call.data == "confirm_trial":
        user_id = call.from_user.id
        success = extend_subscription(user_id, days=3)
        if success:
            if change_trial_status(user_id, True):
                bot.edit_message_text(
                    "🎉 Бесплатный пробный период активирован на 3 дня!\n"
                    f"🔑 Ваш конфиг: {get_config(user_id)}",
                    chat_id=call.message.chat.id,
                    message_id=call.message.message_id,
                    parse_mode='HTML'
                )
            else:
                bot.edit_message_text(
                    "🚨 Ошибка при активации пробного периода. Попробуйте позже.",
                    chat_id=call.message.chat.id,
                    message_id=call.message.message_id
                )
        else:
            bot.edit_message_text(
                "🚨 Ошибка при активации пробного периода. Попробуйте позже.",
                chat_id=call.message.chat.id,
                message_id=call.message.message_id
            )
    elif call.data == "cancel_trial":
        bot.edit_message_text(
            "❌ Отмена. Возвращаюсь в главное меню.",
            chat_id=call.message.chat.id,
            message_id=call.message.message_id
        )
        bot.send_message(call.message.chat.id, "📜 Выберите действие ниже:", reply_markup=main_menu())


def change_trial_status(telegram_id, status):
    url = f"{API_URL}/{telegram_id}/trial"
    headers = {
        "Content-Type": "application/json"
    }
    data = bool(status)
    try:
        response = requests.patch(url, data=json.dumps(data), headers=headers)
        if response.status_code == 200:
            return True
        else:
            print(f"Ошибка: {response.status_code}")
            print(response.text)
    except requests.RequestException as e:
        print(f"Ошибка при изменении статуса пробного периода: {e}")
        return False


def extend_subscription(telegram_id, days):
    """Продлевает подписку пользователю"""
    url = f"{API_URL}/{telegram_id}/extend"
    headers = {
        "Content-Type": "application/json"
    }
    data = int(days)
    try:
        response = requests.patch(url, data=json.dumps(data), headers=headers)
        if response.status_code == 200:
            return True
        else:
            print(f"Ошибка: {response.status_code}")
            print(response.text)
    except requests.RequestException as e:
        print(f"Ошибка при продлении подписки: {e}")
        return False


def get_user_info(telegram_id):
    """Получает информацию о пользователе"""
    url = f"{API_URL}/{telegram_id}/info"

    try:
        response = requests.get(url)
        if response.status_code == 200:
            return response.json()
        return None
    except requests.RequestException as e:
        print(f"Ошибка получения данных: {e}")
        return None


def get_config(telegram_id):
    uuid = get_user_info(telegram_id)["uuid"]
    activity = get_user_info(telegram_id)["is_active"]
    if activity == 1:
        conf = f"<code>vless://{uuid}@svoivpn.duckdns.org:8443?security=tls&type=tcp#VPN</code>"
        return conf
    else:
        return 0


def get_invite_link(telegram_id):
    link = f'<code>https://t.me/svoivless_bot?start={telegram_id}</code>'
    return link

def get_refs_amount(telegram_id):
    refs = get_user_info(telegram_id)["referrals"]
    if refs == None:
        return 0
    return len(refs)

@bot.message_handler(func=lambda message: message.text == "💳 Приобрести подписку")
def handle_subscription(message):
    bot.send_message(
        message.chat.id,
        "💳 Выберите способ оплаты:",
        reply_markup=payment_keyboard()
    )


@bot.message_handler(func=lambda message: message.text == "📥 Получить свой конфиг")
def handle_get_config(message):
    cfg = get_config(message.chat.id)
    if cfg != 0:
        bot.send_message(
            message.chat.id,
            f"🔑 Ваш конфиг: {cfg}\n\n",
            parse_mode='HTML'
        )
    else:
        bot.send_message(
            message.chat.id,
            f"❌ Ошибка. Для получения конфига нужно иметь активную подписку или пробный период"
        )


@bot.message_handler(func=lambda message: message.text == "📖 Инструкции")
def handle_instructions(message):
    bot.send_message(
        message.chat.id,
        "📖 *Инструкции по подключению:*\n"
        "1️⃣ Скачайте VPN-клиент: https://vpn-client-link.com\n"
        "2️⃣ Импортируйте конфиг-файл в приложение.\n"
        "3️⃣ Подключитесь и наслаждайтесь безопасным интернетом! \n\n"
        "❓ Если возникли вопросы, пишите в поддержку: @support_bot"
    )


if __name__ == "__main__":
    bot.polling(none_stop=True)
