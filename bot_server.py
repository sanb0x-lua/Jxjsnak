import os
import json
import threading
from datetime import datetime, timedelta

import psycopg2
from flask import Flask
from telegram import Update
from telegram.ext import ApplicationBuilder, CommandHandler, ContextTypes

# ================== CONFIG ==================

BOT_TOKEN = os.getenv("BOT_TOKEN")
DATABASE_URL = os.getenv("DATABASE_URL")

app = Flask(__name__)

# ================== DATABASE ==================

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

# ================== TELEGRAM COMMANDS ==================

async def create_key(update: Update, context: ContextTypes.DEFAULT_TYPE):
    key_value = os.urandom(16).hex()
    expire_date = datetime.utcnow() + timedelta(days=1)

    conn = get_connection()
    cur = conn.cursor()
    cur.execute(
        "INSERT INTO keys (key, expire, ip) VALUES (%s, %s, %s)",
        (key_value, expire_date, None)
    )
    conn.commit()
    cur.close()
    conn.close()

    await update.message.reply_text(f"Key created:\n{key_value}")

async def list_keys(update: Update, context: ContextTypes.DEFAULT_TYPE):
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("SELECT key, expire FROM keys")
    rows = cur.fetchall()
    cur.close()
    conn.close()

    if not rows:
        await update.message.reply_text("No keys in database.")
        return

    text = ""
    for key, expire in rows:
        text += f"{key} | {expire}\n"

    await update.message.reply_text(text)

# ================== START BOT ==================

def start_bot():
    application = ApplicationBuilder().token(BOT_TOKEN).build()

    application.add_handler(CommandHandler("create", create_key))
    application.add_handler(CommandHandler("keys", list_keys))

    application.run_polling()

# ================== FLASK ROUTE ==================

@app.route("/")
def home():
    return "Bot is running!"

# ================== MAIN ==================

if __name__ == "__main__":
    create_table()

    # Запуск бота в отдельном потоке
    threading.Thread(target=start_bot).start()

    # ВАЖНО ДЛЯ RENDER
    port = int(os.environ.get("PORT", 10000))
    app.run(host="0.0.0.0", port=port)