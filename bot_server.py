import os
import time
import random
import string
import sqlite3

from flask import Flask, request, jsonify
import telebot
from telebot.types import Update

BOT_TOKEN = os.environ.get("BOT_TOKEN")
WEBHOOK_URL = "https://jxjsnak.onrender.com"  # твой сайт

bot = telebot.TeleBot(BOT_TOKEN)
app = Flask(__name__)

ADMIN_PASSWORD = "12345"
DB_FILE = "keys.db"

# =========================
# DATABASE
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


def generate_key():
    random_part = ''.join(random.choices(string.ascii_lowercase + string.digits, k=16))
    return f"KeySystem_{random_part}"


def add_key(key, expire):
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    cursor.execute("INSERT INTO keys (key, expire) VALUES (?, ?)", (key, expire))
    conn.commit()
    conn.close()


def check_key_db(key):
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    cursor.execute("SELECT expire FROM keys WHERE key=?", (key,))
    row = cursor.fetchone()
    conn.close()

    if not row:
        return False

    return time.time() < row[0]


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
    markup = telebot.types.ReplyKeyboardMarkup(resize_keyboard=True)
    markup.add("🔑 Получить ключ", "📋 Список ключей (админ)")
    bot.send_message(message.chat.id, "Выберите действие:", reply_markup=markup)


@bot.message_handler(func=lambda m: m.text == "🔑 Получить ключ")
def choose_time(message):
    markup = telebot.types.InlineKeyboardMarkup()
    markup.add(
        telebot.types.InlineKeyboardButton("24 часа", callback_data="24h"),
        telebot.types.InlineKeyboardButton("2 минуты", callback_data="2m")
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
    expire = int(time.time() + duration)

    add_key(key, expire)

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
# WEBHOOK ROUTE
# =========================

@app.route(f"/{BOT_TOKEN}", methods=['POST'])
def webhook():
    json_str = request.get_data().decode("UTF-8")
    update = Update.de_json(json_str)
    bot.process_new_updates([update])
    return "ok", 200


@app.route("/")
def home():
    return "Bot is running"


@app.route("/check_key")
def check_key():
    key = request.args.get("key")
    if check_key_db(key):
        return jsonify({"ok": True})
    return jsonify({"ok": False})


@app.route("/keys")
def keys():
    rows = get_all_keys()
    return jsonify([{"key": k, "expire": e} for k, e in rows])


# =========================
# START
# =========================

if __name__ == "__main__":
    bot.remove_webhook()
    time.sleep(1)
    bot.set_webhook(url=f"{WEBHOOK_URL}/{BOT_TOKEN}")

    port = int(os.environ.get("PORT", 10000))
    app.run(host="0.0.0.0", port=port)