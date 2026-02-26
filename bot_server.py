import os
import time
import json
import random
import string
import threading
from datetime import datetime, timedelta

import psycopg2
import telebot
from flask import Flask, request, jsonify

# =====================================================
# ENV
# =====================================================

BOT_TOKEN = os.environ.get("BOT_TOKEN")
DATABASE_URL = os.environ.get("DATABASE_URL")

if not BOT_TOKEN:
    raise Exception("BOT_TOKEN not set")

if not DATABASE_URL:
    raise Exception("DATABASE_URL not set")

# =====================================================
# DATABASE
# =====================================================

conn = psycopg2.connect(DATABASE_URL, sslmode="require")
conn.autocommit = False
cur = conn.cursor()

cur.execute("""
CREATE TABLE IF NOT EXISTS keys (
    id SERIAL PRIMARY KEY,
    key TEXT UNIQUE NOT NULL,
    expire BIGINT,
    ip TEXT,
    activated_at BIGINT,
    blocked BOOLEAN DEFAULT FALSE
);
""")
conn.commit()

# =====================================================
# JSON ЛОГИКА (как было)
# =====================================================

def db_to_json():
    cur.execute("SELECT key, expire, ip, activated_at, blocked FROM keys")
    rows = cur.fetchall()

    data = {}

    for row in rows:
        data[row[0]] = {
            "expire": row[1],
            "ip": row[2],
            "activated_at": row[3],
            "blocked": row[4]
        }

    return data


def save_key_to_db(key_data):
    try:
        cur.execute("""
            INSERT INTO keys (key, expire, ip, activated_at, blocked)
            VALUES (%s, %s, %s, %s, %s)
            ON CONFLICT (key) DO UPDATE SET
                expire = EXCLUDED.expire,
                ip = EXCLUDED.ip,
                activated_at = EXCLUDED.activated_at,
                blocked = EXCLUDED.blocked
        """, (
            key_data["key"],
            key_data["expire"],
            key_data["ip"],
            key_data["activated_at"],
            key_data["blocked"]
        ))
        conn.commit()
    except:
        conn.rollback()


# =====================================================
# BOT
# =====================================================

bot = telebot.TeleBot(BOT_TOKEN)

def generate_key():
    return ''.join(random.choices(string.ascii_uppercase + string.digits, k=20))


@bot.message_handler(commands=['create'])
def create_key(message):
    key_value = generate_key()
    expire_time = int((datetime.utcnow() + timedelta(days=30)).timestamp())

    key_json = {
        "key": key_value,
        "expire": expire_time,
        "ip": None,
        "activated_at": None,
        "blocked": False
    }

    save_key_to_db(key_json)

    bot.reply_to(message, f"✅ Ключ создан:\n{key_value}")


@bot.message_handler(commands=['check'])
def check_key(message):
    try:
        key_value = message.text.split(" ")[1]
    except:
        bot.reply_to(message, "Используй: /check КЛЮЧ")
        return

    data = db_to_json()

    if key_value not in data:
        bot.reply_to(message, "❌ Ключ не найден")
        return

    key_data = data[key_value]

    if key_data["blocked"]:
        bot.reply_to(message, "⛔ Ключ заблокирован")
        return

    if key_data["expire"] and int(time.time()) > key_data["expire"]:
        bot.reply_to(message, "⌛ Ключ просрочен")
        return

    bot.reply_to(message, "✅ Ключ действителен")


# =====================================================
# API ДЛЯ LUA / SCRIPT
# =====================================================

app = Flask(__name__)

@app.route("/")
def home():
    return "Server is running"


@app.route("/api/check", methods=["POST"])
def api_check():
    data = request.json
    key_value = data.get("key")
    user_ip = request.remote_addr

    cur.execute("SELECT expire, ip, blocked FROM keys WHERE key=%s", (key_value,))
    result = cur.fetchone()

    if not result:
        return jsonify({"status": "invalid"})

    expire, ip, blocked = result

    if blocked:
        return jsonify({"status": "blocked"})

    if expire and int(time.time()) > expire:
        return jsonify({"status": "expired"})

    if ip and ip != user_ip:
        return jsonify({"status": "ip_mismatch"})

    if not ip:
        cur.execute("UPDATE keys SET ip=%s, activated_at=%s WHERE key=%s",
                    (user_ip, int(time.time()), key_value))
        conn.commit()

    return jsonify({"status": "valid"})


# =====================================================
# THREADING
# =====================================================

def run_bot():
    bot.infinity_polling()

if __name__ == "__main__":
    threading.Thread(target=run_bot).start()
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 10000)))