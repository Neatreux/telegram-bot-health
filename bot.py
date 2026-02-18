import datetime
import csv
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Updater, CommandHandler, CallbackQueryHandler, CallbackContext, JobQueue

TOKEN = "8223330413:AAHDgNxy29Qy_Fd1_wOuJIEIprSNjEjjAhE"
CHAT_ID = "5886734154"
LOG_FILE = "data/daily_log.csv"

# Создание CSV, если ещё нет
try:
    with open(LOG_FILE, "x", newline="") as f:
        writer = csv.writer(f)
        writer.writerow(["Дата", "Время", "Вопрос", "Ответ"])
except FileExistsError:
    pass

buttons_done = [
    [InlineKeyboardButton("Сделал ✅", callback_data="Сделал"),
     InlineKeyboardButton("Пропустил ❌", callback_data="Пропустил"),
     InlineKeyboardButton("Делаю ⏳", callback_data="Делаю")]
]

def log_response(question, answer):
    now = datetime.datetime.now()
    with open(LOG_FILE, "a", newline="") as f:
        writer = csv.writer(f)
        writer.writerow([now.date(), now.time().strftime("%H:%M:%S"), question, answer])

def start(update: Update, context: CallbackContext):
    update.message.reply_text(
        "Привет! Я твой интерактивный бот для здоровья и дневника.\n"
        "Нажми /work, когда начнёшь дневную работу."
    )

def ask_question(context: CallbackContext):
    job = context.job
    context.bot.send_message(chat_id=CHAT_ID,
                             text=job.context["question"],
                             reply_markup=InlineKeyboardMarkup(buttons_done))

def button(update: Update, context: CallbackContext):
    query = update.callback_query
    query.answer()
    answer = query.data
    question = query.message.text
    log_response(question, answer)

    if answer == "Делаю":
        context.job_queue.run_once(ask_question, 900, context={"question": question})
        query.edit_message_text(text=f"{question}\nОтвет: {answer} (повтор через 15 мин)")
    else:
        query.edit_message_text(text=f"{question}\nОтвет: {answer}")

def start_work(update: Update, context: CallbackContext):
    update.message.reply_text("Бот будет присылать напоминания о разминке каждый час.")
    context.job_queue.run_repeating(remind_stretch, interval=3600, first=3600, context=CHAT_ID)

def remind_stretch(context: CallbackContext):
    context.bot.send_message(chat_id=CHAT_ID,
                             text="Время размяться! Сделай короткую зарядку.",
                             reply_markup=InlineKeyboardMarkup(buttons_done))

def schedule_jobs(updater: Updater):
    job_queue: JobQueue = updater.job_queue

    # Пример: утренние напоминания
    job_queue.run_daily(ask_question, time=datetime.time(hour=8, minute=0),
                        context={"question": "Доброе утро! Как спалось?"})
    job_queue.run_daily(ask_question, time=datetime.time(hour=8, minute=5),
                        context={"question": "Ты принял утренние таблетки?"})
    job_queue.run_daily(ask_question, time=datetime.time(hour=9, minute=0),
                        context={"question": "Время утренней зарядки или похода в зал"})
    job_queue.run_daily(ask_question, time=datetime.time(hour=9, minute=30),
                        context={"question": "Сколько воды ты выпил? Цель — 500 мл"})

    # Дневной блок
    job_queue.run_daily(ask_question, time=datetime.time(hour=12, minute=30),
                        context={"question": "Начинаем дневной блок! Время немного размяться перед активностью"})
    job_queue.run_daily(ask_question, time=datetime.time(hour=12, minute=45),
                        context={"question": "Пора на прогулку с собакой!"})
    job_queue.run_daily(ask_question, time=datetime.time(hour=13, minute=15),
                        context={"question": "Время обеда! Не забудь поесть"})
    job_queue.run_daily(ask_question, time=datetime.time(hour=13, minute=45),
                        context={"question": "Принял дневные таблетки?"})
    job_queue.run_daily(ask_question, time=datetime.time(hour=13, minute=45),
                        context={"question": "Сколько воды ты выпил? Цель — 1 литр"})

    # Вечер
    job_queue.run_daily(ask_question, time=datetime.time(hour=22, minute=0),
                        context={"question": "Время обязательной прогулки с собакой!"})
    job_queue.run_daily(ask_question, time=datetime.time(hour=22, minute=30),
                        context={"question": "Сделай лёгкую растяжку перед сном"})
    job_queue.run_daily(ask_question, time=datetime.time(hour=22, minute=50),
                        context={"question": "Сколько воды ты выпил? Цель — 1 литр к вечеру"})
    job_queue.run_daily(ask_question, time=datetime.time(hour=23, minute=30),
                        context={"question": "Как прошёл твой день?"})

if __name__ == "__main__":
    updater = Updater(TOKEN)
    dp = updater.dispatcher

    dp.add_handler(CommandHandler("start", start))
    dp.add_handler(CommandHandler("work", start_work))
    dp.add_handler(CallbackQueryHandler(button))

    schedule_jobs(updater)

    updater.start_polling()
    updater.idle()
