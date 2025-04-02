from dotenv import load_dotenv
import os
import requests, json

load_dotenv()

API_URL = os.getenv("API_URL")

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
