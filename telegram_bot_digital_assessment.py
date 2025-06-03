# telegram_bot_digital_assessment.py

import sqlite3
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup, ReplyKeyboardRemove
from telegram.ext import ApplicationBuilder, CommandHandler, CallbackQueryHandler, MessageHandler, filters, ContextTypes, ConversationHandler

TOKEN

# States
(ASK_Q, GET_PHONE) = range(2)

# Questions and options
questions = [
    ("تعداد کارمندان فعال شما چقدر است؟", [("1–5 نفر", 1), ("6–25 نفر", 2), ("26 نفر به بالا", 3)]),
    ("گردش مالی سالانه شما چقدر است؟ (تومان)", [("کمتر از ۱۰۰ میلیون", 1), ("۱۰۰ تا ۵۰۰ میلیون", 2), ("بیش از ۵۰۰ میلیون", 3)]),
    ("مهم‌ترین هدف دیجیتال شما چیست؟", [("نامشخص", 0), ("یک هدف کلی", 1), ("چند هدف با KPI مشخص", 2)]),

    ("وضعیت وب‌سایت شما چگونه است؟", [("ندارم", 0), ("ساده/غیرواکنش‌گرا", 1), ("واکنش‌گرا با فروش", 2), ("یکپارچه با CRM", 3)]),
    ("از چه ابزارهایی برای مدیریت مشتریان استفاده می‌کنید؟", [("هیچ", 0), ("تلگرام/ایمیل", 1), ("نرم‌افزار پایه", 2), ("CRM حرفه‌ای", 3)]),
    ("آیا از پرداخت آنلاین استفاده می‌کنید؟", [("خیر", 0), ("درگاه ساده", 1), ("یکپارچه با سایت", 2)]),

    ("کانال‌های اجتماعی فعال شما کدامند؟", [("ندارم", 0), ("۱ کانال با فعالیت نامنظم", 1), ("۲+ کانال منظم", 2), ("استراتژی چندکاناله با تعامل بالا", 3)]),
    ("تجربه تبلیغات آنلاین چگونه است؟", [("هیچ", 0), ("تست کوتاه", 1), ("کمپین فعال", 2), ("بهینه‌سازی شده", 3)]),
    ("وضعیت تحلیل داده؟", [("ندارم", 0), ("نصب شده اما بدون بررسی", 1), ("گزارش ماهانه", 2), ("داشبورد یکپارچه", 3)]),

    ("بودجه ماهانه دیجیتال مارکتینگ چقدر است؟", [("نامشخص", 0), ("<۵ میلیون", 1), ("۵–۲۰ میلیون", 2), (">۲۰ میلیون", 3)]),
    ("درصد فروش وابسته به دیجیتال؟", [("<۲۰%", 0), ("۲۰–۵۰%", 1), (">۵۰%", 2)]),
    ("آیا از اتوماسیون استفاده می‌کنید؟", [("خیر", 0), ("اطلاع‌رسانی ساده", 1), ("اتوماسیون چندکاناله", 2), ("یکپارچه با CRM", 3)]),
]

# SQLite setup
conn = sqlite3.connect("assessment.db")
c = conn.cursor()
c.execute("""
CREATE TABLE IF NOT EXISTS responses (
    phone TEXT PRIMARY KEY,
    answers TEXT,
    score INTEGER
)
""")
conn.commit()
conn.close()

user_data = {}

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "سلام! برای شروع ارزیابی آمادگی دیجیتال روی دکمه زیر کلیک کنید.",
        reply_markup=InlineKeyboardMarkup([
            [InlineKeyboardButton("شروع ارزیابی", callback_data="start_assessment")]
        ])
    )

async def start_assessment(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    user_data[query.from_user.id] = {"current_q": 0, "score": 0, "answers": []}
    return await ask_question(query.message.chat_id, context)

async def ask_question(chat_id, context):
    user = user_data[chat_id]
    q_index = user["current_q"]
    if q_index < len(questions):
        q_text, options = questions[q_index]
        buttons = [[InlineKeyboardButton(opt[0], callback_data=str(i))] for i, opt in enumerate(options)]
        await context.bot.send_message(chat_id=chat_id, text=q_text, reply_markup=InlineKeyboardMarkup(buttons))
        return ASK_Q
    else:
        await context.bot.send_message(chat_id=chat_id, text="لطفاً شماره تماس خود را وارد کنید:")
        return GET_PHONE

async def handle_answer(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    user = user_data[query.from_user.id]
    q_index = user["current_q"]
    _, options = questions[q_index]
    selected = int(query.data)
    user["answers"].append(options[selected][0])
    user["score"] += options[selected][1]
    user["current_q"] += 1
    return await ask_question(query.from_user.id, context)

async def save_phone(update: Update, context: ContextTypes.DEFAULT_TYPE):
    phone = update.message.text
    uid = update.message.from_user.id
    user = user_data.get(uid)
    if not user:
        await update.message.reply_text("خطا در ذخیره‌سازی. لطفاً مجدداً شروع کنید.")
        return ConversationHandler.END

    conn = sqlite3.connect("assessment.db")
    c = conn.cursor()
    try:
        c.execute("INSERT INTO responses (phone, answers, score) VALUES (?, ?, ?)",
                  (phone, str(user["answers"]), user["score"]))
        conn.commit()
    except sqlite3.IntegrityError:
        await update.message.reply_text("شما قبلاً این پرسشنامه را تکمیل کرده‌اید.")
        return ConversationHandler.END
    finally:
        conn.close()

    # Determine result
    score = user["score"]
    if score <= 10:
        level = "مبتدی"
        gift = "📚 آموزش پایه دیجیتال + 📞 ۱۵ دقیقه مشاوره رایگان"
    elif score <= 20:
        level = "در حال رشد"
        gift = "🔍 بررسی SEO + 📅 تمپلیت برنامه‌ریزی محتوا"
    elif score <= 28:
        level = "پیشرفته"
        gift = "📊 ابزار تحلیل رقبا ۱ ماه رایگان + 🎤 جلسه استراتژی"
    else:
        level = "حرفه‌ای"
        gift = "🚀 مشاوره ۲ ساعته + 📈 گزارش تحلیلی سفارشی"

    await update.message.reply_text(f"✅ سطح شما: {level}\n🎁 هدیه شما: {gift}")
    return ConversationHandler.END

if __name__ == '__main__':
    app = ApplicationBuilder().token(TOKEN).build()

    conv_handler = ConversationHandler(
        entry_points=[CommandHandler("start", start)],
        states={
            ASK_Q: [CallbackQueryHandler(handle_answer)],
            GET_PHONE: [MessageHandler(filters.TEXT & ~filters.COMMAND, save_phone)],
        },
        fallbacks=[]
    )

    app.add_handler(conv_handler)
    app.add_handler(CallbackQueryHandler(start_assessment, pattern="start_assessment"))
    print("Bot is running...")
    app.run_polling()
