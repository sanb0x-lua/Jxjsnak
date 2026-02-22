import telebot
from telebot import types
from flask import Flask, request, jsonify
import threading
import os
import time
import random
import string
import sqlite3

BOT_TOKEN = os.environ.get("BOT_TOKEN")
bot = telebot.TeleBot(BOT_TOKEN)

app = Flask(__name__)

ADMIN_PASSWORD = "12345"

DB_FILE = "keys.db"


# =========================
# DATABASE INIT
# =========================

def init_db():
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS keys (
            key TEXT PRIMARY KEY,
            expire INTEGER
        )
    """)
    conn.commit()
    conn.close()

init_db()


# =========================
# FUNCTIONS
# =========================

def generate_key():
    random_part = ''.join(random.choices(string.ascii_lowercase + string.digits, k=16))
    return f"KeySystem_{random_part}"


def add_key_to_db(key, expire_time):
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    cursor.execute("INSERT INTO keys (key, expire) VALUES (?, ?)", (key, expire_time))
    conn.commit()
    conn.close()


def check_key_in_db(key):
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    cursor.execute("SELECT expire FROM keys WHERE key=?", (key,))
    row = cursor.fetchone()
    conn.close()

    if not row:
        return False

    expire_time = row[0]
    if time.time() > expire_time:
        return False

    return True


def get_all_keys():
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    cursor.execute("SELECT key, expire FROM keys")
    rows = cursor.fetchall()
    conn.close()
    return rows


# =========================
# TELEGRAM
# =========================

@bot.message_handler(commands=['start'])
def start(message):
    markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
    markup.add("🔑 Получить ключ", "📋 Список ключей (админ)")
    bot.send_message(message.chat.id, "Выберите действие:", reply_markup=markup)


@bot.message_handler(func=lambda m: m.text == "🔑 Получить ключ")
def choose_time(message):
    markup = types.InlineKeyboardMarkup()
    markup.add(
        types.InlineKeyboardButton("24 часа", callback_data="24h"),
        types.InlineKeyboardButton("2 минуты", callback_data="2m")
    )
    bot.send_message(message.chat.id, "Выберите время:", reply_markup=markup)


@bot.callback_query_handler(func=lambda call: True)
def callback(call):
    if call.data == "24h":
        duration = 60 * 60 * 24
    elif call.data == "2m":
        duration = 60 * 2
    else:
        return

    key = generate_key()
    expire_time = int(time.time() + duration)

    add_key_to_db(key, expire_time)

    bot.send_message(call.message.chat.id, f"✅ Ваш ключ:\n\n`{key}`", parse_mode="Markdown")


@bot.message_handler(func=lambda m: m.text == "📋 Список ключей (админ)")
def admin_request(message):
    msg = bot.send_message(message.chat.id, "Введите пароль:")
    bot.register_next_step_handler(msg, check_admin)


def check_admin(message):
    if message.text != ADMIN_PASSWORD:
        bot.send_message(message.chat.id, "❌ Неверный пароль")
        return

    rows = get_all_keys()

    if not rows:
        bot.send_message(message.chat.id, "База пустая.")
        return

    text = "📋 База ключей:\n\n"
    now = time.time()

    for key, expire in rows:
        remaining = int(expire - now)
        if remaining > 0:
            text += f"{key} | Активен | {remaining} сек\n"
        else:
            text += f"{key} | Просрочен\n"

    bot.send_message(message.chat.id, text)


# =========================
# FLASK API
# =========================

@app.route("/")
def home():
    return "Server is running"


@app.route("/check_key")
def check_key():
    key = request.args.get("key")
    if not key:
        return jsonify({"ok": False})

    if check_key_in_db(key):
        return jsonify({"ok": True})
    else:
        return jsonify({"ok": False})


@app.route("/keys")
def view_keys():
    rows = get_all_keys()
    result = []

    for key, expire in rows:
        result.append({
            "key": key,
            "expire": expire
        })

    return jsonify(result)


# =========================
# START
# =========================

def run_bot():
    bot.infinity_polling(skip_pending=True)


if __name__ == "__main__":
    port = int(os.environ.get("PORT", 10000))

    thread = threading.Thread(target=run_bot)
    thread.daemon = True
    thread.start()

    app.run(host="0.0.0.0", port=port, use_reloader=False)