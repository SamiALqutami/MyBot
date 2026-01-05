import asyncio
import random
import logging
from telegram import Update, ReplyKeyboardMarkup, ReplyKeyboardRemove
from telegram.ext import ContextTypes, MessageHandler, filters
from modules.pepper import PepperManager

logger = logging.getLogger(__name__)

# --- الإعدادات والأسماء ---
MAIN_BUTTON = "🏠 غرف الدردشة"
JOIN_PUBLIC_ROOM = "انضمام إلى الغرفة العامة 🌍"
JOIN_FUN_ROOM = "انضمام إلى غرفة المرح 🍓"
EXIT_BUTTON = "إيقاف المحادثة 🛑"
CREATE_ROOM_CMD = "إضافة غرفة ➕"
PROMOTE_CMD = "ترقية مشرف 🏆"

# --- قاعدة البيانات المؤقتة ---
rooms_db = {
    "العامة 🌍": {"users": set()},
    "المرح 🍓": {"users": set()}
}
user_session = {}    # {user_id: room_name}
user_nicks = {}      # {user_id: nickname}
user_state = {}      # {user_id: state}

BOT_ACTORS = ["سلا 💝", "فاطمة 🌸"]
BOT_PHRASES = ["منورين يا جماعة 😍", "كيفكم؟ أنا سلا", "فاطمة: هلا وغلا بالكل", "منورين بنقاطكم الفلفلية 🌶️"]

async def setup(application):
    # معالج القائمة الرئيسية
    application.add_handler(MessageHandler(filters.Regex(f"^{MAIN_BUTTON}$"), start_rooms))
    
    # معالجات الانضمام (أزرار أسفل الشاشة)
    application.add_handler(MessageHandler(filters.Regex(f"^{JOIN_PUBLIC_ROOM}$"), lambda u, c: set_joining_state(u, c, "العامة 🌍")))
    application.add_handler(MessageHandler(filters.Regex(f"^{JOIN_FUN_ROOM}$"), lambda u, c: set_joining_state(u, c, "المرح 🍓")))
    
    # معالجات الوظائف الأخرى
    application.add_handler(MessageHandler(filters.Regex(f"^{CREATE_ROOM_CMD}$"), create_room_info))
    application.add_handler(MessageHandler(filters.Regex(f"^{PROMOTE_CMD}$"), promote_info))
    application.add_handler(MessageHandler(filters.Regex(f"^{EXIT_BUTTON}$"), exit_room))
    
    # المحرك الرئيسي للمعالجة (الأسماء والدردشة)
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND & ~filters.Regex(f"^{EXIT_BUTTON}$"), main_processor), group=2)

# --- [ القوائم ] ---

async def start_rooms(update: Update, context: ContextTypes.DEFAULT_TYPE):
    # عرض الأزرار بالأسفل بدلاً من الأزرار المضمنة لضمان الاستجابة
    kb = [
        [JOIN_PUBLIC_ROOM, JOIN_FUN_ROOM],
        [CREATE_ROOM_CMD, PROMOTE_CMD]
    ]
    await update.message.reply_text(
        "✨ **مرحباً بك في غرف الدردشة**\nاختر الغرفة التي تود دخولها من الأزرار بالأسفل:",
        reply_markup=ReplyKeyboardMarkup(kb, resize_keyboard=True), parse_mode="Markdown"
    )

async def set_joining_state(update: Update, context: ContextTypes.DEFAULT_TYPE, room_name: str):
    user_id = update.effective_user.id
    user_state[user_id] = f"wait_nick_{room_name}"
    await update.message.reply_text(
        f"📝 **دخول {room_name}**\nأرسل الآن اسمك المستعار الذي تود الظهور به:",
        reply_markup=ReplyKeyboardRemove() # إخفاء الأزرار مؤقتاً لكتابة الاسم
    )

# --- [ المحرك الرئيسي ] ---

async def main_processor(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    text = update.message.text
    state = user_state.get(user_id, "")

    # 1. حالة تسجيل الاسم المستعار
    if state.startswith("wait_nick_"):
        room_name = state.replace("wait_nick_", "")
        user_nicks[user_id] = text
        user_session[user_id] = room_name
        rooms_db[room_name]["users"].add(user_id)
        user_state.pop(user_id)

        await update.message.reply_text(
            f"✅ تم دخولك باسم: **{text}**\nيمكنك البدء بالدردشة الآن!",
            reply_markup=ReplyKeyboardMarkup([[EXIT_BUTTON]], resize_keyboard=True)
        )
        await broadcast(context, room_name, f"💖 انضم المستعار: **{text}**", user_id)
        return

    # 2. منطق الدردشة داخل الغرف
    if user_id in user_session:
        room = user_session[user_id]
        nick = user_nicks.get(user_id, "مجهول")
        final_msg = f"👤 **{nick}**:\n{text}"
        
        await broadcast(context, room, final_msg, user_id)
        # تحريك المستخدمين الوهميين
        asyncio.create_task(dummy_chat_logic(context, room))

# --- [ الوظائف المساعدة ] ---

async def broadcast(context, room_name, msg, exclude_id):
    if room_name in rooms_db:
        for member in list(rooms_db[room_name]["users"]):
            if member != exclude_id:
                try: await context.bot.send_message(member, msg, parse_mode="Markdown")
                except: rooms_db[room_name]["users"].discard(member)

async def exit_room(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    if user_id in user_session:
        room = user_session.pop(user_id)
        nick = user_nicks.pop(user_id, "مستخدم")
        rooms_db[room]["users"].discard(user_id)
        await update.message.reply_text("🛑 تم الخروج بنجاح.")
        await broadcast(context, room, f"🚶 غادر المستعار: **{nick}**", user_id)
    await start_rooms(update, context)

async def dummy_chat_logic(context, room_name):
    await asyncio.sleep(8)
    if room_name in rooms_db and rooms_db[room_name]["users"]:
        name = random.choice(BOT_ACTORS)
        msg = random.choice(BOT_PHRASES)
        await broadcast(context, room_name, f"👤 **{name}**:\n{msg}", None)

async def create_room_info(update: Update, context: ContextTypes.DEFAULT_TYPE):
    bot_info = await context.bot.get_me()
    link = f"https://t.me/{bot_info.username}?start=room_{update.effective_user.id}"
    await update.message.reply_text(f"➕ **إنشاء غرفة خاصة**\nادعُ 15 شخصاً عبر رابطك:\n`{link}`", parse_mode="Markdown")

async def promote_info(update: Update, context: ContextTypes.DEFAULT_TYPE):
    bot_info = await context.bot.get_me()
    link = f"https://t.me/{bot_info.username}?start=admin_{update.effective_user.id}"
    await update.message.reply_text(f"🏆 **طلب إشراف**\nادعُ 5 أشخاص عبر رابطك:\n`{link}`", parse_mode="Markdown")
