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
import sys
from memory_profiler import memory_usage
import pprint


bot = telebot.TeleBot(config.TOKEN)

client = pymongo.MongoClient(config.CLUSTER_TOKEN)
users = client.bot.users

with open('items.json', encoding='utf-8') as f:
    items_f = json.load(f)

with open('dino_data.json', encoding='utf-8') as f:
    json_f = json.load(f)

def dino_pre_answer(message):
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
    user['dinos'][user_dino_pn(user)] = {'dino_id': dino_id, "status": 'dino', 'activ_status': 'pass_active', 'name': dino['name'], 'stats':  {"heal": 100, "eat": random.randint(70, 100), 'game': random.randint(50, 100), 'mood': random.randint(7, 100), "unv": 100}, 'games': []}

    users.update_one( {"userid": user['userid']}, {"$set": {'dinos': user['dinos']}} )


def notifications_manager(notification, user, arg = None):
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
            else:
                text = f'💥 | {chat.first_name}, your dinosaur.... Died...'

            try:
                bot.send_message(user['userid'], text, reply_markup = markup(1, user))
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

def check_memory():
    while True:
        time.sleep(5)
        print(int(memory_usage()[0]), 'mb')

thr2 = threading.Thread(target = check_memory, daemon=True)

def check_incub(): #проверка каждые 5 секунд
    while True:
        nn = 0
        time.sleep(5)
        t_st = int(time.time())

        members = users.find({ })
        for user in members:
            nn += 1
            # try:
            if True:
                dns_l = list(user['dinos'].keys()).copy()

                for dino_id in dns_l:
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

        print(f'Проверка инкубации - {int(time.time()) - t_st}s {nn}u')

thr_icub = threading.Thread(target = check_incub, daemon=True)

def check_sleep(): #проверка каждые 10 секунд
    while True:
        nn = 0
        time.sleep(10)
        t_st = int(time.time())

        members = users.find({ })
        for user in members:
            nn += 1
            # try:
            if True:
                dns_l = list(user['dinos'].keys()).copy()

                for dino_id in dns_l:
                    dino = user['dinos'][dino_id]

                    if dino['status'] == 'dino': #дино

                        if dino['activ_status'] == 'sleep':

                            if user['dinos'][dino_id]['stats']['unv'] < 100:
                                if random.randint(1,45) == 1:
                                    user['dinos'][dino_id]['stats']['unv'] += random.randint(1,2)

                            if user['dinos'][dino_id]['stats']['game'] < 40:
                                if random.randint(1,45) == 1:
                                    user['dinos'][dino_id]['stats']['game'] += random.randint(1,2)

                            if user['dinos'][dino_id]['stats']['mood'] < 50:
                                if random.randint(1,45) == 1:
                                    user['dinos'][dino_id]['stats']['mood'] += random.randint(1,2)

                            if user['dinos'][dino_id]['stats']['heal'] < 100:
                                if user['dinos'][dino_id]['stats']['eat'] > 50:
                                    if random.randint(1,45) == 1:
                                        user['dinos'][dino_id]['stats']['heal'] += random.randint(1,2)
                                        user['dinos'][dino_id]['stats']['eat'] -= random.randint(0,1)

                            if user['dinos'][dino_id]['stats']['unv'] >= 100:
                                user['dinos'][dino_id]['activ_status'] = 'pass_active'
                                notifications_manager("woke_up", user)

                users.update_one( {"userid": user['userid']}, {"$set": {'dinos': user['dinos'] }} )

        print(f'Проверка сна - {int(time.time()) - t_st}s {nn}u')

thr_sleep = threading.Thread(target = check_sleep, daemon=True)

def check_game(): #проверка каждые 10 секунд
    while True:
        nn = 0
        time.sleep(10)
        t_st = int(time.time())

        members = users.find({ })
        for user in members:
            nn += 1
            # try:
            if True:
                dns_l = list(user['dinos'].keys()).copy()

                for dino_id in dns_l:
                    dino = user['dinos'][dino_id]

                    if dino['status'] == 'dino': #дино

                        if dino['activ_status'] == 'game':

                            if random.randint(1, 65) == 1: #unv
                                user['dinos'][dino_id]['stats']['unv'] -= random.randint(0,2)

                            if random.randint(1, 45) == 1: #unv
                                user['lvl'][1] += random.randint(0,20)

                            if user['dinos'][dino_id]['stats']['game'] < 100:
                                if random.randint(1,30) == 1:
                                    user['dinos'][dino_id]['stats']['game'] += int(random.randint(2,15) * user['dinos'][dino_id]['game_%'])

                            if int(dino['game_time']-time.time()) <= 0:
                                user['dinos'][dino_id]['activ_status'] = 'pass_active'
                                notifications_manager("game_end", user)

                                del user['dinos'][ dino_id ]['game_time']
                                del user['dinos'][ dino_id ]['game_%']

                users.update_one( {"userid": user['userid']}, {"$set": {'dinos': user['dinos'] }} )
            users.update_one( {"userid": user['userid']}, {"$set": {'lvl': user['lvl'] }} )

        print(f'Проверка игры - {int(time.time()) - t_st}s {nn}u')

thr_game = threading.Thread(target = check_game, daemon=True)

def check_hunt(): #проверка каждые 10 секунд
    while True:
        nn = 0
        time.sleep(10)
        t_st = int(time.time())

        members = users.find({ })
        for user in members:
            nn += 1
            # try:
            if True:
                dns_l = list(user['dinos'].keys()).copy()

                for dino_id in dns_l:
                    dino = user['dinos'][dino_id]

                    if dino['status'] == 'dino': #дино
                        if dino['activ_status'] == 'hunting':

                            if random.randint(1, 65) == 1: #unv
                                user['dinos'][dino_id]['stats']['unv'] -= random.randint(0,2)

                            if random.randint(1, 45) == 1: #unv
                                user['lvl'][1] += random.randint(0,20)

                            r = random.randint(1, 15)
                            if r == 1:

                                if dino['h_type'] == 'all':
                                    items = [2, 5, 6, 7, 8, 9, 10, 11, 12, 13]

                                if dino['h_type'] == 'collecting':
                                    items = [6, 9, 11]

                                if dino['h_type'] == 'hunting':
                                    items = [5, 8, 12]

                                if dino['h_type'] == 'fishing':
                                    items = [7, 10, 13]

                                item = random.choice(items)
                                i_count = random.randint(1, 2)
                                for i in list(range(i_count)):
                                    user['inventory'].append(str(item))
                                    dino['target'][0] += 1

                                if dino['target'][0] >= dino['target'][1]:
                                    del user['dinos'][ dino_id ]['target']
                                    del user['dinos'][ dino_id ]['h_type']
                                    user['dinos'][dino_id]['activ_status'] = 'pass_active'

                                    notifications_manager("hunting_end", user)

                users.update_one( {"userid": user['userid']}, {"$set": {'dinos': user['dinos'] }} )
            users.update_one( {"userid": user['userid']}, {"$set": {'lvl': user['lvl'] }} )
            users.update_one( {"userid": user['userid']}, {"$set": {'inventory': user['inventory'] }} )

        print(f'Проверка сбора пищи - {int(time.time()) - t_st}s {nn}u')

thr_hunt = threading.Thread(target = check_hunt, daemon=True)

def check_journey(): #проверка каждые 10 секунд
    while True:
        nn = 0
        time.sleep(10)
        t_st = int(time.time())

        members = users.find({ })
        for user in members:
            nn += 1
            # try:
            if True:
                dns_l = list(user['dinos'].keys()).copy()

                for dino_id in dns_l:
                    dino = user['dinos'][dino_id]

                    if dino['status'] == 'dino': #дино

                        if dino['activ_status'] == 'journey':

                            if random.randint(1, 65) == 1: #unv
                                user['dinos'][dino_id]['stats']['unv'] -= random.randint(0,2)

                            if random.randint(1, 45) == 1: #unv
                                user['lvl'][1] += random.randint(0,20)

                            if int(dino['journey_time']-time.time()) <= 0:
                                user['dinos'][dino_id]['activ_status'] = 'pass_active'

                                notifications_manager("journey_end", user, user['dinos'][ dino_id ]['journey_log'])

                                del user['dinos'][ dino_id ]['journey_time']
                                del user['dinos'][ dino_id ]['journey_log']

                            r_e_j = random.randint(1,30)
                            if r_e_j == 1:
                                if random.randint(1,3) != 1:

                                    if dino['stats']['mood'] >= 55:
                                        mood_n = True
                                    else:
                                        mood_n = False

                                    r_event = random.randint(1, 100)
                                    if r_event in list(range(1,51)): #обычное соб
                                        events = ['sunny', 'm_coins']
                                    elif r_event in list(range(51,76)): #необычное соб
                                        events = ['+eat', 'sleep', 'u_coins']
                                    elif r_event in list(range(76,91)): #редкое соб
                                        events = ['random_items', 'b_coins']
                                    elif r_event in list(range(91,100)): #мистическое соб
                                        events = ['random_items_leg', 'y_coins']
                                    else: #легендарное соб
                                        events = ['egg', 'l_coins']

                                    event = random.choice(events)
                                    if event == 'sunny':
                                        mood = random.randint(1, 15)
                                        user['dinos'][dino_id]['stats']['mood'] += mood

                                        if user['language_code'] == 'ru':
                                            event = f'☀ | Солнечно, настроение динозавра повысилось на {mood}%'
                                        else:
                                            event = f"☀ | Sunny, the dinosaur's mood has increased by {mood}%"

                                    elif event == '+eat':
                                        eat = random.randint(1, 10)
                                        user['dinos'][dino_id]['stats']['eat'] += eat

                                        if user['language_code'] == 'ru':
                                            event = f'🥞 | Динозавр нашёл что-то вкусненькое и съел это!'
                                        else:
                                            event = f"🥞 | The dinosaur found something delicious and ate it!"

                                    elif event == 'sleep':
                                        unv = random.randint(1, 5)
                                        user['dinos'][dino_id]['stats']['unv'] += unv

                                        if user['language_code'] == 'ru':
                                            event = f'💭 | Динозавр смог вздремнуть по дороге.'
                                        else:
                                            event = f"💭 | Динозавр смог вздремнуть по дороге."

                                    elif event == 'random_items':
                                        items = ["1", "2", '18', '19', '25', '25']
                                        item = random.choice(items)
                                        if mood_n == True:
                                            user['inventory'].append(item)

                                            if user['language_code'] == 'ru':
                                                event = f"🧸 | Бегая по лесам, динозавр видит что-то похожее на сундук.\n>  Открыв его, он находит: {items_f['items'][item]['nameru']}!"
                                            else:
                                                event = f"🧸 | Running through the woods, the dinosaur sees something that looks like a chest.\n> Opening it, he finds: {items_f['items'][item]['nameen']}!"

                                        if mood_n == False:

                                            if user['language_code'] == 'ru':
                                                event = '❌ | Редкое событие отменено из-за плохого настроения!'
                                            else:
                                                event = '❌ | A rare event has been canceled due to a bad mood!'

                                    elif event == 'random_items_leg':
                                        items = ["4", "13", "14", "15", "16"]
                                        item = random.choice(items)
                                        if mood_n == True:
                                            user['inventory'].append(item)

                                            if user['language_code'] == 'ru':
                                                event = f"🧸 | Бегая по горам, динозавр видит что-то похожее на сундук.\n>  Открыв его, он находит: {items_f['items'][item]['nameru']}!"
                                            else:
                                                event = f"🧸 | Running through the mountains, the dinosaur sees something similar to a chest.\n> Opening it, he finds: {items_f['items'][item]['nameen']}!"

                                        if mood_n == False:

                                            if user['language_code'] == 'ru':
                                                event = '❌ | Мистическое событие отменено из-за плохого настроения!'
                                            else:
                                                event = '❌ | The mystical event has been canceled due to a bad mood!'

                                    elif event == 'egg':
                                        eggs = ["3", '20', '21', '22', '23', '24']
                                        egg = random.choice(eggs)
                                        if mood_n == True:
                                            user['inventory'].append(egg)

                                            if user['language_code'] == 'ru':
                                                event = f"🧸 | Бегая по по пещерам, динозавр видит что-то похожее на сундук.\n>  Открыв его, он находит: {items_f['items'][egg]['nameru']}!"
                                            else:
                                                event = f"🧸 | Running through the caves, the dinosaur sees something similar to a chest.\n> Opening it, he finds: {items_f['items'][egg]['nameen']}!"

                                        if mood_n == False:

                                            if user['language_code'] == 'ru':
                                                event = '❌ | Легендарное событие отменено из-за плохого настроения!'
                                            else:
                                                event = '❌ | The legendary event has been canceled due to a bad mood!'

                                    elif event[2:] == 'coins':

                                        if mood_n == True:
                                            if event[:1] == 'm':
                                                coins = random.randint(1, 10)
                                            if event[:1] == 'u':
                                                coins = random.randint(10, 50)
                                            if event[:1] == 'b':
                                                coins = random.randint(50, 100)
                                            if event[:1] == 'y':
                                                coins = random.randint(100, 300)
                                            if event[:1] == 'l':
                                                coins = random.randint(300, 500)

                                            user['coins'] += coins

                                            if user['language_code'] == 'ru':
                                                event = f'💎 | Ходя по тропинкам, динозавр находит мешочек c монетками.\n>   Вы получили {coins} монет.'
                                            else:
                                                event = f'💎 | Walking along the paths, the dinosaur finds a bag with coins.\n> You have received {coins} coins.'

                                        if mood_n == False:
                                            if user['language_code'] == 'ru':
                                                event = '❌ | Cобытие отменено из-за плохого настроения!'
                                            else:
                                                event = '❌ | Event has been canceled due to a bad mood!'

                                    user['dinos'][ dino_id ]['journey_log'].append(event)

                                else:
                                    if dino['stats']['mood'] >= 55:
                                        mood_n = False
                                    else:
                                        mood_n = True

                                    r_event = random.randint(1, 100)
                                    if r_event in list(range(1,51)): #обычное соб
                                        events = ['rain', 'm_coins']
                                    elif r_event in list(range(51,76)): #необычное соб
                                        events = ['fight', '-eat', 'u_coins']
                                    elif r_event in list(range(76,91)): #редкое соб
                                        events = ['b_coins']
                                    elif r_event in list(range(91,100)): #мистическое соб
                                        events = ['toxic_rain', 'y_coins']
                                    else: #легендарное соб
                                        events = ['lose_item', 'l_coins']


                                    event = random.choice(events)
                                    if event == 'rain':
                                        mood = random.randint(1, 15)
                                        user['dinos'][dino_id]['stats']['mood'] -= mood

                                        if user['language_code'] == 'ru':
                                            event = f'🌨 | Прошёлся дождь, настроение понижено на {mood}%'
                                        else:
                                            event = f"🌨 | It has rained, the mood is lowered by {mood}%"

                                    elif event == '-eat':
                                        eat = random.randint(1, 10)
                                        heal = random.randint(1, 3)
                                        user['dinos'][dino_id]['stats']['eat'] -= eat
                                        user['dinos'][dino_id]['stats']['heal'] -= heal

                                        if user['language_code'] == 'ru':
                                            event = f'🍤 | Динозавр нашёл что-то вкусненькое и съел это, еда оказалась испорчена. Динозавр теряет {eat}% еды и {heal}% здоровья.'
                                        else:
                                            event = f"🍤 | The dinosaur found something delicious and ate it, the food was spoiled. Dinosaur loses {eat}% of food and {heal}% health."

                                    elif event == 'toxic_rain':
                                        heal = random.randint(1, 5)
                                        user['dinos'][dino_id]['stats']['heal'] -= heal

                                        if user['language_code'] == 'ru':
                                            event = f"⛈ | Динозавр попал под токсичный дождь!"
                                        else:
                                            event = f"⛈ | The dinosaur got caught in the toxic rain!"


                                    elif event == 'fight':
                                        unv = random.randint(1, 10)
                                        user['dinos'][dino_id]['stats']['unv'] -= unv

                                        if random.randint(1,2) == 1:
                                            heal = random.randint(1, 5)
                                            user['dinos'][dino_id]['stats']['heal'] -= heal
                                            textru = f'\nДинозавр не смог избежать ран, он теряет {heal}% здоровья.'
                                            texten = f"\nThe dinosaur couldn't escape the wounds, it loses {heal}% health."
                                        else:
                                            textru = f'\nДинозавр смог избежать ран, он не теряет здоровья.'
                                            texten = f"\nThe dinosaur was able to avoid wounds, he does not lose health."

                                        if user['language_code'] == 'ru':
                                            event = f'⚔ | Динозавр нарвался на драку, он теряет {unv}% сил.'
                                            event += textru
                                        else:
                                            event = f"⚔ | The dinosaur ran into a fight, he loses {unv}% of his strength."
                                            event += texten

                                    elif event == 'lose_items':
                                        items = user['inventory']
                                        item = random.choice(items)
                                        if mood_n == True:
                                            user['inventory'].remove(item)

                                            if user['language_code'] == 'ru':
                                                event = f"❗ | Бегая по лесам, динозавр обранил {items_f['items'][item]['nameru']}\n>  Предмет потерян!"
                                            else:
                                                event = f"🧸 | Running through the woods, the dinosaur sees something that looks like a chest.\n> Opening it, he finds: {items_f['items'][item]['nameen']}!"

                                        if mood_n == False:

                                            if user['language_code'] == 'ru':
                                                event = '🍭 | Отрицательное событие отменено из-за хорошего настроения!'
                                            else:
                                                event = '🍭 | Negative event canceled due to good mood!'

                                    elif event[2:] == 'coins':

                                        if mood_n == True:
                                            if event[:1] == 'm':
                                                coins = random.randint(1, 2)
                                            if event[:1] == 'u':
                                                coins = random.randint(5, 10)
                                            if event[:1] == 'b':
                                                coins = random.randint(10, 50)
                                            if event[:1] == 'y':
                                                coins = random.randint(50, 100)
                                            if event[:1] == 'l':
                                                coins = random.randint(100, 150)

                                            user['coins'] += coins

                                            if user['language_code'] == 'ru':
                                                event = f'💎 | Ходя по тропинкам, динозавр обронил несколько монет из рюкзака\n>   Вы потеряли {coins} монет.'
                                            else:
                                                event = f'💎 | Walking along the paths, the dinosaur dropped some coins from his backpack.   You have lost {coins} coins.'

                                        if mood_n == False:
                                            if user['language_code'] == 'ru':
                                                event = '🍭 | Отрицательное событие отменено из-за хорошего настроения!'
                                            else:
                                                event = '🍭 | Negative event canceled due to good mood!'

                                    user['dinos'][ dino_id ]['journey_log'].append(event)

                users.update_one( {"userid": user['userid']}, {"$set": {'dinos': user['dinos'] }} )
            users.update_one( {"userid": user['userid']}, {"$set": {'lvl': user['lvl'] }} )
            users.update_one( {"userid": user['userid']}, {"$set": {'inventory': user['inventory'] }} )
            users.update_one( {"userid": user['userid']}, {"$set": {'coins': user['coins'] }} )

        print(f'Проверка путешествие - {int(time.time()) - t_st}s {nn}u')

thr_journey = threading.Thread(target = check_journey, daemon=True)

def check(): #проверка каждые 10 секунд
    while True:
        nn = 0
        time.sleep(10)
        t_st = int(time.time())

        members = users.find({ })
        for user in members:
            nn += 1
            # try:
            if True:
                dns_l = list(user['dinos'].keys()).copy()

                for dino_id in dns_l:
                    dino = user['dinos'][dino_id]

                    if dino['status'] == 'dino': #дино
                    #stats  - pass_active (ничего) sleep - (сон) journey - (путешествиеф)


                        if dino['activ_status'] != 'sleep':
                            if random.randint(1, 55) == 1: #eat
                                user['dinos'][dino_id]['stats']['eat'] -= random.randint(1,2)
                        else:
                            if random.randint(1, 80) == 1: #eat
                                user['dinos'][dino_id]['stats']['eat'] -= random.randint(1,2)

                        if dino['activ_status'] != 'game':
                            if random.randint(1, 60) == 1: #game
                                user['dinos'][dino_id]['stats']['game'] -= random.randint(1,2)

                        if dino['activ_status'] != 'sleep':
                            if random.randint(1, 130) == 1: #unv
                                user['dinos'][dino_id]['stats']['unv'] -= random.randint(1,2)

                        if dino['activ_status'] == 'pass_active':

                            if user['dinos'][dino_id]['stats']['game'] > 60:
                                if dino['stats']['mood'] < 100:
                                    if random.randint(1,15) == 1:
                                        user['dinos'][dino_id]['stats']['mood'] += random.randint(1,15)

                                    if random.randint(1,60) == 1:
                                        user['coins'] += random.randint(0,100)

                            if user['dinos'][dino_id]['stats']['mood'] > 80:
                                if random.randint(1,60) == 1:
                                    user['coins'] += random.randint(0,100)

                            if user['dinos'][dino_id]['stats']['unv'] <= 20 and user['dinos'][dino_id]['stats']['unv'] != 0:
                                if dino['stats']['mood'] > 0:
                                    if random.randint(1,30) == 1:
                                        user['dinos'][dino_id]['stats']['mood'] -= random.randint(1,2)

                        if user['dinos'][dino_id]['stats']['game'] < 40 and user['dinos'][dino_id]['stats']['game'] > 10:
                            if dino['stats']['mood'] > 0:
                                if random.randint(1,30) == 1:
                                    user['dinos'][dino_id]['stats']['mood'] -= random.randint(1,2)

                        if user['dinos'][dino_id]['stats']['game'] < 10:
                            if dino['stats']['mood'] > 0:
                                if random.randint(1,15) == 1:
                                    user['dinos'][dino_id]['stats']['mood'] -= 3

                        if user['dinos'][dino_id]['stats']['unv'] <= 10 and user['dinos'][dino_id]['stats']['eat'] <= 20:
                            if random.randint(1,30) == 1:
                                user['dinos'][dino_id]['stats']['heal'] -= random.randint(1,2)

                        if user['dinos'][dino_id]['stats']['eat'] <= 20:
                            if user['dinos'][dino_id]['stats']['unv'] <= 10 and user['dinos'][dino_id]['stats']['eat'] <= 20:
                                pass
                            else:
                                if random.randint(1,40) == 1:
                                    user['dinos'][dino_id]['stats']['heal'] -= random.randint(0,1)

                        if user['dinos'][dino_id]['stats']['eat'] > 80:
                            if dino['stats']['mood'] < 100:
                                if random.randint(1,15) == 1:
                                    user['dinos'][dino_id]['stats']['mood'] += random.randint(1,10)

                        if user['dinos'][dino_id]['stats']['eat'] <= 40 and user['dinos'][dino_id]['stats']['eat'] != 0:
                            if dino['stats']['mood'] > 0:
                                if random.randint(1,30) == 1:
                                    user['dinos'][dino_id]['stats']['mood'] -= random.randint(1,2)


                        if user['dinos'][dino_id]['stats']['eat'] > 80 and user['dinos'][dino_id]['stats']['unv'] > 70 and user['dinos'][dino_id]['stats']['mood'] > 50:

                            if random.randint(1,6) == 1:
                                user['dinos'][dino_id]['stats']['heal'] += random.randint(1,4)
                                user['dinos'][dino_id]['stats']['eat'] -= random.randint(0,1)


                        if user['dinos'][dino_id]['stats']['unv'] >= 100:
                            user['dinos'][dino_id]['stats']['unv'] = 100

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

                        if user['dinos'][dino_id]['stats']['game'] < 0:
                            user['dinos'][dino_id]['stats']['game'] = 0

                        if user['dinos'][dino_id]['stats']['game'] <= 50:
                            if 'need_game' not in list(user['notifications'].keys()) or user['notifications']['need_game'] == False:
                                notifications_manager("need_game", user, user['dinos'][dino_id]['stats']['game'])

                        if user['dinos'][dino_id]['stats']['mood'] < 0:
                            user['dinos'][dino_id]['stats']['mood'] = 0

                        if user['dinos'][dino_id]['stats']['mood'] <= 70:
                            if 'need_mood' not in list(user['notifications'].keys()) or user['notifications']['need_mood'] == False:
                                notifications_manager("need_mood", user, user['dinos'][dino_id]['stats']['mood'])

                        if user['dinos'][dino_id]['stats']['heal'] <= 0:
                            user['dinos'][dino_id]['stats']['heal'] = 0
                            del user['dinos'][dino_id]

                            if 'dead' not in list(user['notifications'].keys()) or user['notifications']['dead'] == False:
                                notifications_manager("dead", user)


                        users.update_one( {"userid": user['userid']}, {"$set": {'dinos': user['dinos'] }} )
                        users.update_one( {"userid": user['userid']}, {"$set": {'coins': user['coins'] }} )

                        expp = 5 * user['lvl'][0] * user['lvl'][0] + 50 * user['lvl'][0] + 100
                        if user['lvl'][1] >= expp:
                            user['lvl'][0] += 1
                            user['lvl'][1] = user['lvl'][1] - expp

                        users.update_one( {"userid": user['userid']}, {"$set": {'lvl': user['lvl'] }} )
            # except:
            #     pass

        print(f'Проверка - {int(time.time()) - t_st}s {nn}u')

thr1 = threading.Thread(target = check, daemon=True)


def markup(element = 1, user = None):
    if type(user) == int:
        userid = user
    else:
        userid = user.id

    markup = types.ReplyKeyboardMarkup(resize_keyboard = True)
    bd_user = users.find_one({"userid": userid})

    if bd_user != None and len(bd_user['dinos']) == 0 and 'dead' in bd_user['notifications'] and bd_user['notifications']['dead'] == True:

        if bd_user['language_code'] == 'ru':
            nl = "🧩 Проект: Возрождение"
        else:
            nl = '🧩 Project: Rebirth'

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

        if bd_user['language_code'] == 'ru':
            nl = ['❗ Уведомления', "👅 Язык", '💬 Переименовать', '↪ Назад']

        else:
            nl = ['❗ Notifications', "👅 Language", '💬 Rename', '↪ Back']

        item1 = types.KeyboardButton(nl[0])
        item2 = types.KeyboardButton(nl[1])
        item3 = types.KeyboardButton(nl[2])
        item4 = types.KeyboardButton(nl[3])

        markup.add(item1, item2, item3, item4)

    elif element == "friends-menu" and bd_user != None:

        if bd_user['language_code'] == 'ru':
            nl = ["➕ Добавить", '📜 Список', '➖ Удалить', '💌 Запросы', '↪ Назад']

        else:
            nl = ["➕ Add", '📜 List', '➖ Delete', '💌 Inquiries', '↪ Back']

        item1 = types.KeyboardButton(nl[0])
        item2 = types.KeyboardButton(nl[1])
        item3 = types.KeyboardButton(nl[2])
        item4 = types.KeyboardButton(nl[3])
        item5 = types.KeyboardButton(nl[4])

        markup.add(item1, item2, item3, item4, item5)

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
            nl = ['📜 Информация', '🎮 Инвентарь', '🎢 Рейтинг', '↪ Назад']

        else:
            nl = ['📜 Information', '🎮 Inventory', '🎢 Rating', '↪ Back']

        item1 = types.KeyboardButton(nl[0])
        item2 = types.KeyboardButton(nl[1])
        item3 = types.KeyboardButton(nl[2])
        item4 = types.KeyboardButton(nl[3])

        markup.add(item1, item2, item3, item4)


    else:
        print(f'{element}\n{user}')

    return markup

def member_profile(mem_id, lang):
    try:
        user = bot.get_chat(int(mem_id))
        bd_user = users.find_one({"userid": user.id})
        expp = 5 * bd_user['lvl'][0] * bd_user['lvl'][0] + 50 * bd_user['lvl'][0] + 100
        n_d = len(list(bd_user['dinos']))
        t_dinos = ''
        for k in bd_user['dinos']:

            if list( bd_user['dinos']) [ len(bd_user['dinos']) - 1 ] == k:
                n = '└'

            else:
                n = '├'

            i = bd_user['dinos'][k]
            stat = i['activ_status']
            if lang == 'ru':

                if i['activ_status'] == 'pass_active':
                    stat = 'ничего не делает'
                elif i['activ_status'] == 'sleep':
                    stat = 'спит'
                elif i['activ_status'] == 'game':
                    stat = 'играет'
                elif i['activ_status'] == 'hunting':
                    stat = 'собирает еду'
                elif i['activ_status'] == 'journey':
                    stat = 'путешествует'

                dino = json_f['elements'][str(i['dino_id'])]
                pre_qual = dino['image'][5:8]
                qual = ''
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

                t_dinos += f"\n   *{n}* {i['name']}\n      *├* Статус: {stat}\n      *└* Редкость: {qual}\n"

            else:

                if i['activ_status'] == 'pass_active':
                    stat = 'does nothing'
                elif i['activ_status'] == 'sleep':
                    stat = 'sleeping'
                elif i['activ_status'] == 'game':
                    stat = 'is playing'
                elif i['activ_status'] == 'hunting':
                    stat = 'collects food'
                elif i['activ_status'] == 'journey':
                    stat = 'travels'

                t_dinos += f"\n   *{n}* {i['name']}\n      *└* Status: {stat}\n"

        if lang == 'ru':
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
            text += f'\n\n'
            text += f"*┌* *👥 Друзья*\n"
            text += f"*└* Количество: {len(bd_user['friends']['friends_list'])}"
            text += f'\n\n'
            text += f"*┌* *🎈 Инвентарь*\n"
            text += f"*└* Предметов: {len(bd_user['inventory'])}"

        else:
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
            text += f'\n\n'
            text += f"*┌**👥 Friends*\n"
            text += f"*└* Quantity: {len(bd_user['friends']['friends_list'])}"
            text += f'\n\n'
            text += f"*┌* *🎈 Inventory*\n"
            text += f"*└* Items: {len(bd_user['inventory'])}"
    except:
        text = 'KMk456 jr5uhsd7489 lkjs47609485\n               ERRoR'

    return text

@bot.message_handler(commands=['emulate_not'])
def command(message):
    print('emulate_not')
    time.sleep(60)
    user = message.from_user
    bd_user = users.find_one({"userid": user.id})
    notifications_manager(message.text[13:][:-3], bd_user, message.text[-2:])

@bot.message_handler(commands=['start', 'main-menu'])
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

    print(user.first_name, message.text)

    def trans_paste(fg_img,bg_img,alpha=10,box=(0,0)):
        fg_img_trans = Image.new("RGBA",fg_img.size)
        fg_img_trans = Image.blend(fg_img_trans,fg_img,alpha)
        bg_img.paste(fg_img_trans,box,fg_img_trans)
        return bg_img


    if users.find_one({"userid": user.id}) != None:
        bd_user = users.find_one({"userid": user.id})
        bd_user['last_m'] = int(time.time())
        users.update_one( {"userid": bd_user['userid']}, {"$set": {'last_m': bd_user['last_m'] }} )

    if message.chat.type == 'private':

        if users.find_one({"userid": user.id}) != None and bot.get_chat_member(-1001673242031, user.id).status == 'left':
            bd_user = users.find_one({"userid": user.id})
            r = bot.get_chat_member(-1001673242031, user.id)

            if bd_user['language_code'] == 'ru':
                text = f'📜 | Уважаемый пользователь!\n\n*•* Для получения новостей и важных уведомлений по поводу бота, мы просим вас подписаться на телеграм канал бота!\n\n🔴 | Нажмите на кнопку *"Подписаться"* для перехода в канал, а после на кнопку *"Проверить"*, для продолжения работы!'
                b1 = "🦖 | Подписаться"
                b2 = "🔄 | Проверить"
            else:
                text = f"📜 | Dear user!\n\n*•* To receive news and important notifications about the bot, we ask you to subscribe to the bot's telegram channel!\n\n🔴 | Click on the *'Subscribe'* button to go to the channel, and then on the *'Check'*, to continue working!"
                b1 = "🦖 | Subscribe"
                b2 = "🔄 | Check"

            markup_inline = types.InlineKeyboardMarkup()
            markup_inline.add( types.InlineKeyboardButton(text= b1, url="https://t.me/DinoGochi"))
            markup_inline.add( types.InlineKeyboardButton(text= b2, callback_data = 'checking_the_user_in_the_channel') )

            bot.reply_to(message, text, reply_markup = markup_inline, parse_mode="Markdown")


        else:

            if message.text in ['🍡 Начать играть', '🍡 Start playing']:
                if users.find_one({"userid": user.id}) == None:

                    bd_user = users.find_one({"userid": user.id})
                    try:
                        r = bot.get_chat_member(-1001673242031, user.id)
                    except:
                        return

                    if r.status == 'left':

                        if user.language_code == 'ru':
                            text = f'📜 | Уважаемый пользователь!\n\n*•* Для получения новостей и важных уведомлений по поводу бота, мы просим вас подписаться на телеграм канал бота!\n\n🔴 | Нажмите на кнопку *"Подписаться"* для перехода в канал, а после на кнопку *"Проверить"*, для продолжения работы!'
                            b1 = "🦖 | Подписаться"
                            b2 = "🔄 | Проверить"
                        else:
                            text = f"📜 | Dear user!\n\n*•* To receive news and important notifications about the bot, we ask you to subscribe to the bot's telegram channel!\n\n🔴 | Click on the *'Subscribe'* button to go to the channel, and then on the *'Check'*, to continue working!"
                            b1 = "🦖 | Subscribe"
                            b2 = "🔄 | Check"

                        markup_inline = types.InlineKeyboardMarkup()
                        markup_inline.add( types.InlineKeyboardButton(text= b1, url="https://t.me/DinoGochi"))
                        markup_inline.add( types.InlineKeyboardButton(text= b2, callback_data = 'start') )

                        bot.reply_to(message, text, reply_markup = markup_inline, parse_mode="Markdown")

                    else:

                        if user.language_code == 'ru':
                            text = f'🎍 | Захватывающий мир приключений ждёт, ты готов стать владельцем динозавра и сразиться в рейтинге с другими пользователями?!\n\nЕсли да, то скорее нажимай на кнопку снизу!'
                            b1 = "🎋 | Начать!"
                        else:
                            text = f"🎍 | An exciting world of adventures awaits, are you ready to become the owner of a dinosaur and compete in the ranking with other users?!\n\nIf yes, then rather press the button from below!"
                            b1 = "🎋 | Start!"


                        markup_inline = types.InlineKeyboardMarkup()
                        markup_inline.add( types.InlineKeyboardButton(text= b1, callback_data = 'start') )

                        bot.reply_to(message, text, reply_markup = markup_inline, parse_mode="Markdown")


            if message.text in ["🧩 Проект: Возрождение", '🧩 Project: Rebirth']:
                bd_user = users.find_one({"userid": user.id})
                if bd_user != None:

                    if bd_user['language_code'] == 'ru':
                        text =  f"К вам подходит человек в чёрном одеянии.\n\n"
                        text += f"Вы видите, что у человека чёрные волосы и какой-то шрам на щеке, но его глаза не видны в тени шляпы.\n\n"
                        text += f"*Личность:* - Здраствуйте, меня зовут { random.choice( ['мистер', 'доктор'] ) } { random.choice( ['Джеймс', 'Роберт', 'Винсент', 'Альберт'] ) }, а вас...\n\n"
                        text += f"*Вы:* - ... {user.first_name}, {user.first_name} {user.last_name}, так меня зовут\n\n"
                        text += f"*Личность:* - Прекрасно {user.first_name}, давно вы в нашем бизнесе? _улыбается_\n\n"
                        text += f"*Вы:* - ...Что? Бизнес? О чем, вы говорите?!\n\n"
                        text += f"*Личность:* - Понятно, понятно... Так и запишем. _Записывает что-то в блокнот_\n\n"
                        text += f"*Вы:* - ...\n\n"
                        text += f"*Личность:* - Давайте ближе к делу, мы предлагаем вам заключить с нами контракт, мы получаем ваши монеты и ресурсы, вы получаете яйцо с динозавром.\n\n"
                        text += f"*Вы:* - Яяя, я не знаю...\n\n"
                        text += f"*Вы:* - \n\n"
                        text += f"❓ | Выберите вариант ответа"
                        b1 = ['❓ | Кто вы такой?', '❓ | Это законно?', '❓ | Кто "мы"?', '🧩 | У меня же нет выбора, так?']
                    else:
                        text = f"A man in a black robe approaches you.\n\n"
                        text += f"You can see that the man has black hair and some kind of scar on his cheek, but his eyes are not visible in the shadow of the hat.\n\n"
                        text += f"*Personality:* - Hello, my name is { random.choice(['mister', 'doctor'] ) } { random.choice( ['James', 'Robert', 'Vincent', 'Albert'] ) }, and you...\n\n"
                        text += f"*You are:* - ... {user.first_name}, {user.first_name} {user.last_name}, that's my name\n\n"
                        text += f"*Personality:* - Fine {user.first_name}, how long have you been in our business? _ulybaet_\n\n"
                        text += f"*You are:* - ...What? Business? What are you talking about?!\n\n"
                        text += f"*Personality:* - I see, I see... So we'll write it down. _ Writes something in notepad_\n\n"
                        text += f"*You are:* - ...\n\n"
                        text += f"*Personality:* - Let's get down to business, we offer you to sign a contract with us, we get your coins and resources, you get an egg with a dinosaur.\n\n"
                        text += f"*You:* - I know, I don't know...\n\n"
                        text += f"*You:* - \n\n"
                        text += f"❓ | Choose the answer option'"
                        b1 = ['❓ | Who are you?', '❓ | Is it legal?', '❓ | Who are "we"?', "🧩 | I don't have a choice, right?"]

                    markup_inline = types.InlineKeyboardMarkup()
                    markup_inline.add( types.InlineKeyboardButton(text= b1[0], callback_data = 'dead_answer1') )
                    markup_inline.add( types.InlineKeyboardButton(text= b1[1], callback_data = 'dead_answer2') )
                    markup_inline.add( types.InlineKeyboardButton(text= b1[2], callback_data = 'dead_answer3') )
                    markup_inline.add( types.InlineKeyboardButton(text= b1[3], callback_data = 'dead_answer4') )

                    bot.reply_to(message, text, reply_markup = markup_inline, parse_mode="Markdown")

            if message.text in ['🦖 Динозавр', '🦖 Dinosaur']:
                bd_user = users.find_one({"userid": user.id})
                if bd_user != None:

                    def egg_profile(bd_user, user, bd_dino):
                        egg_id = bd_dino['egg_id']

                        if bd_user['language_code'] == 'ru':
                            lang = bd_user['language_code']
                        else:
                            lang = 'en'

                        t_incub = bd_dino['incubation_time'] - time.time()
                        if t_incub < 0:
                            t_incub = 0

                        time_end = functions.time_end(t_incub, True)
                        if len(time_end) >= 18:
                            time_end = time_end[:-6]

                        bg_p = Image.open(f"images/remain/egg_profile_{lang}.png")
                        egg = Image.open("images/" + str(json_f['elements'][egg_id]['image']))
                        egg = egg.resize((290, 290), Image.ANTIALIAS)

                        img = trans_paste(egg, bg_p, 1.0, (-50, 40))

                        idraw = ImageDraw.Draw(img)
                        line1 = ImageFont.truetype("fonts/Comic Sans MS.ttf", size = 35)

                        idraw.text((430, 220), time_end, font = line1)

                        img.save('profile.png')
                        profile = open(f"profile.png", 'rb')

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

                        class_ = dino['image'][5:8]

                        panel_i = Image.open(f"images/remain/{class_}_profile_{lang}.png")

                        img = trans_paste(panel_i, bg_p, 1.0)

                        dino_image = Image.open("images/"+str(json_f['elements'][dino_id]['image']))

                        sz = 412
                        dino_image = dino_image.resize((sz, sz), Image.ANTIALIAS)

                        xy = -80
                        x2 = 80
                        img = trans_paste(dino_image, img, 1.0, (xy + x2, xy, sz + xy + x2, sz + xy ))


                        idraw = ImageDraw.Draw(img)
                        line1 = ImageFont.truetype("fonts/Comic Sans MS.ttf", size = 35)

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

                    elif len(bd_user['dinos'].keys()) > 0:

                        def p_profile(message, bd_dino, user, bd_user, dino_user_id):

                            if bd_dino['status'] == 'incubation':

                                profile, time_end  = egg_profile(bd_user, user, bd_dino)
                                if bd_user['language_code'] == 'ru':
                                    text = f'🥚 | Яйцо инкубируется, осталось: {time_end}'
                                else:
                                    text = f'🥚 | The egg is incubated, left: {time_end}'

                                bot.send_photo(message.chat.id, profile, text, reply_markup = markup(user = user))

                            if bd_dino['status'] == 'dino':

                                for i in bd_user['dinos'].keys():
                                    if bd_user['dinos'][i] == bd_dino:
                                        dino_user_id = i

                                profile = dino_profile(bd_user, user, dino_user_id = dino_user_id )

                                if bd_user['language_code'] == 'ru':
                                    st_t = bd_dino['activ_status']

                                    dino = json_f['elements'][str(bd_dino['dino_id'])]
                                    pre_qual = dino['image'][5:8]
                                    qual = ''
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

                                    if bd_dino['activ_status'] == 'pass_active':
                                        st_t = 'ничего не делает 💭'
                                    elif bd_dino['activ_status'] == 'sleep':
                                        st_t = 'спит 🌙'
                                    elif bd_dino['activ_status'] == 'game':
                                        st_t = 'играет 🎮'
                                    elif bd_dino['activ_status'] == 'journey':
                                        st_t = 'путешествует 🎴'
                                    elif bd_dino['activ_status'] in ['hunt', 'hunting']:
                                        st_t = 'сбор пищи 🥞'

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


                                    text = f'🦖 | Имя: {bd_dino["name"]}\n👁‍🗨 | Статус: {st_t}\n🧿 | Редкость: {qual}\n\n{h_text}\n{e_text}\n{g_text}\n{m_text}\n{u_text}'

                                    if bd_dino['activ_status'] == 'journey':
                                        w_t = bd_dino['journey_time'] - time.time()
                                        if w_t < 0:
                                            w_t = 0
                                        text += f"\n\n🌳 | Путешествие: \n·  Осталось: { functions.time_end(w_t) }"
                                else:

                                    dino = json_f['elements'][str(bd_dino['dino_id'])]
                                    pre_qual = dino['image'][5:8]
                                    qual = ''
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
                                        st_t = 'does nothing 💭'
                                    elif bd_dino['activ_status'] == 'sleep':
                                        st_t = 'sleeping 🌙'
                                    elif bd_dino['activ_status'] == 'game':
                                        st_t = 'playing 🎮'
                                    elif bd_dino['activ_status'] == 'journey':
                                        st_t = 'travels 🎴'
                                    elif bd_dino['activ_status'] == 'hunt':
                                        st_t = 'collecting food 🥞'

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

                                    text = f'🦖 | Name: {bd_dino["name"]}\n👁‍🗨 | Status: {st_t}\n🧿 | Rare: {qual}\n\n{h_text}\n{e_text}\n{g_text}\n{m_text}\n{u_text}'

                                    if bd_dino['activ_status'] == 'journey':
                                        w_t = bd_dino['journey_time'] - time.time()
                                        if w_t < 0:
                                            w_t = 0
                                        text += f"\n\n🌳 | Journey: \n·  Left: { functions.time_end(w_t, True) }"

                                bot.send_photo(message.chat.id, profile, text, reply_markup = markup(user = user) )

                        n_dp, dp_a = dino_pre_answer(message)
                        if n_dp == 1:

                            bot.send_message(message.chat.id, f'❌', reply_markup = markup(1, user))
                            return

                        if n_dp == 2:
                            bd_dino = dp_a
                            try:
                                p_profile(message, bd_dino, user, bd_user, list(bd_user['dinos'].keys())[0])
                            except:
                                print('Ошибка в профиле')

                        if n_dp == 3:
                            rmk = dp_a[0]
                            text = dp_a[1]
                            dino_dict = dp_a[2]

                            def ret(message, dino_dict, user, bd_user):
                                try:
                                    p_profile(message, dino_dict[message.text][0], user, bd_user, dino_dict[message.text][1])
                                except:
                                    print('Ошибка в профиле')

                            msg = bot.send_message(message.chat.id, text, reply_markup = rmk)
                            bot.register_next_step_handler(msg, ret, dino_dict, user, bd_user)



            if message.text in ['🔧 Настройки', '🔧 Settings']:
                bd_user = users.find_one({"userid": user.id})

                if bd_user != None:

                    if bd_user['language_code'] == 'ru':
                        text = '🔧 Меню настроек активировано'
                    else:
                        text = '🔧 The settings menu is activated'


                    bot.send_message(message.chat.id, text, reply_markup = markup('settings', user))

            if message.text in ['↪ Назад', '↪ Back']:
                bd_user = users.find_one({"userid": user.id})
                if bd_user != None:

                    if bd_user['language_code'] == 'ru':
                        text = '↪ Возврат в главное меню'
                    else:
                        text = '↪ Return to the main menu'

                    bot.send_message(message.chat.id, text, reply_markup = markup(1, user))

            if message.text in ['👥 Друзья', '👥 Friends']:
                bd_user = users.find_one({"userid": user.id})
                if bd_user != None:

                    if bd_user['language_code'] == 'ru':
                        text = '👥 | Перенаправление в меню друзей!'
                    else:
                        text = '👥 | Redirecting to the friends menu!'

                    bot.send_message(message.chat.id, text, reply_markup = markup("friends-menu", user))

            if message.text in ['❗ FAQ']:
                bd_user = users.find_one({"userid": user.id})
                if bd_user != None:

                    if bd_user['language_code'] == 'ru':
                        text2  = '*❗ FAQ*\n\n'
                        text2 += "*┌* *Редкости 🎈*\n\n"
                        text2 += "*├* События и динозавры делятся на редкости.\nЧем больше редкость, тем слаще награда.\n\n"
                        text2 += "*├*  1. Обычная - 50%\n*├*  2. Необычная - 25%\n*├*  3. Редкая - 15%\n*├*  4. Мистическая - 9%\n*└*  5. Легендарная - 1%\n\n"
                        text2 += "*┌* *Взаимодейтвия 🕹*\n\n"
                        text2 += "*├* Для взаимодействия с динозарвом передите в `🕹 Действия`.\n\n"
                        text2 += "*├*  1. Для того что бы покормить динозавра, вам требуется добыть пищу, нажмите на `🕹 Действия` > `🍕 Сбор пищи` и следуйте инструкциям.\n\n"
                        text2 += "*├*  2. Для того чтобы покормить динозавра нажмите на `🕹 Действия` > `🍣 Покормить` и выберите подходящую пищу.\n\n"
                        text2 += "*├*  3. Для повышения настроения динозавра треубется времени от времени развлекать динозавра. Перейдите `🕹 Действия` > `🎮 Развлечения` и следуйте указаниям.\n\n"
                        text2 += "*├*  4. Чтобы возобновить силы динозавра, отправляйте его спать, `🕹 Действия` > `🌙 Уложить спать`\n\n"
                        text2 += "*└*  5. Для повышения настроения, требуется держать потребность в еде, игры, сна в норме.\n\n"
                        text2 += "*┌* *Профиль 🎮*\n"
                        text2 += "*└*  Чтобы посмотреть инвентарь или узнать свою статистику, перейдите в `👁‍🗨 Профиль`\n\n"
                        text2 += "*┌* *Настройки 🔧*\n\n"
                        text2 += "*└*  В настройках вы можете переименовать динозавра, отключить уведомления или переключить язык.\n\n"
                    else:
                        text2  = '*❗ FAQ*\n\n'
                        text2 += "*┌* *Rarities 🎈*\n\n"
                        text2 += "*├* Events and dinosaurs are divided into rarities.The greater the rarity, the sweeter the reward.\n\n"
                        text2 += "*├* 1. Normal - 50%\n*├* 2. Unusual - 25%\n*├* 3. Rare - 15%\n*├* 4. Mystical - 9%\n*└* 5. Legendary - 1%\n\n"
                        text2 += "*┌* *Interaction 🕹*\n\n"
                        text2 += "*├* To interact with dinozarv, pass in `🕹 Actions`.\n\n"
                        text2 += "*├* 1. In order to feed the dinosaur, you need to get food, click on `🕹 Actions` > `🍕 Food Collection` and follow the instructions.\n\n"
                        text2 += "*├*  2. To feed the dinosaur, click on `🕹 Actions` > `🍣 Feed` and choose the appropriate food.\n\n"
                        text2 += "*├* 3. To improve the mood of the dinosaur, it is necessary to entertain the dinosaur from time to time. Go to `🕹 Actions` > `🎮 Entertainment` and follow the instructions.\n\n"
                        text2 += "*├* 4. To renew the dinosaur's powers, send it to sleep, `🕹 Action` > `🌙 Put to bed`\n\n"
                        text2 += "*└* 5. To improve mood, it is required to keep the need for iodine, games, sleep normal.\n\n"
                        text2 += "*┌* *Profile 🎮*\n"
                        text2 += "*└* To view inventory or find out your statistics, go to `👁 Profile`\n\n"
                        text2 += "*┌* *Settings 🔧*\n\n"
                        text2 += "*└*  In the settings, you can rename the dinosaur, disable notifications, or switch the language.\n\n"

                    bot.send_message(message.chat.id, text2, parse_mode = 'Markdown')


            if message.text in ['❗ Notifications', '❗ Уведомления']:
                bd_user = users.find_one({"userid": user.id})
                if bd_user != None:

                    if bd_user['language_code'] == 'ru':
                        ans = ['✅ Включить', '❌ Выключить', '↪ Назад']
                        text = '❗ Взаимодействие с настройкой уведомлений, выберите активность уведомлений >'
                    else:
                        ans = ['✅ Enable', '❌ Disable', '↪ Back']
                        text = '❗ Interaction with notification settings, select notification activity >'

                    rmk = types.ReplyKeyboardMarkup(resize_keyboard = True)
                    rmk.add(ans[0], ans[1])
                    rmk.add(ans[2])

                    def ret(message, ans, bd_user):

                        if message.text not in ans or message.text == ans[2]:
                            res = None
                        else:
                            res = message.text

                        if res == None:
                            bot.send_message(message.chat.id, f'❌', reply_markup = markup('settings', user))
                            return

                        if res in ['✅ Enable', '✅ Включить']:

                            bd_user['settings']['notifications'] = True
                            users.update_one( {"userid": bd_user['userid']}, {"$set": {'settings': bd_user['settings'] }} )

                            if bd_user['language_code'] == 'ru':
                                text = '🔧 Уведомления были активированы!'
                            else:
                                text = '🔧 Notifications have been activated!'

                            bot.send_message(message.chat.id, text, reply_markup = markup("settings", user))

                        if res in ['❌ Disable', '❌ Выключить']:

                            bd_user['settings']['notifications'] = False
                            users.update_one( {"userid": bd_user['userid']}, {"$set": {'settings': bd_user['settings'] }} )

                            if bd_user['language_code'] == 'ru':
                                text = '🔧 Уведомления были отключены!'
                            else:
                                text = '🔧 Notifications have been disabled!'

                            bot.send_message(message.chat.id, text, reply_markup = markup("settings", user))

                        else:
                            return

                    msg = bot.send_message(message.chat.id, text, reply_markup = rmk)
                    bot.register_next_step_handler(msg, ret, ans, bd_user)

            if message.text in ["👅 Язык", "👅 Language"]:
                bd_user = users.find_one({"userid": user.id})
                if bd_user != None:

                    if bd_user['language_code'] == 'ru':
                        ans = ['🇬🇧 English', '🇷🇺 Русский', '↪ Назад']
                        text = '❗ Взаимодействие с настройкой языка, выберите язык >'
                    else:
                        ans = ['🇬🇧 English', '🇷🇺 Русский', '↪ Back']
                        text = '❗ Interaction with the language setting, select the language >'

                    rmk = types.ReplyKeyboardMarkup(resize_keyboard = True)
                    rmk.add(ans[0], ans[1])
                    rmk.add(ans[2])

                    def ret(message, ans, bd_user):

                        if message.text not in ans or message.text == ans[2]:
                            res = None
                        else:
                            res = message.text

                        if res == None:
                            bot.send_message(message.chat.id, f'❌', reply_markup = markup('settings', user))
                            return

                        if res == ans[0]:
                            users.update_one( {"userid": bd_user['userid']}, {"$set": {'language_code': 'en' }} )
                        if res == ans[1]:
                            users.update_one( {"userid": bd_user['userid']}, {"$set": {'language_code': 'ru' }} )
                        bd_user = users.find_one({"userid": user.id})

                        if bd_user['language_code'] == 'ru':
                            text = '🔧 Язык установлен на 🇷🇺 Русский!'
                        else:
                            text = '🔧 The language is set to 🇬🇧 English!'

                        bot.send_message(message.chat.id, text, reply_markup = markup("settings", user))

                    msg = bot.send_message(message.chat.id, text, reply_markup = rmk)
                    bot.register_next_step_handler(msg, ret, ans, bd_user)

            if message.text in ["➕ Добавить", "➕ Add"]:
                bd_user = users.find_one({"userid": user.id})
                if bd_user != None:

                    if bd_user['language_code'] == 'ru':
                        ans = ['↪ Назад']
                        text = '➡ | Перешлите мне любое сообщение от человека, с которым вы хотите стать друзьями.\nВажно! Ваш друг должен быть зарегистрирован в боте!'
                    else:
                        ans = ['↪ Back']
                        text = '➡ | Forward me any message from the person you want to become friends with.\nImportant! Your friend must be registered in the bot!'

                    rmk = types.ReplyKeyboardMarkup(resize_keyboard = True)
                    rmk.add(ans[0])

                    def ret(message, ans, bd_user):
                        res = message
                        if res.text == ans[0] or res.forward_from == None:
                            bot.send_message(message.chat.id, f'❌', reply_markup = markup('friends-menu', user))

                        else:
                            two_user = users.find_one({"userid": res.forward_from.id})
                            if two_user == None:
                                bot.send_message(message.chat.id, f'❌', reply_markup = markup('friends-menu', user))

                            if two_user == bd_user:
                                bot.send_message(message.chat.id, f'❌', reply_markup = markup('friends-menu', user))

                            else:

                                if 'friends_list' not in bd_user['friends']:
                                    bd_user['friends']['friends_list'] = []
                                    bd_user['friends']['requests'] = []
                                    users.update_one( {"userid": bd_user['userid']}, {"$set": {'friends': bd_user['friends'] }} )

                                if 'friends_list' not in two_user['friends']:
                                    two_user['friends']['friends_list'] = []
                                    two_user['friends']['requests'] = []
                                    users.update_one( {"userid": two_user['userid']}, {"$set": {'friends': two_user['friends'] }} )

                                if bd_user['userid'] not in two_user['friends']['requests'] and bd_user['userid'] not in bd_user['friends']['friends_list']:

                                    two_user['friends']['requests'].append(bd_user['userid'])
                                    users.update_one( {"userid": two_user['userid']}, {"$set": {'friends': two_user['friends'] }} )

                                    bot.send_message(message.chat.id, f'✔', reply_markup = markup('friends-menu', user))
                                    notifications_manager('friend_request', two_user)

                                else:

                                    if bd_user['language_code'] == 'ru':
                                        text = f"📜 | Данный пользователь уже в друзьях / получил запрос от вас!"

                                    else:
                                        text = f"📜 | This user is already a friend / has received a request from you!"

                                    bot.send_message(message.chat.id, text, reply_markup = markup('friends-menu', user))

                    msg = bot.send_message(message.chat.id, text, reply_markup = rmk)
                    bot.register_next_step_handler(msg, ret, ans, bd_user)

            if message.text in ["📜 Список", "📜 List"]:
                bd_user = users.find_one({"userid": user.id})
                if bd_user != None:

                    def chunks(lst, n):
                        for i in range(0, len(lst), n):
                            yield lst[i:i + n]

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

                    friends_chunks = list(chunks(list(chunks(friends_name, 2)), 3))

                    def work_pr(message, friends_id, page, friends_chunks, friends_id_d, mms = None):
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

                            bot.send_message(message.chat.id, text, reply_markup = markup('friends-menu', user))

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

                            def ret(message, bd_user, page, friends_chunks, friends_id, friends_id_d):
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

                                    if res == '▶':
                                        if page + 1 > len(friends_chunks):
                                            page = len(friends_chunks)
                                        else:
                                            page += 1

                                    else:
                                        if res in list(friends_id_d.keys()):
                                            fr_id = friends_id_d[res]
                                            text = member_profile(fr_id, bd_user['language_code'])
                                            mms = bot.send_message(message.chat.id, text, parse_mode = 'Markdown')

                                    work_pr(message, friends_id, page, friends_chunks, friends_id_d, mms = mms)

                            if mms == None:
                                msg = bot.send_message(message.chat.id, text, reply_markup = rmk)
                            else:
                                msg = mms
                            bot.register_next_step_handler(msg, ret, bd_user, page, friends_chunks, friends_id, friends_id_d)

                    work_pr(message, friends_id, page, friends_chunks, friends_id_d)

            if message.text in ["💌 Запросы", "💌 Inquiries"]:
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

                            def chunks(lst, n):
                                for i in range(0, len(lst), n):
                                    yield lst[i:i + n]

                            fr_pages = list(chunks(friends, 3))
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

                            def ret(message, id_friends, bd_user, user):
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

                                    bot.send_message(message.chat.id, text, reply_markup = markup('friends-menu', user))
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
                                            notifications_manager("friend_rejection", users.find_one({"userid": int(uid) }), user.first_name)

                                            if bd_user['language_code'] == 'ru':
                                                text = "👥 | Запрос в друзья отклонён!"
                                            else:
                                                text = "👥 | Friend request rejected!"

                                            bot.send_message(message.chat.id, text)

                                            bd_user['friends']['requests'].remove(uid)
                                            users.update_one( {"userid": bd_user['userid']}, {"$set": {'friends': bd_user['friends'] }} )


                                        if list(res)[0] == '✅':
                                            notifications_manager("friend_accept", users.find_one({"userid": int(uid) }), user.first_name)

                                            if bd_user['language_code'] == 'ru':
                                                text = "👥 | Запрос в друзья одобрен!"
                                            else:
                                                text = "👥 | The friend request is approved!"

                                            bot.send_message(message.chat.id, text)

                                            bd_user['friends']['requests'].remove(uid)
                                            bd_user['friends']['friends_list'].append(uid)
                                            users.update_one( {"userid": bd_user['userid']}, {"$set": {'friends': bd_user['friends'] }} )

                                            two_user = users.find_one({"userid": int(uid) })
                                            two_user['friends']['friends_list'].append(bd_user['userid'])
                                            users.update_one( {"userid": int(uid) }, {"$set": {'friends': two_user['friends'] }} )

                                    work_pr(message, id_friends)

                            msg = bot.send_message(message.chat.id, text, reply_markup = rmk)
                            bot.register_next_step_handler(msg, ret, id_friends, bd_user, user)

                        work_pr(message, id_friends)

            if message.text in ['➖ Удалить', '➖ Delete']:
                bd_user = users.find_one({"userid": user.id})
                if bd_user != None:

                    friends_id = bd_user['friends']['friends_list']
                    page = 1

                    if friends_id != []:
                        if bd_user['language_code'] == 'ru':
                            text = "➖ | Выберите пользователя для удаления из друзей > "
                        else:
                            text = "➖ | Select the user to remove from friends >"
                        bot.send_message(message.chat.id, text, reply_markup = markup('friends-menu', user))

                    def work_pr(message, friends_id, page):
                        global pages
                        a = []

                        def ret(message):
                            if message.text in ['↪ Назад', '↪ Back']:
                                a.append(None)
                                return False
                            else:
                                a.append(message.text)

                            return False

                        if bd_user['language_code'] == 'ru':
                            text = "💌 | Обновление..."
                        else:
                            text = "💌 | Update..."

                        rmk = types.ReplyKeyboardMarkup(resize_keyboard = True, row_width = 3)
                        friends_name = []
                        id_names = {}

                        def chunks(lst, n):
                            for i in range(0, len(lst), n):
                                yield lst[i:i + n]

                        for i in friends_id:
                            try:
                                fr_name = bot.get_chat(int(i)).first_name
                                friends_name.append(fr_name)
                                id_names[bot.get_chat(int(i)).first_name] = i
                            except:
                                pass

                        friends_chunks = list(chunks(list(chunks(friends_name, 2)), 3))

                        if friends_chunks == []:

                            if bd_user['language_code'] == 'ru':
                                text = "👥 | Список пуст!"
                            else:
                                text = "👥 | The list is empty!"

                            bot.send_message(message.chat.id, text, reply_markup = markup('friends-menu', user))
                            return

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

                            def ret(message, friends_id, page, bd_user):
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
                                    return None
                                else:
                                    if res == '◀':
                                        if page - 1 == 0:
                                            page = 1
                                        else:
                                            page -= 1

                                    if res == '▶':
                                        if page + 1 > len(friends_chunks):
                                            page = len(friends_chunks)
                                        else:
                                            page += 1

                                    else:
                                        uid = id_names[res]

                                        if bd_user['language_code'] == 'ru':
                                            text = "👥 | Пользователь удалён из друзей!"
                                        else:
                                            text = "👥 | The user has been removed from friends!"

                                        bd_user['friends']['friends_list'].remove(uid)
                                        users.update_one( {"userid": bd_user['userid']}, {"$set": {'friends': bd_user['friends'] }} )

                                        two_user = users.find_one({"userid": uid})
                                        two_user['friends']['friends_list'].remove(bd_user['userid'])
                                        users.update_one( {"userid": two_user['userid']}, {"$set": {'friends': two_user['friends'] }} )

                                        if bd_user['friends']['friends_list'] == []:
                                            bot.send_message(message.chat.id, text, reply_markup = markup('friends-menu', user))
                                            return
                                        else:
                                            bot.send_message(message.chat.id, text)

                                work_pr(message, friends_id, page)

                            msg = bot.send_message(message.chat.id, text, reply_markup = rmk)
                            bot.register_next_step_handler(msg, ret, friends_id, page, bd_user)

                    work_pr(message, friends_id, page)

            if message.text in ['👁‍🗨 Профиль', '👁‍🗨 Profile']:
                bd_user = users.find_one({"userid": user.id})
                if bd_user != None:

                    if bd_user['language_code'] == 'ru':
                        text = '👁‍🗨 | Панель профиля открыта!'
                    else:
                        text = '👁‍🗨 | The profile panel is open!'

                    bot.send_message(message.chat.id, text, reply_markup = markup("profile", user))

            # nl = ['📜 Информация', '🎮 Инвентарь', '🎢 Рейтинг', '↪ Назад']
            # nl = ['📜 Information', '🎮 Inventory', '🎢 Rating', '↪ Back']

            if message.text in ['🎢 Рейтинг', '🎢 Rating']:
                if bd_user != None:

                    def f_m(x):
                        return 5 * x['lvl'][0] * x['lvl'][0] + 50 * x['lvl'][0] + 100

                    mr_l = list(sorted(list(users.find({})), key=lambda x: x['coins'], reverse=True))
                    lv_l = list(sorted(list(users.find({})), key=lambda x: (x['lvl'][0] - 1) * (5 * x['lvl'][0] * x['lvl'][0] + 50 * x['lvl'][0] + 100) +  x['lvl'][1], reverse=True))

                    du_mc, du_lv = [{}, {}, {}], [{}, {}, {}]


                    i = -1
                    us_i_l = []
                    while du_mc[0] == {} or du_mc[1] == {} or du_mc[2] == {}:
                        i += 1
                        if i >= len(mr_l):
                            break

                        if du_mc[0] == {} and mr_l[i]['userid'] not in us_i_l:
                            try:
                                m = bot.get_chat(mr_l[i]['userid'])
                                du_mc[0] = {'ui': mr_l[i]['userid'], 'coins': mr_l[i]['coins'], 'mn': m.first_name}

                                us_i_l.append(mr_l[i]['userid'])
                            except:
                                pass

                        if du_mc[1] == {} and mr_l[i]['userid'] not in us_i_l:
                            try:
                                m = bot.get_chat(mr_l[i]['userid'])
                                du_mc[1] = {'ui': mr_l[i]['userid'], 'coins': mr_l[i]['coins'], 'mn': m.first_name}

                                us_i_l.append(mr_l[i]['userid'])
                            except:
                                pass

                        if du_mc[2] == {} and mr_l[i]['userid'] not in us_i_l:
                            try:
                                m = bot.get_chat(mr_l[i]['userid'])
                                du_mc[2] = {'ui': mr_l[i]['userid'], 'coins': mr_l[i]['coins'], 'mn': m.first_name}

                                us_i_l.append(mr_l[i]['userid'])
                            except:
                                pass

                    i = -1
                    us_i_m = []
                    while du_lv[0] == {} or du_lv[1] == {} or du_lv[2] == {}:
                        i += 1
                        if i >= len(lv_l):
                            break

                        if du_lv[0] == {} and lv_l[i]['userid'] not in us_i_m:
                            try:
                                m = bot.get_chat(lv_l[i]['userid'])
                                x = lv_l[i]
                                du_lv[0] = {'ui': lv_l[i]['userid'], 'lvl': lv_l[i]['lvl'][0], 'exp': (x['lvl'][0] - 1) * (5 * x['lvl'][0] * x['lvl'][0] + 50 * x['lvl'][0] + 100) +  x['lvl'][1], 'mn': m.first_name }

                                us_i_m.append(lv_l[i]['userid'])
                            except:
                                pass

                        if du_lv[1] == {} and lv_l[i]['userid'] not in us_i_m:
                            try:
                                m = bot.get_chat(lv_l[i]['userid'])
                                x = lv_l[i]
                                du_lv[1] = {'ui': lv_l[i]['userid'], 'lvl': lv_l[i]['lvl'][0], 'exp': (x['lvl'][0] - 1) * (5 * x['lvl'][0] * x['lvl'][0] + 50 * x['lvl'][0] + 100) +  x['lvl'][1], 'mn': m.first_name }

                                us_i_m.append(lv_l[i]['userid'])
                            except:
                                pass

                        if du_lv[2] == {} and lv_l[i]['userid'] not in us_i_m:
                            try:
                                m = bot.get_chat(lv_l[i]['userid'])
                                x = lv_l[i]
                                du_lv[2] = {'ui': lv_l[i]['userid'], 'lvl': lv_l[i]['lvl'][0], 'exp': (x['lvl'][0] - 1) * (5 * x['lvl'][0] * x['lvl'][0] + 50 * x['lvl'][0] + 100) +  x['lvl'][1], 'mn': m.first_name }

                                us_i_m.append(lv_l[i]['userid'])
                            except:
                                pass

                    if bd_user['language_code'] == 'ru':
                        text =  f'*┌* 🎢 Рейтинг по уровню:\n'
                        text += f"*├* Ваше место в рейтинге: #{lv_l.index(bd_user)+1}\n\n"

                        n = 0
                        for i in du_lv:
                            n += 1
                            if i == {}:
                                pass
                            else:
                                if n != 3:
                                    text += f"*├* #{n} *{i['mn']}*:\n      *└* Ур. {i['lvl']} (Всего опыта {i['exp']})\n"
                                else:
                                    text += f"*└* #{n} *{i['mn']}*:\n      *└* Ур. {i['lvl']} (Всего опыта {i['exp']})\n"

                        text += f'\n\n*┌* 🎢 Рейтинг по монетам:\n'
                        text += f"*├* Ваше место в рейтинге: #{mr_l.index(bd_user)+1}\n\n"

                        n = 0
                        for i in du_mc:
                            n += 1
                            if i == {}:
                                pass
                            else:
                                if n != 3:
                                    text += f"*├* #{n} *{i['mn']}*:\n      *└* Монеты {i['coins']}\n"
                                else:
                                    text += f"*└* #{n} *{i['mn']}*:\n      *└* Монеты {i['coins']}\n"
                    else:
                        text =  f'*┌* 🎢 Rating by level:\n'
                        text += f"*├* Your place in the ranking: #{lv_l.index(bd_user)+1}\n\n"

                        n = 0
                        for i in du_lv:
                            n += 1
                            if i == {}:
                                pass
                            else:
                                if n != 3:
                                    text += f"*├* #{n} *{i['mn']}*:\n      *└* lvl {i['lvl']} (Total experience {i['exp']})\n"
                                else:
                                    text += f"*└* #{n} *{i['mn']}*:\n      *└* lvl {i['lvl']} (Total experience {i['exp']})\n"

                        text += f'\n\n*┌* 🎢 Coin Rating:\n'
                        text += f"*├* Your place in the ranking: #{mr_l.index(bd_user)+1}\n\n"

                        n = 0
                        for i in du_mc:
                            n += 1
                            if i == {}:
                                pass
                            else:
                                if n != 3:
                                    text += f"*├* #{n} *{i['mn']}*:\n      *└* Coins {i['coins']}\n"
                                else:
                                    text += f"*└* #{n} *{i['mn']}*:\n      *└* Coins {i['coins']}\n"

                    bot.send_message(message.chat.id, text, parse_mode = "Markdown")



            if message.text in ['🎮 Инвентарь', '🎮 Inventory']:
                bd_user = users.find_one({"userid": user.id})
                if bd_user != None:

                    def chunks(lst, n):
                        for i in range(0, len(lst), n):
                            yield lst[i:i + n]

                    data_items = items_f['items']
                    items = bd_user['inventory']

                    if items == []:

                        if bd_user['language_code'] == 'ru':
                            text = 'Инвентарь пуст.'
                        else:
                            text = 'Inventory is empty.'

                        bot.send_message(message.chat.id, text)

                        return

                    items_id = {}
                    page = 1
                    items_names = []

                    if bd_user['language_code'] == 'ru':
                        lg = "nameru"
                    else:
                        lg = "nameen"

                    for i in items:
                        items_id[ items_f['items'][str(i)][lg] ] = i
                        items_names.append( items_f['items'][str(i)][lg] )

                    items_sort = []
                    d_it_sort = {}
                    ind_sort_it = {}

                    for i in items_names:
                        if i in list(d_it_sort.keys()):
                            d_it_sort[i] += 1
                        else:
                            d_it_sort[i] = 1

                    for n in list(d_it_sort.keys()):
                        col = d_it_sort[n]
                        name = n
                        items_sort.append(f'{n} x{col}')
                        ind_sort_it[f'{n} x{col}'] = n

                    pages = list(chunks(list(chunks(items_sort, 2)), 3))

                    for i in pages:
                        for ii in i:
                            if len(ii) == 1:
                                ii.append(' ')

                        if len(i) != 3:
                            for iii in range(3 - len(i)):
                                i.append([' ', ' '])

                    if bd_user['language_code'] == 'ru':
                        textt = '🎈 | Инвентарь открыт'
                    else:
                        textt = '🎈 | Inventory is open'

                    bot.send_message(message.chat.id, textt)

                    def work_pr(message, pages, page, items_id, ind_sort_it):
                        a = []
                        l_pages = pages
                        l_page = page
                        l_ind_sort_it = ind_sort_it

                        rmk = types.ReplyKeyboardMarkup(resize_keyboard = True, row_width = 3)
                        for i in pages[page-1]:
                            rmk.add(i[0], i[1])

                        if len(pages) > 1:
                            if bd_user['language_code'] == 'ru':
                                com_buttons = ['◀', '↪ Назад', '▶']
                                textt = '🎈 | Обновление...'
                            else:
                                com_buttons = ['◀', '↪ Back', '▶']
                                textt = '🎈 | Update...'

                            rmk.add(com_buttons[0], com_buttons[1], com_buttons[2])

                        else:
                            if bd_user['language_code'] == 'ru':
                                com_buttons = '↪ Назад'
                                textt = '🎈 | Обновление...'
                            else:
                                textt = '🎈 | Update...'
                                com_buttons = '↪ Back'

                            rmk.add(com_buttons)

                        def ret(message, l_pages, l_page, l_ind_sort_it, pages, page, items_id, ind_sort_it, bd_user, user):
                            if message.text in ['↪ Назад', '↪ Back']:
                                res = None
                            else:
                                if message.text in list(l_ind_sort_it.keys()) or message.text in ['◀', '▶']:
                                    res = message.text
                                else:
                                    res = None

                            if res == None:
                                if bd_user['language_code'] == 'ru':
                                    text = "👥 | Возвращение в меню профиля!"
                                else:
                                    text = "👥 | Return to the profile menu!"

                                bot.send_message(message.chat.id, text, reply_markup = markup('profile', user))
                                return '12'

                            else:
                                if res == '◀':
                                    if page - 1 == 0:
                                        page = 1
                                    else:
                                        page -= 1

                                    work_pr(message, pages, page, items_id, ind_sort_it)

                                elif res == '▶':
                                    if page + 1 > len(l_pages):
                                        page = len(l_pages)
                                    else:
                                        page += 1

                                    work_pr(message, pages, page, items_id, ind_sort_it)

                                else:
                                    item_id = items_id[ l_ind_sort_it[res] ]
                                    item = items_f['items'][item_id]
                                    type = item['type']

                                    if bd_user['language_code'] == 'ru':
                                        if item['type'] == '+heal':
                                            type = 'лекарство'
                                            d_text = f"*└* Эффективность: {item['act']}"

                                        elif item['type'] == '+eat':
                                            type = 'еда'
                                            d_text = f"*└* Эффективность: {item['act']}"

                                        elif item['type'] == 'egg':
                                            if item['inc_type'] == 'random': eg_q = 'рандом'
                                            if item['inc_type'] == 'com': eg_q = 'обычная'
                                            if item['inc_type'] == 'unc': eg_q = 'необычная'
                                            if item['inc_type'] == 'rare': eg_q = 'редкая'
                                            if item['inc_type'] == 'myt': eg_q = 'мистическая'
                                            if item['inc_type'] == 'legendary': eg_q = 'легендарная'

                                            type = 'яйцо динозавра'
                                            d_text = f"*├* Инкубация: {item['incub_time']}{item['time_tag']}\n"
                                            d_text += f"*└* Редкость яйца: {eg_q}"

                                        elif item['type'] in ['game_ac', 'unv_ac', 'journey_ac', 'hunt_ac']:
                                            type = 'активный предмет'
                                            d_text = f"*└* Эффективность: {item['act']}"

                                        elif item['type'] == 'None':
                                            type = 'пустышка'
                                            d_text = f"*└* Ничего не делает и не для чего не нужна"

                                        text =  f"*┌* *🎴 Информация о предмете*\n"
                                        text += f"*├* Название: {item['nameru']}\n"
                                        text += f"*├* Тип: {type}\n"
                                        text += d_text

                                    else:
                                        if item['type'] == '+heal':
                                            type = 'medicine'
                                            d_text = f"*└* Effectiveness: {item['act']}"

                                        elif item['type'] == '+eat':
                                            type = 'eat'
                                            d_text = f"*└* Effectiveness: {item['act']}"

                                        elif item['type'] == 'egg':
                                            if item['inc_type'] == 'random': eg_q = 'random'
                                            if item['inc_type'] == 'com': eg_q = 'common'
                                            if item['inc_type'] == 'unc': eg_q = 'uncommon'
                                            if item['inc_type'] == 'rare': eg_q = 'rare'
                                            if item['inc_type'] == 'myt': eg_q = 'mystical'
                                            if item['inc_type'] == 'legendary': eg_q = 'legendary'

                                            type = 'dinosaur egg'
                                            d_text = f"*└* Incubation: {item['incub_time']}{item['time_tag']}\n"
                                            d_text += f"*└* The rarity of eggs: {eg_q}"

                                        elif item['type'] in ['game_ac', 'unv_ac', 'journey_ac', 'hunt_ac']:
                                            type = 'active game item'
                                            d_text = f"*└* Effectiveness: {item['act']}"

                                        elif item['type'] == 'None':
                                            type = 'dummy'
                                            d_text = f"*└* Does nothing and is not needed for anything"

                                        text =  f"*┌* *🎴 Subject information*\n"
                                        text += f"*├* Name: {item['nameen']}\n"
                                        text += f"*├* Type: {type}\n"
                                        text += d_text


                                    bot.send_message(message.chat.id, text, reply_markup = markup('profile', user), parse_mode = 'Markdown')

                        msg = bot.send_message(message.chat.id, textt, reply_markup = rmk)
                        bot.register_next_step_handler(msg, ret, l_pages, l_page, l_ind_sort_it, pages, page, items_id, ind_sort_it, bd_user, user)



                    work_pr(message, pages, page, items_id, ind_sort_it)

            if message.text in ['📜 Информация', '📜 Information']:
                bd_user = users.find_one({"userid": user.id})
                if bd_user != None:
                    text = member_profile(user.id, lang = bd_user['language_code'])
                    bot.send_message(message.chat.id, text, parse_mode = 'Markdown')


            bd_user = users.find_one({"userid": user.id})
            tr_c = False
            if bd_user != None and len(list(bd_user['dinos'])) > 0:
                if len(list(bd_user['dinos'])) > 1:
                    tr_c = True

                else:
                    if bd_user['dinos'][ bd_user['settings']['dino_id'] ]['status'] == 'dino':
                        tr_c = True

            if tr_c == True:

                if message.text in ['↩ Назад', '↩ Back']:
                    bd_user = users.find_one({"userid": user.id})

                    if bd_user['language_code'] == 'ru':
                        text = '↩ Возврат в меню активностей'
                    else:
                        text = '↩ Return to the activity menu'

                    bot.send_message(message.chat.id, text, reply_markup = markup('actions', user))

                if message.text in ['💬 Переименовать', '💬 Rename']:
                    bd_user = users.find_one({"userid": user.id})
                    if bd_user != None:
                        n_dp, dp_a = dino_pre_answer(message)

                        def rename(message, bd_user, user, dino_user_id, dino):
                            if bd_user['language_code'] == 'ru':
                                text = f"🦖 | Введите новое имя для {dino['name']}\nРазмер: не более 20-ти символов\n>"
                                ans = ['↪ Назад']
                            else:
                                text = f"🦖 | Enter a new name for {dino['name']}\nSize: no more than 20 characters\n>"
                                ans = ['↪ Back']

                            rmk = types.ReplyKeyboardMarkup(resize_keyboard = True)
                            rmk.add(ans[0])

                            def ret(message, ans, bd_user):
                                if message.text == ans[0]:
                                    bot.send_message(message.chat.id, f'❌', reply_markup = markup('settings', user))
                                    return

                                dino_name = message.text

                                if len(dino_name) > 20:

                                    if bd_user['language_code'] == 'ru':
                                        text = f"🦖 | Новое имя больше 20-ти символов!"
                                    else:
                                        text = f"🦖 | The new name is more than 20 characters!"

                                    msg = bot.send_message(message.chat.id, text)

                                else:
                                    if bd_user['language_code'] == 'ru':
                                        text = f"🦖 | Переименовать {dino['name']} > {dino_name}?"
                                        ans2 = ['✅ Подтверждаю', '↪ Назад']
                                    else:
                                        text = f"🦖 | Rename {dino['name']} > {dino_name}?"
                                        ans2 = ['✅ Confirm', '↪ Back']

                                    rmk = types.ReplyKeyboardMarkup(resize_keyboard = True)
                                    rmk.add(ans2[0])
                                    rmk.add(ans2[1])

                                    def ret2(message, ans2, bd_user):
                                        if message.text == ans2[1]:
                                            bot.send_message(message.chat.id, f'❌', reply_markup = markup('settings', user))
                                            return
                                        else:
                                            res = message.text

                                        if res in ['✅ Confirm', '✅ Подтверждаю']:

                                            bd_user['dinos'][str(dino_user_id)]['name'] = dino_name
                                            users.update_one( {"userid": bd_user['userid']}, {"$set": {'dinos': bd_user['dinos'] }} )

                                            bot.send_message(message.chat.id, f'✅', reply_markup = markup('settings', user))

                                    msg = bot.send_message(message.chat.id, text, reply_markup = rmk)
                                    bot.register_next_step_handler(msg, ret2, ans2, bd_user)

                            msg = bot.send_message(message.chat.id, text, reply_markup = rmk)
                            bot.register_next_step_handler(msg, ret, ans, bd_user)

                        if n_dp == 1:
                            bot.send_message(message.chat.id, f'❌', reply_markup = markup('settings', user))
                            return

                        if n_dp == 2:
                            bd_dino = dp_a
                            rename(message, bd_user, user, list(bd_user['dinos'].keys())[0], dp_a)

                        if n_dp == 3:
                            rmk = dp_a[0]
                            text = dp_a[1]
                            dino_dict = dp_a[2]

                            def ret(message, dino_dict, user, bd_user):
                                rename(message, bd_user, user, dino_dict[message.text][1], dino_dict[message.text][0])

                            msg = bot.send_message(message.chat.id, text, reply_markup = rmk)
                            bot.register_next_step_handler(msg, ret, dino_dict, user, bd_user)


                if message.text in ['🕹 Действия', '🕹 Actions']:
                    bd_user = users.find_one({"userid": user.id})
                    if bd_user != None:

                        if bd_user['language_code'] == 'ru':
                            text = '🕹 Панель действий открыта!'
                        else:
                            text = '🕹 The action panel is open!'

                        bot.send_message(message.chat.id, text, reply_markup = markup("actions", user))

                if message.text in ['🌙 Уложить спать', '🌙 Put to bed']:
                    bd_user = users.find_one({"userid": user.id})
                    if bd_user != None:
                        dino = bd_user['dinos'][ str(bd_user['settings']['dino_id']) ]

                        if dino != None:
                            if dino['activ_status'] == 'pass_active':
                                if dino['stats']['unv'] >= 90:

                                    if bd_user['language_code'] == 'ru':
                                        text = '🌙 Динозавр не хочет спать!'
                                    else:
                                        text = "🌙 The dinosaur doesn't want to sleep!"

                                    bot.send_message(message.chat.id, text, reply_markup = markup("actions", user))

                                else:

                                    bd_user['dinos'][ list(bd_user['dinos'].keys())[0] ]['activ_status'] = 'sleep'
                                    users.update_one( {"userid": bd_user['userid']}, {"$set": {'dinos': bd_user['dinos'] }} )

                                    if bd_user['language_code'] == 'ru':
                                        text = '🌙 Вы уложили динозавра спать!'
                                    else:
                                        text = "🌙 You put the dinosaur to sleep!"

                                    bot.send_message(message.chat.id, text , reply_markup = markup('actions', user))

                        else:
                            bot.send_message(message.chat.id, f'❌', reply_markup = markup('actions', user))
                            return


                if message.text in ['🌙 Пробудить', '🌙 Awaken']:
                    bd_user = users.find_one({"userid": user.id})
                    if bd_user != None:
                        dino = bd_user['dinos'][ str(bd_user['settings']['dino_id']) ]

                        if dino['activ_status'] == 'sleep' and dino != None:
                            r_n = random.randint(0, 20)

                            bd_user['dinos'][ list(bd_user['dinos'].keys())[0] ]['activ_status'] = 'pass_active'
                            bd_user['dinos'][ list(bd_user['dinos'].keys())[0] ]['stats']['mood'] -= r_n

                            if bd_user['dinos'][ list(bd_user['dinos'].keys())[0] ]['stats']['mood'] < 0:
                                bd_user['dinos'][ list(bd_user['dinos'].keys())[0] ]['stats']['mood'] = 0

                            users.update_one( {"userid": bd_user['userid']}, {"$set": {'dinos': bd_user['dinos'] }} )

                            if bd_user['language_code'] == 'ru':
                                text = f'🌙 Ваш динозавр пробудился. Он сильно не доволен что вы его разбудили!\nДинозавр потерял {r_n}% настроения.'
                            else:
                                text = f"🌙 Your dinosaur has awakened. He is very unhappy that you woke him up!\nDinosaur lost {r_n}% of mood."

                            bot.send_message(message.chat.id, text , reply_markup = markup('actions', user))

                        else:
                            bot.send_message(message.chat.id, f'❌', reply_markup = markup('actions', user))
                            return

                if message.text in ['🎑 Путешествие', '🎑 Journey']:
                    bd_user = users.find_one({"userid": user.id})
                    if bd_user != None:
                        dino = bd_user['dinos'][ str(bd_user['settings']['dino_id']) ]

                        if dino['activ_status'] == 'pass_active' and dino != None:
                            markup_inline = types.InlineKeyboardMarkup()

                            if bd_user['language_code'] == 'ru':
                                text = '🌳 На какое время отправить динозавра в путешествие?'

                                item_0 = types.InlineKeyboardButton( text = '10 мин.', callback_data = f"10min_journey_{str(bd_user['settings']['dino_id'])}")

                                item_1 = types.InlineKeyboardButton( text = '30 мин.', callback_data = f"30min_journey_{str(bd_user['settings']['dino_id'])}")

                                item_2 = types.InlineKeyboardButton( text = '60 мин.', callback_data = f"60min_journey_{str(bd_user['settings']['dino_id'])}")

                                item_3 = types.InlineKeyboardButton( text = '90 мин.', callback_data = f"90min_journey_{str(bd_user['settings']['dino_id'])}")

                            else:
                                text = "🌳 How long to send a dinosaur on a journey?"

                                item_0 = types.InlineKeyboardButton( text = '10 min.', callback_data = f"10min_journey_{str(bd_user['settings']['dino_id'])}")

                                item_1 = types.InlineKeyboardButton( text = '30 min.', callback_data = f"30min_journey_{str(bd_user['settings']['dino_id'])}")

                                item_2 = types.InlineKeyboardButton( text = '60 min.', callback_data = f"60min_journey_{str(bd_user['settings']['dino_id'])}")

                                item_3 = types.InlineKeyboardButton( text = '90 min.', callback_data = f"90min_journey_{str(bd_user['settings']['dino_id'])}")

                            markup_inline.add(item_0, item_1, item_2, item_3)

                            bot.send_message(message.chat.id, text, reply_markup = markup_inline)

                        else:
                            bot.send_message(message.chat.id, f'❌', reply_markup = markup('actions', user))
                            return


                if message.text in ['🎑 Вернуть', '🎑 Call']:
                    bd_user = users.find_one({"userid": user.id})
                    if bd_user != None:
                        dino = bd_user['dinos'][ str(bd_user['settings']['dino_id']) ]

                        if dino['activ_status'] == 'journey' and dino != None:
                            if random.randint(1,2) == 1:

                                if bd_user['language_code'] == 'ru':
                                    text = f'🦖 | Вы вернули динозавра из путешествия!\nВот что произошло в его путешествии:\n'

                                    if bd_user['dinos'][ list(bd_user['dinos'].keys())[0] ]['journey_log'] == []:
                                        text += 'Ничего не произошло!'
                                    else:
                                        n = 1
                                        for el in bd_user['dinos'][ list(bd_user['dinos'].keys())[0] ]['journey_log']:
                                            text += f'<b>{n}.</b> {el}\n\n'
                                            n += 1
                                else:
                                    text = f"🦖 | Turned the dinosaur out of the journey!\nHere's what happened on his journey:\n"

                                    if bd_user['dinos'][ list(bd_user['dinos'].keys())[0] ]['journey_log'] == []:
                                        text += 'Nothing happened!'
                                    else:
                                        n = 1
                                        for el in bd_user['dinos'][ list(bd_user['dinos'].keys())[0] ]['journey_log']:
                                            text += f'<b>{n}.</b> {el}\n\n'
                                            n += 1


                                bd_user['dinos'][ list(bd_user['dinos'].keys())[0] ]['activ_status'] = 'pass_active'
                                del bd_user['dinos'][ list(bd_user['dinos'].keys())[0] ]['journey_time']
                                del bd_user['dinos'][ list(bd_user['dinos'].keys())[0] ]['journey_log']

                                users.update_one( {"userid": bd_user['userid']}, {"$set": {'dinos': bd_user['dinos'] }} )

                                bot.send_message(message.chat.id, text, reply_markup = markup('actions', user), parse_mode = 'html')


                            else:
                                if bd_user['language_code'] == 'ru':
                                    text = f'🔇 | Вы попробовали вернуть динозавра, но что-то пошло не так...'
                                else:
                                    text = f"🔇 | You tried to bring the dinosaur back, but something went wrong..."

                                bot.send_message(message.chat.id, text , reply_markup = markup('actions', user))
                        else:
                            bot.send_message(message.chat.id, f'❌', reply_markup = markup('actions', user))
                            return


                if message.text[:11] in ['🦖 Динозавр:'] or message.text[:7] in [ '🦖 Dino:']:
                    bd_user = users.find_one({"userid": user.id})
                    if bd_user != None:
                        if bd_user['language_code'] == 'ru':
                            did = int(message.text[12:])
                        else:
                            did = int(message.text[8:])

                        if did == int(bd_user['settings']['dino_id']):
                            ll = list(bd_user['dinos'].keys())
                            ind = list(bd_user['dinos'].keys()).index(str(did))

                            if ind + 1 == len(ll):
                                bd_user['settings']['dino_id'] = ll[0]
                                users.update_one( {"userid": bd_user['userid']}, {"$set": {'settings': bd_user['settings'] }} )
                            else:
                                bd_user['settings']['dino_id'] = list(bd_user['dinos'].keys())[int(ll[did-1])]
                                users.update_one( {"userid": bd_user['userid']}, {"$set": {'settings': bd_user['settings'] }} )

                            if bd_user['language_code'] == 'ru':
                                text = f"Вы выбрали динозавра {bd_user['dinos'][ str(bd_user['settings']['dino_id']) ]['name']}"
                            else:
                                text = f"You have chosen a dinosaur {bd_user['dinos'][ str(bd_user['settings']['dino_id']) ]['name']}"

                            bot.send_message(message.chat.id, text , reply_markup = markup('actions', user))


                if message.text in ['🎮 Развлечения', '🎮 Entertainments']:
                    bd_user = users.find_one({"userid": user.id})
                    if bd_user != None:
                        dino = bd_user['dinos'][ str(bd_user['settings']['dino_id']) ]

                        if bd_user['language_code'] == 'ru':
                            text = f"🎮 | Перенаправление в меню развлечений!"

                        else:
                            text = f"🎮 | Redirecting to the entertainment menu!"

                        bot.send_message(message.chat.id, text, reply_markup = markup('games', user))

                if message.text in ['🎮 Консоль', '🪁 Змей', '🏓 Пинг-понг', '🏐 Мяч', '🎮 Console', '🪁 Snake', '🏓 Ping Pong', '🏐 Ball']:
                    bd_user = users.find_one({"userid": user.id})
                    if bd_user != None:
                        dino = bd_user['dinos'][ str(bd_user['settings']['dino_id']) ]
                        if dino['activ_status'] == 'pass_active':

                            markup_inline = types.InlineKeyboardMarkup(row_width=2)

                            if bd_user['language_code'] == 'ru':
                                text = ['25 - 60 мин.', '60 - 90 мин.', '90 - 120 мин.']
                                m_text = '🎮 Укажите разрешённое время игры > '
                            else:
                                text = ['25 - 60 min.', '60 - 90 min.', '90 - 120 min.']
                                m_text = '🎮 Specify the allowed game time >'

                            if message.text in ['🎮 Консоль', '🎮 Console']:
                                g = 'con'
                            elif message.text in ['🪁 Змей', '🪁 Snake']:
                                g = 'sna'
                            elif message.text in ['🏓 Пинг-понг', '🏓 Ping Pong']:
                                g = 'pin'
                            elif message.text in ['🏐 Мяч', '🏐 Ball']:
                                g = 'bal'

                            item_1 = types.InlineKeyboardButton( text = text[0], callback_data = f"1_{g}_game_{str(bd_user['settings']['dino_id'])}")
                            item_2 = types.InlineKeyboardButton( text = text[1], callback_data = f"2_{g}_game_{str(bd_user['settings']['dino_id'])}")
                            item_3 = types.InlineKeyboardButton( text = text[2], callback_data = f"3_{g}_game_{str(bd_user['settings']['dino_id'])}")
                            markup_inline.add(item_1, item_2, item_3)

                            bot.send_message(message.chat.id, m_text, reply_markup = markup_inline)

                if message.text in ['❌ Остановить игру', '❌ Stop the game']:
                    bd_user = users.find_one({"userid": user.id})
                    if bd_user != None:
                        dino = bd_user['dinos'][ str(bd_user['settings']['dino_id']) ]
                        if dino['activ_status'] == 'game':

                            if dino['game_%'] == 1:
                                rt = random.randint(1,3)

                            if dino['game_%'] == 0.5:
                                rt = 1

                            if dino['game_%'] == 0.9:
                                rt = random.randint(1,2)

                            if rt == 1:

                                if dino['game_%'] == 1:
                                    bd_user['dinos'][ str(bd_user['settings']['dino_id']) ]['stats']['mood'] -= 20

                                    if bd_user['language_code'] == 'ru':
                                        text = f"🎮 | Динозавру нравилось играть, но вы его остановили, его настроение снижено на 20%!"

                                    else:
                                        text = f"🎮 | The dinosaur liked to play, but you stopped him, his mood is reduced by 20%!"

                                if dino['game_%'] == 0.5:

                                    if bd_user['language_code'] == 'ru':
                                        text = f"🎮 | Динозавру не особо нравилось играть, он не теряет настроение..."

                                    else:
                                        text = f"🎮 | The dinosaur didn't really like playing, he doesn't lose his mood..."

                                if dino['game_%'] == 0.9:
                                    bd_user['dinos'][ str(bd_user['settings']['dino_id']) ]['stats']['mood'] -= 5

                                    if bd_user['language_code'] == 'ru':
                                        text = f"🎮 | Динозавр немного расстроен что вы его отвлекли, он теряет 5% настроения..."

                                    else:
                                        text = f"🎮 | The dinosaur is a little upset that you distracted him, he loses 5% of his mood..."

                                bd_user['dinos'][ str(bd_user['settings']['dino_id']) ]['activ_status'] = 'pass_active'
                                del bd_user['dinos'][ str(bd_user['settings']['dino_id']) ]['game_time']
                                del bd_user['dinos'][ str(bd_user['settings']['dino_id']) ]['game_%']


                                users.update_one( {"userid": bd_user['userid']}, {"$set": {'dinos': bd_user['dinos'] }} )
                                bot.send_message(message.chat.id, text, reply_markup = markup('games', user))

                            else:

                                if bd_user['language_code'] == 'ru':
                                    text = f"🎮 | Динозавра невозможно оторвать от игры, попробуйте ещё раз. Имейте ввиду, динозавр будет расстроен."

                                else:
                                    text = f"🎮 | It is impossible to tear the dinosaur away from the game, try again. Keep in mind, the dinosaur will be upset."

                                bot.send_message(message.chat.id, text, reply_markup = markup('games', user))

                if message.text in ['🍣 Покормить', '🍣 Feed']:
                    bd_user = users.find_one({"userid": user.id})
                    if bd_user != None:

                        if bd_user['dinos'][ bd_user['settings']['dino_id'] ]['activ_status'] == 'sleep':

                            if bd_user['language_code'] == 'ru':
                                text = 'Во время сна нельзя кормить динозавра.'
                            else:
                                text = 'During sleep, you can not feed the dinosaur.'

                            bot.send_message(message.chat.id, text)
                            return

                        def chunks(lst, n):
                            for i in range(0, len(lst), n):
                                yield lst[i:i + n]

                        nitems = bd_user['inventory']

                        if nitems == []:

                            if bd_user['language_code'] == 'ru':
                                text = 'Инвентарь пуст.'
                            else:
                                text = 'Inventory is empty.'

                            bot.send_message(message.chat.id, text)
                            return

                        data_items = items_f['items']
                        items = []
                        items_id = {}
                        page = 1
                        items_names = []

                        for i in nitems:
                            if data_items[str(i)]['type'] == "+eat":
                                items.append(i)

                        if items == []:

                            if bd_user['language_code'] == 'ru':
                                text = '🥞 | В инвентаре нет продуктов питания.'
                            else:
                                text = '🥞 | There are no food items in the inventory.'

                            bot.send_message(message.chat.id, text)
                            return


                        if bd_user['language_code'] == 'ru':
                            lg = "nameru"
                        else:
                            lg = "nameen"

                        for i in items:
                            items_id[ items_f['items'][str(i)][lg] ] = i
                            items_names.append( items_f['items'][str(i)][lg] )

                        items_sort = []
                        d_it_sort = {}
                        ind_sort_it = {}

                        for i in items_names:
                            if i in list(d_it_sort.keys()):
                                d_it_sort[i] += 1
                            else:
                                d_it_sort[i] = 1

                        for n in list(d_it_sort.keys()):
                            col = d_it_sort[n]
                            name = n
                            items_sort.append(f'{n} x{col}')
                            ind_sort_it[f'{n} x{col}'] = n

                        pages = list(chunks(list(chunks(items_sort, 2)), 3))

                        for i in pages:
                            for ii in i:
                                if len(ii) == 1:
                                    ii.append(' ')

                            if len(i) != 3:
                                for iii in range(3 - len(i)):
                                    i.append([' ', ' '])

                        def work_pr(message, pages, page, items_id, ind_sort_it):
                            global l_pages, l_page, l_ind_sort_it
                            a = []
                            l_pages = pages
                            l_page = page
                            l_ind_sort_it = ind_sort_it

                            def ret(message):
                                global l_pages, l_page, l_ind_sort_it
                                if message.text in ['↩ Назад', '↩ Back']:
                                    a.append(None)
                                    return False
                                else:
                                    if message.text in list(l_ind_sort_it.keys()) or message.text in ['◀', '▶']:
                                        a.append(message.text)
                                    else:
                                        a.append(None)
                                    return False

                            rmk = types.ReplyKeyboardMarkup(resize_keyboard = True, row_width = 3)
                            for i in pages[page-1]:
                                rmk.add(i[0], i[1])

                            if len(pages) > 1:
                                if bd_user['language_code'] == 'ru':
                                    com_buttons = ['◀', '↩ Назад', '▶']
                                    textt = '🍕 | Выберите чем вы хотите покормить динозавра > '
                                else:
                                    com_buttons = ['◀', '↩ Back', '▶']
                                    textt = '🍕 | Choose what you want to feed the dinosaur >'

                                rmk.add(com_buttons[0], com_buttons[1], com_buttons[2])

                            else:
                                if bd_user['language_code'] == 'ru':
                                    com_buttons = '↩ Назад'
                                    textt = '🍕 | Выберите чем вы хотите покормить динозавра > '
                                else:
                                    textt = '🍕 | Choose what you want to feed the dinosaur >'
                                    com_buttons = '↩ Back'

                                rmk.add(com_buttons)

                            def ret(message, l_pages, l_page, l_ind_sort_it, bd_user, user, pages, page, items_id, ind_sort_it):
                                if message.text in ['↩ Назад', '↩ Back']:
                                    res = None

                                else:
                                    if message.text in list(l_ind_sort_it.keys()) or message.text in ['◀', '▶']:
                                        res = message.text
                                    else:
                                        res = None


                                if res == None:
                                    if bd_user['language_code'] == 'ru':
                                        text = "👥 | Возвращение в меню активностей!"
                                    else:
                                        text = "👥 | Return to the friends menu!"

                                    bot.send_message(message.chat.id, text, reply_markup = markup('actions', user))
                                    return '12'
                                else:
                                    if res == '◀':
                                        if page - 1 == 0:
                                            page = 1
                                        else:
                                            page -= 1

                                        work_pr(message, pages, page, items_id, ind_sort_it)

                                    elif res == '▶':
                                        if page + 1 > len(l_pages):
                                            page = len(l_pages)
                                        else:
                                            page += 1

                                        work_pr(message, pages, page, items_id, ind_sort_it)

                                    else:
                                        item_id = items_id[ l_ind_sort_it[res] ]
                                        item = items_f['items'][item_id]
                                        bd_dino = bd_user['dinos'][ bd_user['settings']['dino_id'] ]
                                        d_dino = json_f['elements'][ str(bd_dino['dino_id']) ]

                                        if bd_user['language_code'] == 'ru':
                                            if item['class'] == 'ALL':
                                                text = f"🍕 | Динозавр с удовольствием съел {item['nameru']}!"
                                                bd_user['dinos'][ bd_user['settings']['dino_id'] ]['stats']['eat'] += item['act']

                                            elif item['class'] == d_dino['class']:
                                                text = f"🍕 | Динозавр с удовольствием съел {item['nameru']}!"
                                                bd_user['dinos'][ bd_user['settings']['dino_id'] ]['stats']['eat'] += item['act']

                                            else:
                                                eatr = random.randint( 0, int(item['act'] / 2) )
                                                moodr = random.randint( 1, 10 )
                                                text = f"🍕 | Динозавру не по вкусу {item['nameru']}, он теряет {eatr}% сытости и {moodr}% настрояния!"

                                                bd_user['dinos'][ bd_user['settings']['dino_id'] ]['stats']['eat'] -= eatr
                                                bd_user['dinos'][ bd_user['settings']['dino_id'] ]['stats']['mood'] -= moodr

                                        else:
                                            if item['class'] == 'ALL':
                                                text = f"🍕 | The dinosaur ate it with pleasure {item['nameen']}!"
                                                bd_user['dinos'][ bd_user['settings']['dino_id'] ]['stats']['eat'] += item['act']

                                            elif item['class'] == d_dino['class']:
                                                text = f"🍕 | The dinosaur ate it with pleasure {item['nameen']}!"
                                                bd_user['dinos'][ bd_user['settings']['dino_id'] ]['stats']['eat'] += item['act']

                                            else:
                                                eatr = random.randint( 0, int(item['act'] / 2) )
                                                moodr = random.randint( 1, 10 )
                                                text = f"🍕 | The dinosaur doesn't like {item['nameen']}, it loses {eatr}% satiety and {mood}% mood!"

                                                bd_user['dinos'][ bd_user['settings']['dino_id'] ]['stats']['eat'] -= eatr
                                                bd_user['dinos'][ bd_user['settings']['dino_id'] ]['stats']['mood'] -= moodr

                                        users.update_one( {"userid": bd_user['userid']}, {"$set": {'dinos': bd_user['dinos'] }} )

                                        bd_user['inventory'].remove(item_id)
                                        users.update_one( {"userid": bd_user['userid']}, {"$set": {'inventory': bd_user['inventory'] }} )

                                        bot.send_message(message.chat.id, text, reply_markup = markup('actions', user))

                            msg = bot.send_message(message.chat.id, textt, reply_markup = rmk)
                            bot.register_next_step_handler(msg, ret, l_pages, l_page, l_ind_sort_it, bd_user, user, pages, page, items_id, ind_sort_it)

                        work_pr(message, pages, page, items_id, ind_sort_it)

                if message.text in ['🍕 Сбор пищи', '🍕 Collecting food']:
                    if bd_user['dinos'][ bd_user['settings']['dino_id'] ]['activ_status'] == 'pass_active':

                        if bd_user['language_code'] == 'ru':
                            bbt = ['🌿 | Собирательство', '🍖 | Охота', '🍤 | Рыбалка', '🥗 | Все вместе', '↩ Назад']
                            text = '🌴 | Выберите способ добычи продовольствия >'
                        else:
                            bbt = ['🌿 | Collecting', '🍖 | Hunting', '🍤 | Fishing', '🥗 | All together', '↩ Back']
                            text = '🌴 | Choose a way to get food >'

                        rmk = types.ReplyKeyboardMarkup(resize_keyboard = True)
                        rmk.add(bbt[0], bbt[1])
                        rmk.add(bbt[2], bbt[3])
                        rmk.add(bbt[4])

                        def ret(message, ans, bd_user):

                            if message.text not in ans or message.text == ans[4]:
                                res = None
                            else:
                                res = message.text

                            if res == None:
                                if bd_user['language_code'] == 'ru':
                                    text = '↩ Возврат в меню активностей'
                                else:
                                    text = '↩ Return to the activity menu'

                                bot.send_message(message.chat.id, text, reply_markup = markup('actions', user))

                            else:

                                if bd_user['language_code'] == 'ru':
                                    ans = ['↩ Назад']
                                    text = '🍽 | Введите число продуктов, которое должен собрать динозавр >'
                                else:
                                    ans = ['↩ Back']
                                    text = '🍽 | Enter the number of products that the dinosaur must collect >'

                                rmk = types.ReplyKeyboardMarkup(resize_keyboard = True)
                                rmk.add(ans[0])

                                def ret2(message, ans, bd_user):
                                    number = message.text
                                    try:
                                        number = int(number)
                                        if number <= 0 or number >= 101:
                                            if bd_user['language_code'] == 'ru':
                                                text = '0️⃣1️⃣0️⃣ | Введите число от 1 до 100!'
                                            else:
                                                text = '0️⃣1️⃣0️⃣ | Enter a number from 1 to 100!'

                                            bot.send_message(message.chat.id, text)
                                            number = None
                                    except:
                                        number = None

                                    if number == None:
                                        if bd_user['language_code'] == 'ru':
                                            text = '↩ Возврат в меню активностей'
                                        else:
                                            text = '↩ Return to the activity menu'

                                        bot.send_message(message.chat.id, text, reply_markup = markup('actions', user))

                                    else:
                                        bd_user['dinos'][ bd_user['settings']['dino_id'] ]['activ_status'] = 'hunting'
                                        bd_user['dinos'][ bd_user['settings']['dino_id'] ]['target'] = [0, number]

                                        if res == bbt[0]:
                                            bd_user['dinos'][ bd_user['settings']['dino_id'] ]['h_type'] = 'collecting'

                                            if bd_user['language_code'] == 'ru':
                                                text = f'🌿 | Сбор ягод и трав начат!\n♻ | Текущий прогресс: 0%\n🎲 | Цель: {number}'
                                            else:
                                                text = f'🌿 | The gathering of berries and herbs has begun!\n♻ | Current progress: 0%\n🎲 | Goal: {number}'

                                        if res == bbt[1]:
                                            bd_user['dinos'][ bd_user['settings']['dino_id'] ]['h_type'] = 'hunting'

                                            if bd_user['language_code'] == 'ru':
                                                text = f'🍖 | Охота началась!\n♻ | Текущий прогресс: 0%\n🎲 | Цель: {number}'
                                            else:
                                                text = f'🍖 | The hunt has begun!\n♻ | Current progress: 0%\n🎲 | Goal: {number}'

                                        if res == bbt[2]:
                                            bd_user['dinos'][ bd_user['settings']['dino_id'] ]['h_type'] = 'fishing'

                                            if bd_user['language_code'] == 'ru':
                                                text = f'🍣 | Рыбалка началась!\n♻ | Текущий прогресс: 0%\n🎲 | Цель: {number}'
                                            else:
                                                text = f'🍣 | Fishing has begun!\n♻ | Current progress: 0%\n🎲 | Goal: {number}'

                                        if res == bbt[3]:
                                            bd_user['dinos'][ bd_user['settings']['dino_id'] ]['h_type'] = 'all'

                                            if bd_user['language_code'] == 'ru':
                                                text = f'🍱 | Общий сбор пищи начат!\n♻ | Текущий прогресс: 0%\n🎲 | Цель: {number}'
                                            else:
                                                text = f'🍱 | The general food collection has begun!\n♻ | Current progress: 0%\n🎲 | Goal: {number}'

                                        users.update_one( {"userid": bd_user['userid']}, {"$set": {'dinos': bd_user['dinos'] }} )
                                        bot.send_message(message.chat.id, text, reply_markup = markup('actions', user))

                                msg = bot.send_message(message.chat.id, text, reply_markup = rmk)
                                bot.register_next_step_handler(msg, ret2, ans, bd_user)

                        msg = bot.send_message(message.chat.id, text, reply_markup = rmk)
                        bot.register_next_step_handler(msg, ret, bbt, bd_user)


                if message.text in ['🍕 Прогресс', '🍕 Progress']:
                    if bd_user['dinos'][ bd_user['settings']['dino_id'] ]['activ_status'] == 'hunting':
                        number = bd_user['dinos'][ bd_user['settings']['dino_id'] ]['target'][0]
                        tnumber = bd_user['dinos'][ bd_user['settings']['dino_id'] ]['target'][1]
                        prog = number / (tnumber / 100)

                        if bd_user['language_code'] == 'ru':
                            text = f'🍱 | Текущий прогресс: {int( prog )}%\n🎲 | Цель: {tnumber}'
                        else:
                            text = f'🍱 | Current progress: {int( prog )}%\n🎲 | Goal: {tnumber}'

                        bot.send_message(message.chat.id, text)



@bot.callback_query_handler(func = lambda call: True)
def answer(call):
    user = call.from_user
    bd_user = users.find_one({"userid": user.id})

    if call.data == 'start':
        if bot.get_chat_member(-1001673242031, user.id).status != 'left' and bd_user == None:
            message = call
            try:
                message.chat = bot.get_chat(user.id)
            except:
                return

            if user.language_code == 'ru':
                text = f'📜 | Приятной игры!'
            else:
                text = f"📜 | Have a nice game!"

            bot.edit_message_text(text, call.message.chat.id, call.message.message_id, parse_mode = 'Markdown')

            def trans_paste(fg_img,bg_img,alpha=10,box=(0,0)):
                fg_img_trans = Image.new("RGBA",fg_img.size)
                fg_img_trans = Image.blend(fg_img_trans,fg_img,alpha)
                bg_img.paste(fg_img_trans,box,fg_img_trans)
                return bg_img

            def photo():
                global json_f
                bg_p = Image.open(f"images/remain/{random.choice(['back', 'back2'])}.png")
                eg_l = []
                id_l = []

                for i in range(3):
                    rid = str(random.choice(list(json_f['data']['egg'])))
                    image = Image.open('images/'+str(json_f['elements'][rid]['image']))
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

            if user.language_code == 'ru':
                lg = "ru"
            else:
                lg = 'en'

            users.insert_one({'userid': user.id, 'last_m': int(time.time()), 'dinos': {}, 'eggs': [], 'notifications': {}, 'settings': {'notifications': True, 'dino_id': '1'}, 'language_code': lg, 'inventory': [], 'coins': 0, 'lvl': [1, 0], 'activ_items': {'game': None, 'hunt': None, 'journey': None, 'unv': None}, 'friends': { 'friends_list': [], 'requests': [] } })

            markup_inline = types.InlineKeyboardMarkup()
            item_1 = types.InlineKeyboardButton( text = '🥚 1', callback_data = 'egg_answer_1')
            item_2 = types.InlineKeyboardButton( text = '🥚 2', callback_data = 'egg_answer_2')
            item_3 = types.InlineKeyboardButton( text = '🥚 3', callback_data = 'egg_answer_3')
            markup_inline.add(item_1, item_2, item_3)

            photo, id_l = photo()
            bot.send_photo(message.chat.id, photo, text, reply_markup = markup_inline)
            users.update_one( {"userid": user.id}, {"$set": {'eggs': id_l}} )

    if call.data == 'checking_the_user_in_the_channel':
        if bot.get_chat_member(-1001673242031, user.id).status != 'left':

            if bd_user['language_code'] == 'ru':
                text = f'📜 | Уважаемый пользователь!\n\n*•* Для получения новостей и важных уведомлений по поводу бота, мы просим вас подписаться на телеграм канал бота!\n\n🟢 | Спасибо за понимание, приятного использования бота!'
            else:
                text = f"📜 | Dear user!\n\n*•* To receive news and important notifications about the bot, we ask you to subscribe to the bot's telegram channel!\n\n🟢 | Thank you for understanding, enjoy using the bot!"

            bot.edit_message_text(text, call.message.chat.id, call.message.message_id, parse_mode = 'Markdown')


    if call.data in ['egg_answer_1', 'egg_answer_2', 'egg_answer_3']:

        if 'eggs' in list(bd_user.keys()):
            egg_n = call.data[11:]

            bd_user['dinos'][ user_dino_pn(bd_user) ] = {'status': 'incubation', 'incubation_time': time.time() + 10 * 60, 'egg_id': bd_user['eggs'][int(egg_n)-1]}

            users.update_one( {"userid": user.id}, {"$unset": {'eggs': None}} )
            users.update_one( {"userid": user.id}, {"$set": {'dinos': bd_user['dinos']}} )

            if bd_user['language_code'] == 'ru':
                text = f'🥚 | Выберите яйцо с динозавром!\n🦖 | Вы выбрали яйцо 🥚{egg_n}!'
                text2 = f'Поздравляем, у вас появился свой первый динозавр!\nВ данный момент яйцо инкубируется, а через 10 минут из него вылупится динозаврик!\nЧтобы посмотреть актуальную информацию о яйце, нажмите кнопку *🦖 Динозавр*!'
                text2 += "\n\n*Новичок!*\n\nДавай немного расскажу тебе об этом мире и как устроен бот!\n"
            else:
                text = f'🥚 | Choose a dinosaur egg!\n🦖 | You have chosen an egg 🥚{egg_n}!'
                text2 = f'Congratulations, you have your first dinosaur!\n At the moment the egg is incubating, and in 10 minutes a dinosaur will hatch out of it!To view up-to-date information about the egg, click *🦖 Dinosaur*!'
                text2 += '\n\n**Newbie!*\n\nlet me tell you a little about this world and how the bot works!\n'

            if bd_user['language_code'] == 'ru':
                text2 += "*┌* *Редкости 🎈*\n\n"
                text2 += "*├* События и динозавры делятся на редкости.\nЧем больше редкость, тем слаще награда.\n\n"
                text2 += "*├*  1. Обычная - 50%\n*├*  2. Необычная - 25%\n*├*  3. Редкая - 15%\n*├*  4. Мистическая - 9%\n*└*  5. Легендарная - 1%\n\n"
                text2 += "*┌* *Взаимодейтвия 🕹*\n\n"
                text2 += "*├* Для взаимодействия с динозарвом передите в `🕹 Действия`.\n\n"
                text2 += "*├*  1. Для того что бы покормить динозавра, вам требуется добыть пищу, нажмите на `🕹 Действия` > `🍕 Сбор пищи` и следуйте инструкциям.\n\n"
                text2 += "*├*  2. Для того чтобы покормить динозавра нажмите на `🕹 Действия` > `🍣 Покормить` и выберите подходящую пищу.\n\n"
                text2 += "*├*  3. Для повышения настроения динозавра треубется времени от времени развлекать динозавра. Перейдите `🕹 Действия` > `🎮 Развлечения` и следуйте указаниям.\n\n"
                text2 += "*├*  4. Чтобы возобновить силы динозавра, отправляйте его спать, `🕹 Действия` > `🌙 Уложить спать`\n\n"
                text2 += "*└*  5. Для повышения настроения, требуется держать потребность в еде, игры, сна в норме.\n\n"
                text2 += "*┌* *Профиль 🎮*\n"
                text2 += "*└*  Чтобы посмотреть инвентарь или узнать свою статистику, перейдите в `👁‍🗨 Профиль`\n\n"
                text2 += "*┌* *Настройки 🔧*\n\n"
                text2 += "*└*  В настройках вы можете переименовать динозавра, отключить уведомления или переключить язык.\n\n"
            else:
                text2 += "*┌* *Rarities 🎈*\n\n"
                text2 += "*├* Events and dinosaurs are divided into rarities.The greater the rarity, the sweeter the reward.\n\n"
                text2 += "*├* 1. Normal - 50%\n*├* 2. Unusual - 25%\n*├* 3. Rare - 15%\n*├* 4. Mystical - 9%\n*└* 5. Legendary - 1%\n\n"
                text2 += "*┌* *Interaction 🕹*\n\n"
                text2 += "*├* To interact with dinozarv, pass in `🕹 Actions`.\n\n"
                text2 += "*├* 1. In order to feed the dinosaur, you need to get food, click on `🕹 Actions` > `🍕 Food Collection` and follow the instructions.\n\n"
                text2 += "*├*  2. To feed the dinosaur, click on `🕹 Actions` > `🍣 Feed` and choose the appropriate food.\n\n"
                text2 += "*├* 3. To improve the mood of the dinosaur, it is necessary to entertain the dinosaur from time to time. Go to `🕹 Actions` > `🎮 Entertainment` and follow the instructions.\n\n"
                text2 += "*├* 4. To renew the dinosaur's powers, send it to sleep, `🕹 Action` > `🌙 Put to bed`\n\n"
                text2 += "*└* 5. To improve mood, it is required to keep the need for iodine, games, sleep normal.\n\n"
                text2 += "*┌* *Profile 🎮*\n"
                text2 += "*└* To view inventory or find out your statistics, go to `👁 Profile`\n\n"
                text2 += "*┌* *Settings 🔧*\n\n"
                text2 += "*└*  In the settings, you can rename the dinosaur, disable notifications, or switch the language.\n\n"

            bot.edit_message_caption(text, call.message.chat.id, call.message.message_id)
            bot.send_message(call.message.chat.id, text2, parse_mode = 'Markdown', reply_markup = markup(1, user))

    if call.data[:13] in ['90min_journey', '60min_journey', '30min_journey', '10min_journey']:

        bd_user['dinos'][ call.data[14:] ]['activ_status'] = 'journey'
        bd_user['dinos'][ call.data[14:] ]['journey_time'] = time.time() + 60 * int(call.data[:2])
        bd_user['dinos'][ call.data[14:] ]['journey_log'] = []
        users.update_one( {"userid": user.id}, {"$set": {'dinos': bd_user['dinos']}} )

        if bd_user['language_code'] == 'ru':
            text = f'🎈 | Если у динозавра хорошее настроение, он может принести обратно какие то вещи.\n\n🧶 | Во время путешествия, могут произойти разные ситуации, от них зависит результат путешествия.'
            text2 = f'🌳 | Вы отправили динозавра в путешествие на {call.data[:2]} минут.'

        else:
            text = f"🎈 | If the dinosaur is in a good mood, he can bring back some things.\n\n🧶 | During the trip, different situations may occur, the result of the trip depends on them."
            text2 = f"🌳 | You sent a dinosaur on a journey for {call.data[:2]} minutes."

        bot.edit_message_text(text2, call.message.chat.id, call.message.message_id)
        bot.send_message(call.message.chat.id, text, parse_mode = 'html', reply_markup = markup("actions", user))

    if call.data[:10] in ['1_con_game', '2_con_game', '3_con_game', '1_sna_game', '2_sna_game', '3_sna_game', '1_pin_game', '2_pin_game', '3_pin_game', '1_bal_game', '2_bal_game', '3_bal_game']:
        user = call.from_user
        bd_user = users.find_one({"userid": user.id})
        n_s = int(call.data[:1])
        dino_id = call.data[11:]
        if n_s == 1:
            time_m = random.randint(25, 60) * 60
        if n_s == 2:
            time_m = random.randint(60, 90) * 60
        if n_s == 3:
            time_m = random.randint(90, 120) * 60

        if bd_user['dinos'][dino_id]['activ_status'] != 'pass_active':
            return

        game = call.data[:5][-3:]

        if game == 'con':
            game = 'console'
            e_text = [ [ ['Динозавру надоело играть в консоль...'], ['The dinosaur is tired of playing the console...'] ], [ ['Динозавру немного надоело играть в консоль...'], ['The dinosaur is a little tired of playing the console...'] ], [ ['Динозавр довольно играет в консоль!'], ['The dinosaur is quite playing the game console!'] ] ]

        elif game == 'sna':
            game = 'snake'
            e_text = [ [ ['Динозавру надоело играть в воздушного змея...'], ['The dinosaur is tired of playing kite...'] ], [ ['Динозавру немного надоело играть в воздушного змея...'], ['The dinosaur is a little tired of playing kite...'] ], [ ['Динозавр довольно играет в воздушного змея!'], ['The dinosaur is pretty playing kite!'] ] ]

        elif game == 'pin':
            game = 'ping-pong'
            e_text = [ [ ['Динозавру надоело играть в пинг понг...'], ['The dinosaur is tired of playing ping pong...'] ], [ ['Динозавру немного надоело играть в пинг понг...'], ['The dinosaur is a little tired of playing ping pong...'] ], [ ['Динозавр довольно играет в пинг понг!'], ['Dinosaur is pretty playing ping pong!'] ] ]

        elif game == 'bal':
            game = 'ball'
            e_text = [ [ ['Динозавру надоело играть в мяч...'], ['The dinosaur is tired of playing ball...'] ], [ ['Динозавру немного надоело играть в мяч...'], ['The dinosaur got a little tired of playing ball...'] ], [ ['Динозавр довольно играет в мяч!'], ['The dinosaur is pretty playing ball!'] ] ]

        bd_user['dinos'][ dino_id ]['activ_status'] = 'game'
        if 'games' not in list(bd_user['dinos'][ dino_id ].keys()):
            bd_user['dinos'][ dino_id ]['games'] = []

        if len(bd_user['dinos'][ dino_id ]['games']) >= 3:
            bd_user['dinos'][ dino_id ]['games'].remove( bd_user['dinos'][ dino_id ]['games'][0] )

        bd_user['dinos'][ dino_id ]['games'].append(game)
        games = bd_user['dinos'][ dino_id ]['games'].copy()
        bd_user['dinos'][ dino_id ]['game_%'] = 1

        if len(games) == 1:
            bd_user['dinos'][ dino_id ]['game_%'] = 1

            if bd_user['language_code'] == 'ru':
                text2 = f'🎮 | {e_text[2][0][0]}'

            else:
                text2 = f"🎮 | {e_text[2][1][0]}"

        if len(games) == 2:

            if games[0] == games[1]:
                bd_user['dinos'][ dino_id ]['game_%'] = 0.5
                if bd_user['language_code'] == 'ru':
                    text2 = f"🎮 | {e_text[0][0][0]}, он получает штраф {bd_user['dinos'][ dino_id ]['game_%']}% в получении удовольствия от игры!"

                else:
                    text2 = f"🎮 | {e_text[0][1][0]}, he gets a {bd_user['dinos'][ dino_id ]['game_%']}% penalty in enjoying the game!"

            if games[0] != games[1]:
                bd_user['dinos'][ dino_id ]['game_%'] = 1

                if bd_user['language_code'] == 'ru':
                    text2 = f'🎮 | {e_text[2][0][0]}'

                else:
                    text2 = f"🎮 | {e_text[2][1][0]}"


        if len(games) == 3:

            if games[0] == games[1] and games[1] == games[2]:
                bd_user['dinos'][ dino_id ]['game_%'] = 0.5

                if bd_user['language_code'] == 'ru':
                    text2 = f"🎮 | {e_text[0][0][0]}, он получает штраф {bd_user['dinos'][ dino_id ]['game_%']}% в получении удовольствия от игры!"

                else:
                    text2 = f"🎮 | {e_text[0][1][0]}, he gets a {bd_user['dinos'][ dino_id ]['game_%']}% penalty in enjoying the game!"

            if games[0] == games[1] and games[1] != games[2] or games[0] == games[2] and games[0] != games[1] or games[0] != games[1] and games[1] == games[2]:
                bd_user['dinos'][ dino_id ]['game_%'] = 0.9

                if bd_user['language_code'] == 'ru':
                    text2 = f"🎮 | {e_text[1][0][0]}, он получает штраф {bd_user['dinos'][ dino_id ]['game_%']}% в получении удовольствия от игры!"

                else:
                    text2 = f"🎮 | {e_text[1][1][0]}, he gets a {bd_user['dinos'][ dino_id ]['game_%']}% penalty in enjoying the game!"

            if games[0] != games[1] and games[1] != games[2] and games[0] != games[2]:
                bd_user['dinos'][ dino_id ]['game_%'] = 1

                if bd_user['language_code'] == 'ru':
                    text2 = f'🎮 | {e_text[2][0][0]}'

                else:
                    text2 = f"🎮 | {e_text[2][1][0]}"


        bd_user['dinos'][ dino_id ]['game_time'] = time.time() + time_m
        users.update_one( {"userid": user.id}, {"$set": {'dinos': bd_user['dinos']}} )

        if bd_user['language_code'] == 'ru':

            text = f'🎮 | Чередуйте игры для избежания штрафа!'

        else:

            text = f"🎮 | Alternate games to avoid a penalty!"

        bot.edit_message_text(text2, call.message.chat.id, call.message.message_id)
        bot.send_message(call.message.chat.id, text, parse_mode = 'html', reply_markup = markup("games", user))

    if call.data in ['dead_answer1', 'dead_answer2', 'dead_answer3', 'dead_answer4']:

        user = call.from_user
        bd_user = users.find_one({"userid": user.id})

        if bd_user['language_code'] == 'ru':
            text =  f"К вам подходит человек в чёрном одеянии.\n\n"
            text += f"Вы видите, что у человека чёрные волосы и какой-то шрам на щеке, но его глаза не видны в тени шляпы.\n\n"
            text += f"*Личность:* - Здраствуйте, меня зовут { random.choice( ['мистер', 'доктор'] ) } { random.choice( ['Джеймс', 'Роберт', 'Винсент', 'Альберт'] ) }, а вас...\n\n"
            text += f"*Вы:* - ... {user.first_name}, {user.first_name} {user.last_name}, так меня зовут\n\n"
            text += f"*Личность:* - Прекрасно {user.first_name}, давно вы в нашем бизнесе? _улыбается_\n\n"
            text += f"*Вы:* - ...Что? Бизнес? О чем, вы говорите?!\n\n"
            text += f"*Личность:* - Понятно, понятно... Так и запишем. _Записывает что-то в блокнот_\n\n"
            text += f"*Вы:* - ...\n\n"
            text += f"*Личность:* - Давайте ближе к делу, мы предлагаем вам заключить с нами контракт, мы получаем ваши монеты и ресурсы, вы получаете яйцо с динозавром.\n\n"
            text += f"*Вы:* - Яяя, я не знаю...\n\n"
            text += f"*Вы:* - "
            b1 = ['❓ | Кто вы такой?', '❓ | Это законно?', '❓ | Кто "мы"?', '🧩 | У меня же нет выбора, так?']

        else:
            text = f"A man in a black robe approaches you.\n\n"
            text += f"You can see that the man has black hair and some kind of scar on his cheek, but his eyes are not visible in the shadow of the hat.\n\n"
            text += f"*Personality:* - Hello, my name is { random.choice(['mister', 'doctor'] ) } { random.choice( ['James', 'Robert', 'Vincent', 'Albert'] ) }, and you...\n\n"
            text += f"*You are:* - ... {user.first_name}, {user.first_name} {user.last_name}, that's my name\n\n"
            text += f"*Personality:* - Fine {user.first_name}, how long have you been in our business? _ulybaet_\n\n"
            text += f"*You are:* - ...What? Business? What are you talking about?!\n\n"
            text += f"*Personality:* - I see, I see... So we'll write it down. _ Writes something in notepad_\n\n"
            text += f"*You are:* - ...\n\n"
            text += f"*Personality:* - Let's get down to business, we offer you to sign a contract with us, we get your coins and resources, you get an egg with a dinosaur.\n\n"
            text += f"*You:* - I know, I don't know...\n\n"
            text += f"*You:* - "
            b1 = ['❓ | Who are you?', '❓ | Is it legal?', '❓ | Who are "we"?', "🧩 | I don't have a choice, right?"]

        if call.data == 'dead_answer1':
            text += b1[0]
            if bd_user['language_code'] == 'ru':
                text += f'\n\n*Личность:* - Кто я такой не имеет значения, важно лишь то... что я могу вам дать...\nВот контракт, подпишите'
            else:
                text += f'\n\n*Personality:* - Who I am does not matter, it only matters... what can I give you...\nHere is the contract, sign it'

        if call.data == 'dead_answer2':
            text += b1[1]
            if bd_user['language_code'] == 'ru':
                text += f'\n\n*Личность:* - Ха, ха, ха, как сказать...\nВот контракт, подпишите'
            else:
                text += f'\n\n*Personality:* - Ha, ha, ha, how to say it...\nHere is the contract, sign it'

        if call.data == 'dead_answer3':
            text += b1[2]
            if bd_user['language_code'] == 'ru':
                text += f'\n\n*Личность:* - Это не имеет значение, важно лишь то... что я могу вам дать...\nВот контракт, подпишите'
            else:
                text += f"\n\n*Personality:* - It doesn't matter, it just matters... what can I give you...\nHere is the contract, sign it"

        if call.data == 'dead_answer4':
            text += b1[3]
            if bd_user['language_code'] == 'ru':
                text += f'\n\n*Личность:* - Вы совершенно правы, вот контракт, подпишите'
            else:
                text += f'\n\n*Personality:* - You are absolutely right, here is the contract, sign it'

        mn = bd_user['coins'] / 100 * 85
        markup_inline = types.InlineKeyboardMarkup()

        if bd_user['language_code'] == 'ru':
            text += "\n\n\n"
            text += "     *Контракт*\n"
            text += f"{user.first_name} отдаёт: весь инвентарь, {mn} монет\n"
            text += f"{user.first_name} получает: 1х яйцо динозавра"
            markup_inline.add( types.InlineKeyboardButton(text= '✒ Подписать', callback_data = 'dead_restart') )
        else:
            text += "\n\n\n"
            text += "     *Contract*\n"
            text += f"{user.first_name} gives: all inventory, {mn} coins\n"
            text += f"{user.first_name} receives: 1x dinosaur egg"
            markup_inline.add( types.InlineKeyboardButton(text= '✒ Sign', callback_data = 'dead_restart') )

        bd_user['notifications']['ans_dead'] = mn
        users.update_one( {"userid": user.id}, {"$set": {'notifications': bd_user['notifications']}} )

        bot.edit_message_text(text, call.message.chat.id, call.message.message_id, reply_markup = markup_inline, parse_mode = 'Markdown')

    if call.data == 'dead_restart':
        user = call.from_user
        bd_user = users.find_one({"userid": user.id})

        if bd_user != None and len(bd_user['dinos']) == 0 and 'dead' in bd_user['notifications'] and bd_user['notifications']['dead'] == True:
            egg_n = str(random.choice(list(json_f['data']['egg'])))

            bd_user['dinos'][ user_dino_pn(bd_user) ] = {'status': 'incubation', 'incubation_time': time.time() + 30 * 60, 'egg_id': egg_n}
            bd_user['notifications']['dead'] = False
            bd_user['coins'] -= int(bd_user['notifications']['ans_dead'])
            del bd_user['notifications']['ans_dead']

            users.update_one( {"userid": user.id}, {"$set": {'dinos': bd_user['dinos']}} )
            users.update_one( {"userid": user.id}, {"$set": {'notifications': bd_user['notifications']}} )
            users.update_one( {"userid": user.id}, {"$set": {'coins': bd_user['coins']}} )
            users.update_one( {"userid": user.id}, {"$set": {'inventory': [] }} )


            if bd_user['language_code'] == 'ru':
                text = '✒ | Контракт подписан, динозавр инкубируется.'
            else:
                text = '✒ | The contract is signed, the dinosaur is incubating.'

            bot.send_message(user.id, text, parse_mode = 'Markdown', reply_markup = markup(1, user))

    # if call.data[:5] == 'item_':



print(f'Бот {bot.get_me().first_name} запущен!')
if bot.get_me().first_name == 'DinoGochi':
    thr1.start()
    thr_icub.start()
    thr_sleep.start()
    thr_game.start()
    thr_hunt.start()
    thr_journey.start()
# thr2.start()

bot.infinity_polling()
