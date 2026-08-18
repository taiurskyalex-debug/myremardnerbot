from flask import Flask, request
import telebot
import sqlite3
import os
 
TOKEN = "8893691800:AAH3dIYh9TDqPFZV4TKSjOzEB1n5XcIA-zM"
bot = telebot.TeleBot(TOKEN)
app = Flask(__name__)
 
db_path = os.path.join(os.path.dirname(__file__), 'reminders.db')
conn = sqlite3.connect(db_path, check_same_thread=False)
cursor = conn.cursor()
cursor.execute('''CREATE TABLE IF NOT EXISTS reminders
                  (id INTEGER PRIMARY KEY AUTOINCREMENT, user_id INTEGER, text TEXT)''')
conn.commit()
 
@bot.message_handler(commands=['start'])
def start(message):
    bot.reply_to(message, "Привет! Я бот на Render! Пиши мне дела.")
 
@bot.message_handler(commands=['list'])
def list_reminders(message):
    user_id = message.chat.id
    cursor.execute("SELECT id, text FROM reminders WHERE user_id=?", (user_id,))
    rows = cursor.fetchall()
    if rows:
        answer = "Твои дела:\n" + "\n".join([f"{row[0]}. {row[1]}" for row in rows])
    else:
        answer = "У тебя пока нет дел."
    bot.reply_to(message, answer)
 
@bot.message_handler(commands=['delete'])
def delete_reminder(message):
    try:
        parts = message.text.split()
        if len(parts) < 2:
            bot.reply_to(message, "Напиши: /delete 1")
            return
        reminder_id = int(parts[1])
        user_id = message.chat.id
        cursor.execute("DELETE FROM reminders WHERE id=? AND user_id=?", (reminder_id, user_id))
        conn.commit()
        if cursor.rowcount > 0:
            bot.reply_to(message, f"Дело №{reminder_id} удалено.")
        else:
            bot.reply_to(message, "Дело не найдено.")
    except:
        bot.reply_to(message, "Ошибка. Пиши: /delete 1")
 
@bot.message_handler(func=lambda message: True)
def save_reminder(message):
    user_id = message.chat.id
    text = message.text
    cursor.execute("INSERT INTO reminders (user_id, text) VALUES (?, ?)", (user_id, text))
    conn.commit()
    bot.reply_to(message, f"Запомнил: «{text}». Напиши /list, чтобы увидеть все дела.")
 
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