from flask import Flask, request, jsonify
import telebot
import json
import time
import os
import random
import string
import threading

# =========================
# НАСТРОЙКИ
# =========================

BOT_TOKEN = os.getenv("BOT_TOKEN")
if not BOT_TOKEN:
    raise Exception("BOT_TOKEN не найден в Environment Variables")

ADMIN_PASSWORD = "123"
DB_FILE = "keys_db.json"

bot = telebot.TeleBot(BOT_TOKEN)
app = Flask(__name__)

# =========================
# БАЗА
# =========================

def load_keys():
    if not os.path.exists(DB_FILE):
        with open(DB_FILE, "w") as f:
            json.dump([], f)
        return []

    with open(DB_FILE, "r") as f:
        try:
            return json.load(f)
        except:
            return []

def save_keys(data):
    with open(DB_FILE, "w") as f:
        json.dump(data, f, indent=4)

# =========================
# ГЕНЕРАЦИЯ КЛЮЧА
# =========================

def generate_key():
    return "KeySystem_" + ''.join(random.choices(string.ascii_lowercase + string.digits, k=16))

# =========================
# TELEGRAM UI
# =========================

@bot.message_handler(commands=['start'])
def start(message):
    markup = telebot.types.InlineKeyboardMarkup()

    btn1 = telebot.types.InlineKeyboardButton("⏳ 2 минуты", callback_data="2min")
    btn2 = telebot.types.InlineKeyboardButton("🕒 24 часа", callback_data="24h")
    btn3 = telebot.types.InlineKeyboardButton("👑 Админ", callback_data="admin")

    markup.add(btn1, btn2)
    markup.add(btn3)

    bot.send_message(
        message.chat.id,
        "Добро пожаловать в KeySystem!\nВыбери срок действия ключа:",
        reply_markup=markup
    )

# =========================
# ОБРАБОТКА КНОПОК
# =========================

@bot.callback_query_handler(func=lambda call: True)
def callback_handler(call):

    if call.data == "admin":
        msg = bot.send_message(call.message.chat.id, "Введите пароль администратора:")
        bot.register_next_step_handler(msg, admin_panel)
        return

    keys = load_keys()

    if call.data == "2min":
        expire_time = int(time.time()) + 120

    elif call.data == "24h":
        expire_time = int(time.time()) + 86400

    else:
        return

    key = generate_key()

    keys.append({
        "key": key,
        "user_id": call.from_user.id,
        "username": call.from_user.username,
        "expire": expire_time
    })

    save_keys(keys)

    bot.send_message(
        call.message.chat.id,
        f"🔑 Ваш ключ:\n\n{key}"
    )

# =========================
# АДМИН ПАНЕЛЬ
# =========================

def admin_panel(message):
    if message.text != ADMIN_PASSWORD:
        bot.send_message(message.chat.id, "❌ Неверный пароль.")
        return

    keys = load_keys()
    now = int(time.time())

    if not keys:
        bot.send_message(message.chat.id, "База ключей пуста.")
        return

    text = "📋 Список ключей:\n\n"

    for k in keys:
        left = k["expire"] - now
        status = "Активен" if left > 0 else "Истёк"
        text += f"{k['key']} | {status} | {max(left,0)} сек\n"

    bot.send_message(message.chat.id, text)

# =========================
# API ПРОВЕРКА
# =========================

@app.route("/")
def home():
    return "Server is running"

@app.route("/check_key")
def check_key():
    key = request.args.get("key")

    if not key:
        return jsonify({"ok": False})

    keys = load_keys()
    now = int(time.time())

    for k in keys:
        if k["key"] == key:
            if k["expire"] > now:
                return jsonify({"ok": True})
            else:
                return jsonify({"ok": False})

    return jsonify({"ok": False})

# =========================
# ЗАПУСК
# =========================

def run_bot():
    bot.infinity_polling(skip_pending=True)

if __name__ == "__main__":
    threading.Thread(target=run_bot).start()
    port = int(os.environ.get("PORT", 10000))
    app.run(host="0.0.0.0", port=port)