import telebot
from telebot import types
import pymongo
import sys
import random
import json
import time
from PIL import Image, ImageFont, ImageDraw, ImageOps, ImageSequence, ImageFilter

sys.path.append("..")
import config

client = pymongo.MongoClient(config.CLUSTER_TOKEN)
users = client.bot.users

with open('data/items.json', encoding='utf-8') as f:
    items_f = json.load(f)

with open('data/dino_data.json', encoding='utf-8') as f:
    json_f = json.load(f)

checks_data = {'memory': [0, time.time()], 'incub': [0, time.time()], 'notif': [0, time.time()], 'main': [0, time.time()], "us": 0}

class functions:
    json_f = json_f
    items_f = items_f
    checks_data = checks_data

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

    def markup(bot, element = 1, user = None):
        try:
            user = int(user)
        except:
            pass

        if type(user) == int:
            userid = user
        else:
            userid = user.id

        markup = types.ReplyKeyboardMarkup(resize_keyboard = True)
        bd_user = users.find_one({"userid": userid})

        if bd_user != None and len(bd_user['dinos']) == 0 and functions.inv_egg(bd_user) == False and bd_user['lvl'][0] < 5:

            if bd_user['language_code'] == 'ru':
                nl = "🧩 Проект: Возрождение"
            else:
                nl = '🧩 Project: Rebirth'

            markup.add(nl)
            return markup

        if bd_user != None and len(bd_user['dinos']) == 0 and functions.inv_egg(bd_user) == False and bd_user['lvl'][0] >= 5:

            if bd_user['language_code'] == 'ru':
                nl = '🎮 Инвентарь'
            else:
                nl = '🎮 Inventory'

            markup.add(nl)
            return markup

        if element == 1 and bd_user != None:

            if len(list(bd_user['dinos'])) == 1 and bd_user['dinos']['1']['status'] == 'incubation':

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

                else:
                    nl = ['🦖 Dinosaur', '🕹 Actions', '👁‍🗨 Profile', '🔧 Settings', '👥 Friends', '❗ FAQ']

                item1 = types.KeyboardButton(nl[0])
                item2 = types.KeyboardButton(nl[1])
                item3 = types.KeyboardButton(nl[2])
                item4 = types.KeyboardButton(nl[3])
                item5 = types.KeyboardButton(nl[4])

                if 'vis.faq' in bd_user['settings'].keys() and bd_user['settings']['vis.faq'] == False:
                    nl.remove('❗ FAQ')
                    markup.add(item1, item2, item3, item4, item5)

                else:
                    item6 = types.KeyboardButton(nl[5])
                    markup.add(item1, item2, item3, item4, item5, item6)

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

            markup = types.ReplyKeyboardMarkup(resize_keyboard = True, row_width = 2)

            if bd_user['language_code'] == 'ru':
                nl = ['❗ Уведомления', "👅 Язык", '💬 Переименовать', '⁉ Видимость FAQ', '↪ Назад']

            else:
                nl = ['❗ Notifications', "👅 Language", '💬 Rename', '⁉ Visibility FAQ', '↪ Back']

            item1 = types.KeyboardButton(nl[0])
            item2 = types.KeyboardButton(nl[1])
            item3 = types.KeyboardButton(nl[2])
            item4 = types.KeyboardButton(nl[3])
            item5 = types.KeyboardButton(nl[4])

            markup.add(item1, item2, item3, item4, item5)

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

            if bd_user['language_code'] == 'ru':
                nl = ['🎮 Развлечения', '🍣 Покормить', '↪ Назад']

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
                    item6 = types.KeyboardButton(nl[5])

                    markup.add(item0, item1, item2, item3, item4, item5, item6)

                else:

                    item1 = types.KeyboardButton(nl[0])
                    item2 = types.KeyboardButton(nl[1])
                    item3 = types.KeyboardButton(nl[2])
                    item4 = types.KeyboardButton(nl[3])
                    item5 = types.KeyboardButton(nl[4])
                    item6 = types.KeyboardButton(nl[5])

                    markup.add(item1, item2, item3, item4, item5, item6)

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
                    item6 = types.KeyboardButton(nl[5])

                    markup.add(item0, item1, item2, item3, item4, item5, item6)

                else:

                    item1 = types.KeyboardButton(nl[0])
                    item2 = types.KeyboardButton(nl[1])
                    item3 = types.KeyboardButton(nl[2])
                    item4 = types.KeyboardButton(nl[3])
                    item5 = types.KeyboardButton(nl[4])
                    item6 = types.KeyboardButton(nl[5])

                    markup.add(item1, item2, item3, item4, item5, item6)

        elif element == 'games' and bd_user != None:

            if bd_user['dinos'][ str(bd_user['settings']['dino_id']) ]['activ_status'] == 'game':
                markup = types.ReplyKeyboardMarkup(resize_keyboard = True, row_width = 1)

                if bd_user['language_code'] == 'ru':
                    nl = ['❌ Остановить игру', '↪ Назад']
                else:
                    nl = ['❌ Stop the game', '↪ Back']

                item1 = types.KeyboardButton(nl[0])
                item2 = types.KeyboardButton(nl[1])

                markup.add(item1, item2)

            else:
                markup = types.ReplyKeyboardMarkup(resize_keyboard = True, row_width = 2)

                if bd_user['language_code'] == 'ru':
                    nl = ['🎮 Консоль', '🪁 Змей', '🏓 Пинг-понг', '🏐 Мяч', '↩ Назад']
                else:
                    nl = ['🎮 Console', '🪁 Snake', '🏓 Ping Pong', '🏐 Ball', '↩ Back']

                item1 = types.KeyboardButton(nl[0])
                item2 = types.KeyboardButton(nl[1])
                item3 = types.KeyboardButton(nl[2])
                item4 = types.KeyboardButton(nl[3])
                item5 = types.KeyboardButton(nl[4])

                markup.add(item1, item2, item3, item4, item5)

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


        else:
            print(f'{element}\n{user}')

        return markup

    @staticmethod
    def time_end(seconds:int, mini = False):

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
    def dino_pre_answer(bot, message):
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
        user['dinos'][functions.user_dino_pn(user)] = {'dino_id': dino_id, "status": 'dino', 'activ_status': 'pass_active', 'name': dino['name'], 'stats':  {"heal": 100, "eat": random.randint(70, 100), 'game': random.randint(50, 100), 'mood': random.randint(7, 100), "unv": 100}, 'games': []}

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

                if notification == "5_min_incub":

                    if user['language_code'] == 'ru':
                        text = f'🥚 | {chat.first_name}, ваш динозавр вылупится через 5 минут!'
                    else:
                        text = f'🥚 | {chat.first_name}, your dinosaur will hatch in 5 minutes!'

                    try:
                        bot.send_message(user['userid'], text)
                    except:
                        pass

                elif notification == "incub":

                    if user['language_code'] == 'ru':
                        text = f'🦖 | {chat.first_name}, динозавр вылупился! 🎉'
                    else:
                        text = f'🦖 | {chat.first_name}, the dinosaur has hatched! 🎉'

                    try:
                        bot.send_message(user['userid'], text)
                    except:
                        pass

                elif notification == "need_eat":

                    if user['language_code'] == 'ru':
                        text = f'🍕 | {chat.first_name}, динозавр хочет кушать, его потребность в еде опустилась до {arg}%!'
                    else:
                        text = f'🍕 | {chat.first_name}, the dinosaur wants to eat, his need for food has dropped to {arg}%!'

                    try:
                        bot.send_message(user['userid'], text)
                    except:
                        pass

                elif notification == "need_game":

                    if user['language_code'] == 'ru':
                        text = f'🎮 | {chat.first_name}, динозавр хочет играть, его потребность в игре опустилось до {arg}%!'
                    else:
                        text = f'🎮 | {chat.first_name}, The dinosaur wants to play, his need for the game has dropped to {arg}%!'

                    try:
                        bot.send_message(user['userid'], text)
                    except:
                        pass

                elif notification == "need_mood":

                    if user['language_code'] == 'ru':
                        text = f'🦖 | {chat.first_name}, у динозавра плохое настроение, его настроение опустилось до {arg}%!'
                    else:
                        text = f'🦖 | {chat.first_name}, the dinosaur is in a bad mood, his mood has sunk to {arg}%!'

                    try:
                        bot.send_message(user['userid'], text)
                    except:
                        pass

                elif notification == "need_unv":

                    if user['language_code'] == 'ru':
                        text = f'🌙 | {chat.first_name}, динозавр хочет спать, его харрактеристика сна опустилось до {arg}%!'
                    else:
                        text = f'🌙 | {chat.first_name}, the dinosaur wants to sleep, his sleep characteristic dropped to {arg}%!'

                    try:
                        bot.send_message(user['userid'], text)
                    except:
                        pass

                elif notification == "dead":

                    if user['language_code'] == 'ru':
                        text = f'💥 | {chat.first_name}, ваш динозаврик.... Умер...'
                        nl = "🧩 Проект: Возрождение"
                        nl2 = '🎮 Инвентарь'
                    else:
                        text = f'💥 | {chat.first_name}, your dinosaur.... Died...'
                        nl = '🧩 Project: Rebirth'
                        nl2 = '🎮 Inventory'

                    if functions.inv_egg(user) == False:
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

                elif notification == "woke_up":

                    if user['language_code'] == 'ru':
                        text = f'🌙 | {chat.first_name}, ваш динозавр проснулся и полон сил!'
                    else:
                        text = f'🌙 | {chat.first_name}, your dinosaur is awake and full of energy!'

                    try:
                        bot.send_message(user['userid'], text)
                    except:
                        pass

                elif notification == "game_end":

                    if user['language_code'] == 'ru':
                        text = f'🎮 | {chat.first_name}, ваш динозавр прекратил играть!'
                    else:
                        text = f'🎮 | {chat.first_name}, your dinosaur has stopped playing!'

                    try:
                        bot.send_message(user['userid'], text)
                    except:
                        pass


                elif notification == "journey_end":

                    if user['language_code'] == 'ru':

                        text = f'🦖 | Ваш динозавр вернулся из путешествия!\nВот что произошло в его путешествии:\n'

                        if user['dinos'][ list(user['dinos'].keys())[0] ]['journey_log'] == []:
                            text += 'Ничего не произошло!'
                        else:
                            n = 1
                            for el in user['dinos'][ list(user['dinos'].keys())[0] ]['journey_log']:
                                text += f'<b>{n}.</b> {el}\n\n'
                                n += 1
                    else:

                        text = f"🦖 | Your dinosaur has returned from a journey!\nHere's what happened on his journey:\n"

                        if bd_user['dinos'][ list(bd_user['dinos'].keys())[0] ]['journey_log'] == []:
                            text += 'Nothing happened!'
                        else:
                            n = 1
                            for el in bd_user['dinos'][ list(bd_user['dinos'].keys())[0] ]['journey_log']:
                                text += f'<b>{n}.</b> {el}\n\n'
                                n += 1

                    try:
                        bot.send_message(user['userid'], text, parse_mode = 'html')
                    except:
                        pass

                elif notification == "friend_request":

                    if user['language_code'] == 'ru':
                        text = f'💬 | {chat.first_name}, вам поступил запрос в друзья!'
                    else:
                        text = f'💬 | {chat.first_name}, you have received a friend request!'

                    try:
                        bot.send_message(user['userid'], text)
                    except:
                        pass

                elif notification == "friend_accept":

                    if user['language_code'] == 'ru':
                        text = f'💬 | {chat.first_name}, {arg} приянл запрос в друзья!'
                    else:
                        text = f'💬 | {chat.first_name}, {arg} accepted a friend request!'

                    try:
                        bot.send_message(user['userid'], text)
                    except:
                        pass

                elif notification == "friend_rejection":

                    if user['language_code'] == 'ru':
                        text = f'💬 | {chat.first_name}, ваш запрос в друзья {arg}, был отклонён...'
                    else:
                        text = f'💬 | {chat.first_name}, your friend request {arg} has been rejected...'

                    try:
                        bot.send_message(user['userid'], text)
                    except:
                        pass

                elif notification == "hunting_end":

                    if user['language_code'] == 'ru':
                        text = f'🍕 | {chat.first_name}, ваш динозавр вернулся со сбора пищи!'
                    else:
                        text = f'🍕 | {chat.first_name}, your dinosaur is back from collecting food!'

                    try:
                        bot.send_message(user['userid'], text)
                    except:
                        pass

                else:
                    print(notification, 'notification')

    @staticmethod
    def check_data(t = None, ind = None, zn = None, m = 'ncheck'):
        global checks_data
        #checks_data = {'memory': [0, time.time()], 'incub': [0, time.time()], 'notif': [0, time.time()], 'main': [0, time.time()], "us": 0}
        if m == 'check':
            return checks_data

        else:
            if t != 'us':
                checks_data[t][ind] = zn
            else:
                checks_data[t] = zn

    @staticmethod
    def inv_egg(user):

        for i in user['inventory']:
            if items_f['items'][i]['type'] == 'egg':
                return True

        return False

    @staticmethod
    def random_items(com_i:list, unc_i:list, rar_i:list, myt_i:list, leg_i:list):

        r_q = random.randint(1, 100)
        if r_q in list(range(1, 51)):
            items = com_i
        elif r_q in list(range(51, 76)):
            items = unc_i
        elif r_q in list(range(76, 91)):
            items = rar_i
        elif r_q in list(range(91, 99)):
            items = myt_i
        else:
            items = leg_i

        return random.choice(items)

    @staticmethod
    def sort_items_col(nls_i:list, lg):
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
            nl.append(f"{name} x{it}")

        return nl

    @staticmethod
    def item_info(item_id, lg):

        item = items_f['items'][item_id]
        type = item['type']
        d_text = ''


        if lg == 'ru':
            if item['type'] == '+heal':
                type = '❤ лекарство'
                d_text = f"*└* Эффективность: {item['act']}"

            elif item['type'] == '+eat':
                type = '🍔 еда'
                d_text = f"*└* Эффективность: {item['act']}"

            elif item['type'] == '+unv':
                type = '☕ энергетический напиток'
                d_text = f"*└* Эффективность: {item['act']}"

            elif item['type'] == 'egg':
                eg_q = item['inc_type']
                if item['inc_type'] == 'random': eg_q = 'рандом'
                if item['inc_type'] == 'com': eg_q = 'обычная'
                if item['inc_type'] == 'unc': eg_q = 'необычная'
                if item['inc_type'] == 'rar': eg_q = 'редкая'
                if item['inc_type'] == 'myt': eg_q = 'мистическая'
                if item['inc_type'] == 'leg': eg_q = 'легендарная'

                type = '🥚 яйцо динозавра'
                d_text = f"*├* Инкубация: {item['incub_time']}{item['time_tag']}\n"
                d_text += f"*└* Редкость яйца: {eg_q}"

            elif item['type'] in ['game_ac', 'unv_ac', 'journey_ac', 'hunt_ac']:
                type = '💍 активный предмет'
                d_text = f"*└* {item['descriptionru']}"

            elif item['type'] == 'None':
                type = '🕳 пустышка'
                d_text = f"*└* Ничего не делает и не для чего не нужна"

            elif item['type'] == 'material':
                type = '🧱 материал'
                d_text = f"*└* Данный предмет нужен для изготовления."

            elif item['type'] == 'recipe':
                type = '🧾 рецепт создания'
                d_text = f'*├* Создаёт: {", ".join(functions.sort_items_col( item["create"], "ru" ))}\n'
                d_text += f'*├* Материалы: {", ".join(functions.sort_items_col( item["materials"], "ru" ))}\n'
                d_text +=  f"*└* {item['descriptionru']}"


            if list(set([ '+mood' ]) & set(item.keys())) != []:
                d_text += f'\n\n*┌* *🍡 Дополнительные бонусы*\n'

                if '+mood' in item.keys():
                    d_text += f"*└* Повышение настроения: {item['+mood']}%"

            if list(set([ '-mood', "-eat" ]) & set(item.keys())) != []:
                d_text += f'\n\n*┌* *📌 Дополнительные штрафы*\n'

                if '-mood' in item.keys():
                    d_text += f"*├* Понижение настроения: {item['-mood']}%"

                if '-eat' in item.keys():
                    d_text += f"*└* Понижение сытости: {item['-eat']}%"

            text =  f"*┌* *🎴 Информация о предмете*\n"
            text += f"*├* Название: {item['nameru']}\n"
            text += f"*├* Тип: {type}\n"
            text += d_text
            in_text = ['🔮 | Использовать', '🗑 | Выбросить', '🔁 | Передать']

        else:
            if item['type'] == '+heal':
                type = '❤ medicine'
                d_text = f"*└* Effectiveness: {item['act']}"

            elif item['type'] == '+eat':
                type = '🍔 eat'
                d_text = f"*└* Effectiveness: {item['act']}"

            elif item['type'] == '+unv':
                type = '☕ energy drink'
                d_text = f"*└* Effectiveness: {item['act']}"

            elif item['type'] == 'egg':
                if item['inc_type'] == 'random': eg_q = 'random'
                if item['inc_type'] == 'com': eg_q = 'common'
                if item['inc_type'] == 'unc': eg_q = 'uncommon'
                if item['inc_type'] == 'rare': eg_q = 'rare'
                if item['inc_type'] == 'myt': eg_q = 'mystical'
                if item['inc_type'] == 'leg': eg_q = 'legendary'

                type = '🥚 dinosaur egg'
                d_text = f"*└* Incubation: {item['incub_time']}{item['time_tag']}\n"
                d_text += f"*└* The rarity of eggs: {eg_q}"

            elif item['type'] in ['game_ac', 'unv_ac', 'journey_ac', 'hunt_ac']:
                type = '💍 active game item'
                d_text = f"*└* {item['descriptionen']}"

            elif item['type'] == 'None':
                type = '🕳 dummy'
                d_text = f"*└* Does nothing and is not needed for anything"

            elif item['type'] == 'material':
                type = '🧱 material'
                d_text = f"*└* This item is needed for manufacturing."

            elif item['type'] == 'recipe':
                type = '🧾 recipe for creation'
                d_text = f'*├* Creates: {", ".join(functions.sort_items_col( item["create"], "ru" ))}\n'
                d_text += f'*├* Materials: {", ".join(functions.sort_items_col( item["materials"], "ru" ))}\n'
                d_text +=  f"*└* {item['descriptionru']}"

            if list(set([ '+mood' ]) & set(item.keys())) != []:
                d_text += f'\n\n*┌* *🍡 Additional bonuses*\n'

                if '+mood' in item.keys():
                    d_text += f"*└* Mood boost: {item['+mood']}%"

            if list(set([ '-mood', "-eat" ]) & set(item.keys())) != []:
                d_text += f'\n\n*┌* *📌 Additional penalties*\n'

                if '-mood' in item.keys():
                    d_text += f"*├* Lowering the mood: {item['-mood']}%"

                if '-eat' in item.keys():
                    d_text += f"*└* Reducing satiety: {item['-eat']}%"

            text =  f"*┌* *🎴 Subject information*\n"
            text += f"*├* Name: {item['nameen']}\n"
            text += f"*├* Type: {type}\n"
            text += d_text
            in_text = ['🔮 | Use', '🗑 | Delete', '🔁 | Transfer']

        markup_inline = types.InlineKeyboardMarkup()
        markup_inline.add( types.InlineKeyboardButton( text = in_text[0], callback_data = f"item_{item_id}"),  types.InlineKeyboardButton( text = in_text[1], callback_data = f"remove_item_{item_id}") )
        markup_inline.add( types.InlineKeyboardButton( text = in_text[2], callback_data = f"exchange_{item_id}") )

        return text, markup_inline

    @staticmethod
    def exchange(bot, message, item_id, bd_user):

        def zero(message, item_id, bd_user):

            if message.text in ['Yes, transfer the item', 'Да, передать предмет']:
                pass
            else:
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

            friends_chunks = list(functions.chunks(list(functions.chunks(friends_name, 2)), 3))

            def work_pr(message, friends_id, page, friends_chunks, friends_id_d, item_id, mms = None):
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

                    bot.send_message(message.chat.id, text, reply_markup = functions.markup(bot, 'profile', bd_user['userid']))

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

                    def ret(message, bd_user, page, friends_chunks, friends_id, friends_id_d, item_id):
                        if message.text in ['↪ Назад', '↪ Back']:
                            res = None
                        else:
                            res = message.text

                        if res == None:
                            if bd_user['language_code'] == 'ru':
                                text = "👥 | Возвращение в меню друзей!"
                            else:
                                text = "👥 | Return to the friends menu!"

                            bot.send_message(message.chat.id, text, reply_markup = markup('friends-menu', user))

                        else:
                            mms = None
                            if res == '◀':
                                if page - 1 == 0:
                                    page = 1
                                else:
                                    page -= 1

                                work_pr(message, friends_id, page, friends_chunks, friends_id_d, item_id, mms = mms)

                            if res == '▶':
                                if page + 1 > len(friends_chunks):
                                    page = len(friends_chunks)
                                else:
                                    page += 1

                                work_pr(message, friends_id, page, friends_chunks, friends_id_d, item_id, mms = mms)

                            else:
                                if res in list(friends_id_d.keys()):
                                    fr_id = friends_id_d[res]
                                    bd_user = users.find_one({"userid": bd_user['userid']})
                                    two_user = users.find_one({"userid": fr_id})

                                    if item_id in bd_user['inventory']:
                                        bd_user['inventory'].remove(item_id)
                                        two_user['inventory'].append(item_id)

                                        users.update_one( {"userid": two_user['userid']}, {"$set": {'inventory': two_user['inventory'] }} )
                                        users.update_one( {"userid": bd_user['userid']}, {"$set": {'inventory': bd_user['inventory'] }} )

                                        if bd_user['language_code'] == 'ru':
                                            text = f'🔁 | Предмет был отправлен игроку!'
                                        else:
                                            text = f"🔁 | The item has been sent to the player!"

                                        bot.send_message(message.chat.id, text, reply_markup = functions.markup(bot, 'profile', bd_user['userid']))

                    if mms == None:
                        msg = bot.send_message(message.chat.id, text, reply_markup = rmk)
                    else:
                        msg = mms
                    bot.register_next_step_handler(msg, ret, bd_user, page, friends_chunks, friends_id, friends_id_d, item_id)

            work_pr(message, friends_id, page, friends_chunks, friends_id_d, item_id)

        if bd_user['language_code'] == 'ru':
            com_buttons = ['Да, передать предмет', '↪ Назад']
            text = '🔁 | Вы уверены что хотите передать предмет другому пользователю?'
        else:
            com_buttons = ['Yes, transfer the item', '↪ Back']
            text = '🔁 | Are you sure you want to transfer the item to another user?'

        rmk = types.ReplyKeyboardMarkup(resize_keyboard = True, row_width = 1)
        rmk.add(com_buttons[0], com_buttons[1])

        msg = bot.send_message(message.chat.id, text, reply_markup = rmk)
        bot.register_next_step_handler(msg, zero, item_id, bd_user)

    def member_profile(bot, mem_id, lang):
        try:
            user = bot.get_chat(int(mem_id))
            bd_user = users.find_one({"userid": user.id})
            expp = 5 * bd_user['lvl'][0] * bd_user['lvl'][0] + 50 * bd_user['lvl'][0] + 100
            n_d = len(list(bd_user['dinos']))
            t_dinos = ''
            for k in bd_user['dinos']:
                i = bd_user['dinos'][k]

                if list( bd_user['dinos']) [ len(bd_user['dinos']) - 1 ] == k:
                    n = '└'

                else:
                    n = '├'

                if i['status'] == 'incubation':

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


                        t_dinos += f"\n   *{n}* Статус: яйцо\n      *└* Редкость: {qual}\n"

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


                        t_dinos += f"\n   *{n}*\n      *├* Status: egg\n      *└* Rare: {qual}\n"

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

                        dino = json_f['elements'][str(i['dino_id'])]
                        pre_qual = dino['image'][5:8]
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

                        t_dinos += f"\n   *{n}* {i['name']}\n      *├* Статус: {stat}\n      *└* Редкость: {qual}\n"

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

                        dino = json_f['elements'][str(i['dino_id'])]
                        pre_qual = dino['image'][5:8]
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

                        t_dinos += f"\n   *{n}* {i['name']}\n      *└* Status: {stat}\n      *└* Rare: {qual}\n"

            if lang == 'ru':

                #act_items
                act_ii = []
                for itmk in bd_user['activ_items'].keys():
                    itm = bd_user['activ_items'][itmk]
                    if itm == None:
                        act_ii.append('Нет')
                    else:
                        item = items_f['items'][itm]['nameru']
                        act_ii.append(item)

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
                text += f"*├* 🌙 Сон: {act_ii[3]}\n"
                text += f"*├* 🎮 Игра: {act_ii[0]}\n"
                text += f"*├* 🌿 Сбор пищи: {act_ii[1]}\n"
                text += f"*└* 🎍 Путешествие: {act_ii[2]}"

            else:
                #act_items
                act_ii = []
                for itmk in bd_user['activ_items'].keys():
                    itm = bd_user['activ_items'][itmk]
                    if itm == None:
                        act_ii.append('None')
                    else:
                        item = items_f['items'][itm]['nameen']
                        act_ii.append(item)

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
                text += f"*├* 🌙 Sleep: {act_ii[3]}\n"
                text += f"*├* 🎮 Game: {act_ii[0]}\n"
                text += f"*├* 🌿 Collecting food: {act_ii[1]}\n"
                text += f"*└* 🎍 Journey: {act_ii[2]}"
        except:
            text = 'KMk456 jr5uhsd7489 lkjs47609485\n               ERRoR'

        return text
