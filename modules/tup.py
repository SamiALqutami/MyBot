import logging
from telegram import Update
from telegram.ext import ContextTypes, MessageHandler, filters
from modules.db_handler import get_db_connection

logger = logging.getLogger(__name__)

# --- [ الإعدادات ] ---
MAIN_BUTTON = "المتصدرين 🏆"

async def setup(application):
    """ربط الموديول بالمحرك الرئيسي"""
    # نستخدم group=5 لضمان عدم التداخل مع أنظمة الدردشة
    application.add_handler(MessageHandler(filters.Regex(f"^{MAIN_BUTTON}$"), show_leaderboard), group=5)
    logger.info(f"✅ تم تفعيل موديول {MAIN_BUTTON} مع ميزة الإصلاح التلقائي.")

def fix_db_schema():
    """وظيفة للتأكد من وجود عمود nickname لمنع الخطأ الذي ظهر عندك"""
    conn = get_db_connection()
    cursor = conn.cursor()
    try:
        # محاولة جلب البيانات للتأكد من وجود الأعمدة
        cursor.execute("SELECT nickname FROM users LIMIT 1")
    except Exception:
        # إذا حدث خطأ (العمود غير موجود)، نقوم بإضافته فوراً
        logger.info("⚠️ عمود nickname مفقود.. جاري تحديث قاعدة البيانات...")
        cursor.execute("ALTER TABLE users ADD COLUMN nickname TEXT")
        conn.commit()
    conn.close()

async def show_leaderboard(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """جلب وعرض قائمة أغنى 10 مستخدمين"""
    # إصلاح القاعدة قبل الاستعلام
    fix_db_schema()
    
    conn = get_db_connection()
    cursor = conn.cursor()
    
    try:
        # جلب أفضل 10 مستخدمين حسب النقاط
        cursor.execute("""
            SELECT nickname, points 
            FROM users 
            ORDER BY points DESC 
            LIMIT 10
        """)
        top_users = cursor.fetchall()
    except Exception as e:
        logger.error(f"خطأ في قاعدة البيانات: {e}")
        return await update.message.reply_text("❌ حدث خطأ أثناء جلب البيانات.")
    finally:
        conn.close()

    if not top_users:
        return await update.message.reply_text("📭 القائمة فارغة حالياً!")

    # بناء نص القائمة (نقاط 🔛 اسم) كما طلبت
    leader_text = "🏆 **قائمة المتصدرين (أعلى 10)**\n"
    leader_text += "━━━━━━━━━━━━━━\n\n"
    
    medals = ["🥇", "🥈", "🥉", "👤", "👤", "👤", "👤", "👤", "👤", "👤"]
    
    for i, user in enumerate(top_users):
        # معالجة الاسم إذا كان فارغاً
        name = user['nickname'] if user['nickname'] else f"مستخدم {i+1}"
        points = user['points']
        medal = medals[i]
        
        # التنسيق المطلوب: نقاط 🔛 اسم
        leader_text += f"{medal} `{points}` 🔛 {name}\n"
    
    leader_text += "\n━━━━━━━━━━━━━━\n"
    leader_text += "🏠 للعودة أرسل: /start"

    await update.message.reply_text(leader_text, parse_mode="Markdown")
