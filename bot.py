from flask import Flask, request
import telebot
import os
from datetime import datetime, timedelta
from supabase import create_client, Client
import logging

# --- НАСТРОЙКА ЛОГИРОВАНИЯ ---
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

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
    try:
        response = supabase.table('reminders').select('start_date').eq('user_id', user_id).limit(1).execute()
        data = response.data
        logging.info(f"Проверка подписки для {user_id}: {data}")
        
        if not data:
            start_date = datetime.now().isoformat()
            supabase.table('reminders').insert({
                'user_id': user_id,
                'text': 'Привет!',
                'start_date': start_date
            }).execute()
            logging.info(f"Новый пользователь {user_id} добавлен в базу")
            return True
        else:
            start_date = datetime.fromisoformat(data[0]['start_date'])
            if datetime.now() - start_date > timedelta(days=7):
                logging.info(f"Подписка пользователя {user_id} истекла")
                return False
            logging.info(f"Подписка пользователя {user_id} активна")
            return True
    except Exception as e:
        logging.error(f"Ошибка в check_subscription: {e}")
        return True  # В случае ошибки пропускаем (чтобы бот не блокировал)

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
        logging.info(f"Подписка для {user_id} продлена до {new_date}")
    except Exception as e:
        bot.reply_to(message, f"❌ Ошибка: {e}")
        logging.error(f"Ошибка в extend: {e}")

# --- ОСНОВНЫЕ КОМАНДЫ ---
@bot.message_handler(commands=['start'])
def start(message):
    logging.info(f"Получен /start от {message.chat.id}")
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
    logging.info(f"Получен /list от {message.chat.id}")
    user_id = message.chat.id
    if not check_subscription(user_id):
        bot.reply_to(message, "⛔ Подписка истекла. Оплати доступ.")
        return
    
    try:
        response = supabase.table('reminders').select('id, text').eq('user_id', user_id).neq('text', 'Привет!').execute()
        rows = response.data
        logging.info(f"Найдено дел для {user_id}: {len(rows)}")
        
        if rows:
            answer = "📋 Твои дела:\n" + "\n".join([f"{row['id']}. {row['text']}" for row in rows])
        else:
            answer = "🎉 У тебя пока нет дел!"
        bot.reply_to(message, answer)
    except Exception as e:
        bot.reply_to(message, f"❌ Ошибка: {e}")
        logging.error(f"Ошибка в list: {e}")

@bot.message_handler(commands=['delete'])
def delete_reminder(message):
    logging.info(f"Получен /delete от {message.chat.id}")
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
        logging.info(f"Дело {reminder_id} удалено для {user_id}")
    except Exception as e:
        bot.reply_to(message, f"❌ Ошибка: {e}")
        logging.error(f"Ошибка в delete: {e}")

@bot.message_handler(func=lambda message: True)
def save_reminder(message):
    logging.info(f"Получено сообщение от {message.chat.id}: {message.text}")
    user_id = message.chat.id
    if not check_subscription(user_id):
        bot.reply_to(message, "⛔ Подписка истекла.")
        return
    try:
        text = message.text
        supabase.table('reminders').insert({
            'user_id': user_id,
            'text': text,
            'start_date': datetime.now().isoformat()
        }).execute()
        bot.reply_to(message, f"✅ Запомнил: «{text}».")
        logging.info(f"Дело «{text}» добавлено для {user_id}")
    except Exception as e:
        bot.reply_to(message, f"❌ Ошибка: {e}")
        logging.error(f"Ошибка в save_reminder: {e}")

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