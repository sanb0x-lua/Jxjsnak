import telebot
from telebot import types
from flask import Flask, request, jsonify
import threading
import os
import time
import random
import string

BOT_TOKEN = os.environ.get("BOT_TOKEN")
bot = telebot.TeleBot(BOT_TOKEN)

app = Flask(__name__)

# ВРЕМЕННАЯ БАЗА В ПАМЯТИ
keys_db = {}

ADMIN_PASSWORD = "12345"  # можешь поменять


# =========================
# ГЕНЕРАЦИЯ КЛЮЧА
# =========================

def generate_key():
    random_part = ''.join(random.choices(string.ascii_lowercase + string.digits, k=16))
    return f"KeySystem_{random_part}"


# =========================
# START
# =========================

@bot.message_handler(commands=['start'])
def start(message):
    markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
    btn1 = types.KeyboardButton("🔑 Получить ключ")
    btn2 = types.KeyboardButton("📋 Список ключей (админ)")
    markup.add(btn1, btn2)

    bot.send_message(message.chat.id, "Добро пожаловать!\nВыберите действие:", reply_markup=markup)


# =========================
# ПОЛУЧИТЬ КЛЮЧ
# =========================

@bot.message_handler(func=lambda m: m.text == "🔑 Получить ключ")
def choose_time(message):
    markup = types.InlineKeyboardMarkup()
    btn1 = types.InlineKeyboardButton("24 часа", callback_data="24h")
    btn2 = types.InlineKeyboardButton("2 минуты", callback_data="2m")
    markup.add(btn1, btn2)

    bot.send_message(message.chat.id, "Выберите время действия ключа:", reply_markup=markup)


@bot.callback_query_handler(func=lambda call: True)
def callback_handler(call):
    if call.data == "24h":
        duration = 60 * 60 * 24
    elif call.data == "2m":
        duration = 60 * 2
    else:
        return

    key = generate_key()
    expire_time = time.time() + duration

    keys_db[key] = expire_time

    bot.send_message(call.message.chat.id, f"✅ Ваш ключ:\n\n`{key}`", parse_mode="Markdown")


# =========================
# СПИСОК КЛЮЧЕЙ
# =========================

@bot.message_handler(func=lambda m: m.text == "📋 Список ключей (админ)")
def admin_request(message):
    msg = bot.send_message(message.chat.id, "Введите пароль администратора:")
    bot.register_next_step_handler(msg, check_admin_password)


def check_admin_password(message):
    if message.text != ADMIN_PASSWORD:
        bot.send_message(message.chat.id, "❌ Неверный пароль!")
        return

    if not keys_db:
        bot.send_message(message.chat.id, "База ключей пуста.")
        return

    text = "📋 Список ключей:\n\n"
    current_time = time.time()

    for key, expire in keys_db.items():
        remaining = int(expire - current_time)
        if remaining > 0:
            text += f"{key} | Активен | {remaining} сек\n"
        else:
            text += f"{key} | Просрочен\n"

    bot.send_message(message.chat.id, text)


# =========================
# ПРОВЕРКА КЛЮЧА (для Lua)
# =========================

@app.route("/check_key")
def check_key():
    key = request.args.get("key")

    if not key or key not in keys_db:
        return jsonify({"ok": False})

    if time.time() > keys_db[key]:
        return jsonify({"ok": False})

    return jsonify({"ok": True})


@app.route("/")
def home():
    return "Server is running"


# =========================
# ЗАПУСК
# =========================

def run_bot():
    print("BOT STARTED")
    bot.infinity_polling(skip_pending=True)


if __name__ == "__main__":
    port = int(os.environ.get("PORT", 10000))

    thread = threading.Thread(target=run_bot)
    thread.daemon = True
    thread.start()

    app.run(host="0.0.0.0", port=port, use_reloader=False)