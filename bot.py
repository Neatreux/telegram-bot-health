import os
import datetime
import csv
import pathlib
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    ApplicationBuilder,
    CommandHandler,
    CallbackQueryHandler,
    ContextTypes,
)

# ====== НАСТРОЙКИ ======
TOKEN = "8223330413:AAHDgNxy29Qy_Fd1_wOuJIEIprSNjEjjAhE"
CHAT_ID = 5886734154
LOG_FILE = "data/daily_log.csv"

# ====== ПАПКА И CSV ======
pathlib.Path("data").mkdir(exist_ok=True)
if not os.path.exists(LOG_FILE):
    with open(LOG_FILE, "w", newline="") as f:
        writer = csv.writer(f)
        writer.writerow(["Дата", "Время", "Вопрос", "Ответ"])

# ====== КНОПКИ ======
buttons_work = [
    [
        InlineKeyboardButton("Сделал ✅", callback_data="done"),
        InlineKeyboardButton("Пропустил ❌", callback_data="skip"),
        InlineKeyboardButton("Делаю ⏳", callback_data="doing"),
    ],
    [
        InlineKeyboardButton("Остановить работу 🛑", callback_data="stop_work")
    ]
]

buttons_evening = [
    [
        InlineKeyboardButton("Сделал ✅", callback_data="done"),
        InlineKeyboardButton("Пропустил ❌", callback_data="skip"),
        InlineKeyboardButton("Делаю ⏳", callback_data="doing"),
    ],
    [
        InlineKeyboardButton("Выключить вечер сегодня 🌙", callback_data="stop_evening")
    ]
]

# ====== ЛОГИРОВАНИЕ ======
def log_response(question, answer):
    now = datetime.datetime.now()
    with open(LOG_FILE, "a", newline="") as f:
        writer = csv.writer(f)
        writer.writerow([
            now.date(),
            now.time().strftime("%H:%M:%S"),
            question,
            answer
        ])

# ====== КОМАНДЫ ======
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "Привет 👋\n"
        "Нажми /work чтобы запустить рабочий блок."
    )

# ====== РАБОЧИЙ БЛОК ======
async def start_work(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "Рабочий блок активирован ✅\n"
        "Буду напоминать о разминке и воде каждый час."
    )

    context.job_queue.run_repeating(
        remind_work,
        interval=3600,
        first=0,
        name="work_block"
    )

async def remind_work(context: ContextTypes.DEFAULT_TYPE):
    now = datetime.datetime.now()
    if now.hour == 13:
        text = "🍽 Время обеда!"
    else:
        text = "⏰ Время размяться и выпить воды!"
    await context.bot.send_message(
        chat_id=CHAT_ID,
        text=text,
        reply_markup=InlineKeyboardMarkup(buttons_work)
    )

# ====== ВЕЧЕРНИЙ БЛОК ======
async def start_evening_auto(context: ContextTypes.DEFAULT_TYPE):
    context.job_queue.run_repeating(
        remind_evening,
        interval=1800,  # каждые 30 минут
        first=0,
        name="evening_block"
    )

async def stop_evening_auto(context: ContextTypes.DEFAULT_TYPE):
    evening_jobs = context.job_queue.get_jobs_by_name("evening_block")
    for job in evening_jobs:
        job.schedule_removal()

async def remind_evening(context: ContextTypes.DEFAULT_TYPE):
    now = datetime.datetime.now()
    if now.hour >= 22:
        text = "🐕 Время вечерней прогулки с собакой!"
    elif now.hour >= 21:
        text = "🧘 Сделай лёгкую растяжку"
    else:
        text = "💧 Проверь воду перед сном"
    await context.bot.send_message(
        chat_id=CHAT_ID,
        text=text,
        reply_markup=InlineKeyboardMarkup(buttons_evening)
    )

# ====== ОБРАБОТКА КНОПОК ======
async def button(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    answer = query.data
    question = query.message.text

    # --- Остановка блоков ---
    if answer == "stop_work":
        jobs = context.job_queue.get_jobs_by_name("work_block")
        for job in jobs:
            job.schedule_removal()
        await query.edit_message_text("Рабочий блок остановлен 🛑")
        log_response("Рабочий блок остановлен", "Да")
        return

    if answer == "stop_evening":
        jobs = context.job_queue.get_jobs_by_name("evening_block")
        for job in jobs:
            job.schedule_removal()
        await query.edit_message_text("Вечер сегодня отключён 🌙")
        log_response("Вечер отключён", "Да")
        return

    # --- Обычные ответы ---
    if answer == "done":
        log_response(question, "Сделал")
        await query.edit_message_text(f"{question}\nОтвет: Сделал ✅")
    elif answer == "skip":
        log_response(question, "Пропустил")
        await query.edit_message_text(f"{question}\nОтвет: Пропустил ❌")
    elif answer == "doing":
        log_response(question, "Делаю")
        context.job_queue.run_once(
            remind_repeat,
            900,
            data={"question": question}
        )
        await query.edit_message_text(f"{question}\nОтвет: Делаю ⏳ (повтор через 15 минут)")

# ====== ПОВТОР ЕСЛИ "ДЕЛАЮ" ======
async def remind_repeat(context: ContextTypes.DEFAULT_TYPE):
    question = context.job.data["question"]
    await context.bot.send_message(
        chat_id=CHAT_ID,
        text=f"Напоминаю:\n{question}",
        reply_markup=InlineKeyboardMarkup(buttons_work + buttons_evening)
    )

# ====== ЕЖЕДНЕВНЫЕ ВОПРОСЫ ======
async def ask_daily(context: ContextTypes.DEFAULT_TYPE):
    question = context.job.data["question"]
    await context.bot.send_message(
        chat_id=CHAT_ID,
        text=question,
        reply_markup=InlineKeyboardMarkup(buttons_work)
    )

def schedule_daily(app):
    jq = app.job_queue

    # Утренние вопросы
    jq.run_daily(
        ask_daily,
        time=datetime.time(hour=8, minute=0),
        data={"question": "Доброе утро! Как спалось?"}
    )

    # Вечерние вопросы
    jq.run_daily(
        ask_daily,
        time=datetime.time(hour=23, minute=30),
        data={"question": "Как прошёл день?"}
    )

    # Автостарт вечера в 21:00
    jq.run_daily(
        start_evening_auto,
        time=datetime.time(hour=21, minute=0)
    )

    # Автоостановка вечера в 23:59
    jq.run_daily(
        stop_evening_auto,
        time=datetime.time(hour=23, minute=59)
    )

# ====== ЗАПУСК БОТА ======
if __name__ == "__main__":
    app = ApplicationBuilder().token(TOKEN).build()

    # Команды
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("work", start_work))

    # Кнопки
    app.add_handler(CallbackQueryHandler(button))

    # Планирование ежедневных задач
    schedule_daily(app)

    print("Бот запущен...")
    app.run_polling()
