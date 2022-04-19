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
    def main_pass():

        nn = 0
        t_st = int(time.time())
        members = users.find({ })
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

                                if random.randint(1,60) == 1:
                                    user['coins'] += random.randint(0,20)
                                    users.update_one( {"userid": user['userid']}, {"$set": {'coins': user['coins'] }} )

                        if user['dinos'][dino_id]['stats']['mood'] > 80:
                            if random.randint(1,60) == 1:
                                user['coins'] += random.randint(0,100)
                                users.update_one( {"userid": user['userid']}, {"$set": {'coins': user['coins'] }} )

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
    def main_sleep():

        nn = 0
        t_st = int(time.time())
        members = users.find({ })
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
    def main_game():

        nn = 0
        t_st = int(time.time())
        members = users.find({ })
        for user in members:

            dns_l = list(user['dinos'].keys()).copy()

            for dino_id in dns_l:
                dino = user['dinos'][dino_id]
                dinos_stats = {'game': 0, 'unv': 0}

                if dino['status'] == 'dino': #дино

                    if dino['activ_status'] == 'game':
                        nn += 1

                        if random.randint(1, 65) == 1: #unv
                            dinos_stats['unv'] -= random.randint(0,2)

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
    def main_hunting():

        nn = 0
        t_st = int(time.time())
        members = users.find({ })
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

                        if user['activ_items']['hunt'] == '15':
                            pr_hunt = 15
                        else:
                            pr_hunt = 20

                        r = random.randint(1, pr_hunt)
                        if r == 1:

                            if user['activ_items']['hunt'] == '31':
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
                                try:
                                    users.update_one( {"userid": user['userid']}, {"$inc": {f'dinos.{dino_id}.target': 1 }} )
                                except:
                                    users.update_one( {"userid": user['userid']}, {"$set": {f'dinos.{dino_id}.activ_status': 'pass_active' }} )

                                users.update_one( {"userid": user['userid']}, {"$push": {'inventory': item }} )

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
    def main(bot):
        nn = 0
        t_st = int(time.time())
        members = users.find({ })
        for user in members:
            nn += 1

            dns_l = list(user['dinos'].keys()).copy()
            lvl_ = 0

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

                        # if dino['activ_status'] == 'pass_active':
                        #
                        #     if user['dinos'][dino_id]['stats']['game'] > 60:
                        #         if dino['stats']['mood'] < 100:
                        #             if random.randint(1,15) == 1:
                        #                 dinos_stats['mood'] += random.randint(1,15)
                        #
                        #             if random.randint(1,60) == 1:
                        #                 user['coins'] += random.randint(0,100)
                        #
                        #     if user['dinos'][dino_id]['stats']['mood'] > 80:
                        #         if random.randint(1,60) == 1:
                        #             user['coins'] += random.randint(0,100)
                        #
                        #     if user['dinos'][dino_id]['stats']['unv'] <= 20 and user['dinos'][dino_id]['stats']['unv'] != 0:
                        #         if dino['stats']['mood'] > 0:
                        #             if random.randint(1,30) == 1:
                        #                 dinos_stats['mood'] -= random.randint(1,2)

                        elif dino['activ_status'] == 'journey':

                            if random.randint(1, 65) == 1: #unv
                                dinos_stats['unv'] -= random.randint(0,1)

                            if random.randint(1, 45) == 1: #unv
                                lvl_ += random.randint(0,20)

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
                                                            if fr_dino['activ_status'] == 'journey':
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

                                        item = functions.random_items(["1", "2", '25'], ['17', '18', '19'], ['26', '27', '28'], ["30", "32"], ["30", "32"])

                                        if mood_n == True:

                                            if user['language_code'] == 'ru':
                                                event = f"🧸 | Бегая по лесам, динозавр видит что-то похожее на сундук.\n>  Открыв его, он находит: {items_f['items'][item]['nameru']}!"
                                            else:
                                                event = f"🧸 | Running through the woods, the dinosaur sees something that looks like a chest.\n> Opening it, he finds: {items_f['items'][item]['nameen']}!"

                                            users.update_one( {"userid": user['userid']}, {"$push": {'inventory': item }} )

                                        if mood_n == False:

                                            if user['language_code'] == 'ru':
                                                event = '❌ | Редкое событие отменено из-за плохого настроения!'
                                            else:
                                                event = '❌ | A rare event has been canceled due to a bad mood!'

                                    elif event == 'random_items_leg':

                                        item = functions.random_items(["4", '14', "15", "16"], ["4", '14', "15", "16"], ["30", "32", '34', "19"], ["37", "19"], ["21", "37"])
                                        if mood_n == True:

                                            if user['language_code'] == 'ru':
                                                event = f"🧸 | Бегая по горам, динозавр видит что-то похожее на сундук.\n>  Открыв его, он находит: {items_f['items'][item]['nameru']}!"
                                            else:
                                                event = f"🧸 | Running through the mountains, the dinosaur sees something similar to a chest.\n> Opening it, he finds: {items_f['items'][item]['nameen']}!"

                                            users.update_one( {"userid": user['userid']}, {"$push": {'inventory': item }} )

                                        if mood_n == False:

                                            if user['language_code'] == 'ru':
                                                event = '❌ | Мистическое событие отменено из-за плохого настроения!'
                                            else:
                                                event = '❌ | The mystical event has been canceled due to a bad mood!'

                                    elif event == 'egg':

                                        # eggs = ["3", '20', '21', '22', '23', '24']
                                        egg = functions.random_items(['21', "3"], ['20', "3"], ['22'], ['23', "3"], ['24', "3"])
                                        # egg = random.choice(eggs)
                                        if mood_n == True:

                                            if user['language_code'] == 'ru':
                                                event = f"🧸 | Бегая по по пещерам, динозавр видит что-то похожее на сундук.\n>  Открыв его, он находит: {items_f['items'][egg]['nameru']}!"
                                            else:
                                                event = f"🧸 | Running through the caves, the dinosaur sees something similar to a chest.\n> Opening it, he finds: {items_f['items'][egg]['nameen']}!"

                                            users.update_one( {"userid": user['userid']}, {"$push": {'inventory': egg }} )

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
                                        if user['activ_items']['journey'] != '14':

                                            mood = random.randint(1, 15)
                                            user['dinos'][dino_id]['stats']['mood'] -= mood

                                            if user['language_code'] == 'ru':
                                                event = f'🌨 | Прошёлся дождь, настроение понижено на {mood}%'
                                            else:
                                                event = f"🌨 | It has rained, the mood is lowered by {mood}%"

                                        else:

                                            if user['language_code'] == 'ru':
                                                event = f'🌨 | Прошёлся дождь, настроение не ухудшено.'
                                            else:
                                                event = f"🌨 | It rained, the mood is not worsened."


                                    elif event == '-eat':
                                        eat = random.randint(1, 10)
                                        heal = random.randint(1, 3)
                                        dinos_stats['eat'] -= eat
                                        dinos_stats['heal'] -= heal

                                        if user['language_code'] == 'ru':
                                            event = f'🍤 | Динозавр нашёл что-то вкусненькое и съел это, еда оказалась испорчена. Динозавр теряет {eat}% еды и {heal}% здоровья.'
                                        else:
                                            event = f"🍤 | The dinosaur found something delicious and ate it, the food was spoiled. Dinosaur loses {eat}% of food and {heal}% health."

                                    elif event == 'toxic_rain':
                                        heal = random.randint(1, 5)
                                        dinos_stats['heal'] -= heal

                                        if user['language_code'] == 'ru':
                                            event = f"⛈ | Динозавр попал под токсичный дождь!"
                                        else:
                                            event = f"⛈ | The dinosaur got caught in the toxic rain!"


                                    elif event == 'fight':

                                        unv = random.randint(1, 10)
                                        dinos_stats['unv'] -= unv

                                        if user['activ_items']['journey'] != '29' and random.randint(1,2) == 1:
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


                                    elif event == 'lose_items':
                                        user = users.find_one({"userid": user['userid']})
                                        items = user['inventory']
                                        item = random.choice(items)
                                        if mood_n == True:
                                            user['inventory'].remove(item)

                                            if user['language_code'] == 'ru':
                                                event = f"❗ | Бегая по лесам, динозавр обронил {items_f['items'][item]['nameru']}\n>  Предмет потерян!"
                                            else:
                                                event = f"❗ | Running through the woods, the dinosaur dropped {items_f['items'][item]['nameen']}\n>  The item is lost!"

                                            users.update_one( {"userid": user['userid']}, {"$set": {'inventory': user['inventory'] }} )

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


                if lvl_ != 0:
                    user['lvl'][1] += lvl_
                    expp = 5 * user['lvl'][0] * user['lvl'][0] + 50 * user['lvl'][0] + 100
                    if user['lvl'][0] < 100:
                        if user['lvl'][1] >= expp:
                            user['lvl'][0] += 1
                            user['lvl'][1] = user['lvl'][1] - expp

                            if user['lvl'][0] == 5:
                                if 'referal_system' in user.keys():
                                    if 'friend' in user['referal_system'].keys():
                                        egg = random.choice(['20', '22'])
                                        rf_fr = users.find_one({"userid": user['referal_system']['friend']})

                                        users.update_one( {"userid": rf_fr['userid']}, {"$push": {'inventory': egg }} )

                    users.update_one( {"userid": user['userid']}, {"$set": {'lvl': user['lvl'] }} )

        print(f'Проверка - {int(time.time()) - t_st}s {nn}u')
        functions.check_data('main', 0, int(time.time() - t_st) )
        functions.check_data('main', 1, int(time.time()) )
        functions.check_data('us', 0, nn )
