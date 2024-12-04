import sqlite3
import telebot
from telebot import types
import pandas as pd

# Бот токен
bot = telebot.TeleBot('7439429538:AAHKb7bcueScuoVEJKaRJsPH94lDqx8iHwY')

# Стартовая клавиатура (Кнопка пропустить)
start_keybrd = types.ReplyKeyboardMarkup(resize_keyboard=True)
skip_btn = types.KeyboardButton('Пропустить')
reg_btn = types.KeyboardButton('Зарегистрироваться')
start_keybrd.add(reg_btn, skip_btn)

# Скип клавиатура
skip_keybrd = types.ReplyKeyboardMarkup(resize_keyboard=True)
skip_keybrd.add(skip_btn)

# Лист клавиатура (Кнопка Создать список)
list_keybrd = types.ReplyKeyboardMarkup(resize_keyboard=True)
list_btn = types.KeyboardButton('Создать список')
list_keybrd.add(list_btn)

# Клавиатура под сообщением (Кнопка добавиться)
add_markup = types.InlineKeyboardMarkup()
add_btn = types.InlineKeyboardButton('Добавиться', callback_data='add_me')
add_markup.add(add_btn)

# Админ клавиатура (кнопка admin button)
admin_keys = types.ReplyKeyboardMarkup(resize_keyboard=True)
admin_btn = (types.KeyboardButton('admin button'))
admin_keys.add(reg_btn, list_btn, admin_btn)

admin_users = [934127824]
message_ids = {}

# Стартовая функция, создание базы данных
@bot.message_handler(commands=['start'])
def start(message):
    conn = sqlite3.connect('listbot.sql')
    cur = conn.cursor()
    # cur.execute('CREATE TABLE IF NOT EXISTS users (id int auto_increment primary key, name varchar(100))')
    # conn.commit()
    cur.close()
    conn.close()
    if message.from_user.id in admin_users:
      bot.send_message(message.chat.id, 'Привет, я готов к твоим указаниям', reply_markup = admin_keys)
      bot.register_next_step_handler(message, commands_work)
    else:
      bot.send_message(message.chat.id, 'Привет, давай внесем твою фамилию и имя в базу, если тебя там еще нет!', reply_markup = start_keybrd)
      bot.register_next_step_handler(message, commands_work)

# Выгружает chat id в множество user_ids
def load_chat_ids():
    conn = sqlite3.connect('listbot.sql')
    cur = conn.cursor()
    cur.execute('SELECT id FROM users')
    user_ids = {row[0] for row in cur.fetchall()}
    conn.close()
    return user_ids

# Сохраняем пользователей в базу данных
def save_chat_id(user_id, message):
    conn = sqlite3.connect('listbot.sql')
    cur = conn.cursor()
    cur.execute('INSERT OR REPLACE INTO users (id, name) VALUES (?, ?)', (user_id, message.text.strip()))
    conn.commit()
    conn.close()

# Обработка командных кнопок
@bot.message_handler(content_types=['text'])
def commands_work(message):
  if message.text == 'Пропустить':
    bot.send_message(message.chat.id, 'Хорошо, жду твоих указаний..', reply_markup=start_keybrd)
  elif message.text == 'Зарегистрироваться':
    bot.send_message(message.chat.id, 'Введи своё ФИ..')
    bot.register_next_step_handler(message, username_filter)
  elif message.text == 'Создать список':
    create_users_list(message)
  elif message.text == 'admin button':
    conn = sqlite3.connect('listbot.sql')
    cur = conn.cursor()
    users_date = ('SELECT * FROM users;')
    cur.execute('SELECT * FROM users')
    users = cur.fetchall()
    users_list = ''
    for el in users:
      users_list += f'ID: {el[0]}, Имя: {el[1]}\n'
    bot.send_message(message.chat.id, users_list, reply_markup= admin_keys)
    df = pd.read_sql_query(users_date, conn)
    cur.close()
    conn.close()
    df.to_excel("USER_DATE.xlsx", index=False)

# Регистрация пользователей
def username_filter(message):
  if len(message.text.strip().split(' ')) == 2:
    save_chat_id(message.chat.id, message)
    if message.from_user.id not in admin_users:  # юзер не админ
      bot.send_message(message.chat.id, 'Твоё ФИ успешно зарегестрированно!\n Можешь ожидать новые списки..')
    if message.from_user.id  in admin_users:  # юзер админ
      bot.send_message(message.chat.id, 'Твоё ФИ успешно зарегестрированно..')
      bot.send_message(message.chat.id, 'Жду твоих указаний!', reply_markup = admin_keys)
  else:
    if message.text == 'Пропустить' or message.text == 'Зарегестрироваться':
      commands_work(message)
    else:
      bot.send_message(message.chat.id, 'Некорректная форма имени и фамилии!\n Попробуйте заново..', reply_markup = start_keybrd)
      bot.register_next_step_handler(message, commands_work)

# Регистрируем описание списка
def create_users_list(message):
  bot.send_message(message.chat.id, 'Введите описание списка..')
  bot.register_next_step_handler(message, list_description)

# Настройка и отправка списка всем пользователям
list_format = ''
#
def list_description(message):
    user_ids = load_chat_ids()
    global list_format
    list_format = f'{message.text}\nСписок участников:\n'

    for user_id in user_ids:
        try:
            sent_message = bot.send_message(user_id, list_format, reply_markup=add_markup)
            message_ids[user_id] = sent_message.message_id
        except Exception as e:
            print(f"Не удалось отправить сообщение пользователю {user_id}: {e}")

# Добавление пользователя в список
i = 1
added_users = set()
#
@bot.callback_query_handler(func=lambda call: call.data == 'add_me')
def callback(call):
    global list_format
    global i
    user_id = call.from_user.id
    chat_id = call.message.chat.id

    try:
        # Проверяем, добавлен ли уже пользователь в список
        if user_id in added_users:
            bot.send_message(user_id, "Вы уже добавлены в список!",  reply_markup=admin_keys)
            if user_id in admin_users:
              bot.edit_message_text(chat_id=chat_id, message_id=message_ids[user_id], text=list_format)
            else:
              bot.edit_message_text(chat_id=chat_id, message_id=message_ids[user_id], text=list_format)
            return

        with sqlite3.connect('listbot.sql') as conn:
            cur = conn.cursor()
            cur.execute("SELECT name FROM users WHERE id = ?", (user_id,))
            user_row = cur.fetchone()
            if user_row:
                user_add_name = user_row[0]
                if user_id in message_ids:
                    # Обновляем сообщение для всех пользователей в списке
                    for uid in message_ids.keys():
                            list_text = f'{list_format}' + f'{i}. ' + user_add_name + '\n'
                            bot.edit_message_text(
                                chat_id=uid,
                                message_id=message_ids[uid],
                                text=list_text,
                                reply_markup=add_markup
                            )
                    list_format = list_text
                    added_users.add(user_id)  # Добавляем пользователя в список добавленных
                    i += 1
                else:
                    bot.send_message(user_id, "Сообщение не найдено для редактирования.")
            else:
                bot.send_message(user_id, "Пользователь не найден в базе данных.")
    except sqlite3.Error as e:
        print(f"Ошибка базы данных: {e}")
        bot.send_message(user_id, "Произошла ошибка при обработке запроса.")

bot.polling(none_stop=True)

