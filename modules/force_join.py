import logging
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes, MessageHandler, filters, CallbackQueryHandler, ApplicationHandlerStop
from telegram.error import BadRequest, TelegramError

logger = logging.getLogger(__name__)

# --- [ الإعدادات الذكية ] ---
CHANNEL_ID = "@NN26S"
GROUP_ID = -1002235957017  # الآيدي الرقمي
GROUP_USERNAME = "@Anonymousa_Arabic"  # استخدام المعرف كخطة بديلة (Fallback)

CHANNEL_LINK = "https://t.me/NN26S"
GROUP_LINK = "https://t.me/Anonymousa_Arabic"

async def setup(application):
    application.add_handler(MessageHandler(filters.ALL & ~filters.COMMAND, enforce_subscription), group=-1)
    application.add_handler(CallbackQueryHandler(enforce_callback_sub), group=-1)
    application.add_handler(CallbackQueryHandler(verify_subscription, pattern="^check_sub$"), group=0)

async def check_membership_smart(bot, user_id):
    """طريقة ذكية للفحص تجرب الآيدي ثم المعرف"""
    # 1. تجربة الفحص عبر الآيدي الرقمي (الأسرع)
    try:
        member = await bot.get_chat_member(chat_id=GROUP_ID, user_id=user_id)
        if member.status in ['member', 'administrator', 'creator', 'restricted']:
            return True
    except Exception:
        # 2. إذا فشل، تجربة الفحص عبر اسم المستخدم للمجموعة
        try:
            member = await bot.get_chat_member(chat_id=GROUP_USERNAME, user_id=user_id)
            if member.status in ['member', 'administrator', 'creator', 'restricted']:
                return True
        except Exception as e:
            logger.error(f"فشل الفحص بكافة الطرق للمجموعة: {e}")
    return False

async def enforce_subscription(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not update.effective_user or update.effective_user.is_bot: return
    if update.message and update.message.text == "/start": return

    user_id = update.effective_user.id
    name = update.effective_user.first_name

    # التحقق من المجموعة أولاً بطريقة ذكية
    is_in_group = await check_membership_smart(context.bot, user_id)
    
    if not is_in_group:
        kb = [[InlineKeyboardButton("👥 انضم للمجموعة الآن", url=GROUP_LINK)],
              [InlineKeyboardButton("✅ تحقق من انضمامي", callback_data="check_sub")]]
        await update.message.reply_text(
            f"⚠️ **عذراً {name}!**\n\nيجب عليك الانضمام لمجموعة النقاش أولاً لتفعيل البوت.",
            reply_markup=InlineKeyboardMarkup(kb)
        )
        raise ApplicationHandlerStop

    # التحقق من القناة ثانياً
    try:
        channel_member = await context.bot.get_chat_member(chat_id=CHANNEL_ID, user_id=user_id)
        if channel_member.status not in ['member', 'administrator', 'creator', 'restricted']:
            raise Exception
    except Exception:
        kb = [[InlineKeyboardButton("📢 انضم للقناة الرسمية", url=CHANNEL_LINK)],
              [InlineKeyboardButton("✅ تحقق من انضمامي", callback_data="check_sub")]]
        await update.message.reply_text(
            f"✅ **ممتاز! بقي القليل..**\n\nلقد انضممت للمجموعة، الآن اشترك في القناة الرسمية ليفتح لك البوت بالكامل.",
            reply_markup=InlineKeyboardMarkup(kb)
        )
        raise ApplicationHandlerStop

async def enforce_callback_sub(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    if query.data == "check_sub": return
    user_id = query.from_user.id
    if not await check_membership_smart(context.bot, user_id):
        await query.answer("🚫 المحتوى مقفل! انضم للمجموعة والقناة أولاً.", show_alert=True)
        raise ApplicationHandlerStop

async def verify_subscription(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    user_id = query.from_user.id
    await query.answer("جاري التحقق دقيقة...")

    in_group = await check_membership_smart(context.bot, user_id)
    
    # فحص القناة
    in_channel = False
    try:
        c = await context.bot.get_chat_member(chat_id=CHANNEL_ID, user_id=user_id)
        in_channel = c.status in ['member', 'administrator', 'creator', 'restricted']
    except: pass

    if in_group and in_channel:
        await query.edit_message_text("✅ تم التأكيد! حسابك الآن مفعل بالكامل. أرسل /start للبدء.")
    elif not in_group:
        await query.answer("❌ ما زلت غير موجود في المجموعة! انضم وحاول مجدداً.", show_alert=True)
    else:
        await query.answer("❌ بقي عليك الاشتراك في القناة الرسمية!", show_alert=True)
