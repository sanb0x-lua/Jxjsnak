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

def add_key(duration):
    db = load_db()
    key = generate_key()

    db["keys"].append({
        "key": key,
        "expire": int(time.time()) + duration,
        "ip": None,
        "activated_at": None,
        "blocked": False
    })

    save_db(db)
    return key

def find_key(key):
    db = load_db()
    for k in db["keys"]:
        if k["key"] == key:
            return k
    return None

# ================= TELEGRAM MENUS =================

def main_menu(chat_id):
    markup = telebot.types.ReplyKeyboardMarkup(resize_keyboard=True)
    markup.add("Получить ключ", "Админ панель")
    bot.send_message(chat_id, "Выберите:", reply_markup=markup)

def admin_menu(chat_id):
    markup = telebot.types.ReplyKeyboardMarkup(resize_keyboard=True)
    markup.add("Все ключи", "Статистика")
    markup.add("Найти ключ", "Блокировать ключ")
    markup.add("Разблокировать ключ", "Удалить ключ")
    markup.add("Назад")
    bot.send_message(chat_id, "Админ панель:", reply_markup=markup)

@bot.message_handler(commands=['start'])
def start(message):
    main_menu(message.chat.id)

# ================= KEY CREATE =================

@bot.message_handler(func=lambda m: m.text == "Получить ключ")
def choose_time(message):
    markup = telebot.types.InlineKeyboardMarkup()
    markup.add(
        telebot.types.InlineKeyboardButton("24 часа", callback_data="24h"),
        telebot.types.InlineKeyboardButton("2 минуты", callback_data="2m")
    )

    if os.path.exists("choose.png"):
        with open("choose.png", "rb") as photo:
            bot.send_photo(message.chat.id, photo, caption="Выберите время:", reply_markup=markup)
    else:
        bot.send_message(message.chat.id, "Выберите время:", reply_markup=markup)

@bot.callback_query_handler(func=lambda call: True)
def callback(call):
    if call.data == "24h":
        key = add_key(86400)
    elif call.data == "2m":
        key = add_key(120)
    else:
        return

    text = f"Ключ создан:\n\n{key}"

    if os.path.exists("key.png"):
        with open("key.png", "rb") as photo:
            bot.send_photo(call.message.chat.id, photo, caption=text)
    else:
        bot.send_message(call.message.chat.id, text)

# ================= ADMIN LOGIN =================

@bot.message_handler(func=lambda m: m.text == "Админ панель")
def admin_login(message):
    msg = bot.send_message(message.chat.id, "Введите пароль:")
    bot.register_next_step_handler(msg, check_admin)

def check_admin(message):
    if message.text != ADMIN_PASSWORD:
        bot.send_message(message.chat.id, "Неверный пароль")
        return
    admin_menu(message.chat.id)

@bot.message_handler(func=lambda m: m.text == "Назад")
def back(message):
    main_menu(message.chat.id)

# ================= SHOW ALL =================

@bot.message_handler(func=lambda m: m.text == "Все ключи")
def show_all(message):
    db = load_db()
    now = int(time.time())
    text = "Keys:\n\n"

    for i, k in enumerate(db["keys"], 1):
        remaining = k["expire"] - now
        if k["blocked"]:
            status = "Blocked"
        elif remaining > 0:
            status = "Active"
        else:
            status = "Expired"

        text += f"{i}. {k['key']}\n"
        text += f"IP: {k['ip']}\n"
        text += f"Status: {status}\n"
        text += f"Remaining: {remaining if remaining>0 else 0}\n\n"

    bot.send_message(message.chat.id, text)

# ================= SEARCH =================

@bot.message_handler(func=lambda m: m.text == "Найти ключ")
def search_prompt(message):
    msg = bot.send_message(message.chat.id, "Введите ключ:")
    bot.register_next_step_handler(msg, search_action)

def search_action(message):
    k = find_key(message.text.strip())
    if not k:
        bot.send_message(message.chat.id, "Не найден")
        return

    remaining = k["expire"] - int(time.time())
    status = "Blocked" if k["blocked"] else ("Active" if remaining>0 else "Expired")

    text = f"""
Key: {k['key']}
IP: {k['ip']}
Status: {status}
Remaining: {remaining if remaining>0 else 0}
"""
    bot.send_message(message.chat.id, text)

# ================= BLOCK =================

@bot.message_handler(func=lambda m: m.text == "Блокировать ключ")
def block_prompt(message):
    msg = bot.send_message(message.chat.id, "Введите ключ:")
    bot.register_next_step_handler(msg, block_action)

def block_action(message):
    db = load_db()
    for k in db["keys"]:
        if k["key"] == message.text.strip():
            k["blocked"] = True
            save_db(db)
            bot.send_message(message.chat.id, "Ключ заблокирован")
            return
    bot.send_message(message.chat.id, "Не найден")

# ================= UNBLOCK =================

@bot.message_handler(func=lambda m: m.text == "Разблокировать ключ")
def unblock_prompt(message):
    msg = bot.send_message(message.chat.id, "Введите ключ:")
    bot.register_next_step_handler(msg, unblock_action)

def unblock_action(message):
    db = load_db()
    for k in db["keys"]:
        if k["key"] == message.text.strip():
            k["blocked"] = False
            save_db(db)
            bot.send_message(message.chat.id, "Ключ разблокирован")
            return
    bot.send_message(message.chat.id, "Не найден")

# ================= DELETE =================

@bot.message_handler(func=lambda m: m.text == "Удалить ключ")
def delete_prompt(message):
    msg = bot.send_message(message.chat.id, "Введите ключ:")
    bot.register_next_step_handler(msg, delete_action)

def delete_action(message):
    db = load_db()
    db["keys"] = [k for k in db["keys"] if k["key"] != message.text.strip()]
    save_db(db)
    bot.send_message(message.chat.id, "Удалено")

# ================= STATS =================

@bot.message_handler(func=lambda m: m.text == "Статистика")
def stats(message):
    db = load_db()
    now = int(time.time())

    total = len(db["keys"])
    active = sum(1 for k in db["keys"] if not k["blocked"] and k["expire"] > now)
    expired = sum(1 for k in db["keys"] if k["expire"] <= now)
    blocked = sum(1 for k in db["keys"] if k["blocked"])

    text = f"""
Статистика:

Всего: {total}
Активных: {active}
Просроченных: {expired}
Заблокированных: {blocked}
"""
    bot.send_message(message.chat.id, text)

# ================= CHECK KEY =================

@app.route("/check_key")
def check_key():
    key = request.args.get("key")
    user_ip = request.remote_addr

    db = load_db()

    for k in db["keys"]:
        if k["key"] == key:

            if k["blocked"]:
                return jsonify({"ok": False, "blocked": True})

            if time.time() > k["expire"]:
                return jsonify({"ok": False, "expired": True})

            if k["ip"] is None:
                k["ip"] = user_ip
                k["activated_at"] = int(time.time())
                save_db(db)

            return jsonify({"ok": True})

    return jsonify({"ok": False})

# ================= WEB =================

@app.route("/keys")
def view_keys():
    return json.dumps(load_db(), indent=4)

@app.route("/")
def home():
    return "Key System Running"

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