import os
import time
import random
import string
import sqlite3
from flask import Flask, request, jsonify
import telebot

BOT_TOKEN = os.environ.get("BOT_TOKEN")
WEBHOOK_URL = "https://jxjsnak.onrender.com"

bot = telebot.TeleBot(BOT_TOKEN)
app = Flask(__name__)

ADMIN_PASSWORD = "12345"
DB_FILE = "keys.db"
IP_LIMIT = 5  # макс активаций с одного IP

# ================= DATABASE =================

def init_db():
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS keys (
            key TEXT PRIMARY KEY,
            expire INTEGER,
            hwid TEXT,
            ip TEXT,
            activated_at INTEGER,
            activations INTEGER DEFAULT 0
        )
    """)
    conn.commit()
    conn.close()

init_db()

def generate_key():
    return "KeySystem_" + ''.join(random.choices(string.ascii_lowercase + string.digits, k=16))

def add_key(key, expire):
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    cursor.execute("""
        INSERT INTO keys (key, expire, hwid, ip, activated_at, activations)
        VALUES (?, ?, NULL, NULL, NULL, 0)
    """, (key, expire))
    conn.commit()
    conn.close()

def activate_key(key, hwid, ip):
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()

    cursor.execute("SELECT activations FROM keys WHERE key=?", (key,))
    row = cursor.fetchone()
    activations = row[0] if row else 0

    if activations >= IP_LIMIT:
        conn.close()
        return False

    cursor.execute("""
        UPDATE keys
        SET hwid=?, ip=?, activated_at=?, activations=activations+1
        WHERE key=?
    """, (hwid, ip, int(time.time()), key))

    conn.commit()
    conn.close()
    return True

def get_key_data(key):
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    cursor.execute("SELECT expire, hwid, activations FROM keys WHERE key=?", (key,))
    row = cursor.fetchone()
    conn.close()
    return row

def delete_key(key):
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    cursor.execute("DELETE FROM keys WHERE key=?", (key,))
    conn.commit()
    conn.close()

def get_all_keys():
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    cursor.execute("SELECT key, expire, hwid, ip, activations FROM keys ORDER BY expire DESC")
    rows = cursor.fetchall()
    conn.close()
    return rows

# ================= TELEGRAM =================

@bot.message_handler(commands=['start'])
def start(message):
    markup = telebot.types.ReplyKeyboardMarkup(resize_keyboard=True)
    markup.add("🔑 Получить ключ", "📋 Admin Panel")
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
        duration = 86400
    elif call.data == "2m":
        duration = 120
    else:
        return

    key = generate_key()
    expire = int(time.time() + duration)
    add_key(key, expire)

    bot.send_message(call.message.chat.id, f"✅ Ключ создан:\n\n`{key}`", parse_mode="Markdown")

# ================= ADMIN PANEL =================

@bot.message_handler(func=lambda m: m.text == "📋 Admin Panel")
def admin_login(message):
    msg = bot.send_message(message.chat.id, "Введите пароль:")
    bot.register_next_step_handler(msg, check_admin)

def check_admin(message):
    if message.text != ADMIN_PASSWORD:
        bot.send_message(message.chat.id, "❌ Неверный пароль")
        return

    markup = telebot.types.ReplyKeyboardMarkup(resize_keyboard=True)
    markup.add("📋 Все ключи", "🟢 Активные", "🔴 Просроченные")
    markup.add("🔍 Поиск HWID", "🗑 Удалить ключ", "📊 Статистика")
    markup.add("⬅ Назад")
    bot.send_message(message.chat.id, "Admin Panel:", reply_markup=markup)

@bot.message_handler(func=lambda m: m.text == "📋 Все ключи")
def show_all(message):
    rows = get_all_keys()
    if not rows:
        bot.send_message(message.chat.id, "База пустая.")
        return

    now = time.time()
    text = "Keys:\n\n"

    for i, (key, expire, hwid, ip, acts) in enumerate(rows, 1):
        remaining = int(expire - now)
        status = "Active" if remaining > 0 else "Expired"

        text += f"{i}. Key: {key}\n"
        text += f"   API: {ip if ip else 'Not activated'}\n"
        text += f"   HWID: {hwid if hwid else 'Not activated'}\n"
        text += f"   Status: {status}\n"
        text += f"   Activations: {acts}\n"
        text += f"   Remaining: {remaining if remaining > 0 else 0} sec\n\n"

    bot.send_message(message.chat.id, text)

@bot.message_handler(func=lambda m: m.text == "🗑 Удалить ключ")
def delete_key_prompt(message):
    msg = bot.send_message(message.chat.id, "Введите ключ для удаления:")
    bot.register_next_step_handler(msg, delete_key_action)

def delete_key_action(message):
    delete_key(message.text.strip())
    bot.send_message(message.chat.id, "✅ Ключ удалён")

@bot.message_handler(func=lambda m: m.text == "📊 Статистика")
def stats(message):
    rows = get_all_keys()
    total = len(rows)
    active = sum(1 for r in rows if r[1] > time.time())
    expired = total - active

    text = f"""
📊 Статистика:

Всего ключей: {total}
Активных: {active}
Просроченных: {expired}
"""
    bot.send_message(message.chat.id, text)

# ================= CHECK KEY =================

@app.route("/check_key")
def check_key():
    key = request.args.get("key")
    hwid = request.args.get("hwid")
    user_ip = request.remote_addr

    data = get_key_data(key)
    if not data:
        return jsonify({"ok": False})

    expire, saved_hwid, activations = data

    if time.time() > expire:
        return jsonify({"ok": False, "expired": True})

    if saved_hwid is None:
        if not activate_key(key, hwid, user_ip):
            return jsonify({"ok": False, "limit": True})
        return jsonify({"ok": True})

    if saved_hwid != hwid:
        return jsonify({"ok": False})

    return jsonify({"ok": True})

@app.route("/")
def home():
    return "PRO Key System Running"

# ================= WEBHOOK =================

@app.route(f"/{BOT_TOKEN}", methods=["POST"])
def webhook():
    update = telebot.types.Update.de_json(request.stream.read().decode("utf-8"))
    bot.process_new_updates([update])
    return "ok", 200

if __name__ == "__main__":
    bot.remove_webhook()
    time.sleep(1)
    bot.set_webhook(url=f"{WEBHOOK_URL}/{BOT_TOKEN}")
    port = int(os.environ.get("PORT", 10000))
    app.run(host="0.0.0.0", port=port)