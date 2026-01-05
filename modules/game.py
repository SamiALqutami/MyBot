import logging
import random
import asyncio
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup, ReplyKeyboardMarkup, ReplyKeyboardRemove
from telegram.ext import ContextTypes, CallbackQueryHandler, MessageHandler, filters
from modules.pepper import PepperManager

logger = logging.getLogger(__name__)

# الأزرار الرئيسية
MAIN_BUTTON = "🎮 عالم الألعاب المطورة"
EXIT_GAMES = "🚫 مغادرة الألعاب"

# مخازن الألعاب
xo_waiting = []
guess_waiting = []
active_games = {}

async def setup(application):
    application.add_handler(MessageHandler(filters.Regex(f"^{MAIN_BUTTON}$"), games_menu))
    application.add_handler(MessageHandler(filters.Regex(f"^{EXIT_GAMES}$"), exit_games))
    # الطريقة الذكية: استخدام نمط Regex واسع لالتقاط كل حركات الألعاب
    application.add_handler(CallbackQueryHandler(handle_game_logic, pattern=".*"))
    # استقبال أرقام التخمين
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND & ~filters.Regex(f"^{EXIT_GAMES}$"), handle_guess_input), group=4)

async def games_menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    kb = [
        [InlineKeyboardButton("❌⭕ تحدي XO الشفاف", callback_data="join_xo")],
        [InlineKeyboardButton("🔢 تحدي التخمين الثنائي", callback_data="join_guess")]
    ]
    await update.message.reply_text(
        "🎮 **مرحباً بك في ساحة الألعاب!**\n🏆 الفوز +10 🌶️ | الخسارة -3 إلى -5 🌶️",
        reply_markup=InlineKeyboardMarkup(kb), parse_mode="Markdown"
    )

# --- [ قسم لعبة XO المطورة بذكاء ] ---

def generate_big_board(game_id, board):
    buttons = []
    for i in range(0, 9, 3):
        row = []
        for j in range(i, i+3):
            # استخدام مساحات شفافة ضخمة لزيادة دقة اللمس
            label = board[j] if board[j] != "" else " ( ㅤ ) " 
            row.append(InlineKeyboardButton(label, callback_data=f"xo_{game_id}_{j}"))
        buttons.append(row)
    return InlineKeyboardMarkup(buttons)

async def start_xo(context, p1, p2):
    game_id = f"{random.randint(100, 999)}" # آيدي قصير وذكي
    active_games[game_id] = {
        "p1": p1, "p2": p2, "type": "xo",
        "p1_name": (await context.bot.get_chat(p1)).first_name,
        "p2_name": (await context.bot.get_chat(p2)).first_name,
        "board": [""] * 9, "turn": p1, "msgs": {}
    }
    g = active_games[game_id]
    kb = generate_big_board(game_id, g["board"])
    for p in [p1, p2]:
        txt = "🟢 دورك الآن!" if p == p1 else f"⌛ دور: {g['p1_name']}"
        msg = await context.bot.send_message(p, f"🕹 **تحدي XO**\n{txt}", reply_markup=kb, parse_mode="Markdown")
        g["msgs"][p] = msg.message_id

async def handle_game_logic(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer() # فك تعليق الزر فوراً
    user_id = query.from_user.id
    data = query.data

    if data == "join_xo":
        if user_id not in xo_waiting:
            xo_waiting.append(user_id)
            await query.edit_message_text("🔎 جاري البحث عن خصم...")
            if len(xo_waiting) >= 2: await start_xo(context, xo_waiting.pop(0), xo_waiting.pop(0))

    elif data.startswith("xo_"):
        _, game_id, idx = data.split("_")
        g = active_games.get(game_id)
        if not g or g["turn"] != user_id: return
        idx = int(idx)
        if g["board"][idx] != "": return

        g["board"][idx] = "❌" if user_id == g["p1"] else "⭕"
        win = check_winner(g["board"])
        
        if win:
            await finish_xo(context, game_id, win)
        else:
            g["turn"] = g["p2"] if user_id == g["p1"] else g["p1"]
            kb = generate_big_board(game_id, g["board"])
            for p in [g["p1"], g["p2"]]:
                name = g["p1_name"] if g["turn"] == g["p1"] else g["p2_name"]
                status = "🟢 دورك!" if p == g["turn"] else f"⌛ دور: {name}"
                try: await context.bot.edit_message_text(chat_id=p, message_id=g["msgs"][p], text=f"🕹 **تحدي XO**\n{status}", reply_markup=kb, parse_mode="Markdown")
                except: pass

    elif data == "join_guess":
        if user_id not in guess_waiting:
            guess_waiting.append(user_id)
            await query.edit_message_text("🔎 جاري البحث عن خصم للتخمين...")
            if len(guess_waiting) >= 2:
                p1, p2 = guess_waiting.pop(0), guess_waiting.pop(0)
                gid = f"g_{random.randint(10, 99)}"
                active_games[gid] = {"p1": p1, "p2": p2, "type": "guess", "secret": random.randint(1, 100), "turn": p1}
                for p in [p1, p2]: await context.bot.send_message(p, "🔢 **بدأ التحدي!** خمن رقم 1-100.\nالمحاولات لا نهائية.", reply_markup=ReplyKeyboardMarkup([[EXIT_GAMES]], resize_keyboard=True))

def check_winner(b):
    w = [(0,1,2), (3,4,5), (6,7,8), (0,3,6), (1,4,7), (2,5,8), (0,4,8), (2,4,6)]
    for pos in w:
        if b[pos[0]] == b[pos[1]] == b[pos[2]] != "": return b[pos[0]]
    return "draw" if "" not in b else None

async def finish_xo(context, game_id, res):
    g = active_games.pop(game_id)
    if res == "draw": txt = "🤝 تعادل!"
    else:
        win = g["p1"] if res == "❌" else g["p2"]
        lose = g["p2"] if res == "❌" else g["p1"]
        PepperManager.update_balance(win, 10); PepperManager.update_balance(lose, -3)
        txt = f"🎉 فاز {g['p1_name'] if win==g['p1'] else g['p2_name']}!\n🏆 +10 🌶️ | 📉 -3 🌶️"
    for p in [g["p1"], g["p2"]]: await context.bot.send_message(p, txt, reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔄 إعادة", callback_data="join_xo")]]))

# --- [ قسم التخمين المطور ] ---

async def handle_guess_input(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    if not update.message.text.isdigit(): return
    gid = next((k for k,v in active_games.items() if v.get("type") == "guess" and (v["p1"] == user_id or v["p2"] == user_id)), None)
    if not gid: return
    g = active_games[gid]
    if user_id != g["turn"]: 
        await update.message.reply_text("⌛ انتظر دورك!"); return
    
    val = int(update.message.text)
    partner = g["p2"] if user_id == g["p1"] else g["p1"]
    if val == g["secret"]:
        PepperManager.update_balance(user_id, 10); PepperManager.update_balance(partner, -5)
        active_games.pop(gid)
        for p in [g["p1"], g["p2"]]: await context.bot.send_message(p, f"🎊 {update.effective_user.first_name} وجد الرقم {val}!\n🏆 +10 🌶️", reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔄 إعادة", callback_data="join_guess")]]))
    else:
        g["turn"] = partner
        hint = "أكبر ⬆️" if val < g["secret"] else "أصغر ⬇️"
        p_name = (await context.bot.get_chat(partner)).first_name
        for p in [g["p1"], g["p2"]]: await context.bot.send_message(p, f"📥 {update.effective_user.first_name}: `{val}` ({hint})\n🟢 دور: {p_name}")

async def exit_games(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("🛑 تم الخروج.", reply_markup=ReplyKeyboardRemove())
