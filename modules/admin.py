import logging
from telegram import Update, ReplyKeyboardMarkup, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes, MessageHandler, filters, CommandHandler
from db import db
from config import Config

logger = logging.getLogger(__name__)

# زر اللوحة الرئيسي للحقن في القائمة
MAIN_BUTTON = "🛠️ لوحة المشرف"

async def setup(application):
    # الفلتر الخاص بالمشرفين فقط
    admin_filter = filters.User(user_id=Config.ADMIN_IDS)

    # 1. أوامر التحكم الفردي (عبر ID المستخدم)
    application.add_handler(CommandHandler("add", cmd_add_points, filters=admin_filter), group=0)
    application.add_handler(CommandHandler("sub", cmd_sub_points, filters=admin_filter), group=0)
    application.add_handler(CommandHandler("ban", cmd_ban_user, filters=admin_filter), group=0)
    application.add_handler(CommandHandler("unban", cmd_unban_user, filters=admin_filter), group=0)
    application.add_handler(CommandHandler("vip", cmd_give_vip, filters=admin_filter), group=0)
    application.add_handler(CommandHandler("unvip", cmd_take_vip, filters=admin_filter), group=0)
    application.add_handler(CommandHandler("send", cmd_send_private, filters=admin_filter), group=0)

    # 2. أزرار اللوحة والتحكم الجماعي
    application.add_handler(MessageHandler(filters.Regex(f"^{MAIN_BUTTON}$") & admin_filter, show_admin_panel), group=0)
    application.add_handler(MessageHandler(filters.Regex("^📢 إرسال للجميع$") & admin_filter, start_broadcast), group=0)
    application.add_handler(MessageHandler(filters.Regex("^💰 منح نقاط للجميع$") & admin_filter, points_to_all), group=0)
    
    # التقاط نص الإذاعة
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND & admin_filter, handle_broadcast_text), group=0)

async def show_admin_panel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    kb = [
        ["📢 إرسال للجميع", "💰 منح نقاط للجميع"],
        ["⚙️ تعليمات الأوامر", "🏠 القائمة الرئيسية"]
    ]
    msg = (
        "⚡ **غرفة التحكم المركزية (ID System)** ⚡\n"
        "━━━━━━━━━━━━━━\n"
        "**التحكم الفردي (أرسل الأمر والـ ID):**\n"
        "• `/add [ID] [العدد]` : منح نقاط\n"
        "• `/sub [ID] [العدد]` : خصم نقاط\n"
        "• `/ban [ID]` : حظر مستخدم\n"
        "• `/unban [ID]` : فك حظر\n"
        "• `/vip [ID]` : تفعيل VIP\n"
        "• `/unvip [ID]` : إلغاء VIP\n"
        "• `/send [ID] [النص]` : إرسال رسالة"
    )
    await update.message.reply_text(msg, reply_markup=ReplyKeyboardMarkup(kb, resize_keyboard=True), parse_mode="Markdown")

# --- [ وظائف التحكم الفردي عبر ID ] ---

async def cmd_add_points(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if len(context.args) < 2: return await update.message.reply_text("❌ الصيغة: `/add [ID] [العدد]`")
    uid, amount = int(context.args[0]), int(context.args[1])
    with db.get_cursor() as cur:
        cur.execute("UPDATE users SET points = points + ? WHERE user_id = ?", (amount, uid))
    await update.message.reply_text(f"✅ تم إضافة {amount} نقطة للمستخدم {uid}")

async def cmd_sub_points(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if len(context.args) < 2: return await update.message.reply_text("❌ الصيغة: `/sub [ID] [العدد]`")
    uid, amount = int(context.args[0]), int(context.args[1])
    with db.get_cursor() as cur:
        cur.execute("UPDATE users SET points = points - ? WHERE user_id = ?", (amount, uid))
    await update.message.reply_text(f"✅ تم خصم {amount} نقطة من المستخدم {uid}")

async def cmd_ban_user(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not context.args: return await update.message.reply_text("❌ الصيغة: `/ban [ID]`")
    uid = int(context.args[0])
    with db.get_cursor() as cur:
        cur.execute("UPDATE users SET is_ban = 1 WHERE user_id = ?", (uid,))
    await update.message.reply_text(f"🚫 تم حظر المستخدم {uid}")

async def cmd_unban_user(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not context.args: return await update.message.reply_text("❌ الصيغة: `/unban [ID]`")
    uid = int(context.args[0])
    with db.get_cursor() as cur:
        cur.execute("UPDATE users SET is_ban = 0 WHERE user_id = ?", (uid,))
    await update.message.reply_text(f"✅ تم فك حظر المستخدم {uid}")

async def cmd_give_vip(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not context.args: return await update.message.reply_text("❌ الصيغة: `/vip [ID]`")
    uid = int(context.args[0])
    with db.get_cursor() as cur:
        # التأكد من وجود العمود في حال لم يتم إنشاؤه
        try: cur.execute("UPDATE users SET is_vip = 1 WHERE user_id = ?", (uid,))
        except: 
            cur.execute("ALTER TABLE users ADD COLUMN is_vip INTEGER DEFAULT 0")
            cur.execute("UPDATE users SET is_vip = 1 WHERE user_id = ?", (uid,))
    await update.message.reply_text(f"💎 تم منح VIP للمستخدم {uid}")

async def cmd_take_vip(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not context.args: return await update.message.reply_text("❌ الصيغة: `/unvip [ID]`")
    uid = int(context.args[0])
    with db.get_cursor() as cur:
        cur.execute("UPDATE users SET is_vip = 0 WHERE user_id = ?", (uid,))
    await update.message.reply_text(f"🌑 تم سحب VIP من المستخدم {uid}")

async def cmd_send_private(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if len(context.args) < 2: return await update.message.reply_text("❌ الصيغة: `/send [ID] [النص]`")
    uid = int(context.args[0])
    text = " ".join(context.args[1:])
    try:
        await context.bot.send_message(uid, f"✉️ **رسالة إدارية:**\n\n{text}", parse_mode="Markdown")
        await update.message.reply_text("✅ تم إرسال الرسالة.")
    except: await update.message.reply_text("❌ فشل الإرسال.")

# --- [ وظائف التحكم الجماعي ] ---

async def points_to_all(update: Update, context: ContextTypes.DEFAULT_TYPE):
    with db.get_cursor() as cur:
        cur.execute("UPDATE users SET points = points + 50") # مثال 50 نقطة
    await update.message.reply_text("💰 تم منح 50 نقطة لجميع مستخدمي البوت!")

async def start_broadcast(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("📥 أرسل الآن الرسالة التي تود نشرها للجميع...")
    context.user_data['waiting_broadcast'] = True

async def handle_broadcast_text(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not context.user_data.get('waiting_broadcast'): return
    
    with db.get_cursor() as cur:
        users = cur.execute("SELECT user_id FROM users").fetchall()
    
    count = 0
    for user in users:
        try:
            await update.message.copy(chat_id=user['user_id'])
            count += 1
        except: continue
        
    context.user_data['waiting_broadcast'] = False
    await update.message.reply_text(f"✅ تم النشر بنجاح لـ {count} مستخدم.")
