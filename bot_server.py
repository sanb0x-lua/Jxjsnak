import os
import time
import json
import random
import string
from flask import Flask, request, jsonify
import telebot

BOT_TOKEN = os.environ.get("BOT_TOKEN")
WEBHOOK_URL = "https://jxjsnak.onrender.com"

bot = telebot.TeleBot(BOT_TOKEN)
app = Flask(__name__)

ADMIN_PASSWORD = "123"
DB_FILE = "keys.json"

# ================= DATABASE =================

def load_db():
    if not os.path.exists(DB_FILE):
        with open(DB_FILE, "w") as f:
            json.dump({"keys": []}, f)

    with open(DB_FILE, "r") as f:
        return json.load(f)

def save_db(data):
    with open(DB_FILE, "w") as f:
        json.dump(data, f, indent=4)

def generate_key():
    return "KeySystem_" + ''.join(random.choices(string.ascii_lowercase + string.digits, k=16))

def add_key(key, duration):
    db = load_db()
    expire = int(time.time()) + duration

    db["keys"].append({
        "key": key,
        "expire": expire,
        "hwid": None,
        "ip": None,
        "activated_at": None
    })

    save_db(db)

def find_key(key):
    db = load_db()
    for k in db["keys"]:
        if k["key"] == key:
            return k
    return None

# ================= TELEGRAM =================

@bot.message_handler(commands=['start'])
def start(message):
    markup = telebot.types.ReplyKeyboardMarkup(resize_keyboard=True)
    markup.add("🔑 Получить ключ", "📋 Keys (админ)")
    bot.send_message(message.chat.id, "Выберите:", reply_markup=markup)

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
    add_key(key, duration)

    bot.send_message(call.message.chat.id, f"✅ Ключ создан:\n\n`{key}`", parse_mode="Markdown")

# ================= ADMIN PANEL =================

@bot.message_handler(func=lambda m: m.text == "📋 Keys (админ)")
def admin_login(message):
    msg = bot.send_message(message.chat.id, "Введите пароль:")
    bot.register_next_step_handler(msg, check_admin)

def check_admin(message):
    if message.text != ADMIN_PASSWORD:
        bot.send_message(message.chat.id, "❌ Неверный пароль")
        return

    db = load_db()
    keys = db["keys"]

    if not keys:
        bot.send_message(message.chat.id, "База пустая.")
        return

    text = "Keys:\n\n"
    now = int(time.time())

    for i, k in enumerate(keys, 1):
        remaining = k["expire"] - now
        status = "Active" if remaining > 0 else "Expired"

        text += f"{i}. Key: {k['key']}\n"
        text += f"   API: {k['ip']}\n"
        text += f"   HWID: {k['hwid']}\n"
        text += f"   Status: {status}\n"
        text += f"   Remaining: {remaining if remaining > 0 else 0} sec\n\n"

    bot.send_message(message.chat.id, text)

# ================= CHECK KEY =================

@app.route("/check_key")
def check_key():
    key = request.args.get("key")
    hwid = request.args.get("hwid")
    user_ip = request.remote_addr

    db = load_db()

    for k in db["keys"]:
        if k["key"] == key:

            if time.time() > k["expire"]:
                return jsonify({"ok": False, "expired": True})

            if k["hwid"] is None:
                k["hwid"] = hwid
                k["ip"] = user_ip
                k["activated_at"] = int(time.time())
                save_db(db)
                return jsonify({"ok": True})

            if k["hwid"] != hwid:
                return jsonify({"ok": False})

            return jsonify({"ok": True})

    return jsonify({"ok": False})

@app.route("/keys")
def show_keys():
    db = load_db()
    html = "<h1>Keys Database</h1><pre>"

    for i, k in enumerate(db["keys"], 1):
        html += f"""
{i}. Key: {k['key']}
   IP: {k['ip']}
   HWID: {k['hwid']}
   Expire: {k['expire']}

"""

    html += "</pre>"
    return html

@app.route("/")
def home():
    return "JSON Key System Running"

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