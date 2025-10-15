from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ApplicationBuilder, CommandHandler, CallbackQueryHandler, ContextTypes
from apscheduler.schedulers.background import BackgroundScheduler
from datetime import datetime, time, timedelta
import os

TOKEN = os.environ.get("BOT_TOKEN")

scheduler = BackgroundScheduler()
scheduler.start()

user_states = {}
START_TIME = time(7, 30)
END_TIME = time(23, 59)
INTERVAL = timedelta(hours=1, minutes=30)
REPEAT_DELAY = 10  # минут

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_id = update.effective_chat.id
    user_states[chat_id] = {"waiting_ack": False}
    await update.message.reply_text(
        "Привет, Настюша! 💧 Я создал бота который будет напоминать тебе пить воду каждые 1,5 часа "
        "с 7:30 до 00:00)"
    )
    schedule_daily_reminders(chat_id, context)

def schedule_daily_reminders(chat_id, context):
    now = datetime.now()
    today_start = datetime.combine(now.date(), START_TIME)
    current = today_start
    while current.time() <= END_TIME:
        scheduler.add_job(
            send_reminder,
            "date",
            run_date=current,
            args=[chat_id, context],
            id=f"{chat_id}_{current.strftime('%H%M')}",
            replace_existing=True
        )
        current += INTERVAL
    scheduler.add_job(
        schedule_daily_reminders,
        "date",
        run_date=datetime.combine(now.date() + timedelta(days=1), time(0, 0)),
        args=[chat_id, context],
        id=f"reschedule_{chat_id}",
        replace_existing=True
    )

async def send_reminder(chat_id, context):
    now = datetime.now().time()
    if not (START_TIME <= now <= END_TIME):
        return
    state = user_states.get(chat_id, {"waiting_ack": False})
    if state.get("waiting_ack"):
        await context.bot.send_message(
            chat_id=chat_id,
            text="⏰Солнце, ты ещё не выпила воду! Не забудь 💧",
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton("Я выпила 💦", callback_data="drank_water")]
            ])
        )
        return
    user_states[chat_id]["waiting_ack"] = True
    keyboard = InlineKeyboardMarkup([
        [InlineKeyboardButton("Я выпила 💦", callback_data="drank_water")]
    ])
    await context.bot.send_message(chat_id=chat_id, text="💧 Бусинка, пора выпить воды!", reply_markup=keyboard)
    scheduler.add_job(
        repeat_reminder,
        "date",
        run_date=datetime.now() + timedelta(minutes=REPEAT_DELAY),
        args=[chat_id, context],
        id=f"repeat_{chat_id}",
        replace_existing=True
    )

async def repeat_reminder(chat_id, context):
    state = user_states.get(chat_id)
    if state and state.get("waiting_ack"):
        await context.bot.send_message(
            chat_id=chat_id,
            text="⏰ Напоминаю: Ты всё ещё не выпила воду, уже пора(💧",
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton("Я выпила 💦", callback_data="drank_water")]
            ])
        )

async def drank_water(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    chat_id = query.message.chat.id
    if chat_id in user_states:
        user_states[chat_id]["waiting_ack"] = False
    await query.answer()
    await query.edit_message_text("✅ Оес! Умничка моя, что не забываешь пить воду 💦")

app = ApplicationBuilder().token(TOKEN).build()
app.add_handler(CommandHandler("start", start))
app.add_handler(CallbackQueryHandler(drank_water, pattern="drank_water"))

print("Бот запущен...")
app.run_polling()
