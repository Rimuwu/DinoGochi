import glob
import json
import logging
import os
import random
import sys
import time

import telebot
from PIL import Image, ImageDraw, ImageFilter, ImageFont
from telebot import types

sys.path.append("..")
import config

client = config.CLUSTER_CLIENT
users, management, dungeons = client.bot.users, client.bot.management, client.bot.dungeons


with open('json/items.json', encoding='utf-8') as f: 
    items_f = json.load(f)

with open('json/dino_data.json', encoding='utf-8') as f: 
    json_f = json.load(f)

with open('json/mobs.json', encoding='utf-8') as f: 
    mobs_f = json.load(f)

with open('json/floors_dungeon.json', encoding='utf-8') as f: 
    floors_f = json.load(f)

with open('json/quests_data.json', encoding='utf-8') as f: 
    quests_f = json.load(f)

checks_data = {'memory': [0, time.time()], 'incub': [0, time.time(), 0], 'notif': [[], []], 'main': [[], [], []], 'main_hunt': [ [], [], [] ], 'main_game': [ [], [], [] ], 'main_sleep': [ [], [], [] ], 'main_pass': [ [], [], [] ], 'main_journey': [ [], [], [] ], 'col': 0}
reyt_ = [[], [], {}]
users_timeout = {}
callback_timeout = {}

languages = {}

class Functions:

    def insert_user(user):
        global languages

        if user.language_code in languages.keys():
            lg = user.language_code
        else:
            lg = 'en'

        users.insert_one({

            'userid': user.id,
            'last_m': int(time.time()),
            'create_acc': int(time.time()),
            'dead_dinos': 0,
            'dinos': {}, 'eggs': [],
            'notifications': {},
            'settings': {'notifications': True,
                         'dino_id': '1',
                         'last_markup': 1},
            'language_code': lg,
            'inventory': [],
            'coins': 0, 'lvl': [1, 0],
            'user_dungeon': { "equipment": { 'backpack': None}, 
                              'statistics': []
                            },
            'activ_items': { '1': { 'game': None, 'hunt': None,
                                    'journey': None, 'unv': None }
                            },
            'friends': { 'friends_list': [],
                        'requests': []
                        }
                            })

    @staticmethod
    def trans_paste(fg_img,bg_img,alpha=10,box=(0,0)):
        fg_img_trans = Image.new("RGBA",fg_img.size)
        fg_img_trans = Image.blend(fg_img_trans,fg_img,alpha)
        bg_img.paste(fg_img_trans,box,fg_img_trans)
        return bg_img

    @staticmethod
    def chunks(lst, n):
        for i in range(0, len(lst), n):
            yield lst[i:i + n]

    @staticmethod
    def inline_markup(bot, element = None, user = None, inp_text:list = [None, None], arg = None):

        try:  #ошибка связанная с Int64 при попытке поставить обычную проверку
            user = int(user)
        except:
            pass

        if type(user) == int:
            userid = user

        elif type(user) == dict:
            userid = user['userid']

        else:
            userid = user.id

        bd_user = users.find_one({"userid": userid})
        markup_inline = types.InlineKeyboardMarkup()

        if element == 'inventory' and bd_user != None: #markup_inline

            if bd_user['language_code'] == 'ru':
                markup_inline.add(
                types.InlineKeyboardButton( text = f'🍭 | {inp_text[0]}', callback_data = f"inventory")
                )

            else:
                markup_inline.add(
                types.InlineKeyboardButton( text = f'🍭 | {inp_text[1]}', callback_data = f"inventory")
                )

        elif element == 'delete_message': #markup_inline

            if bd_user['language_code'] == 'ru':
                inl_l = {"⚙ Удалить сообщение": 'message_delete'}
            else:
                inl_l = {"⚙ Delete a message": 'message_delete'}

            markup_inline.add( *[ types.InlineKeyboardButton( text = inl, callback_data = f"{inl_l[inl]}") for inl in inl_l.keys() ])

        elif element == 'requests' and bd_user != None: #markup_inline

            if bd_user['language_code'] == 'ru':
                markup_inline.add(
                types.InlineKeyboardButton( text = f'👥 | {inp_text[0]}', callback_data = f"requests")
                )

            else:
                markup_inline.add(
                types.InlineKeyboardButton( text = f'👥 | {inp_text[1]}', callback_data = f"requests")
                )

        elif element == 'send_request' and bd_user != None: #markup_inline

            if bd_user['language_code'] == 'ru':
                markup_inline.add(
                types.InlineKeyboardButton( text = f'✔ | {inp_text[0]}', callback_data = f"send_request")
                )

            else:
                markup_inline.add(
                types.InlineKeyboardButton( text = f'✔ | {inp_text[1]}', callback_data = f"send_request")
                )

        elif element == 'open_dino_profile' and bd_user != None: #markup_inline

            if bd_user['language_code'] == 'ru':
                markup_inline.add(
                types.InlineKeyboardButton( text = f'🦕 | {inp_text[0]}', callback_data = f"open_dino_profile_{arg}")
                )

            else:
                markup_inline.add(
                types.InlineKeyboardButton( text = f'🦕 | {inp_text[1]}', callback_data = f"open_dino_profile_{arg}")
                )

        else:
            print(f'{element}\n{user}')

        return markup_inline

    @staticmethod
    def markup(bot, element = 1, user = None, inp_text:list = [None, None], bd_user = None):

        try:  #ошибка связанная с Int64 при попытке поставить обычную проверку
            user = int(user)
        except:
            pass

        if type(user) == int:
            userid = user

        elif type(user) == dict:
            userid = int(user['userid'])
            bd_user = user

        else:
            userid = user.id

        markup = types.ReplyKeyboardMarkup(resize_keyboard = True)
        if bd_user == None:
            bd_user = users.find_one({"userid": userid})

        if bd_user != None:
            try:
                dino = bd_user['dinos'][ bd_user['settings']['dino_id'] ]
            except:
                if len(bd_user['dinos']) > 0:
                    bd_user['settings']['dino_id'] = list(bd_user['dinos'].keys())[0]
                    users.update_one( {"userid": bd_user['userid']}, {"$set": {'settings': bd_user['settings'] }} )

        if bd_user != None and len(bd_user['dinos']) == 0 and Functions.inv_egg(bd_user) == False and bd_user['lvl'][0] <= 5:

            if bd_user['language_code'] == 'ru':
                nl = "🧩 Проект: Возрождение"
            else:
                nl = '🧩 Project: Rebirth'

            markup.add(nl)
            return markup

        elif bd_user != None and len(bd_user['dinos']) == 0 and Functions.inv_egg(bd_user) == False and bd_user['lvl'][0] > 5:

            if bd_user['language_code'] == 'ru':
                nl = '🎮 Инвентарь'
            else:
                nl = '🎮 Inventory'

            markup.add(nl)
            return markup

        elif element == 1 and bd_user != None:

            if len(list(bd_user['dinos'])) == 1 and bd_user['dinos'][ list(bd_user['dinos'].keys())[0] ]['status'] == 'incubation' and bd_user['lvl'][0] < 2:

                if bd_user['language_code'] == 'ru':
                    nl = ['🦖 Динозавр', '🔧 Настройки', '👥 Друзья', '❗ FAQ']
                else:
                    nl = ['🦖 Dinosaur', '🔧 Settings', '👥 Friends', '❗ FAQ']

                item1 = types.KeyboardButton(nl[0])
                item2 = types.KeyboardButton(nl[1])
                item3 = types.KeyboardButton(nl[2])
                item4 = types.KeyboardButton(nl[3])

                markup.add(item1, item2, item3, item4)

            else:

                if bd_user['language_code'] == 'ru':
                    nl = ['🦖 Динозавр', '🕹 Действия', '👁‍🗨 Профиль', '🔧 Настройки', '👥 Друзья', '❗ FAQ']
                    tv = ['🍺 Дино-таверна']
                else:
                    nl = ['🦖 Dinosaur', '🕹 Actions', '👁‍🗨 Profile', '🔧 Settings', '👥 Friends', '❗ FAQ']
                    tv = ['🍺 Dino-tavern']

                if 'vis.faq' in bd_user['settings'].keys() and bd_user['settings']['vis.faq'] == False:
                    nl.remove('❗ FAQ')

                markup.add( *[i for i in nl] )
                markup.add( *[i for i in tv] )


        elif element == 1:
            try:
                if user.language_code == 'ru':
                    nl = ['🍡 Начать играть']
                else:
                    nl = ['🍡 Start playing']
            except:
                nl = ['🍡 Start playing']

            item1 = types.KeyboardButton(nl[0])

            markup.add(item1)

        elif element == "settings" and bd_user != None:

            if 'vis.faq' not in bd_user['settings']:
                bd_user['settings']['vis.faq'] = True

                users.update_one( {"userid": bd_user['userid']}, {"$set": {'settings': bd_user['settings'] }} )

            if 'inv_view' not in bd_user['settings']:
                bd_user['settings']['inv_view'] = [2, 3]

                users.update_one( {"userid": bd_user['userid']}, {"$set": {'settings': bd_user['settings'] }} )

            markup = types.ReplyKeyboardMarkup(resize_keyboard = True, row_width = 2)

            if bd_user['language_code'] == 'ru':
                nl = ['❗ Уведомления', "👅 Язык", '💬 Переименовать', '⁉ Видимость FAQ', '🎞 Инвентарь', '↪ Назад']

            else:
                nl = ['❗ Notifications', "👅 Language", '💬 Rename', '⁉ Visibility FAQ', '🎞 Inventory', '↪ Back']

            item1 = types.KeyboardButton(nl[0])
            item2 = types.KeyboardButton(nl[1])
            item3 = types.KeyboardButton(nl[2])
            item4 = types.KeyboardButton(nl[3])
            item5 = types.KeyboardButton(nl[4])
            item6 = types.KeyboardButton(nl[5])

            markup.add(item1, item2, item3, item4, item5)
            markup.add(item6)

        elif element == "friends-menu" and bd_user != None:

            if bd_user['language_code'] == 'ru':
                nl = ["➕ Добавить", '📜 Список', '➖ Удалить', '💌 Запросы', '🤍 Пригласи друга', '↪ Назад']

            else:
                nl = ["➕ Add", '📜 List', '➖ Delete', '💌 Inquiries', '🤍 Invite a friend', '↪ Back']

            item1 = types.KeyboardButton(nl[0])
            item2 = types.KeyboardButton(nl[1])
            item3 = types.KeyboardButton(nl[2])
            item4 = types.KeyboardButton(nl[3])
            item5 = types.KeyboardButton(nl[4])
            item6 = types.KeyboardButton(nl[5])

            markup.add(item1, item2, item3, item4, item5)
            markup.add(item6)

        elif element == "referal-system" and bd_user != None:

            if 'referal_system' in bd_user.keys():

                if bd_user['language_code'] == 'ru':
                    nl = [f'🎲 Код: {bd_user["referal_system"]["my_cod"]}', '👥 Меню друзей']

                    if bd_user["referal_system"]["friend_cod"] == None:
                        nl.insert(1, '🎞 Ввести код')
                    else:
                        nl.insert(1, f'🎞 Друг: {bd_user["referal_system"]["friend_cod"]}')
                else:
                    nl = [f'🎲 Code: {bd_user["referal_system"]["my_cod"]}', '👥 Friends Menu']

                    if bd_user["referal_system"]["friend_cod"] == None:
                        nl.insert(1, '🎞 Enter Code')
                    else:
                        nl.insert(1, f'🎞 Friend: {bd_user["referal_system"]["friend_cod"]}')

            else:

                if bd_user['language_code'] == 'ru':
                    nl = ['🎲 Сгенерировать код', '🎞 Ввести код', '👥 Меню друзей']
                else:
                    nl = ['🎲 Generate Code', '🎞 Enter Code', '👥 Friends Menu']

            item1 = types.KeyboardButton(nl[0])
            item2 = types.KeyboardButton(nl[1])
            item3 = types.KeyboardButton(nl[2])

            markup.add(item1, item2)
            markup.add(item3)

        elif element == 'actions' and bd_user != None:
            markup = types.ReplyKeyboardMarkup(resize_keyboard = True, row_width = 2)

            if len(bd_user['dinos']) == 0:
                return markup

            if bd_user['dinos'][ bd_user['settings']['dino_id'] ]['status'] == 'incubation':
                ll = []

                if bd_user['language_code'] == 'ru':
                    nl = '🥚 Яйцо инкубируется'
                    nll = '↪ Назад'
                else:
                    nl = '🥚 The egg is incubated'
                    nll = '↪ Back'

                if len(bd_user['dinos']) > 1:
                    nid_dino = bd_user['settings']['dino_id']
                    ll.append(f'🦖 Динозавр: {nid_dino}')

                ll.append(nl)
                ll.append(nll)

                markup.add(* [ x for x in ll ])

            if bd_user['dinos'][ bd_user['settings']['dino_id'] ]['status'] == 'dino':

                if bd_user['language_code'] == 'ru':
                    nl = ['🎮 Развлечения', '🍣 Покормить']
                    nl2 = ['↪ Назад']

                    if len(bd_user['dinos']) == 1:
                        nid_dino = list(bd_user['dinos'].keys())[0]
                        dino = bd_user['dinos'][ str(nid_dino) ]

                    if len(bd_user['dinos']) > 1:
                        try:
                            nid_dino = bd_user['settings']['dino_id']
                            dino = bd_user['dinos'][ str(nid_dino) ]
                        except:
                            nid_dino = list(bd_user['dinos'].keys())[0]
                            bd_user['settings']['dino_id'] = list(bd_user['dinos'].keys())[0]
                            users.update_one( {"userid": bd_user['userid']}, {"$set": {'settings': bd_user['settings'] }} )
                            dino = bd_user['dinos'][ str(nid_dino) ]

                    if len(bd_user['dinos']) == 0:
                        return markup

                    if dino['activ_status'] == 'journey':
                        nl.insert(2, '🎑 Вернуть')
                    else:
                        nl.insert(2, '🎑 Путешествие')

                    if dino['activ_status'] == 'sleep':
                        nl.insert(3, '🌙 Пробудить')
                    else:
                        nl.insert(3, '🌙 Уложить спать')

                    if dino['activ_status'] != 'hunting':
                        nl.insert(4, '🍕 Сбор пищи')

                    else:
                        nl.insert(4, '🍕 Прогресс')

                    if len(bd_user['dinos']) > 1:
                        item0 = types.KeyboardButton(f'🦖 Динозавр: {nid_dino}')
                        item1 = types.KeyboardButton(nl[0])
                        item2 = types.KeyboardButton(nl[1])
                        item3 = types.KeyboardButton(nl[2])
                        item4 = types.KeyboardButton(nl[3])
                        item5 = types.KeyboardButton(nl[4])
                        item6 = types.KeyboardButton(nl2[0])

                        markup.add(item0, item1, item2, item3, item4, item5)
                        markup.add(item6)

                    else:
                        markup.add(* [ x for x in nl ])
                        markup.add(* [ x for x in nl2 ])

                else:
                    nl = ['🎮 Entertainments', '🍣 Feed', '↪ Back']

                    if len(bd_user['dinos']) == 1:
                        nid_dino = list(bd_user['dinos'].keys())[0]
                        dino = bd_user['dinos'][ str(nid_dino) ]

                    if len(bd_user['dinos']) > 1:
                        if 'dino_id' not in bd_user['settings']:
                            bd_user['settings']['dino_id'] = list(bd_user['dinos'].keys())[0]
                            users.update_one( {"userid": bd_user['userid']}, {"$set": {'settings': bd_user['settings'] }} )
                        try:
                            nid_dino = bd_user['settings']['dino_id']
                            dino = bd_user['dinos'][ str(nid_dino) ]
                        except:
                            nid_dino = list(bd_user['dinos'].keys())[0]
                            users.update_one( {"userid": bd_user['userid']}, {"$set": {'settings': bd_user['settings'] }} )
                            dino = bd_user['dinos'][ str(nid_dino) ]

                    if len(bd_user['dinos']) == 0:
                        return markup

                    if dino['activ_status'] == 'journey':
                        nl.insert(2, '🎑 Call')
                    else:
                        nl.insert(2, '🎑 Journey')

                    if dino['activ_status'] == 'sleep':
                        nl.insert(3, '🌙 Awaken')
                    else:
                        nl.insert(3, '🌙 Put to bed')

                    if dino['activ_status'] != 'hunting':
                        nl.insert(4, '🍕 Collecting food')

                    else:
                        nl.insert(4, '🍕 Progress')

                    if len(bd_user['dinos']) > 1:
                        item0 = types.KeyboardButton(f'🦖 Dino: {nid_dino}')
                        item1 = types.KeyboardButton(nl[0])
                        item2 = types.KeyboardButton(nl[1])
                        item3 = types.KeyboardButton(nl[2])
                        item4 = types.KeyboardButton(nl[3])
                        item5 = types.KeyboardButton(nl[4])
                        item6 = types.KeyboardButton(nl2[0])

                        markup.add(item0, item1, item2, item3, item4, item5)
                        markup.add(item6)

                    else:

                        markup.add(* [ x for x in nl ])
                        markup.add(* [ x for x in nl2 ])

        elif element == 'games' and bd_user != None:

            if bd_user['dinos'][ str(bd_user['settings']['dino_id']) ]['activ_status'] == 'game':
                markup = types.ReplyKeyboardMarkup(resize_keyboard = True, row_width = 1)

                if bd_user['language_code'] == 'ru':
                    nl = ['❌ Остановить игру', '↩ Назад']
                else:
                    nl = ['❌ Stop the game', '↩ Back']

                item1 = types.KeyboardButton(nl[0])
                item2 = types.KeyboardButton(nl[1])

                markup.add(item1, item2)

            else:
                markup = types.ReplyKeyboardMarkup(resize_keyboard = True, row_width = 2)

                if bd_user['language_code'] == 'ru':
                    nl = ['🎮 Консоль', '🪁 Змей', '🏓 Пинг-понг', '🏐 Мяч']

                    if Functions.acc_check(bot, bd_user, '44', str(bd_user['settings']['dino_id'])):
                        for x in ['🧩 Пазлы', '♟ Шахматы', '🧱 Дженга', '🎲 D&D']:
                            nl.append(x)

                    nl.append('↩ Назад')

                else:
                    nl = ['🎮 Console', '🪁 Snake', '🏓 Ping Pong', '🏐 Ball']

                    if Functions.acc_check(bot, bd_user, '44', str(bd_user['settings']['dino_id'])):
                        for x in ['🧩 Puzzles', '♟ Chess', '🧱 Jenga', '🎲 D&D']:
                            nl.append(x)

                    nl.append('↩ Back')

                markup.add(* [x for x in nl] )

        elif element == "profile" and bd_user != None:

            if bd_user['language_code'] == 'ru':
                nl = ['📜 Информация', '🎮 Инвентарь', '🎢 Рейтинг', '💍 Аксессуары', '🛒 Рынок', '↪ Назад']

            else:
                nl = ['📜 Information', '🎮 Inventory', '🎢 Rating', '💍 Accessories', '🛒 Market', '↪ Back']

            markup.add(nl[0], nl[1])
            markup.add(nl[2], nl[3], nl[4])
            markup.add(nl[5])

        elif element == "market" and bd_user != None:

            if bd_user['language_code'] == 'ru':
                nl = ['🛒 Случайные товары', '🔍 Поиск товара', '➕ Добавить товар', '📜 Мои товары', '➖ Удалить товар', '👁‍🗨 Профиль']

            else:
                nl = ['🛒 Random Products', '🔍 Product Search', '➕ Add Product', '📜 My products', '➖ Delete Product', '👁‍🗨 Profile']

            markup.add(nl[0], nl[1])
            markup.add(nl[2], nl[3], nl[4])
            markup.add(nl[5])

        elif element == "dino-tavern" and bd_user != None:
            markup = types.ReplyKeyboardMarkup(resize_keyboard = True, row_width = 3)

            if bd_user['language_code'] == 'ru':
                nl = ['⛓ Квесты', '♻ Изменение Динозавра']
                nl2 = ["🗻 Подземелья"]
                nl3 = ['↪ Назад']

            else:
                nl = ['⛓ Quests', '♻ Change Dinosaur']
                nl2 = ["🗻 Dungeons"]
                nl3 = ['↪ Back']

            markup.add(* [x for x in nl] )
            markup.add(* [x for x in nl2] )
            markup.add(* [x for x in nl3] )

        elif element == "dungeon_menu" and bd_user != None:
            markup = types.ReplyKeyboardMarkup(resize_keyboard = True, row_width = 3)

            if bd_user['language_code'] == 'ru':
                nl = ['🗻 Создать', '🚪 Присоединиться', '⚔ Экипировка', '📕 Правила подземелья', '🎮 Статистика']
                nl3 = ['↪ Назад']

            else:
                nl = ['🗻 Create', '🚪 Join', '⚔ Equip', '📕 Dungeon Rules', '🎮 Statistics']
                nl3 = ['↪ Back']

            markup.add(* [x for x in nl] )
            markup.add(* [x for x in nl3] )

        elif element == "dungeon" and bd_user != None:

            if bd_user['language_code'] == 'ru':
                nl = ['Ничего не делает']

            else:
                nl = ['Does nothing']

            markup.add(* [x for x in nl] )

        else:
            print(f'{element}\n{user.first_name}')

        users.update_one( {"userid": userid}, {"$set": {f'settings.last_markup': element }} )
        return markup

    @staticmethod
    def time_end(seconds:int, mini = False):

        if seconds < 0: seconds = 0

        def ending_w(word, number:str, mini):
            if int(number) not in [11,12,13,14,15]:
                ord = int(str(number)[int(len(str(number))) - 1:])
            else:
                ord = int(number)

            if word == 'секунда':
                if mini != True:
                    if ord == 1:
                        newword = word
                    elif ord in [2,3,4]:
                        newword = 'секунды'
                    elif ord > 4 or ord == 0:
                        newword = 'секунд'
                else:
                    newword = 's'

            elif word == 'минута':
                if mini != True:
                    if ord == 1:
                        newword = word
                    elif ord in [2,3,4]:
                        newword = 'минуты'
                    elif ord > 4 or ord == 0:
                        newword = 'минут'
                else:
                    newword = 'm'

            elif word == 'час':
                if mini != True:
                    if ord == 1:
                        newword = word
                    elif ord in [2,3,4]:
                        newword = 'часа'
                    elif ord > 4 or ord == 0:
                        newword = 'часов'
                else:
                    newword = 'h'

            elif word == 'день':
                if mini != True:
                    if ord == 1:
                        newword = word
                    elif ord in [2,3,4]:
                        newword = 'дня'
                    elif ord > 4 or ord == 0:
                        newword = 'дней'
                else:
                    newword = 'd'

            elif word == 'неделя':
                if mini != True:
                    if ord == 1:
                        newword = word
                    elif ord in [2,3,4]:
                        newword = 'недели'
                    elif ord > 4 or ord == 0:
                        newword = 'недель'
                else:
                    newword = 'w'

            elif word == 'месяц':
                if mini != True:
                    if ord == 1:
                        newword = word
                    elif ord in [2,3,4]:
                        newword = 'месяца'
                    elif ord > 4 or ord == 0:
                        newword = 'месяцев'
                else:
                    newword = 'M'

            return newword


        mm = int(seconds//2592000)
        seconds -= mm*2592000
        w = int(seconds//604800)
        seconds -= w*604800
        d = int(seconds//86400)
        seconds -= d*86400
        h = int(seconds//3600)
        seconds -= h*3600
        m = int(seconds//60)
        seconds -= m*60
        s = int(seconds%60)

        if mm < 10: mm = f"0{mm}"
        if w < 10: w = f"0{w}"
        if d < 10: d = f"0{d}"
        if h < 10: h = f"0{h}"
        if m < 10: m = f"0{m}"
        if s < 10: s = f"0{s}"

        if m == '00' and h == '00' and d == '00' and w == '00' and mm == '00':
            return f"{s} {ending_w('секунда',s,mini)}"
        elif h == '00' and d == '00' and w == '00' and mm == '00':
            return f"{m} {ending_w('минута',m,mini)}, {s} {ending_w('секунда',s,mini)}"
        elif d == '00' and w == '00' and mm == '00':
            return f"{h} {ending_w('час',h,mini)}, {m} {ending_w('минута',m,mini)}, {s} {ending_w('секунда',s,mini)}"
        elif w == '00' and mm == '00':
            return f"{d} {ending_w('день',d,mini)}, {h} {ending_w('час',h,mini)}, {m} {ending_w('минута',m,mini)}, {s} {ending_w('секунда',s,mini)}"
        elif mm == '00':
            return f"{w} {ending_w('неделя',w,mini)}, {d} {ending_w('день',d,mini)}, {h} {ending_w('час',h,mini)}, {m} {ending_w('минута',m,mini)}, {s} {ending_w('секунда',s,mini)}"
        else:
            return  f"{mm} {ending_w('месяц',mm,mini)}, {w} {ending_w('неделя',w,mini)}, {d} {ending_w('день',d,mini)}, {h} {ending_w('час',h,mini)}, {m} {ending_w('минута',m,mini)}, {s} {ending_w('секунда',s,mini)}"


    @staticmethod
    def dino_pre_answer(bot, message, type:str = 'all'):
        id_dino = {}

        user = message.from_user
        bd_user = users.find_one({"userid": user.id})

        if bd_user == None:
            return 1, None

        rmk = types.ReplyKeyboardMarkup(resize_keyboard = True)

        if len(bd_user['dinos'].keys()) == 0:
            return 1, None

        elif len(bd_user['dinos'].keys()) == 1:
            return 2, bd_user['dinos'][ list(bd_user['dinos'].keys())[0] ]

        else:
            for dii in bd_user['dinos']:
                if bd_user['dinos'][dii]['status'] == 'incubation':
                    if type == 'all':
                        rmk.add( f"{dii}# 🥚" )
                        id_dino[f"{dii}# 🥚"] = [bd_user['dinos'][dii], dii]
                else:
                    rmk.add( f"{dii}# {bd_user['dinos'][dii]['name']}" )
                    id_dino[f"{dii}# {bd_user['dinos'][dii]['name']}"] = [bd_user['dinos'][dii], dii]

            if bd_user['language_code'] == 'ru':
                rmk.add('↪ Назад')
                text = '🦖 | Выберите динозавра > '
            else:
                rmk.add('↪ Back')
                text = '🦖 | Choose a dinosaur >'

            return 3, [rmk, text, id_dino]

    @staticmethod
    def user_dino_pn(user):
        if len(user['dinos'].keys()) == 0:
            return '1'
        else:
            id_list = []
            for i in user['dinos'].keys():
                try:
                    id_list.append(int(i))
                except:
                    pass
            return str(max(id_list) + 1)

    @staticmethod
    def random_dino(user, dino_id_remove, quality = None):
        if quality == None or quality == 'random':
            r_q = random.randint(1, 10000)
            if r_q in list(range(1, 5001)):
                quality = 'com'
            elif r_q in list(range(5001, 7501)):
                quality = 'unc'
            elif r_q in list(range(7501, 9001)):
                quality = 'rar'
            elif r_q in list(range(9001, 9801)):
                quality = 'myt'
            else:
                quality = 'leg'

        dino_id = None

        while dino_id == None:
            p_var = random.choice(json_f['data']['dino'])
            dino = json_f['elements'][str(p_var)]
            if dino['image'][5:8] == quality:
                dino_id = p_var

        dino = json_f['elements'][str(dino_id)]
        del user['dinos'][str(dino_id_remove)]
        user['dinos'][Functions.user_dino_pn(user)] = {
                'dino_id': dino_id, "status": 'dino',
                'activ_status': 'pass_active', 'name': dino['name'],
                'stats': {"heal": 100, "eat": random.randint(70, 100), 'game': random.randint(50, 100), 'mood': random.randint(7, 100), "unv": 100},
                'games': [],
                'quality': quality, 'dungeon': {"equipment": {'armor': None, 'weapon': None}}
                                                      }

        users.update_one( {"userid": user['userid']}, {"$set": {'dinos': user['dinos']}} )

    @staticmethod
    def notifications_manager(bot, notification, user, arg = None, dino_id = '1', met = 'send'):

        if met == 'delete':

            if notification in ['friend_request', "friend_rejection", "friend_accept"]:
                if notification in user['notifications'].keys():
                    del user['notifications'][notification]
                    users.update_one( {"userid": user['userid']}, {"$set": {'notifications': user['notifications'] }} )

            else:
                if dino_id in user['notifications']:
                    if notification in user['notifications'][dino_id].keys():
                        del user['notifications'][dino_id][notification]
                        users.update_one( {"userid": user['userid']}, {"$set": {'notifications': user['notifications'] }} )

                else:

                    user['notifications'][str(dino_id)] = {}
                    users.update_one( {"userid": user['userid']}, {"$set": {'notifications': user['notifications'] }} )


        if met == 'check':
            if notification in ['friend_request', "friend_rejection", "friend_accept"]:
                if notification in list(user['notifications'].keys()) and user['notifications'][notification] == True:
                    return True
                else:
                    user['notifications'][notification] = False
                    users.update_one( {"userid": user['userid']}, {"$set": {'notifications': user['notifications'] }} )
                    return False

            else:
                if str(dino_id) not in user['notifications'].keys():
                    user['notifications'][str(dino_id)] = {}

                    users.update_one( {"userid": user['userid']}, {"$set": {'notifications': user['notifications'] }} )
                    return False

                else:
                    if notification in user['notifications'][dino_id]:
                        return user['notifications'][dino_id][notification]
                    else:
                        user['notifications'][dino_id][notification] = False
                        users.update_one( {"userid": user['userid']}, {"$set": {'notifications': user['notifications'] }} )
                        return False


        if met == 'send':

            if notification not in ['friend_request', "friend_rejection", "friend_accept"]:
                if dino_id in user['notifications'].keys():
                    user['notifications'][dino_id][notification] = True
                else:
                    user['notifications'][dino_id] = {}
                    user['notifications'][dino_id][notification] = True
                    users.update_one( {"userid": user['userid']}, {"$set": {'notifications': user['notifications'] }} )
            else:
                user['notifications'][notification] = True

            users.update_one( {"userid": user['userid']}, {"$set": {'notifications': user['notifications'] }} )

            if user['settings']['notifications'] == True:
                try:
                    chat = bot.get_chat(user['userid'])
                except:
                    return False

                try:
                    dinoname = user['dinos'][ dino_id ]['name']
                except:
                    dinoname = 'none'

                if notification == "5_min_incub":

                    if user['language_code'] == 'ru':
                        text = f'🥚 | {chat.first_name}, ваш динозавр вылупится через 5 минут!'
                    else:
                        text = f'🥚 | {chat.first_name}, your dinosaur will hatch in 5 minutes!'

                    try:
                        bot.send_message(user['userid'], text)
                    except:
                        pass

                if notification == "incub":

                    if user['language_code'] == 'ru':
                        text = f'🦖 | {chat.first_name}, динозавр вылупился! 🎉'
                    else:
                        text = f'🦖 | {chat.first_name}, the dinosaur has hatched! 🎉'

                    try:
                        bot.send_message(user['userid'], text, reply_markup = Functions.inline_markup(bot, f'open_dino_profile', chat.id, ['Открыть профиль', 'Open a profile'], dino_id) )
                    except:
                        pass

                if notification == "need_eat":

                    if user['language_code'] == 'ru':
                        text = f'🍕 | {chat.first_name}, {dinoname} хочет кушать, его потребность в еде опустилась до {arg}%!'
                    else:
                        text = f'🍕 | {chat.first_name}, {dinoname} wants to eat, his need for food has dropped to {arg}%!'

                    try:
                        bot.send_message(user['userid'], text, reply_markup = Functions.inline_markup(bot, f'open_dino_profile', chat.id, ['Открыть профиль', 'Open a profile'], dino_id))
                    except:
                        pass

                if notification == "need_game":

                    if user['language_code'] == 'ru':
                        text = f'🎮 | {chat.first_name}, {dinoname} хочет играть, его потребность в игре опустилось до {arg}%!'
                    else:
                        text = f'🎮 | {chat.first_name}, {dinoname} wants to play, his need for the game has dropped to {arg}%!'

                    try:
                        bot.send_message(user['userid'], text, reply_markup = Functions.inline_markup(bot, f'open_dino_profile', chat.id, ['Открыть профиль', 'Open a profile'], dino_id))
                    except:
                        pass

                if notification == "need_mood":

                    if user['language_code'] == 'ru':
                        text = f'🦖 | {chat.first_name}, у {dinoname} плохое настроение, его настроение опустилось до {arg}%!'
                    else:
                        text = f'🦖 | {chat.first_name}, {dinoname} is in a bad mood, his mood has sunk to {arg}%!'

                    try:
                        bot.send_message(user['userid'], text, reply_markup = Functions.inline_markup(bot, f'open_dino_profile', chat.id, ['Открыть профиль', 'Open a profile'], dino_id))
                    except:
                        pass

                if notification in ["need_heal", "need_heal!"]:

                    if user['language_code'] == 'ru':
                        text = f'❤ | {chat.first_name}, у {dinoname} плохое самочувствие, его здоровье опустилось до {arg}%!'
                    else:
                        text = f'❤ | {chat.first_name}, {dinoname} is feeling unwell, his health has dropped to {arg}%!'

                    try:
                        bot.send_message(user['userid'], text, reply_markup = Functions.inline_markup(bot, 'inventory', chat.id, ['Открыть инвентарь', 'Open inventory']) )
                    except:
                        pass

                if notification == "need_unv":

                    if user['language_code'] == 'ru':
                        text = f'🌙 | {chat.first_name}, {dinoname} хочет спать, его характеристика сна опустилось до {arg}%!'
                    else:
                        text = f'🌙 | {chat.first_name}, {dinoname} wants to sleep, his sleep characteristic dropped to {arg}%!'

                    try:
                        bot.send_message(user['userid'], text, reply_markup = Functions.inline_markup(bot, f'open_dino_profile', chat.id, ['Открыть профиль', 'Open a profile'], dino_id))
                    except:
                        pass

                if notification == "dead":

                    if user['language_code'] == 'ru':
                        text = f'💥 | {chat.first_name}, ваш динозаврик.... Умер...'
                        nl = "🧩 Проект: Возрождение"
                        nl2 = '🎮 Инвентарь'
                    else:
                        text = f'💥 | {chat.first_name}, your dinosaur.... Died...'
                        nl = '🧩 Project: Rebirth'
                        nl2 = '🎮 Inventory'

                    if Functions.inv_egg(user) == False and user['lvl'][0] <= 5:
                        markup = types.ReplyKeyboardMarkup(resize_keyboard = True)
                        markup.add(nl)

                        try:
                            bot.send_message(user['userid'], text, reply_markup = markup)
                        except:
                            pass

                    else:
                        markup = types.ReplyKeyboardMarkup(resize_keyboard = True)
                        markup.add(nl2)

                        if user['language_code'] == 'ru':
                            text += f'\n\nНе стоит печалиться! Загляните в инвентарь, там у вас завалялось ещё одно яйцо!'

                        else:
                            text += f'\n\nDo not be sad! Take a look at the inventory, there you have another egg lying around!'

                        try:
                            bot.send_message(user['userid'], text, reply_markup = markup)
                        except:
                            pass

                if notification == "woke_up":

                    if user['language_code'] == 'ru':
                        text = f'🌙 | {chat.first_name}, {dinoname} проснулся и полон сил!'
                    else:
                        text = f'🌙 | {chat.first_name}, {dinoname} is awake and full of energy!'

                    try:
                        bot.send_message(user['userid'], text, reply_markup = Functions.inline_markup(bot, f'open_dino_profile', chat.id, ['Открыть профиль', 'Open a profile'], dino_id))
                    except Exception as error:
                        print('woke_up ', error)
                        pass

                if notification == "game_end":

                    if user['language_code'] == 'ru':
                        text = f'🎮 | {chat.first_name}, {dinoname} прекратил играть!'
                    else:
                        text = f'🎮 | {chat.first_name}, {dinoname} has stopped playing!'

                    try:
                        bot.send_message(user['userid'], text, reply_markup = Functions.inline_markup(bot, f'open_dino_profile', chat.id, ['Открыть профиль', 'Open a profile'], dino_id))
                    except:
                        pass


                if notification == "journey_end":

                    try:
                        Functions.journey_end_log(bot, user['userid'], dino_id)
                    except:
                        pass

                if notification == "friend_request":

                    if user['language_code'] == 'ru':
                        text = f'💬 | {chat.first_name}, вам поступил запрос в друзья!'
                    else:
                        text = f'💬 | {chat.first_name}, you have received a friend request!'

                    try:
                        bot.send_message(user['userid'], text, reply_markup = Functions.inline_markup(bot, 'requests', chat.id, ['Проверить запросы', 'Check requests']))
                    except:
                        pass

                if notification == "friend_accept":

                    if user['language_code'] == 'ru':
                        text = f'💬 | {chat.first_name}, {arg} принял запрос в друзья!'
                    else:
                        text = f'💬 | {chat.first_name}, {arg} accepted a friend request!'

                    try:
                        bot.send_message(user['userid'], text)
                    except:
                        pass

                if notification == "friend_rejection":

                    if user['language_code'] == 'ru':
                        text = f'💬 | {chat.first_name}, ваш запрос в друзья {arg}, был отклонён...'
                    else:
                        text = f'💬 | {chat.first_name}, your friend request {arg} has been rejected...'

                    try:
                        bot.send_message(user['userid'], text)
                    except:
                        pass

                if notification == "hunting_end":

                    if user['language_code'] == 'ru':
                        text = f'🍕 | {chat.first_name}, {dinoname} вернулся со сбора пищи!'
                    else:
                        text = f'🍕 | {chat.first_name}, {dinoname} is back from collecting food!'

                    try:
                        bot.send_message(user['userid'], text, reply_markup = Functions.inline_markup(bot, 'inventory', chat.id, ['Открыть инвентарь', 'Open inventory']) )
                    except:
                        pass

                if notification == "acc_broke":

                    item_d = items_f['items'][arg]

                    if user['language_code'] == 'ru':
                        text = f'🛠 | {chat.first_name}, ваш аксессуар {item_d["nameru"]} сломался!'
                    else:
                        text = f'🛠 | {chat.first_name}, your accessory {item_d["nameen"]} broke!'

                    try:
                        bot.send_message(user['userid'], text, reply_markup = Functions.inline_markup(bot, 'inventory', chat.id, ['Открыть инвентарь', 'Open inventory']) )
                    except:
                        pass

                if notification == "quest_completed":

                    quest = arg['quest']

                    if user['language_code'] == 'ru':
                        text = f'🎉 | {chat.first_name}, квест {arg["name"]} выполнен!'
                    else:
                        text = f'🎉 | {chat.first_name}, quest {arg["name"]} completed!'

                    if user['language_code'] == 'ru':
                        text += f'\n\n👑 | Награда\nМонеты: '
                    else:
                        text += f'\n\n👑 | Reward\nМонеты: '

                    text += f"{quest['reward']['money']}💰\n"

                    if quest['reward']['items'] != []:

                        if user['language_code'] == 'ru':
                            text += f"Предметы: {', '.join(Functions.sort_items_col(quest['reward']['items'], 'ru') )}"
                        else:
                            text += f"Items: {', '.join(Functions.sort_items_col(quest['reward']['items'], 'en') )}"

                    try:
                        bot.send_message(user['userid'], text, reply_markup = Functions.inline_markup(bot, f'delete_message', user['userid']) )
                    except:
                        pass


                if notification == "lvl_up":

                    if user['language_code'] == 'ru':
                        text = f'🎉 | {chat.first_name}, ваш уровень повышен! ({arg})'
                    else:
                        text = f'🎉 | {chat.first_name}, your level has been raised! ({arg})'

                    if int(arg) in [20, 40, 60, 80, 100]:

                        if user['language_code'] == 'ru':
                            text = f'\n\n✨ | Теперь у вас появился +1 слот для динозавров!'
                        else:
                            text = f'\n\n✨ | Now you have +1 dinosaur slot!'

                    if int(arg) == 50:

                        if user['language_code'] == 'ru':
                            text = f'\n\n🎴 | Вы на полпути к максимальному уровню, так держать!'
                        else:
                            text = f'\n\n🎴 | You are halfway to the maximum level, keep it up!'

                    if int(arg) == 100:

                        if user['language_code'] == 'ru':
                            text = f'\n\n🎴 | Вы достигли максимального уровня!'
                        else:
                            text = f'\n\n🎴 | You have reached the maximum level!'


                    try:
                        bot.send_message(user['userid'], text)
                    except:
                        pass

                if notification == "quest":

                    if user['language_code'] == 'ru':
                        text = f'🎴 | Вы получили новый квест!'
                    else:
                        text = f'🎴 | You have received a new quest!'

                    try:
                        bot.send_message(user['userid'], text)
                    except:
                        pass

                if notification == "product_bought":

                    if user['language_code'] == 'ru':
                        text = f'💡 | Ваш продукт на рынке был куплен!\nВам начислено {arg} монет!'
                    else:
                        text = f'💡 | Your product has been purchased on the market!\nYou have been awarded {arg} coins!'

                    try:
                        bot.send_message(user['userid'], text)
                    except:
                        pass


                # else:
                #     print(notification, 'notification')

    @staticmethod
    def check_data(t = None, ind = None, zn = None, m = 'ncheck'):
        global checks_data

        if m == 'check':
            return checks_data

        if t not in ['memory', 'incub',  'col_main', 'col_notif', 'col']:
            if len(checks_data[t][ind]) >= checks_data['col']:
                checks_data[t][ind] = []

        if m != 'check':
            if t in ['memory', 'incub']:
                checks_data[t][ind] = zn

            elif t not in ['col', 'memory']:
                checks_data[t][ind].append(zn)

            else:
                checks_data[t] = zn

    @staticmethod
    def inv_egg(user):

        for i in user['inventory']:
            if items_f['items'][i['item_id']]['type'] == 'egg':
                return True

        return False

    @staticmethod
    def random_items(rand_d:dict):

        '''
            example = {
            'com': [], 'unc': [], 'rar': [], 'myt': [], 'leg': []
            }
        '''

        r_event = random.randint(1, 100)
        if r_event >= 1 and r_event <= 50: #50%
            items = rand_d['com']

        elif r_event > 50 and r_event <= 75: #25%
            items = rand_d['unc']

        elif r_event > 75 and r_event <= 90: #15%
            items = rand_d['rar']

        elif r_event > 90 and r_event <= 99: #9%
            items = rand_d['myt']

        elif r_event > 99 and r_event <= 100: #1%
            items = rand_d['leg']

        random.shuffle(items)
        return random.choice(items)

    @staticmethod
    def sort_items_col(nls_i:list, lg, col_display = True):
        dct = {}
        nl = []

        for i in nls_i:
            if i not in dct.keys():
                dct[i] = 1
            else:
                dct[i] += 1

        for i in dct.keys():
            it = dct[i]
            name = items_f['items'][i][f'name{lg}']

            if col_display == True:
                nl.append(f"{name} x{it}")
            else:
                nl.append(f"{name}")

        return nl

    @staticmethod
    def item_info(us_item, lg, mark: bool = True):

        def sort_materials(nls_i:list, lg):
            dct = {}
            nl = []

            for i in nls_i:
                if i['item'] not in dct.keys():
                    dct[i['item']] = 1
                else:
                    dct[i['item']] += 1

            itts = []
            for i in nls_i:
                if i not in itts:
                    name = items_f['items'][i['item']][f'name{lg}']
                    if i['type'] == 'endurance':
                        nl.append(f"{name} (⬇ -{i['act']}) x{dct[i['item']]}")
                    else:
                        nl.append(f"{name} x{dct[i['item']]}")

                    itts.append(i)

            return nl

        item_id = us_item['item_id']
        item = items_f['items'][item_id]
        type = item['type']
        d_text = ''

        if item['type'] == '+eat':
            if lg == 'ru':
                type = '🍔 еда'
                d_text = f"*└* Эффективность: {item['act']}"
            else:
                type = '🍔 eat'
                d_text = f"*└* Effectiveness: {item['act']}"

        elif item['type'] == '+unv':
            if lg == 'ru':
                type = '☕ энергетический напиток'
                d_text = f"*└* Эффективность: {item['act']}"
            else:
                type = '☕ energy drink'
                d_text = f"*└* Effectiveness: {item['act']}"

        elif item['type'] == 'freezing':
            if lg == 'ru':
                type = '❄ Заморозка'
                d_text = f"*└* Данный предмет останавливает метаболизм у динозавра, тем самым он замораживается."
            else:
                type = '❄ Freezing'
                d_text = f"*└* This item stops the metabolism of the dinosaur, thereby it freezes."

        elif item['type'] == 'defrosting':
            if lg == 'ru':
                type = '🔥 Разморозка'
                d_text = f"*└* Предмет восстанавливает метаболизм у динозавра."
            else:
                type = '🔥 defrosting'
                d_text = f"*└* The item restores the metabolism of the dinosaur."

        elif item['type'] == 'egg':

            if lg == 'ru':
                eg_q = item['inc_type']
                if item['inc_type'] == 'random': eg_q = 'рандом'
                elif item['inc_type'] == 'com': eg_q = 'обычное'
                elif item['inc_type'] == 'unc': eg_q = 'необычное'
                elif item['inc_type'] == 'rar': eg_q = 'редкое'
                elif item['inc_type'] == 'myt': eg_q = 'мистическое'
                elif item['inc_type'] == 'leg': eg_q = 'легендарное'

                type = '🥚 яйцо динозавра'
                d_text = f"*├* Инкубация: {item['incub_time']}{item['time_tag']}\n"
                d_text += f"*└* Редкость яйца: {eg_q}"

            else:
                if item['inc_type'] == 'random': eg_q = 'random'
                elif item['inc_type'] == 'com': eg_q = 'common'
                elif item['inc_type'] == 'unc': eg_q = 'uncommon'
                elif item['inc_type'] == 'rare': eg_q = 'rare'
                elif item['inc_type'] == 'myt': eg_q = 'mystical'
                elif item['inc_type'] == 'leg': eg_q = 'legendary'

                type = '🥚 dinosaur egg'
                d_text = f"*└* Incubation: {item['incub_time']}{item['time_tag']}\\n"
                d_text += f"*└* The rarity of eggs: {eg_q}"

        elif item['type'] in ['game_ac', 'unv_ac', 'journey_ac', 'hunt_ac']:
            if lg == 'ru':
                type = '💍 активный предмет'
                d_text = f"*└* {item['descriptionru']}"
            else:
                type = '💍 active game item'
                d_text = f"*└* {item['descriptionen']}"

        elif item['type'] in ['None', 'none']:
            if lg == 'ru':
                type = '🕳 пустышка'
                d_text = f"*└* Ничего не делает и не для чего не нужна"
            else:
                type = '🕳 dummy'
                d_text = f"*└* Does nothing and is not needed for anything"

        elif item['type'] == 'material':
            if lg == 'ru':
                type = '🧱 материал'
                d_text = f"*└* Данный предмет нужен для изготовления."
            else:
                type = '🧱 material'
                d_text = f"*└* This item is needed for manufacturing."

        elif item['type'] == 'recipe':
            if lg == 'ru':
                type = '🧾 рецепт создания'

                d_text = f'*├* Создаёт: {", ".join(sort_materials( item["create"], "ru" ))}\n'
                d_text += f'*└* Материалы: {", ".join(sort_materials( item["materials"], "ru"))}\n\n'
                d_text +=  f"{item['descriptionru']}"
            else:
                type = '🧾 recipe for creation'

                d_text = f'*├* Creates: {", ".join(sort_materials( item["create"], "en" ))}\n'
                d_text += f'*└* Materials: {", ".join(sort_materials( item["materials"], "en"))}\n\n'
                d_text +=  f"{item['descriptionen']}"

        elif item['type'] == 'weapon':
            if lg == 'ru':
                if item['class'] == 'far':
                    type = '🔫 Оружие'
                    d_text += f'*├* Боеприпасы: {", ".join(Functions.sort_items_col( item["ammunition"], "ru", False ))}\n'

                if item['class'] == 'near':
                    type = '🗡 Оружие'

                d_text += f"*└* Урон: {item['damage']['min']} - {item['damage']['max']}"


            else:
                if item['class'] == 'far':
                    type = '🔫 Weapon'
                    d_text += f'*├* Ammunition: {", ".join(Functions.sort_items_col( item["ammunition"], "en", False ))}\n'

                if item['class'] == 'near':
                    type = '🗡 Weapon'

                d_text = f"*└* Damage: {item['damage']['min']} - {item['damage']['max']}"

        elif item['type'] == 'ammunition':
            if lg == 'ru':
                type = '🌠 Боеприпас'
                d_text += f'*└* Доп. урон: {item["add_damage"]}\n'

            else:
                type = '🌠 Ammunition'
                d_text += f'*└* Add. damage: {item["add_damage"]}\n'

        elif item['type'] == 'armor':
            if lg == 'ru':
                type = '🛡 Броня'
                d_text += f'*└* Отражение: {item["reflection"]}\n'

            else:
                type = '🛡 Armor'
                d_text += f'*└* Reflection: {item["reflection"]}\n'

        elif item['type'] == 'backpack':
            if lg == 'ru':
                type = '🎒 Хранилище'
                d_text += f'*└* Вместимость: {item["capacity"]}\n'

            else:
                type = '🎒 Storage'
                d_text += f'*└* Capacity: {item["capacity"]}\n'


        if list(set([ '+mood', '+energy', '+eat', '+hp' ]) & set(item.keys())) != []:
            if lg == 'ru':
                d_text += f'\n\n*┌* *🍡 Дополнительные бонусы*\n'
            else:
                d_text += f'\n\n*┌* *🍡 Additional bonuses*\n'

            if '+mood' in item.keys():
                if lg == 'ru':
                    d_text += f"*└* Повышение настроения: {item['+mood']}%\n"
                else:
                    d_text += f"*└* Mood boost: {item['+mood']}%\n"

            if '+eat' in item.keys():
                if lg == 'ru':
                    d_text += f"*└* Повышение сытости: {item['+eat']}%\n"
                else:
                    d_text += f"*└* Increased satiety: {item['+eat']}%\n"

            if '+energy' in item.keys():
                if lg == 'ru':
                    d_text += f"*└* Повышение энергии: {item['+energy']}%\n"
                else:
                    d_text += f"*└* Energy Boost: {item['+energy']}%\n"

            if '+hp' in item.keys():
                if lg == 'ru':
                    d_text += f"*└* Повышение здоровья: {item['+hp']}%\n"
                else:
                    d_text += f"*└* Improving health: {item['+hp']}%\n"

        if list(set([ '-mood', "-eat", '-energy', '-hp' ]) & set(item.keys())) != []:
            if lg == 'ru':
                d_text += f'\n\n*┌* *📌 Дополнительные штрафы*\n'
            else:
                d_text += f'\n\n*┌* *📌 Additional penalties*\n'

            if '-mood' in item.keys():
                if lg == 'ru':
                    d_text += f"*└* Понижение настроения: {item['-mood']}%\n"
                else:
                    d_text += f"*└* Lowering the mood: {item['-mood']}%\n"

            if '-eat' in item.keys():
                if lg == 'ru':
                    d_text += f"*└* Понижение сытости: {item['-eat']}%\n"
                else:
                    d_text += f"*└* Reducing satiety: {item['-eat']}%\n"

            if '-energy' in item.keys():
                if lg == 'ru':
                    d_text += f"*└* Понижение энергии: {item['-energy']}%\n"
                else:
                    d_text += f"*└* Energy reduction: {item['-energy']}%\n"

            if '-hp' in item.keys():
                if lg == 'ru':
                    d_text += f"*└* Понижение здоровья: {item['-hp']}%\n"
                else:
                    d_text += f"*└* Lower health: {item['-hp']}%\n"

        if lg == 'ru':
            text =  f"*┌* *🎴 Информация о предмете*\n"
            text += f"*├* Название: {item['nameru']}\n"
        else:
            text =  f"*┌* *🎴 Subject information*\n"
            text += f"*├* Name: {item['nameen']}\n"

        if 'rank' in item.keys():

            if lg == 'ru':
                text +=  f"*├* Ранг: "
            else:
                text +=  f"*├* Rank: "

            if item['rank'] == 'common':

                if lg == 'ru':
                    text += '🤍 Обычный\n'
                else:
                    text += '🤍 Сommon\n'

            if item['rank'] == 'uncommon':

                if lg == 'ru':
                    text += '💚 Необычный\n'
                else:
                    text += '💚 Uncommon\n'

            if item['rank'] == 'rare':

                if lg == 'ru':
                    text += '💙 Редкий\n'
                else:
                    text += '💙 Rare\n'

            if item['rank'] == 'mystical': #мистическое

                if lg == 'ru':
                    text += '💜 Мистический\n'
                else:
                    text += '💜 Mystical\n'

            if item['rank'] == 'legendary':

                if lg == 'ru':
                    text += '💛 Легендарный\n'
                else:
                    text += '💛 Legendary\n'

            if item['rank'] == 'mythical': #мифическое

                if lg == 'ru':
                    text += '❤ Мифический (За гранью)\n'
                else:
                    text += '❤ Mythical\n'

        else:
            if lg == 'ru':
                text +=  f"*├* Ранг: Отсутствует\n"
            else:
                text +=  f"*├* Rank: None\n"

        if 'abilities' in us_item.keys():
            if 'uses' in us_item['abilities'].keys():

                if lg == 'ru':
                    text += f"*├* Использований: {us_item['abilities']['uses']}\n"
                else:
                    text += f"*├* Uses: {us_item['abilities']['uses']}\n"

            if 'endurance' in us_item['abilities'].keys():
                if lg == 'ru':
                    text += f"*├* Прочность: {us_item['abilities']['endurance']}\n"
                else:
                    text += f"*├* Endurance: {us_item['abilities']['endurance']}\n"

            if 'mana' in us_item['abilities'].keys():
                if lg == 'ru':
                    text += f"*├* Мана: {us_item['abilities']['mana']}\n"
                else:
                    text += f"*├* Mana: {us_item['abilities']['mana']}\n"

            if 'stack' in us_item['abilities'].keys():
                if lg == 'ru':
                    text += f"*├* В наборе: {us_item['abilities']['stack']} / {item['max_stack']}\n"
                else:
                    text += f"*├* In the set: {us_item['abilities']['stack']} / {item['max_stack']}\n"

        if lg == 'ru':
            text += f"*├* Тип: {type}\n"
            text += d_text
            in_text = ['🔮 | Использовать', '🗑 | Выбросить', '🔁 | Передать', '🛠 | Создаваемый предмет']

        else:
            text += f"*├* Type: {type}\n"
            text += d_text
            in_text = ['🔮 | Use', '🗑 | Delete', '🔁 | Transfer', '🛠 | Сreated item']

        if 'image' in item.keys():
            try:
                image = open(f"images/items/{item['image']}.png", 'rb')
            except Exception as e:
                image = None
                print(f'item {item_id} image incorrect')

        else:
            image = None

        if mark == True:
            markup_inline = types.InlineKeyboardMarkup()
            markup_inline.add( types.InlineKeyboardButton( text = in_text[0], callback_data = f"item_{Functions.qr_item_code(us_item)}"),  types.InlineKeyboardButton( text = in_text[1], callback_data = f"remove_item_{Functions.qr_item_code(us_item)}") )
            markup_inline.add( types.InlineKeyboardButton( text = in_text[2], callback_data = f"exchange_{Functions.qr_item_code(us_item)}") )

            if item['type'] == 'recipe':
                if len(item["create"]) == 1:
                    markup_inline.add( types.InlineKeyboardButton( text = in_text[3], callback_data = f"iteminfo_{item['create'][0]['item']}") )

            if "ns_craft" in item.keys():
                for cr_dct_id in item["ns_craft"].keys():
                    cr_dct = item["ns_craft"][cr_dct_id]
                    bt_text = f''

                    if lg == 'ru':
                        bt_text += ", ".join(Functions.sort_items_col( item["ns_craft"][cr_dct_id]["materials"], "ru"))

                    else:
                        bt_text += ", ".join(Functions.sort_items_col( item["ns_craft"][cr_dct_id]["materials"], "en"))

                    bt_text += ' = '

                    if lg == 'ru':
                        bt_text += ", ".join(Functions.sort_items_col( item["ns_craft"][cr_dct_id]["create"], "ru" ))

                    else:
                        bt_text += ", ".join(Functions.sort_items_col( item["ns_craft"][cr_dct_id]["create"], "en" ))

                    markup_inline.add( types.InlineKeyboardButton( text = bt_text, callback_data = f"ns_craft {Functions.qr_item_code(us_item)} {cr_dct_id}") )

            return text, markup_inline, image

        else:
            return text, image

    @staticmethod
    def exchange(bot, message, user_item, bd_user, user):

        def zero(message, user_item, bd_user):

            if message.text not in ['Yes, transfer the item', 'Да, передать предмет']:
                bot.send_message(message.chat.id, '❌', reply_markup = Functions.markup(bot, Functions.last_markup(bd_user, alternative = 'profile'), bd_user ))
                return

            friends_id = bd_user['friends']['friends_list']
            page = 1

            friends_name = []
            friends_id_d = {}

            for i in friends_id:
                try:
                    if users.find_one({"userid": int(i)}) != None:
                        fr_name = bot.get_chat(int(i)).first_name
                        friends_name.append(fr_name)
                        friends_id_d[fr_name] = i
                except:
                    pass

            friends_chunks = list(Functions.chunks(list(Functions.chunks(friends_name, 2)), 3))

            def work_pr(message, friends_id, page, friends_chunks, friends_id_d, user_item, mms = None):
                global pages

                if bd_user['language_code'] == 'ru':
                    text = "📜 | Обновление..."
                else:
                    text = "📜 | Update..."

                rmk = types.ReplyKeyboardMarkup(resize_keyboard = True, row_width = 3)

                if friends_chunks == []:

                    if bd_user['language_code'] == 'ru':
                        text = "👥 | Список пуст!"
                    else:
                        text = "👥 | The list is empty!"

                    bot.send_message(message.chat.id, text, reply_markup = Functions.markup(bot, 'profile', bd_user['userid']))

                else:

                    for el in friends_chunks[page-1]:
                        if len(el) == 2:
                            rmk.add(el[0], el[1])
                        else:
                            rmk.add(el[0], ' ')

                    if 3 - len(friends_chunks[page-1]) != 0:
                        for i in list(range(3 - len(friends_chunks[page-1]))):
                            rmk.add(' ', ' ')

                    if len(friends_chunks) > 1:
                        if bd_user['language_code'] == 'ru':
                            com_buttons = ['◀', '↪ Назад', '▶']
                        else:
                            com_buttons = ['◀', '↪ Back', '▶']

                        rmk.add(com_buttons[0], com_buttons[1], com_buttons[2])
                    else:
                        if bd_user['language_code'] == 'ru':
                            com_buttons = '↪ Назад'
                        else:
                            com_buttons = '↪ Back'

                        rmk.add(com_buttons)

                    def ret(message, bd_user, page, friends_chunks, friends_id, friends_id_d, user_item):
                        if message.text in ['↪ Назад', '↪ Back']:
                            res = None
                        else:
                            res = message.text

                        if res == None:
                            if bd_user['language_code'] == 'ru':
                                text = "👥 | Возвращение в меню друзей!"
                            else:
                                text = "👥 | Return to the friends menu!"

                            bot.send_message(message.chat.id, text, reply_markup = Functions.markup('friends-menu', bd_user['userid']))

                        else:
                            mms = None
                            if res == '◀':
                                if page - 1 == 0:
                                    page = 1
                                else:
                                    page -= 1

                                work_pr(message, friends_id, page, friends_chunks, friends_id_d, user_item, mms = mms)

                            if res == '▶':
                                if page + 1 > len(friends_chunks):
                                    page = len(friends_chunks)
                                else:
                                    page += 1

                                work_pr(message, friends_id, page, friends_chunks, friends_id_d, user_item, mms = mms)

                            else:
                                if res in list(friends_id_d.keys()):
                                    fr_id = friends_id_d[res]
                                    bd_user = users.find_one({"userid": bd_user['userid']})
                                    two_user = users.find_one({"userid": fr_id})

                                    data_items = items_f['items']
                                    data_item = data_items[ user_item['item_id'] ]
                                    if data_item['type'] == '+eat':
                                        eat_c = Functions.items_counting(two_user, '+eat')
                                        if eat_c >= 800:

                                            if bd_user['language_code'] == 'ru':
                                                text = f'🌴 | У данного пользователя очень много еды, в данный момент вы не можете отправить ему {data_item["nameru"]}!'
                                            else:
                                                text = f"🌴 | This user has a lot of food, at the moment you can't send him {data_item['nameen']}!"

                                            bot.send_message(message.chat.id, text, reply_markup = Functions.markup(bot, Functions.last_markup(bd_user, 'profile') , bd_user))
                                            return

                                    col = 1
                                    mx_col = 0
                                    for item_c in bd_user['inventory']:
                                        if item_c == user_item:
                                            mx_col += 1

                                    if bd_user['language_code'] == 'ru':
                                        text_col = f"🏓 | Введите сколько вы хотите передать или выберите из списка >"
                                    else:
                                        text_col = f"🏓 | Enter how much you want to transfer or select from the list >"

                                    rmk = types.ReplyKeyboardMarkup(resize_keyboard = True, row_width = 3)

                                    bt_1 = f"x1"
                                    bt_2 = f"x{int(mx_col / 2)}"
                                    bt_3 = f"x{mx_col}"

                                    col_l = [[], [1, int(mx_col / 2), mx_col]]

                                    col_l[0].append(bt_1), col_l[0].append(bt_2), col_l[0].append(bt_3)

                                    if mx_col == 1:

                                        rmk.add(bt_1)

                                    elif mx_col >= 4:

                                        rmk.add(bt_1, bt_2, bt_3)

                                    elif mx_col > 1:

                                        rmk.add(bt_1, bt_3)

                                    if bd_user['language_code'] == 'ru':
                                        rmk.add('↩ Назад')
                                    else:
                                        rmk.add('↩ Back')

                                    def tr_complete(message, bd_user, user_item, mx_col, col_l, two_user):

                                        if message.text in ['↩ Back', '↩ Назад']:

                                            if bd_user['language_code'] == 'ru':
                                                text = "👥 | Отмена!"
                                            else:
                                                text = "👥 | Cancel!"

                                            bot.send_message(message.chat.id, text, reply_markup = Functions.markup(bot, 'profile', bd_user['userid']))
                                            return '12'

                                        try:
                                            col = int(message.text)
                                        except:
                                            if message.text in col_l[0]:
                                                col = col_l[1][ col_l[0].index(message.text) ]

                                            else:

                                                if bd_user['language_code'] == 'ru':
                                                    text = f"Введите корректное число!"
                                                else:
                                                    text = f"Enter the correct number!"

                                                bot.send_message(message.chat.id, text, reply_markup = Functions.markup(bot, 'actions', bd_user))
                                                return

                                        if col < 1:

                                            if bd_user['language_code'] == 'ru':
                                                text = f"Введите корректное число!"
                                            else:
                                                text = f"Enter the correct number!"

                                            bot.send_message(message.chat.id, text, reply_markup = Functions.markup(bot, 'actions', user))
                                            return

                                        if col > mx_col:

                                            if bd_user['language_code'] == 'ru':
                                                text = f"У вас нет столько предметов в инвентаре!"
                                            else:
                                                text = f"You don't have that many items in your inventory!"

                                            bot.send_message(message.chat.id, text, reply_markup = Functions.markup(bot, 'actions', user))
                                            return

                                        for i in range(col):
                                            bd_user['inventory'].remove(user_item)
                                            users.update_one( {"userid": two_user['userid']}, {"$push": {'inventory': user_item }} )

                                        users.update_one( {"userid": bd_user['userid']}, {"$set": {'inventory': bd_user['inventory'] }} )

                                        if bd_user['language_code'] == 'ru':
                                            text = f'🔁 | Предмет(ы) был отправлен игроку!'
                                        else:
                                            text = f"🔁 | The item(s) has been sent to the player!"

                                        bot.send_message(message.chat.id, text)

                                        user = bot.get_chat( bd_user['userid'] )

                                        if two_user['language_code'] == 'ru':
                                            text = f"🦄 | Единорог-курьер доставил вам предмет(ы) от {user.first_name}, загляните в инвентарь!\n\n📜 Доставлено:\n{items_f['items'][str(user_item['item_id'])]['nameru']} x{col}"
                                        else:
                                            text = f"🦄 | The Unicorn-courier delivered you an item(s) from {user.first_name}, take a look at the inventory!\n\n📜 Delivered:\n{items_f['items'][str(user_item['item_id'])]['nameen']} x{col}"

                                        bot.send_message(two_user['userid'], text, reply_markup = Functions.inline_markup(bot, 'inventory', two_user['userid'], ['Проверить инвентарь', 'Check inventory']))

                                        Functions.user_inventory(bot, user, message)

                                    msg = bot.send_message(message.chat.id, text_col, reply_markup = rmk)
                                    bot.register_next_step_handler(msg, tr_complete, bd_user, user_item, mx_col, col_l, two_user)

                    if mms == None:
                        msg = bot.send_message(message.chat.id, text, reply_markup = rmk)
                    else:
                        msg = mms
                    bot.register_next_step_handler(msg, ret, bd_user, page, friends_chunks, friends_id, friends_id_d, user_item)

            work_pr(message, friends_id, page, friends_chunks, friends_id_d, user_item)

        if bd_user['language_code'] == 'ru':
            com_buttons = ['Да, передать предмет', '↪ Назад']
            text = '🔁 | Вы уверены что хотите передать предмет другому пользователю?'
        else:
            com_buttons = ['Yes, transfer the item', '↪ Back']
            text = '🔁 | Are you sure you want to transfer the item to another user?'

        rmk = types.ReplyKeyboardMarkup(resize_keyboard = True, row_width = 1)
        rmk.add(com_buttons[0], com_buttons[1])

        msg = bot.send_message(message.chat.id, text, reply_markup = rmk)
        bot.register_next_step_handler(msg, zero, user_item, bd_user)

    def member_profile(bot, mem_id, lang):

        user = bot.get_chat(int(mem_id))
        bd_user = users.find_one({"userid": user.id})

        expp = 5 * bd_user['lvl'][0] * bd_user['lvl'][0] + 50 * bd_user['lvl'][0] + 100
        n_d = len(list(bd_user['dinos']))
        t_dinos = ''
        for k in bd_user['dinos']:
            bd_user = Functions.dino_q(bd_user)
            i = bd_user['dinos'][k]


            if list( bd_user['dinos']) [ len(bd_user['dinos']) - 1 ] == k:
                n = '└'

            else:
                n = '├'

            if i['status'] == 'incubation':
                t_incub = i['incubation_time'] - time.time()
                time_end = Functions.time_end(t_incub, True)

                if lang == 'ru':

                    qual = '🎲 Случайное'
                    if 'quality' in i.keys():
                        pre_qual = i['quality']

                        if pre_qual == 'com':
                            qual = '🤍 Обычное'
                        if pre_qual == 'unc':
                            qual = '💚 Необычное'
                        if pre_qual == 'rar':
                            qual = '💙 Редкое'
                        if pre_qual == 'myt':
                            qual = '💜 Мистическое'
                        if pre_qual == 'leg':
                            qual = '💛 Легендарное'

                    t_dinos += f"\n   *{n}* Статус: яйцо\n      *├* Редкость: {qual}\n      *└* Осталось: {time_end}\n"

                else:

                    qual = '🎲 Random'
                    if 'quality' in i.keys():
                        pre_qual = i['quality']

                        if pre_qual == 'com':
                            qual = '🤍 Common'
                        if pre_qual == 'unc':
                            qual = '💚 Uncommon'
                        if pre_qual == 'rar':
                            qual = '💙 Rare'
                        if pre_qual == 'myt':
                            qual = '💜 Mystical'
                        if pre_qual == 'leg':
                            qual = '💛 Legendary'


                    t_dinos += f"\n   *{n}*\n      *├* Status: egg\n      *├* Rare: {qual}\n      *└* Left: {time_end}\n"

            if i['status'] == 'dino':

                stat = i['activ_status']
                if lang == 'ru':

                    if i['activ_status'] == 'pass_active':
                        stat = '🧩 ничего не делает'

                    elif i['activ_status'] == 'sleep':
                        stat = '💤 спит'

                    elif i['activ_status'] == 'game':
                        stat = '🕹 играет'

                    elif i['activ_status'] == 'hunting':
                        stat = '🌿 собирает еду'

                    elif i['activ_status'] == 'journey':
                        stat = '🎴 путешествует'

                    elif i['activ_status'] == 'dungeon':
                        stat = '🗻 в подземелье'

                    elif i['activ_status'] == 'freezing':
                        stat = '❄ заморожен'

                    dino = json_f['elements'][str(i['dino_id'])]
                    pre_qual = i['quality']
                    qual = ''
                    if pre_qual == 'com':
                        qual = '🤍 Обычный'
                    if pre_qual == 'unc':
                        qual = '💚 Необычный'
                    if pre_qual == 'rar':
                        qual = '💙 Редкий'
                    if pre_qual == 'myt':
                        qual = '💜 Мистический'
                    if pre_qual == 'leg':
                        qual = '💛 Легендарный'

                    t_dinos += f"\n   *{n}* {i['name'].replace('*', '')}\n      *├* Статус: {stat}\n      *└* Редкость: {qual}\n"

                else:

                    if i['activ_status'] == 'pass_active':
                        stat = '🧩 does nothing'

                    elif i['activ_status'] == 'sleep':
                        stat = '💤 sleeping'

                    elif i['activ_status'] == 'game':
                        stat = '🕹 is playing'

                    elif i['activ_status'] == 'hunting':
                        stat = '🌿 collects food'

                    elif i['activ_status'] == 'journey':
                        stat = '🎴 travels'

                    elif i['activ_status'] == 'dungeon':
                        stat = '🗻 in dungeon'

                    elif i['activ_status'] == 'freezing':
                        stat = '❄ freezing'

                    dino = json_f['elements'][str(i['dino_id'])]
                    pre_qual = i['quality']
                    qual = ''
                    if pre_qual == 'com':
                        qual = '🤍 Common'
                    if pre_qual == 'unc':
                        qual = '💚 Uncommon'
                    if pre_qual == 'rar':
                        qual = '💙 Rare'
                    if pre_qual == 'myt':
                        qual = '💜 Mystical'
                    if pre_qual == 'leg':
                        qual = '💛 Legendary'

                    t_dinos += f"\n   *{n}* {i['name'].replace('*', '')}\n      *└* Status: {stat}\n      *└* Rare: {qual}\n"

        if lang == 'ru':

            #act_items
            act_ii = {}
            for d_id in bd_user['activ_items'].keys():
                act_ii[d_id] = []
                for itmk in bd_user['activ_items'][d_id].keys():
                    itm = bd_user['activ_items'][d_id][itmk]
                    if itm == None:
                        act_ii[d_id].append('-')
                    else:
                        item = items_f['items'][str(itm['item_id'])]['nameru']
                        if 'abilities' in itm.keys() and 'endurance' in itm['abilities'].keys():
                            act_ii[d_id].append(f"{item} ({itm['abilities']['endurance']})")
                        else:
                            act_ii[d_id].append(f'{item}')

            text =  f"*┌* *🎴 Профиль пользователя*\n"
            text += f"*├* Имя: {user.first_name}\n"
            text += f"*└* ID: `{user.id}`\n\n"
            text += f"*┌* Уровень: {bd_user['lvl'][0]}\n"
            text += f"*├* Опыт: {bd_user['lvl'][1]} / {expp}\n"
            text += f"*└* Монеты: {bd_user['coins']}"
            text += f'\n\n'
            text += f"*┌* *🦖 Динозавры*\n"
            text += f"*├* Количество: {n_d}\n"
            text += f"*├* Динозавры:\n{t_dinos}"
            text += f'\n'
            text += f"*┌* *👥 Друзья*\n"
            text += f"*└* Количество: {len(bd_user['friends']['friends_list'])}"
            text += f'\n\n'
            text += f"*┌* *🎈 Инвентарь*\n"
            text += f"*└* Предметов: {len(bd_user['inventory'])}"
            text += f'\n\n'
            text += f"*┌* *💍 Аксессуары*\n"

            for i in act_ii.keys():
                try:
                    d_n = bd_user['dinos'][i]['name']
                except:
                    break

                text += f"\n*┌* 🦖 > {d_n.replace('*', '')}\n"
                text += f"*├* 🌙 Сон: {act_ii[i][3]}\n"
                text += f"*├* 🎮 Игра: {act_ii[i][0]}\n"
                text += f"*├* 🌿 Сбор пищи: {act_ii[i][1]}\n"
                text += f"*└* 🎍 Путешествие: {act_ii[i][2]}\n"

        else:
            #act_items
            act_ii = {}
            for d_id in bd_user['activ_items'].keys():
                act_ii[d_id] = []
                for itmk in bd_user['activ_items'][d_id].keys():
                    itm = bd_user['activ_items'][d_id][itmk]
                    if itm == None:
                        act_ii[d_id].append('-')
                    else:
                        item = items_f['items'][str(itm['item_id'])]['nameen']
                        act_ii[d_id].append(item)

            text =  f"*┌**🎴 User profile*\n"
            text += f"*├* Name: {user.first_name}\n"
            text += f"*└* ID: `{user.id}`\n\n"
            text += f"*┌* Level: {bd_user['lvl'][0]}\n"
            text += f"*├* Experience: {bd_user['lvl'][1]} / {expp}\n"
            text += f"*└* Coins: {bd_user['coins']}"
            text += f'\n\n'
            text += f"*┌**🦖 Dinosaurs*\n"
            text += f"*├* Number: {n_d}\n"
            text += f"*├* Dinosaurs:\n{t_dinos}"
            text += f'\n'
            text += f"*┌**👥 Friends*\n"
            text += f"*└* Quantity: {len(bd_user['friends']['friends_list'])}"
            text += f'\n\n'
            text += f"*┌* *🎈 Inventory*\n"
            text += f"*└* Items: {len(bd_user['inventory'])}"
            text += f'\n\n'
            text += f"*┌* *💍 Accessories*\n"

            for i in act_ii.keys():
                try:
                    d_n = bd_user['dinos'][i]['name']
                except:
                    break

                text += f"\n*┌* 🦖 > {d_n.replace('*', '')}\n"
                text += f"*├* 🌙 Sleep: {act_ii[i][3]}\n"
                text += f"*├* 🎮 Game: {act_ii[i][0]}\n"
                text += f"*├* 🌿 Collecting food: {act_ii[i][1]}\n"
                text += f"*└* 🎍 Journey: {act_ii[i][2]}"

        return text

    @staticmethod
    def rayt_update(met = "save", lst_save = None):
        global reyt_

        if met == 'save':
            reyt_ = lst_save

        if met == 'check':
            return reyt_

    @staticmethod
    def get_dict_item(item_id:str, preabil:dict = None):

        item = items_f['items'][item_id]
        d_it = {'item_id': item_id}
        if 'abilities' in item.keys():
            abl = {}
            for k in item['abilities'].keys():

                if type(item['abilities'][k]) == int:
                    abl[k] = item['abilities'][k]

                elif type(item['abilities'][k]) == dict:
                    abl[k] = Functions.rand_d( item['abilities'][k] )

            d_it['abilities'] = abl

        if preabil != None:

            for ak in d_it['abilities'].keys():
                if ak in preabil.keys():

                    if type(preabil[ak]) == int:
                        d_it['abilities'][ak] = preabil[ak]

                    elif type(preabil[ak]) == dict:
                        d_it['abilities'][ak] = Functions.rand_d(preabil[ak])

        return d_it

    @staticmethod
    def add_item_to_user(user:dict, item_id:str, col:int = 1, type:str = 'add', preabil:dict = None):

        d_it = Functions.get_dict_item(item_id, preabil)

        if type == 'add':
            for i in range(col):
                users.update_one( {"userid": user['userid']}, {"$push": {'inventory': d_it }} )

            return True

        if type == 'data':
            ret_d = []
            for i in range(col):
                ret_d.append(d_it)

            return ret_d

    @staticmethod
    def item_authenticity(item:dict):
        item_data = items_f['items'][ item['item_id'] ]
        if list(item.keys()) == ['item_id']:
            return True

        else:
            if 'abilities' in item.keys():
                if item['abilities'] == item_data['abilities']:
                    return True
                else:
                    return False
            else:
                return True


    @staticmethod
    def qr_item_code(item:dict, v_id:bool = True):
        if v_id == True:
            text = f"i{item['item_id']}"
        else:
            text = ''

        if 'abilities' in item.keys():

            if 'uses' in item['abilities'].keys():
                # u - ключ код для des_qr

                if v_id == True:
                    text += f".u{item['abilities']['uses']}"
                else:
                    text += f"{item['abilities']['uses']}"

            if 'endurance' in item['abilities'].keys():
                # e - ключ код для des_qr

                if v_id == True:
                    text += f".e{item['abilities']['endurance']}"
                else:
                    text += f"{item['abilities']['endurance']}"

            if 'mana' in item['abilities'].keys():
                # m - ключ код для des_qr

                if v_id == True:
                    text += f".m{item['abilities']['mana']}"
                else:
                    text += f"{item['abilities']['mana']}"

            if 'stack' in item['abilities'].keys():
                # s - ключ код для des_qr

                if v_id == True:
                    text += f".s{item['abilities']['stack']}"
                else:
                    text += f"{item['abilities']['stack']}"

        return text

    @staticmethod
    def des_qr(it_qr:str, i_type:bool = False):
        l_data = {}
        ind = 0

        for i in it_qr:
            if i != '.':
                if ind in l_data.keys():
                    l_data[ind] += i
                else:
                    l_data[ind] = i
            else:
                ind += 1

        ret_data = {}
        for i in l_data.keys():
            tx = list(l_data[i])

            if tx[0] == 'i':
                if i_type == False:
                    ret_data['id'] = int(''.join(l_data[i])[1:])
                else:
                    ret_data['item_id'] = str(''.join(l_data[i])[1:])

            if tx[0] in ['u', 'e', 's', 'm']:

                if i_type == True:
                    if 'abilities' not in ret_data.keys():
                        ret_data['abilities'] = {}

                if tx[0] == 'u':
                    if i_type == False:
                        ret_data['uses'] = int(''.join(l_data[i])[1:])
                    else:
                        ret_data['abilities']['uses'] = int(''.join(l_data[i])[1:])

                elif tx[0] == 'e':
                    if i_type == False:
                        ret_data['endurance'] = int(''.join(l_data[i])[1:])
                    else:
                        ret_data['abilities']['endurance'] = int(''.join(l_data[i])[1:])

                elif tx[0] == 's':
                    if i_type == False:
                        ret_data['stack'] = int(''.join(l_data[i])[1:])
                    else:
                        ret_data['abilities']['stack'] = int(''.join(l_data[i])[1:])

                elif tx[0] == 'm':
                    if i_type == False:
                        ret_data['mana'] = int(''.join(l_data[i])[1:])
                    else:
                        ret_data['abilities']['mana'] = int(''.join(l_data[i])[1:])

        return ret_data

    @staticmethod
    def user_inventory(bot, user, message, inv_t = 'info'):

        bd_user = users.find_one({"userid": user.id})
        if bd_user != None:

            if bd_user['inventory'] == []:

                if bd_user['language_code'] == 'ru':
                    text = '💥 | Инвентарь пуст.'
                else:
                    text = '💥 | Inventory is empty.'

                bot.send_message(message.chat.id, text)
                return

            pages, page, items_data, items_names, row_width = Functions.inventory_pages(bd_user)

            if bd_user['language_code'] == 'ru':
                textt = '🎈 | Инвентарь открыт'
            else:
                textt = '🎈 | Inventory is open'

            bot.send_message(message.chat.id, textt)

            def work_pr(message, mms = None, page = None):

                rmk = types.ReplyKeyboardMarkup(resize_keyboard = True, row_width = row_width)
                for i in pages[page-1]:
                    rmk.add( *[ it for it in i ] )

                if bd_user['language_code'] == 'ru':

                    textt = f'🎈 | Страница: {page} | {len(pages)}\n🎟 | Обновление...'

                    if len(pages) > 1:
                        com_buttons = ['◀', '↪ Назад', '▶']

                    else:
                        com_buttons = ['◀', '↪ Назад', '▶']

                else:

                    textt = f'🎈 | Page: {page} | {len(pages)}\n🎟 | Update...'

                    if len(pages) > 1:
                        com_buttons = ['↪ Back']

                    else:
                        com_buttons = ['↪ Back']

                rmk.row(* [cm for cm in com_buttons] )

                def ret(message, page):

                    if message.text in ['Yes, transfer the item', 'Да, передать предмет', 'Да, я хочу это сделать', 'Yes, I want to do it']:
                        return

                    if message.text in ['↪ Назад', '↪ Back']:
                        res = None

                    else:
                        if message.text in items_names or message.text in ['◀', '▶']:
                            res = message.text
                        else:
                            res = None

                    if res == None:
                        if bd_user['language_code'] == 'ru':
                            text = "👥 | Возвращение в меню профиля!"
                        else:
                            text = "👥 | Return to the profile menu!"

                        bot.send_message(message.chat.id, text, reply_markup = Functions.markup(bot, 'profile', user))
                        return '12'

                    else:
                        if res == '◀':
                            if page - 1 == 0:
                                page = 1
                            else:
                                page -= 1

                            work_pr(message, page = page)

                        elif res == '▶':
                            if page + 1 > len(pages):
                                page = len(pages)
                            else:
                                page += 1

                            work_pr(message, page = page)

                        else:
                            item = items_data[ res ]

                            if inv_t == 'info':

                                text,  markup_inline, image = Functions.item_info(item, bd_user['language_code'])

                                if image == None:
                                    mms = bot.send_message(message.chat.id, text, reply_markup = markup_inline, parse_mode = 'Markdown')

                                else:
                                    mms = bot.send_photo(message.chat.id, image, text, reply_markup = markup_inline, parse_mode = 'Markdown')

                                work_pr(message, mms, page = page)

                            if inv_t == 'add_product':

                                def sch_items(item, bd_user):
                                    return bd_user['inventory'].count(item)

                                if bd_user['language_code'] == 'ru':
                                    text = "🛒 | Введите количество товара: "
                                    ans = ['🛒 Рынок']
                                else:
                                    text = "🛒 | Enter the quantity of the product: "
                                    ans = ['🛒 Market']

                                rmk = types.ReplyKeyboardMarkup(resize_keyboard = True, row_width = 1)
                                rmk.add(ans[0])

                                def ret_number(message):
                                    col = message.text
                                    try:
                                        col = int(col)
                                        mn = sch_items(item, bd_user)
                                        if col <= 0 or col >= mn + 1:
                                            if bd_user['language_code'] == 'ru':
                                                text = f'0️⃣1️⃣0️⃣ | Введите число от 1 до {mn}!'
                                            else:
                                                text = f'0️⃣1️⃣0️⃣ | Enter a number from 1 to {mn}!'

                                            bot.send_message(message.chat.id, text)
                                            col = None
                                    except:
                                        col = None

                                    if col == None:
                                        if bd_user['language_code'] == 'ru':
                                            text = "🛒 | Возвращение в меню рынка!"
                                        else:
                                            text = "🛒 | Return to the market menu!"

                                        bot.send_message(message.chat.id, text, reply_markup = Functions.markup(bot, 'market', user))

                                    else:

                                        def max_k(dct):
                                            mx_dct = -1
                                            for i in dct.keys():
                                                if int(i) > mx_dct:
                                                    mx_dct = int(i)
                                            return str(mx_dct+1)

                                        data_item = items_f['items'][item['item_id']]

                                        if 'rank' in data_item.keys():

                                            if data_item['rank'] == 'common': max_price = 2000

                                            if data_item['rank'] == 'uncommon': max_price = 4000

                                            if data_item['rank'] == 'rare': max_price = 8000

                                            if data_item['rank'] == 'mystical': max_price = 15000

                                            if data_item['rank'] == 'legendary': max_price = 50000

                                            if data_item['rank'] == 'mythical': max_price = 1000000

                                        else:
                                            max_price = 2000

                                        if bd_user['language_code'] == 'ru':
                                            text = f"🛒 | Введите стоимость предмета х1: (макс {max_price})"
                                        else:
                                            text = f"🛒 | Enter the cost of the item x1: (max {max_price})"

                                        def ret_number2(message):
                                            number = message.text
                                            try:
                                                number = int(number)
                                                if number <= 0 or number >= max_price + 1:
                                                    if bd_user['language_code'] == 'ru':
                                                        text = f'0️⃣1️⃣0️⃣ | Введите число от 1 до {max_price}!'
                                                    else:
                                                        text = f'0️⃣1️⃣0️⃣ | Enter a number from 1 to {max_price}!'

                                                    bot.send_message(message.chat.id, text)
                                                    number = None
                                            except:
                                                number = None

                                            if number == None:
                                                if bd_user['language_code'] == 'ru':
                                                    text = "🛒 | Возвращение в меню рынка!"
                                                else:
                                                    text = "🛒 | Return to the market menu!"

                                                bot.send_message(message.chat.id, text, reply_markup = Functions.markup(bot, 'market', user))

                                            else:

                                                market_ = management.find_one({"_id": 'products'})

                                                try:
                                                    products = market_['products'][str(user.id)]['products']
                                                except:
                                                    market_['products'][str(user.id)] = { 'products': {}, 'dinos': {} }
                                                    products = market_['products'][str(user.id)]['products']

                                                market_['products'][str(user.id)]['products'][ max_k(products) ] = { 'item': item, 'price': number, 'col': [0, col]}

                                                for _ in range(col):
                                                    bd_user['inventory'].remove(item)

                                                users.update_one( {"userid": bd_user['userid']}, {"$set": {'inventory': bd_user['inventory'] }} )

                                                management.update_one( {"_id": 'products'}, {"$set": {'products': market_['products'] }} )

                                                if bd_user['language_code'] == 'ru':
                                                    text = "🛒 | Продукт добавлен на рынок, статус своих продуктов вы можете посмотреть в своих продуктах!"
                                                else:
                                                    text = "🛒 | The product has been added to the market, you can see the status of your products in your products!"

                                                bot.send_message(message.chat.id, text, reply_markup = Functions.markup(bot, 'market', user))


                                        msg = bot.send_message(message.chat.id, text)
                                        bot.register_next_step_handler(msg, ret_number2)

                                msg = bot.send_message(message.chat.id, text, reply_markup = rmk)
                                bot.register_next_step_handler(msg, ret_number)

                if mms == None:
                    msg = bot.send_message(message.chat.id, textt, reply_markup = rmk)
                else:
                    msg = mms

                bot.register_next_step_handler(msg, ret, page)

            work_pr(message, page = page)

    @staticmethod
    def user_requests(bot, user, message):

        bd_user = users.find_one({"userid": user.id})
        if bd_user != None:
            if 'requests' in bd_user['friends']:
                id_friends = bd_user['friends']['requests']

                if bd_user['language_code'] == 'ru':
                    text = "💌 | Меню запросов открыто!"
                else:
                    text = "💌 | The query menu is open!"

                msg = bot.send_message(message.chat.id, text)

                def work_pr(message, id_friends):
                    global pages, pagen
                    a = []

                    id_names = {}
                    friends = []
                    for i in id_friends:
                        try:
                            userr = bot.get_chat(int(i))
                            id_names[userr.first_name] = int(i)
                            friends.append(userr.first_name)
                        except:
                            pass

                    fr_pages = list(Functions.chunks(friends, 3))
                    page = 1

                    pages_buttons = []
                    for i in range(len(fr_pages)):
                        pages_buttons.append([])

                    page_n = 0
                    for el in fr_pages:
                        for i in el:
                            pages_buttons[page_n].append([f"✅ {i}", f'❌ {i}'])
                        page_n += 1

                    if bd_user['language_code'] == 'ru':

                        com_buttons = ['◀', '↪ Назад', '▶']
                    else:

                        com_buttons = ['◀', '↪ Back', '▶']

                    rmk = types.ReplyKeyboardMarkup(resize_keyboard = True)

                    if pages_buttons != []:
                        for i in pages_buttons[page-1]:
                            rmk.add( i[0], i[1] )

                        for nn in range(3 - int(len(pages_buttons[page-1]))):
                            rmk.add( ' ', ' ')

                    else:
                        for i in range(3):
                            rmk.add( ' ', ' ')

                    if len(pages_buttons) > 1:
                        rmk.add( com_buttons[0], com_buttons[1], com_buttons[2] )
                    else:
                        rmk.add( com_buttons[1] )

                    pages = []
                    if pages_buttons != []:
                        for ii in pages_buttons[page-1]:
                            for iii in ii:
                                pages.append(iii)

                    pagen = page

                    if bd_user['language_code'] == 'ru':
                        text = "💌 | Обновление..."
                    else:
                        text = "💌 | Update..."

                    def ret(message, id_friends, bd_user, user, page):
                        if message.text in ['↪ Назад', '↪ Back']:
                            res = None

                        else:
                            if message.text in pages or message.text in ['◀', '▶']:
                                res = message.text

                            else:
                                res = None

                        if res == None:
                            if bd_user['language_code'] == 'ru':
                                text = "👥 | Возвращение в меню друзей!"
                            else:
                                text = "👥 | Return to the friends menu!"

                            bot.send_message(message.chat.id, text, reply_markup = Functions.markup(bot, 'friends-menu', user))
                            return None
                        else:
                            if res == '◀':
                                if page - 1 == 0:
                                    page = 1
                                else:
                                    page -= 1

                            if res == '▶':
                                if page + 1 > len(pages_buttons):
                                    page = len(pages_buttons)
                                else:
                                    page += 1

                            else:
                                uid = id_names[res[2:]]

                                if list(res)[0] == '❌':
                                    Functions.notifications_manager(bot, "friend_rejection", users.find_one({"userid": int(uid) }), user.first_name)

                                    if bd_user['language_code'] == 'ru':
                                        text = "👥 | Запрос в друзья отклонён!"
                                    else:
                                        text = "👥 | Friend request rejected!"

                                    bot.send_message(message.chat.id, text)

                                    try:
                                        bd_user['friends']['requests'].remove(uid)
                                        users.update_one( {"userid": bd_user['userid']}, {"$pull": {'friends.requests': uid }} )
                                    except:
                                        pass


                                if list(res)[0] == '✅':
                                    Functions.notifications_manager(bot, "friend_accept", users.find_one({"userid": int(uid) }), user.first_name)

                                    if bd_user['language_code'] == 'ru':
                                        text = "👥 | Запрос в друзья одобрен!"
                                    else:
                                        text = "👥 | The friend request is approved!"

                                    bot.send_message(message.chat.id, text)

                                    try:
                                        bd_user['friends']['requests'].remove(uid)
                                        bd_user['friends']['friends_list'].append(uid)
                                        users.update_one( {"userid": bd_user['userid']}, {"$set": {'friends': bd_user['friends'] }} )

                                        two_user = users.find_one({"userid": int(uid) })
                                        two_user['friends']['friends_list'].append(bd_user['userid'])
                                        users.update_one( {"userid": int(uid) }, {"$set": {'friends': two_user['friends'] }} )
                                    except:
                                        pass

                            work_pr(message, id_friends)

                    msg = bot.send_message(message.chat.id, text, reply_markup = rmk)
                    bot.register_next_step_handler(msg, ret, id_friends, bd_user, user, page)

                work_pr(message, id_friends)

    @staticmethod
    def acc_check(bot, user, item_id:str, dino_id, endurance = False):

        data_item = items_f['items'][item_id]
        acc_type = data_item['type'][:-3]

        try:
            acc_item = user['activ_items'][ dino_id ]
        except:
            user['activ_items'][ dino_id ] = {'game': None, 'hunt': None, 'journey': None, 'unv': None}
            users.update_one( {"userid": user["userid"] }, {"$set": {'activ_items': user['activ_items'] }} )

        acc_item = user['activ_items'][ dino_id ][acc_type]

        if acc_item != None:
            if user['activ_items'][ dino_id ][acc_type]['item_id'] == item_id:

                if endurance == True:
                    if 'abilities' in acc_item.keys():
                        if 'endurance' in acc_item['abilities'].keys():
                            r_ = random.randint(0, 2)
                            acc_item['abilities']['endurance'] -= r_

                            if acc_item['abilities']['endurance'] <= 0:
                                user['activ_items'][ dino_id ][acc_type] = None
                                Functions.notifications_manager(bot, "acc_broke", user, arg = item_id)

                            users.update_one( {"userid": user["userid"] }, {"$set": {'activ_items': user['activ_items'] }} )

                return True
            else:
                return False
        else:
            return False

    @staticmethod
    def last_markup(bd_user, alternative = 1):

        if 'last_markup' not in bd_user['settings'].keys():
            return alternative

        else:
            return bd_user['settings']['last_markup']

    @staticmethod
    def p_profile(bot, message, bd_dino, user, bd_user, dino_user_id):

        def egg_profile(bd_user, user, bd_dino):
            egg_id = bd_dino['egg_id']

            if bd_user['language_code'] == 'ru':
                lang = bd_user['language_code']
            else:
                lang = 'en'

            if 'quality' in bd_dino.keys():
                quality = bd_dino['quality']
            else:
                quality = 'random'

            if quality == 'random':
                if lang == 'ru':
                    dino_quality = ['Редкость:', 'Случайный']
                else:
                    dino_quality = ['Quality:', 'Random']
                fill = (207, 70, 204)

            if quality == 'com':
                if lang == 'ru':
                    dino_quality = ['Редкость:', 'Обычный']
                else:
                    dino_quality = ['Quality:', 'Common']
                fill = (108, 139, 150)

            if quality == 'unc':
                if lang == 'ru':
                    dino_quality = ['Редкость:', 'Необычный']
                else:
                    dino_quality = ['Quality:', 'Uncommon']
                fill = (68, 235, 90)

            if quality == 'rar':
                if lang == 'ru':
                    dino_quality = ['Редкость:', 'Редкий']
                else:
                    dino_quality = ['Quality:', 'Rare']
                fill = (68, 143, 235)

            if quality == 'myt':
                if lang == 'ru':
                    dino_quality = ['Редкость:', 'Мистическое']
                else:
                    dino_quality = ['Quality:', 'Mystical']
                fill = (230, 103, 175)

            if quality == 'leg':
                if lang == 'ru':
                    dino_quality = ['Редкость:', 'Легендарное']
                else:
                    dino_quality = ['Quality:', 'Legendary']
                fill = (235, 168, 68)


            t_incub = bd_dino['incubation_time'] - time.time()
            if t_incub < 0:
                t_incub = 0

            time_end = Functions.time_end(t_incub, True)
            if len(time_end) >= 18:
                time_end = time_end[:-6]

            bg_p = Image.open(f"images/remain/egg_profile_{lang}.png")
            egg = Image.open("images/" + str(json_f['elements'][egg_id]['image']))
            egg = egg.resize((290, 290), Image.ANTIALIAS)

            img = Functions.trans_paste(egg, bg_p, 1.0, (-50, 40))

            idraw = ImageDraw.Draw(img)
            line1 = ImageFont.truetype("fonts/Comic Sans MS.ttf", size = 35)

            idraw.text((430, 220), time_end, font = line1, stroke_width = 1)
            idraw.text((210, 270), dino_quality[0], font = line1)
            idraw.text((385, 270), dino_quality[1], font = line1, fill = fill)

            img.save(f'{config.TEMP_DIRECTION}/profile {user.id}.png')
            profile = open(f'{config.TEMP_DIRECTION}/profile {user.id}.png', 'rb')

            return profile, time_end

        def dino_profile(bd_user, user, dino_user_id):

            dino_id = str(bd_user['dinos'][ dino_user_id ]['dino_id'])

            if bd_user['language_code'] == 'ru':
                lang = bd_user['language_code']
            else:
                lang = 'en'

            dino = json_f['elements'][dino_id]
            if 'class' in list(dino.keys()):
                bg_p = Image.open(f"images/remain/{dino['class']}_icon.png")
            else:
                bg_p = Image.open(f"images/remain/None_icon.png")

            bd_user = Functions.dino_q(bd_user)
            class_ = bd_user['dinos'][ dino_user_id ]['quality']

            panel_i = Image.open(f"images/remain/{class_}_profile_{lang}.png")

            img = Functions.trans_paste(panel_i, bg_p, 1.0)

            dino_image = Image.open("images/"+str(json_f['elements'][dino_id]['image']))

            sz = 412
            dino_image = dino_image.resize((sz, sz), Image.ANTIALIAS)

            xy = -80
            x2 = 80
            img = Functions.trans_paste(dino_image, img, 1.0, (xy + x2, xy, sz + xy + x2, sz + xy ))

            idraw = ImageDraw.Draw(img)
            line1 = ImageFont.truetype("fonts/Comic Sans MS.ttf", size = 35)

            idraw.text((530, 110), str(bd_user['dinos'][dino_user_id]['stats']['heal']), font = line1)
            idraw.text((530, 190), str(bd_user['dinos'][dino_user_id]['stats']['eat']), font = line1)

            idraw.text((750, 110), str(bd_user['dinos'][dino_user_id]['stats']['game']), font = line1)
            idraw.text((750, 190), str(bd_user['dinos'][dino_user_id]['stats']['mood']), font = line1)
            idraw.text((750, 270), str(bd_user['dinos'][dino_user_id]['stats']['unv']), font = line1)

            img.save(f'{config.TEMP_DIRECTION}/profile {user.id}.png')
            profile = open(f'{config.TEMP_DIRECTION}/profile {user.id}.png', 'rb')

            return profile

        if bd_dino['status'] == 'incubation':

            profile, time_end  = egg_profile(bd_user, user, bd_dino)
            if bd_user['language_code'] == 'ru':
                text = f'🥚 | Яйцо инкубируется, осталось: {time_end}'
            else:
                text = f'🥚 | The egg is incubated, left: {time_end}'

            bot.send_photo(message.chat.id, profile, text, reply_markup = Functions.markup(bot, user = user))

        if bd_dino['status'] == 'dino':

            for i in bd_user['dinos'].keys():
                if bd_user['dinos'][i] == bd_dino:
                    dino_user_id = i

            profile = dino_profile(bd_user, user, dino_user_id = dino_user_id )

            st_t = bd_dino['activ_status']

            dino = json_f['elements'][str(bd_dino['dino_id'])]
            pre_qual = bd_user['dinos'][ dino_user_id ]['quality']
            qual = ''

            if bd_user['language_code'] == 'ru':
                if pre_qual == 'com':
                    qual = 'Обычный'
                if pre_qual == 'unc':
                    qual = 'Необычный'
                if pre_qual == 'rar':
                    qual = 'Редкий'
                if pre_qual == 'myt':
                    qual = 'Мистический'
                if pre_qual == 'leg':
                    qual = 'Легендарный'
            else:
                if pre_qual == 'com':
                    qual = 'Сommon'
                if pre_qual == 'unc':
                    qual = 'Unusual'
                if pre_qual == 'rar':
                    qual = 'Rare'
                if pre_qual == 'myt':
                    qual = 'Mystical'
                if pre_qual == 'leg':
                    qual = 'Legendary'

            if bd_dino['activ_status'] == 'pass_active':
                if bd_user['language_code'] == 'ru':
                    st_t = 'ничего не делает 💭'
                else:
                    st_t = 'does nothing 💭'

            elif bd_dino['activ_status'] == 'sleep':
                if bd_user['language_code'] == 'ru':
                    st_t = 'спит 🌙'
                else:
                    st_t = 'sleeping 🌙'

            elif bd_dino['activ_status'] == 'game':
                if bd_user['language_code'] == 'ru':
                    st_t = 'играет 🎮'
                else:
                    st_t = 'playing 🎮'

            elif bd_dino['activ_status'] == 'journey':
                if bd_user['language_code'] == 'ru':
                    st_t = 'путешествует 🎴'
                else:
                    st_t = 'travels 🎴'

            elif bd_dino['activ_status'] in ['hunt', 'hunting']:
                if bd_user['language_code'] == 'ru':
                    st_t = 'сбор пищи 🥞'
                else:
                    st_t = 'collecting food 🥞'

            elif bd_dino['activ_status'] == 'dungeon':
                if bd_user['language_code'] == 'ru':
                    st_t = 'в подземелье 🗻'
                else:
                    st_t = 'in dungeon 🗻'

            elif bd_dino['activ_status'] == 'freezing':
                if bd_user['language_code'] == 'ru':
                    st_t = 'заморожен ❄'
                else:
                    st_t = 'freezing ❄'

            if bd_dino['stats']['heal'] >= 60:
                if bd_user['language_code'] == 'ru':
                    h_text = '❤ *┌* Динозавр здоров'
                else:
                    h_text = '❤ *┌* The dinosaur is healthy'

            elif bd_dino['stats']['heal'] < 60 and bd_dino['stats']['heal'] > 10:
                if bd_user['language_code'] == 'ru':
                    h_text = '❤ *┌* Динозавр в плохом состоянии'
                else:
                    h_text = '❤ *┌* Dinosaur in bad condition'

            elif bd_dino['stats']['heal'] <= 10:
                if bd_user['language_code'] == 'ru':
                    h_text = '❤ *┌* Динозавр в крайне плохом состоянии!'
                else:
                    h_text = '❤ *┌* The dinosaur is in extremely bad condition!'


            if bd_dino['stats']['eat'] >= 60:
                if bd_user['language_code'] == 'ru':
                    e_text = '🍕 *├* Динозавр сыт'
                else:
                    e_text = '🍕 *├* The dinosaur is full'

            elif bd_dino['stats']['eat'] < 60 and bd_dino['stats']['eat'] > 10:
                if bd_user['language_code'] == 'ru':
                    e_text = '🍕 *├* Динозавр голоден'
                else:
                    e_text = '🍕 *├* The dinosaur is hungry'

            elif bd_dino['stats']['eat'] <= 10:
                if bd_user['language_code'] == 'ru':
                    e_text = '🍕 *├* Динозавр умирает от голода!'
                else:
                    e_text = '🍕 *├* The dinosaur is starving!'


            if bd_dino['stats']['game'] >= 60:
                if bd_user['language_code'] == 'ru':
                    g_text = '🎮 *├* Динозавр не хочет играть'
                else:
                    g_text = "🎮 *├* The dinosaur doesn't want to play"

            elif bd_dino['stats']['game'] < 60 and bd_dino['stats']['game'] > 10:
                if bd_user['language_code'] == 'ru':
                    g_text = '🎮 *├* Динозавр скучает...'
                else:
                    g_text = '🎮 *├* The dinosaur is bored...'

            elif bd_dino['stats']['game'] <= 10:
                if bd_user['language_code'] == 'ru':
                    g_text = '🎮 *├* Динозавр умирает от скуки!'
                else:
                    g_text = '🎮 *├* The dinosaur is dying of boredom!'


            if bd_dino['stats']['mood'] >= 60:
                if bd_user['language_code'] == 'ru':
                    m_text = '🎈 *├* Динозавр в хорошем настроении'
                else:
                    m_text = '🎈 *├* The dinosaur is in a good mood'

            elif bd_dino['stats']['mood'] < 60 and bd_dino['stats']['mood'] > 10:
                if bd_user['language_code'] == 'ru':
                    m_text = '🎈 *├* У динозавра нормальное настроение'
                else:
                    m_text = '🎈 *├* The dinosaur has a normal mood'

            elif bd_dino['stats']['mood'] <= 10:
                if bd_user['language_code'] == 'ru':
                    m_text = '🎈 *├* Динозавр грустит!'
                else:
                    m_text = '🎈 *├* The dinosaur is sad!'


            if bd_dino['stats']['unv'] >= 60:
                if bd_user['language_code'] == 'ru':
                    u_text = '🌙 *└* Динозавр полон сил'
                else:
                    u_text = '🌙 *└* The dinosaur is full of energy'

            elif bd_dino['stats']['unv'] < 60 and bd_dino['stats']['unv'] > 10:
                if bd_user['language_code'] == 'ru':
                    u_text = '🌙 *└* У динозавра есть силы'
                else:
                    u_text = '🌙 *└* The dinosaur has powers'

            elif bd_dino['stats']['unv'] <= 10:
                if bd_user['language_code'] == 'ru':
                    u_text = '🌙 *└* Динозавр устал!'
                else:
                    u_text = '🌙 *└* The dinosaur is tired!'


            if bd_user['language_code'] == 'ru':
                text = f'🦖 *┌* Имя: {bd_dino["name"].replace("*", "")}\n👁‍🗨 *├* Статус: {st_t}\n🧿 *└* Редкость: {qual}\n\n{h_text}\n{e_text}\n{g_text}\n{m_text}\n{u_text}'
            else:
                text = f'🦖 *┌* Name: {bd_dino["name"].replace("*", "")}\n👁‍🗨 *├* Status: {st_t}\n🧿 *└* Rare: {qual}\n\n{h_text}\n{e_text}\n{g_text}\n{m_text}\n{u_text}'

            if bd_dino['activ_status'] == 'journey':
                w_t = bd_dino['journey_time'] - time.time()
                if w_t < 0:
                    w_t = 0
                if bd_user['language_code'] == 'ru':
                    text += f"\n\n🌳 *┌* Путешествие: \n·  Осталось: { Functions.time_end(w_t) }"
                else:
                    text += f"\n\n🌳 *┌* Journey: \n·  Left: { Functions.time_end(w_t, True) }"

            if bd_dino['activ_status'] == 'game':
                if Functions.acc_check(bot, bd_user, '4', dino_user_id, True):
                    w_t = bd_dino['game_time'] - time.time()
                    if w_t < 0:
                        w_t = 0
                    if bd_user['language_code'] == 'ru':
                        text += f"\n\n🎮 *┌* Игра: \n·  Осталось: { Functions.time_end(w_t) }"
                    else:
                        text += f"\n\n🎮 *┌* Game: \n·  Left: { Functions.time_end(w_t, True) }"

            d_id = dino_user_id
            act_ii = []
            for itmk in bd_user['activ_items'][d_id].keys():
                itm = bd_user['activ_items'][d_id][itmk]
                if itm == None:
                    act_ii.append('-')
                else:
                    if bd_user['language_code'] == 'ru':
                        item = items_f['items'][str(itm['item_id'])]['nameru']
                    else:
                        item = items_f['items'][str(itm['item_id'])]['nameen']

                    if 'abilities' in itm.keys() and 'endurance' in itm['abilities'].keys():
                        act_ii.append(f"{item} ({itm['abilities']['endurance']})")
                    else:
                        act_ii.append(f'{item}')

            if bd_user['language_code'] == 'ru':
                text += f"\n\n🌙 *┌* Сон: {act_ii[3]}\n"
                text += f"🎮 *├* Игра: {act_ii[0]}\n"
                text += f"🌿 *├* Сбор пищи: {act_ii[1]}\n"
                text += f"🎍 *└* Путешествие: {act_ii[2]}\n"

            else:
                text += f"\n\n🌙 *┌* Sleep: {act_ii[3]}\n"
                text += f"🎮 *├* Game: {act_ii[0]}\n"
                text += f"🌿 *├* Collecting food: {act_ii[1]}\n"
                text += f"🎍 *└* Journey: {act_ii[2]}\n"

            bot.send_photo(message.chat.id, profile, text, reply_markup = Functions.markup(bot, user = user), parse_mode = 'Markdown' )

    @staticmethod
    def journey_end_log(bot, user_id, dino_id):
        bd_user = users.find_one({"userid": user_id })

        text = f'🦖 | {bd_user["dinos"][ dino_id ]["name"]} вернулся из путешествия!\nВот что произошло в его путешествии:\n\n'

        if bd_user['dinos'][ dino_id ]['journey_log'] == []:
            text += 'Ничего не произошло!'
            bot.send_message(user_id, text, parse_mode = 'Markdown')

        else:
            messages = []

            n = 1
            for el in bd_user['dinos'][ dino_id ]['journey_log']:
                if len(text) >= 3700:
                    messages.append(text)
                    text = ''

                text += f'*{n}.* {el}\n\n'
                n += 1

            messages.append(text)

            for m in messages:
                bot.send_message(user_id, m, parse_mode = 'Markdown')

    @staticmethod
    def items_counting(user, item_type):
        data_items = items_f['items']
        count = 0
        for i in user['inventory']:
            data_item = data_items[ i['item_id'] ]
            if data_item['type'] == item_type:
                count += 1

        return count

    @staticmethod
    def spam_stop(user_id, sec = 0.5):
        global users_timeout

        if str(user_id) in users_timeout.keys():
            if users_timeout[str(user_id)] + sec < time.time():
                users_timeout[str(user_id)] = time.time()
                return True

            else:
                users_timeout[str(user_id)] = time.time()
                return False

        else:
            users_timeout[str(user_id)] = time.time()
            return True

    @staticmethod
    def callback_spam_stop(user_id, sec = 0.5):
        global callback_timeout

        if str(user_id) in callback_timeout.keys():
            if callback_timeout[str(user_id)] + sec < time.time():
                callback_timeout[str(user_id)] = time.time()
                return True

            else:
                callback_timeout[str(user_id)] = time.time()
                return False

        else:
            callback_timeout[str(user_id)] = time.time()
            return True

    @staticmethod
    def dino_q(bd_user):

        for i in bd_user['dinos']:
            if 'quality' not in bd_user['dinos'][i].keys():
                dino = bd_user['dinos'][i]

                if dino['status'] == 'dino':
                    dino_data = json_f['elements'][str(dino['dino_id'])]
                    bd_user['dinos'][i]['quality'] = dino_data['image'][5:8]

                    users.update_one( {"userid": bd_user['userid']}, {"$set": {f'dinos.{i}.quality': dino_data['image'][5:8] }} )

        return bd_user

    # @staticmethod
    # def message_from_delete(bot, userid, text):
    #     markup_inline = types.InlineKeyboardMarkup()

    #     if dung['settings']['lang'] == 'ru':
    #         inl_l = {"⚙ Удалить сообщение": 'message_delete', }
    #     else:
    #         inl_l = {"⚙ Delete a message": 'message_delete'}

    #     markup_inline.add( *[ types.InlineKeyboardButton( text = inl, callback_data = f"{inl_l[inl]}") for inl in inl_l.keys() ])

    #     bot.send_message(userid, text, reply_markup = Functions.markup(bot, "dungeon_menu", int(u_k) ))

    @staticmethod
    def rand_d(rd:dict):

        """
        Тип словаря:
        { "min": 1, "max": 2, "type": "random" }
                       /
        { "act": 1, "type": "static" }
        """

        if 'type' in rd.keys():

            if rd["type"] in ["static", "random"]:

                number = 0
                if rd["type"] == "static":
                    number = rd['act']

                elif rd["type"] == "random":

                    if rd['min'] >= rd['max']:
                        pass

                    else:
                        number = random.randint( rd['min'], rd['max'] )

                return number

            else:
                return rd

        else:
            return rd

    @staticmethod
    def inventory_pages(bd_user, i_filter_type = 'all', i_filter = None):

        data_items = items_f['items']
        items = bd_user['inventory']

        page = 1
        add_item = False
        items_data = {}
        items_names = []

        if 'inv_view' in bd_user['settings'].keys():
            pages_v = bd_user['settings']['inv_view']
        else:
            pages_v = [2, 3]

        if bd_user['language_code'] == 'ru':
            lg = "nameru"
        else:
            lg = "nameen"

        for i in items:
            ic = items.count(i)

            if ic == 1:
                i_col = ''
            else:
                i_col = f' x{ic}'

            if i_filter_type == 'all':
                add_item = True

            elif i_filter_type == 'itemid':

                if int(i['item_id']) == int(i_filter):
                    add_item = True

                else:
                    add_item = False

            if i_filter_type == 'itemtype':

                if data_items[str(i['item_id'])] == i_filter:
                    add_item = True

                else:
                    add_item = False

            if add_item == True:

                if Functions.item_authenticity(i) == True:
                    i_name = f"{items_f['items'][ i['item_id'] ][lg]}{i_col}"

                else:
                    i_name = f"{items_f['items'][ i['item_id'] ][lg]}{i_col} ({Functions.qr_item_code(i, False)})"

                items_data[ i_name] = i


        items_names = list(items_data.keys())
        items_names.sort()

        pages = list(Functions.chunks(list(Functions.chunks( items_names, pages_v[0] )), pages_v[1] ))

        for i in pages:

            if len(i) != pages_v[1]:
                for _ in range(pages_v[1] - len(i)):
                    i.append( [ ' ' for _ in range(pages_v[0]) ])

        row_width = pages_v[0]
        return pages, page, items_data, items_names, row_width

    @staticmethod
    def tr_c_f(bd_user):

        tr_c = False
        stats_list = []
        if bd_user != None and len(list(bd_user['dinos'])) > 0:
            for i in bd_user['dinos'].keys():
                dd = bd_user['dinos'][i]
                stats_list.append(dd['status'])

            if 'dino' in stats_list:
                tr_c = True

        return tr_c

    @staticmethod
    def lst_m_f(bd_user):

        if bd_user != None:
            last_mrk = Functions.last_markup(bd_user, alternative = 1)
        else:
            last_mrk = None

        return last_mrk

    def clean_tmp():

        for file in glob.glob(f"{config.TEMP_DIRECTION}/*"):
            os.remove(file)
            print(f"Система: {str(file)} удалён.")

    def load_languages():
        global languages

        for filename in os.listdir("localization"):
            with open(f'localization/{filename}', encoding='utf-8') as f: 
                languages_f = json.load(f)

            for l_key in languages_f.keys():
                languages[l_key] = languages_f[l_key]
        
        print(f"Система: Загружено {len(languages.keys())} файла(ов) локализации.")
        logging.info(f"Загружено {len(languages.keys())} файла(ов) локализации.")
    
    def create_logfile():

        logging.basicConfig(
            level = logging.INFO, 
            filename = f"{config.LOGS_DERECTION}/{time.strftime('%Y %m-%d %H.%M.%S')}.log",
            filemode = "w", encoding='utf-8',
            format = "%(asctime)s %(levelname)s %(message)s" 
            )
    
    def get_text(l_key:str, text_key:str, dp_text_key:str = None):
        global languages

        if l_key not in languages.keys():
            l_key = 'en'
        
        if text_key not in languages[ l_key ].keys():
            text_key = "no_text_key"
        
        if dp_text_key == None:
            return  languages[ l_key ][ text_key ]
        
        else:

            if type(languages[ l_key ][ text_key ]) == dict:

                if dp_text_key not in languages[ l_key ][ text_key ].keys():
                    return  languages[ l_key ][ "no_dp_text_key" ]
                
                else:
                    return  languages[ l_key ][ text_key ][ dp_text_key ]

            else:
                return  languages[ l_key ][ text_key ]

class Dungeon:

    def random_mobs(mobs_type:str, floor_lvl:int, count:int = 1):
        ret_list = []

        if mobs_type == 'mobs':
            mobs_data = mobs_f['mobs']

            mobs_keys = list(mobs_data.keys())
            random.shuffle(mobs_keys)

            for n in range(count):
                random.shuffle(mobs_keys)

                mob_key = mobs_keys[ 0 ]
                mob = mobs_data[mob_key]

                if mob['lvls']['min'] >= floor_lvl or floor_lvl <= mob['lvls']['max']:

                    mob_data = {'mob_key': mob_key, 'effects': []}

                    l_k = ['hp', 'damage', 'intelligence']

                    if mob['damage-type'] == 'magic':
                        l_k.append('mana')

                    elif mob['damage-type'] == 'near':
                        l_k.append('endurance')

                    elif mob['damage-type'] == 'far':
                        l_k.append('ammunition')

                    for i in l_k:

                        mob_data[i] = Functions.rand_d( mob[i] )

                        if i in ['hp', 'mana']:
                            mob_data[f"max{i}"] = mob_data[i]

                    mob_data[f"activ_effects"] = []
                    ret_list.append(mob_data)

            return ret_list

        elif mobs_type == 'boss':
            boss_data = mobs_f['boss']

            boss_keys = list(boss_data.keys())
            random.shuffle(boss_keys)

            boss_key = boss_keys[ 0 ]
            boss = boss_data[boss_key]

            if boss['lvls']['min'] >= floor_lvl or floor_lvl <= boss['lvls']['max']:

                boss_data = {'mob_key': boss_key}

                l_k = ['hp', 'damage', 'intelligence']

                if boss['damage-type'] == 'magic':
                    l_k.append('mana')

                elif boss['damage-type'] == 'near':
                    l_k.append('endurance')

                elif boss['damage-type'] == 'far':
                    l_k.append('ammunition')

                for i in l_k:

                    boss_data[i] = Functions.rand_d( boss[i] )

                    if i in ['hp', 'mana']:
                        boss_data[f"max{i}"] = boss_data[i]

                boss_data[f"activ_effects"] = []

            return boss_data

        else:
            print('random_mobs - mobs_type error')
            return []

    def base_upd(userid = None, messageid = None, dinosid = [], dungeonid = None, type = None, kwargs = {} ):

        def dino_data(dinosid):
            dinos = {}
            for i in dinosid:
                dinos[i] = {'activ_effects': []}

            return dinos

        def user_data(messageid, dinos):
            return {'messageid': messageid, 'last_page': 'main', 'dinos': dinos, 'coins': 200, 'inventory': []}

        if dungeonid == None:
            dung = dungeons.find_one({"dungeonid": int(userid)})
            bd_user = users.find_one({"userid": int(userid) })

            if dung == None:
                dinos = dino_data(dinosid)

                dungeons.insert_one(
                {
                    'dungeonid': userid,
                    'users': { str(userid): user_data(messageid, dinos) },
                    'floor': {},
                    'dungeon_stage': 'preparation', "create_time": int( time.time() ),
                    'stage_data':  { 'preparation': {'image': random.randint(1,5), 'ready': [] }
                                   },
                    'settings': { 'lang': bd_user['language_code'], 'max_dinos': 10, 'max_rooms': 10, 'start_floor': 0, 'battle_notifications': True} # начальный уровень -1;
                } )

                dung = dungeons.find_one({"dungeonid": userid})
                return dung, 'create_dungeon'

            else:
                return dung, 'error_(find_dungeon)'

        if dungeonid != None:
            dung = dungeons.find_one({"dungeonid": dungeonid})

            if dung != None:

                if type in ['create_floor', 'create_room']:

                    floor_n = dung['stage_data']['game']['floor_n'] + 1
                    floor_data = Dungeon.floor_data(floor_n)

                    if type == 'create_floor':

                        dung['stage_data']['game']['floor_n'] += 1
                        dung['stage_data']['game']['room_n'] = 0

                        dung['stage_data']['game']['floors_stat'][ str( dung['stage_data']['game']['floor_n'] ) ] = {
                            'start_time': int(time.time()),
                            'mobs_killing': 0,
                            'end_time': int(time.time())
                        }

                        dungeons.update_one( {"dungeonid": dungeonid}, {"$set": {f'stage_data': dung['stage_data'] }} )

                        floor = { '0': { 'room_type': 'start_room', 'image': f'images/dungeon/start_room/{random.randint(1,2)}.png', 'next_room': True, 'ready': [] }, 'floor_data': {}}

                        for rmn in range(1, dung['settings']['max_rooms'] + 1):
                            floor[ str(rmn) ] = {}

                        rooms_list = list(range(1, dung['settings']['max_rooms'] ))
                        room_type_cr = "random"

                        if floor_n % 5 == 0 and floor_n % 10 == 0:
                            # босс каждые 10 этажей

                            boss = Dungeon.random_mobs(mobs_type = 'boss', floor_lvl = dung['stage_data']['game']['floor_n'])

                            floor['10'] = {
                                'room_type': 'battle', 'battle_type': 'boss',
                                'reward': { 'experience': 0, 'items': [], 'collected': {}, 'coins': 0 },
                                'mobs': boss,
                                'image': f'images/dungeon/simple_rooms/{random.randint(1,5)}.png',
                                'next_room': False,
                                'ready': []
                                          }

                        else:
                            #остальное
                            rooms_list = list(range(1, dung['settings']['max_rooms'] + 1 ))

                        floor['11'] = { 'room_type': 'safe_exit', 'image': f'images/dungeon/start_room/1.png', 'next_room': True, 'ready': [] }

                    else:

                        floor = dung['floor']
                        rooms_list = kwargs['rooms_list']
                        room_type_cr = "static"

                    # rooms = { 'com': ['battle'],
                    #           'unc': ['battle', 'empty_room'], # 'forest'
                    #           'rar': ['fork_2', 'fork_3'],  #, 'quest'],
                    #           'myt': ['mine'],#, 'town'],
                    #           'leg': ['mine'] #['chest', 'mimic']
                    #         }

                    rooms = floor_data["rooms_type"]

                    for room_n in rooms_list:

                        if room_type_cr == "random":
                            room_type = Functions.random_items(rooms)

                        else:
                            room_type = kwargs['rooms'][ str(room_n) ]

                        if room_type == 'battle':
                            m_count = Functions.rand_d( floor_data['mobs_count'] )

                            mobs = Dungeon.random_mobs(mobs_type = 'mobs', floor_lvl = dung['stage_data']['game']['floor_n'], count = m_count)

                            floor[str(room_n)] = {
                                'room_type': room_type, 'battle_type': 'mobs',
                                'reward': { 'experience': 0, 'items': [], 'collected': {}, 'coins': 0 },
                                'mobs': mobs,
                                'image': f'images/dungeon/simple_rooms/{random.randint(1,5)}.png',
                                'next_room': False,
                                'ready': []
                                                 }

                            # collected - items : True, exp: True, coins: True
                            # при нажатии выдавать опыт, и давать выбрать предметы

                        elif room_type == 'empty_room':
                            secrets = []

                            if random.randint(1, 100) > 90:
                                secrets_n = ['item', 'way', 'battle']
                                secrets.append( random.choice(secrets_n) )

                            floor[str(room_n)] = { 'room_type': room_type, 'image': f'images/dungeon/simple_rooms/{random.randint(1,5)}.png', 'next_room': True, 'secrets': secrets }

                        elif room_type == 'mine':
                            resources = []

                            res_count = Functions.rand_d( floor_data["resources"]["items_col"] )

                            for _ in range(res_count):
                                for item_d in floor_data["resources"]['items']:
                                    if random.randint(1, 1000) <= item_d['chance']:
                                        resources.append( { 'item': Functions.get_dict_item( item_d['item'] ), 'min_efect': item_d['min_efect'] } )

                            floor[str(room_n)] = { 'room_type': room_type, 'image': f'images/dungeon/mine/{1}.png', 'next_room': True, 'resources': resources, 'users_res': {} }

                        elif room_type == 'town':
                            products = []
                            col = Functions.rand_d( floor_data["products_settings"]['col'] )

                            while len(products) < col:
                                for pr_k in floor_data['products'].keys():
                                    if len(products) < col:

                                        pr = floor_data['products'][pr_k]
                                        ccol = Functions.rand_d( pr['col'] )

                                        for _ in range( ccol ):
                                            if random.randint(1, 1000) <= pr['chance']:

                                                p_data = {}
                                                p_data['price'] = Functions.rand_d( pr['price'] )
                                                p_data['item'] = Functions.get_dict_item(pr['item'])

                                                products.append(p_data)


                            floor[str(room_n)] = { 'room_type': room_type, 'image': f'images/dungeon/town/{ random.randint(1,3) }.png', 'next_room': True, 'products': products }

                        elif room_type in ['fork_2', 'fork_3']:

                            if room_type == 'fork_2':
                                poll_rooms = [ Functions.random_items(rooms) for i in range(2) ]
                                results = [[], []]

                            if room_type == 'fork_3':
                                poll_rooms = [ Functions.random_items(rooms) for i in range(3) ]
                                results = [ [], [], [] ]

                            floor[str(room_n)] = { 'room_type': room_type, 'poll_rooms': poll_rooms, 'image': f'images/dungeon/{room_type}/1.png', 'results': results, 'next_room': False }

                        else:
                            floor[str(room_n)] = { 'room_type': room_type, 'image': f'images/dungeon/simple_rooms/{random.randint(1,5)}.png', 'next_room': True }

                        floor[str(room_n)]['ready'] = []

                    dung['floor'] = floor
                    dungeons.update_one( {"dungeonid": dungeonid}, {"$set": {f'floor': floor }} )

                    return dung, type

                if type == 'next_move':

                    last_move = dung['stage_data']['game']['player_move'][0]
                    mvs = dung['stage_data']['game']['player_move'][1]
                    last_move_ind = mvs.index(last_move)
                    move_id = mvs[0]

                    for uid in dung['stage_data']['game']['player_move'][1]:
                        if uid not in dung['users'].keys():
                            dung['stage_data']['game']['player_move'][1].remove(uid)

                    if last_move_ind + 1 >= len(mvs):
                        move_id = mvs[0]

                    else:
                        move_id = mvs[ last_move_ind + 1 ]

                    dung['stage_data']['game']['player_move'][0] = move_id
                    dungeons.update_one( {"dungeonid": dungeonid}, {"$set": {f'stage_data': dung['stage_data'] }} )

                    return dung, 'next_move'

                if type == 'add_user':

                    if str(userid) not in dung['users'].keys():
                        dinos = dino_data(dinosid)

                        dung['users'][str(userid)] = user_data(messageid, dinos)
                        dungeons.update_one( {"dungeonid": dungeonid}, {"$set": {f'users': dung['users'] }} )

                        return dung, 'add_user'

                    else:
                        return dung, 'error_user_in_dungeon'

                if type == 'remove_user':

                    if str(userid) in dung['users'].keys():

                        if dung['users'][str(userid)]['inventory'] != []:
                            bd_user = users.find_one({"userid": int(userid) })

                            for item in dung['users'][str(userid)]['inventory']:
                                bd_user['inventory'].append(item)

                            users.update_one( {"userid": int(userid)}, {"$set": {f'inventory': bd_user['inventory']}} )


                        del dung['users'][str(userid)]
                        dungeons.update_one( {"dungeonid": dungeonid}, {"$set": {f'users': dung['users'] }} )

                        return dung, 'remove_user'

                    else:
                        return dung, 'error_user_not_in_dungeon'

                if type == 'delete_dungeon':

                    if kwargs == {}:
                        save_inv = True
                    else:
                        save_inv = kwargs['save_inv']

                    for user_id in dung['users']:

                        bd_user = users.find_one({"userid": int(user_id) })

                        if save_inv == True:
                            if dung['users'][str(user_id)]['inventory'] != []:

                                for item in dung['users'][str(user_id)]['inventory']:
                                    bd_user['inventory'].append(item)

                                users.update_one( {"userid": int(user_id)}, {"$set": {f'inventory': bd_user['inventory']}} )

                            if dung['users'][str(user_id)]['coins'] != 0 and dung['dungeon_stage'] == 'game':
                                users.update_one( {"userid": int(user_id)}, {"$inc": {f'coins': dung['users'][str(user_id)]['coins'] }} )

                        for d_k in dung['users'][ str(user_id) ]['dinos'].keys():

                            bd_user['dinos'][d_k]['activ_status'] = 'pass_active'
                            users.update_one( {"userid": int(user_id)}, {"$set": {f'dinos.{d_k}': bd_user['dinos'][d_k] }} )

                    dungeons.delete_one({"dungeonid": dungeonid})
                    return None, 'delete_dungeon'

                if type == 'leave_user':
                    floor_n = dung['stage_data']['game']['floor_n']
                    room_n = dung['stage_data']['game']['room_n']
                    bd_user = users.find_one({"userid": int(userid) })

                    if room_n == 11:

                        if dung['users'][str(userid)]['inventory'] != []:

                            for item in dung['users'][str(userid)]['inventory']:
                                bd_user['inventory'].append(item)

                            users.update_one( {"userid": int(userid)}, {"$set": {f'inventory': bd_user['inventory']}} )

                        if dung['users'][str(userid)]['coins'] != 0:

                            users.update_one( {"userid": int(userid)}, {"$inc": {f'coins': dung['users'][str(userid)]['coins'] }} )

                    for d_k in dung['users'][ str(userid) ]['dinos'].keys():
                        bd_user['dinos'][d_k]['activ_status'] = 'pass_active'
                        del bd_user['dinos'][d_k]['dungeon_id']

                        users.update_one( {"userid": int(userid)}, {"$set": {f'dinos.{d_k}': bd_user['dinos'][d_k] }} )

                    del dung['users'][str(userid)]
                    dungeons.update_one( {"dungeonid": dungeonid}, {"$set": {f'users': dung['users'] }} )

                    if str(userid) == dung['stage_data']['game']['player_move'][0]:
                        dng, inf = Dungeon.base_upd(dungeonid = dungeonid, type = 'next_move')

                    return dung, 'leave_user'

                if type == 'edit_message':

                    dung['users'][str(userid)]['messageid'] = messageid
                    dungeons.update_one( {"dungeonid": dungeonid}, {"$set": {f'users': dung['users'] }} )

                    return dung, 'edit_message_data'

                if type == 'edit_last_page':

                    dung['users'][str(userid)]['last_page'] = messageid
                    dungeons.update_one( {"dungeonid": dungeonid}, {"$set": {f'users': dung['users'] }} )

                    return dung, 'edit_last_page'

                if type == 'remove_dino':

                    for d_k in dinosid:
                        if str(d_k) in dung['users'][str(userid)]['dinos'].keys():
                            del dung['users'][str(userid)]['dinos'][str(d_k)]

                        else:
                            pass
                            # print('dinoid - ', d_k, 'not in keys')

                    dungeons.update_one( {"dungeonid": dungeonid}, {"$set": {f'users': dung['users'] }} )

                    return dung, 'remove_dino'

                if type == 'add_dino':
                    ddnl = []
                    bd_user = users.find_one({"userid": int(userid) })

                    d_n = 0
                    for u in dung['users']:
                        d_n += len(dung['users'][u]['dinos'])

                    if d_n < dung['settings']['max_dinos']:

                        for d_k in dinosid:
                            if str(d_k) not in dung['users'][str(userid)]['dinos'].keys():
                                if bd_user['dinos'][str(d_k)]['status'] != 'incubation':
                                    if bd_user['dinos'][str(d_k)]['activ_status'] == 'pass_active':
                                        ddnl.append(d_k)

                                    else:
                                        return dung, 'action_dino_is_not_pass'

                                else:
                                    return dung, 'dino_incubation'

                            else:
                                pass
                                #print('dinoid - ', d_k, 'not in keys')

                        dinos = dino_data(ddnl)

                        for i in dinos:
                            d_data = dinos[str(i)]

                            dung['users'][str(userid)]['dinos'][i] = d_data

                        dungeons.update_one( {"dungeonid": dungeonid}, {"$set": {f'users': dung['users'] }} )

                        return dung, 'add_dino'

                    else:

                        return dung, 'limit_(add_dino)'

                else:
                    return dung, f'error_type_dont_find - {type}'

            else:
                return None, 'error_no_dungeon'

    def inline(bot, userid = None, dungeonid = None, type = None, kwargs = None):
        dung = dungeons.find_one({"dungeonid": dungeonid})
        markup_inline = types.InlineKeyboardMarkup(row_width = 3)
        inl_l2 = {}

        if dung != None:

            if type == 'mine':

                if dung['settings']['lang'] == 'ru':
                    inl_l = { '📜 Инвентарь': 'dungeon.inventory 1', '⛏ Копать': 'dungeon.mine', '🦕 Состояние': 'dungeon.dinos_stats'
                            }

                    if userid == dungeonid:
                        inl_l2 = {'⏩ След. комната': 'dungeon.next_room', '❌ Исключить': 'dungeon.kick_member'}

                    else:
                        inl_l2 = {'✅ Готовность': 'dungeon.next_room_ready', '🚪 Выйти': 'dungeon.leave_in_game_answer'}

                else:
                    inl_l = { '📜 Inventory': 'dungeon.inventory 1', '⛏ Dig': 'dungeon.mine', '🦕 Condition': 'dungeon.dinos_stats'
                            }

                    if userid == dungeonid:
                        inl_l2 = {'⏩ Next room': 'dungeon.next_room', '❌ Exclude': 'dungeon.kick_member'}

                    else:
                        inl_l2 = {'✅ Ready': 'dungeon.next_room_ready', '🚪 Go out': 'dungeon.leave_in_game_answer'}

                markup_inline.add( *[ types.InlineKeyboardButton( text = inl, callback_data = f"{inl_l[inl]} {dungeonid}") for inl in inl_l.keys() ])

                markup_inline.add( *[ types.InlineKeyboardButton( text = inl, callback_data = f"{inl_l2[inl]} {dungeonid}") for inl in inl_l2.keys() ])

            elif type == 'town':

                if dung['settings']['lang'] == 'ru':
                    inl_l = { '📜 Инвентарь': 'dungeon.inventory 1', '🧭 Лавка': 'dungeon.shop_menu', '🦕 Состояние': 'dungeon.dinos_stats'
                            }

                    if userid == dungeonid:
                        inl_l2 = {'⏩ След. комната': 'dungeon.next_room', '❌ Исключить': 'dungeon.kick_member'}

                    else:
                        inl_l2 = {'✅ Готовность': 'dungeon.next_room_ready', '🚪 Выйти': 'dungeon.leave_in_game_answer'}

                else:
                    inl_l = { '📜 Inventory': 'dungeon.inventory 1', '🧭 Shop': 'dungeon.shop_menu', '🦕 Condition': 'dungeon.dinos_stats'
                            }

                    if userid == dungeonid:
                        inl_l2 = {'⏩ Next room': 'dungeon.next_room', '❌ Exclude': 'dungeon.kick_member'}

                    else:
                        inl_l2 = {'✅ Ready': 'dungeon.next_room_ready', '🚪 Go out': 'dungeon.leave_in_game_answer'}

                markup_inline.add( *[ types.InlineKeyboardButton( text = inl, callback_data = f"{inl_l[inl]} {dungeonid}") for inl in inl_l.keys() ])

                markup_inline.add( *[ types.InlineKeyboardButton( text = inl, callback_data = f"{inl_l2[inl]} {dungeonid}") for inl in inl_l2.keys() ])


            elif type == 'safe_exit':
                markup_inline = types.InlineKeyboardMarkup(row_width = 3)

                if dung['settings']['lang'] == 'ru':

                    if userid == dungeonid:
                        inl_l = {'⏩ След. комната': f'dungeon.next_room {dungeonid}', '🚪 Выйти': f'dungeon.safe_exit {dungeonid}'}

                    else:
                        inl_l = {'✅ Готовность': f'dungeon.next_room_ready {dungeonid}', '🚪 Выйти': f'dungeon.safe_exit {dungeonid}'}

                else:

                    if userid == dungeonid:
                        inl_l = {'⏩ Next room': f'dungeon.next_room {dungeonid}', '🚪 Exit': f'dungeon.safe_exit {dungeonid}'}

                    else:
                        inl_l = {'✅ Ready': f'dungeon.next_room_ready {dungeonid}', '🚪 Exit': f'dungeon.safe_exit {dungeonid}'}

                markup_inline.add( *[ types.InlineKeyboardButton( text = inl, callback_data = inl_l[inl] ) for inl in inl_l.keys() ])


            elif type in ['fork_2', 'fork_3']:
                markup_inline = types.InlineKeyboardMarkup(row_width = 3)

                inl_l = {"1️⃣": f'dungeon.fork_answer {dungeonid} 1', '2️⃣': f'dungeon.fork_answer {dungeonid} 2'}

                if type == 'fork_3':
                    inl_l["3️⃣"] = f'dungeon.fork_answer {dungeonid} 3'


                if dung['settings']['lang'] == 'ru':

                    if userid == dungeonid:
                        inl_l2['❌ Исключить'] = f'dungeon.kick_member {dungeonid}'

                    else:
                        inl_l2['🚪 Выйти'] = f'dungeon.leave_in_game_answer {dungeonid}'

                else:
                    if userid == dungeonid:
                        inl_l2['❌ Exclude'] = f'dungeon.kick_member {dungeonid}'

                    else:
                        inl_l2['🚪 Go out'] = f'dungeon.leave_in_game_answer {dungeonid}'

                markup_inline.add( *[ types.InlineKeyboardButton( text = inl, callback_data = inl_l[inl] ) for inl in inl_l.keys() ])

                markup_inline.add( *[ types.InlineKeyboardButton( text = inl, callback_data = inl_l2[inl] ) for inl in inl_l2.keys() ])

            elif type == 'battle_action':
                markup_inline = types.InlineKeyboardMarkup(row_width = 2)

                if dung['settings']['lang'] == 'ru':
                    inl_l = {"⚔ Атаковать": 'dungeon.battle_action_attack', '🛡 Защищаться': 'dungeon.battle_action_defend', '❌ Бездействовать': 'dungeon.battle_action_idle'}
                else:
                    inl_l = {"⚔ Attack": 'dungeon.battle_action_attack', '🛡 Defend yourself': 'dungeon.battle_action_defend', '❌ Idle': 'dungeon.battle_action_idle'}

                markup_inline.add( *[ types.InlineKeyboardButton( text = inl, callback_data = f"{inl_l[inl]} {dungeonid} {kwargs['dinoid']}") for inl in inl_l.keys() ])

            elif type == 'battle':
                room_n = dung['stage_data']['game']['room_n']
                room = dung['floor'][str(room_n)]

                markup_inline = types.InlineKeyboardMarkup(row_width = 2)

                if room['next_room'] == False:
                    inl_l = {}

                    if str(userid) == dung['stage_data']['game']['player_move'][0]:
                        d_inl = {}

                        bd_user = users.find_one({"userid": int(userid) })

                        for d_k in dung['users'][str(userid)]['dinos'].keys():
                            din_name = bd_user['dinos'][str(d_k)]['name']
                            d_inl[f'#{d_k} {din_name}'] = f'dungeon.action.battle_action {dungeonid} {d_k}'

                        markup_inline.add( *[ types.InlineKeyboardButton( text = inl, callback_data = f"{d_inl[inl]}") for inl in d_inl.keys() ])

                        if dung['settings']['lang'] == 'ru':
                            inl_l["✅ Завершить ход"] = 'dungeon.end_move'
                        else:
                            inl_l["✅ Complete the move"] = 'dungeon.end_move'

                    if dung['settings']['lang'] == 'ru':

                        if userid == dungeonid:
                            inl_l['❌ Исключить'] = 'dungeon.kick_member'

                        else:
                            inl_l['🚪 Выйти'] = 'dungeon.leave_in_game_answer'

                        if dung['settings']['battle_notifications'] == False:

                            inl_l['🦕 Состояние'] = 'dungeon.dinos_stats'

                    else:

                        if userid == dungeonid:
                            inl_l['❌ Exclude'] = 'dungeon.kick_member'

                        else:
                            inl_l['🚪 Go out'] = 'dungeon.leave_in_game_answer'

                        if dung['settings']['battle_notifications'] == False:

                            inl_l['🦕 Condition'] = 'dungeon.dinos_stats'

                    markup_inline.add( *[ types.InlineKeyboardButton( text = inl, callback_data = f"{inl_l[inl]} {dungeonid}") for inl in inl_l.keys() ])

                if room['next_room'] == True:

                    if dung['settings']['lang'] == 'ru':
                        inl_l = { '📜 Инвентарь': 'dungeon.inventory 1', '🦕 Состояние': 'dungeon.dinos_stats', '👑 Награда': 'dungeon.collect_reward'
                                }

                        if userid == dungeonid:
                            inl_l2 = {'⏩ След. комната': 'dungeon.next_room', '❌ Исключить': 'dungeon.kick_member'}

                        else:
                            inl_l2 = {'✅ Готовность': 'dungeon.next_room_ready', '🚪 Выйти': 'dungeon.leave_in_game_answer'}

                    else:
                        inl_l = { '📜 Inventory': 'dungeon.inventory 1', '🦕 Condition': 'dungeon.dinos_stats', '👑 Reward': 'dungeon.collect_reward'
                                }

                        if userid == dungeonid:
                            inl_l2 = {'⏩ Next room': 'dungeon.next_room', '❌ Exclude': 'dungeon.kick_member'}

                        else:
                            inl_l2 = {'✅ Ready': 'dungeon.next_room_ready', '🚪 Go out': 'dungeon.leave_in_game_answer'}

                    markup_inline.add( *[ types.InlineKeyboardButton( text = inl, callback_data = f"{inl_l[inl]} {dungeonid}") for inl in inl_l.keys() ])

                    markup_inline.add( *[ types.InlineKeyboardButton( text = inl, callback_data = f"{inl_l2[inl]} {dungeonid}") for inl in inl_l2.keys() ])

            elif type == 'game':

                if dung['settings']['lang'] == 'ru':
                    inl_l = { '📜 Инвентарь': 'dungeon.inventory 1', '🦕 Состояние': 'dungeon.dinos_stats'
                            }

                    if userid == dungeonid:
                        inl_l2 = {'⏩ След. комната': 'dungeon.next_room', '❌ Исключить': 'dungeon.kick_member'}

                    else:
                        inl_l2 = {'✅ Готовность': 'dungeon.next_room_ready', '🚪 Выйти': 'dungeon.leave_in_game_answer'}

                else:
                    inl_l = { '📜 Inventory': 'dungeon.inventory 1', '🦕 Condition': 'dungeon.dinos_stats'
                            }

                    if userid == dungeonid:
                        inl_l2 = {'⏩ Next room': 'dungeon.next_room', '❌ Exclude': 'dungeon.kick_member'}

                    else:
                        inl_l2 = {'✅ Ready': 'dungeon.next_room_ready', '🚪 Go out': 'dungeon.leave_in_game_answer'}

                markup_inline.add( *[ types.InlineKeyboardButton( text = inl, callback_data = f"{inl_l[inl]} {dungeonid}") for inl in inl_l.keys() ])

                markup_inline.add( *[ types.InlineKeyboardButton( text = inl, callback_data = f"{inl_l2[inl]} {dungeonid}") for inl in inl_l2.keys() ])

            elif type == 'preparation':

                if dung['settings']['lang'] == 'ru':
                    inl_l = {'🦕 Добавить': 'dungeon.menu.add_dino',
                             '💼 Припасы':  'dungeon.supplies',
                             '🦕 Удалить':  'dungeon.menu.remove_dino'
                            }

                    if userid == dungeonid:
                        inl_l['🛠 Настройки'] = 'dungeon.settings'
                        inl_l['👥 Пригласить'] = 'dungeon.invite'
                        inl_l2 = {'✅ Начать': 'dungeon.start'}

                    else:
                        inl_l2 = {'✅ Готовность': 'dungeon.ready', '🚪 Выйти': 'dungeon.leave'}

                else:
                    inl_l = {'🦕 Add': 'dungeon.menu.add_dino',
                             '💼 Supplies': 'dungeon.supplies',
                             '🦕 Remove':  'dungeon.menu.remove_dino'
                            }

                    if userid == dungeonid:
                        inl_l['🛠 Settings'] = 'dungeon.settings'
                        inl_l['👥 Invite'] = 'dungeon.invite'
                        inl_l2 = {'✅ Start': 'dungeon.start'}
                    else:
                        inl_l2 = {'✅ Ready': 'dungeon.ready', '🚪 Go out': 'dungeon.leave'}

                markup_inline.add( *[ types.InlineKeyboardButton( text = inl, callback_data = f"{inl_l[inl]} {dungeonid}") for inl in inl_l.keys() ])

                markup_inline.add( *[ types.InlineKeyboardButton( text = inl, callback_data = f"{inl_l2[inl]} {dungeonid}") for inl in inl_l2.keys() ])

            elif type == 'settings':
                markup_inline = types.InlineKeyboardMarkup(row_width = 2)

                start_floor = dung['settings']['start_floor'] + 1

                if dung['settings']['lang'] == 'ru':
                    inl_l = {'Язык: 🇷🇺': 'dungeon.settings_lang',
                             '🗑 Удалить': 'dungeon.remove'
                            }

                    if dung['settings']['battle_notifications'] == True:
                        inl_l['👁‍🗨 Уведомления в бою: Вкл'] = 'dungeon.settings_batnotf'

                    else:
                        inl_l['👁‍🗨 Уведомления в бою: Откл'] = 'dungeon.settings_batnotf'

                    inl_l2 = {
                    f'🏷 Начальный этаж: {start_floor}': 'dungeon.settings_start_floor',
                    '🕹 Назад': 'dungeon.to_lobby'
                    }

                else:
                    inl_l = {'Language: 🇬🇧': 'dungeon.settings_lang',
                             '🗑 Delete': 'dungeon.remove'
                            }

                    if dung['settings']['battle_notifications'] == True:
                        inl_l['👁‍🗨 Notifications in Battle: On'] = 'dungeon.settings_batnotf'

                    else:
                        inl_l['👁‍🗨 Notifications in Battle: Off'] = 'dungeon.settings_batnotf'

                    inl_l2 = {f'🏷 Начальный этаж: {start_floor}': 'dungeon.settings_start_floor',
                    '🕹 Back': 'dungeon.to_lobby'
                    }

                markup_inline.add( *[ types.InlineKeyboardButton( text = inl, callback_data = f"{inl_l[inl]} {dungeonid}") for inl in inl_l.keys() ])

                markup_inline.add( *[ types.InlineKeyboardButton( text = inl, callback_data = f"{inl_l2[inl]} {dungeonid}") for inl in inl_l2.keys() ])

            elif type == 'invite_room':

                if dung['settings']['lang'] == 'ru':
                    inl_l = {'🕹 Назад': 'dungeon.to_lobby'}

                else:
                    inl_l = {'🕹 Back': 'dungeon.to_lobby'}

                markup_inline.add( *[ types.InlineKeyboardButton( text = inl, callback_data = f"{inl_l[inl]} {dungeonid}") for inl in inl_l.keys() ])

            elif type == 'add_dino':

                if dung['settings']['lang'] == 'ru':
                    inl_l = {'⚙ Действие: Добавить': 'dungeon.menu.remove_dino'
                            }

                    inl_l2 = {'🕹 Назад': 'dungeon.to_lobby'
                            }

                else:
                    inl_l = {'⚙ Action: Add': 'dungeon.menu.remove_dino'
                            }
                    inl_l2 = {'🕹 Back': 'dungeon.to_lobby'
                            }

                d_inl = {}

                bd_user = users.find_one({"userid": int(userid) })
                for d_k in bd_user['dinos'].keys():
                    if d_k not in dung['users'][str(userid)]['dinos'].keys():
                        din_name = bd_user['dinos'][str(d_k)]['name']
                        d_inl[f'#{d_k} {din_name}'] = f'dungeon.action.add_dino {dungeonid} {d_k}'


                markup_inline.add( *[ types.InlineKeyboardButton( text = inl, callback_data = f"{inl_l[inl]} {dungeonid}") for inl in inl_l.keys() ])

                markup_inline.add( *[ types.InlineKeyboardButton( text = inl, callback_data = f"{d_inl[inl]}") for inl in d_inl.keys() ])

                markup_inline.add( *[ types.InlineKeyboardButton( text = inl, callback_data = f"{inl_l2[inl]} {dungeonid}") for inl in inl_l2.keys() ])

            elif type == 'remove_dino':

                if dung['settings']['lang'] == 'ru':
                    inl_l = {'⚙ Действие: Удалить': 'dungeon.menu.add_dino'
                            }

                    inl_l2 = {'🕹 Назад': 'dungeon.to_lobby'
                            }

                else:
                    inl_l = {'⚙ Action: Delete': 'dungeon.menu.add_dino'
                            }
                    inl_l2 = {'🕹 Back': 'dungeon.to_lobby'
                            }

                d_inl = {}

                bd_user = users.find_one({"userid": int(userid) })
                for d_k in dung['users'][str(userid)]['dinos'].keys():
                    din_name = bd_user['dinos'][str(d_k)]['name']
                    d_inl[f'#{d_k} {din_name}'] = f'dungeon.action.remove_dino {dungeonid} {d_k}'


                markup_inline.add( *[ types.InlineKeyboardButton( text = inl, callback_data = f"{inl_l[inl]} {dungeonid}") for inl in inl_l.keys() ])

                markup_inline.add( *[ types.InlineKeyboardButton( text = inl, callback_data = f"{d_inl[inl]}") for inl in d_inl.keys() ])

                markup_inline.add( *[ types.InlineKeyboardButton( text = inl, callback_data = f"{inl_l2[inl]} {dungeonid}") for inl in inl_l2.keys() ])

            elif type == 'supplies':
                markup_inline = types.InlineKeyboardMarkup(row_width = 2)

                if dung['settings']['lang'] == 'ru':
                    inl_l = {'⚙ Добавить': 'dungeon.action.add_item',
                             '💸 Монеты': 'dungeon.action.set_coins',
                             '⚙ Удалить': 'dungeon.action.remove_item'
                            }

                    inl_l2 = {'🕹 Назад': 'dungeon.to_lobby'
                            }

                else:
                    inl_l = {'⚙ Add': 'dungeon.action.add_item',
                             '💸 Coins': 'dungeon.action.set_coins',
                             '⚙ Remove': 'dungeon.action.remove_item'
                            }
                    inl_l2 = {'🕹 Back': 'dungeon.to_lobby'
                            }

                bd_user = users.find_one({"userid": int(userid) })

                markup_inline.row( *[ types.InlineKeyboardButton( text = inl, callback_data = f"{inl_l[inl]} {dungeonid}") for inl in inl_l.keys() ])

                markup_inline.add( *[ types.InlineKeyboardButton( text = inl, callback_data = f"{inl_l2[inl]} {dungeonid}") for inl in inl_l2.keys() ])

            elif type == 'collect_reward':

                room_n = str(dung['stage_data']['game']['room_n'])
                room_rew = dung['floor'][room_n]['reward']

                inv = room_rew['collected'][ str(userid) ]['items']
                r_inv = room_rew['items']
                d_items = []

                for itm in inv:

                    if itm in r_inv:
                        r_inv.remove(itm)

                d_items = r_inv
                inl_l = {}

                if dung['settings']['lang'] == 'ru':
                    inl_l2 = {'🕹 Назад': 'dungeon.to_lobby'}

                else:
                    inl_l2 = {'🕹 Back': 'dungeon.to_lobby'}

                for itm in d_items:
                    item_data = items_f['items'][ itm['item_id'] ]

                    if Functions.item_authenticity(itm) == False:
                        nlg = f"name{dung['settings']['lang']}"
                        iname = f'{item_data[ nlg ]} ({Functions.qr_item_code(itm, False)})'
                    else:
                        iname = item_data[ f"name{dung['settings']['lang']}" ]

                    if iname not in inl_l.keys():
                        if 'abilities' in itm.keys():
                            inl_l[ iname ] = {'item_id': itm['item_id'], 'col': 1, 'abilities': itm['abilities']}

                        else:
                            inl_l[ iname ] = {'item_id': itm['item_id'], 'col': 1}

                    else:
                        inl_l[ iname ]['col'] += 1

                markup_inline.add( *[ types.InlineKeyboardButton( text = f"{inl} x{inl_l[inl]['col']}", callback_data = f"dungeon.item_from_reward {dungeonid} {Functions.qr_item_code(inl_l[inl]) }") for inl in inl_l.keys() ])

                markup_inline.add( *[ types.InlineKeyboardButton( text = inl, callback_data = f"{inl_l2[inl]} {dungeonid}") for inl in inl_l2.keys() ])

            else:
                print('error_type_dont_find')

            return markup_inline

        else:
            print('error_no_dungeon')
            return markup_inline

    def message_upd(bot, userid = None, dungeonid = None, upd_type = 'one', type = None, image_update = False, ignore_list = [], kwargs = {}):

        def update(dung, text, stage_type, image_way = None):

            def message_updt(users_ids):
                undl = 0
                dl = 0

                for u_k in users_ids:
                    us = dung['users'][str(u_k)]

                    if int(u_k) not in ignore_list:

                        if upd_type == 'one' or us['last_page'] == 'main':

                            if us['messageid'] != None:

                                if image_update == False:

                                    try:
                                        bot.edit_message_caption(text, int(u_k), us['messageid'], parse_mode = 'Markdown', reply_markup = Dungeon.inline(bot, int(u_k), dungeonid = dungeonid, type = stage_type))
                                        dl += 1
                                    except Exception as e:
                                        #print(e)
                                        undl += 1

                                if image_update == True:
                                    image = open(image_way, 'rb')

                                    try:

                                        bot.edit_message_media(
                                            chat_id = int(u_k),
                                            message_id =  int(dung['users'][str(u_k)]['messageid']),
                                            reply_markup = Dungeon.inline(bot, int(u_k), dungeonid = dungeonid, type = stage_type),
                                            media = telebot.types.InputMedia(type='photo', media = image, caption = text, parse_mode = 'Markdown')
                                        )
                                    except Exception as e:
                                        return f'2error_(message_and_image_no_update)? {e} ?'

                            else:
                                image = open(image_way, 'rb')

                                try:
                                    msg = bot.send_photo(int(u_k), image, text, parse_mode = 'Markdown', reply_markup = Dungeon.inline(bot, int(u_k), dungeonid = dungeonid, type = stage_type))

                                    Dungeon.base_upd(userid = int(u_k), messageid = msg.id, dungeonid = dung['dungeonid'], type = 'edit_message')

                                    dl += 1
                                except Exception as e:
                                    return f'5error_(message_no_update)? {e} ?'

                return f'message_update < upd {dl} - unupd {undl} >'

            if upd_type == 'one':

                return message_updt( [str(userid)] )

            if upd_type == 'all':

                return message_updt( list( dung['users'].keys() ) )

            else:
                return 'upd_type_dont_find'

        dung = dungeons.find_one({"dungeonid": dungeonid})

        if dung != None:
            if type == None:

                if dung['dungeon_stage'] == 'game':

                    text, inline_type, image = Dungeon.panel_message(bot, dung, type, image_update)

                    return update(dung, text, inline_type, image)

                if dung['dungeon_stage'] == 'preparation':

                    if dung['settings']['lang'] == 'ru':
                        inf_m = '`/message_update` - если сообщение не обновляется\n'

                        text = f'*🎴 Лобби*\n\n   *🗻 | Информация*\nВы стоите перед входом в подземелье. Кого-то трясёт от страха, а кто-то жаждет приключений. Что вы найдёте в подземелье, известно только богу удачи, соберите команду и покорите бесконечное подземелье!\n{inf_m}\n   *🦕 | Динозавры*'

                    else:
                        inf_m = '`/message_update` - if the message is not updated\n'

                        text = f"*🎴 Lobby*\n\n   *🗻 | Information*\nYou are standing in front of the entrance to the dungeon. Someone is shaking with fear, and someone is eager for adventure. What you will find in the dungeon is known only to the god of luck, gather a team and conquer the endless dungeon!\n{inf_m}\n   *🦕 | Dinosaurs*"

                    d_n = 0
                    dinos_text = ''
                    users_text = ''
                    u_n = 0
                    for k in dung['users'].keys():
                        us = dung['users'][k]
                        bd_us = users.find_one({"userid": int(k)})

                        if int(k) in dung['stage_data']['preparation']['ready']:
                            r_e = '✅'

                        else:
                            r_e = '❌'

                        u_n += 1
                        username = bot.get_chat(int(k)).first_name
                        users_text += f'{u_n}. {username} (🦕 {len(us["dinos"])})  ({r_e})\n'

                        for din in us['dinos'].keys():
                            d_n += 1

                            if d_n % 2 == 0:
                                dinos_text += '   |   '
                            else:
                                if d_n != 0:
                                    dinos_text += '\n'

                            dinos_text += f'{bd_us["dinos"][din]["name"]}'


                    text += f" {d_n} / {dung['settings']['max_dinos']}"
                    text += dinos_text

                    if dung['settings']['lang'] == 'ru':
                        text += '\n\n   *👥 | Игроки*\n'

                    else:
                        text += '\n\n   *👥 | Players*\n'

                    text += users_text

                    return update(dung, text, 'preparation', f"images/dungeon/preparation/{dung['stage_data']['preparation']['image']}.png")

            elif type == 'delete_dungeon':
                dl = 0
                undl = 0
                text = ' '

                if dung['dungeon_stage'] == 'game':
                    floor_n = dung['stage_data']['game']['floor_n']
                    floors_st = dung['stage_data']['game']['floors_stat']
                    flr_text = ''
                    mobs_count = 0

                    start_floor = dung['settings']['start_floor']

                    for flr_k in floors_st:
                        floor_st = floors_st[flr_k]
                        mobs_count += floor_st['mobs_killing']

                        try:
                            if dung['settings']['lang'] == 'ru':
                                flr_time = Functions.time_end(floor_st['end_time'] - floor_st['start_time'])
                                flr_text += f'{flr_k}# Время: {flr_time}\n   *└* Убито: {floor_st["mobs_killing"]}\n\n'

                            else:
                                flr_time = Functions.time_end(floor_st['end_time'] - floor_st['start_time'], True)
                                flr_text += f'{flr_k}# Time: {flr_time}\n   *└ *Killed: {floor_st["mobs_killing"]}\n\n'
                        except:
                            pass

                    if dung['settings']['lang'] == 'ru':
                        text = f'*🗻 | Подземелье завершено!*\n\n*🗝 | Статистика*\n\n🏆 Пройдено этажей: {floor_n - start_floor}\n👿 Убито боссов: {(floor_n - start_floor) // 10}\n😈 Убито мобов: {mobs_count}\n\n*🖼 | Статистика по этажам*\n\n{flr_text}'
                    else:
                        text = f'*🗻 | Dungeon conspiracy!*\n\n*🗝 | Statistics*\n\nFloors passed: {floor_n - start_floor} 🏆\nBosses killed: {(floor_n - start_floor) // 10}\nMobs killed:: {mobs_count}\n\n*🖼 | Floor statistics*\n\n{flr_text}'

                if dung['dungeon_stage'] == 'preparation':

                    if dung['settings']['lang'] == 'ru':
                        text = '🗻 | Подземелье удалено'
                    else:
                        text = '🗻 | Dungeon removed'

                for u_k in dung['users']:
                    us = dung['users'][u_k]

                    try:
                        bot.delete_message(int(u_k), us['messageid'])
                        bot.send_message(int(u_k), text, parse_mode = 'Markdown', reply_markup = Functions.markup(bot, "dungeon_menu", int(u_k) ))
                        dl += 1
                    except Exception as e:
                        undl += 1
                        #print(e)

                return f'message_update < delete {dl} - undelete {undl} >'

            elif type == 'collect_reward':
                room_n = str(dung['stage_data']['game']['room_n'])
                room_rew = dung['floor'][room_n]['reward']

                if dung['settings']['lang'] == 'ru':
                    text = f"🏆 | Вы достойно сражались, заполните свой рюкзак материалами и выдвигайтесь дальше!\n\n🎇 Опыт: {room_rew['experience']}\n👑 Монеты: {room_rew['coins']}"
                else:
                    text = f"🏆 | You fought with dignity, fill your backpack with materials and move on!\n\n🎇 Experience: {room_rew['experience']}\n👑 Coins: {room_rew['coins']}"

                if str(userid) not in room_rew['collected'].keys():
                    room_rew['collected'][str(userid)] = {'experience': True, 'items': []}

                    bd_user = users.find_one({"userid": int(userid) })
                    bd_user['lvl'][1] += room_rew['experience']

                    users.update_one( {"userid": bd_user['userid']}, {"$set": {'lvl': bd_user['lvl'] }} )

                    dungeons.update_one( {"dungeonid": dungeonid}, {"$set": {f'floor': dung['floor'] }} )

                try:

                    bot.edit_message_caption(
                        chat_id = int(userid),
                        message_id =  int(dung['users'][str(userid)]['messageid']),
                        caption = text,
                        reply_markup = Dungeon.inline(bot, int(userid), dungeonid = dungeonid, type = 'collect_reward'),
                    )

                except Exception as e:
                    return f'message_dont_update - collect_reward ~{e}~'

                return 'message_update - collect_reward'

            elif type == 'settings':

                if dung['settings']['lang'] == 'ru':
                    text = '⚙ | Настройте ваше подземелье для комфортной игры!'

                else:
                    text = '⚙ | Customize your dungeon for a comfortable game!'

                try:

                    image = open('images/dungeon/settings/1.png','rb')
                    bot.edit_message_media(
                        chat_id = int(userid),
                        message_id =  int(dung['users'][str(userid)]['messageid']),
                        reply_markup = Dungeon.inline(bot, int(userid), dungeonid = dungeonid, type = 'settings'),
                        media = telebot.types.InputMedia(type='photo', media = image, caption = text)
                    )

                except Exception as e:
                    return f'message_dont_update - settings ~{e}~'

                return 'message_update - settings'

            elif type == 'invite_room':

                if dung['settings']['lang'] == 'ru':
                    text = f'🎲 | Код приглашения: `{dungeonid}` (можно кликнуть)\n\n📢 | Отправте друзьям код приглашения, чтобы они могли присоединиться к вам!'

                else:
                    text = f'🎲 | Invitation code: `{dungeonid}` (you can click)\n\n📢 | Send your friends an invitation code so they can join you!'

                try:

                    image = open('images/dungeon/invite_room/1.png','rb')
                    bot.edit_message_media(
                        chat_id = int(userid),
                        message_id =  int(dung['users'][str(userid)]['messageid']),
                        reply_markup = Dungeon.inline(bot, int(userid), dungeonid = dungeonid, type = 'invite_room'),
                        media = telebot.types.InputMedia(type='photo', media = image, parse_mode = 'Markdown', caption = text)
                    )

                except Exception as e:
                    return f'message_dont_update - invite_room ~{e}~'

                return 'message_update - invite_room'

            elif type == 'supplies':

                bd_user = users.find_one({"userid": userid})
                items_id = [ i['item_id'] for i in dung['users'][str(userid)]['inventory']]

                floor = dung['settings']['start_floor'] + 1
                min_money = 150 + floor * 50

                if dung['settings']['lang'] == 'ru':
                    text = f'💼 | Во время путешествия в подземелье может случится что-то неожиданное. Лучше быть готовым ко всему. Учтите, для входа в подземелье требуется минимум {min_money} монет!\n\n💸 | Монеты: { dung["users"][str(userid)]["coins"] }\n👜 | Вместимость рюкзака: {len(dung["users"][str(userid)]["inventory"])} / {Dungeon.d_backpack(bd_user)}\n🧵 | Предметы: {", ".join(Functions.sort_items_col( items_id, "ru" ))}'

                else:
                    text = f"💼 | During the journey to the dungeon, something unexpected may happen. It's better to be prepared for everything.Please note that a minimum of {min_money} coins is required to enter the dungeon!\n\n💸 | Coins: {dung['users'][str(userid)]['coins']}\n👜 | Backpack capacity: {len(dung['users'][str(userid)]['inventory'])} / {Dungeon.d_backpack(bd_user)}\n🧵 | Items: {', '.join(Functions.sort_items_col( items_id, 'en' ))}"

                try:

                    image = open('images/dungeon/supplies/1.png','rb')
                    bot.edit_message_media(
                        chat_id = int(userid),
                        message_id =  int(dung['users'][str(userid)]['messageid']),
                        reply_markup = Dungeon.inline(bot, int(userid), dungeonid = dungeonid, type = 'supplies'),
                        media = telebot.types.InputMedia(type='photo', media = image, parse_mode = 'Markdown', caption = text)
                    )

                except Exception as e:
                    return f'message_dont_update - supplies ~{e}~'

                return 'message_update - supplies'

            elif type in ['add_dino', 'limit_(add_dino)', 'action_dino_is_not_pass']:

                if dung['settings']['lang'] == 'ru':
                    text = '🦕 | Выберите динозавров из списка ниже, чтобы он принял участие в подземелье. Динозавры могут принять участие, только если ничем не заняты в данный момент!\n\n🍔 | Вы можете изменить действие на Добавить / Удалить.'
                    text_limit = '\n\n💢 | В лобби уже максимальное количество динозавров!'
                    text_inp = '\n\n💢 | Динозавр уже чем-то занят!'

                else:
                    text = '🦕 | Select the dinosaurs from the list below to take part in the dungeon. Dinosaurs can take part only if they are not busy at the moment!\n\n🍔 | You can also change the action to Add / Remove.'
                    text_limit = '\n\n💢 | There is already a maximum number of dinosaurs in the lobby!'
                    text_inp = '💢 | The dinosaur is already busy with something!'

                if type == 'limit_(add_dino)':
                    text += text_limit

                if type == 'action_dino_is_not_pass':
                    text += text_inp

                try:

                    image = open('images/dungeon/add_remove_dino/1.png','rb')
                    bot.edit_message_media(
                        chat_id = int(userid),
                        message_id =  int(dung['users'][str(userid)]['messageid']),
                        reply_markup = Dungeon.inline(bot, int(userid), dungeonid = dungeonid, type = 'add_dino'),
                        media = telebot.types.InputMedia(type='photo', media = image, caption = text)
                    )

                except Exception as e:
                    return f'message_dont_update - settings ~{e}~'

                return 'message_update - add_dino'

            elif type == 'remove_dino':

                if dung['settings']['lang'] == 'ru':
                    text = '🦕 | Выберите динозавра, который не будет принимать участие.\n\n🍔 | Вы можете изменить действие на Добавить / Удалить.'

                else:
                    text = '🦕 | Choose a dinosaur that will not take part.\n\n🍔 | You can also change the action to Add / Remove.'

                try:

                    image = open('images/dungeon/add_remove_dino/1.png','rb')
                    bot.edit_message_media(
                        chat_id = int(userid),
                        message_id =  int(dung['users'][str(userid)]['messageid']),
                        reply_markup = Dungeon.inline(bot, int(userid), dungeonid = dungeonid, type = 'remove_dino'),
                        media = telebot.types.InputMedia(type='photo', media = image, caption = text)
                    )

                except Exception as e:
                    return f'message_dont_update - settings ~{e}~'

                return 'message_update - remove_dino'

            elif type == 'user_inventory':

                page = kwargs['page']
                bd_user = kwargs['bd_user']
                items = dung['users'][str(userid)]['inventory']
                data_items = items_f['items']
                sort_items = {}

                if dung['settings']['lang'] == 'ru':
                    lg_name = "nameru"
                else:
                    lg_name = "nameen"

                for i in items:

                    if Functions.item_authenticity(i) == True:

                        if data_items[ str(i['item_id']) ][lg_name] not in sort_items.keys():
                            sort_items[ data_items[ str(i['item_id']) ][lg_name] ] = { 'col': 1, 'callback_data': f"dungeon_use_item_info {dungeonid} {Functions.qr_item_code(i)}" }

                        else:
                            sort_items[ data_items[ str(i['item_id']) ][lg_name] ]['col'] += 1

                    else:
                        if f"{data_items[ str(i['item_id']) ][lg_name]} ({Functions.qr_item_code(i, False)})" not in sort_items.keys():

                            sort_items[ f"{data_items[ str(i['item_id']) ][lg_name]} ({Functions.qr_item_code(i, False)})" ] = { 'col': 1, 'callback_data': f"dungeon_use_item_info {dungeonid} {Functions.qr_item_code(i)}" }

                        else:
                            sort_items[ f"{data_items[ str(i['item_id']) ][lg_name]} ({Functions.qr_item_code(i, False)})" ]['col'] += 1

                sort_items_keys = {}
                sort_list = []

                for i in sort_items.keys():
                    i_n = f'{i} x{sort_items[i]["col"]}'

                    if i_n not in sort_list:
                        sort_list.append( i_n )
                        sort_items_keys[ i_n ] = sort_items[i]['callback_data']

                pages_inv = list( Functions.chunks(sort_list, 6) )
                inl_d = {}
                markup_inline = types.InlineKeyboardMarkup(row_width = 2)

                if pages_inv != []:
                    sl_n = 0

                    for i in pages_inv[page-1]:
                        sl_n += 1
                        inl_d[i] = sort_items_keys[i]

                    if sl_n != 6:
                        for _ in range(6 - sl_n):
                            sl_n += 1
                            inl_d[ ' ' * (6 - sl_n) ] = '-'

                    markup_inline.add( *[
                                        types.InlineKeyboardButton(
                                            text = inl,
                                            callback_data = inl_d[inl] ) for inl in inl_d.keys()
                                     ])

                if len(pages_inv) > 1:

                    inl_serv = { }

                    if page - 1 < 1:
                        m_page = 1

                    else:
                        m_page = page - 1
                        inl_serv['◀'] = f'dungeon.inventory {m_page} {dungeonid}'

                    inl_serv['❌'] = f'dungeon.to_lobby {dungeonid}'

                    if page + 1 > len(pages_inv):
                        p_page = len(pages_inv)

                    else:
                        p_page = page + 1
                        inl_serv['▶'] = f'dungeon.inventory {p_page} {dungeonid}'

                else:
                    inl_serv = { '❌': f'dungeon.to_lobby {dungeonid}'}

                markup_inline.row( *[ types.InlineKeyboardButton(
                                      text = inl,
                                      callback_data = inl_serv[inl] ) for inl in inl_serv.keys()
                                 ])

                if dung['settings']['lang'] == 'ru':
                    text = ( f"🎒 | Инвентарь\n\n"
                             f"👑 | Монет: {dung['users'][ str(userid) ]['coins']}\n"
                             f"🎈 | Предметов: {len(dung['users'][ str(userid) ]['inventory'])} / {Dungeon.d_backpack(bd_user)}"
                           )

                else:
                    text = ( f"🎒 | Inventory\n\n"
                             f"👑 | Coins: {dung['users'][ str(userid) ]['coins']}\n"
                             f"🎈 | Items: {len(dung['users'][ str(userid) ]['inventory'])} / {Dungeon.d_backpack(bd_user)}"
                           )

                bot.edit_message_caption(text, int(userid), dung['users'][ str(userid) ]['messageid'], parse_mode = 'Markdown', reply_markup = markup_inline)


            else:
                return 'error_type_no_ind'

        else:
            return 'error_no_dungeon'

    def d_backpack(bd_user):

        data_items = items_f['items']

        if 'user_dungeon' in bd_user.keys():

            item = bd_user['user_dungeon']["equipment"]['backpack']

            if item == None:
                return 5

            else:
                return data_items[ item['item_id'] ]['capacity']

        else:
            return 5

    def generate_boss_image(image_way, boss, dungeonid):

        def generate_bar(act, maxact):

            colorbg = '#9a1752'
            color = '#ff0000'
            mask_way = 'images/dungeon/remain/bar_mask_heal_boss.png'

            sz_osn = [900, 70]
            szz = [ sz_osn[1] / 100 * 90, sz_osn[1] / 100 * 10 ]

            bar = Image.new('RGB', (sz_osn[0], sz_osn[1]),  color = colorbg)
            mask = Image.open(mask_way).convert('L').resize((sz_osn[0], sz_osn[1]), Image.ANTIALIAS)

            x = (act / maxact) * 100
            x = int(x * 8.7) + 16

            ImageDraw.Draw(bar).polygon(xy=[(szz[1], szz[1]),(x, szz[1]),(x,szz[0]),(szz[1],szz[0])], fill = color)
            bar = bar.filter(ImageFilter.GaussianBlur(0.6))
            bar.putalpha(mask)

            return bar

        data_mob = mobs_f['boss'][ boss['mob_key'] ]

        alpha_img = Image.open('images/dungeon/remain/alpha.png')

        bar = generate_bar(boss['hp'], boss['maxhp'])
        alpha_img = Functions.trans_paste(bar, alpha_img, 1.0, (0, -5) )

        bg_p = Image.open(image_way)
        img = Image.open(mobs_f['boss'][ boss['mob_key']]['image'] )
        sz = 325
        img = img.resize((sz, sz), Image.ANTIALIAS)

        xy = 20
        x2 = 287
        alpha_img = Functions.trans_paste(img, alpha_img, 1, (xy + x2, xy, sz + xy + x2, sz + xy ))

        image = Functions.trans_paste(alpha_img, bg_p, 1.0 )
        image.save(f'boss {dungeonid}.png')

        return 'generation - ok'

    def generate_battle_image(image_way, mob, dungeonid):

        def generate_bar(act, maxact, tp):

            if tp == 'heal':
                colorbg = '#860c1d'
                color = '#ff0000'
                mask_way = 'images/dungeon/remain/bar_mask_heal.png'

            if tp == 'mana':
                colorbg = '#0e3895'
                color = '#009cff'
                mask_way = 'images/dungeon/remain/bar_mask_mana.png'

            bar = Image.new('RGB', (153, 33),  color = colorbg)
            mask = Image.open(mask_way).convert('L').resize((153, 33), Image.ANTIALIAS)

            x = (act / maxact) * 100
            x = int(x * 1.5) + 5

            ImageDraw.Draw(bar).polygon(xy=[(3, 3),(x, 3),(x,30),(3,30)], fill = color)
            bar = bar.filter(ImageFilter.GaussianBlur(0.6))
            bar.putalpha(mask)

            return bar

        data_mob = mobs_f['mobs'][ mob['mob_key'] ]

        alpha_img = Image.open('images/dungeon/remain/alpha.png')

        bg_p = Image.open(image_way)
        img = Image.open(mobs_f['mobs'][ mob['mob_key']]['image'] )
        sz = 350
        img = img.resize((sz, sz), Image.ANTIALIAS)

        xy = -10
        x2 = 100
        alpha_img = Functions.trans_paste(img, alpha_img, 0.95, (xy + x2, xy, sz + xy + x2, sz + xy ))

        # здоровье
        img = Image.open( 'images/dungeon/remain/mob_heal.png' )
        sz1, sz2 = img.size
        sz1, sz2 = int(sz1 / 1.5), int(sz2 / 1.5)

        img = img.resize((sz1, sz2), Image.ANTIALIAS)

        y, x = 50, 390
        alpha_img = Functions.trans_paste(img, alpha_img, 1, (y + x, y, sz1 + y + x, sz2 + y ))

        bar = generate_bar(mob['hp'], mob['maxhp'], 'heal')
        alpha_img = Functions.trans_paste(bar, alpha_img, 1.0, (510, 68) )

        #мана
        if data_mob['damage-type'] == 'magic':

            img = Image.open( 'images/dungeon/remain/mob_mana.png' )
            sz1, sz2 = img.size
            sz1, sz2 = int(sz1 / 1.5), int(sz2 / 1.5)

            img = img.resize((sz1, sz2), Image.ANTIALIAS)

            y, x = 120, 320
            alpha_img = Functions.trans_paste(img, alpha_img, 1, (y + x, y, sz1 + y + x, sz2 + y ))

            bar = generate_bar(mob['mana'], mob['maxmana'], 'mana')
            alpha_img = Functions.trans_paste(bar, alpha_img, 1.0, (510, 140) )

        image = alpha_img = Functions.trans_paste(alpha_img, bg_p, 1.0 )
        image.save(f'{config.TEMP_DIRECTION}/battle {dungeonid}.png')
        return 'generation - ok'

    def battle_user_move(bot, dungeonid, userid, bd_user, call = None):

        dung = dungeons.find_one({"dungeonid": dungeonid})
        room_n = str(dung['stage_data']['game']['room_n'])
        room = dung['floor'][room_n]

        if len(dung['floor'][room_n]['mobs']) != 0:

            if room['battle_type'] == 'mobs':
                mob = dung['floor'][room_n]['mobs'][0]
            else:
                mob = dung['floor'][room_n]['mobs']

            userdata = dung['users'][str(userid)]
            damage = 0
            damage_permission = True
            show_text = ''

            for i in userdata['dinos'].keys():
                dino_data = userdata['dinos'][i]

                if 'action' in dino_data.keys():
                    if dino_data['action'] == 'attack':

                        if bd_user['dinos'][i]['dungeon']['equipment']['weapon'] == None:
                            damage += random.randint(0, 2) #стандартный урон без оружия

                        else:
                            dmg, at_log = Dungeon.dino_attack(bd_user, i, dungeonid)
                            damage += dmg
                            show_text += at_log

                if dung['users'][str(userid)]['dinos'][i]['activ_effects'] != []:
                    pass
                    #print('dino have effect')


            if damage_permission == True:
                mob['hp'] -= damage

            dungeons.update_one( {"dungeonid": dungeonid}, {"$set": {f'floor': dung['floor'] }} )

            if call != None:

                if bd_user['language_code'] == 'ru':
                    show_text += f"🦕 Ваши динозавры нанесли: {damage} 💥"

                else:
                    show_text += f"🦕 Your dinosaurs inflicted: {damage} 💥"

            return show_text, 'user_move'

        return '', 'no_mobs'

    def battle_mob_move(bot, dungeonid, userid, bd_user, call = None):

        dung = dungeons.find_one({"dungeonid": dungeonid})
        room_n = str(dung['stage_data']['game']['room_n'])
        floor_n = dung['stage_data']['game']['floor_n']
        room = dung['floor'][room_n]

        if room['battle_type'] == 'mobs':
            mob = dung['floor'][room_n]['mobs'][0]
            data_mob = mobs_f['mobs'][ mob['mob_key'] ]
        else:
            mob = dung['floor'][room_n]['mobs']
            data_mob = mobs_f['boss'][ mob['mob_key'] ]

        log = []

        def mob_heal(standart = True, heal_dict = None): #могут использовать только маги
            successful = True

            if standart == True or heal_dict['type'] == 'standart':

                heal_col = random.randint(0, 3)
                mana_use = 15
                rg_type = 'simple_regeneration'

            else:
                if heal_dict['heal']['type'] == 'random':
                    heal_col = random.randint(heal_dict['heal']['min'], heal_dict['heal']['max'])
                else:
                    heal_col = heal_dict['heal']['act']

                if heal_dict['mana']['type'] == 'random':
                    mana_use = random.randint(heal_dict['mana']['min'], heal_dict['mana']['max'])
                else:
                    mana_use = heal_dict['mana']['act']

                rg_type = heal_dict['name']

            if rg_type == 'simple_regeneration':

                if mob['mana'] >= mana_use:
                    if mob['hp'] < mob['maxhp']:

                        mob['hp'] += heal_col
                        mob['mana'] -= mana_use

                else:
                    successful = False

            if mob['hp'] > mob['maxhp']:
                mob['hp'] = mob['maxhp']

            return heal_col, successful

        def mob_damage(standart = True, attack_dict = None):
            damage = 0
            successful = True

            if standart == True or attack_dict['type'] == 'standart':
                damag_d = random.randint( mob['damage'] // 2, mob['damage'] )
                mind = mob['damage'] // 2

                endur = random.randint(0,2)
                ammun = 1
                mana = random.randint(0,10)
                at_type = 'simple_attack'

            else:

                if attack_dict['damage']['type'] == 'random':
                    damag_d = random.randint( attack_dict['damage']['min'], attack_dict['damage']['max'] )
                    mind = attack_dict['damage']['max'] // 2
                else:
                    damag_d = attack_dict['damage']['act']
                    mind  = attack_dict['damage']['act'] // 2

                if "endurance" in attack_dict.keys():
                    if attack_dict["endurance"]['type'] == 'random':
                        endur = random.randint( attack_dict['endurance']['min'], attack_dict['endurance']['max'] )
                    else:
                        endur = attack_dict['endurance']['act']

                if "ammunition" in attack_dict.keys():
                    if attack_dict["ammunition"]['type'] == 'random':
                        ammun = random.randint( attack_dict['ammunition']['min'], attack_dict['ammunition']['max'] )
                    else:
                        ammun = attack_dict['ammunition']['act']

                if "mana" in attack_dict.keys():
                    if attack_dict["mana"]['type'] == 'random':
                        mana = random.randint( attack_dict['mana']['min'], attack_dict['mana']['max'] )
                    else:
                        mana = attack_dict['mana']['act']

                at_type = attack_dict['name']

            if at_type == 'simple_attack':

                if data_mob["damage-type"] == "near":
                    if mob['endurance'] > 0:
                        mob['endurance'] -= endur
                        damage = damag_d

                    else:
                        damage = random.randint(0, mind )
                        successful = False

                elif data_mob["damage-type"] == "far":
                    if mob['ammunition'] > 0:
                        mob['ammunition'] -= ammun
                        damage = damag_d

                    else:
                        damage = random.randint(0, mind )
                        successful = False

                elif data_mob["damage-type"] == "magic":
                    if mob['mana'] > 0:
                        mob['mana'] -= mana
                        damage = damag_d

                    else:
                        damage = random.randint(0, mind )
                        successful = False

            return damage, successful


        if mob['hp'] <= 0:

            if room['battle_type'] == 'mobs':
                dung['floor'][room_n]['mobs'].pop(0)

            else:
                dung['floor'][room_n]['mobs'] = []

            if len(dung['floor'][room_n]['mobs']) == 0:
                dung['floor'][room_n]['next_room'] = True

            loot = dung['floor'][room_n]['reward']['items']
            exp = dung['floor'][room_n]['reward']['experience']
            coins = dung['floor'][room_n]['reward']['coins']

            if data_mob["experience"]['type'] == 'random':
                exp += random.randint( data_mob["experience"]['min'], data_mob["experience"]['max'] )
            else:
                exp += data_mob["experience"]['act']

            if data_mob["coins"]['type'] == 'random':
                coins += random.randint( data_mob["coins"]['min'], data_mob["coins"]['max'] )
            else:
                coins += data_mob["coins"]['act']

            if room['battle_type'] == 'mobs':
                n_l = Dungeon.loot_generator( mob['mob_key'], 'mobs' )
            else:
                n_l = Dungeon.loot_generator( mob['mob_key'], 'boss' )

            for i in n_l: loot.append(i)

            dung['floor'][room_n]['reward']['items'] = loot
            dung['floor'][room_n]['reward']['experience'] = exp
            dung['floor'][room_n]['reward']['coins'] = coins

            dungeons.update_one( {"dungeonid": dungeonid}, {"$set": {f'floor': dung['floor'] }} )
            dungeons.update_one( {"dungeonid": dungeonid}, {"$inc": {f'stage_data.game.floors_stat.{floor_n}.mobs_killing': 1 }} )

            if dung['settings']['lang'] == 'ru':
                log.append( f"💥 {data_mob['name'][dung['settings']['lang']]} умер." )
            else:
                log.append( f"💥 {data_mob['name'][dung['settings']['lang']]} dead." )

            inf = Dungeon.message_upd(bot, userid = userid, dungeonid = dungeonid, upd_type = 'all', image_update = True)

            bd_user = users.find_one({"userid": int(userid)})
            Dungeon.check_quest(bot, bd_user, met = 'check', quests_type = 'kill', kwargs = {'mob': mob['mob_key']} )

            return log, 'mob_move'

        else:
            dinos_keys_pr = list(dung['users'][str(userid)]['dinos'].keys())
            act_log = []
            damage_count = 1

            if len(dinos_keys_pr) == 0:
                damage_count = 0

            if len(dinos_keys_pr) > 1:
                damage_count = random.randint(int(len(dinos_keys_pr) / 2), len(dinos_keys_pr))

            if mob['intelligence'] < 10:

                for i in range(damage_count):
                    random.shuffle(dinos_keys_pr)
                    damage, successful = mob_damage()

                    act_log.append( {'type': 'damage_dino', 'dino_key': dinos_keys_pr[0], 'damage': damage, 'successful': successful} )

            if mob['intelligence'] >= 10 and mob['intelligence'] < 20:

                if data_mob["damage-type"] == "magic":
                    act_l = ["attacks", "healing"] #, "other"] доделать еффекты
                else:
                    act_l = ["attacks"] #, "other"] доделать еффекты

                a = 0
                for i in range(damage_count):
                    random.shuffle(dinos_keys_pr)
                    mob_action = random.choice(act_l)

                    if mob_action == "attacks":
                        damage, successful = mob_damage( False, random.choice(data_mob['actions'][mob_action]) )

                        act_log.append( {'type': 'damage_dino', 'dino_key': dinos_keys_pr[0], 'damage': damage, 'successful': successful} )

                    elif mob_action == "healing":
                        hp, successful = mob_heal( False, random.choice(data_mob['actions'][mob_action]) )

                        act_log.append( {'type': 'mob_heal', 'heal': hp, 'successful': successful} )

            if mob['intelligence'] >= 20 and mob['intelligence'] < 30:

                pass
                # моб выбирает что ему сделать из действий, но само действие рандомное (actions - выбирает, random( mob[actions][?] ) )

            if mob['intelligence'] >= 30 and mob['intelligence'] < 40:

                pass
                # моб выбирает что ему сделать, как и при 30-ти + выбирает цель на основе косвенных данных (у кого меньше хп и тд)

            if mob['intelligence'] >= 40 and mob['intelligence'] < 50:

                pass
                # моб выбирает что ему сделать, как и при 40-ти + выбирает цель на основе всех данных

            dungeons.update_one( {"dungeonid": dungeonid}, {"$set": {f'floor.{room_n}.mobs':  dung['floor'][room_n]['mobs'] }} )

            for log_d in act_log:

                if log_d['type'] == 'mob_heal':

                    if log_d['successful'] == True:

                        if dung['settings']['lang'] == 'ru':
                            log.append( f"⬆ {data_mob['name'][ dung['settings']['lang'] ]} восстанавливает себе {log_d['heal']} ❤" )
                        else:
                            log.append( f"⬆ {data_mob['name'][ dung['settings']['lang'] ]} restores itself {log_d['heal']} ❤" )

                    else:

                        if dung['settings']['lang'] == 'ru':
                            log.append( f"❌ У {data_mob['name'][ dung['settings']['lang'] ]} не хватает маны на восстановление здоровья..." )
                        else:
                            log.append( f"❌{data_mob['name'][dung['settings']['lang']]} doesn't have enough mana to restore health..." )

                elif log_d['type'] == 'damage_dino':

                    if bd_user['dinos'][ log_d['dino_key'] ]['dungeon']['equipment']['armor'] == None:
                        reflection = 1 # 1 урон будет отражен

                    else:
                        arm_id = bd_user['dinos'][ log_d['dino_key'] ]['dungeon']['equipment']['armor']['item_id']

                        reflection = items_f['items'][arm_id]['reflection']

                    if 'action' in dung['users'][str(userid)]['dinos'][ log_d['dino_key'] ].keys() and dung['users'][str(userid)]['dinos'][ log_d['dino_key'] ]['action'] == 'defend':
                        use_armor = True

                    else:
                        use_armor = False

                    if dung['settings']['lang'] == 'ru':
                        if log_d['successful'] == True:

                            log.append(f"💢 {data_mob['name'][dung['settings']['lang']]} наносит {bd_user['dinos'][ log_d['dino_key'] ]['name']} {damage} урон(а).")

                        else:

                            if data_mob["damage-type"] == "magic":

                                log.append(f"💢 У {data_mob['name'][dung['settings']['lang']]} не хватает маны, атаки ослабли, {bd_user['dinos'][ log_d['dino_key'] ]['name']} получает {damage} урон(а).")

                            elif data_mob["damage-type"] == "near":

                                log.append(f"💢 У {data_mob['name'][dung['settings']['lang']]} сломалось оружие, атаки ослабли, {bd_user['dinos'][ log_d['dino_key'] ]['name']} получает {damage} урон(а).")

                            elif data_mob["damage-type"] == "far":

                                log.append(f"💢 У {data_mob['name'][dung['settings']['lang']]} не хватает боеприпасов, атаки ослабли, {bd_user['dinos'][ log_d['dino_key'] ]['name']} получает {damage} урона.")


                    else:
                        if log_d['successful'] == True:

                            log.append(f"💢 {data_mob['name'][dung['settings']['lang']]} causes {bd_user['dinos'][ log_d['dino_key'] ]['name']} {damage} damage.")

                        else:

                            if data_mob["damage-type"] == "magic":

                                log.append(f"💢 At {data_mob['name'][dung['settings']['lang']]} not enough mana, attacks weakened, {bd_user['dinos'][ log_d['dino_key'] ]['name']} receives {damage} damage.")

                            elif data_mob["damage-type"] == "near":

                                log.append(f"💢 At {data_mob['name'][dung['settings']['lang']]} the weapon broke, attacks weakened, {bd_user['dinos'][ log_d['dino_key'] ]['name']} receives {damage} damage.")

                            elif data_mob["damage-type"] == "far":

                                log.append(f"💢 At {data_mob['name'][dung['settings']['lang']]} not enough ammunition, attacks weakened, {bd_user['dinos'][ log_d['dino_key'] ]['name']} receives {damage} damage.")

                    if use_armor == True:

                        if dung['settings']['lang'] == 'ru':

                            log.append( f"🛡 {bd_user['dinos'][ log_d['dino_key'] ]['name']} отражает {reflection} урон(а)." )

                        else:

                            log.append( f"🛡 {bd_user['dinos'][ log_d['dino_key'] ]['name']} reflects {reflection} damage." )

                    dmg = damage
                    if use_armor == True:
                        dmg -= reflection

                        # item = bd_user['dinos'][ log_d['dino_key'] ]['dungeon']['equipment']['weapon']
                        # item['abilities']['endurance'] -= random.randint(0,2)

                    if dmg < 1:
                        dmg = 0

                    if bd_user['dinos'][ log_d['dino_key'] ]['stats']['heal'] - dmg <= 10:
                        bd_user['dinos'][ log_d['dino_key'] ]['stats']['heal'] = 10
                        del dung['users'][ str(userid) ]['dinos'][ log_d['dino_key'] ]

                        dungeons.update_one( {"dungeonid": dungeonid}, {"$set": {f'users': dung['users'] }} )

                        if dung['settings']['lang'] == 'ru':

                            log.append( f"🦕 У {bd_user['dinos'][ log_d['dino_key'] ]['name']} остаётся 10 ❤, он покидает подземелье в целях безопасности." )

                        else:

                            log.append( f"🦕 At {bd_user['dinos'][ log_d['dino_key'] ]['name']} remains 10 ❤, he leaves the dungeon for safety reasons." )

                        if userid == dung['dungeonid'] and len(dung['users'][ str(userid) ]['dinos']) == 0:

                            for uk in dung['users'].keys():
                                Dungeon.user_dungeon_stat(int(uk), dungeonid)

                                inf = Dungeon.message_upd(bot, dungeonid = int(uk ), type = 'delete_dungeon')

                            kwargs = { 'save_inv': False }
                            dng, inf = Dungeon.base_upd(dungeonid = userid, type = 'delete_dungeon', kwargs = kwargs)

                    else:
                        bd_user['dinos'][ log_d['dino_key'] ]['stats']['heal'] -= dmg

                        if dung['settings']['lang'] == 'ru':

                            log.append( f"🦕 У {bd_user['dinos'][ log_d['dino_key'] ]['name']} остаётся {bd_user['dinos'][ log_d['dino_key'] ]['stats']['heal']} ❤" )

                        else:

                            log.append( f"🦕 At {bd_user['dinos'][ log_d['dino_key'] ]['name']} remains {bd_user['dinos'][ log_d['dino_key'] ]['stats']['heal']} ❤" )

                    users.update_one( {"userid": bd_user['userid']}, {"$set": {'dinos': bd_user['dinos'] }} )

            return log, 'mob_move'

    def loot_generator(mob_key, mt):
        """ Доки функции

        Шанс берётся из моба, рандомится от 1-го до 1к, и проверяется число из лута, если x (item['chance']) >= ra.int - значит выпал"""
        loot = []

        data_mob = mobs_f[mt][ mob_key ]

        for i_d in data_mob['loot']:
            for _ in range(i_d['col']):
                if random.randint(1, 1000) <= i_d['chance']:

                    if 'preabil' not in i_d.keys():
                        preabil = None
                    else:
                        preabil = i_d['preabil']

                    loot.append( Functions.get_dict_item( i_d['item'], preabil ) )

        return loot

    def dino_attack(bd_user, dino_id, dungeonid):

        dung = dungeons.find_one({"dungeonid": dungeonid})

        data_items = items_f['items']
        item = bd_user['dinos'][dino_id]['dungeon']['equipment']['weapon']
        data_item = data_items[ item['item_id'] ]
        log = ''
        user_inv_dg = dung['users'][ str(bd_user['userid']) ]['inventory'].copy()
        upd_items = False
        upd_inv = False

        damage = random.randint( data_item['damage']['min'], data_item['damage']['max'] )

        if data_item['class'] == 'near':

            item['abilities']['endurance'] -= random.randint(0,2)
            upd_items = True

        if data_item['class'] == 'far':

            user_inv_id = []
            for i in user_inv_dg: user_inv_id.append( i['item_id'] )
            am_itemid_list = data_item['ammunition']
            sv_lst = list(set(am_itemid_list) & set(user_inv_id))

            if sv_lst != []:

                amm_id_item = sv_lst[0]
                itm_ind = am_itemid_list.index(amm_id_item)
                itm = user_inv_dg[ itm_ind ]
                itm['abilities']['stack'] -= 1
                upd_inv = True

                damage += data_items[ str(amm_id_item) ]['add_damage']

                if itm['abilities']['stack'] <= 0:
                    user_inv_dg.pop(itm_ind)
                else:
                    user_inv_dg[ itm_ind ] = itm

                if random.randint(1, 100) > 60:

                    item['abilities']['endurance'] -= random.randint(1,2)
                    upd_items = True
            else:
                damage = 0

                if dung['settings']['lang'] == 'ru':
                    log += '💢 В инвентаре нет боеприпасов для этого оружия!\n'
                else:
                    log += '💢 There is no ammunition for this weapon in the inventory!\n'

        if item['abilities']['endurance'] <= 0:
            bd_user['dinos'][dino_id]['dungeon']['equipment']['weapon'] = None
            upd_items = True

            if dung['settings']['lang'] == 'ru':
                log += '💢 Ваше оружие сломалось!\n'
            else:
                log += '💢 Your weapon is broken!\n'

        if upd_items == True:
            users.update_one( {"userid": bd_user['userid']}, {"$set": {f'dinos.{dino_id}': bd_user['dinos'][dino_id] }} )

        if upd_inv == True:
            dungeons.update_one( {"dungeonid": dungeonid}, {"$set": {f'users.{bd_user["userid"]}.inventory': user_inv_dg }} )

        return damage, log

    def user_dungeon_stat(user_id:int, dungeonid):

        dung = dungeons.find_one({"dungeonid": dungeonid})
        user_stat = {
                'time': int(time.time()) - int(dung['stage_data']['game']['start_time']),
                'end_floor': dung['stage_data']['game']['floor_n'] + 1,
                'start_floor': dung['settings']['start_floor'],
                    }

        users.update_one( {"userid": user_id }, {"$push": {'user_dungeon.statistics': user_stat }} )

        return True

    def floor_data(floor_n):
        floors_data = floors_f["floors"]

        if str(floor_n) not in floors_data.keys():

            while floor_n != 1:

                if str(floor_n) not in floors_data.keys():
                    floor_n -= 1

                else:
                    return floors_data[str(floor_n)]

            else:
                return floors_data['1']

        else:
            return floors_data[str(floor_n)]

    def panel_message(bot, dung, type, image_update):

        dungeonid = dung['dungeonid']
        room_n = dung['stage_data']['game']['room_n']
        floor_n = dung['stage_data']['game']['floor_n']
        image = dung['floor'][str(room_n)]['image']
        room = dung['floor'][str(room_n)]
        room_type = dung['floor'][str(room_n)]['room_type']
        inline_type = 'game'

        if dung['settings']['lang'] == 'ru':
            text = f"🕹 | Комната: #{room_n} | Время: {Functions.time_end(int( time.time()) - dung['stage_data']['game']['start_time']) }"

        else:
            text = f'🕹 | Room: #{room_n} | Time: {Functions.time_end(int( time.time()) - dung["stage_data"]["game"]["start_time"], True) }'

        if room_type == 'battle':
            if room['battle_type'] == 'boss':
                if dung['floor'][str(room_n)]['next_room'] == False:

                    inline_type = 'battle'
                    boss = dung['floor'][str(room_n)]['mobs']

                    data_mob = mobs_f['boss'][ boss['mob_key'] ]
                    inline_type = 'battle'

                    if dung['settings']['lang'] == 'ru':
                        text += (
                        f"\n\n⚔ | Сражение с боссом"
                        f"\n\n😈 | {data_mob['name'][dung['settings']['lang']]}"
                        f"\n❤ | Здоровье: {boss['hp']} / {boss['maxhp']} ({ round( (boss['hp'] / boss['maxhp']) * 100, 2)}%)"
                        )

                    else:
                        text += (
                        f"\n\n⚔ | Boss battle: \n"
                        f"\n\n😈 | {data_mob['name'][dung['settings']['lang']]}"
                        f"\n❤ | Health: {boss['hp']} / {boss['maxhp']} ({ round( (boss['hp'] / boss['maxhp']) * 100, 2)}%)"
                        )

                    if data_mob['damage-type'] == 'magic':

                        if dung['settings']['lang'] == 'ru':
                            text +=  f"\n🌌 | Мана: {boss['mana']} / {boss['maxmana']} ({ round( (boss['mana'] / boss['maxmana']) * 100, 2)}%)"

                        else:
                            text +=  f"\n🌌 | Mana: {boss['mana']} / {boss['maxmana']} ({ round( (boss['mana'] / boss['maxmana']) * 100, 2)}%)"


                    u_n = 0
                    users_text = '\n\n'
                    pl_move = dung['stage_data']['game']['player_move'][0]
                    for k in dung['users'].keys():

                        if k == pl_move:
                            r_e = ' ⬅'

                        else:
                            r_e = ' ⛔'

                        u_n += 1
                        username = bot.get_chat(int(k)).first_name
                        users_text += f'{u_n}. {username} {r_e}\n'

                    if dung['settings']['lang'] == 'ru':
                        move_text = f'\n🛡⚔ | {bot.get_chat(int( pl_move )).first_name}, выберите действие для динозавров, а после завершите ход! Если вы хотите пропустить ход, просто не выбирайте действия.'
                    else:
                        move_text = f"\n🛡⚔ | {bot.get_chat(int( pl_move )).first_name} choose an action for the dinosaurs, and then complete the move! If you want to skip a move, just don't choose actions."

                    dino_text = '\n\n'

                    at_action = 0
                    df_action = 0
                    nn_action = 0

                    for dn_id in dung['users'][ pl_move ]['dinos'].keys():
                        dn = dung['users'][ pl_move ]['dinos'][dn_id]

                        if 'action' not in dn.keys():
                            nn_action += 1

                        else:
                            if dn['action'] == 'attack':
                                at_action += 1

                            if dn['action'] == 'defend':
                                df_action += 1

                    if dung['settings']['lang'] == 'ru':
                        dino_text += f'🦕 | Действия: ⚔{at_action} 🛡{df_action} ❌{nn_action}'
                    else:
                        dino_text += f'🦕 | Actions: ⚔{at_action} 🛡{df_action} ❌{nn_action}'

                    text += users_text
                    text += move_text
                    text += dino_text

                    if image_update == True:
                        ok = Dungeon.generate_boss_image(image, boss, dungeonid)

                        image = f'boss {dungeonid}.png'

                if dung['floor'][str(room_n)]['next_room'] == True:
                    inline_type = 'battle'

                    if dung['settings']['lang'] == 'ru':
                        text += f'\n\n🏆 Вы победили босса этажа #{floor_n}! Подземелье трепещет от ваших достижений, заберите награду и продолжайте покорение!'

                    else:
                        text += f'\n\n🏆 You have defeated the floor boss #{floor_n}! The dungeon is trembling with your achievements, collect the reward and continue the conquest!'

                    text += '\n\n'
                    u_n = 0
                    users_text = ''
                    for k in dung['users'].keys():
                        us = dung['users'][k]
                        bd_us = users.find_one({"userid": int(k)})

                        if int(k) in dung['floor'][str(room_n)]['ready']:
                            r_e = '✅'

                        else:
                            r_e = '❌'

                        u_n += 1
                        username = bot.get_chat(int(k)).first_name
                        users_text += f'{u_n}. {username} (🦕 {len(us["dinos"])}) ({r_e})\n'

                    text += users_text

            if room['battle_type'] == 'mobs':
                if dung['floor'][str(room_n)]['next_room'] == False:
                    mob = dung['floor'][str(room_n)]['mobs'][0]
                    data_mob = mobs_f['mobs'][ mob['mob_key'] ]
                    inline_type = 'battle'

                    if dung['settings']['lang'] == 'ru':
                        text += (
                        f"\n\n⚔ | Схватка: \n"
                        f"        └ Врагов: {len(dung['floor'][str(room_n)]['mobs'])}"
                        f"\n\n😈 | Текущий враг: {data_mob['name'][dung['settings']['lang']]}"
                        f"\n❤ | Здоровье: {mob['hp']} / {mob['maxhp']} ({ round( (mob['hp'] / mob['maxhp']) * 100, 2)}%)"
                        )

                    else:
                        text += (
                        f"\n\n⚔ | The fight: \n"
                        f"        └ Enemies: {len(dung['floor'][str(room_n)]['mobs'])}"
                        f"\n\n😈 | Current enemy: {data_mob['name'][dung['settings']['lang']]}"
                        f"\n❤ | Health: {mob['hp']} / {mob['maxhp']} ({ round( (mob['hp'] / mob['maxhp']) * 100, 2)}%)"
                        )

                    if data_mob['damage-type'] == 'magic':

                        if dung['settings']['lang'] == 'ru':
                            text +=  f"\n🌌 | Мана: {mob['mana']} / {mob['maxmana']} ({ round( (mob['mana'] / mob['maxmana']) * 100, 2)}%)"

                        else:
                            text +=  f"\n🌌 | Mana: {mob['mana']} / {mob['maxmana']} ({ round( (mob['mana'] / mob['maxmana']) * 100, 2)}%)"


                    u_n = 0
                    users_text = '\n\n'
                    pl_move = dung['stage_data']['game']['player_move'][0]
                    for k in dung['users'].keys():

                        if k == pl_move:
                            r_e = ' ⬅'

                        else:
                            r_e = ' ⛔'

                        u_n += 1
                        username = bot.get_chat(int(k)).first_name
                        users_text += f'{u_n}. {username} {r_e}\n'

                    if dung['settings']['lang'] == 'ru':
                        move_text = f'\n🛡⚔ | {bot.get_chat(int( pl_move )).first_name}, выберите действие для динозавров, а после завершите ход! Если вы хотите пропустить ход, просто не выбирайте действия.'
                    else:
                        move_text = f"\n🛡⚔ | {bot.get_chat(int( pl_move )).first_name} choose an action for the dinosaurs, and then complete the move! If you want to skip a move, just don't choose actions."

                    dino_text = '\n\n'

                    at_action = 0
                    df_action = 0
                    nn_action = 0

                    for dn_id in dung['users'][ pl_move ]['dinos'].keys():
                        dn = dung['users'][ pl_move ]['dinos'][dn_id]

                        if 'action' not in dn.keys():
                            nn_action += 1

                        else:
                            if dn['action'] == 'attack':
                                at_action += 1

                            if dn['action'] == 'defend':
                                df_action += 1

                    if dung['settings']['lang'] == 'ru':
                        dino_text += f'🦕 | Действия: ⚔{at_action} 🛡{df_action} ❌{nn_action}'
                    else:
                        dino_text += f'🦕 | Actions: ⚔{at_action} 🛡{df_action} ❌{nn_action}'

                    text += users_text
                    text += move_text
                    text += dino_text

                    if image_update == True:
                        ok = Dungeon.generate_battle_image(image, mob, dungeonid)

                        image = f'{config.TEMP_DIRECTION}/battle {dungeonid}.png'

                if dung['floor'][str(room_n)]['next_room'] == True:
                    inline_type = 'battle'

                    if dung['settings']['lang'] == 'ru':
                        text += f'\n\n🏆 Вы одолели всех монстров в этой локации, забери свою награду и продвигайтесь дальше!'

                    else:
                        text += f'\n\n🏆 You have defeated all the monsters in this location, take your reward and move on!'

                    text += '\n\n'
                    u_n = 0
                    users_text = ''
                    for k in dung['users'].keys():
                        us = dung['users'][k]
                        bd_us = users.find_one({"userid": int(k)})

                        if int(k) in dung['floor'][str(room_n)]['ready']:
                            r_e = '✅'

                        else:
                            r_e = '❌'

                        u_n += 1
                        username = bot.get_chat(int(k)).first_name
                        users_text += f'{u_n}. {username} (🦕 {len(us["dinos"])}) ({r_e})\n'

                    text += users_text

        elif room_type == 'empty_room':

            if dung['settings']['lang'] == 'ru':
                text += f"\n\nПохоже это просто пустая комната. Тут немного темно, но ничего интересного вы не видите."

            else:
                text += f"\n\nIt looks like it's just an empty room. It's a little dark here, but you don't see anything interesting."

            if dung['floor'][str(room_n)]['next_room'] == True:

                text += '\n\n'
                u_n = 0
                users_text = ''
                for k in dung['users'].keys():
                    us = dung['users'][k]
                    bd_us = users.find_one({"userid": int(k)})

                    if int(k) in dung['floor'][str(room_n)]['ready']:
                        r_e = '✅'

                    else:
                        r_e = '❌'

                    u_n += 1
                    username = bot.get_chat(int(k)).first_name
                    users_text += f'{u_n}. {username} (🦕 {len(us["dinos"])}) ({r_e})\n'

                text += users_text

        elif room_type == 'safe_exit':
            inline_type = 'safe_exit'

            if dung['settings']['lang'] == 'ru':
                text += f"\n\n✨ | Поздравляем, вы прошли достаточно тяжёлый путь, перед вами стоит выбор, выйти из подземелья или продолжить путь..."

            else:
                text += f"\n\n✨ | Congratulations, you have passed a rather difficult path, you have a choice before you, to leave the dungeon or continue on your way..."

            if dung['floor'][str(room_n)]['next_room'] == True:

                text += '\n\n'
                u_n = 0
                users_text = ''
                for k in dung['users'].keys():
                    us = dung['users'][k]
                    bd_us = users.find_one({"userid": int(k)})

                    if int(k) in dung['floor'][str(room_n)]['ready']:
                        r_e = '✅'

                    else:
                        r_e = '❌'

                    u_n += 1
                    username = bot.get_chat(int(k)).first_name
                    users_text += f'{u_n}. {username} (🦕 {len(us["dinos"])}) ({r_e})\n'

                text += users_text

        elif room_type in ['fork_2', 'fork_3']:

            poll_rooms = dung['floor'][str(room_n)]['poll_rooms']
            olr = {}
            t_l = []

            for r in poll_rooms:
                if r in olr.keys():
                    olr[r] += 1
                else:
                    olr[r] = 1

            r_n = { 'battle': [ 'Бой', 'Battle' ],
                    "empty_room": [ 'Пустая комната', 'Empty room' ],
                    "fork_2": [ 'Развилка', 'Fork' ],
                    "fork_3": [ 'Развилка', 'Fork' ],
                    "mine": [ 'Комната с ресурсами', 'Room with resources' ],
                    "town": [ 'Город', 'Town' ]
            }

            for i in olr.keys():

                if dung['settings']['lang'] == 'ru':
                    t_l.append( f'{ r_n[ i ][0] } x{olr[i]}' )
                else:
                    t_l.append( f'{ r_n[ i ][1] } x{olr[i]}' )

            random.shuffle(t_l)


            if dung['settings']['lang'] == 'ru':
                text += f"\n\n🧩 | Перед вами находится несколько проходов, выберите общим голосованием куда вы направитесь!\n"
                text += f'🧭 | Возможные комнаты: {", ".join(t_l)}'
                text += "\n\n*🎏 | Выберите*\n"

            else:
                text += f'\n\n🧩 | There are several passageways in front of you, choose by general vote where you will go!\n'
                text += f'🧭 | Possible rooms: {", ".join(t_l)}'
                text += '\n\n*🎏 | Select*\n'

            results = dung['floor'][str(room_n)]['results']
            inline_type = room_type

            rs_all = 0
            for l in results: rs_all += len(l)

            if rs_all == 0:
                rs_all = 1

            rs_n = 0
            for rs in results:
                rs_n += 1

                pr = int(round( (len(rs) / rs_all * 100), 0))

                if pr <= 10: bar = '▫'

                if pr > 10 and pr <= 25:  bar = '▫◽'

                if pr > 25 and pr <= 50:  bar = '▫◽⬜'

                if pr > 50 and pr <= 75: bar = '▫◽⬜⬛'

                if pr > 75 and pr < 100: bar = '▫◽⬜⬛⬜'

                if pr >= 100: bar = '▫◽⬜⬛⬜⬛'

                text += f'{rs_n}# {bar} ({ pr }%)\n'

        elif room_type == 'mine':
            inline_type = 'mine'

            if dung['settings']['lang'] == 'ru':
                text += f"\n\n💎 | В этой комнате всё так блестит и светится!\nСоберите все эти блестяшки!\n\n"

            else:
                text += f'\n\n💎 | Everything in this room is so shiny and glowing!\nCollect all these sparkles!\n\n'

            u_n = 0
            users_text = ''
            for k in dung['users'].keys():
                us = dung['users'][k]
                bd_us = users.find_one({"userid": int(k)})

                if int(k) in dung['floor'][str(room_n)]['ready']:
                    r_e = '✅'

                else:
                    r_e = '❌'

                u_n += 1
                username = bot.get_chat(int(k)).first_name
                users_text += f'{u_n}. {username} (🦕 {len(us["dinos"])}) ({r_e})\n'

            text += users_text

        elif room_type == 'town':
            inline_type = 'town'

            if dung['settings']['lang'] == 'ru':
                text += f"\n\n🗼 | Вы вошли в подземный город! Пройдитесь по городу и приготовьтесь к дальнейшим путешествиям!\n\n"

            else:
                text += f'\n\n🗼 | You have entered the underground city! Take a walk around the city and get ready for further travels!\n\n'

            u_n = 0
            users_text = ''
            for k in dung['users'].keys():
                us = dung['users'][k]
                bd_us = users.find_one({"userid": int(k)})

                if int(k) in dung['floor'][str(room_n)]['ready']:
                    r_e = '✅'

                else:
                    r_e = '❌'

                u_n += 1
                username = bot.get_chat(int(k)).first_name
                users_text += f'{u_n}. {username} (🦕 {len(us["dinos"])}) ({r_e})\n'

            text += users_text

        elif room_type == 'start_room':

            if dung['settings']['lang'] == 'ru':
                text += f"\n\nВы спустились на этаж #{floor_n}, подготовьтесь к испытаниям и продолжайте ваш путь!"
                text += '\n\n   *👥 | Игроки*\n'

            else:
                text += f'\n\n You have descended to the floor #{floor_n}, prepare for the tests and continue your journey!'
                text += '\n\n   *👥 | Players*\n'

            u_n = 0
            users_text = ''
            for k in dung['users'].keys():
                us = dung['users'][k]
                bd_us = users.find_one({"userid": int(k)})

                if int(k) in dung['floor'][str(room_n)]['ready']:
                    r_e = '✅'

                else:
                    r_e = '❌'

                u_n += 1
                username = bot.get_chat(int(k)).first_name
                users_text += f'{u_n}. {username} (🦕 {len(us["dinos"])}) ({r_e})\n'

            text += users_text

        return text, inline_type, image

    def create_quest(bd_user):

        def comp_r(complex):
            if str(complex) not in quests_f['complexity'].keys():

                while complex > 1:

                    if str(complex) not in quests_f['complexity'].keys():

                        if complex <= 0:
                            return quests_f['complexity']['1']

                        else:
                            complex -= 1

                    else:
                        return quests_f['complexity'][str(complex)]

                else:
                    return quests_f['complexity']['1']

            else:
                return quests_f['complexity'][str(complex)]

        types = ['get', 'do', 'kill', 'do', 'come', 'get', 'kill', 'do']
        random.shuffle(types)

        quest_type = random.choice(types)

        quest = {
        'reward': {'money': 0, 'items': []},
        'complexity': 0,
        'type': quest_type,
        'time': 0,
        'name': None
        }

        if quest_type == 'get':

            if bd_user['language_code'] == 'ru':
                names = ['Доставка припасов', 'Поиски припасов']

            else:
                names = ['Delivery of supplies', 'Search for supplies']

            quest['get_items'] = []
            qq = list(quests_f['quests']['get']['items'])
            random.shuffle(qq)

            col, n = random.randint(1, 3), 0
            t = time.time()

            while n != col:
                for i in qq:

                    if random.randint(1, 100) <= 50:
                        if n < col:
                            for _ in range(Functions.rand_d( i["col"] )):
                                if random.randint(1, 100) <= 50:
                                    if n < col:
                                        quest['get_items'].append(i['item'])
                                        quest['complexity'] += i["complexity"]
                                        n += 1

        if quest_type == 'kill':

            if bd_user['language_code'] == 'ru':
                names = ['Живым или мёртвым', 'Мертвецы не рассказывают сказки', 'Покорай монстров!']

            else:
                names = ['Alive or dead', "Dead men don't tell fairy tales", 'Conquer monsters!']

            col, n = random.randint(1, 3), 0

            mbs = list(mobs_f['mobs'].keys())
            random.shuffle(mbs)

            quest['mob'] = mbs[0]
            quest['col'] = [random.randint(1, 3), 0]

            quest['complexity'] += col * random.randint(1, 2)

        if quest_type == 'come':

            if bd_user['language_code'] == 'ru':
                names = ['Покоряй рекорды!', 'Покорение горизонта!', 'Там чудо ждёт тебя..']

            else:
                names = ['Conquer records!', 'Conquering the horizon!', "There's a miracle waiting for you.."]

            ns_res = None
            st = bd_user['user_dungeon']['statistics']

            for i in st:

                if ns_res == None:
                    ns_res = i

                else:
                    if i['end_floor'] >= ns_res['end_floor']:
                        ns_res = i

            if ns_res == None:
                quest['lvl'] = random.randint(1, 3)

            else:
                quest['lvl'] = ns_res["end_floor"] + random.randint(1, 3)

            quest['complexity'] += random.randint(2, 5)
            quest['reward']['money'] += quest['lvl'] * random.randint(20, 80)


        if quest_type == 'do':

            q_case = [ 'game', 'journey', 'hunting', 'fishing', 'collecting', 'feed' ]
            random.shuffle(q_case)

            dp_type = random.choice(q_case)
            quest['dp_type'] = dp_type

            if dp_type == 'game':
                # поиграть определённое время

                tl = [ [100, 1], [150, 1], [240, 1], [360, 3], [480, 5], [540, 10] ]
                game_time = random.choice(tl)

                quest['target'] = [game_time[0], 0]
                quest['complexity'] = game_time[1]

                if bd_user['language_code'] == 'ru':
                    names = ['Время игр!', "Пора пройти ту самую игру!", "Играть, играть, играть!"]

                else:
                    names = ['Game time!', "It's time to pass that very game!", "Play, play, play!"]

            if dp_type == 'journey':
                #сходить в путешествие несколько раз

                j_col = random.randint(3, 20)
                quest['target'] = [j_col, 0]

                if j_col < 5:
                    quest['complexity'] = 1

                elif j_col < 10:
                    quest['complexity'] = 2

                elif j_col < 15:
                    quest['complexity'] = 5

                elif j_col <= 20:
                    quest['complexity'] = 10

                if bd_user['language_code'] == 'ru':
                    names = ['Путешествия зовут...', "Долгая прогулка...", 'Там путешествия ждут нас...']

                else:
                    names = ['Travel is called...', 'A long walk...', 'There are journeys waiting for us...']

            if dp_type == 'hunting':
                #добыть в охоте Х предметов

                h_col = random.randint(10, 50)
                quest['target'] = [h_col, 0]

                if h_col < 5:
                    quest['complexity'] = 1

                elif h_col < 15:
                    quest['complexity'] = 2

                elif h_col < 25:
                    quest['complexity'] = 5

                elif h_col <= 50:
                    quest['complexity'] = 10

                if bd_user['language_code'] == 'ru':
                    names = ['Пора поохотится...', "Там есть тот, кого я съем!", "Мясоооо!"]

                else:
                    names = ["It's time to hunt...", "There's someone I'm going to eat!", "Meat!"]

            if dp_type == 'fishing':
                #наловить Х предметов

                f_col = random.randint(10, 50)
                quest['target'] = [f_col, 0]

                if f_col < 5:
                    quest['complexity'] = 1

                elif f_col < 15:
                    quest['complexity'] = 2

                elif f_col < 25:
                    quest['complexity'] = 5

                elif f_col <= 50:
                    quest['complexity'] = 10

                if bd_user['language_code'] == 'ru':
                    names = ['Ловись рыбка большая и маленькая...', "Рыбаааааааа!", "Карасики..."]

                else:
                    names = ['Catch a fish big and small...', "Fishaaaaaaaa!", "Crucians ..."]

            if dp_type == 'collecting':
                #собрать Х предметов

                c_col = random.randint(10, 50)
                quest['target'] = [c_col, 0]

                if c_col < 5:
                    quest['complexity'] = 1

                elif c_col < 15:
                    quest['complexity'] = 2

                elif c_col < 25:
                    quest['complexity'] = 5

                elif c_col <= 50:
                    quest['complexity'] = 10

                if bd_user['language_code'] == 'ru':
                    names = ["Бананааааа!", "Пора собрать ягодки...", "Ягодки, кустики - вкусненько"]

                else:
                    names = ["Bananaaaaaa!", "It's time to pick berries...", "Berries, bushes - delicious"]

            if dp_type == 'feed':
                #покормить определённой едой

                eat_col = random.randint(3, 15)

                if eat_col < 5:
                    quest['complexity'] = 2

                elif eat_col < 10:
                    quest['complexity'] = 5

                elif eat_col <= 15:
                    quest['complexity'] = 10

                eat_items = []
                quest['target'] = {}

                for i in items_f['items'].keys():

                    if items_f['items'][i]["type"] == '+eat' and items_f['items'][i]["class"] == 'ALL':
                        eat_items.append(i)

                        if 'rank' in items_f['items'][i].keys():

                            if items_f['items'][i]['rank'] == 'common':
                                quest['reward']['money'] += 10

                            if items_f['items'][i]['rank'] == 'uncommon':
                                quest['reward']['money'] += 20

                            if items_f['items'][i]['rank'] == 'rare':
                                quest['reward']['money'] += 80

                            if items_f['items'][i]['rank'] == 'mystical':
                                quest['reward']['money'] += 100

                            if items_f['items'][i]['rank'] == 'legendary':
                                quest['reward']['money'] += 200

                            if items_f['items'][i]['rank'] == 'mythical':
                                quest['reward']['money'] += 500

                        else:
                            quest['reward']['money'] += 10

                random.shuffle(eat_items)

                cl = 0
                while cl < eat_col:

                    random.shuffle(eat_items)
                    item = random.choice(eat_items)

                    if item not in quest['target'].keys():
                        quest['target'][item] = [1, 0]

                    else:
                        quest['target'][item][0] += 1

                    cl += 1

                if bd_user['language_code'] == 'ru':
                    names = ["Пора устроить динозавру вкусный ужин!", "Динозавр давно вкусно не ел...", "Хочется чего-то вкусненького..."]

                else:
                    names = ["It's time to arrange a delicious dinner for the dinosaur!", "The dinosaur has not eaten delicious for a long time...", "I want something delicious ..."]

        quest['name'] = random.choice(names)

        complex = quest['complexity']
        cmp_data = comp_r(complex)

        quest['reward']['money'] += Functions.rand_d(cmp_data['money'])
        quest['time'] = int(time.time()) + cmp_data['time']

        rew_items = cmp_data['items']
        random.shuffle(rew_items)

        if random.randint(1, 1000) <= cmp_data["item_chance"]:

            for i in rew_items:

                for _ in range( Functions.rand_d(i['col']) ):
                    if random.randint(1, 1000) <= i['chance']:
                        quest['reward']['items'].append(i['item'])

        ncor = True
        while ncor:
            quest['id'] = random.randint(0, 1000)
            ncor = False

            for i in bd_user['user_dungeon']['quests']['activ_quests']:

                if i['id'] == quest['id']:
                    ncor = True
                    break

        return quest

    def quest_reward(bd_user, quest):

        reward = quest['reward']

        if 'money' in reward.keys():
            bd_user['coins'] += reward['money']

        if 'items' in reward.keys() and reward['items'] != []:
            for i in reward['items']:
                bd_user['inventory'].append( Functions.get_dict_item(i) )

        users.update_one( {"userid": bd_user['userid']}, {"$set": {'inventory': bd_user['inventory'] }} )
        users.update_one( {"userid": bd_user['userid']}, {"$set": {'coins': bd_user['coins'] }} )


    def check_quest(bot, bd_user, met:str = 'check', quests_type:str = None, kwargs:dict = None):

        if 'user_dungeon' in bd_user.keys():
            if 'quests' in bd_user['user_dungeon'].keys():
                quests = bd_user['user_dungeon']['quests']['activ_quests']

                if met == 'user_active':
                    quest = kwargs['quest']

                    if quest in quests:
                        bd_user['user_dungeon']['quests']['activ_quests'].remove(quest)
                        q_completed = False

                        if quest['type'] == 'get':

                            all_ok = True

                            for i in quest['get_items']:
                                item = Functions.get_dict_item(i)

                                if item in bd_user['inventory']:
                                    bd_user['inventory'].remove(item)

                                else:
                                    all_ok = False
                                    break

                            if all_ok:

                                qdata = { 'name': quest['name'], 'quest': quest }
                                Functions.notifications_manager(bot, 'quest_completed', bd_user, arg = qdata)

                                users.update_one( {"userid": bd_user['userid']}, {"$set": {'inventory': bd_user['inventory'] }} )

                                bd_user['user_dungeon']['quests']['ended'] += 1
                                users.update_one( {"userid": bd_user['userid']}, {"$set": {'user_dungeon': bd_user['user_dungeon'] }} )

                                Dungeon.quest_reward(bd_user, quest)

                                q_completed = True


                        if quest['type'] == 'kill':

                            if quest['col'][1] >= quest['col'][0]:

                                qdata = { 'name': quest['name'], 'quest': quest }
                                Functions.notifications_manager(bot, 'quest_completed', bd_user, arg = qdata)

                                bd_user['user_dungeon']['quests']['ended'] += 1
                                users.update_one( {"userid": bd_user['userid']}, {"$set": {'user_dungeon': bd_user['user_dungeon'] }} )

                                Dungeon.quest_reward(bd_user, quest)

                                q_completed = True

                        if quest['type'] == 'do':
                            if quest['dp_type'] == 'feed':
                                glob_targ = [len(list(quest['target'].keys())), 0]

                                for i in quest['target'].keys():
                                    tg = quest['target'][i]

                                    if tg[0] == tg[1]:
                                        glob_targ[1] += 1

                                if glob_targ[0] == glob_targ[1]:

                                    qdata = { 'name': quest['name'], 'quest': quest }
                                    Functions.notifications_manager(bot, 'quest_completed', bd_user, arg = qdata)

                                    bd_user['user_dungeon']['quests']['ended'] += 1
                                    users.update_one( {"userid": bd_user['userid']}, {"$set": {'user_dungeon': bd_user['user_dungeon'] }} )

                                    Dungeon.quest_reward(bd_user, quest)
                                    q_completed = True


                            else:

                                if quest['target'][1] >= quest['target'][0]:

                                    qdata = { 'name': quest['name'], 'quest': quest }
                                    Functions.notifications_manager(bot, 'quest_completed', bd_user, arg = qdata)

                                    bd_user['user_dungeon']['quests']['ended'] += 1
                                    users.update_one( {"userid": bd_user['userid']}, {"$set": {'user_dungeon': bd_user['user_dungeon'] }} )

                                    Dungeon.quest_reward(bd_user, quest)
                                    q_completed = True

                        return q_completed, 'n_cmp'

                    else:
                        return False, 'n_quests'


                if met == 'check':
                    for quest in quests:
                        if quest['type'] == quests_type:

                            if quest['type'] == 'come': # может быть вызван тоько системой

                                if quest['lvl'] >= kwargs['lvl']:

                                    bd_user['user_dungeon']['quests']['activ_quests'].remove(quest)

                                    qdata = { 'name': quest['name'], 'quest': quest }
                                    Functions.notifications_manager(bot, 'quest_completed', bd_user, arg = qdata)

                                    bd_user['user_dungeon']['quests']['ended'] += 1
                                    users.update_one( {"userid": bd_user['userid']}, {"$set": {'user_dungeon': bd_user['user_dungeon'] }} )

                                    Dungeon.quest_reward(bd_user, quest)


                            if quest['type'] == 'kill':

                                if quest['mob'] == kwargs['mob']:

                                    if quest['col'][1] != quest['col'][0]:
                                        quest['col'][1] += 1

                                        users.update_one( {"userid": bd_user['userid']}, {"$set": {'user_dungeon': bd_user['user_dungeon'] }} )

                            if quest['type'] == 'do':
                                ok = True

                                if quest['dp_type'] == kwargs['dp_type']:

                                    if quest['dp_type'] == 'feed':

                                        if kwargs['item'] in quest['target'].keys():
                                            quest['target'][kwargs['item']][1] += kwargs['act']

                                            if quest['target'][kwargs['item']][1] > quest['target'][kwargs['item']][0]:
                                                quest['target'][kwargs['item']][1] = quest['target'][kwargs['item']][0]

                                        else:
                                            ok = False

                                    else:
                                        quest['target'][1] += kwargs['act']

                                        if quest['target'][1] > quest['target'][0]:
                                            quest['target'][1] = quest['target'][0]

                                    if ok:
                                        users.update_one( {"userid": bd_user['userid']}, {"$set": {'user_dungeon': bd_user['user_dungeon'] }} )