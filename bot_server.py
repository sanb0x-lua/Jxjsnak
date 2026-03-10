import os
import secrets
from datetime import datetime, timedelta

from telegram import (
    Update,
    InlineKeyboardButton,
    InlineKeyboardMarkup
)
from telegram.ext import (
    ApplicationBuilder,
    CommandHandler,
    CallbackQueryHandler,
    ContextTypes
)

BOT_TOKEN = os.getenv("BOT_TOKEN")

CHANNEL = "@S1nboxChe2ts"
ADMIN_USERNAME = "superfemboy"

# ---------------------------
# Проверка подписки
# ---------------------------

async def is_subscribed(user_id, context):
    try:
        member = await context.bot.get_chat_member(CHANNEL, user_id)
        return member.status in ["member", "administrator", "creator"]
    except:
        return False


# ---------------------------
# /start
# ---------------------------

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


# ---------------------------
# Verify screen
# ---------------------------

async def verify_menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    
    # Удаляем предыдущее сообщение
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


# ---------------------------
# Проверка подписки
# ---------------------------

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


# ---------------------------
# Главное меню
# ---------------------------

async def main_menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    keyboard = [
        [InlineKeyboardButton("Keys", callback_data="keys")]
    ]

    if user.username == ADMIN_USERNAME:
        keyboard.append(
            [InlineKeyboardButton("Admin", callback_data="admin")]
        )

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
        keyboard.append(
            [InlineKeyboardButton("Admin", callback_data="admin")]
        )

    with open("Main.png", "rb") as photo:
        await query.message.reply_photo(
            photo=photo,
            caption="**Welcome! Press the 'Keys' button to get a script.**",
            parse_mode="Markdown",
            reply_markup=InlineKeyboardMarkup(keyboard)
        )


# ---------------------------
# Keys меню
# ---------------------------

async def keys_menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    
    # Удаляем предыдущее сообщение
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


# ---------------------------
# Генерация ключа
# ---------------------------

async def generate_key(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    
    # Удаляем предыдущее сообщение
    await query.message.delete()

    key = secrets.token_hex(16)
    expire = datetime.utcnow() + timedelta(hours=6)

    # Здесь нужно сохранять ключ в базу данных
    # TODO: Добавить сохранение ключа в БД

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


# ---------------------------
# Админ панель
# ---------------------------

async def admin_panel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query

    if query.from_user.username != ADMIN_USERNAME:
        await query.answer("Access denied!", show_alert=True)
        return
    
    # Удаляем предыдущее сообщение
    await query.message.delete()

    keyboard = [
        [InlineKeyboardButton("Back", callback_data="main")]
    ]

    await query.message.reply_text(
        "**Welcome to Admin Panel.**\n\n"
        "• View keys\n"
        "• Generate keys\n"
        "• Statistics",
        parse_mode="Markdown",
        reply_markup=InlineKeyboardMarkup(keyboard)
    )


# ---------------------------
# Callback router
# ---------------------------

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
    
    await query.answer()


# ---------------------------
# Запуск
# ---------------------------

if __name__ == "__main__":
    if not BOT_TOKEN:
        print("Error: BOT_TOKEN environment variable not set!")
        exit(1)
    
    print("Starting bot...")
    app = ApplicationBuilder().token(BOT_TOKEN).build()
    
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CallbackQueryHandler(callbacks))
    
    print("Bot is running...")
    app.run_polling()