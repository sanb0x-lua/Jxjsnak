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

bot = telebot.TeleBot(BOT_TOKEN)
app = Flask(__name__)

DB_FILE = "keys_db.json"

# =========================
# БАЗА ДАННЫХ
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
# TELEGRAM БОТ
# =========================

@bot.message_handler(commands=['start'])
def start(message):
    bot.reply_to(message, "Привет!\nНапиши /getkey чтобы получить ключ.")

@bot.message_handler(commands=['getkey'])
def get_key(message):
    keys = load_keys()

    new_key = generate_key()
    expire_time = int(time.time()) + 86400  # 24 часа

    keys.append({
        "key": new_key,
        "user_id": message.from_user.id,
        "username": message.from_user.username,
        "expire": expire_time
    })

    save_keys(keys)

    bot.reply_to(message, f"Твой ключ:\n\n{new_key}\n\nДействует 24 часа.")

# =========================
# API ПРОВЕРКИ КЛЮЧА
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
    current_time = int(time.time())

    for k in keys:
        if k["key"] == key:
            if current_time < k["expire"]:
                return jsonify({"ok": True})
            else:
                return jsonify({"ok": False})

    return jsonify({"ok": False})

# =========================
# ЗАПУСК
# =========================

def run_bot():
    bot.infinity_polling()

if __name__ == "__main__":
    threading.Thread(target=run_bot).start()
    app.run(host="0.0.0.0", port=10000)