import sqlite3
import json
from datetime import datetime
import requests

import telebot
from telebot import types


import config # for secret tokens
import utils

# command description used in the "help" command
common_description = 'Этот бот позволяет сохранить Ваше текущее положение и снабдить его текстовым/голосовым/фото/видео комментариями.'
commands = {  
    'start': 'Начать работу с ботом',
    'help' : 'Информация по доступным командам',
    'save': 'Сохранить текущую точку',
    'show' : 'Показать список точек',
    'point #': 'Показать подробную информацию о точке номер #',
}

DB_FILENAME = 'my_bot.db'

connection = sqlite3.connect(DB_FILENAME)
cursor = connection.cursor()

cursor.execute('''
CREATE TABLE IF NOT EXISTS users (
    user_db_id INTEGER PRIMARY KEY,
    user_tg_id INTEGER NOT NULL,
    user_name  TEXT NOT NULL,

    step       INTEGER,
    curr_point_id   INTEGER
    
    );''')
cursor.execute('''
CREATE TABLE IF NOT EXISTS points (
    point_id    INTEGER PRIMARY KEY,
    user_db_id  INTEGER NOT NULL,
    date        INTEGER NOT NULL,
    
    longitude   REAL,
    latitude    REAL,
    address     TEXT,
    name        TEXT,
    audio       TEXT,
    video       TEXT,
    voice       TEXT,

    FOREIGN KEY (user_db_id) REFERENCES users(user_db_id)
    );''')

connection.commit()
connection.close()

bot = telebot.TeleBot(config.token)



def add_user_to_db(cursor, user):
    if user.username is not None:
        name = user.username
    elif (user.first_name is not None) and (user.last_name is not None):
        name = f'{user.first_name} {user.last_name}'
    elif user.first_name is not None:
        name = user.first_name
    elif user.last_name is not None:
        name = user.last_name
    else:
        name = str(user.id)
    cursor.execute(
            '''INSERT INTO users
            (user_tg_id, user_name, step) VALUES (?, ?, ?)''',
            (user.id, name, 0))
    return name

def identify(cursor, user):
    '''Return user_db_id, user_name, flag
    flag = True - old user,
    flag = False - user was created in DB'''
    
    cursor.execute('''SELECT user_db_id, user_name FROM users
        WHERE user_tg_id = ?''',
        (user.id, ))
    tmp = cursor.fetchall()
    if tmp:
        return tmp[0][0], tmp[0][1], True
    
    add_user_to_db(cursor, user)

    cursor.execute('''SELECT user_db_id, user_name FROM users
        WHERE user_tg_id = ?''',
        (user.id, ))
    tmp = cursor.fetchall()
    if tmp:
        return tmp[0][0], tmp[0][1], False

    raise RuntimeError

# help page
@bot.message_handler(commands=['help'])
def command_help(m):
    cid = m.chat.id
    # generate help text out of the commands dictionary defined at the top
    help_text = f'{common_description}\nДоступны следующие команды:\n'
    for command, description in commands.items():  
        help_text += f'/{command}: {description}\n'
    bot.send_message(cid, help_text)  # send the generated help page

#start page
@bot.message_handler(commands=['start'])
def command_start(m):
    cid = m.chat.id

    connection = sqlite3.connect(DB_FILENAME)
    cursor = connection.cursor()

    user_db_id, user_name, flag = identify(cursor, m.from_user)
    
    if flag:
        greeting = f'Рады видеть Вас снова, {user_name}!'
    else:
        greeting = f'Рады с Вами познакомиться, {user_name}!'
        
    connection.commit()
    connection.close()

    markup = types.ReplyKeyboardMarkup(
        resize_keyboard=True, 
        one_time_keyboard=True,
        selective=True,
        #row_width=1,
        )

    # btn1 = types.KeyboardButton(text='/help')
    # btn2 = types.KeyboardButton(text='/save')
    # btn3 = types.KeyboardButton(text='/show')

    #markup.add(btn1, btn2, btn3)
    markup.add('/save', '/show')

    bot.send_message(cid, greeting, reply_markup=markup)

    command_help(m)

#show page
@bot.message_handler(commands=['show'])
def command_show(m):
    cid = m.chat.id

    connection = sqlite3.connect(DB_FILENAME)
    cursor = connection.cursor()

    user_db_id, user_name, flag = identify(cursor, m.from_user)
    
    cursor.execute('''SELECT * FROM points 
        WHERE user_db_id = ?''',
        (user_db_id, ))

    tmp = cursor.fetchall()

    connection.commit()
    connection.close()
    
    if not tmp:
        bot.send_message(cid,
            f'Уважаемый {user_name}, у Вас пока нет ни одной сохранённой точки.')
    else:
        w = len(tmp)
        bot.send_message(cid,
            f'Уважаемый {user_name}, у Вас есть {w} сохранённых точек:')
        for i, point in enumerate(tmp):
            s = ', '.join(str(e) for e in point)
            mess = f'Точка {i+1}. {s}.'
            bot.send_message(cid, mess)
            
def prepare_point(cursor, user_db_id, date):
    cursor.execute('''INSERT INTO points
            (user_db_id, date) VALUES (?, ?)''',
        (user_db_id, date))
    cursor.execute('''SELECT point_id 
                   FROM points
                   WHERE user_db_id=& AND date=?''',
            (user_db_id, date))
    point_id = cursor.fetchone()[0]
    return point_id
            
# save point
@bot.message_handler(commands=['save'])
def command_save(m):
    cid = m.chat.id
    date = m.date # in UNIX time

    connection = sqlite3.connect(DB_FILENAME)
    cursor = connection.cursor()

    user_db_id, user_name, flag = identify(cursor, m.from_user)
    step = cursor.execute('''SELECT step 
                          FROM users 
                          WHERE user_db_id=?''',
                   (user_db_id,)).fetchone()[0]
    
    if step == 0:
        # prepare point in points
        point_id = prepare_point(cursor, user_db_id, date)
        # set link to the point in users
        cursor.execute('''UPDATE users
                       SET step=?, curr_point_id=?
                       WHERE user_db_id=?''',
                       (1, point_id, user_db_id))
    # elif step == 1:
    #     # last point do not have coordinates, so 
    #     # we only update datetime in last point
    #     cursor.execute('''UPDATE points
    #                    SET date=?
    #                    WHERE point_id=?''',
    #                    (date, point_id))
        
        
    # step = cursor.fetchall()
    # assert len(tmp)==1
    # step = tmp
    print(f'{step=}')
    
    date_str = datetime.fromtimestamp(date).strftime('%d %b %Y, %H:%M:%S')

    cursor.execute('''INSERT INTO points
            (user_db_id, date, step) VALUES (?, ?, ?)''',
        (user_db_id, date, 0))

    connection.commit()
    connection.close()

    # CREATE TABLE IF NOT EXISTS points (
    # point_id    INTEGER PRIMARY KEY,
    # user_db_id  INTEGER NOT NULL,
    # date        INTEGER NOT NULL,
    
    # coordinates TEXT,

    # name        TEXT,
    # address     TEXT,
    
    # audio       TEXT,
    # video       TEXT,
    # voice       TEXT,
    # step        INTEGER,

    # FOREIGN KEY (user_db_id) REFERENCES users(user_db_id)
    # );''')
    bot.send_message(cid, 'Сохраняем текущую точку')
    bot.send_message(cid, f'Дата и время {date_str}')

    markup = types.ReplyKeyboardMarkup(
        resize_keyboard=True, 
        one_time_keyboard=True,
        selective=True,
        row_width=1)
    btn1 = types.KeyboardButton(text='Получить Ваши координаты',
        request_location=True)
    markup.add(btn1)
    
    bot.send_message(cid, 
        'Для сохранения координат, нажмите на кнопку ниже и подтвердите отправку данных о местоположении',
        reply_markup=markup)

@bot.message_handler(content_types=['location'])
def handler_location(m):
    cid = m.chat.id
    location = m.location
    location_str = f'{location.longitude},{location.latitude}'
    address = utils.get_address_from_coords(longitude=location.longitude, latitude=location.latitude)
    bot.send_message(cid, f'Получил Ваши координаты {location_str}')
    bot.send_message(cid, f'Ваш адрес {address}')

    print(m)
        
@bot.message_handler(content_types=['text'])
def all_text(message):
    # keyboard = types.InlineKeyboardMarkup()
    # url_button = types.InlineKeyboardButton(text="Перейти на Яндекс", url="https://ya.ru")
    # keyboard.add(url_button)
    # bot.send_message(message.chat.id, "Привет! Нажми на кнопку и перейди в поисковик.", reply_markup=keyboard)

    keyboard = types.ReplyKeyboardMarkup(row_width=1, resize_keyboard=True)
    button_phone = types.KeyboardButton(text="Отправить номер телефона", request_contact=True)
    button_geo = types.KeyboardButton(text="Отправить местоположение", request_location=True)
    keyboard.add(button_phone, button_geo)
    bot.send_message(message.chat.id, "Отправь мне свой номер телефона или поделись местоположением, жалкий человечишка!", reply_markup=keyboard)
    
    # global mess
    # mess = message
    # print('Умолчальный')
    print(message)
    
 
bot.polling() # start polling
# bot.send_message(402035303, 'ho-ho-ho')
