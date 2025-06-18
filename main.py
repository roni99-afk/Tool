
import os
import io
import qrcode
from flask import Flask, request
from telegram import Update, InputFile, Bot
from telegram.ext import (
    Dispatcher, CommandHandler, MessageHandler,
    ConversationHandler, ContextTypes, filters
)
from telegram.ext import CallbackContext

app = Flask(__name__)
BOT_TOKEN = os.getenv("BOT_TOKEN", "REPLACE_WITH_YOUR_TOKEN")
bot = Bot(token=BOT_TOKEN)

UPI_ID, NAME, AMOUNT = range(3)

from telegram.ext import Dispatcher
dispatcher = Dispatcher(bot, None, workers=4, use_context=True)

user_state = {}
user_data = {}

@app.route("/webhook", methods=["POST"])
def webhook():
    update = Update.de_json(request.get_json(force=True), bot)
    dispatcher.process_update(update)
    return "OK", 200

def start(update, context: CallbackContext):
    chat_id = update.effective_chat.id
    user_state[chat_id] = UPI_ID
    user_data[chat_id] = {}
    context.bot.send_message(chat_id, text=(
        "👋 Welcome to *QRFlow* — your instant UPI QR code generator bot!\n\n"
        "🔹 Enter your UPI ID, name, and amount\n"
        "🔹 Get a scannable QR for any UPI app\n\n"
        "➡️ Let's begin! Please enter your *UPI ID* (e.g., `yourname@upi`):"
    ), parse_mode="Markdown")

def handle_message(update, context: CallbackContext):
    chat_id = update.effective_chat.id
    text = update.message.text.strip()

    if chat_id not in user_state:
        return context.bot.send_message(chat_id, "Send /start to begin.")

    state = user_state[chat_id]

    if state == UPI_ID:
        user_data[chat_id]['upi'] = text
        user_state[chat_id] = NAME
        context.bot.send_message(chat_id, "📛 Now enter your *name* (receiver):", parse_mode='Markdown')
    elif state == NAME:
        user_data[chat_id]['name'] = text
        user_state[chat_id] = AMOUNT
        context.bot.send_message(chat_id, "💰 Finally, enter *amount in ₹* (minimum ₹1):", parse_mode='Markdown')
    elif state == AMOUNT:
        try:
            amount = float(text)
            if amount < 1:
                return context.bot.send_message(chat_id, "❌ Minimum amount is ₹1. Try again:")

            upi = user_data[chat_id]['upi']
            name = user_data[chat_id]['name']
            uri = f"upi://pay?pa={upi}&pn={name}&am={amount:.2f}&cu=INR"

            qr = qrcode.make(uri)
            buffer = io.BytesIO()
            qr.save(buffer, format="PNG")
            buffer.seek(0)

            context.bot.send_photo(chat_id, photo=InputFile(buffer),
                caption=f"✅ *QR Code Generated!*\n\n*Name:* {name}\n*Amount:* ₹{amount:.2f}", parse_mode='Markdown')

            del user_state[chat_id]
            del user_data[chat_id]
        except ValueError:
            context.bot.send_message(chat_id, "❌ Invalid amount. Please enter a number.")

def cancel(update, context: CallbackContext):
    chat_id = update.effective_chat.id
    user_state.pop(chat_id, None)
    user_data.pop(chat_id, None)
    context.bot.send_message(chat_id, "❌ Cancelled. Type /start to try again.")

dispatcher.add_handler(CommandHandler("start", start))
dispatcher.add_handler(CommandHandler("cancel", cancel))
dispatcher.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))

@app.route("/", methods=["GET"])
def root():
    return "QRFlow bot webhook is running!", 200
