import logging
from telegram import Update, ReplyKeyboardMarkup, ReplyKeyboardRemove, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes, MessageHandler, filters, ConversationHandler, CallbackQueryHandler
from db import db
from config import Config

logger = logging.getLogger(__name__)

# --- [ الإعدادات ] ---
MAIN_BUTTON = "👰 طلبات الزواج والارتباط 🤵"
MARRIAGE_CHANNEL_ID = "-1002341857929" # تأكد من وضع ID قناتك الصحيح هنا
GENERAL_BROWSE_URL = "https://t.me/+zXF3JS4FqkQ2NDFk"

# حالات المحادثة
GENDER, AGE, COUNTRY, BIO = range(4)

async def setup(application):
    application.add_handler(MessageHandler(filters.Regex(f"^{MAIN_BUTTON}$"), marriage_main_menu), group=0)
    
    # معالج التسجيل الاحترافي
    conv_handler = ConversationHandler(
        entry_points=[MessageHandler(filters.Regex("^📝 إنشاء ملفي الشخصي$"), start_reg)],
        states={
            GENDER: [MessageHandler(filters.Text(["ذكر 👨", "أنثى 👩"]), set_gender)],
            AGE: [MessageHandler(filters.Regex(r'^\d+$'), set_age), 
                  MessageHandler(filters.TEXT & ~filters.COMMAND, invalid_age)], # منع النصوص في العمر
            COUNTRY: [MessageHandler(filters.TEXT & ~filters.COMMAND, set_country)],
            BIO: [MessageHandler(filters.TEXT & ~filters.COMMAND, set_bio)],
        },
        fallbacks=[MessageHandler(filters.Regex("^إلغاء ❌$"), cancel_reg)],
        map_to_parent={-1: 0}
    )
    application.add_handler(conv_handler)
    
    # معالجات الأزرار
    application.add_handler(MessageHandler(filters.Regex("^🔍 استعراض الملفات 💎$"), browse_files_gate), group=0)
    application.add_handler(MessageHandler(filters.Regex("^📋 عرض بياناتي$"), show_my_data), group=0)
    application.add_handler(CallbackQueryHandler(handle_browsing, pattern="^(next_file|chat_with_)"), group=0)

# --- [ القائمة الرئيسية ] ---
async def marriage_main_menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    kb = [
        ["🔍 استعراض الملفات 💎", "📝 إنشاء ملفي الشخصي"],
        ["📋 عرض بياناتي", "🏠 القائمة الرئيسية"]
    ]
    msg = (
        "🌹 **〖 مـنـصـة الـنصيب الـذكية 〗** 🌹\n"
        "━━━━━━━━━━━━━━\n"
        "مرحباً بك في عالم الاستقرار والارتباط.\n\n"
        "⚠️ **ملاحظة:** استعراض الملفات متاح فقط لمشتركي الـ VIP لضمان الجدية التامة.\n"
        "━━━━━━━━━━━━━━"
    )
    await update.message.reply_text(msg, reply_markup=ReplyKeyboardMarkup(kb, resize_keyboard=True), parse_mode="Markdown")

# --- [ مرحلة التسجيل الذكية ] ---
async def start_reg(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "بدأنا التسجيل.. هل أنت (ذكر 👨) أم (أنثى 👩)؟", 
        reply_markup=ReplyKeyboardMarkup([["ذكر 👨", "أنثى 👩"], ["إلغاء ❌"]], resize_keyboard=True, one_time_keyboard=True)
    )
    return GENDER

async def set_gender(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data['m_gender'] = update.message.text
    # استخدام ReplyKeyboardRemove لإخفاء أزرار الجنس فوراً
    await update.message.reply_text(f"تم اختيار {update.message.text}. الآن كم عمرك؟ (أرقام فقط)", reply_markup=ReplyKeyboardRemove())
    return AGE

async def invalid_age(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("❌ خطأ! يرجى إدخال العمر بالأرقام فقط (مثال: 25).")
    return AGE

async def set_age(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data['m_age'] = update.message.text
    await update.message.reply_text("من أي دولة أنت؟")
    return COUNTRY

async def set_country(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data['m_country'] = update.message.text
    await update.message.reply_text("اكتب نبذة عنك وماذا تطلب في شريك حياتك:")
    return BIO

async def set_bio(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    data = context.user_data
    bio = update.message.text
    
    with db.get_cursor() as cur:
        # إنشاء الجدول إذا لم يوجد
        cur.execute('''CREATE TABLE IF NOT EXISTS marriage_profiles 
                     (user_id INTEGER PRIMARY KEY, gender TEXT, age INTEGER, country TEXT, bio TEXT)''')
        cur.execute("INSERT OR REPLACE INTO marriage_profiles VALUES (?, ?, ?, ?, ?)", 
                    (user_id, data['m_gender'], data['m_age'], data['m_country'], bio))

    # --- إرسال للقناة ---
    channel_msg = (
        f"🆕 **طـلـب ارتبـاط جـديد**\n"
        f"━━━━━━━━━━━━━━\n"
        f"👤 الـجنس: {data['m_gender']}\n"
        f"🎂 الـعـمر: {data['m_age']}\n"
        f"🌍 الـبلد: {data['m_country']}\n"
        f"📝 الـمواصفات: {bio}\n"
        f"━━━━━━━━━━━━━━"
    )
    try: await context.bot.send_message(chat_id=MARRIAGE_CHANNEL_ID, text=channel_msg)
    except: pass

    await update.message.reply_text("✅ تم حفظ ملفك بنجاح!", reply_markup=ReplyKeyboardMarkup([[MAIN_BUTTON]], resize_keyboard=True))
    return ConversationHandler.END

# --- [ بوابة استعراض الملفات (VIP فقط) ] ---
async def browse_files_gate(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    
    with db.get_cursor() as cur:
        # التحقق من حالة VIP
        try:
            res = cur.execute("SELECT is_vip FROM users WHERE user_id = ?", (user_id,)).fetchone()
            is_vip = res['is_vip'] if res else 0
        except: is_vip = 0

    if not is_vip:
        kb = [[InlineKeyboardButton("👑 اشترك في VIP الآن", callback_data="buy_vip")],
              [InlineKeyboardButton("🌐 تصفح القناة (مجاناً)", url=GENERAL_BROWSE_URL)]]
        return await update.message.reply_text(
            "🚫 **عذراً! هذه الميزة مخصصة لمشتركي الـ VIP فقط.**\n\n"
            "اشتراك الـ VIP يمنحك القدرة على استعراض كافة الملفات والتواصل المباشر مع أصحابها داخل البوت.",
            reply_markup=InlineKeyboardMarkup(kb), parse_mode="Markdown"
        )
    
    # إذا كان VIP يبدأ الاستعراض
    await show_next_partner(update, context)

async def show_next_partner(update, context):
    user_id = update.effective_user.id
    with db.get_cursor() as cur:
        # جلب ملف عشوائي للجنس الآخر
        me = cur.execute("SELECT gender FROM marriage_profiles WHERE user_id = ?", (user_id,)).fetchone()
        target_gender = "أنثى 👩" if me and me['gender'] == "ذكر 👨" else "ذكر 👨"
        partner = cur.execute("SELECT * FROM marriage_profiles WHERE gender = ? AND user_id != ? ORDER BY RANDOM() LIMIT 1", 
                              (target_gender, user_id)).fetchone()

    if not partner:
        msg = "🧐 لا توجد ملفات جديدة حالياً.. حاول لاحقاً."
        if update.message: await update.message.reply_text(msg)
        else: await update.callback_query.edit_message_text(msg)
        return

    msg = (
        f"💎 **〖 مـلف شخصي مـقترح 〗**\n"
        f"━━━━━━━━━━━━━━\n"
        f"👤 الـجنس: {partner['gender']}\n"
        f"🎂 الـعـمر: {partner['age']}\n"
        f"🌍 الـبلد: {partner['country']}\n"
        f"📝 الـمواصفات: \n_{partner['bio']}_\n"
        f"━━━━━━━━━━━━━━"
    )
    kb = [
        [InlineKeyboardButton("💬 بدء دردشة", callback_data=f"chat_with_{partner['user_id']}")],
        [InlineKeyboardButton("➡️ الـملف التالي", callback_data="next_file")]
    ]
    
    if update.message: await update.message.reply_text(msg, reply_markup=InlineKeyboardMarkup(kb), parse_mode="Markdown")
    else: await update.callback_query.edit_message_text(msg, reply_markup=InlineKeyboardMarkup(kb), parse_mode="Markdown")

async def handle_browsing(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    if query.data == "next_file":
        await show_next_partner(update, context)

async def show_my_data(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    with db.get_cursor() as cur:
        u = cur.execute("SELECT * FROM marriage_profiles WHERE user_id = ?", (user_id,)).fetchone()
    if not u: return await update.message.reply_text("❌ لم تسجل بياناتك بعد.")
    await update.message.reply_text(f"📋 **بياناتك:**\n\nالجنس: {u['gender']}\nالعمر: {u['age']}\nالبلد: {u['country']}\nالمواصفات: {u['bio']}")

async def cancel_reg(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("تم إلغاء التسجيل.", reply_markup=ReplyKeyboardRemove())
    return ConversationHandler.END
