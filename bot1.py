import os
from datetime import datetime
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ApplicationBuilder, CommandHandler, MessageHandler, CallbackQueryHandler, ContextTypes, filters
import requests
from bs4 import BeautifulSoup
from urllib.parse import urljoin, urlparse
from io import BytesIO

BOT_TOKEN = os.environ.get("BOT_TOKEN")
ADMIN_ID = 901802280  # رقم حسابك

admin_paths = ["admin","admin/login","wp-admin","administrator","cpanel","panel","dashboard"]
user_urls = {}

users_log = {}
targets_log = []
activity_log = []
stats = {"info":0,"links":0,"admin":0,"cloudflare":0,"cms":0,"subs":0}

def now():
    return datetime.now().strftime("%Y-%m-%d %H:%M:%S")

async def notify_admin(context, text):
    try:
        await context.bot.send_message(chat_id=ADMIN_ID, text=text)
    except:
        pass

def user_info(update):
    u = update.effective_user
    return f"{u.first_name} | @{u.username} | {u.id}"

def admin_panel_keyboard():
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("📊 الإحصائيات", callback_data="panel_stats")],
        [InlineKeyboardButton("👥 المستخدمين", callback_data="panel_users")],
        [InlineKeyboardButton("🌐 آخر المواقع", callback_data="panel_targets")],
        [InlineKeyboardButton("🔔 آخر النشاط", callback_data="panel_activity")],
        [InlineKeyboardButton("🔙 الرجوع للفحص", callback_data="panel_back")]
    ])

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    users_log[update.effective_user.id] = update.effective_user.username
    await notify_admin(context, f"🚀 دخول مستخدم\n{user_info(update)}")

    if update.effective_user.id == ADMIN_ID:
        await update.message.reply_text("👑 لوحة تحكم المالك", reply_markup=admin_panel_keyboard())
    else:
        await update.message.reply_text("👋 أهلاً بك\nأرسل رابط الموقع للبدء.")

async def handle_url(update: Update, context: ContextTypes.DEFAULT_TYPE):
    url = update.message.text.strip()
    user_urls[update.effective_user.id] = url
    targets_log.append(url)
    activity_log.append(f"{now()} - {user_info(update)} - {url}")

    await notify_admin(context, f"🌐 فحص موقع\n{user_info(update)}\n{url}")

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

    if query.data.startswith("panel_"):
        if query.from_user.id != ADMIN_ID:
            return

        if query.data == "panel_stats":
            msg = "📊 الإحصائيات\n\n"
            msg += f"👥 المستخدمين: {len(users_log)}\n"
            msg += f"🌐 الفحوصات: {len(targets_log)}\n\n"
            for k,v in stats.items():
                msg += f"{k}: {v}\n"
            await query.message.reply_text(msg)

        elif query.data == "panel_users":
            msg = "👥 آخر المستخدمين:\n"
            for uid,uname in list(users_log.items())[-10:]:
                msg += f"- @{uname} ({uid})\n"
            await query.message.reply_text(msg)

        elif query.data == "panel_targets":
            msg = "🌐 آخر المواقع:\n"
            for t in targets_log[-10:]:
                msg += f"- {t}\n"
            await query.message.reply_text(msg)

        elif query.data == "panel_activity":
            msg = "🔔 آخر النشاط:\n"
            for a in activity_log[-10:]:
                msg += f"- {a}\n"
            await query.message.reply_text(msg)

        elif query.data == "panel_back":
            await query.message.reply_text("أرسل رابط موقع للفحص.")

        return

    url = user_urls.get(query.from_user.id)
    domain = urlparse(url).netloc
    scan_type = query.data
    stats[scan_type] += 1
    activity_log.append(f"{now()} - {user_info(update)} - {scan_type}")

    await notify_admin(context, f"🧪 فحص: {scan_type}\n{user_info(update)}\n{url}")

    result = ""
    try:
        if scan_type == "info":
            data = requests.get(f"http://ip-api.com/json/{domain}", timeout=15).json()
            result = f"IP: {data.get('query')}\nCountry: {data.get('country')}\nISP: {data.get('isp')}"

        elif scan_type == "links":
            r = requests.get(url, timeout=15)
            soup = BeautifulSoup(r.text, "html.parser")
            links = set(urljoin(url, a['href']) for a in soup.find_all("a", href=True))
            result = "\n".join(list(links))

        elif scan_type == "admin":
            found = []
            for p in admin_paths:
                test = f"{url.rstrip('/')}/{p}"
                try:
                    if requests.get(test, timeout=10).status_code == 200:
                        found.append(test)
                except:
                    pass
            result = "\n".join(found) if found else "لا يوجد"

        elif scan_type == "cloudflare":
            h = requests.get(url, timeout=15).headers
            result = "مفعل" if "cloudflare" in str(h).lower() else "غير ظاهر"

        elif scan_type == "cms":
            r = requests.get(url, timeout=15).text
            result = "WordPress" if "wp-content" in r else "غير معروف"

        elif scan_type == "subs":
            crt = requests.get(f"https://crt.sh/?q=%25.{domain}&output=json", timeout=20).json()
            subs = list(set([i["name_value"] for i in crt]))
            result = "\n".join(subs)

    except Exception as e:
        result = f"خطأ: {e}"

    await send_txt(query.message.chat_id, context, result)

def main():
    app = ApplicationBuilder().token(BOT_TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_url))
    app.add_handler(CallbackQueryHandler(buttons))

    app.run_webhook(
        listen="0.0.0.0",
        port=10000,
        url_path=BOT_TOKEN,
        webhook_url=f"https://webreconbot.onrender.com/{BOT_TOKEN}"
    )

if __name__ == "__main__":
    main()