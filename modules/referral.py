import logging
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup, ReplyKeyboardMarkup
from telegram.ext import ContextTypes, MessageHandler, filters
from modules.pepper import PepperManager

logger = logging.getLogger(__name__)

# --- [ الإعدادات ] ---
MAIN_BUTTON = "💰 اربح فلفل مجاني"
REWARD_AMOUNT = 40  # المكافأة لكل صديق

# ذاكرة لتجنب احتساب نفس الصديق مرتين
# {inviter_id: [invited_user_ids]}
referral_history = {}

async def setup(application):
    # زر القائمة الرئيسية
    application.add_handler(MessageHandler(filters.Regex(f"^{MAIN_BUTTON}$"), show_referral_menu))

async def show_referral_menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """عرض صفحة الربح ورابط الدعوة"""
    user_id = update.effective_user.id
    bot_username = (await context.bot.get_me()).username
    
    # إنشاء رابط الدعوة الخاص بالمستخدم
    referral_link = f"https://t.me/{bot_username}?start=ref_{user_id}"
    
    # إحصائيات المستخدم
    invited_count = len(referral_history.get(user_id, []))
    total_earned = invited_count * REWARD_AMOUNT

    text = (
        f"🔥 **نظام الأرباح الهائل!** 🔥\n"
        f"━━━━━━━━━━━━━━\n"
        f"هل تريد الحصول على الكثير من الفلفل 🌶️ مجاناً؟\n\n"
        f"🎁 **العرض الحالي:**\n"
        f"ستحصل على **{REWARD_AMOUNT} فلفلة** فوراً عن كل صديق يدخل البوت عبر رابطك!\n\n"
        f"📈 **إحصائياتك:**\n"
        f"👤 عدد الأصدقاء: `{invited_count}`\n"
        f"💰 إجمالي أرباحك: `{total_earned} 🌶️`\n"
        f"━━━━━━━━━━━━━━\n"
        f"👇 **انسخ رابطك وانشره الآن:**\n"
        f"`{referral_link}`"
    )

    # زر للمشاركة السريعة
    share_text = f"دخلت هذا البوت الرهيب وبدي اياك تجربه! سجل من رابطي وبنحصل هدايا: {referral_link}"
    kb = [
        [InlineKeyboardButton("🚀 مشاركة الرابط مع الأصدقاء", url=f"https://t.me/share/url?url={referral_link}&text={share_text}")],
        [InlineKeyboardButton("🏠 العودة للقائمة", callback_data="back_to_main")]
    ]
    
    await update.message.reply_text(text, reply_markup=InlineKeyboardMarkup(kb), parse_mode="Markdown")

async def process_referral(update: Update, context: ContextTypes.DEFAULT_TYPE, inviter_id: int):
    """دالة معالجة الإحالة عند دخول عضو جديد (يتم استدعاؤها من موديول الـ Start)"""
    new_user_id = update.effective_user.id
    
    # التأكد أن المستخدم لا يدعو نفسه وأن الصديق لم يسبق دعوته
    if inviter_id == new_user_id:
        return

    # التحقق من أن الصديق لم يدخل البوت من قبل عبر أي رابط
    # ملاحظة: في النسخ الاحترافية نتحقق من قاعدة البيانات
    all_invited = [uid for sublist in referral_history.values() for uid in sublist]
    
    if new_user_id not in all_invited:
        if inviter_id not in referral_history:
            referral_history[inviter_id] = []
        
        referral_history[inviter_id].append(new_user_id)
        
        # إضافة المكافأة (40 فلفلة)
        PepperManager.update_balance(inviter_id, REWARD_AMOUNT)
        
        # إرسال تنبيه حماسي للشخص الذي قام بالدعوة
        try:
            await context.bot.send_message(
                chat_id=inviter_id,
                text=f"🎊 **خبر سعيد!**\n\n"
                     f"صديقك المبدع انضم للبوت عبر رابطك.\n"
                     f"تم إضافة **{REWARD_AMOUNT} 🌶️** إلى رصيدك فوراً!\n"
                     f"استمر في المشاركة لزيادة أرباحك.",
                parse_mode="Markdown"
            )
        except Exception as e:
            logger.error(f"Could not send reward notification: {e}")
