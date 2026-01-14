import os
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ApplicationBuilder, CommandHandler, MessageHandler, CallbackQueryHandler, ContextTypes, filters
import requests
from bs4 import BeautifulSoup
from urllib.parse import urljoin, urlparse
from io import BytesIO

BOT_TOKEN = os.environ.get("BOT_TOKEN")

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
            result = f"""معلومات الموقع
IP: {data.get('query')}
الدولة: {data.get('country')}
المدينة: {data.get('city')}
الشركة: {data.get('isp')}
المنظمة: {data.get('org')}
"""

        elif query.data == "links":
            r = requests.get(url, timeout=15)
            soup = BeautifulSoup(r.text, "html.parser")
            links = set(urljoin(url, a['href']) for a in soup.find_all("a", href=True))
            result = "روابط الموقع:\n" + "\n".join(list(links))

        elif query.data == "admin":
            found = []
            for p in admin_paths:
                test = f"{url.rstrip('/')}/{p}"
                try:
                    if requests.get(test, timeout=10).status_code == 200:
                        found.append(test)
                except:
                    pass
            result = "Admin Panel:\n" + ("\n".join(found) if found else "لم يتم العثور على لوحة تحكم")

        elif query.data == "cloudflare":
            h = requests.get(url, timeout=15).headers
            result = "Cloudflare: مفعل" if "cloudflare" in str(h).lower() else "Cloudflare: غير ظاهر"

        elif query.data == "cms":
            r = requests.get(url, timeout=15).text
            result = "النظام: WordPress" if "wp-content" in r else "النظام: غير معروف"

        elif query.data == "subs":
            crt = requests.get(f"https://crt.sh/?q=%25.{domain}&output=json", timeout=20).json()
            subs = list(set([i["name_value"] for i in crt]))
            result = "Subdomains:\n" + "\n".join(subs)

    except Exception as e:
        result = f"حدث خطأ أثناء الفحص:\n{e}"

    await send_txt(query.message.chat_id, context, result)

def main():
    app = ApplicationBuilder().token(BOT_TOKEN).build()

    app.add_handler(CommandHandler("start", start))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_url))
    app.add_handler(CallbackQueryHandler(buttons))

    app.run_webhook(
        listen="0.0.0.0",
        port=10000,
        webhook_url=f"https://webreconbot.onrender.com/{BOT_TOKEN}"
    )

if __name__ == "__main__":
    main()