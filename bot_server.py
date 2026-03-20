import os
import secrets
import json
import threading
from datetime import datetime, timedelta

import psycopg2
from flask import Flask, request, jsonify
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ApplicationBuilder, CommandHandler, CallbackQueryHandler, ContextTypes

# ================== CONFIG ==================

BOT_TOKEN = os.getenv("BOT_TOKEN")
DATABASE_URL = os.getenv("DATABASE_URL")
CHANNEL = "@S1nboxChe2ts"
ADMIN_USERNAME = "superfemboy"

app_flask = Flask(__name__)

# ================== DATABASE (как в твоем файле) ==================

def get_connection():
    return psycopg2.connect(DATABASE_URL)

def create_table():
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("""
        CREATE TABLE IF NOT EXISTS keys (
            id SERIAL PRIMARY KEY,
            key TEXT UNIQUE,
            expire TIMESTAMP,
            ip TEXT
        );
    """)
    conn.commit()
    cur.close()
    conn.close()

create_table()

# Дополнительные функции для работы с БД
def save_key(key, expire_date, user_id):
    conn = get_connection()
    cur = conn.cursor()
    cur.execute(
        "INSERT INTO keys (key, expire, ip) VALUES (%s, %s, %s)",
        (key, expire_date, None)
    )
    conn.commit()
    cur.close()
    conn.close()

def get_all_keys():
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("SELECT key, expire, ip FROM keys ORDER BY expire DESC")
    rows = cur.fetchall()
    cur.close()
    conn.close()
    return rows

def get_keys_stats():
    conn = get_connection()
    cur = conn.cursor()
    
    cur.execute("SELECT COUNT(*) FROM keys")
    total = cur.fetchone()[0]
    
    cur.execute("SELECT COUNT(*) FROM keys WHERE expire < NOW()")
    expired = cur.fetchone()[0]
    
    cur.close()
    conn.close()
    return total, expired

# ================== FLASK API (для скрипта) ==================

@app_flask.route("/check_key", methods=["GET"])
def check_key():
    key = request.args.get("key")
    hwid = request.args.get("hwid")
    ip = request.remote_addr
    
    if not key or not hwid:
        return jsonify({"ok": False, "error": "Missing parameters"})
    
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("SELECT * FROM keys WHERE key = %s", (key,))
    key_data = cur.fetchone()
    
    if not key_data:
        cur.close()
        conn.close()
        return jsonify({"ok": False, "error": "Invalid key"})
    
    # Проверка срока действия
    expire = key_data[2]  # expire
    if datetime.utcnow() > expire:
        cur.close()
        conn.close()
        return jsonify({"ok": False, "expired": True})
    
    # Обновляем IP
    cur.execute("UPDATE keys SET ip = %s WHERE key = %s", (ip, key))
    conn.commit()
    cur.close()
    conn.close()
    
    return jsonify({"ok": True, "message": "Key valid"})

@app_flask.route("/")
def home():
    return "Bot is running!"

# ================== TELEGRAM БОТ ==================

# Проверка подписки
async def is_subscribed(user_id, context):
    try:
        member = await context.bot.get_chat_member(CHANNEL, user_id)
        return member.status in ["member", "administrator", "creator"]
    except:
        return False

# /start
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user

    if await is_subscribed(user.id, context):
        await main_menu(update, context)
        return

    keyboard = [
        [InlineKeyboardButton("Verify", callback_data="verify")]
    ]

    with open("Welcome.png", "rb") as photo:
        await update.message.reply_photo(
            photo=photo,
            caption="**Hello! This bot creates keys for the script. To continue, press the button below.**",
            parse_mode="Markdown",
            reply_markup=InlineKeyboardMarkup(keyboard)
        )

# Verify screen
async def verify_menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.message.delete()

    keyboard = [
        [InlineKeyboardButton("Subscribe", url="https://t.me/S1nboxChe2ts")],
        [InlineKeyboardButton("I'm Subscribed", callback_data="check_sub")]
    ]

    with open("Verify.png", "rb") as photo:
        await query.message.reply_photo(
            photo=photo,
            caption="**Subscribe to the channel to get access: @S1nboxChe2ts**",
            parse_mode="Markdown",
            reply_markup=InlineKeyboardMarkup(keyboard)
        )

# Проверка подписки
async def check_subscription(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    user = query.from_user

    if await is_subscribed(user.id, context):
        await query.answer()
        await main_menu_callback(query, context)
    else:
        await query.answer(
            "You haven't subscribed yet! Please join the channel and try again.",
            show_alert=True
        )

# Главное меню
async def main_menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    keyboard = [
        [InlineKeyboardButton("Keys", callback_data="keys")]
    ]

    if user.username == ADMIN_USERNAME:
        keyboard.append([InlineKeyboardButton("Admin", callback_data="admin")])

    with open("Main.png", "rb") as photo:
        await update.message.reply_photo(
            photo=photo,
            caption="**Welcome! Press the 'Keys' button to get a script.**",
            parse_mode="Markdown",
            reply_markup=InlineKeyboardMarkup(keyboard)
        )

async def main_menu_callback(query, context):
    keyboard = [
        [InlineKeyboardButton("Keys", callback_data="keys")]
    ]

    if query.from_user.username == ADMIN_USERNAME:
        keyboard.append([InlineKeyboardButton("Admin", callback_data="admin")])

    with open("Main.png", "rb") as photo:
        await query.message.reply_photo(
            photo=photo,
            caption="**Welcome! Press the 'Keys' button to get a script.**",
            parse_mode="Markdown",
            reply_markup=InlineKeyboardMarkup(keyboard)
        )

# Keys меню
async def keys_menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.message.delete()

    keyboard = [
        [InlineKeyboardButton("6 Hours", callback_data="6h")],
        [InlineKeyboardButton("Back to Main", callback_data="main")]
    ]

    with open("Keys.png", "rb") as photo:
        await query.message.reply_photo(
            photo=photo,
            caption="**Currently, there is only one key for 6 hours. More options will be available in the future.**",
            parse_mode="Markdown",
            reply_markup=InlineKeyboardMarkup(keyboard)
        )

# Генерация ключа (6 часов)
async def generate_key(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    user = query.from_user
    await query.message.delete()

    # Генерируем и сохраняем ключ в БД
    key = secrets.token_hex(16)
    expire = datetime.utcnow() + timedelta(hours=6)
    save_key(key, expire, user.id)

    keyboard = [
        [InlineKeyboardButton("Back to Keys", callback_data="keys")]
    ]

    text = f"""**Here is your 6-hour key:**
`{key}`

**Valid until:** {expire.strftime('%Y-%m-%d %H:%M:%S')} UTC

**Thank you for using our project!**"""

    with open("Key.png", "rb") as photo:
        await query.message.reply_photo(
            photo=photo,
            caption=text,
            parse_mode="Markdown",
            reply_markup=InlineKeyboardMarkup(keyboard)
        )

# ==================== АДМИН ПАНЕЛЬ ====================

async def admin_panel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query

    if query.from_user.username != ADMIN_USERNAME:
        await query.answer("Access denied!", show_alert=True)
        return
    
    await query.message.delete()

    keyboard = [
        [InlineKeyboardButton("📋 Список ключей", callback_data="admin_list")],
        [InlineKeyboardButton("📊 Статистика", callback_data="admin_stats")],
        [InlineKeyboardButton("◀️ Назад", callback_data="main")]
    ]

    await query.message.reply_text(
        "**👑 Админ панель**\n\n"
        "Выберите действие:",
        parse_mode="Markdown",
        reply_markup=InlineKeyboardMarkup(keyboard)
    )

# Список ключей
async def admin_list_keys(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    
    if query.from_user.username != ADMIN_USERNAME:
        await query.answer("Access denied!", show_alert=True)
        return
    
    await query.message.delete()
    
    keys = get_all_keys()
    
    if not keys:
        keyboard = [[InlineKeyboardButton("◀️ Назад в админку", callback_data="admin")]]
        await query.message.reply_text(
            "📭 База данных ключей пуста",
            reply_markup=InlineKeyboardMarkup(keyboard)
        )
        return
    
    text = "**📋 Все ключи:**\n\n"
    for k in keys:
        text += f"🔑 `{k[0]}`\n"
        text += f"   Истекает: {k[1].strftime('%Y-%m-%d %H:%M:%S')}\n"
        text += f"   IP: {k[2] if k[2] else 'не использован'}\n\n"
    
    keyboard = [[InlineKeyboardButton("◀️ Назад в админку", callback_data="admin")]]
    
    if len(text) > 4000:
        for i in range(0, len(text), 4000):
            await query.message.reply_text(text[i:i+4000], parse_mode="Markdown")
        await query.message.reply_text(
            "Выберите действие:",
            reply_markup=InlineKeyboardMarkup(keyboard)
        )
    else:
        await query.message.reply_text(
            text, 
            parse_mode="Markdown",
            reply_markup=InlineKeyboardMarkup(keyboard)
        )

# Статистика
async def admin_stats(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    
    if query.from_user.username != ADMIN_USERNAME:
        await query.answer("Access denied!", show_alert=True)
        return
    
    await query.message.delete()
    
    total, expired = get_keys_stats()
    active = total - expired
    
    text = f"""**📊 Статистика ключей**

📌 **Всего ключей:** {total}
⏰ **Активных:** {active}
⌛ **Истекло:** {expired}"""
    
    keyboard = [[InlineKeyboardButton("◀️ Назад в админку", callback_data="admin")]]
    
    await query.message.reply_text(
        text,
        parse_mode="Markdown",
        reply_markup=InlineKeyboardMarkup(keyboard)
    )

# ==================== Callback router ====================

async def callbacks(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    data = query.data

    if data == "verify":
        await verify_menu(update, context)
    elif data == "check_sub":
        await check_subscription(update, context)
    elif data == "keys":
        await keys_menu(update, context)
    elif data == "6h":
        await generate_key(update, context)
    elif data == "main":
        await main_menu_callback(query, context)
    elif data == "admin":
        await admin_panel(update, context)
    elif data == "admin_list":
        await admin_list_keys(update, context)
    elif data == "admin_stats":
        await admin_stats(update, context)
    
    await query.answer()

# ================== START BOT ==================

def start_bot():
    application = ApplicationBuilder().token(BOT_TOKEN).build()
    
    application.add_handler(CommandHandler("start", start))
    application.add_handler(CallbackQueryHandler(callbacks))
    
    application.run_polling()

# ================== MAIN ==================

if __name__ == "__main__":
    create_table()

    # Запуск бота в отдельном потоке
    threading.Thread(target=start_bot).start()

    # Запуск Flask
    port = int(os.environ.get("PORT", 10000))
    app_flask.run(host="0.0.0.0", port=port)