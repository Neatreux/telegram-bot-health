import os
import datetime
import csv
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    ApplicationBuilder,
    CommandHandler,
    CallbackQueryHandler,
    ContextTypes,
)

# ====== Настройки ======
TOKEN = "8223330413:AAHDgNxy29Qy_Fd1_wOuJIEIprSNjEjjAhE"
CHAT_ID = 5886734154
LOG_FILE = "data/daily_log.csv"

# ====== Создание папки и CSV ======
import pathlib
pathlib.Path("data").mkdir(exist_ok=True)
if not os.path.exists(LOG_FILE):
    with open(LOG_FILE, "w", newline="") as f:
        writer = csv.writer(f)
        writer.writerow(["Дата", "Время", "Вопрос", "Ответ"])

# ====== Кнопки ======
buttons_done = [
    [InlineKeyboardButton("Сделал ✅", callback_data="Сделал"),
     InlineKeyboardButton("Пропустил ❌", callback_data="Пропустил"),
     InlineKeyboardButton("Делаю ⏳", callback_data="Делаю")]
]

buttons_done_work = [
    [InlineKeyboardButton("Закончил работу ✅", callback_data="done_work")]
]

buttons_done_office = [
    [InlineKeyboardButton("Закончил офисный блок ✅", callback_data="done_office")]
]

# ====== Логирование ======
def log_response(question, answer):
    now = datetime.datetime.now()
    with open(LOG_FILE, "a", newline="") as f:
        writer = csv.writer(f)
        writer.writerow([now.date(), now.time().strftime("%H:%M:%S"), question, answer])

# ====== Команды ======
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "Привет! Я твой интерактивный бот для здоровья и дневника.\n"
        "Нажми /work, когда начнёшь дневную работу, или /office, если ты в офисе."
    )

# --- Дневной блок ---
async def start_work(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "Дневной блок активирован! Напоминания о растяжке, прогулке, обеде и воде будут приходить."
    )
    context.job_queue.run_repeating(remind_stretch, interval=3600, first=0, data={})

async def done_work(update: Update, context: ContextTypes.DEFAULT_TYPE):
    for job in context.job_queue.jobs():
        job.schedule_removal()
    await update.message.reply_text(
        "Дневной блок завершён ✅ Все повторяющиеся напоминания остановлены."
    )
    log_response("Дневной блок завершён", "Да")

# --- Офисный блок ---
async def start_office(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "Офисный блок активирован! Напоминания о разминке, воде и обеде будут приходить."
    )
    context.job_queue.run_repeating(remind_office, interval=3600, first=0, data={})

async def done_office(update: Update, context: ContextTypes.DEFAULT_TYPE):
    for job in context.job_queue.jobs():
        job.schedule_removal()
    await update.message.reply_text(
        "Офисный блок завершён ✅ Все напоминания остановлены."
    )
    log_response("Офисный блок завершён", "Да")

# ====== Напоминания ======
async def remind_stretch(context: ContextTypes.DEFAULT_TYPE):
    await context.bot.send_message(
        chat_id=CHAT_ID,
        text="Время размяться! Сделай короткую зарядку.",
        reply_markup=InlineKeyboardMarkup(buttons_done + buttons_done_work)
    )

async def remind_office(context: ContextTypes.DEFAULT_TYPE):
    now = datetime.datetime.now()
    if now.hour == 13:
        msg = "Время обеда!"
    else:
        msg = "Время размяться и выпить воды 💧"
    await context.bot.send_message(
        chat_id=CHAT_ID,
        text=msg,
        reply_markup=InlineKeyboardMarkup(buttons_done + buttons_done_office)
    )

async def ask_question(context: ContextTypes.DEFAULT_TYPE):
    job = context.job
    await context.bot.send_message(
        chat_id=CHAT_ID,
        text=job.data["question"],
        reply_markup=InlineKeyboardMarkup(buttons_done + buttons_done_work)
    )

# ====== Обработка кнопок ======
async def button(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    answer = query.data
    question = query.message.text

    if answer == "done_work":
        for job in context.job_queue.jobs():
            job.schedule_removal()
        await query.edit_message_text("Дневной блок завершён ✅")
        log_response("Дневной блок завершён", "Да")
        return

    if answer == "done_office":
        for job in context.job_queue.jobs():
            job.schedule_removal()
        await query.edit_message_text("Офисный блок завершён ✅")
        log_response("Офисный блок завершён", "Да")
        return

    log_response(question, answer)

    if answer == "Делаю":
        context.job_queue.run_once(ask_question, 900, data={"question": question})
        await query.edit_message_text(f"{question}\nОтвет: {answer} (повтор через 15 мин)")
    else:
        await query.edit_message_text(f"{question}\nОтвет: {answer}")

# ====== Планирование ежедневных напоминаний ======
def schedule_jobs(app):
    jq = app.job_queue

    # Утро
    jq.run_daily(ask_question, time=datetime.time(hour=8, minute=0), data={"question": "Доброе утро! Как спалось?"})
    jq.run_daily(ask_question, time=datetime.time(hour=8, minute=5), data={"question": "Ты принял утренние таблетки?"})
    jq.run_daily(ask_question, time=datetime.time(hour=9, minute=0), data={"question": "Время утренней зарядки или похода в зал"})
    jq.run_daily(ask_question, time=datetime.time(hour=9, minute=30), data={"question": "Сколько воды ты выпил? Цель — 500 мл"})

    # Дневной блок
    jq.run_daily(ask_question, time=datetime.time(hour=12, minute=30), data={"question": "Начинаем дневной блок! Время немного размяться"})
    jq.run_daily(ask_question, time=datetime.time(hour=12, minute=45), data={"question": "Пора на прогулку с собакой!"})
    jq.run_daily(ask_question, time=datetime.time(hour=13, minute=15), data={"question": "Время обеда! Не забудь поесть"})
    jq.run_daily(ask_question, time=datetime.time(hour=13, minute=45), data={"question": "Принял дневные таблетки?"})
    jq.run_daily(ask_question, time=datetime.time(hour=13, minute=45), data={"question": "Сколько воды ты выпил? Цель — 1 литр"})

    # Вечер
    jq.run_daily(ask_question, time=datetime.time(hour=22, minute=0), data={"question": "Время обязательной прогулки с собакой!"})
    jq.run_daily(ask_question, time=datetime.time(hour=22, minute=30), data={"question": "Сделай лёгкую растяжку перед сном"})
    jq.run_daily(ask_question, time=datetime.time(hour=22, minute=50), data={"question": "Сколько воды ты выпил? Цель — 1 литр к вечеру"})
    jq.run_daily(ask_question, time=datetime.time(hour=23, minute=30), data={"question": "Как прошёл твой день?"})

# ====== Запуск бота ======
if __name__ == "__main__":
    app = ApplicationBuilder().token(TOKEN).build()

    # Команды
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("work", start_work))
    app.add_handler(CommandHandler("done", done_work))
    app.add_handler(CommandHandler("office", start_office))
    app.add_handler(CommandHandler("done_office", done_office))

    # Кнопки
    app.add_handler(CallbackQueryHandler(button))

    # Планирование JobQueue
    schedule_jobs(app)
    app.run_polling()



