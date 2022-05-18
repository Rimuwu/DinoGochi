import telebot
from telebot import types
import random
import json
import pymongo
import time
import os
import sys
import pprint
from functions import functions
from memory_profiler import memory_usage

sys.path.append("..")
import config


client = pymongo.MongoClient(config.CLUSTER_TOKEN)
users = client.bot.users

with open('data/items.json', encoding='utf-8') as f:
    items_f = json.load(f)

with open('data/dino_data.json', encoding='utf-8') as f:
    json_f = json.load(f)

class checks:

    @staticmethod
    def check_dead_users(bot):
        act1 = 0
        act2 = 0
        act3 = 0
        members = users.find({ 'dinos': {'$eq': {} } })

        for user in members:

            try:
                notactivity_time = int(time.time()) - int(user['last_m'])
            except:
                users.update_one( {"userid": user['userid']}, {"$set": {'last_m': int(time.time()) - 604800 }} )
                user['last_m'] = int(time.time()) - 604800
                notactivity_time = int(time.time()) - int(user['last_m'])

            if notactivity_time >= 604800 and len(user['dinos']) == 0: #7 дней не активности

                try:

                    if user['language_code'] == 'ru':
                        text = f"🦕 | {bot.get_chat( user['userid'] ).first_name}, мы скучаем по тебе 😥, ты уже очень давно не пользовался ботом ({functions.time_end( notactivity_time )})!\n\n❤ | Давай сного будем играть, путешествовать и развлекаться вместе! Мы с нетерпением ждём тебя!"
                    else:
                        text = f"🦕 | {bot.get_chat( user['userid'] ).first_name}, we miss you 😥, you haven't used the bot for a long time ({functions.time_end( notactivity_time )})!\n\n❤ | Let's play, travel and have fun together! We are looking forward to seeing you!"


                    bot.send_message(user['userid'], text)
                    act3 += 1

                    users.update_one( {"userid": user['userid']}, {"$set": {'last_m': int(time.time()) }} )
                    user['notifications']['dead_user'] = False

                    users.update_one( {"userid": user['userid']}, {"$set": {'notifications': user['notifications'] }} )


                except Exception as error:

                    if str(error) in ['A request to the Telegram API was unsuccessful. Error code: 403. Description: Forbidden: bot was blocked by the user', 'A request to the Telegram API was unsuccessful. Error code: 403. Description: Forbidden: user is deactivated']:
                        # пользователь заблокировал бота, удаляем из базы.
                        users.delete_one({"userid": user['userid']})
                        act2 += 1


                    else:
                        print('WARNING in dead check users, 7 days check\n' + str(error))


            elif notactivity_time >= 172800 and len(user['dinos']) == 0: #2 дня не активнсоти

                if 'dead_user' not in user['notifications'].keys() or user['notifications']['dead_user'] == False:

                    try:

                        if user['language_code'] == 'ru':
                            text = f"🦕 | Хей {bot.get_chat( user['userid'] ).first_name}, мы уже довольно давно с тобой не виделись ({functions.time_end( notactivity_time )})!\n\n🦄 | Пока тебя не было, в боте появилось куча всего интересного и произошло много событий! Мы сного ждём тебя в игре и будем рады твоей активности! ❤"
                        else:
                            text = f"🦕 | Hey {bot.get_chat( user['userid'] ).first_name}, we haven't seen you for quite a while ({functions.time_end( notactivity_time, True )})!\n\n🦄 | When you weren't there, a bunch of interesting things appeared in the bot and a lot of events happened! We are waiting for you a lot in the game and we will be glad of your activity! ❤"

                        bot.send_message(user['userid'], text)
                        act3 += 1
                        user['notifications']['dead_user'] = True

                        users.update_one( {"userid": user['userid']}, {"$set": {'notifications': user['notifications'] }} )

                    except Exception as error:
                        if str(error) in ['A request to the Telegram API was unsuccessful. Error code: 403. Description: Forbidden: bot was blocked by the user']:
                            # пользователь заблокировал бота, дадим ему возможность подумать ещё пару дней.
                            act1 += 1


                        else:
                            print('WARNING in dead check users, 2 days check\n' + str(error))

        #print('Предупреждено - нет ответа -', act1, '\n', 'Удалено - ', act2,  '\n', 'Получили ув: ', act3 )


    @staticmethod
    def check_memory():

        functions.check_data('memory', 0, int(memory_usage()[0]) )
        functions.check_data('memory', 1, int(time.time()) )

    @staticmethod
    def check_incub(bot): #проверка каждые 5 секунд
        nn = 0
        t_st = int(time.time())
        members = users.find({ 'dinos': {'$ne': {} } })

        for user in members:
            dns_l = list(user['dinos'].keys()).copy()

            for dino_id in dns_l:
                dino = user['dinos'][dino_id]
                if dino['status'] == 'incubation': #инкубация
                    nn += 1
                    if dino['incubation_time'] - int(time.time()) <= 60*5 and dino['incubation_time'] - int(time.time()) > 0: #уведомление за 5 минут

                        if functions.notifications_manager(bot, '5_min_incub', user, None, dino_id, 'check') == False:
                            functions.notifications_manager(bot, "5_min_incub", user, dino, dino_id)


                    elif dino['incubation_time'] - int(time.time()) <= 0:

                        functions.notifications_manager(bot, "5_min_incub", user, dino, dino_id, met = 'delete')

                        if 'quality' in dino.keys():
                            functions.random_dino(user, dino_id, dino['quality'])
                        else:
                            functions.random_dino(user, dino_id)
                        functions.notifications_manager(bot, "incub", user, dino_id)

        functions.check_data('incub', 0, int(time.time() - t_st) )
        functions.check_data('incub', 1, int(time.time()) )
        functions.check_data('incub', 2, nn)

    @staticmethod
    def rayt(members):
        mr_l, lv_l = [], []

        loc_users = list(members).copy()
        mr_l_r = list(sorted(loc_users, key=lambda x: x['coins'], reverse=True))
        lv_l_r = list(sorted(loc_users, key=lambda x: (x['lvl'][0] - 1) * (5 * x['lvl'][0] * x['lvl'][0] + 50 * x['lvl'][0] + 100) +  x['lvl'][1], reverse=True))

        for i in mr_l_r:
            mr_l.append( {'userid': i['userid'], 'coins': i['coins']} )

        for i in lv_l_r:
            lv_l.append( {'userid': i['userid'], 'lvl': i['lvl']} )

        functions.rayt_update('save', [mr_l, lv_l])


    @staticmethod
    def check_notif(bot, members): #проверка каждые 5 секунд
        nn = 0
        t_st = int(time.time())

        for user in members:
            nn += 1
            dns_l = list(user['dinos'].keys()).copy()

            for dino_id in dns_l:
                dino = user['dinos'][dino_id]
                if dino['status'] == 'dino': #дино

                    if dino['activ_status'] == 'sleep':

                        if user['dinos'][dino_id]['stats']['unv'] >= 100:
                            user['dinos'][dino_id]['activ_status'] = 'pass_active'
                            functions.notifications_manager(bot, 'woke_up', user, None, dino_id, 'send')

                            try:
                                del user['dinos'][dino_id]['sleep_start']
                            except:
                                pass

                            users.update_one( {"userid": user['userid']}, {"$set": {f'dinos.{dino_id}': user['dinos'][dino_id] }} )


                        if 'sleep_type' in user['dinos'][dino_id].keys() and user['dinos'][dino_id]['sleep_type'] == 'short':

                            if user['dinos'][dino_id]['sleep_time'] - int(time.time()) <= 0:

                                user['dinos'][dino_id]['activ_status'] = 'pass_active'
                                functions.notifications_manager(bot, 'woke_up', user, None, dino_id, 'send')

                                del user['dinos'][dino_id]['sleep_type']
                                del user['dinos'][dino_id]['sleep_time']
                                users.update_one( {"userid": user['userid']}, {"$set": {f'dinos.{dino_id}': user['dinos'][dino_id] }} )


                    elif dino['activ_status'] == 'game':

                        if int(dino['game_time'] - time.time()) <= 0:
                            user['dinos'][dino_id]['activ_status'] = 'pass_active'
                            functions.notifications_manager(bot, 'game_end', user, None, dino_id, 'send')

                            del user['dinos'][ dino_id ]['game_time']
                            del user['dinos'][ dino_id ]['game_%']
                            users.update_one( {"userid": user['userid']}, {"$set": {f'dinos.{dino_id}': user['dinos'][dino_id] }} )

                    elif dino['activ_status'] == 'journey':

                        if int(dino['journey_time']-time.time()) <= 0:
                            user['dinos'][dino_id]['activ_status'] = 'pass_active'

                            functions.notifications_manager(bot, "journey_end", user, user['dinos'][ dino_id ]['journey_log'], dino_id = dino_id)

                            del user['dinos'][ dino_id ]['journey_time']
                            del user['dinos'][ dino_id ]['journey_log']
                            users.update_one( {"userid": user['userid']}, {"$set": {f'dinos.{dino_id}': user['dinos'][dino_id] }} )

                    elif dino['activ_status'] == 'hunting':
                        if dino['target'][0] >= dino['target'][1]:
                            del user['dinos'][ dino_id ]['target']
                            del user['dinos'][ dino_id ]['h_type']
                            user['dinos'][dino_id]['activ_status'] = 'pass_active'

                            functions.notifications_manager(bot, "hunting_end", user, dino_id = dino_id)
                            users.update_one( {"userid": user['userid']}, {"$set": {f'dinos.{dino_id}': user['dinos'][dino_id] }} )


                    if user['dinos'][dino_id]['stats']['mood'] <= 70:
                        if functions.notifications_manager(bot, "need_mood", user, dino_id = dino_id, met = 'check') == False:
                            functions.notifications_manager(bot, "need_mood", user, user['dinos'][dino_id]['stats']['mood'], dino_id = dino_id)

                    if user['dinos'][dino_id]['stats']['game'] <= 50:
                        if functions.notifications_manager(bot, "need_game", user, dino_id = dino_id, met = 'check') == False:
                            functions.notifications_manager(bot, "need_game", user, user['dinos'][dino_id]['stats']['game'], dino_id = dino_id)

                    if user['dinos'][dino_id]['stats']['eat'] <= 40:
                        if functions.notifications_manager(bot, "need_eat", user, dino_id = dino_id, met = 'check') == False:
                            functions.notifications_manager(bot, "need_eat", user, user['dinos'][dino_id]['stats']['eat'], dino_id = dino_id)

                    if user['dinos'][dino_id]['stats']['unv'] <= 30:
                        if functions.notifications_manager(bot, "need_unv", user, dino_id = dino_id, met = 'check') == False:
                            functions.notifications_manager(bot, "need_unv", user, user['dinos'][dino_id]['stats']['unv'], dino_id = dino_id)

                    if user['dinos'][dino_id]['stats']['mood'] >= 80:
                        functions.notifications_manager(bot, 'need_mood', user, dino_id = dino_id, met = 'delete')

                    if user['dinos'][dino_id]['stats']['game'] >= 80:
                        functions.notifications_manager(bot, 'need_game', user, dino_id = dino_id, met = 'delete')

                    if user['dinos'][dino_id]['stats']['eat'] >= 50:
                        functions.notifications_manager(bot, 'need_eat', user, dino_id = dino_id, met = 'delete')

                    if user['dinos'][dino_id]['stats']['unv'] >= 40:
                        functions.notifications_manager(bot, 'need_unv', user, dino_id = dino_id, met = 'delete')

                    if user['dinos'][dino_id]['stats']['heal'] <= 0:
                        del user['dinos'][dino_id]

                        if user['lvl'][0] >= 5:
                            functions.add_item_to_user(user, '21')

                        functions.notifications_manager(bot, "dead", user, dino_id = dino_id)

                        users.update_one( {"userid": user['userid']}, {"$set": {f'dinos': user['dinos'] }} )

        # print(f'Проверка уведомлений - {int(time.time()) - t_st}s {nn}u')
        functions.check_data('notif', 0, int(time.time() - t_st) )
        functions.check_data('notif', 1, int(time.time()) )

    @staticmethod
    def main_pass(members):

        nn = 0
        t_st = int(time.time())
        # members = users.find({ })
        for user in members:

            dns_l = list(user['dinos'].keys()).copy()

            for dino_id in dns_l:
                dino = user['dinos'][dino_id]
                dinos_stats = {'mood': 0}

                if dino['status'] == 'dino': #дино

                    if dino['activ_status'] == 'pass_active':
                        nn += 1

                        if user['dinos'][dino_id]['stats']['game'] > 60:
                            if dino['stats']['mood'] < 100:
                                if random.randint(1,15) == 1:
                                    dinos_stats['mood'] += random.randint(1,15)

                                if random.randint(1,10) == 1:
                                    users.update_one( {"userid": user['userid']}, {"$inc": {'coins': random.randint(0,20) }} )

                        if user['dinos'][dino_id]['stats']['mood'] > 80:
                            if random.randint(1,60) == 1:
                                users.update_one( {"userid": user['userid']}, {"$inc": {'coins': random.randint(0,20) }} )

                        if user['dinos'][dino_id]['stats']['unv'] <= 20 and user['dinos'][dino_id]['stats']['unv'] != 0:
                            if dino['stats']['mood'] > 0:
                                if random.randint(1,30) == 1:
                                    dinos_stats['mood'] -= random.randint(1,2)

                        bd_user = users.find_one({"userid": user['userid']})
                        if bd_user != None:
                            if len(bd_user['dinos']) != 0:
                                for i in dinos_stats.keys():
                                    if dinos_stats[i] != 0:
                                        users.update_one( {"userid": user['userid']}, {"$inc": {f'dinos.{dino_id}.stats.{i}': dinos_stats[i] }} )

        # print(f'Проверка пассивность - {int(time.time() - t_st)}s {nn}u')
        functions.check_data('main_pass', 0, int(time.time() - t_st) )
        functions.check_data('main_pass', 1, int(time.time()))
        functions.check_data('main_pass', 2, nn )

    @staticmethod
    def main_sleep(members):

        nn = 0
        t_st = int(time.time())
        # members = users.find({ })
        for user in members:

            dns_l = list(user['dinos'].keys()).copy()

            for dino_id in dns_l:
                dino = user['dinos'][dino_id]
                dinos_stats = {'game': 0, 'unv': 0, 'mood': 0, 'heal': 0, 'eat': 0}

                if dino['status'] == 'dino': #дино

                    if dino['activ_status'] == 'sleep':
                        nn += 1

                        if 'sleep_type' not in user['dinos'][dino_id].keys() or user['dinos'][dino_id]['sleep_type'] == 'long':

                            if user['dinos'][dino_id]['stats']['unv'] < 100:
                                if random.randint(1,80) == 1:
                                    dinos_stats['unv'] += random.randint(1,2)

                        else:

                            if user['dinos'][dino_id]['stats']['unv'] < 100:
                                if random.randint(1,30) == 1:
                                    dinos_stats['unv'] += random.randint(1,2)

                        if user['dinos'][dino_id]['stats']['game'] < 40:
                            if random.randint(1,40) == 1:
                                dinos_stats['game'] += random.randint(1,2)

                        if user['dinos'][dino_id]['stats']['mood'] < 50:
                            if random.randint(1,40) == 1:
                                dinos_stats['mood'] += random.randint(1,2)

                        if user['dinos'][dino_id]['stats']['heal'] < 100:
                            if user['dinos'][dino_id]['stats']['eat'] > 50:
                                if random.randint(1,45) == 1:
                                    dinos_stats['heal'] += random.randint(1,2)
                                    dinos_stats['eat'] -= random.randint(0,1)

                        bd_user = users.find_one({"userid": user['userid']})
                        if bd_user != None:
                            if len(bd_user['dinos']) != 0:
                                for i in dinos_stats.keys():
                                    if dinos_stats[i] != 0:
                                        users.update_one( {"userid": user['userid']}, {"$inc": {f'dinos.{dino_id}.stats.{i}': dinos_stats[i] }} )

        # print(f'Проверка сон - {int(time.time() - t_st)}s {nn}u')
        functions.check_data('main_sleep', 0, int(time.time() - t_st) )
        functions.check_data('main_sleep', 1, int(time.time()))
        functions.check_data('main_sleep', 2, nn )

    @staticmethod
    def main_game(members):

        nn = 0
        t_st = int(time.time())
        # members = users.find({ })
        for user in members:

            dns_l = list(user['dinos'].keys()).copy()

            for dino_id in dns_l:
                dino = user['dinos'][dino_id]
                dinos_stats = {'game': 0, 'unv': 0}

                if dino['status'] == 'dino': #дино

                    if dino['activ_status'] == 'game':
                        nn += 1

                        if random.randint(1, 65) == 1: #unv
                            dinos_stats['unv'] -= random.randint(0,1)

                        if random.randint(1, 45) == 1: #unv

                            user['lvl'][1] += random.randint(0,20)
                            users.update_one( {"userid": user['userid']}, {"$set": {'lvl': user['lvl'] }} )

                        if user['dinos'][dino_id]['stats']['game'] < 100:
                            if random.randint(1,30) == 1:
                                dinos_stats['game'] += int(random.randint(2,15) * user['dinos'][dino_id]['game_%'])

                        bd_user = users.find_one({"userid": user['userid']})
                        if bd_user != None:
                            if len(bd_user['dinos']) != 0:
                                for i in dinos_stats.keys():
                                    if dinos_stats[i] != 0:
                                        users.update_one( {"userid": user['userid']}, {"$inc": {f'dinos.{dino_id}.stats.{i}': dinos_stats[i] }} )

        # print(f'Проверка игра - {int(time.time() - t_st)}s {nn}u')
        functions.check_data('main_game', 0, int(time.time() - t_st) )
        functions.check_data('main_game', 1, int(time.time()))
        functions.check_data('main_game', 2, nn )

    @staticmethod
    def main_hunting(members):

        nn = 0
        t_st = int(time.time())
        # members = users.find({ })
        for user in members:

            dns_l = list(user['dinos'].keys()).copy()

            for dino_id in dns_l:
                dino = user['dinos'][dino_id]
                dinos_stats = {'unv': 0}

                if dino['status'] == 'dino': #дино

                    if dino['activ_status'] == 'hunting':
                        nn += 1

                        if random.randint(1, 45) == 1:

                            user['lvl'][1] += random.randint(0,20)
                            users.update_one( {"userid": user['userid']}, {"$set": {'lvl': user['lvl'] }} )

                        if random.randint(1, 65) == 1: #unv
                            dinos_stats['unv'] -= random.randint(0,1)

                        if user['activ_items']['hunt'] != None and user['activ_items']['hunt']['item_id'] == '15':
                            pr_hunt = 15
                        else:
                            pr_hunt = 20

                        r = random.randint(1, pr_hunt)
                        if r == 1:

                            if user['activ_items']['hunt'] != None and user['activ_items']['hunt']['item_id'] == '31':
                                col_l1 = ['27', '11', "35"]
                                col_l2 = ['6', '11', "35"]
                                col_l3 = ['6', "35"]

                                all_l1 = ['27', '11', "26", "12", "28", "13", '2', "35"]
                                all_l2 = ['6', '11', '5', "12", '7', "13", "19", "35"]
                                all_l3 = ['6', '5', '7', '18', "35"]
                            else:
                                col_l1 = ['27', '11']
                                col_l2 = ['6', '11']
                                col_l3 = ['6']

                                all_l1 = ['27', '11', "26", "12", "28", "13", '2']
                                all_l2 = ['6', '11', '5', "12", '7', "13", "19"]
                                all_l3 = ['6', '5', '7', '18']


                            if dino['h_type'] == 'all':
                                item = functions.random_items(['9', '8', "10", '2'], ['27', '9', "26", '8', "28", "10", '2'], all_l1, all_l2, all_l3)

                            if dino['h_type'] == 'collecting':
                                item = functions.random_items(['9'], ['27', '9'], col_l1, col_l2, col_l3)

                            if dino['h_type'] == 'hunting':
                                item = functions.random_items(['8'], ["26", '8'], ["26", "12"], ['5', "12"], ['5'])

                            if dino['h_type'] == 'fishing':
                                item = functions.random_items(["10"], ["28", "10"], ["28", "13"], ['7', "13"], ['7'])

                            i_count = functions.random_items([int(ii) for ii in range(1, 3)], [int(ii) for ii in range(1, 3)], [int(ii) for ii in range(1, 4)], [int(ii) for ii in range(1, 5)], [int(ii) for ii in range(1, 6)])
                            for i in list(range(i_count)):
                                dino['target'][0] += 1

                                functions.add_item_to_user(user, item)

                            users.update_one( {"userid": user['userid']}, {"$set": {f'dinos.{dino_id}.target': dino['target'] }} )

                        bd_user = users.find_one({"userid": user['userid']})
                        if bd_user != None:
                            if len(bd_user['dinos']) != 0:
                                for i in dinos_stats.keys():
                                    if dinos_stats[i] != 0:
                                        users.update_one( {"userid": user['userid']}, {"$inc": {f'dinos.{dino_id}.stats.{i}': dinos_stats[i] }} )

        # print(f'Проверка охота - {int(time.time()) - t_st}s {nn}u')
        functions.check_data('main_hunt', 0, int(time.time() - t_st) )
        functions.check_data('main_hunt', 1, int(time.time()))
        functions.check_data('main_hunt', 2, nn )

    @staticmethod
    def main_journey(bot, members):

        nn = 0
        t_st = int(time.time())
        # members = users.find({ })
        for user in members:

            dns_l = list(user['dinos'].keys()).copy()
            lvl_ = 0

            for dino_id in dns_l:
                dino = user['dinos'][dino_id]
                dinos_stats = {'heal': 0, 'eat': 0, 'game': 0, 'mood': 0, 'unv': 0}

                if dino['status'] == 'dino': #дино

                    if dino['activ_status'] == 'journey':
                        nn += 1

                        if random.randint(1, 65) == 1: #unv
                            dinos_stats['unv'] -= random.randint(0,1)

                        if random.randint(1, 45) == 1: #unv
                            lvl_ += random.randint(0,20)

                        if user['activ_items']['journey'] != None and user['activ_items']['journey']['item_id'] == '45':
                            tick = [1, 25]
                        else:
                            tick = [1, 30]

                        r_e_j = random.randint(tick[0], tick[1])
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
                                    events = ['+eat', 'sleep', 'u_coins', 'friend_meet']
                                elif r_event in list(range(76,91)): #редкое соб
                                    events = ['random_items', 'b_coins']
                                elif r_event in list(range(91,100)): #мистическое соб
                                    events = ['random_items_leg', 'y_coins']
                                else: #легендарное соб
                                    events = ['egg', 'l_coins']

                                event = random.choice(events)

                                if event == 'friend_meet':
                                    fr_d = {}

                                    sh_friends = user['friends']['friends_list']
                                    random.shuffle(sh_friends)
                                    for friend in sh_friends:
                                        if fr_d == {}:
                                            bd_friend = users.find_one({"userid": int(friend)})
                                            if bd_friend != None:

                                                try:
                                                    bot_friend = bot.get_chat( bd_friend['userid'] )
                                                except:
                                                    bot_friend = None

                                                if bot_friend != None:
                                                    for k_dino in bd_friend['dinos'].keys():
                                                        fr_dino = bd_friend['dinos'][k_dino]
                                                        if 'activ_status' in fr_dino.keys() and fr_dino['activ_status'] == 'journey':
                                                            fr_d['friend_bd'] = bd_friend
                                                            fr_d['friend_in_bot'] = bot_friend
                                                            fr_d['dino_id'] = k_dino

                                        if fr_d != {}:
                                            break

                                    if fr_d == {}:

                                        if user['language_code'] == 'ru':
                                            event = f'🦕 | Динозавр гулял по знакомым тропинкам, но не увидел знакомых динозавров...'
                                        else:
                                            event = f"🦕 | The dinosaur was walking along familiar paths, but did not see familiar dinosaurs..."

                                    else:
                                        try:
                                            this_user = bot.get_chat(user['userid'])
                                        except:
                                            this_user = None

                                        if this_user != None:
                                            mood = random.randint(1, 20)
                                            dinos_stats['mood'] += mood
                                            fr_d['friend_bd']['dinos'][ fr_d['dino_id'] ]['stats']['mood'] += mood

                                            if user['language_code'] == 'ru':
                                                event = f"🦕 | Гуляя по знакомым тропинкам, динозавр встречает {fr_d['friend_bd']['dinos'][ fr_d['dino_id'] ]['name']} (динозавр игрока {fr_d['friend_in_bot'].first_name})\n> Динозавры крайне рады друг другу!\n   > Динозавры получают бонус {mood}% к настроению!"
                                            else:
                                                event = f"🦕 | Walking along familiar paths, the dinosaur meets {fr_d['friend_bd']['dinos'][ fr_d['dino_id'] ]['name']} (the player's dinosaur {fr_d['friend_in_bot'].first_name})\n> Dinosaurs are extremely happy with each other!\n > Dinosaurs get a bonus {mood}% to mood!"

                                            if fr_d['friend_bd']['language_code'] == 'ru':
                                                fr_event = f"🦕 | Гуляя по знакомым тропинкам, динозавр встречает {user['dinos'][dino_id]['name']} (динозавр игрока {this_user.first_name})\n> Динозавры крайне рады друг другу!\n   > Динозавры получают бонус {mood}% к настроению!"
                                            else:
                                                fr_event = f"🦕 | Walking along familiar paths, the dinosaur meets {user['dinos'][dino_id]['name']} (the player's dinosaur {this_user.first_name})\n> Dinosaurs are extremely happy with each other!\n > Dinosaurs get a bonus {mood}% to mood!"

                                            users.update_one( {"userid": fr_d['friend_bd']['userid']}, {"$push": {f'dinos.{dino_id}.journey_log': fr_event }} )

                                        else:

                                            if user['language_code'] == 'ru':
                                                event = f'🦕 | Динозавр гулял по знакомым тропинкам, но не увидел знакомых динозавров...'
                                            else:
                                                event = f"🦕 | The dinosaur was walking along familiar paths, but did not see familiar dinosaurs..."


                                if event == 'sunny':
                                    mood = random.randint(1, 15)
                                    dinos_stats['mood'] += mood

                                    if user['language_code'] == 'ru':
                                        event = f'☀ | Солнечно, настроение динозавра повысилось на {mood}%'
                                    else:
                                        event = f"☀ | Sunny, the dinosaur's mood has increased by {mood}%"

                                elif event == '+eat':
                                    eat = random.randint(1, 10)
                                    dinos_stats['eat'] += eat

                                    if user['language_code'] == 'ru':
                                        event = f'🥞 | Динозавр нашёл что-то вкусненькое и съел это!'
                                    else:
                                        event = f"🥞 | The dinosaur found something delicious and ate it!"

                                elif event == 'sleep':
                                    unv = random.randint(1, 5)
                                    dinos_stats['unv'] += unv

                                    if user['language_code'] == 'ru':
                                        event = f'💭 | Динозавр смог вздремнуть по дороге.'
                                    else:
                                        event = f"💭 | Динозавр смог вздремнуть по дороге."

                                elif event == 'random_items':

                                    item = functions.random_items(["1", "2", '25'], ['17', '18', '19'], ['26', '27', '28'], ["30", "32", '44'], ["30", "32", "39", "41", "43", '44', "46"])

                                    if mood_n == True:

                                        if user['language_code'] == 'ru':
                                            event = f"🧸 | Бегая по лесам, динозавр видит что-то похожее на сундук.\n>  Открыв его, он находит: {items_f['items'][item]['nameru']}!"
                                        else:
                                            event = f"🧸 | Running through the woods, the dinosaur sees something that looks like a chest.\n> Opening it, he finds: {items_f['items'][item]['nameen']}!"

                                        functions.add_item_to_user(user, item)

                                    if mood_n == False:

                                        if user['language_code'] == 'ru':
                                            event = '❌ | Редкое событие отменено из-за плохого настроения!'
                                        else:
                                            event = '❌ | A rare event has been canceled due to a bad mood!'

                                elif event == 'random_items_leg':

                                    item = functions.random_items(["4", '14', "15", "16"], ["4", '14', "15", "16"], ["30", "32", '34', "19", "39", "41", '44'], ["37", "19", "39", "41", "43", '44', "46"], ["21", "37", "39", "41", "43", '44', "46"])
                                    if mood_n == True:

                                        if user['language_code'] == 'ru':
                                            event = f"🧸 | Бегая по горам, динозавр видит что-то похожее на сундук.\n>  Открыв его, он находит: {items_f['items'][item]['nameru']}!"
                                        else:
                                            event = f"🧸 | Running through the mountains, the dinosaur sees something similar to a chest.\n> Opening it, he finds: {items_f['items'][item]['nameen']}!"

                                        functions.add_item_to_user(user, item)

                                    if mood_n == False:

                                        if user['language_code'] == 'ru':
                                            event = '❌ | Мистическое событие отменено из-за плохого настроения!'
                                        else:
                                            event = '❌ | The mystical event has been canceled due to a bad mood!'

                                elif event == 'egg':


                                    egg = functions.random_items(['21', "3"], ['20', "3"], ['22'], ['23', "3"], ['24', "3"])

                                    if mood_n == True:

                                        if user['language_code'] == 'ru':
                                            event = f"🧸 | Бегая по по пещерам, динозавр видит что-то похожее на сундук.\n>  Открыв его, он находит: {items_f['items'][egg]['nameru']}!"
                                        else:
                                            event = f"🧸 | Running through the caves, the dinosaur sees something similar to a chest.\n> Opening it, he finds: {items_f['items'][egg]['nameen']}!"

                                        functions.add_item_to_user(user, egg)

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

                                        users.update_one( {"userid": user['userid']}, {"$inc": {'coins': coins }} )

                                        if user['language_code'] == 'ru':
                                            event = f'💎 | Ходя по тропинкам, динозавр находит мешочек c монетками.\n>   Вы получили {coins} монет.'
                                        else:
                                            event = f'💎 | Walking along the paths, the dinosaur finds a bag with coins.\n> You have received {coins} coins.'

                                    if mood_n == False:
                                        if user['language_code'] == 'ru':
                                            event = '❌ | Cобытие отменено из-за плохого настроения!'
                                        else:
                                            event = '❌ | Event has been canceled due to a bad mood!'

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
                                    if user['activ_items']['journey'] != None and user['activ_items']['journey']['item_id'] != '14':

                                        mood = random.randint(1, 15)
                                        dinos_stats['mood'] -= mood

                                        if user['language_code'] == 'ru':
                                            event = f'🌨 | Прошёлся дождь, настроение понижено на {mood}%'
                                        else:
                                            event = f"🌨 | It has rained, the mood is lowered by {mood}%"

                                    else:

                                        if user['language_code'] == 'ru':
                                            event = f'🌨 | Прошёлся дождь, настроение не ухудшено.'
                                        else:
                                            event = f"🌨 | It rained, the mood is not worsened."


                                if event == '-eat':
                                    eat = random.randint(1, 10)
                                    heal = random.randint(1, 3)
                                    dinos_stats['eat'] -= eat
                                    dinos_stats['heal'] -= heal

                                    if user['language_code'] == 'ru':
                                        event = f'🍤 | Динозавр нашёл что-то вкусненькое и съел это, еда оказалась испорчена. Динозавр теряет {eat}% еды и {heal}% здоровья.'
                                    else:
                                        event = f"🍤 | The dinosaur found something delicious and ate it, the food was spoiled. Dinosaur loses {eat}% of food and {heal}% health."

                                if event == 'toxic_rain':
                                    heal = random.randint(1, 5)
                                    dinos_stats['heal'] -= heal

                                    if user['language_code'] == 'ru':
                                        event = f"⛈ | Динозавр попал под токсичный дождь!"
                                    else:
                                        event = f"⛈ | The dinosaur got caught in the toxic rain!"

                                if event == 'fight':

                                    unv = random.randint(1, 10)
                                    dinos_stats['unv'] -= unv

                                    if (user['activ_items']['journey'] != None and user['activ_items']['journey']['item_id'] != '29') and random.randint(1,2) == 1:
                                        heal = random.randint(1, 5)
                                        dinos_stats['heal'] -= heal
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


                                if event == 'lose_items':
                                    user = users.find_one({"userid": user['userid']})
                                    items = user['inventory']
                                    item = random.choice(items)
                                    if mood_n == True:

                                        if user['language_code'] == 'ru':
                                            event = f"❗ | Бегая по лесам, динозавр обронил {items_f['items'][item]['nameru']}\n>  Предмет потерян!"
                                        else:
                                            event = f"❗ | Running through the woods, the dinosaur dropped {items_f['items'][item]['nameen']}\n>  The item is lost!"

                                        user['inventory'].remove(item)
                                        users.update_one( {"userid": user['userid']}, {"$set": {'inventory': user['inventory'] }} )

                                    if mood_n == False:

                                        if user['language_code'] == 'ru':
                                            event = '🍭 | Отрицательное событие отменено из-за хорошего настроения!'
                                        else:
                                            event = '🍭 | Negative event canceled due to good mood!'

                                if event[2:] == 'coins':

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

                                        users.update_one( {"userid": user['userid']}, {"$inc": {'coins': coins * -1 }} )

                                        if user['language_code'] == 'ru':
                                            event = f'💎 | Ходя по тропинкам, динозавр обронил несколько монет из рюкзака\n>   Вы потеряли {coins} монет.'
                                        else:
                                            event = f'💎 | Walking along the paths, the dinosaur dropped some coins from his backpack.   You have lost {coins} coins.'

                                    if mood_n == False:
                                        if user['language_code'] == 'ru':
                                            event = '🍭 | Отрицательное событие отменено из-за хорошего настроения!'
                                        else:
                                            event = '🍭 | Negative event canceled due to good mood!'

                            users.update_one( {"userid": user['userid']}, {"$push": {f'dinos.{dino_id}.journey_log': event }} )

                        bd_user = users.find_one({"userid": user['userid']})
                        if bd_user != None:
                            if len(bd_user['dinos']) != 0:
                                for i in dinos_stats.keys():
                                    if dinos_stats[i] != 0 or bd_user['dinos'][dino_id]['stats'][i] > 100 or bd_user['dinos'][dino_id]['stats'][i] < 0:
                                        if dinos_stats[i] + bd_user['dinos'][dino_id]['stats'][i] > 100:
                                            users.update_one( {"userid": user['userid']}, {"$set": {f'dinos.{dino_id}.stats.{i}': 100 }} )

                                        elif dinos_stats[i] + bd_user['dinos'][dino_id]['stats'][i] < 0:
                                            users.update_one( {"userid": user['userid']}, {"$set": {f'dinos.{dino_id}.stats.{i}': 0 }} )

                                        else:
                                            users.update_one( {"userid": user['userid']}, {"$inc": {f'dinos.{dino_id}.stats.{i}': dinos_stats[i] }} )

            expp = 5 * user['lvl'][0] * user['lvl'][0] + 50 * user['lvl'][0] + 100
            if lvl_ != 0 or user['lvl'][1] >= expp:
                user['lvl'][1] += lvl_
                if user['lvl'][0] < 101:
                    if user['lvl'][1] >= expp:
                        user['lvl'][0] += 1
                        user['lvl'][1] = user['lvl'][1] - expp

                        if user['lvl'][0] == 5:
                            if 'referal_system' in user.keys():
                                if 'friend' in user['referal_system'].keys():
                                    egg = random.choice(['20', '22'])
                                    rf_fr = users.find_one({"userid": user['referal_system']['friend']})

                                    functions.add_item_to_user(rf_fr, egg)

                users.update_one( {"userid": user['userid']}, {"$set": {'lvl': user['lvl'] }} )



        # print(f'Проверка охота - {int(time.time()) - t_st}s {nn}u')
        functions.check_data('main_journey', 0, int(time.time() - t_st) )
        functions.check_data('main_journey', 1, int(time.time()))
        functions.check_data('main_journey', 2, nn )

    @staticmethod
    def main(members):

        nn = 0
        t_st = int(time.time())
        # members = users.find({ })
        for user in members:
            nn += 1

            dns_l = list(user['dinos'].keys()).copy()

            if len(dns_l) != 0:
                for dino_id in dns_l:
                    dino = user['dinos'][dino_id]
                    dinos_stats = {'heal': 0, 'eat': 0, 'game': 0, 'mood': 0, 'unv': 0}

                    if dino['status'] == 'dino': #дино
                    #stats  - pass_active (ничего) sleep - (сон) journey - (путешествиеф)

                        if dino['activ_status'] != 'sleep':
                            if random.randint(1, 65) == 1: #eat
                                dinos_stats['eat'] -= random.randint(1,2)
                        else:
                            if random.randint(1, 90) == 1: #eat
                                dinos_stats['eat'] -= random.randint(1,2)

                        if dino['activ_status'] != 'game':
                            if random.randint(1, 60) == 1: #game
                                dinos_stats['game'] -= random.randint(1,2)

                        if dino['activ_status'] != 'sleep':
                            if random.randint(1, 130) == 1: #unv
                                dinos_stats['unv'] -= random.randint(1,2)

                        if user['dinos'][dino_id]['stats']['game'] < 40 and user['dinos'][dino_id]['stats']['game'] > 10:
                            if dino['stats']['mood'] > 0:
                                if random.randint(1,30) == 1:
                                    dinos_stats['mood'] -= random.randint(1,2)

                        if user['dinos'][dino_id]['stats']['game'] < 10:
                            if dino['stats']['mood'] > 0:
                                if random.randint(1,15) == 1:
                                    dinos_stats['mood'] -= 3

                        if user['dinos'][dino_id]['stats']['unv'] <= 10 and user['dinos'][dino_id]['stats']['eat'] <= 20:
                            if random.randint(1,30) == 1:
                                dinos_stats['heal'] -= random.randint(1,2)

                        if user['dinos'][dino_id]['stats']['eat'] <= 20:
                            if user['dinos'][dino_id]['stats']['unv'] <= 10 and user['dinos'][dino_id]['stats']['eat'] <= 20:
                                pass
                            else:
                                if random.randint(1,40) == 1:
                                    dinos_stats['heal'] -= random.randint(0,1)

                        if user['dinos'][dino_id]['stats']['eat'] > 80:
                            if dino['stats']['mood'] < 100:
                                if random.randint(1,15) == 1:
                                    dinos_stats['mood'] += random.randint(1,10)

                        if user['dinos'][dino_id]['stats']['eat'] <= 40 and user['dinos'][dino_id]['stats']['eat'] != 0:
                            if dino['stats']['mood'] > 0:
                                if random.randint(1,30) == 1:
                                    dinos_stats['mood'] -= random.randint(1,2)

                        if user['dinos'][dino_id]['stats']['eat'] > 80 and user['dinos'][dino_id]['stats']['unv'] > 70 and user['dinos'][dino_id]['stats']['mood'] > 50:

                            if random.randint(1,6) == 1:
                                dinos_stats['heal'] += random.randint(1,4)
                                dinos_stats['eat'] -= random.randint(0,1)

                        bd_user = users.find_one({"userid": user['userid']})
                        if bd_user != None:
                            if len(bd_user['dinos']) != 0:
                                for i in dinos_stats.keys():
                                    if dinos_stats[i] != 0 or bd_user['dinos'][dino_id]['stats'][i] > 100 or bd_user['dinos'][dino_id]['stats'][i] < 0:
                                        if dinos_stats[i] + bd_user['dinos'][dino_id]['stats'][i] > 100:
                                            users.update_one( {"userid": user['userid']}, {"$set": {f'dinos.{dino_id}.stats.{i}': 100 }} )

                                        elif dinos_stats[i] + bd_user['dinos'][dino_id]['stats'][i] < 0:
                                            users.update_one( {"userid": user['userid']}, {"$set": {f'dinos.{dino_id}.stats.{i}': 0 }} )

                                        else:
                                            users.update_one( {"userid": user['userid']}, {"$inc": {f'dinos.{dino_id}.stats.{i}': dinos_stats[i] }} )

        # print(f'Проверка - {int(time.time()) - t_st}s {nn}u')
        functions.check_data('main', 0, int(time.time() - t_st) )
        functions.check_data('main', 1, int(time.time()) )
        functions.check_data('main', 2, nn )
