import os
import importlib
import logging
import asyncio
from telegram import Update, ReplyKeyboardMarkup
from telegram.ext import Application, CommandHandler, ContextTypes
from config import Config

# إعداد السجلات
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

async def auto_load_modules(application):
    """محرك اكتشاف الأنظمة وتسجيل الأزرار تلقائياً"""
    base_dir = os.path.dirname(os.path.abspath(__file__))
    modules_dir = os.path.join(base_dir, "modules")

    if not os.path.exists(modules_dir):
        os.makedirs(modules_dir)
        return

    # مسح الأزرار القديمة عند إعادة التشغيل لضمان التحديث
    Config.DYNAMIC_BUTTONS = {}

    for filename in os.listdir(modules_dir):
        if filename.endswith(".py") and filename != "__init__.py":
            module_name = f"modules.{filename[:-3]}"
            try:
                # استيراد الموديول برمجياً
                module = importlib.import_module(module_name)
                
                # تسجيل الزر الرئيسي إذا كان معرفاً داخل الملف
                if hasattr(module, 'MAIN_BUTTON'):
                    Config.DYNAMIC_BUTTONS[module_name] = module.MAIN_BUTTON
                
                # تشغيل دالة الربط setup
                if hasattr(module, 'setup'):
                    await module.setup(application)
                    logger.info(f"✅ تم ربط: {filename}")
            except Exception as e:
                logger.error(f"❌ خطأ في تحميل {filename}: {e}")

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """عرض القائمة الرئيسية المبنية ديناميكياً من الموديولات"""
    all_buttons = list(Config.DYNAMIC_BUTTONS.values())
    
    # تقسيم الأزرار (2 في كل سطر)
    keyboard = [all_buttons[i:i+2] for i in range(0, len(all_buttons), 2)]
    
    # إضافة أزرار ثابتة للبوت
    
    
    reply_markup = ReplyKeyboardMarkup(keyboard, resize_keyboard=True)
    await update.message.reply_text(
        "🚀 أهلاً بك! تم تحديث جميع الأنظمة تلقائياً.\nاختر من القائمة المتاحة:",
        reply_markup=reply_markup
    )

async def run_bot():
    """تشغيل المحرك"""
    if "ضع_التوكن" in Config.BOT_TOKEN:
        print("❌ خطأ: يرجى وضع التوكن الصحيح في ملف config.py")
        return

    app = Application.builder().token(Config.BOT_TOKEN).build()
    app.add_handler(CommandHandler("start", start))

    # الأتمتة: تحميل كل موديول موجود في المجلد
    await auto_load_modules(app)

    print("📡 البوت يعمل الآن.. جرب إرسال /start")
    await app.initialize()
    await app.start()
    await app.updater.start_polling()
    while True: await asyncio.sleep(1)

if __name__ == "__main__":
    try:
        asyncio.run(run_bot())
    except Exception as e:
        print(f"🛑 حدث خطأ أثناء التشغيل: {e}")
