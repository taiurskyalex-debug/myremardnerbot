from flask import Flask, request
import telebot
import sqlite3
import os
from datetime import datetime, timedelta

TOKEN = "8893691800:AAH3dIYh9TDqPFZV4TKSjOzEB1n5XcIA-zM"
bot = telebot.TeleBot(TOKEN)
app = Flask(__name__)

# --- БАЗА ДАННЫХ ---
db_path = os.path.join(os.path.dirname(__file__), 'reminders.db')
conn = sqlite3.connect(db_path, check_same_thread=False)
cursor = conn.cursor()
cursor.execute('''CREATE TABLE IF NOT EXISTS reminders
                  (id INTEGER PRIMARY KEY AUTOINCREMENT, 
                   user_id INTEGER, 
                   text TEXT, 
                   start_date TEXT)''')
conn.commit()

# --- ПРОВЕРКА ПОДПИСКИ ---
def check_subscription(user_id):
    cursor.execute("SELECT start_date FROM reminders WHERE user_id=? LIMIT 1", (user_id,))
    result = cursor.fetchone()
    if result is None:
        start_date = datetime.now().isoformat()
        cursor.execute("INSERT INTO reminders (user_id, text, start_date) VALUES (?, ?, ?)", (user_id, "Привет!", start_date))
        conn.commit()
        return True
    else:
        start_date = datetime.fromisoformat(result[0])
        if datetime.now() - start_date > timedelta(days=7):
            return False
        return True

# --- СЕКРЕТНАЯ КОМАНДА ДЛЯ ПРОДЛЕНИЯ (ТОЛЬКО ДЛЯ ТЕБЯ) ---
@bot.message_handler(commands=['extend'])
def extend_subscription(message):
    YOUR_ID = 8490191572  # ТВОЙ ID
    if message.chat.id != YOUR_ID:
        bot.reply_to(message, "⛔ Доступ запрещен.")
        return
    try:
        parts = message.text.split()
        if len(parts) < 2:
            bot.reply_to(message, "❌ Напиши: /extend USER_ID")
            return
        user_id = int(parts[1])
        new_date = (datetime.now() + timedelta(days=30)).isoformat()
        cursor.execute("UPDATE reminders SET start_date = ? WHERE user_id=?", (new_date, user_id))
        conn.commit()
        bot.reply_to(message, f"✅ Подписка для {user_id} продлена на 30 дней.")
    except:
        bot.reply_to(message, "❌ Ошибка. Пиши: /extend USER_ID")

# --- ОСНОВНЫЕ КОМАНДЫ ---
@bot.message_handler(commands=['start'])
def start(message):
    user_id = message.chat.id
    if check_subscription(user_id):
        bot.reply_to(message, 
            "📋 Привет! Я — твой личный помощник по задачам.\n\n"
            "Ты на 7-дневном пробном периоде.\n"
            "📌 Команды:\n"
            "/list — список дел\n"
            "/delete N — удалить дело\n\n"
            "💰 Подписка — 300 ₽/месяц. Для оплаты пиши @твой_юзернейм")
    else:
        bot.reply_to(message, 
            "⛔ Твой пробный период закончился.\n"
            "Оплати подписку 300 ₽/мес и напиши мне @твой_юзернейм.")

@bot.message_handler(commands=['list'])
def list_reminders(message):
    user_id = message.chat.id
    if not check_subscription(user_id):
        bot.reply_to(message, "⛔ Подписка истекла. Оплати доступ.")
        return
    cursor.execute("SELECT id, text FROM reminders WHERE user_id=? AND text!='Привет!'", (user_id,))
    rows = cursor.fetchall()
    if rows:
        answer = "📋 Твои дела:\n" + "\n".join([f"{row[0]}. {row[1]}" for row in rows])
    else:
        answer = "🎉 У тебя пока нет дел!"
    bot.reply_to(message, answer)

@bot.message_handler(commands=['delete'])
def delete_reminder(message):
    user_id = message.chat.id
    if not check_subscription(user_id):
        bot.reply_to(message, "⛔ Подписка истекла.")
        return
    try:
        parts = message.text.split()
        if len(parts) < 2:
            bot.reply_to(message, "❌ Напиши: /delete 1")
            return
        reminder_id = int(parts[1])
        cursor.execute("DELETE FROM reminders WHERE id=? AND user_id=?", (reminder_id, user_id))
        conn.commit()
        if cursor.rowcount > 0:
            bot.reply_to(message, f"✅ Дело №{reminder_id} удалено.")
        else:
            bot.reply_to(message, "❌ Дело не найдено.")
    except:
        bot.reply_to(message, "❌ Ошибка. Пиши: /delete 1")

@bot.message_handler(func=lambda message: True)
def save_reminder(message):
    user_id = message.chat.id
    if not check_subscription(user_id):
        bot.reply_to(message, "⛔ Подписка истекла.")
        return
    text = message.text
    cursor.execute("INSERT INTO reminders (user_id, text, start_date) VALUES (?, ?, ?)", 
                   (user_id, text, datetime.now().isoformat()))
    conn.commit()
    bot.reply_to(message, f"✅ Запомнил: «{text}».")

@app.route('/webhook', methods=['POST'])
def webhook():
    json_data = request.get_data().decode('utf-8')
    update = telebot.types.Update.de_json(json_data)
    bot.process_new_updates([update])
    return 'OK', 200

@app.route('/')
def index():
    return "Бот работает на Render!"

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=int(os.environ.get('PORT', 5000)))