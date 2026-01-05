import logging
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes, MessageHandler, filters
from db import db
from config import Config

logger = logging.getLogger(__name__)

# الاسم الذي سيظهر في القائمة الرئيسية تلقائياً بفضل نظام الـ auto_load في main.py
MAIN_BUTTON = "👑 شخصيات VIP"

# ضع رابط قناتك هنا
VIP_CHANNEL_URL = "https://t.me/+zXF3JS4FqkQ2NDFk" 

async def setup(application):
    # ربط ضغطة الزر الرئيسي بالدالة
    application.add_handler(MessageHandler(filters.Regex(f"^{MAIN_BUTTON}$"), show_vip_promo), group=0)

async def show_vip_promo(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """عرض رسالة ترويجية مع زر الانضمام للقناة"""
    
    # رسالة عرض VIP جذابة ومزخرفة
    msg_text = (
        "👑 **〖 نـادي شـخصـيات VIP الـملكي 〗** 👑\n"
        "━━━━━━━━━━━━━━\n"
        "انضم الآن إلى النخبة واستمتع بمحتوى حصري وعالم من الإثارة لا يتوفر للجميع!\n\n"
        "✨ **مـمـيزات الانـضـمام:**\n"
        "• 🎥 مشاهدة **دردشات الـفيديو** الحية والمباشرة.\n"
        "• 🔞 الوصول إلى **الـمحتوى الـحصري** السري واليومي.\n"
        "• ⚡ أولوية في الظهور وعمليات البحث داخل البوت.\n"
        "• 🎖️ الحصول على شارة الـتميز الملكية.\n\n"
        "👇 **اضغط على الزر أدناه للانضمام فوراً عبر القناة:**\n"
        "━━━━━━━━━━━━━━"
    )

    # إنشاء الأزرار الشفافة
    keyboard = [
        [InlineKeyboardButton("🎬 دخول مـحتوى VIP الـحصري", url=VIP_CHANNEL_URL)],
        [InlineKeyboardButton("💖 غرف دردشات الـفيديو", url=VIP_CHANNEL_URL)]
    ]
    
    reply_markup = InlineKeyboardMarkup(keyboard)

    # إرسال الرسالة
    await update.message.reply_text(
        msg_text,
        reply_markup=reply_markup,
        parse_mode="Markdown",
        disable_web_page_preview=False # تفعيل معاينة الرابط إذا أردت ظهور صورة القناة
    )

    # تحديث بسيط في قاعدة البيانات (اختياري) للتسجيل أن المستخدم دخل لقسم الـ VIP
    try:
        with db.get_cursor() as cur:
            # التأكد من وجود عمود is_vip للأنظمة الأخرى
            cur.execute("UPDATE users SET is_vip = 1 WHERE user_id = ?", (update.effective_user.id,))
    except:
        pass # إذا لم يكن العمود موجوداً لا بأس، فالانضمام خارجي عبر الرابط
