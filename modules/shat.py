import logging
from telegram import Update
from telegram.ext import ContextTypes, MessageHandler, filters, CommandHandler
from db import db

logger = logging.getLogger(__name__)

# 🛑 الزر الرئيسي للقائمة
MAIN_BUTTON = "🔎 بحث عن شريك"

# مخازن الرام للمطابقة
waiting_queue = []
active_chats = {} # {user_id: partner_id}

async def setup(application):
    # ربط زر القائمة الرئيسية
    application.add_handler(MessageHandler(filters.Regex(f"^{MAIN_BUTTON}$"), start_search))
    # أوامر التحكم النصية
    application.add_handler(CommandHandler("stop", stop_command))
    application.add_handler(CommandHandler("next", next_command))
    # معالج الرسائل المباشرة
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, forward_message), group=1)

async def get_user_card(user_id):
    """توليد رسالة العثور بالبيانات المطلوبة حصراً"""
    with db.get_cursor() as cur:
        user = cur.execute("SELECT * FROM users WHERE user_id = ?", (user_id,)).fetchone()
        # محاولة جلب بيانات الزواج
        try:
            marriage = cur.execute("SELECT age, country FROM marriage_profiles WHERE user_id = ?", (user_id,)).fetchone()
        except: marriage = None

    name = user['first_name'] if user else "مجهول"
    points = user['points'] if user and 'points' in user.keys() else 0
    status = "👑 مستخدم VIP" if user and user.get('is_vip', 0) else "👤 مستخدم عادي"
    age = f"{marriage['age']} سنة" if marriage and marriage['age'] else "غير محدد 🎂"
    country = marriage['country'] if marriage and marriage['country'] else "غير محدد 🏴"

    # هذه هي الرسالة التي طلبتها بدقة
    card = (
        "✅ **تم العثور على شريك!**\n"
        "━━━━━━━━━━━━━━\n"
        f"👤 الـأسـم: {name}\n"
        f"🏷️ الـلـقـب: مـشارك 🎖️\n"
        f"🌍 الـدولـة: {country}\n"
        f"🎂 الـعـمـر: {age}\n"
        "━━━━━━━━━━━━━━\n"
        f"💳 الـرصـيـد: {points} فلفلة 🌶️\n"
        f"🌟 الـحـالـة: {status}\n"
        "━━━━━━━━━━━━━━\n"
        "💬 يمكنك الآن الكتابة مباشرة للشريك..\n\n"
        "🛑 /stop لإيقاف الدردشة\n"
        "⏭️ /next للبحث عن شريك آخر"
    )
    return card

async def start_search(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    if user_id in active_chats:
        await update.message.reply_text("⚠️ أنت في محادثة بالفعل! أرسل /stop للإنهاء.")
        return

    if user_id not in waiting_queue:
        waiting_queue.append(user_id)

    # رسالة البحث مع الأوامر النصية
    await update.message.reply_text(
        "🔎 **جاري البحث عن شريك... يرجى الانتظار**\n\n"
        "لإلغاء عملية البحث أرسل: /stop",
        parse_mode="Markdown"
    )
    await match_users(context)

async def match_users(context: ContextTypes.DEFAULT_TYPE):
    while len(waiting_queue) >= 2:
        u1 = waiting_queue.pop(0)
        u2 = waiting_queue.pop(0)
        active_chats[u1] = u2
        active_chats[u2] = u1

        # جلب الرسائل المصممة
        card_1 = await get_user_card(u2)
        card_2 = await get_user_card(u1)

        await context.bot.send_message(u1, card_1, parse_mode="Markdown")
        await context.bot.send_message(u2, card_2, parse_mode="Markdown")

async def forward_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    if user_id in active_chats:
        partner_id = active_chats[user_id]
        try:
            await context.bot.send_message(chat_id=partner_id, text=update.message.text)
        except:
            await handle_end(user_id, partner_id, context)

async def stop_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    if user_id in waiting_queue:
        waiting_queue.remove(user_id)
        await update.message.reply_text("❌ تم إلغاء البحث بنجاح.")
        return

    if user_id in active_chats:
        partner_id = active_chats[user_id]
        await handle_end(user_id, partner_id, context)
    else:
        await update.message.reply_text("❌ أنت لست في محادثة حالياً.")

async def next_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    if user_id in active_chats:
        partner_id = active_chats[user_id]
        await handle_end(user_id, partner_id, context)
    await start_search(update, context)

async def handle_end(u1, u2, context):
    active_chats.pop(u1, None)
    active_chats.pop(u2, None)
    msg = "🏁 **انتهت المحادثة.**\nاضغط على الزر بالأسفل للبحث مجدداً."
    try:
        await context.bot.send_message(u1, msg, parse_mode="Markdown")
        await context.bot.send_message(u2, msg, parse_mode="Markdown")
    except: pass
