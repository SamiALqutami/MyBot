import time
import logging
from telegram import Update, ReplyKeyboardMarkup
from telegram.ext import ContextTypes, MessageHandler, filters
from modules.pepper import PepperManager
from modules.db_handler import get_db_connection

logger = logging.getLogger(__name__)

# --- [ الإعدادات ] ---
MAIN_BUTTON = "🎁 المكافآت والهدايا"
HOURLY_BTN = "⏳ مكافأة كل ساعة"
DAILY_BTN = "📅 مكافأة يومية"

async def setup(application):
    """الربط التلقائي بالمحرك"""
    # نستخدم Group=5 لضمان الأولوية ومنع التداخل
    application.add_handler(MessageHandler(filters.Regex(f"^{MAIN_BUTTON}$"), show_rewards_menu), group=5)
    application.add_handler(MessageHandler(filters.Regex(f"^{HOURLY_BTN}$"), claim_hourly), group=5)
    application.add_handler(MessageHandler(filters.Regex(f"^{DAILY_BTN}$"), claim_daily), group=5)
    logger.info("✅ تم تحديث موديول المكافآت (حذف زر الرجوع وتفعيل الربط بـ /start)")

# --- [ وظائف الحفظ الدائم ] ---

def get_reward_times(user_id):
    conn = get_db_connection()
    cursor = conn.cursor()
    try:
        cursor.execute("SELECT last_hourly, last_daily FROM users WHERE user_id = ?", (user_id,))
        result = cursor.fetchone()
    except Exception:
        # إضافة الأعمدة تلقائياً إذا كانت قاعدة البيانات قديمة
        cursor.execute("ALTER TABLE users ADD COLUMN last_hourly REAL DEFAULT 0")
        cursor.execute("ALTER TABLE users ADD COLUMN last_daily REAL DEFAULT 0")
        conn.commit()
        result = (0, 0)
    conn.close()
    return result if result else (0, 0)

def update_reward_time(user_id, field):
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute(f"UPDATE users SET {field} = ? WHERE user_id = ?", (time.time(), user_id))
    conn.commit()
    conn.close()

# --- [ الدوال التنفيذية ] ---

async def show_rewards_menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    # تم حذف زر الرجوع من هنا والاكتفاء بخيارات المكافآت
    kb = [[HOURLY_BTN, DAILY_BTN]]
    await update.message.reply_text(
        "🎁 **قسم المكافآت المجانية**\n\n"
        "اختر المكافأة التي تود الحصول عليها:\n"
        "• مكافأة الساعة: `3 🌶️`\n"
        "• مكافأة اليوم: `10 🌶️`\n\n"
        "💡 للعودة للقائمة الرئيسية أرسل: /start",
        reply_markup=ReplyKeyboardMarkup(kb, resize_keyboard=True),
        parse_mode="Markdown"
    )

async def claim_hourly(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    last_h, _ = get_reward_times(user_id)
    now = time.time()
    
    if now - last_h < 3600:
        rem = 3600 - (now - last_h)
        return await update.message.reply_text(
            f"⏳ **عفواً!** لم ينتهِ الوقت.\n"
            f"يرجى الانتظار: `{int(rem//60)}` دقيقة أخرى.\n\n"
            f"🏠 للرجوع: /start",
            parse_mode="Markdown"
        )

    PepperManager.update_balance(user_id, 3)
    update_reward_time(user_id, "last_hourly")
    await update.message.reply_text(
        "✅ **رائع!** حصلت على 3 🌶️ مكافأة الساعة.\n\n"
        "🏠 للعودة للقائمة الرئيسية اضغط: /start",
        parse_mode="Markdown"
    )

async def claim_daily(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    _, last_d = get_reward_times(user_id)
    now = time.time()
    
    if now - last_d < 86400:
        rem = 86400 - (now - last_d)
        return await update.message.reply_text(
            f"📅 **المكافأة اليومية** غير متاحة الآن.\n"
            f"يرجى الانتظار: `{int(rem//3600)}` ساعة.\n\n"
            f"🏠 للرجوع للقائمة: /start",
            parse_mode="Markdown"
        )

    PepperManager.update_balance(user_id, 10)
    update_reward_time(user_id, "last_daily")
    await update.message.reply_text(
        "🎊 **تهانينا!** استلمت 10 🌶️ مكافأتك اليومية.\n\n"
        "🏠 للعودة للقائمة الرئيسية اضغط: /start",
        parse_mode="Markdown"
    )
