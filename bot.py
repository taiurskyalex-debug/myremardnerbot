from flask import Flask, request
import telebot
import os
from datetime import datetime, timedelta
from supabase import create_client, Client

# --- НАСТРОЙКИ SUPABASE ---
SUPABASE_URL = "https://qbykbcpecshkveedvswy.supabase.co"
SUPABASE_KEY = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6InFieWtiY3BlY3Noa3ZlZWR2c3d5Iiwicm9sZSI6InNlcnZpY2Vfcm9sZSIsImlhdCI6MTc4OTIyNzU3MywiZXhwIjoyMTA0ODAzNTczfQ.O38QK3bkzG9WWrURjsTsdI9S6IV_5hLkSQT0rG2JdtA"
supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)

# --- НАСТРОЙКИ БОТА ---
TOKEN = "8893691800:AAH3dIYh9TDqPFZV4TKSjOzEB1n5XcIA-zM"
bot = telebot.TeleBot(TOKEN)
app = Flask(__name__)

# --- ПРОВЕРКА ПОДПИСКИ ---
def check_subscription(user_id):
    response = supabase.table('reminders').select('start_date').eq('user_id', user_id).limit(1).execute()
    data = response.data
    
    if not data:
        start_date = datetime.now().isoformat()
        supabase.table('reminders').insert({
            'user_id': user_id,
            'text': 'Привет!',
            'start_date': start_date
        }).execute()
        return True
    else:
        start_date = datetime.fromisoformat(data[0]['start_date'])
        if datetime.now() - start_date > timedelta(days=7):
            return False
        return True

# --- СЕКРЕТНАЯ КОМАНДА ДЛЯ ПРОДЛЕНИЯ (ТОЛЬКО ДЛЯ ТЕБЯ) ---
@bot.message_handler(commands=['extend'])
def extend_subscription(message):
    YOUR_ID = 8490191572
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
        supabase.table('reminders').update({'start_date': new_date}).eq('user_id', user_id).execute()
        bot.reply_to(message, f"✅ Подписка для {user_id} продлена на 30 дней.")
    except Exception as e:
        bot.reply_to(message, f"❌ Ошибка: {e}")

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
            "💰 Подписка — 300 ₽/месяц. Для оплаты пиши @Foghism")
    else:
        bot.reply_to(message, 
            "⛔ Твой пробный период закончился.\n"
            "Оплати подписку 300 ₽/мес и напиши мне @Foghism.")

@bot.message_handler(commands=['list'])
def list_reminders(message):
    user_id = message.chat.id
    if not check_subscription(user_id):
        bot.reply_to(message, "⛔ Подписка истекла. Оплати доступ.")
        return
    
    response = supabase.table('reminders').select('id, text').eq('user_id', user_id).neq('text', 'Привет!').execute()
    rows = response.data
    
    if rows:
        answer = "📋 Твои дела:\n" + "\n".join([f"{row['id']}. {row['text']}" for row in rows])
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
        supabase.table('reminders').delete().eq('id', reminder_id).eq('user_id', user_id).execute()
        bot.reply_to(message, f"✅ Дело №{reminder_id} удалено.")
    except Exception as e:
        bot.reply_to(message, f"❌ Ошибка: {e}")

@bot.message_handler(func=lambda message: True)
def save_reminder(message):
    user_id = message.chat.id
    if not check_subscription(user_id):
        bot.reply_to(message, "⛔ Подписка истекла.")
        return
    text = message.text
    supabase.table('reminders').insert({
        'user_id': user_id,
        'text': text,
        'start_date': datetime.now().isoformat()
    }).execute()
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