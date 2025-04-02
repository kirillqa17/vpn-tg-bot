from telebot import types
from dotenv import load_dotenv
import os

load_dotenv()

MONTH = int(os.getenv("1_MONTH"))
THREE_MOTHS = int(os.getenv("3_MONTH"))
YEAR = int(os.getenv("YEAR"))


def payment_keyboard():
    markup = types.InlineKeyboardMarkup()
    markup.row(
        types.InlineKeyboardButton("💳 Банковская карта", callback_data="card"),
        types.InlineKeyboardButton("₿ Криптовалюта", callback_data="crypto")
    )
    markup.row(
        types.InlineKeyboardButton("⭐ Telegram Stars", callback_data="stars")
    )
    return markup


def subscription_duration_keyboard():
    """Создает клавиатуру с вариантами подписки"""
    markup = types.InlineKeyboardMarkup()
    markup.row(
        types.InlineKeyboardButton(f"📅 1 месяц - {MONTH} ₽", callback_data="sub_1m"),
        types.InlineKeyboardButton(f"📅 3 месяца - {THREE_MOTHS} ₽", callback_data="sub_3m"),
    )
    markup.row(
        types.InlineKeyboardButton(f"📅 1 год - {YEAR} ₽", callback_data="sub_1y"),
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


