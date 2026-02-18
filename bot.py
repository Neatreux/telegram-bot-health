import datetime
import csv
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    ApplicationBuilder,
    CommandHandler,
    CallbackQueryHandler,
    ContextTypes,
    JobQueue,
)

# ====== Настройки ======
TOKEN = "ТВОЙ_TELEGRAM_TOKEN"
CHAT_ID = "ТВОЙ_CHAT_ID"
LOG_FILE = "data/daily_log.csv"

# Создание CSV с заголовком, если ещё нет
try:
    with open(LOG_FILE, "x", newline="") as f:
        writer = csv.writer(f)
        writer.writerow(["Дата", "Время", "Вопрос", "Ответ"])
except FileExistsError:
    pass

# ====== Кнопки ======
buttons_done = [
    [InlineKeyboardButton("Сделал ✅", callback_data="Сделал"),
     InlineKeyboardButton("Пропустил ❌", callback_data="Пропустил"),
     InlineKeyboardButton("Делаю ⏳", callback_data="Делаю")]
]

# ====== Функции ======
def log_response(question, answer):
    now = datetime.datetime.now()
    with open(LOG_FILE, "a", newline="") as f:
        writer = csv.writer(f)
        writer.writerow([now.date(), now.time().strftime("%H:%M:%S"), question, answer])

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "Привет! Я твой интерактивный бот для здоровья и дневника.\n"
        "Нажми /work, когда начнёшь дневную работу."
    )

async def ask_question(context: ContextTypes.DEFAULT_TYPE):
    job = context.job
    await context.bot.send_message(
        chat_id=CHAT_ID,
        text=job.data["question"],
        reply_markup=InlineKeyboardMarkup(buttons_done)
    )

async def button(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    answer = query.data
    question = query.message.text
    log_response(question, answer)

    if answer == "Делаю":
        context.job_queue.run_once(ask_question, 900, data={"question": question})
        await query.edit_message_text(text=f"{question}\nОтвет: {answer} (повтор через 15 мин)")
    else:
        await query.edit_message_text(text=f"{question}\nОтвет: {answer}")

async def start_work(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "Отлично! Бот будет присылать напоминания о разминке каждый час."
    )
    context.job_queue.run_repeating(remind_stretch, interval=3600, first=3600, data={})

async def remind_stretch(context: ContextTypes.DEFAULT_TYPE):
    await context.bot.send_message(
        chat_id=CHAT_ID,
        text="Время размяться! Сделай короткую зарядку.",
        reply_markup=InlineKeyboardMarkup(buttons_done)
    )

# ====== Планирование ежедневных напоминаний ======
def schedule_jobs(app):
    jq: JobQueue = app.job_queue

    # Утро
    jq.run_daily(ask_question, time=datetime.time(hour=8, minute=0),
                 data={"question": "Доброе утро! Как спалось?"})
    jq.run_daily(ask_question, time=datetime.time(hour=8, minute=5),
                 data={"question": "Ты принял утренние таблетки?"})
    jq.run_daily(ask_question, time=datetime.time(hour=9, minute=0),
                 data={"question": "Время утренней зарядки или похода в зал"})
    jq.run_daily(ask_question, time=datetime.time(hour=9, minute=30),
                 data={"question": "Сколько воды ты выпил? Цель — 500 мл"})

    # Дневной блок
    jq.run_daily(ask_question, time=datetime.time(hour=12, minute=30),
                 data={"question": "Начинаем дневной блок! Время немного размяться"})
    jq.run_daily(ask_question, time=datetime.time(hour=12, minute=45),
                 data={"question": "Пора на прогулку с собакой!"})
    jq.run_daily(ask_question, time=datetime.time(hour=13, minute=15),
                 data={"question": "Время обеда! Не забудь поесть"})
    jq.run_daily(ask_question, time=datetime.time(hour=13, minute=45),
                 data={"question": "Принял дневные таблетки?"})
    jq.run_daily(ask_question, time=datetime.time(hour=13, minute=45),
                 data={"question": "Сколько воды ты выпил? Цель — 1 литр"})

    # Вечер
    jq.run_daily(ask_question, time=datetime.time(hour=22, minute=0),
                 data={"question": "Время обязательной прогулки с собакой!"})
    jq.run_daily(ask_question, time=datetime.time(hour=22, minute=30),
                 data={"question": "Сделай лёгкую растяжку перед сном"})
    jq.run_daily(ask_question, time=datetime.time(hour=22, minute=50),
                 data={"question": "Сколько воды ты выпил? Цель — 1 литр к вечеру"})
    jq.run_daily(ask_question, time=datetime.time(hour=23, minute=30),
                 data={"question": "Как прошёл твой день?"})

# ====== Основной запуск ======
if __name__ == "__main__":
    app = ApplicationBuilder().token(TOKEN).build()

    # Обработчики команд и кнопок
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("work", start_work))
    app.add_handler(CallbackQueryHandler(button))

    # Планирование ежедневных напоминаний
    schedule_jobs(app)

    # Запуск бота
    app.run_polling()
