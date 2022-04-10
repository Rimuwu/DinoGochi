import telebot
from telebot import types
import pymongo
import sys
import random
import json

sys.path.append("..")
import config

client = pymongo.MongoClient(config.CLUSTER_TOKEN)
users = client.bot.users

with open('items.json', encoding='utf-8') as f:
    items_f = json.load(f)

with open('dino_data.json', encoding='utf-8') as f:
    json_f = json.load(f)

class functions:
    json_f = json_f
    items_f = items_f

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
        del user['dinos'][str(dino_id_remove)]
        user['dinos'][functions.user_dino_pn(user)] = {'dino_id': dino_id, "status": 'dino', 'activ_status': 'pass_active', 'name': dino['name'], 'stats':  {"heal": 100, "eat": random.randint(70, 100), 'game': random.randint(50, 100), 'mood': random.randint(7, 100), "unv": 100}, 'games': []}

        users.update_one( {"userid": user['userid']}, {"$set": {'dinos': user['dinos']}} )

    @staticmethod
    def notifications_manager(bot, notification, user, arg = None, dino_id = '0', met = 'send'):

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
                    else:
                        text = f'💥 | {chat.first_name}, your dinosaur.... Died...'
                        nl = '🧩 Project: Rebirth'

                    markup = types.ReplyKeyboardMarkup(resize_keyboard = True)
                    markup.add(nl)

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
