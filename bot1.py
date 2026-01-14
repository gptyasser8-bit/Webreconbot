from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ApplicationBuilder, CommandHandler, MessageHandler, CallbackQueryHandler, ContextTypes, filters
import requests
from bs4 import BeautifulSoup
from urllib.parse import urljoin, urlparse
from io import BytesIO

BOT_TOKEN = "7966472278:AAFvR5DtdkAiPJbH34S-rUPsJ484Yb6w3zI"

admin_paths = ["admin","admin/login","wp-admin","administrator","cpanel","panel","dashboard"]
user_urls = {}

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    welcome_text = """👋 مرحبا بك في بوت جمع معلومات المواقع..

🛠️ من إعداد وتطوير: ياسر الشريف
🔗 @Y_SH95

🌐 ادخل رابط الموقع المستهدف المراد فحصه
"""
    await update.message.reply_text(welcome_text)

async def handle_url(update: Update, context: ContextTypes.DEFAULT_TYPE):
    url = update.message.text.strip()
    user_urls[update.effective_user.id] = url

    keyboard = [
        [InlineKeyboardButton("🌐 معلومات الموقع", callback_data="info")],
        [InlineKeyboardButton("🔗 روابط الموقع", callback_data="links")],
        [InlineKeyboardButton("🛡️ Admin Panel", callback_data="admin")],
        [InlineKeyboardButton("☁️ Cloudflare", callback_data="cloudflare")],
        [InlineKeyboardButton("🧩 نوع النظام", callback_data="cms")],
        [InlineKeyboardButton("🌍 Subdomains", callback_data="subs")]
    ]

    await update.message.reply_text("اختر نوع الفحص:", reply_markup=InlineKeyboardMarkup(keyboard))

async def send_txt(chat_id, context, text):
    file = BytesIO()
    file.write(text.encode("utf-8"))
    file.seek(0)
    await context.bot.send_document(chat_id=chat_id, document=file, filename="scan_result.txt")

async def buttons(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    url = user_urls.get(query.from_user.id)
    domain = urlparse(url).netloc
    result = ""

    try:
        if query.data == "info":
            data = requests.get(f"http://ip-api.com/json/{domain}", timeout=15).json()
            result = f