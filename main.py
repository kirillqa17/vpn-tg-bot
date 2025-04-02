import os
import telebot
from telebot import types
from dotenv import load_dotenv
from datetime import datetime

from utils.api import *
from utils.keyboards import *


load_dotenv()

# Конфигурация
TOKEN = str(os.getenv("BOT_TOKEN"))
MONTH = int(os.getenv("1_MONTH"))
THREE_MOTHS = int(os.getenv("3_MONTH"))
YEAR = int(os.getenv("YEAR"))

bot = telebot.TeleBot(TOKEN)
transactions = {}


@bot.message_handler(commands=['start'])
def send_welcome(message):
    """Обрабатывает команду /start, регистрирует пользователя"""
    user_id = int(message.from_user.id)
    referral_id = None
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
    bot.send_message(message.chat.id,
                     f"Ваша реферальная ссылка:\n{get_invite_link(message.chat.id)}\nКоличество людей перешедших во Вашей ссылке: {get_refs_amount(message.chat.id)}",
                     parse_mode='HTML'
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

@bot.message_handler(func=lambda message: message.text == "💳 Приобрести подписку")
def handle_subscription(message):
    bot.send_message(
        message.chat.id,
        "📅 Выберите срок подписки:",
        reply_markup=subscription_duration_keyboard()
    )

@bot.callback_query_handler(func=lambda call: call.data in ["sub_1m", "sub_3m", "sub_1y"])
def handle_subscription_choice(call):
    """Обрабатывает выбор подписки и показывает методы оплаты"""
    subscription_mapping = {
        "sub_1m": ("1 месяц", MONTH),
        "sub_3m": ("3 месяца", THREE_MOTHS),
        "sub_1y": ("1 год", YEAR),
    }

    chosen_plan, price = subscription_mapping[call.data]

    transactions[call.from_user.id] = {"plan": chosen_plan, "price": price}

    bot.edit_message_text(
        f"✅ Вы выбрали подписку на *{chosen_plan}* за *{price} ₽*.\n\n"
        "Выберите удобный способ оплаты:",
        chat_id=call.message.chat.id,
        message_id=call.message.message_id,
        parse_mode="Markdown",
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
