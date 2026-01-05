import logging
import asyncio
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes, CallbackQueryHandler, MessageHandler, filters
from modules.pepper import PepperManager

logger = logging.getLogger(__name__)

# 🛑 الزر الرئيسي
MAIN_BUTTON = "🔍 بحث حسب الجنس"

# طوابير الانتظار
gender_queues = {"male": [], "female": []}
active_gender_chats = {}

async def setup(application):
    # ربط الزر النصي للقائمة الرئيسية
    application.add_handler(MessageHandler(filters.Regex(f"^{MAIN_BUTTON}$"), gender_menu))
    
    # ربط جميع أزرار الـ Inline (تأكد من الـ pattern)
    application.add_handler(CallbackQueryHandler(gender_actions, pattern="^(find_|confirm_g_|cancel_g_|end_g_).*"))
    
    # معالج الرسائل المتبادلة
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, forward_g_messages), group=3)

async def gender_menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    balance = PepperManager.get_balance(user_id)
    
    text = (
        "✨ **البحث المتقدم حسب الجنس**\n\n"
        "سيتم خصم **5 فلفلات** 🌶️ عند المطابقة فقط.\n"
        f"💰 رصيدك: `{balance}` فلفلة"
    )
    
    keyboard = [
        [InlineKeyboardButton("♀️ بحث عن أنثى", callback_data="find_female")],
        [InlineKeyboardButton("♂️ بحث عن ذكر", callback_data="find_male")]
    ]
    await update.message.reply_text(text, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode="Markdown")

async def gender_actions(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    # 🛑 أهم خطوة: الإجابة على التنبيه فوراً لفك تعليق الزر
    await query.answer() 
    
    user_id = query.from_user.id
    data = query.data

    if data.startswith("find_"):
        target = "male" if "male" in data else "female"
        target_text = "ذكر ♂️" if target == "male" else "أنثى ♀️"
        
        keyboard = [
            [InlineKeyboardButton("✅ موافق (خصم 5 🌶️)", callback_data=f"confirm_g_{target}")],
            [InlineKeyboardButton("❌ إلغاء", callback_data="cancel_g_search")]
        ]
        await query.edit_message_text(f"سيتم البحث عن {target_text}.\nهل أنت متأكد؟", reply_markup=InlineKeyboardMarkup(keyboard))

    elif data.startswith("confirm_g_"):
        target = data.replace("confirm_g_", "")
        balance = PepperManager.get_balance(user_id)
        
        if balance < 5:
            await query.message.reply_text("❌ رصيدك غير كافٍ!")
            return

        if user_id not in gender_queues[target]:
            gender_queues[target].append(user_id)
            
        await query.edit_message_text("🔎 جاري البحث... يرجى الانتظار.", 
            reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("❌ إلغاء", callback_data="cancel_g_search")]]))
        
        await try_match(context, target)

    elif data == "cancel_g_search":
        for g in gender_queues:
            if user_id in gender_queues[g]: gender_queues[g].remove(user_id)
        await query.edit_message_text("❌ تم إلغاء البحث.")

async def try_match(context, gender):
    if len(gender_queues[gender]) >= 2:
        u1 = gender_queues[gender].pop(0)
        u2 = gender_queues[gender].pop(0)
        
        PepperManager.update_balance(u1, -5)
        PepperManager.update_balance(u2, -5)
        
        active_gender_chats[u1] = u2
        active_gender_chats[u2] = u1
        
        kb = InlineKeyboardMarkup([[InlineKeyboardButton("🛑 إنهاء", callback_data="end_g_chat")]])
        await context.bot.send_message(u1, "✅ تم العثور على شريك! (خصم 5 🌶️)", reply_markup=kb)
        await context.bot.send_message(u2, "✅ تم العثور على شريك! (خصم 5 🌶️)", reply_markup=kb)

async def forward_g_messages(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    if user_id in active_gender_chats:
        partner_id = active_gender_chats[user_id]
        await context.bot.send_message(partner_id, f"👤: {update.message.text}")
