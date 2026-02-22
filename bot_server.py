import os
import telebot
import random
import time
from telebot import types
from flask import Flask, request, jsonify
import threading

# ==============================
# НАСТРОЙКИ
# ==============================

TOKEN = os.environ.get("BOT_TOKEN")  # берётся из Render
ADMIN_PASSWORD = "123"

bot = telebot.TeleBot(TOKEN)

app = Flask(__name__)

# Хранилище ключей в памяти
keys_db = []

# ==============================
# ФУНКЦИИ
# ==============================

def generate_key():
    chars = 'abcdefghijklmnopqrstuvwxyz1234567890'
    return 'KeySystem_' + ''.join(random.choices(chars, k=16))

# ==============================
# TELEGRAM БОТ
# ==============================

@bot.message_handler(commands=['start'])
def start(message):
    markup = types.InlineKeyboardMarkup()
    markup.add(
        types.InlineKeyboardButton("2 минуты", callback_data="2min"),
        types.InlineKeyboardButton("24 часа", callback_data="24h")
    )
    markup.add(
        types.InlineKeyboardButton("Админ", callback_data="admin")
    )

    bot.send_message(
        message.chat.id,
        "Добро пожаловать в KeySystem!",
        reply_markup=markup
    )

@bot.callback_query_handler(func=lambda call: True)
def callback_query(call):

    if call.data == "2min":
        key = generate_key()
        expire = int(time.time()) + 120

        keys_db.append({
            "key": key,
            "expire": expire
        })

        bot.send_message(call.message.chat.id, f"Ваш ключ на 2 минуты:\n{key}")

    elif call.data == "24h":
        key = generate_key()
        expire = int(time.time()) + 86400

        keys_db.append({
            "key": key,
            "expire": expire
        })

        bot.send_message(call.message.chat.id, f"Ваш ключ на 24 часа:\n{key}")

    elif call.data == "admin":
        msg = bot.send_message(call.message.chat.id, "Введите пароль:")
        bot.register_next_step_handler(msg, admin_login)

def admin_login(message):
    if message.text == ADMIN_PASSWORD:
        now = int(time.time())
        text = "Список ключей:\n\n"

        for k in keys_db:
            left = k["expire"] - now
            status = "Активен" if left > 0 else "Истёк"
            text += f"{k['key']} | {status} | Осталось {max(left,0)} сек\n"

        bot.send_message(message.chat.id, text)
    else:
        bot.send_message(message.chat.id, "Неверный пароль!")

# ==============================
# API ДЛЯ GG
# ==============================

@app.route("/")
def home():
    return "KeySystem работает!"

@app.route("/check_key")
def check_key():
    key = request.args.get("key")
    if not key:
        return jsonify({"ok": False}), 400

    now = int(time.time())

    for k in keys_db:
        if k["key"] == key:
            if k["expire"] > now:
                return jsonify({"ok": True})
            else:
                return jsonify({"ok": False, "status": "expired"})

    return jsonify({"ok": False, "status": "not_found"})

# ==============================
# ЗАПУСК
# ==============================

def run_bot():
    bot.infinity_polling()

if __name__ == "__main__":
    threading.Thread(target=run_bot).start()
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 10000)))