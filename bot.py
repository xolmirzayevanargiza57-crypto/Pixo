import os
import requests
import logging
import base64
from io import BytesIO
from flask import Flask
import threading
from telegram import Update
from telegram.ext import (
    Application,
    CommandHandler,
    MessageHandler,
    filters,
    ContextTypes,
)
from telegram.constants import ChatAction

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

TELEGRAM_TOKEN = "8652624419:AAGr0bjfswnUaf0lxtSV-o2atb2188qOLwM"
GEMINI_API_KEY = "AIzaSyCtYMidjmrqCh_DAXy-xSnoxX23EfmUXxM"

GEMINI_CHAT_URL = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-1.5-flash:generateContent?key={GEMINI_API_KEY}"
GEMINI_IMAGE_URL = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-2.0-flash-preview-image-generation:generateContent?key={GEMINI_API_KEY}"

user_histories = {}

def gemini_chat(user_id, user_text):
    if user_id not in user_histories:
        user_histories[user_id] = []
    user_histories[user_id].append({
        "role": "user",
        "parts": [{"text": user_text}]
    })
    payload = {
        "system_instruction": {
            "parts": [{"text": "Sen Mira — aqlli, do'stona va ko'p tilli AI yordamchisisan. Foydalanuvchi qaysi tilda yozsa, o'sha tilda javob ber."}]
        },
        "contents": user_histories[user_id]
    }
    resp = requests.post(GEMINI_CHAT_URL, json=payload)
    data = resp.json()
    reply = data["candidates"][0]["content"]["parts"][0]["text"]
    user_histories[user_id].append({
        "role": "model",
        "parts": [{"text": reply}]
    })
    return reply

def gemini_image(prompt):
    payload = {
        "contents": [{"parts": [{"text": prompt}]}],
        "generationConfig": {"responseModalities": ["IMAGE", "TEXT"]}
    }
    resp = requests.post(GEMINI_IMAGE_URL, json=payload)
    data = resp.json()
    for part in data["candidates"][0]["content"]["parts"]:
        if "inlineData" in part:
            return base64.b64decode(part["inlineData"]["data"])
    return None

async def start(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "👋 Salom! Men Pixo— AI yordamchisiman!\n\n"
        "💬 Savolingizni yozing\n"
        "🖼 Rasm: /rasm <tavsif>\n"
        "🔄 Tozalash: /yangi"
    )

async def new_chat(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    user_histories.pop(update.effective_user.id, None)
    await update.message.reply_text("✅ Yangi suhbat boshlandi!")

async def handle_message(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    await ctx.bot.send_chat_action(update.effective_chat.id, ChatAction.TYPING)
    try:
        reply = gemini_chat(update.effective_user.id, update.message.text)
        if len(reply) > 4096:
            for i in range(0, len(reply), 4096):
                await update.message.reply_text(reply[i:i+4096])
        else:
            await update.message.reply_text(reply)
    except Exception as e:
        logger.error(e)
        await update.message.reply_text("⚠️ Xatolik. /yangi ni ishlating.")

async def generate_image(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    if not ctx.args:
        await update.message.reply_text("📝 Misol: /rasm tog'da quyosh botishi")
        return
    prompt = " ".join(ctx.args)
    msg = await update.message.reply_text("🎨 Rasm yaratilmoqda...")
    try:
        image_data = gemini_image(prompt)
        if image_data:
            await ctx.bot.delete_message(update.effective_chat.id, msg.message_id)
            await update.message.reply_photo(photo=BytesIO(image_data), caption=f"🖼 {prompt}")
        else:
            await msg.edit_text("❌ Rasm yaratib bo'lmadi.")
    except Exception as e:
        logger.error(e)
        await msg.edit_text("⚠️ Xatolik yuz berdi.")

flask_app = Flask(__name__)

@flask_app.route("/")
def home():
    return "Pixo Bot ishlayapti! ✅"

def run_flask():
    flask_app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 5000)))

def main():
    t = threading.Thread(target=run_flask)
    t.daemon = True
    t.start()
    app = Application.builder().token(TELEGRAM_TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("yangi", new_chat))
    app.add_handler(CommandHandler("rasm", generate_image))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
    logger.info("Mira Bot ishga tushdi!")
    app.run_polling()

if __name__ == "__main__":
    main()
