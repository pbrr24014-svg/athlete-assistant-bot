import telebot
from telebot import types
import json
import os
from datetime import datetime, date
import time
import threading
from flask import Flask

TOKEN = '8905452025:AAEzrOfnXpFSAQ9WEFS0sS6fIa8CUx_FbRs'
bot = telebot.TeleBot(TOKEN)

# Веб-сервер для того, чтобы хостинг (Render) понимал, что бот живой
app = Flask(__name__)

@app.route('/')
def home():
    return "Bot is active and running 24/7! 🚀"

# Жесткая привязка пути к базе данных
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DB_FILE = os.path.join(BASE_DIR, 'users_database.json')

def load_database():
    if os.path.exists(DB_FILE):
        try:
            with open(DB_FILE, 'r', encoding='utf-8') as f:
                return json.load(f)
        except Exception:
            return {}
    return {}

def save_database():
    with open(DB_FILE, 'w', encoding='utf-8') as f:
        json.dump(users_db, f, ensure_ascii=False, indent=4)

users_db = load_database()

def get_main_keyboard():
    markup = types.ReplyKeyboardMarkup(resize_keyboard=True, row_width=2)
    btn_calc = types.KeyboardButton('📊 Рассчитать КБЖУ')
    btn_menu = types.KeyboardButton('🍽 Рацион на день (Меню)')
    btn_profile = types.KeyboardButton('👤 Мой профиль')
    btn_weight = types.KeyboardButton('⚖️ Записать вес')
    btn_tips = types.KeyboardButton('⚠️ Памятка спортсмену')
    markup.add(btn_calc, btn_menu, btn_profile, btn_weight, btn_tips)
    return markup

@bot.message_handler(commands=['start'])
def send_welcome(message):
    user_id = str(message.chat.id)
    global users_db
    users_db = load_database()

    if user_id in users_db and users_db[user_id].get('name'):
        name = users_db[user_id]['name']
        user_data = users_db[user_id]
        is_profile_complete = all(k in user_data for k in ('weight', 'height', 'age'))
        
        if 'reg_date' not in user_data:
            user_data['reg_date'] = date.today().isoformat()
            save_database()

        if is_profile_complete:
            bot.send_message(message.chat.id, 
                             f"С возвращением, {name}! 🏆 Выбери нужный раздел в меню ниже 👇",
                             reply_markup=get_main_keyboard())
        else:
            bot.send_message(message.chat.id, 
                             f"С возвращением, {name}! 🏆 Твои параметры еще не заполнены. Нажми **📊 Рассчитать КБЖУ**.",
                             reply_markup=get_main_keyboard(), parse_mode="Markdown")
    else:
        if user_id not in users_db:
            users_db[user_id] = {}
        bot.send_message(message.chat.id, 
                         "Привет! Я **Ассистент Спортсмена** — твой цифровой помощник для контроля КБЖУ и веса. 🏆\n\n"
                         "Как тебя зовут?", parse_mode="Markdown")
        bot.register_next_step_handler(message, process_name)

def process_name(message):
    user_id = str(message.chat.id)
    name = message.text.strip()
    if user_id not in users_db:
        users_db[user_id] = {}
    
    users_db[user_id]['name'] = name
    if 'reg_date' not in users_db[user_id]:
        users_db[user_id]['reg_date'] = date.today().isoformat()
    save_database()
    
    bot.send_message(message.chat.id, 
                     f"Очень приятно, {name}!\n"
                     "Твоя программа питания и гидратации активирована. Теперь давай настроим твои параметры. Нажми кнопку **📊 Рассчитать КБЖУ**.",
                     reply_markup=get_main_keyboard(), parse_mode="Markdown")

@bot.message_handler(func=lambda message: message.text == '📊 Рассчитать КБЖУ')
def start_calc_flow(message):
    user_id = str(message.chat.id)
    
    if user_id in users_db and all(k in users_db[user_id] for k in ('weight', 'height', 'age')):
        data = users_db[user_id]
        weight = data['weight']
        height = data['height']
        age = data['age']
        bmr = data.get('bmr', (10 * weight) + (6.25 * height) - (5 * age) + 5)
        weight_loss_limit = weight * 0.015
        water_norm = weight * 0.035
        name = data.get('name', 'Спортсмен')

        response = (
            f"📊 **Твои актуальные результаты расчета, {name}:**\n\n"
            f"• Базовый обмен (BMR): **{int(bmr)} ккал**\n"
            f"• Поддержание веса: ~**{int(bmr * 1.2)} ккал**\n"
            f"• Безопасное похудение: ~**{int(bmr * 1.0)} ккал**\n"
            f"• 💧 **Норма воды:** ~**{water_norm:.1f} л** в день\n\n"
            f"⚠️ **Лимит безопасной сгонки:** не более **{weight_loss_limit:.1f} кг** в неделю!\n\n"
            f"💡 *Если хочешь пройти расчет заново, введи команду /reset*"
        )
        bot.send_message(message.chat.id, response, reply_markup=get_main_keyboard(), parse_mode="Markdown")
    else:
        if user_id not in users_db:
            users_db[user_id] = {}
        bot.send_message(message.chat.id, "Введи свой **текущий вес (в кг)**, например: 70", reply_markup=types.ReplyKeyboardRemove(), parse_mode="Markdown")
        bot.register_next_step_handler(message, process_weight)

@bot.message_handler(commands=['reset', 'recalc'])
def reset_data(message):
    user_id = str(message.chat.id)
    current_name = users_db.get(user_id, {}).get('name', 'Спортсмен')
    reg_date = users_db.get(user_id, {}).get('reg_date', date.today().isoformat())
    
    users_db[user_id] = {'name': current_name, 'reg_date': reg_date}
    save_database()
    bot.send_message(message.chat.id, "Давай обновим твои данные. Введи свой **текущий вес (в кг)**, например: 70", reply_markup=types.ReplyKeyboardRemove(), parse_mode="Markdown")
    bot.register_next_step_handler(message, process_weight)

def process_weight(message):
    try:
        weight = float(message.text.replace(',', '.'))
        user_id = str(message.chat.id)
        users_db[user_id]['weight'] = weight
        if 'weight_history' not in users_db[user_id]:
            users_db[user_id]['weight_history'] = [weight]
        save_database()
            
        bot.send_message(message.chat.id, "Отлично! Теперь введи свой **рост (в сантиметрах)**, например: 175", parse_mode="Markdown")
        bot.register_next_step_handler(message, process_height)
    except ValueError:
        bot.send_message(message.chat.id, "Пожалуйста, введи число (например, 70 или 68.5). Попробуй еще раз, нажав кнопку ниже:", reply_markup=get_main_keyboard())

def process_height(message):
    try:
        height = float(message.text.replace(',', '.'))
        user_id = str(message.chat.id)
        users_db[user_id]['height'] = height
        save_database()
        
        msg_text = "И последний параметр — введи свой **возраст (в годах)**, например: 16"
        bot.send_message(message.chat.id, msg_text, parse_mode="Markdown")
        bot.register_next_step_handler(message, process_age)
    except ValueError:
        bot.send_message(message.chat.id, "Пожалуйста, введи корректный рост числом.", reply_markup=get_main_keyboard())

def process_age(message):
    try:
        age = int(message.text)
        user_id = str(message.chat.id)
        users_db[user_id]['age'] = age
        
        weight = users_db[user_id]['weight']
        height = users_db[user_id]['height']
        name = users_db[user_id].get('name', 'Спортсмен')

        bmr = (10 * weight) + (6.25 * height) - (5 * age) + 5
        users_db[user_id]['bmr'] = bmr
        weight_loss_limit = weight * 0.015
        water_norm = weight * 0.035
        save_database()

        response = (
            f"✅ **Готово, {name}! Твои данные сохранены навсегда.**\n\n"
            f"📊 **Результаты расчета:**\n"
            f"• Базовый обмен (BMR): **{int(bmr)} ккал**\n"
            f"• Поддержание веса: ~**{int(bmr * 1.2)} ккал**\n"
            f"• Безопасное похудение: ~**{int(bmr * 1.0)} ккал**\n"
            f"• 💧 **Норма воды:** ~**{water_norm:.1f} л** в день\n\n"
            f"⚠️ **Лимит безопасной сгонки:** не более **{weight_loss_limit:.1f} кг** в неделю!"
        )
        bot.send_message(message.chat.id, response, reply_markup=get_main_keyboard(), parse_mode="Markdown")

    except ValueError:
        bot.send_message(message.chat.id, "Пожалуйста, введи возраст целым числом.", reply_markup=get_main_keyboard())

@bot.message_handler(func=lambda message: message.text == '🍽 Рацион на день (Меню)')
def handle_daily_ration(message):
    user_id = str(message.chat.id)
    
    if user_id in users_db and 'reg_date' in users_db[user_id]:
        reg_date = datetime.fromisoformat(users_db[user_id]['reg_date']).date()
        today = date.today()
        day_num = (today - reg_date).days + 1
        
        if day_num > 30:
            day_num = ((day_num - 1) % 30) + 1
    else:
        day_num = 1

    weight = users_db.get(user_id, {}).get('weight', 70)
    water_norm = weight * 0.035

    show_daily_ration(message, day_num, water_norm)

@bot.message_handler(func=lambda message: True)
def handle_text_buttons(message):
    text = message.text

    if text == '👤 Мой профиль':
        show_user_profile(message)
    elif text == '⚖️ Записать вес':
        bot.send_message(message.chat.id, "Введи свой текущий вес (например, `70.5`):", reply_markup=types.ReplyKeyboardRemove(), parse_mode="Markdown")
        bot.register_next_step_handler(message, save_weight_log)
    elif text == '⚠️ Памятка спортсмену':
        bot.send_message(message.chat.id, 
                         "⚠️ **Памятка для спортсмена:**\n\n"
                         "1. **Безопасная сгонка:** Не более 1-1.5% от массы тела в неделю.\n"
                         "2. **Гидратация:** Пей чистую воду из расчета 30-40 мл на 1 кг веса.\n"
                         "3. **Баланс:** Углеводы дают энергию для тренировок, белок строит мышцы.",
                         reply_markup=get_main_keyboard(), parse_mode="Markdown")
    else:
        bot.send_message(message.chat.id, "Используй кнопки меню ниже 👇", reply_markup=get_main_keyboard())

def save_weight_log(message):
    try:
        new_weight = float(message.text.replace(',', '.'))
        user_id = str(message.chat.id)
        if user_id not in users_db:
            users_db[user_id] = {'weight_history': []}
        if 'weight_history' not in users_db[user_id]:
            users_db[user_id]['weight_history'] = []
            
        users_db[user_id]['weight_history'].append(new_weight)
        users_db[user_id]['weight'] = new_weight
        save_database()
        
        history = users_db[user_id]['weight_history']
        diff_text = ""
        if len(history) > 1:
            diff = history[-1] - history[-2]
            if diff > 0:
                diff_text = f" (📈 +{diff:.1f} кг с прошлого замера)"
            elif diff < 0:
                diff_text = f" (📉 {diff:.1f} кг с прошлого замера)"
            else:
                diff_text = " (⚖️ вес не изменился)"

        bot.send_message(message.chat.id, f"✅ Записано! Новый вес: **{new_weight} кг**{diff_text}", reply_markup=get_main_keyboard(), parse_mode="Markdown")
    except ValueError:
        bot.send_message(message.chat.id, "Пожалуйста, введи вес числом (например, 71.2)", reply_markup=get_main_keyboard())

def show_user_profile(message):
    user_id = str(message.chat.id)
    if user_id in users_db and all(k in users_db[user_id] for k in ('weight', 'height', 'age')):
        data = users_db[user_id]
        history_str = ", ".join([str(w) for w in data.get('weight_history', [data['weight']])])
        
        reg_date = datetime.fromisoformat(data.get('reg_date', date.today().isoformat())).date()
        day_num = (date.today() - reg_date).days + 1
        water_norm = data['weight'] * 0.035
        
        bot.send_message(message.chat.id, 
                         f"👤 **Спортивный профиль: {data.get('name', 'Спортсмен')}**\n\n"
                         f"• Текущий день программы: **День {day_num} из 30**\n"
                         f"• Текущий вес: {data['weight']} кг\n"
                         f"• Рост: {data['height']} см\n"
                         f"• Возраст: {data['age']} лет\n"
                         f"• Базовый обмен (BMR): {int(data.get('bmr', 0))} ккал\n"
                         f"• 💧 Норма воды: ~{water_norm:.1f} л/день\n"
                         f"• История взвешиваний: [{history_str}]",
                         reply_markup=get_main_keyboard(), parse_mode="Markdown")
    else:
        bot.send_message(message.chat.id, "Твой профиль еще не полностью настроен. Нажми **📊 Рассчитать КБЖУ**!", reply_markup=get_main_keyboard(), parse_mode="Markdown")

def show_daily_ration(message, day_num, water_norm):
    if day_num == 1:
        breakfast = "Овсяная каша (60г) на воде, 1 банан, 15г орехов."
        lunch = "Филе индейки (150г), бурый рис (60г), салат из огурцов."
        dinner = "Запеченное филе горбуши (180г), тушеная брокколи."
        snack = "Протеиновый батончик, горсть кураги."
        kbju = "~1550 ккал | Б: 107г | Ж: 34г | У: 180г"
    elif day_num == 2:
        breakfast = "Рисовая каша на молоке (50г), яблоко, корица, 1 яйцо."
        lunch = "Говядина отварная (140г), гречка (60г), томаты."
        dinner = "Филе минтая на пару (200г), овощное рагу (кабачки, перец)."
        snack = "Творог 5% (100г) с ягодами."
        kbju = "~1500 ккал | Б: 110г | Ж: 30г | У: 170г"
    elif day_num == 3:
        breakfast = "Омлет из 3 яиц с помидорами, цельнозерновой тост с сыром."
        lunch = "Куриная грудка (150г), макароны из твердых сортов (60г)."
        dinner = "Креветки или кальмары отварные (170г), салат айсберг."
        snack = "Горсть миндаля (20г) и зеленое яблоко."
        kbju = "~1520 ккал | Б: 115г | Ж: 35г | У: 160г"
    else:
        breakfast = f"Энергетический завтрак атлета (День {day_num}): Овсяно-блин с творогом и ягодами."
        lunch = f"Обед программы (День {day_num}): Куриное филе с киноа и свежими овощами."
        dinner = f"Ужин восстановления (День {day_num}): Белая рыба на гриле с тушеной спаржей."
        snack = f"Перекус (День {day_num}): Протеиновый шейк на воде."
        kbju = "~1500 ккал | Б: 105г | Ж: 32г | У: 175г"

    ration_text = (
        f"📅 **Готовый рацион и водный режим (День {day_num} из 30)**\n\n"
        f"💧 **Цель по воде на сегодня:** выпить не менее **{water_norm:.1f} л** чистой воды\n"
        f"*(Пей равномерно: по 1-2 стакана между приемами пищи и обязательно во время тренировки!)*\n\n"
        f"🌅 **1. Завтрак:**\n• {breakfast}\n\n"
        f"🍎 **2. Перекус:**\n• {snack}\n\n"
        f"☀️ **3. Обед:**\n• {lunch}\n\n"
        f"🌙 **4. Ужин:**\n• {dinner}\n\n"
        f"⚡ **Итого КБЖУ:** {kbju}"
    )
    bot.send_message(message.chat.id, ration_text, reply_markup=get_main_keyboard(), parse_mode="Markdown")

# Фоновый поток для отправки утренних напоминаний в 8:00
def morning_notifications_worker():
    while True:
        now = datetime.now()
        if now.hour == 8 and now.minute == 0:
            global users_db
            users_db = load_database()
            for chat_id, data in users_db.items():
                if data.get('name'):
                    try:
                        bot.send_message(
                            chat_id, 
                            f"🌅 Доброе утро, {data['name']}! 🏆\n"
                            "Не забудь встать на весы, записать текущий вес через кнопку **⚖️ Записать вес** и проверить сегодняшнее меню!",
                            reply_markup=get_main_keyboard(),
                            parse_mode="Markdown"
                        )
                    except Exception:
                        pass
            time.sleep(61)
        else:
            time.sleep(30)

# Запуск фоновых потоков (уведомления) и самого бота
notification_thread = threading.Thread(target=morning_notifications_worker, daemon=True)
notification_thread.start()

bot_thread = threading.Thread(target=lambda: bot.infinity_polling(), daemon=True)
bot_thread.start()

# Запуск веб-сервера на порту, который требует хостинг
if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port)