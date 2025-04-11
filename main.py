import os
import telebot
from telebot import types
from dotenv import load_dotenv

from utils.api import *
from utils.keyboards import *
from utils.crypto import get_pay_link, check_payment_status, currencies, get_crypto_price

load_dotenv()

# Конфигурация
TOKEN = str(os.getenv("BOT_TOKEN"))
MONTH = int(os.getenv("1_MONTH"))
THREE_MOTHS = int(os.getenv("3_MONTH"))
YEAR = int(os.getenv("YEAR"))
CRYPTO_MONTH = float(os.getenv("CRYPTO_MONTH"))
CRYPTO_THREE_MONTHS = float(os.getenv("CRYPTO_3_MONTH"))
CRYPTO_YEAR = float(os.getenv("CRYPTO_YEAR"))
PROVIDER_TOKEN = os.getenv("PROVIDER_TOKEN")  # Токен платежного провайдера

bot = telebot.TeleBot(TOKEN)
transactions = {}
invoices = {}

subscription_mapping = {
    "1 месяц": 30,
    "3 месяца": 90,
    "1 год": 365,
}


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
            "😤 Надоело менять VPN каждый месяц? Очередной сервис снова заблокировали?\n"
            "✨ Для нас — это не проблема.\n"

            "\n\n👋 Добро пожаловать в *SvoiVPN*! 🌍"

            "\n\n🔒 Безопасный и быстрый VPN для доступа к любимым сайтам и сервисам."
            "\n💡 Вы можете попробовать бесплатный пробный период или сразу приобрести подписку."

            "\n\n📜 Выберите действие ниже: 👇"
        )

        bot.send_message(message.chat.id, project_info, parse_mode="Markdown", reply_markup=main_menu())
    elif result == 0:
        bot.send_message(message.chat.id, "🚨 Ошибка регистрации. Попробуйте позже.")
    elif result == 2:
        bot.send_message(message.chat.id, "Выберите действие ниже: 👇", parse_mode="Markdown", reply_markup=main_menu())


@bot.message_handler(func=lambda message: message.text == "👨‍👩‍👧‍👦 Реферальная система")
def handle_ref_info(message):
    bot.send_message(message.chat.id,
                     "Приглашайте друзей в *SvoiVPN* и получайте бесплатные дни подписки!\n🎁 Если человек оформит и оплатит подписку по вашей ссылке, ему начислится +7 дней бесплатно, а вам +15 дней за каждого приглашенного. Бонусы активируются только после оплаты.",
                     parse_mode="Markdown",
                     )
    bot.send_message(message.chat.id,
                     f"Ваша реферальная ссылка:\n{get_invite_link(message.chat.id)}\nКоличество людей перешедших во Вашей ссылке: {get_refs_amount(message.chat.id)}",
                     parse_mode='HTML'
                     )


@bot.message_handler(func=lambda message: message.text == "ℹ Информация о подписке")
def handle_get_info(message):
    cfg = get_config(message.chat.id)
    if cfg != 0:
        date = sub_end(message.chat.id)

        bot.send_message(
            message.chat.id, f"🔑 Ваш конфиг: {cfg}\n"
                             f"⏳Подписка истекает {date}",
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
                send_instructions(call.message.chat.id)
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


@bot.callback_query_handler(func=lambda call: call.data in ["card"])
def handle_payment(call):
    """Обрабатывает оплату через Telegram Payments"""
    user_id = call.from_user.id

    if user_id not in transactions:
        bot.answer_callback_query(call.id, "Ошибка: выберите подписку сначала!", show_alert=True)
        return

    chosen_plan = transactions[user_id]["plan"]
    price = transactions[user_id]["price"]

    currency = os.getenv("CURRENCY", "RUB")

    prices = [types.LabeledPrice(label=f"Подписка на {chosen_plan}",
                                 amount=price * 100)]  # Умножаем на 100, так как в копейках

    provider_data = {
        "receipt": {
            "items": [
                {
                    "description": f"Подписка на {chosen_plan}",
                    "quantity": "1.00",
                    "amount": {
                        "value": f"{price}",
                        "currency": currency
                    },
                    "vat_code": 1
                }
            ]
        }
    }

    bot.send_invoice(
        chat_id=call.message.chat.id,
        title=f"Подписка на {chosen_plan}",
        description=f"Оплата подписки {chosen_plan} на сервис SvoiVPN.",
        invoice_payload=f"user_{user_id}_{chosen_plan}",
        provider_token=PROVIDER_TOKEN,
        currency=currency,
        prices=prices,
        start_parameter="vpn_subscription",
        is_flexible=False,
        need_email=True,
        send_email_to_provider=True,
        provider_data=json.dumps(provider_data)
    )


@bot.pre_checkout_query_handler(func=lambda query: True)
def checkout_process(pre_checkout_query):
    bot.answer_pre_checkout_query(pre_checkout_query.id, ok=True)


@bot.message_handler(content_types=['successful_payment'])
def successful_payment(message):
    """Обрабатывает успешный платеж"""
    user_id = message.from_user.id
    transaction_id = message.successful_payment.provider_payment_charge_id  # ID платежа в ЮKassa

    chosen_plan = transactions[user_id]["plan"]

    # Активируем подписку
    success = extend_subscription(user_id, days=subscription_mapping[chosen_plan])

    if success:
        bot.send_message(
            message.chat.id,
            f"✅ Оплата прошла успешно! Ваша подписка на {chosen_plan} активирована.\n"
            f"🔑 Ваш конфиг:\n{get_config(user_id)}\n"
            f"📌 Номер транзакции: <code>{transaction_id}</code>",
            parse_mode="HTML"
        )
        send_instructions(message.chat.id)
        handle_ref_bonus(message.chat.id)
    else:
        bot.send_message(message.chat.id, "🚨 Ошибка при активации подписки. Свяжитесь с поддержкой.")



    # Удаляем транзакцию
    transactions.pop(user_id, None)


@bot.callback_query_handler(func=lambda call: call.data == "crypto")
def handle_crypto_payment(call):
    user_id = call.from_user.id

    if user_id not in transactions:
        bot.answer_callback_query(call.id, "Ошибка: выберите подписку сначала!", show_alert=True)
        return

    chosen_plan = transactions[user_id]["plan"]
    currency_markup = types.InlineKeyboardMarkup()

    # Создаем кнопки для выбора криптовалюты
    for currency in currencies:
        currency_markup.add(types.InlineKeyboardButton(text=currency, callback_data=f"crypto_{currency}"))

    bot.edit_message_text(
        f"✅ Вы выбрали оплату криптовалютой. Выберите валюту для оплаты подписки на *{chosen_plan}*:",
        chat_id=call.message.chat.id,
        message_id=call.message.message_id,
        parse_mode="Markdown",
        reply_markup=currency_markup
    )


@bot.callback_query_handler(func=lambda call: call.data.startswith("crypto_"))
def handle_currency_choice(call):
    user_id = call.from_user.id
    selected_currency = call.data.split("crypto_")[1]  # Получаем выбранную валюту

    if user_id not in transactions:
        bot.answer_callback_query(call.id, "Ошибка: выберите подписку сначала!", show_alert=True)
        return

    chosen_plan = transactions[user_id]["plan"]
    price = None

    # Устанавливаем цену в зависимости от выбранного плана
    if chosen_plan == "1 месяц":
        price = CRYPTO_MONTH
    elif chosen_plan == "3 месяца":
        price = CRYPTO_THREE_MONTHS
    elif chosen_plan == "1 год":
        price = CRYPTO_YEAR
    price = round(price / get_crypto_price(selected_currency), 8)

    # Получаем ссылку на оплату с выбранной криптовалютой
    pay_link, invoice_id = get_pay_link(str(price), selected_currency)
    if pay_link and invoice_id:
        invoices[user_id] = invoice_id
        markup = types.InlineKeyboardMarkup()
        markup.add(types.InlineKeyboardButton(text=f"Оплатить {price} {selected_currency}", url=pay_link))
        markup.add(types.InlineKeyboardButton(text="Проверить оплату", callback_data=f'check_payment_{invoice_id}'))
        bot.send_message(user_id,
                         "Перейдите по этой ссылке для оплаты и после успешной транзакции нажмите <b><i>Проверить оплату</i></b>",
                         reply_markup=markup, parse_mode="HTML")
    else:
        bot.answer_callback_query(call.id, 'Ошибка: Не удалось создать счет на оплату.')


@bot.callback_query_handler(func=lambda call: call.data.startswith('check_payment_'))
def check_payment(call):
    chat_id = call.message.chat.id
    invoice_id = call.data.split('check_payment_')[1]
    payment_status = check_payment_status(invoice_id)
    if payment_status and payment_status.get('ok'):
        if 'items' in payment_status['result']:
            invoice = next((inv for inv in payment_status['result']['items'] if str(inv['invoice_id']) == invoice_id),
                           None)
            if invoice:
                status = invoice['status']
                if status == 'paid':
                    chosen_plan = transactions[chat_id]["plan"]

                    # Активируем подписку
                    success = extend_subscription(chat_id, days=subscription_mapping[chosen_plan])

                    if success:
                        bot.send_message(
                            chat_id,
                            f"✅ Оплата прошла успешно! Ваша подписка на {chosen_plan} активирована.\n"
                            f"🔑 Ваш конфиг:\n{get_config(chat_id)}\n",
                            parse_mode="HTML"
                        )
                        send_instructions(chat_id)
                        handle_ref_bonus(chat_id)
                    else:
                        bot.send_message(chat_id, "🚨 Ошибка при активации подписки. Свяжитесь с поддержкой.")

                    # Чтобы избежать дублирования счетов, удалим его из списка
                    invoices.pop(chat_id, None)
                    transactions.pop(chat_id, None)
                    bot.answer_callback_query(call.id)
                else:
                    bot.answer_callback_query(call.id, 'Оплата не найдена❌', show_alert=True)
            else:
                bot.answer_callback_query(call.id, 'Счет не найден.', show_alert=True)
        else:
            print(f"Ответ от API не содержит ключа 'items': {payment_status}")
            bot.answer_callback_query(call.id, 'Ошибка при получении статуса оплаты.', show_alert=True)
    else:
        print(f"Ошибка при запросе статуса оплаты: {payment_status}")
        bot.answer_callback_query(call.id, 'Ошибка при получении статуса оплаты.', show_alert=True)


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
    send_instructions(message.chat.id)


def send_instructions(user_id):
    bot.send_message(
        user_id,
        "❓ По любым вопросам пишите @TECH_SUPPORT_LINK\n\n"
        "📚 Выберите нужную инструкцию по подключению для Вашей системы:",
        reply_markup=instructions_keyboard()
    )

def handle_ref_bonus(telegram_id):
    ref_id = get_user_info(telegram_id)["referral_id"]
    if ref_id:
        ref_bonus = get_user_info(telegram_id)["is_used_ref_bonus"]
        if ref_bonus == False:
            days_for_paid = 7
            days_for_ref = 15
            extend = extend_subscription(telegram_id, days=days_for_paid)
            if extend:
                change_ref_bonus_status(telegram_id, True)
                date_paid = sub_end(telegram_id)
                bot.send_message(
                    telegram_id,
                    f"🎁 Вы перешли по реферальной ссылке - Вам начислен бонус <b>{days_for_paid} дней подписки</b> бесплатно!\n"
                    f"⏳ Подписка истекает {date_paid}",
                    parse_mode='HTML'
                )
            else:
                bot.send_message(
                    telegram_id,
                    f"❌ Ошибка получения реферального бонуса. Обратитесь в поддержу."
                )
            extend_ref = extend_subscription(ref_id, days=days_for_ref)
            if extend_ref:
                date_ref = sub_end(ref_id)
                bot.send_message(
                    ref_id,
                    f"🎁 По Вашей ссылке оплатили подписку, Вам начислен бонус <b>{days_for_ref} дней подписки</b> бесплатно!\n"
                    f"⏳ Подписка истекает {date_ref}",
                    parse_mode='HTML'
                )
            else:
                bot.send_message(
                    telegram_id,
                    f"❌ Ошибка получения реферального бонуса за {telegram_id}. Обратитесь в поддержу."
                )

if __name__ == "__main__":
    bot.remove_webhook()
    bot.polling(none_stop=True)
