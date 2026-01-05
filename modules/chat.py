import logging
import asyncio
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes, CallbackQueryHandler, MessageHandler, filters
from db import db
from config import Config

logger = logging.getLogger(__name__)

# 🛑 الزر الرئيسي الذي سيقرأه main.py تلقائياً
MAIN_BUTTON = "🔎 بحث عن شريك"

# مخزن مؤقت في الرام لسرعة المطابقة (بدون استخدام قاعدة البيانات لكل حركة)
waiting_queue = {"all": [], "male": [], "female": []}
active_chats = {} # {user_id: partner_id}

async def setup(application):
    """إعداد معالجات نظام الدردشة"""
    # الربط مع زر القائمة الرئيسية
    application.add_handler(MessageHandler(filters.Regex(f"^{MAIN_BUTTON}$"), start_search))
    
    # معالجات الأزرار الداخلية
    application.add_handler(CallbackQueryHandler(handle_chat_actions, pattern="^(cancel_search|next_partner|end_chat)$"))
    
    # معالج الرسائل بين الطرفين (الأولوية 1 لضمان عدم التداخل)
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, forward_message), group=1)

async def start_search(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    
    # التأكد أن المستخدم ليس في محادثة أصلاً
    if user_id in active_chats:
        await update.message.reply_text("⚠️ أنت في محادثة بالفعل! استخدم زر الإنهاء أولاً.")
        return

    # إضافة المستخدم للطابور
    if user_id not in waiting_queue["all"]:
        waiting_queue["all"].append(user_id)

    keyboard = [[InlineKeyboardButton("❌ إلغاء البحث", callback_data="cancel_search")]]
    await update.message.reply_text(
        "🔎 **جاري البحث عن شريك مجهول...**\n\nتأكد من الالتزام بالقوانين وعدم مشاركة بياناتك الحساسة.",
        reply_markup=InlineKeyboardMarkup(keyboard),
        parse_mode="Markdown"
    )
    
    # محاولة المطابقة
    await match_users(context)

async def match_users(context: ContextTypes.DEFAULT_TYPE):
    """خوارزمية المطابقة السريعة"""
    while len(waiting_queue["all"]) >= 2:
        user1 = waiting_queue["all"].pop(0)
        user2 = waiting_queue["all"].pop(0)

        # تسجيل المحادثة النشطة
        active_chats[user1] = user2
        active_chats[user2] = user1

        # واجهة التحكم في المحادثة
        keyboard = [
            [InlineKeyboardButton("⏭️ التالي", callback_data="next_partner"),
             InlineKeyboardButton("🛑 إنهاء", callback_data="end_chat")]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)

        success_msg = "✅ **تم العثور على شريك!**\nيمكنك الآن إرسال الرسائل مباشرة."
        
        try:
            await context.bot.send_message(user1, success_msg, reply_markup=reply_markup, parse_mode="Markdown")
            await context.bot.send_message(user2, success_msg, reply_markup=reply_markup, parse_mode="Markdown")
        except Exception as e:
            logger.error(f"Error sending match message: {e}")

async def forward_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """توجيه الرسائل بين الطرفين"""
    user_id = update.effective_user.id
    if user_id in active_chats:
        partner_id = active_chats[user_id]
        try:
            await context.bot.send_message(chat_id=partner_id, text=update.message.text)
        except:
            await handle_end_chat(user_id, partner_id, context)
    else:
        # إذا لم يكن في محادثة، لا نفعل شيئاً (يترك للموديولات الأخرى)
        return

async def handle_chat_actions(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    user_id = query.from_user.id
    data = query.data

    if data == "cancel_search":
        if user_id in waiting_queue["all"]:
            waiting_queue["all"].remove(user_id)
        await query.edit_message_text("❌ تم إلغاء البحث.")

    elif data == "end_chat":
        if user_id in active_chats:
            partner_id = active_chats[user_id]
            await handle_end_chat(user_id, partner_id, context)

    elif data == "next_partner":
        if user_id in active_chats:
            partner_id = active_chats[user_id]
            await handle_end_chat(user_id, partner_id, context)
        await start_search(update, context)

async def handle_end_chat(u1, u2, context):
    """تنظيف المحادثة وإخطار الأطراف"""
    active_chats.pop(u1, None)
    active_chats.pop(u2, None)
    
    msg = "🏁 انتهت المحادثة."
    try:
        await context.bot.send_message(u1, msg)
        await context.bot.send_message(u2, msg)
    except: pass
