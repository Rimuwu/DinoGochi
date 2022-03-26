import telebot
from telebot import types
import config
import random
import json
import pymongo
from PIL import Image, ImageFont, ImageDraw, ImageOps, ImageSequence, ImageFilter
import io
from io import BytesIO
from functions import functions
import time
import os
import threading

bot = telebot.TeleBot(config.TOKEN)

client = pymongo.MongoClient(config.CLUSTER_TOKEN)
users = client.bot.users
items = client.bot.items

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
        return str(max(id_list))

def random_dino(user, dino_id_remove):
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
    del user['dinos'][dino_id_remove]
    user['dinos'][user_dino_pn(user)] = {'dino_id': dino_id, "status": 'dino', 'activ_status': 'pass_active', 'name': dino['name'], 'stats':  {"heal": 100, "eat": random.randint(70, 100), 'game': random.randint(50, 100), 'mood': random.randint(7, 100), "unv": 100}}

    users.update_one( {"userid": user['userid']}, {"$set": {'dinos': user['dinos']}} )


def notifications_manager(notification, user, arg = None):
    if user['settings']['notifications'] == True:
        chat = bot.get_chat(user['userid'])

        if notification == "5_min_incub":

            if user['language_code'] == 'ru':
                text = f'🥚 | {chat.first_name}, ваш динозавр вылупится через 5 минут!'
            else:
                text = f'🥚 | {chat.first_name}, your dinosaur will hatch in 5 minutes!'

            bot.send_message(user['userid'], text)

        elif notification == "incub":

            if user['language_code'] == 'ru':
                text = f'🦖 | {chat.first_name}, динозавр вылупился! 🎉'
            else:
                text = f'🦖 | {chat.first_name}, the dinosaur has hatched! 🎉'

            bot.send_message(user['userid'], text)

        elif notification == "need_eat":

            if user['language_code'] == 'ru':
                text = f'🍕 | {chat.first_name}, динозавр хочет кушать, его потребность в еде опустилась до {arg}%!'
            else:
                text = f'🍕 | {chat.first_name}, the dinosaur wants to eat, his need for food has dropped to {arg}%!'

            bot.send_message(user['userid'], text)

        elif notification == "need_game":

            if user['language_code'] == 'ru':
                text = f'🎮 | {chat.first_name}, динозавр хочет играть, его потребность в игре опустилось до {arg}%!'
            else:
                text = f'🎮 | {chat.first_name}, The dinosaur wants to play, his need for the game has dropped to {arg}%!'

            bot.send_message(user['userid'], text)

        elif notification == "need_mood":

            if user['language_code'] == 'ru':
                text = f'🦖 | {chat.first_name}, у динозавра плохое настроение, его настроение опустилось до {arg}%!'
            else:
                text = f'🦖 | {chat.first_name}, the dinosaur is in a bad mood, his mood has sunk to {arg}%!'

            bot.send_message(user['userid'], text)

        elif notification == "need_unv":

            if user['language_code'] == 'ru':
                text = f'🌙 | {chat.first_name}, динозавра хочет спать, его харрактеристика сна опустилось до {arg}%!'
            else:
                text = f'🌙 | {chat.first_name}, the dinosaur wants to sleep, his sleep characteristic dropped to {arg}%!'

            bot.send_message(user['userid'], text)

        elif notification == "dead":

            if user['language_code'] == 'ru':
                text = f'💥 | {chat.first_name}, ваш динозаврик.... Умер...'
            else:
                text = f'💥 | {chat.first_name}, your dinosaur.... Died...'

            bot.send_message(user['userid'], text)

        elif notification == "woke_up":

            if user['language_code'] == 'ru':
                text = f'🌙 | {chat.first_name}, ваш динозавр проснулся и полон сил!'
            else:
                text = f'💥 | {chat.first_name}, your dinosaur is awake and full of energy!'

            bot.send_message(user['userid'], text)

        elif notification == "walk_end":

            if user['language_code'] == 'ru':

                text = f'🦖 | Ваш динозавр вернулся с прогулки!\nВот что произошло пока он гулял:\n'
                n = 1
                for el in arg:
                    text += f'{n}. {el}\n'
                    n += 1
            else:

                text = f"🦖 | Your dinosaur is back from a walk!\nHere's what happened while he was walking:\n"

                n = 1
                for el in arg:
                    text += f'{n}. {el}\n'
                    n += 1

            bot.send_message(user['userid'], text)

def check(): #проверка каждые 10 секунд
    while True:
        time.sleep(10)

        members = users.find({ })
        for user in members:

            for dino_id in user['dinos'].keys():
                dino = user['dinos'][dino_id]
                if dino['status'] == 'incubation': #инкубация
                    if dino['incubation_time'] - int(time.time()) <= 60*5 and dino['incubation_time'] - int(time.time()) > 0: #уведомление за 5 минут

                        if 'inc_notification' in list(user['notifications'].keys()):

                            if user['notifications']['inc_notification'] == False:
                                notifications_manager("5_min_incub", user, dino)

                                user['notifications']['inc_notification'] = True
                                users.update_one( {"userid": user['userid']}, {"$set": {'notifications': user['notifications']}} )

                        else:
                            user['notifications']['inc_notification'] = True
                            users.update_one( {"userid": user['userid']}, {"$set": {'notifications': user['notifications']}} )

                            notifications_manager("5_min_incub", user, dino_id)


                    elif dino['incubation_time'] - int(time.time()) <= 0:

                        if 'inc_notification' in list(user['notifications'].keys()):
                            del user['notifications']['inc_notification']
                            users.update_one( {"userid": user['userid']}, {"$set": {'notifications': user['notifications']}} )

                        random_dino(user, dino_id)
                        notifications_manager("incub", user, dino_id)
                        break

                if dino['status'] == 'dino': #дино
                #stats  - pass_active (ничего) sleep - (сон)

                    #
                    if random.randint(1, 55) == 1: #eat
                        user['dinos'][dino_id]['stats']['eat'] -= random.randint(1,2)

                    if random.randint(1, 28) == 1: #game
                        user['dinos'][dino_id]['stats']['game'] -= random.randint(1,2)

                    if random.randint(1, 130) == 1: #unv
                        user['dinos'][dino_id]['stats']['unv'] -= random.randint(1,2)

                    if dino['activ_status'] == 'pass_active':

                        if user['dinos'][dino_id]['stats']['game'] > 90:
                            if dino['stats']['mood'] < 100:
                                if random.randint(1,30) == 1:
                                    user['dinos'][dino_id]['stats']['mood'] += random.randint(1,2)

                        if user['dinos'][dino_id]['stats']['unv'] <= 20 and user['dinos'][dino_id]['stats']['unv'] != 0:
                            if dino['stats']['mood'] > 0:
                                if random.randint(1,30) == 1:
                                    user['dinos'][dino_id]['stats']['mood'] -= random.randint(1,2)

                            if dino['stats']['heal'] > 0:
                                if random.randint(1,60) == 1:
                                    user['dinos'][dino_id]['stats']['heal'] -= 1
                                    user['dinos'][dino_id]['stats']['mood'] -= random.randint(1,10)

                    if dino['activ_status'] == 'sleep':

                        if user['dinos'][dino_id]['stats']['unv'] < 100:
                            if random.randint(1,45) == 1:
                                user['dinos'][dino_id]['stats']['unv'] += random.randint(1,2)

                        if user['dinos'][dino_id]['stats']['unv'] >= 100:
                            user['dinos'][dino_id]['activ_status'] = 'pass_active'
                            notifications_manager("woke_up", user)

                    if dino['activ_status'] == 'walk':

                        if int(dino['walk_time']-time.time()) <= 0:
                            user['dinos'][dino_id]['activ_status'] = 'pass_active'

                            notifications_manager("walk_end", user, user['dinos'][ dino_id ]['walk_log'])

                            del user['dinos'][ dino_id ]['walk_time']
                            del user['dinos'][ dino_id ]['walk_log']

                        if random.randint(1,60) == 1:
                            if random.randint(1,2) == 1:
                                event = 'положительное событие'
                                user['dinos'][ dino_id ]['walk_log'].append(event)

                            else:
                                event = 'отрицательное событие'
                                user['dinos'][ dino_id ]['walk_log'].append(event)


                    if user['dinos'][dino_id]['stats']['game'] < 40 and user['dinos'][dino_id]['stats']['game'] > 10:
                        if dino['stats']['mood'] > 0:
                            if random.randint(1,30) == 1:
                                user['dinos'][dino_id]['stats']['mood'] -= random.randint(1,2)

                    if user['dinos'][dino_id]['stats']['game'] < 20:
                        if dino['stats']['mood'] > 0:
                            if random.randint(1,15) == 1:
                                user['dinos'][dino_id]['stats']['mood'] -= 5

                    if user['dinos'][dino_id]['stats']['unv'] == 0:
                        if random.randint(1,30) == 1:
                            user['dinos'][dino_id]['stats']['heal'] -= 5

                    if user['dinos'][dino_id]['stats']['eat'] > 90:
                        if dino['stats']['mood'] < 100:
                            if random.randint(1,30) == 1:
                                user['dinos'][dino_id]['stats']['mood'] += random.randint(1,2)

                    if user['dinos'][dino_id]['stats']['eat'] <= 40 and user['dinos'][dino_id]['stats']['eat'] != 0:
                        if dino['stats']['mood'] > 0:
                            if random.randint(1,30) == 1:
                                user['dinos'][dino_id]['stats']['mood'] -= random.randint(1,2)

                        if dino['stats']['heal'] > 0:
                            if random.randint(1,30) == 1:
                                user['dinos'][dino_id]['stats']['heal'] -= random.randint(1,2)

                    if user['dinos'][dino_id]['stats']['eat'] == 0:
                        if dino['stats']['heal'] > 0:
                            if random.randint(1,30) == 1:
                                user['dinos'][dino_id]['stats']['heal'] -= 5


                    if user['dinos'][dino_id]['stats']['eat'] > 80 and user['dinos'][dino_id]['stats']['unv'] > 70 and user['dinos'][dino_id]['stats']['game'] > 70 and user['dinos'][dino_id]['stats']['mood'] > 50:

                        if random.randint(1,6) == 1:
                            user['dinos'][dino_id]['stats']['heal'] += random.randint(1,4)
                            user['dinos'][dino_id]['stats']['eat'] -= random.randint(0,1)
                            user['dinos'][dino_id]['stats']['unv'] -= random.randint(0,1)


                    if user['dinos'][dino_id]['stats']['unv'] >= 100:
                        user['dinos'][dino_id]['stats']['unv'] = 100
                        user['dinos'][dino_id]['activ_status'] = 'pass_active'

                    if user['dinos'][dino_id]['stats']['unv'] >= 40:
                        user['notifications']['need_unv'] = False

                    if user['dinos'][dino_id]['stats']['eat'] >= 100:
                        user['dinos'][dino_id]['stats']['eat'] = 100

                    if user['dinos'][dino_id]['stats']['eat'] >= 50:
                        user['notifications']['need_eat'] = False

                    if user['dinos'][dino_id]['stats']['game'] >= 100:
                        user['dinos'][dino_id]['stats']['game'] = 100

                    if user['dinos'][dino_id]['stats']['game'] >= 80:
                        user['notifications']['need_game'] = False

                    if user['dinos'][dino_id]['stats']['heal'] >= 100:
                        user['dinos'][dino_id]['stats']['heal'] = 100

                    if user['dinos'][dino_id]['stats']['mood'] >= 100:
                        user['dinos'][dino_id]['stats']['mood'] = 100

                    if user['dinos'][dino_id]['stats']['mood'] >= 80:
                        user['notifications']['need_mood'] = False


                    if user['dinos'][dino_id]['stats']['unv'] < 0:
                        user['dinos'][dino_id]['stats']['unv'] = 0

                    if user['dinos'][dino_id]['stats']['unv'] <= 30:
                        if 'need_unv' not in list(user['notifications'].keys()) or user['notifications']['need_unv'] == False:
                            notifications_manager("need_unv", user, user['dinos'][dino_id]['stats']['unv'])
                            user['notifications']['need_unv'] = True

                    if user['dinos'][dino_id]['stats']['eat'] < 0:
                        user['dinos'][dino_id]['stats']['eat'] = 0

                    if user['dinos'][dino_id]['stats']['eat'] <= 40:
                        if 'need_eat' not in list(user['notifications'].keys()) or user['notifications']['need_eat'] == False:
                            notifications_manager("need_eat", user, user['dinos'][dino_id]['stats']['eat'])
                            user['notifications']['need_eat'] = True

                    if user['dinos'][dino_id]['stats']['game'] < 0:
                        user['dinos'][dino_id]['stats']['game'] = 0

                    if user['dinos'][dino_id]['stats']['game'] <= 50:
                        if 'need_game' not in list(user['notifications'].keys()) or user['notifications']['need_game'] == False:
                            notifications_manager("need_game", user, user['dinos'][dino_id]['stats']['game'])
                            user['notifications']['need_game'] = True

                    if user['dinos'][dino_id]['stats']['mood'] < 0:
                        user['dinos'][dino_id]['stats']['mood'] = 0

                    if user['dinos'][dino_id]['stats']['mood'] <= 70:
                        if 'need_mood' not in list(user['notifications'].keys()) or user['notifications']['need_mood'] == False:
                            notifications_manager("need_mood", user, user['dinos'][dino_id]['stats']['mood'])
                            user['notifications']['need_mood'] = True

                    if user['dinos'][dino_id]['stats']['heal'] <= 0:
                        user['dinos'][dino_id]['stats']['heal'] = 0
                        user['dinos'][dino_id]['status'] = 'dead_dino'

                        if 'dead' not in list(user['notifications'].keys()) or user['notifications']['dead'] == False:
                            notifications_manager("dead", user)
                            user['notifications']['dead'] = True


                    users.update_one( {"userid": user['userid']}, {"$set": {'dinos': user['dinos'] }} )
                    users.update_one( {"userid": user['userid']}, {"$set": {'notifications': user['notifications'] }} )



thr1 = threading.Thread(target = check, daemon=True)


with open('../images/dino_data.json') as f:
    json_f = json.load(f)

def markup(element = 1, user = None):
    markup = types.ReplyKeyboardMarkup(resize_keyboard = True)

    if element == 1 and users.find_one({"userid": user.id}) != None:

        if user.language_code == 'ru':
            nl = ['🦖 Динозавр', '🕹 Действия', '🎢 Рейтинг', '🔧 Настройки']
        else:
            nl = ['🦖 Dinosaur', '🕹 Actions', '🎢 Rating', '🔧 Settings']

        item1 = types.KeyboardButton(nl[0])
        item2 = types.KeyboardButton(nl[1])
        item3 = types.KeyboardButton(nl[2])
        item4 = types.KeyboardButton(nl[3])

        markup.add(item1, item2, item3, item4)

    elif element == 1:
        if user.language_code == 'ru':
            nl = ['🍡 Начать играть']
        else:
            nl = ['🍡 Start playing']

        item1 = types.KeyboardButton(nl[0])

        markup.add(item1)

    elif element == "settings":
        bd_user = users.find_one({"userid": user.id})

        if user.language_code == 'ru':
            nl = []

            if bd_user['settings']['notifications'] == True:
                nl.append('❗ Уведомления: ❎')
            else:
                nl.append('❗ Уведомления: ✅')

            nl.append('↪ Назад')

        else:
            nl = []

            if bd_user['settings']['notifications'] == True:
                nl.append('❗ Notifications: ❎')
            else:
                nl.append('❗ Notifications: ✅')

            nl.append('↪ Back')


        item1 = types.KeyboardButton(nl[0])
        item2 = types.KeyboardButton(nl[1])

        markup.add(item1, item2)

    elif element == 'actions' and users.find_one({"userid": user.id}) != None:
        markup = types.ReplyKeyboardMarkup(resize_keyboard = True, row_width = 2)

        bd_user = users.find_one({"userid": user.id})

        if user.language_code == 'ru':
            nl = ['🎮 Поиграть', '🍣 Покормить', '🔪 Поохотиться', '↪ Назад']

            if len(bd_user['dinos']) == 1:
                dino = bd_user['dinos'][ list(bd_user['dinos'].keys())[0] ]

                if dino['activ_status'] == 'walk':
                    nl.insert(2, '🎑 Позвать')
                else:
                    nl.insert(2, '🎑 Погулять')

                if dino['activ_status'] == 'sleep':
                    nl.insert(3, '🌙 Пробудить')
                else:
                    nl.insert(3, '🌙 Уложить спать')

            else:
                pass
        else:
            nl = ['🎮 Play', '🍣 Feed', '🔪 To hunt', '↪ Back']

            if len(bd_user['dinos']) == 1:
                dino = bd_user['dinos'][ list(bd_user['dinos'].keys())[0] ]

                if dino['activ_status'] == 'walk':
                    nl.insert(2, '🎑 Call')
                else:
                    nl.insert(2, '🎑 Walk')

                if dino['activ_status'] == 'sleep':
                    nl.insert(3, '🌙 Awaken')
                else:
                    nl.insert(3, '🌙 Put to bed')

            else:
                pass

        item1 = types.KeyboardButton(nl[0])
        item2 = types.KeyboardButton(nl[1])
        item3 = types.KeyboardButton(nl[2])
        item4 = types.KeyboardButton(nl[3])
        item5 = types.KeyboardButton(nl[4])
        item6 = types.KeyboardButton(nl[5])

        markup.add(item1, item2, item3, item4, item5, item6)

    else:
        print(f'{element}\n{user}')



    return markup


@bot.message_handler(commands=['start', 'help'])
def on_start(message):
    user = message.from_user
    if users.find_one({"userid": user.id}) == None:
        if user.language_code == 'ru':
            text = f"🎋 | Хей <b>{user.first_name}</b>, рад приветствовать тебя!\n"+ f"<b>•</b> Я маленький игровой бот по типу тамагочи, только с динозаврами!🦖\n\n"+f"<b>🕹 | Что такое тамагочи?</b>\n"+f'<b>•</b> Тамагочи - игра с виртуальным питомцем, которого надо кормить, ухаживать за ним, играть и тд.🥚\n'+f"<b>•</b> Соревнуйтесь в рейтинге и станьте лучшим!\n\n"+f"<b>🎮 | Как начать играть?</b>\n"+f'<b>•</b> Нажмите кномку <b>🍡 Начать играть</b>!\n\n'+f'<b>❤ | Ждём в игре!</b>\n'
        else:
            text = f"🎋 | Hey <b>{user.first_name}</b>, I am glad to welcome you!\n" +f"<b>•</b> I'm a small tamagotchi-type game bot, only with dinosaurs!🦖\n\n"+f"<b>🕹 | What is tamagotchi?</b>\n"+ f'<b>•</b> Tamagotchi is a game with a virtual pet that needs to be fed, cared for, played, and so on.🥚\n'+ f"<b>•</b> Compete in the ranking and become the best!\n\n"+ f"<b>🎮 | How to start playing?</b>\n" + f'<b>•</b> Press the button <b>🍡Start playing</b>!\n\n' + f'<b>❤ | Waiting in the game!</b>\n' +f'<b>❗ | In some places, the bot may not be translated!</b>\n'

        bot.reply_to(message, text, reply_markup = markup(user = user), parse_mode = 'html')
    else:
        bot.reply_to(message, '👋', reply_markup = markup(user = user), parse_mode = 'html')


@bot.message_handler(content_types = ['text'])
def on_message(message):
    user = message.from_user

    def trans_paste(fg_img,bg_img,alpha=10,box=(0,0)):
        fg_img_trans = Image.new("RGBA",fg_img.size)
        fg_img_trans = Image.blend(fg_img_trans,fg_img,alpha)
        bg_img.paste(fg_img_trans,box,fg_img_trans)
        return bg_img

    if message.chat.type == 'private':

        if message.text in ['🍡 Начать играть', '🍡 Start playing']:
            if users.find_one({"userid": user.id}) == None:

                def photo():
                    global json_f
                    bg_p = Image.open(f"../images/remain/{random.choice(['back', 'back2'])}.png")
                    eg_l = []
                    id_l = []

                    for i in range(3):
                        rid = str(random.choice(list(json_f['data']['egg'])))
                        image = Image.open('../images/'+str(json_f['elements'][rid]['image']))
                        eg_l.append(image)
                        id_l.append(rid)

                    for i in range(3):
                        bg_img = bg_p
                        fg_img = eg_l[i]
                        img = trans_paste(fg_img, bg_img, 1.0, (i*512,0))

                    img.save('eggs.png')
                    photo = open(f"eggs.png", 'rb')

                    return photo, id_l

                if user.language_code == 'ru':
                    text = '🥚 | Выберите яйцо с динозавром!'
                else:
                    text = '🥚 | Choose a dinosaur egg!'

                users.insert_one({'userid': user.id, 'dinos': {}, 'eggs': [], 'notifications': {}, 'settings': {'notifications': True}, 'language_code': user.language_code, 'inventory': [], 'coins': 0})

                markup_inline = types.InlineKeyboardMarkup()
                item_1 = types.InlineKeyboardButton( text = '🥚 1', callback_data = 'egg_answer_1')
                item_2 = types.InlineKeyboardButton( text = '🥚 2', callback_data = 'egg_answer_2')
                item_3 = types.InlineKeyboardButton( text = '🥚 3', callback_data = 'egg_answer_3')
                markup_inline.add(item_1, item_2, item_3)

                photo, id_l = photo()
                bot.send_photo(message.chat.id, photo, text, reply_markup = markup_inline)
                users.update_one( {"userid": user.id}, {"$set": {'eggs': id_l}} )

    if message.text in ['🦖 Динозавр', '🦖 Dinosaur']:
        bd_user = users.find_one({"userid": user.id})
        if bd_user != None:

            def egg_profile(bd_user, user):
                egg_id = bd_user['dinos'][ list(bd_user['dinos'].keys())[0] ]['egg_id']

                if user.language_code == 'ru':
                    lang = user.language_code
                else:
                    lang = 'en'

                t_incub = bd_user['dinos'][ list(bd_user['dinos'].keys())[0] ]['incubation_time'] - time.time()
                if t_incub < 0:
                    t_incub = 0

                time_end = functions.time_end(t_incub, True)
                if len(time_end) >= 18:
                    time_end = time_end[:-6]

                bg_p = Image.open(f"../images/remain/egg_profile_{lang}.png")
                egg = Image.open("../images/" + str(json_f['elements'][egg_id]['image']))
                egg = egg.resize((290, 290), Image.ANTIALIAS)

                img = trans_paste(egg, bg_p, 1.0, (-50, 40))

                idraw = ImageDraw.Draw(img)
                line1 = ImageFont.truetype("../fonts/Comic Sans MS.ttf", size = 35)

                idraw.text((430, 220), time_end, font = line1)

                img.save('profile.png')
                profile = open(f"profile.png", 'rb')

                return profile, time_end

            def dino_profile(bd_user, user, dino_user_id):

                dino_id = str(bd_user['dinos'][ dino_user_id ]['dino_id'])

                if user.language_code == 'ru':
                    lang = user.language_code
                else:
                    lang = 'en'

                dino = json_f['elements'][dino_id]
                if 'class' in list(dino.keys()):
                    bg_p = Image.open(f"../images/remain/{dino['class']}_icon.png")
                else:
                    bg_p = Image.open(f"../images/remain/None_icon.png")

                class_ = dino['image'][5:8]

                panel_i = Image.open(f"../images/remain/{class_}_profile_{lang}.png")

                img = trans_paste(panel_i, bg_p, 1.0)

                dino_image = Image.open("../images/"+str(json_f['elements'][dino_id]['image']))

                sz = 412
                dino_image = dino_image.resize((sz, sz), Image.ANTIALIAS)

                xy = -80
                x2 = 80
                img = trans_paste(dino_image, img, 1.0, (xy + x2, xy, sz + xy + x2, sz + xy ))


                idraw = ImageDraw.Draw(img)
                line1 = ImageFont.truetype("../fonts/Comic Sans MS.ttf", size = 35)

                idraw.text((530, 110), str(bd_user['dinos'][dino_user_id]['stats']['heal']), font = line1)
                idraw.text((530, 190), str(bd_user['dinos'][dino_user_id]['stats']['eat']), font = line1)

                idraw.text((750, 110), str(bd_user['dinos'][dino_user_id]['stats']['game']), font = line1)
                idraw.text((750, 190), str(bd_user['dinos'][dino_user_id]['stats']['mood']), font = line1)
                idraw.text((750, 270), str(bd_user['dinos'][dino_user_id]['stats']['unv']), font = line1)

                img.save('profile.png')
                profile = open(f"profile.png", 'rb')

                return profile

            if len(bd_user['dinos'].keys()) == 0:
                pass

            elif len(bd_user['dinos'].keys()) == 1:


                if bd_user['dinos'][ list(bd_user['dinos'].keys())[0] ]['status'] == 'incubation':

                    profile, time_end  = egg_profile(bd_user, user)
                    if user.language_code == 'ru':
                        text = f'🥚 | Яйцо инкубируется, осталось: {time_end}'
                    else:
                        text = f'🥚 | The egg is incubated, left: {time_end}'

                    bot.send_photo(message.chat.id, profile, text, reply_markup = markup(user = user))

                if bd_user['dinos'][ list(bd_user['dinos'].keys())[0] ]['status'] == 'dino':
                    bd_dino = bd_user['dinos'][ list(bd_user['dinos'].keys())[0] ]

                    profile = dino_profile(bd_user, user, dino_user_id = list(bd_user['dinos'].keys())[0] )

                    if user.language_code == 'ru':

                        if bd_dino['activ_status'] == 'pass_active':
                            st_t = 'ничего не делает 💭'
                        elif bd_dino['activ_status'] == 'sleep':
                            st_t = 'спит 🌙'
                        elif bd_dino['activ_status'] == 'game':
                            st_t = 'играет 🎮'
                        elif bd_dino['activ_status'] == 'walk':
                            st_t = 'гуляет 🎴'
                        elif bd_dino['activ_status'] == 'hunt':
                            st_t = 'охотится 🔪'

                        if bd_dino['stats']['heal'] >= 60:
                            h_text = '❤ | Динозавр здоров'
                        elif bd_dino['stats']['heal'] < 60 and bd_dino['stats']['heal'] > 10:
                            h_text = '❤ | Динозавр в плохом состоянии'
                        elif bd_dino['stats']['heal'] <= 10:
                            h_text = '❤ | Динозавр в крайне плохом состоянии!'

                        if bd_dino['stats']['eat'] >= 60:
                            e_text = '🍕 | Динозавр сыт'
                        elif bd_dino['stats']['eat'] < 60 and bd_dino['stats']['eat'] > 10:
                            e_text = '🍕 | Динозавр голоден'
                        elif bd_dino['stats']['eat'] <= 10:
                            e_text = '🍕 | Динозавр умирает от голода!'

                        if bd_dino['stats']['game'] >= 60:
                            g_text = '🎮 | Динозавр не хочет играть'
                        elif bd_dino['stats']['game'] < 60 and bd_dino['stats']['game'] > 10:
                            g_text = '🎮 | Динозавр скучает...'
                        elif bd_dino['stats']['game'] <= 10:
                            g_text = '🎮 | Динозавр умерает от скуки!'

                        if bd_dino['stats']['mood'] >= 60:
                            m_text = '🎈 | Динозавр в хорошем настроении'
                        elif bd_dino['stats']['mood'] < 60 and bd_dino['stats']['mood'] > 10:
                            m_text = '🎈 | У динозавра нормальное настроение'
                        elif bd_dino['stats']['mood'] <= 10:
                            m_text = '🎈 | Динозавр грустит!'

                        if bd_dino['stats']['unv'] >= 60:
                            u_text = '🌙 | Динозавр полон сил'
                        elif bd_dino['stats']['unv'] < 60 and bd_dino['stats']['unv'] > 10:
                            u_text = '🌙 | У динозавра есть силы'
                        elif bd_dino['stats']['unv'] <= 10:
                            u_text = '🌙 | Динозавр устал!'


                        text = f'🦖 | Имя: {bd_dino["name"]}\n👁‍🗨 | Статус: {st_t} \n\n{h_text}\n{e_text}\n{g_text}\n{m_text}\n{u_text}'

                        if bd_dino['activ_status'] == 'walk':
                            w_t = bd_dino['walk_time'] - time.time()
                            if w_t < 0:
                                w_t = 0
                            text += f"\n\n🌳 | Прогулка: \n·  Осталось: { functions.time_end(w_t) }"
                    else:

                        if bd_dino['activ_status'] == 'pass_active':
                            st_t = 'does nothing 💭'
                        elif bd_dino['activ_status'] == 'sleep':
                            st_t = 'sleeping 🌙'
                        elif bd_dino['activ_status'] == 'game':
                            st_t = 'playing 🎮'
                        elif bd_dino['activ_status'] == 'walk':
                            st_t = 'walking 🎴'
                        elif bd_dino['activ_status'] == 'hunt':
                            st_t = 'hunting 🔪'

                        if bd_dino['stats']['heal'] >= 60:
                            h_text = '❤ | The dinosaur is healthy'
                        elif bd_dino['stats']['heal'] < 60 and bd_dino['stats']['heal'] > 10:
                            h_text = '❤ | Dinosaur in bad condition'
                        elif bd_dino['stats']['heal'] <= 10:
                            h_text = '❤ | The dinosaur is in extremely bad condition!'

                        if bd_dino['stats']['eat'] >= 60:
                            e_text = '🍕 | The dinosaur is full'
                        elif bd_dino['stats']['eat'] < 60 and bd_dino['stats']['eat'] > 10:
                            e_text = '🍕 | The dinosaur is hungry'
                        elif bd_dino['stats']['eat'] <= 10:
                            e_text = '🍕 | The dinosaur is starving!'

                        if bd_dino['stats']['game'] >= 60:
                            g_text = "🎮 | The dinosaur doesn't want to play"
                        elif bd_dino['stats']['game'] < 60 and bd_dino['stats']['game'] > 10:
                            g_text = '🎮 | The dinosaur is bored...'
                        elif bd_dino['stats']['game'] <= 10:
                            g_text = '🎮 | The dinosaur is dying of boredom!'

                        if bd_dino['stats']['mood'] >= 60:
                            m_text = '🎈 | The dinosaur is in a good mood'
                        elif bd_dino['stats']['mood'] < 60 and bd_dino['stats']['mood'] > 10:
                            m_text = '🎈 | The dinosaur has a normal mood'
                        elif bd_dino['stats']['mood'] <= 10:
                            m_text = '🎈 | The dinosaur is sad!'

                        if bd_dino['stats']['unv'] >= 60:
                            u_text = '🌙 | The dinosaur is full of energy'
                        elif bd_dino['stats']['unv'] < 60 and bd_dino['stats']['unv'] > 10:
                            u_text = '🌙 | The dinosaur has powers'
                        elif bd_dino['stats']['unv'] <= 10:
                            u_text = '🌙 | The dinosaur is tired!'

                        text = f'🦖 | Name: {bd_dino["name"]}\n👁‍🗨 | Status: {st_t}\n\n{h_text}\n{e_text}\n{g_text}\n{m_text}\n{u_text}'

                    bot.send_photo(message.chat.id, profile, text, reply_markup = markup(user = user) )

            else:
                pass

    if message.text in ['🔧 Настройки', '🔧 Settings']:
        bd_user = users.find_one({"userid": user.id})

        if bd_user != None:

            if user.language_code == 'ru':
                text = '🔧 Меню настроек активировано'
            else:
                text = '🔧 The settings menu is activated'


            bot.send_message(message.chat.id, text, reply_markup = markup('settings', user))

    if message.text in ['↪ Назад', '↪ Back']:

        if user.language_code == 'ru':
            text = '↪ Возврат в главное меню'
        else:
            text = '↪ Return to the main menu'

        bot.send_message(message.chat.id, text, reply_markup = markup(1, user))

    if message.text in ['❗ Notifications: ✅', '❗ Уведомления: ✅']:
        bd_user = users.find_one({"userid": user.id})
        if bd_user != None:
            if bd_user['settings']['notifications'] == False:
                bd_user['settings']['notifications'] = True
                users.update_one( {"userid": bd_user['userid']}, {"$set": {'settings': bd_user['settings'] }} )

                if user.language_code == 'ru':
                    text = '🔧 Настройки изменены!'
                else:
                    text = '🔧 Settings changed!'

                bot.send_message(message.chat.id, text, reply_markup = markup("settings", user))

    if message.text in ['❗ Notifications: ❎', '❗ Уведомления: ❎']:
        bd_user = users.find_one({"userid": user.id})
        if bd_user != None:
            if bd_user['settings']['notifications'] == True:
                bd_user['settings']['notifications'] = False
                users.update_one( {"userid": bd_user['userid']}, {"$set": {'settings': bd_user['settings'] }} )

                if user.language_code == 'ru':
                    text = '🔧 Настройки изменены!'
                else:
                    text = '🔧 Settings changed!'

                bot.send_message(message.chat.id, text, reply_markup = markup("settings", user))

    if message.text in ['🕹 Действия', '🕹 Actions']:
        bd_user = users.find_one({"userid": user.id})
        if bd_user != None:

            if user.language_code == 'ru':
                text = '🕹 Панель действий открыта!'
            else:
                text = '🕹 The action panel is open!'

            bot.send_message(message.chat.id, text, reply_markup = markup("actions", user))

    # nl = ['🎮 Поиграть', '🍣 Покормить', '🎑 Погулять', '🔪 Поохотиться', '🌙 Уложить спать', '↪ Назад']
    #
    # nl = ['🎮 Play', '🍣 Feed', '🎑 Walk', '🔪 To hunt', '🌙 Put to bed', '↪ Back']

    if message.text in ['🌙 Уложить спать', '🌙 Put to bed']:
        bd_user = users.find_one({"userid": user.id})
        if bd_user != None:
            if len(bd_user['dinos']) == 1:
                dino = bd_user['dinos'][ list(bd_user['dinos'].keys())[0] ]
                if dino['activ_status'] == 'pass_active':
                    if dino['stats']['unv'] >= 90:

                        if user.language_code == 'ru':
                            text = '🌙 Динозавр не хочет спать!'
                        else:
                            text = "🌙 The dinosaur doesn't want to sleep!"

                        bot.send_message(message.chat.id, text, reply_markup = markup("actions", user))

                    else:

                        bd_user['dinos'][ list(bd_user['dinos'].keys())[0] ]['activ_status'] = 'sleep'
                        users.update_one( {"userid": bd_user['userid']}, {"$set": {'dinos': bd_user['dinos'] }} )

                        if user.language_code == 'ru':
                            text = '🌙 Вы уложили динозавра спать!'
                        else:
                            text = "🌙 You put the dinosaur to sleep!"

                        bot.send_message(message.chat.id, text , reply_markup = markup('actions', user))

            else:
                pass

    if message.text in ['🌙 Пробудить', '🌙 Awaken']:
        bd_user = users.find_one({"userid": user.id})
        if bd_user != None:
            if len(bd_user['dinos']) == 1:
                dino = bd_user['dinos'][ list(bd_user['dinos'].keys())[0] ]
                if dino['activ_status'] == 'sleep':
                    r_n = random.randint(0, 20)

                    bd_user['dinos'][ list(bd_user['dinos'].keys())[0] ]['activ_status'] = 'pass_active'
                    bd_user['dinos'][ list(bd_user['dinos'].keys())[0] ]['stats']['mood'] -= r_n

                    if bd_user['dinos'][ list(bd_user['dinos'].keys())[0] ]['stats']['mood'] < 0:
                        bd_user['dinos'][ list(bd_user['dinos'].keys())[0] ]['stats']['mood'] = 0

                    users.update_one( {"userid": bd_user['userid']}, {"$set": {'dinos': bd_user['dinos'] }} )

                    if user.language_code == 'ru':
                        text = f'🌙 Ваш динозавр пробудился. Он сильно не доволен что вы его разбудили!n\Динозавр потерял {r_n}% настроения.'
                    else:
                        text = f"🌙 Your dinosaur has awakened. He is very unhappy that you woke him up!n\Dinosaur lost {r_n}% of mood."

                    bot.send_message(message.chat.id, text , reply_markup = markup('actions', user))


    if message.text in ['🎑 Погулять', '🎑 Walk']:
        bd_user = users.find_one({"userid": user.id})
        if bd_user != None:
            if len(bd_user['dinos']) == 1:
                dino = bd_user['dinos'][ list(bd_user['dinos'].keys())[0] ]
                if dino['activ_status'] == 'pass_active':
                    markup_inline = types.InlineKeyboardMarkup()

                    if user.language_code == 'ru':
                        text = '🌳 На какое время отпустить динозавра погулять?'

                        item_0 = types.InlineKeyboardButton( text = '10 мин.', callback_data = f"10min_walk_{list(bd_user['dinos'].keys())[0]}")

                        item_1 = types.InlineKeyboardButton( text = '30 мин.', callback_data = f"30min_walk_{list(bd_user['dinos'].keys())[0]}")

                        item_2 = types.InlineKeyboardButton( text = '60 мин.', callback_data = f"60min_walk_{list(bd_user['dinos'].keys())[0]}")

                        item_3 = types.InlineKeyboardButton( text = '90 мин.', callback_data = f"90min_walk_{list(bd_user['dinos'].keys())[0]}")

                    else:
                        text = "🌳 How long should I let the dinosaur go for a walk?"

                        item_0 = types.InlineKeyboardButton( text = '10 min.', callback_data = f"10min_walk_{list(bd_user['dinos'].keys())[0]}")

                        item_1 = types.InlineKeyboardButton( text = '30 min.', callback_data = f"30min_walk_{list(bd_user['dinos'].keys())[0]}")

                        item_2 = types.InlineKeyboardButton( text = '60 min.', callback_data = f"60min_walk_{list(bd_user['dinos'].keys())[0]}")

                        item_3 = types.InlineKeyboardButton( text = '90 min.', callback_data = f"90min_walk_{list(bd_user['dinos'].keys())[0]}")

                    markup_inline.add(item_0, item_1, item_2, item_3)

                    bot.send_message(message.chat.id, text, reply_markup = markup_inline)

        else:
            pass

    if message.text in ['🎑 Позвать', '🎑 Call']:
        bd_user = users.find_one({"userid": user.id})
        if bd_user != None:
            if len(bd_user['dinos']) == 1:
                dino = bd_user['dinos'][ list(bd_user['dinos'].keys())[0] ]
                if dino['activ_status'] == 'walk':
                    if random.randint(1,2) == 1:

                        if user.language_code == 'ru':
                            text = f'🦖 | Вы позвали динозавра и он успешно вернулся!\nВот что произошло пока он гулял:\n'
                            n = 0
                            for el in bd_user['dinos'][ list(bd_user['dinos'].keys())[0] ]['walk_log']:
                                text += f'{n}. {el}\n'

                        else:
                            text = f"🦖 | You called the dinosaur and it successfully returned!\nHere's what happened while he was walking:\n"

                            n = 0
                            for el in bd_user['dinos'][ list(bd_user['dinos'].keys())[0] ]['walk_log']:
                                text += f'{n}. {el}\n'

                        bd_user['dinos'][ list(bd_user['dinos'].keys())[0] ]['activ_status'] = 'pass_active'
                        del bd_user['dinos'][ list(bd_user['dinos'].keys())[0] ]['walk_time']
                        del bd_user['dinos'][ list(bd_user['dinos'].keys())[0] ]['walk_log']

                        users.update_one( {"userid": bd_user['userid']}, {"$set": {'dinos': bd_user['dinos'] }} )

                        bot.send_message(message.chat.id, text, reply_markup = markup('actions', user))


                    else:
                        if user.language_code == 'ru':
                            text = f'🔇 | Ваш голос не слышен динозавру, попробуйте ещё раз!'
                        else:
                            text = f"🔇 | Your voice is not audible to the dinosaur, try again!"

                        bot.send_message(message.chat.id, text , reply_markup = markup('actions', user))



            else:
                pass





@bot.callback_query_handler(func = lambda call: True)
def answer(call):

    if call.data in ['egg_answer_1', 'egg_answer_2', 'egg_answer_3']:
        user = call.from_user
        bd_user = users.find_one({"userid": user.id})

        if 'eggs' in list(bd_user.keys()):
            egg_n = call.data[11:]

            bd_user['dinos'][ user_dino_pn(bd_user) ] = {'status': 'incubation', 'incubation_time': time.time() + 30 * 60, 'egg_id': bd_user['eggs'][int(egg_n)-1]}

            users.update_one( {"userid": user.id}, {"$unset": {'eggs': None}} )
            users.update_one( {"userid": user.id}, {"$set": {'dinos': bd_user['dinos']}} )

            if user.language_code == 'ru':
                text = f'🥚 | Выберите яйцо с динозавром!\n🦖 | Вы выбрали яйцо 🥚{egg_n}!'
                text2 = f'Поздравляем, у вас появился свой первый динозавр!\nВ данный момент яйцо инкубируется, а через 30 минут из него вылупится динозаврик!\nЧтобы посмотреть актуальную информацию о яйце, нажмите кнопку <b>🦖 Динозавр</b>!'
            else:
                text = f'🥚 | Choose a dinosaur egg!\n🦖 | You have chosen an egg 🥚{egg_n}!'
                text2 = f'Congratulations, you have your first dinosaur!\n At the moment the egg is incubating, and after 12 hours a dinosaur will hatch out of it!To view up-to-date information about the egg, click <b>🦖 Dinosaur</b>!'

            bot.edit_message_caption(text, call.message.chat.id, call.message.message_id)
            bot.send_message(call.message.chat.id, text2, parse_mode = 'html', reply_markup = markup(1, user))

    if call.data[:10] in ['90min_walk', '60min_walk', '30min_walk', '10min_walk']:
        user = call.from_user
        bd_user = users.find_one({"userid": user.id})

        bd_user['dinos'][ call.data[11:] ]['activ_status'] = 'walk'
        bd_user['dinos'][ call.data[11:] ]['walk_time'] = time.time() + 60 * int(call.data[:2])
        bd_user['dinos'][ call.data[11:] ]['walk_log'] = []
        users.update_one( {"userid": user.id}, {"$set": {'dinos': bd_user['dinos']}} )

        if user.language_code == 'ru':
            text = f'🎈 | Если у динозавра хорошее настроение, он может принести обратно какие то вещи.\n\n🧶 | Если на прогулке случится какая то неожиданная ситуация, у динозавра может повысится или понизится настроение.'
            text2 = f'🌳 | Вы отправили динозавра в свободную прогулку на {call.data[:2]} минут.'

        else:
            text = f"🎈 | If the dinosaur is in a good mood, he can bring back some things.\n\n🧶 | If some unexpected situation happens on a walk, the dinosaur's mood may rise or fall."
            text2 = f"🌳 | You sent the dinosaur for a free walk for {call.data[:2]} minutes."

        bot.edit_message_text(text2, call.message.chat.id, call.message.message_id)
        bot.send_message(call.message.chat.id, text, parse_mode = 'html', reply_markup = markup("actions", user))



print(f'Бот {bot.get_me().first_name} запущен!')
thr1.start()

bot.infinity_polling()
