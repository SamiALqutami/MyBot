import logging
import time
from telegram import Update, ReplyKeyboardMarkup
from telegram.ext import ContextTypes, MessageHandler, filters
from modules.pepper import PepperManager
from modules.db_handler import get_db_connection
from config import Config

logger = logging.getLogger(__name__)

# --- [ الإعدادات والزخرفة ] ---
MAIN_BUTTON = "🔮 الملف الشخصي 🔮"
EDIT_DATA_BTN = "⚙️ تعديل بياناتي"
STATS_BTN = "📊 إحصائيات المجتمع"
BALANCE_BTN = "💳 رصيدي والاشتراك"
BACK_BUTTON = "🏠 القائمة الرئيسية"

# أزرار التعديل والأسعار
EDIT_NICKNAME = "🏷️ تغيير اللقب (50 🌶️)"
EDIT_COUNTRY = "🌍 تغيير الدولة (30 🌶️)"
EDIT_AGE = "🎂 تغيير العمر (10 🌶️)"

PRICES = {"nickname": 50, "country": 30, "age": 10}

async def setup(application):
    # استخدام group=0 لضمان القوة المطلقة في الاستجابة
    application.add_handler(MessageHandler(filters.Regex(f"^{MAIN_BUTTON}$"), show_profile), group=0)
    application.add_handler(MessageHandler(filters.Regex(f"^{EDIT_DATA_BTN}$"), show_edit_menu), group=0)
    application.add_handler(MessageHandler(filters.Regex(f"^{STATS_BTN}$"), show_bot_stats), group=0)
    application.add_handler(MessageHandler(filters.Regex(f"^{BALANCE_BTN}$"), show_balance), group=0)
    application.add_handler(MessageHandler(filters.Regex(f"^{BACK_BUTTON}$"), back_to_start), group=0)
    
    # التقاط طلبات التعديل بدقة
    application.add_handler(MessageHandler(filters.Regex(r"^(🏷️|🌍|🎂)"), start_edit_flow), group=0)
    
    # خيارات التعديل (القيم)
    all_opts = [
        "الملك 👑", "الزعيم ✨", "الشبح 👻", "الكاسر ⚡", "الصقر 🦅", "الملكة 👑", "الزعيمة ✨", "الفراشة 🦋",
        "السعودية 🇸🇦", "اليمن 🇾🇪", "مصر 🇪🇬", "العراق 🇮🇶", "الإمارات 🇦🇪", "المغرب 🇲🇦", "الكويت 🇰🇼",
        "18 سنة", "22 سنة", "25 سنة", "30 سنة", "35 سنة", "40 سنة"
    ]
    application.add_handler(MessageHandler(filters.Text(all_opts), save_selection), group=0)

async def show_profile(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    conn = get_db_connection()
    user = conn.execute("SELECT * FROM users WHERE user_id = ?", (user_id,)).fetchone()
    conn.close()
    
    msg = (
        f"✨ **〖 بـطـاقـة الـتـعـريـف 〗** ✨\n"
        f"━━━━━━━━━━━━━━\n"
        f"👤 الـأسـم: `{update.effective_user.first_name}`\n"
        f"🏷️ الـلـقـب: `{user['nickname'] or 'لم يحدد 🎖️'}`\n"
        f"🌍 الـدولـة: `{user['country'] or 'غير محدد 🏴'}`\n"
        f"🎂 الـعـمـر: `{user['age'] or 'مجهول 🛡️'}`\n"
        f"━━━━━━━━━━━━━━\n"
        f"💳 الـرصـيـد: `{user['points']}` فلفلة 🌶️\n"
        f"🌟 الـحـالـة: {'💎 عضـو VIP' if user['is_vip'] else '👤 مستخدم عادي'}\n"
        f"━━━━━━━━━━━━━━"
    )
    kb = [[BALANCE_BTN, EDIT_DATA_BTN], [STATS_BTN], [BACK_BUTTON]]
    await update.message.reply_text(msg, reply_markup=ReplyKeyboardMarkup(kb, resize_keyboard=True), parse_mode="Markdown")

async def show_balance(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    conn = get_db_connection()
    user = conn.execute("SELECT points, is_vip FROM users WHERE user_id = ?", (user_id,)).fetchone()
    conn.close()
    
    stars = "⭐⭐⭐⭐⭐" if user['is_vip'] else "☆☆☆☆☆"
    vip_status = "💎 اشتراك VIP نشط" if user['is_vip'] else "🌑 حساب عادي (بدون ميزات)"
    
    msg = (
        f"💳 **〖 مـحـفـظـتـك الـرقـمـيـة 〗** 💳\n"
        f"━━━━━━━━━━━━━━\n"
        f"🌶️ رصـيـد الـفـلفـل: `{user['points']}`\n"
        f"⭐ تـقـيـيـم الـتـميـز: `{stars}`\n"
        f"━━━━━━━━━━━━━━\n"
        f"✨ **الـحـالـة:** {vip_status}\n"
        f"━━━━━━━━━━━━━━\n"
        f"💡 اشترك في VIP للحصول على ضعف الجوائز!"
    )
    await update.message.reply_text(msg, parse_mode="Markdown")

async def show_bot_stats(update: Update, context: ContextTypes.DEFAULT_TYPE):
    conn = get_db_connection()
    total_u = conn.execute("SELECT COUNT(*) FROM users").fetchone()[0]
    total_p = conn.execute("SELECT SUM(points) FROM users").fetchone()[0] or 0
    vips = conn.execute("SELECT COUNT(*) FROM users WHERE is_vip = 1").fetchone()[0]
    conn.close()
    
    msg = (
        f"📊 **〖 إحـصـائـيـات الـمـجـتـمـع 〗** 📊\n"
        f"━━━━━━━━━━━━━━\n"
        f"👥 الأعـضـاء: `{total_u}` نـبـضـة\n"
        f"💎 الـنـخـبـة: `{vips}` عـضـو VIP\n"
        f"🔥 الـفـلفـل الـمـتداول: `{total_p}` 🌶️\n"
        f"🛡️ الـنـظـام: `مـتـصـل وعـال الـجـودة ✅`\n"
        f"━━━━━━━━━━━━━━"
    )
    await update.message.reply_text(msg, parse_mode="Markdown")

async def show_edit_menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    kb = [[EDIT_NICKNAME], [EDIT_COUNTRY], [EDIT_AGE], [MAIN_BUTTON]]
    await update.message.reply_text("⚙️ **اختر القسم الذي تود تعديله:**", reply_markup=ReplyKeyboardMarkup(kb, resize_keyboard=True))

async def start_edit_flow(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    text = update.message.text
    balance = PepperManager.get_balance(user_id)
    
    field = "nickname" if "اللقب" in text else "country" if "الدولة" in text else "age"
    cost = PRICES[field]
    
    if balance < cost:
        return await update.message.reply_text(f"⚠️ رصيدك `{balance}` 🌶️ لا يكفي، تحتاج `{cost}` 🌶️.")

    context.user_data['edit_target'] = field
    
    if field == "nickname":
        kb = [["الملك 👑", "الشبح 👻", "الزعيم ✨"], ["الملكة 👑", "الزعيمة ✨", "الفراشة 🦋"], [EDIT_DATA_BTN]]
    elif field == "country":
        kb = [["السعودية 🇸🇦", "اليمن 🇾🇪", "مصر 🇪🇬"], ["العراق 🇮🇶", "الإمارات 🇦🇪", "المغرب 🇲🇦"], [EDIT_DATA_BTN]]
    else:
        kb = [["18 سنة", "22 سنة", "25 سنة"], ["30 سنة", "35 سنة", "40 سنة"], [EDIT_DATA_BTN]]
        
    await update.message.reply_text(f"⚡ اختر القيمة (سيخصم {cost} 🌶️):", reply_markup=ReplyKeyboardMarkup(kb, resize_keyboard=True))

async def save_selection(update: Update, context: ContextTypes.DEFAULT_TYPE):
    field = context.user_data.get('edit_target')
    if not field: return
    
    user_id = update.effective_user.id
    val = update.message.text
    cost = PRICES[field]
    
    PepperManager.update_balance(user_id, -cost)
    conn = get_db_connection()
    conn.execute(f"UPDATE users SET {field} = ? WHERE user_id = ?", (val, user_id))
    conn.commit()
    conn.close()
    
    context.user_data.pop('edit_target', None)
    await update.message.reply_text(f"✅ تم الحفظ بنجاح! تم خصم `{cost}` 🌶️.")
    await show_profile(update, context)

async def back_to_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    # جلب القائمة الرئيسية الأصلية ديناميكياً
    all_btns = list(Config.DYNAMIC_BUTTONS.values())
    kb = [all_btns[i:i+2] for i in range(0, len(all_btns), 2)]
    if update.effective_user.id in Config.ADMIN_IDS:
        kb.append(["🛠️ لوحة المشرف"])
    await update.message.reply_text("🏠 القائمة الرئيسية", reply_markup=ReplyKeyboardMarkup(kb, resize_keyboard=True))
