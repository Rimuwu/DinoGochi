import json
import random
import sys
import time

from mods.classes import Dungeon, Functions

sys.path.append("..")
import config

client = config.CLUSTER_CLIENT
users, dungeons, management = client.bot.users, client.bot.dungeons, client.bot.management

with open('json/items.json', encoding='utf-8') as f: items_f = json.load(f)

with open('json/dino_data.json', encoding='utf-8') as f: json_f = json.load(f)

class CheckFunction:

    def pre_quest(bot, user, uss):
        if int(time.time()) - user['last_m'] <= 5400:

            if random.randint(1, 10) == 5:
                us_m = uss.copy()

                us_m.remove(user)
                m_bd_user = random.choice(us_m)

                try:
                    m_user = bot.get_chat(m_bd_user['userid'])
                except:
                    m_user = None

                if m_user != None:

                    if user['language_code'] == 'ru':
                        messages = [
                            "Говорят в подземельях бродят страшные монстры...",
                            "Мой динозавр может завалить 20 таких!", "Да не разсказывай, ха ха ха!",
                            "Говорят предметы в подземелье высокого класса...",
                            "Я вчера ходил, мне выпал какой то светящийся камень...",
                            "А вы видели какая у этого гоблина страшная рожа?!", "Да я таких на завтрак ем!",
                            "Как они бьются с этими тупыми мечами?", "Я не вернусь туда!",
                            "Ты что, боишься спустится в подземелье?!",
                            "Мой друг Бари зашёл туда 21 год назад, я всё ещё жду...",
                            "Я вчера видел как Герой выходил из подземелья с золотым мечём!",
                            "Не рассказывай сказки, нету там никого страшного!",
                            "Расскажи как ты потерял свой глаз в этом подземелье...",
                            "Да не боюсь я! Просто монет на вход нет...",
                            "Какой это будет раз, 21-ый? И много ты оттуда вынес уже?", "Да э...", "Да нееет...",
                            "Шутишь?", "АХА ХА ХА!", "Хо хо хо...", "Нарываешься?!", "Выпьем?!",
                            "Хорошая новость, наливай!", "Хрю хрю", "Демон...."
                        ]

                        messages_special = [
                            'Налил бы кто выпить...', "Сухо на душе и во рту...",
                            "Не осталось добрых людей в этом городе..."
                        ]


                    else:
                        messages = [
                            "They say there are scary monsters roaming in the dungeons...",
                            "My dinosaur can knock down 20 of them!", "Don't tell me, ha ha ha!",
                            "They say objects in a high-class dungeon...",
                            "I went yesterday, I got some kind of glowing stone...",
                            "Did you see what a scary face this goblin has?!", "Yes, I eat these for breakfast!",
                            "How do they fight with these blunt swords?", "I'm not going back there!",
                            "Are you afraid to go down to the dungeon?!",
                            "My friend Bari went there 21 years ago, I'm still waiting...",
                            "I saw the Hero coming out of the dungeon with a golden sword yesterday!",
                            "Don't tell fairy tales, there is no one scary there!",
                            "Tell me how you lost your eye in this dungeon...",
                            "Yes, I'm not afraid! There are just no coins to enter...",
                            "What time will it be, the 21st? And how much have you taken out of there already?",
                            "Yes uh...", "Yes nooo...", "Are you kidding?", "AHA HA HA!", "Ho ho ho...",
                            "Are you running into it?!", "Drink?!", "Good news, pour!", "Oink oink", "Demon...."
                        ]

                        messages_special = [
                            'Someone would pour a drink...', 'Dry in the soul and in the mouth...',
                            'There are no good people left in this city...'
                        ]

                    random.shuffle(messages)
                    random.shuffle(messages_special)

                    if random.randint(1, 5) == 2:

                        message = random.choice(messages_special)
                        text = f"<a href='tg://user?id={m_user.id}'>{m_user.first_name}</a>: {message}"

                        try:
                            bot.send_message(user['userid'], text, parse_mode='HTML')
                        except:
                            pass

                    else:

                        message = random.choice(messages)
                        text = f"<a href='tg://user?id={m_user.id}'>{m_user.first_name}</a>: {message}"

                        try:
                            bot.send_message(user['userid'], text, parse_mode='HTML')
                        except:
                            pass

            if random.randint(1, 15) == 5:

                if 'user_dungeon' in user.keys():
                    if 'quests' in user['user_dungeon'].keys():
                        if len(user['user_dungeon']['quests']['activ_quests']) < user['user_dungeon']['quests'][
                            'max_quests']:

                            q = Dungeon.create_quest(user)
                            users.update_one({"userid": user['userid']},
                                                {"$push": {'user_dungeon.quests.activ_quests': q}})

                            if user['language_code'] == 'ru':
                                text = f"📜 | Вам был выдан квест {q['name']}!"
                            else:
                                text = f"📜 | You have been given a quest {q['name']}!"

                            try:
                                bot.send_message(user['userid'], text)
                            except:
                                pass

    def main(bot, user):
        dns_l = list(user['dinos'].keys()).copy()

        if len(dns_l) != 0:
            for dino_id in dns_l:
                dino = user['dinos'][dino_id]
                dinos_stats = {'heal': 0, 'eat': 0, 'game': 0, 'mood': 0, 'unv': 0}

                if dino.get('status', 0) == 'dino':

                    if dino['activ_status'] != 'freezing':

                        if dino['activ_status'] == 'sleep':
                            if random.randint(1, 20) == 10:  # eat
                                dinos_stats['eat'] -= random.randint(1, 2)
                        else:
                            if random.randint(1, 17) == 8:  # eat
                                dinos_stats['eat'] -= random.randint(1, 2)

                        if dino['activ_status'] != 'game':
                            if random.randint(1, 10) == 5:  # game
                                dinos_stats['game'] -= random.randint(1, 2)

                        if dino['activ_status'] != 'sleep':
                            if random.randint(1, 25) == 12:  # unv
                                dinos_stats['unv'] -= random.randint(1, 2)

                        if user['dinos'][dino_id]['stats']['game'] < 40 and user['dinos'][dino_id]['stats'][
                            'game'] > 10:
                            if dino['stats']['mood'] > 0:
                                if random.randint(1, 5) == 3:
                                    dinos_stats['mood'] -= random.randint(1, 2)

                        if user['dinos'][dino_id]['stats']['game'] < 10:
                            if dino['stats']['mood'] > 0:
                                if random.randint(1, 3) == 2:
                                    dinos_stats['mood'] -= 3

                        if user['dinos'][dino_id]['stats']['unv'] <= 10 and user['dinos'][dino_id]['stats'][
                            'eat'] <= 20:
                            if random.randint(1, 17) == 10:
                                dinos_stats['heal'] -= random.randint(0, 1)

                        if user['dinos'][dino_id]['stats']['eat'] > 80:
                            if dino['stats']['mood'] < 100:
                                if random.randint(1, 3) == 2:
                                    dinos_stats['mood'] += random.randint(1, 10)

                        if user['dinos'][dino_id]['stats']['eat'] <= 40 and user['dinos'][dino_id]['stats']['eat'] != 0:
                            if dino['stats']['mood'] > 0:
                                if random.randint(1, 5) == 2:
                                    dinos_stats['mood'] -= random.randint(1, 2)

                        if user['dinos'][dino_id]['stats']['eat'] > 80 and user['dinos'][dino_id]['stats'][
                            'unv'] > 70 and user['dinos'][dino_id]['stats']['mood'] > 50:

                            if random.randint(1, 2) == 1:
                                dinos_stats['heal'] += random.randint(1, 4)
                                dinos_stats['eat'] -= random.randint(0, 1)

                        bd_user = users.find_one({"userid": user['userid']})
                        if bd_user != None:
                            if len(bd_user['dinos']) != 0:
                                for i in dinos_stats.keys():
                                    stats = bd_user['dinos'][dino_id]['stats']

                                    if dinos_stats[i] != 0 or stats[i] > 100 or  stats[i] < 0:

                                        if dinos_stats[i] + stats[i] > 100:
                                            users.update_one({"userid": user['userid']},
                                                {"$set": {f'dinos.{dino_id}.stats.{i}': 100}})

                                        elif dinos_stats[i] + stats[i] < 0:
                                            users.update_one({"userid": user['userid']},
                                                {"$set": {f'dinos.{dino_id}.stats.{i}': 0}})

                                        else:
                                            users.update_one({"userid": user['userid']},
                                                {"$inc": {f'dinos.{dino_id}.stats.{i}': dinos_stats[i]}})

        expp = 5 * user['lvl'][0] * user['lvl'][0] + 50 * user['lvl'][0] + 100
        if user['lvl'][1] >= expp:
            if user['lvl'][0] < 101:
                if user['lvl'][1] >= expp:
                    user['lvl'][0] += 1
                    user['lvl'][1] = user['lvl'][1] - expp

                    if user['lvl'][0] == 5:
                        if 'referal_system' in user.keys():
                            if 'friend' in user['referal_system'].keys():
                                egg = random.choice(['20', '22'])
                                rf_fr = users.find_one({"userid": user['referal_system']['friend']})

                                if rf_fr != None:
                                    Functions.add_item_to_user(rf_fr, egg)

            Functions.notifications_manager(bot, 'lvl_up', user, arg=user['lvl'][0])
            users.update_one({"userid": user['userid']}, {"$set": {'lvl': user['lvl']}})

    def user_journey(bot, user):
        dns_l = list(user['dinos'].keys()).copy()
        lvl_ = 0

        for dino_id in dns_l:
            dino = user['dinos'][dino_id]
            dinos_stats = {'heal': 0, 'eat': 0, 'game': 0, 'mood': 0, 'unv': 0}

            if dino.get('status', 0) == 'dino':  # дино

                if dino['activ_status'] == 'journey':

                    if random.randint(1, 13) == 7:  # unv
                        dinos_stats['unv'] -= random.randint(0, 1)

                    if random.randint(1, 8) == 4:
                        lvl_ += random.randint(0, 20)

                    if Functions.acc_check(bot, user, '45', dino_id, False):
                        tick = [1, 5]
                    else:
                        tick = [1, 7]

                    r_e_j = random.randint(tick[0], tick[1])
                    if r_e_j == 1:
                        rr = random.randint(1, 3)
                        if rr != 1:

                            nd = random.randint(40, 75)
                            if dino['stats']['mood'] >= nd:
                                mood_n = True
                                Functions.acc_check(bot, user, '45', dino_id, True)  # снимает прочность у мешочка

                            else:
                                mood_n = False

                            r_event = random.randint(1, 1000)
                            if r_event >= 1 and r_event <= 500:  # обычное соб
                                events = ['sunny', 'm_coins', 'breeze']  # , 'trade'
                            elif r_event > 500 and r_event <= 800:  # необычное соб
                                events = ['+eat', 'sleep', 'u_coins', 'friend_meet', 'deadlock']
                            elif r_event > 800 and r_event <= 950:  # редкое соб
                                events = ['random_items', 'b_coins', 'deadlock', 'friend_game']
                            elif r_event > 950 and r_event <= 995:  # мистическое соб
                                events = ['random_items_leg', 'y_coins']
                            elif r_event > 995 and r_event <= 1000:  # легендарное соб
                                events = ['egg', 'l_coins']

                            event = random.choice(events)

                            if event == 'trade':
                                pass

                            if event == 'deadlock':

                                tp = random.randint(1, 10)
                                if tp > 1:

                                    if user['language_code'] == 'ru':
                                        event = f'💢 | Динозавр забрёл в тупик, он развернулся и пошёл обратно...'
                                    else:
                                        event = f"💢 | The dinosaur wandered into a dead end, he turned around and went back..."

                                else:

                                    if user['language_code'] == 'ru':
                                        names = ['Федя', 'Вова', 'Алёша', 'Тима', 'Сеня', 'Макс', 'Вера', 'Аня', 'Юля',
                                                 'Гоша', 'Мария', 'Марьяна', 'Олег', 'Оля', 'Маша', 'Петя', 'Слава',
                                                 'Вадим', 'Йося']

                                        locations = ['Тихий лес', "Забытый дом", "Дорога мёртвых", "Лес забытых",
                                                     "Пещеры славы", "Магический лес", 'Город воспоминаний',
                                                     "Торговый путь", "Торговый городок", "Дорога великих",
                                                     'Дорога пропавших']
                                    else:
                                        names = ['Fedya', 'Vova', 'Alyosha', 'Tima', 'Senya', 'Max', 'Vera', 'Anya',
                                                 'Julia', 'Gosha', 'Maria', 'Mariana', 'Oleg', 'Olya', 'Masha', 'Petya',
                                                 'Slava', 'Vadim', 'Yosya']

                                        locations = ['Silent Forest', 'Forgotten House', 'Road of the Dead',
                                                     'Forest of the Forgotten', 'Caves of Glory', 'Magic Forest',
                                                     'City of Memories', 'Trade Route', 'Trading Town',
                                                     'Road of the Great', 'Road of the Lost']

                                    fr_d = {}
                                    sh_friends = user['friends']['friends_list']
                                    for friend in sh_friends:
                                        if fr_d == {}:
                                            bd_friend = users.find_one({"userid": int(friend)})
                                            if bd_friend != None:
                                                if len(bd_friend['dinos']) > 0:
                                                    for d in bd_friend['dinos']:
                                                        dd = bd_friend['dinos'][d]
                                                        if dd['status'] == 'dino':
                                                            names.append(dd['name'])

                                    sf_name = random.choice(names)

                                    if user['language_code'] == 'ru':
                                        event = f'❓ | Динозавр забрёл в тупик, вдруг он видит проходящего мимо динозавра..\n'
                                    else:
                                        event = f"The dinosaur wandered into a dead end, he turned around and went in the opposite direction...\n"

                                    if user['language_code'] == 'ru':
                                        event += f'>  {sf_name}: Хей, я вижу ты забрёл в тупик... Я могу показать тебе 2 пути, только выбери куда ты хочешь пойти...\n'
                                    else:
                                        event += f">  {sf_name}: Hey, I see you've wandered into a dead end... I can show you 2 ways, just choose where you want to go...\n"

                                    loc1 = random.choice(locations)
                                    loc2 = random.choice(locations)
                                    vr = random.randint(1, 2)

                                    while loc1 == loc2:
                                        loc2 = random.choice(locations)

                                    if vr == 1:
                                        event += f'>  ✅ {loc1} ❌ {loc2}\n'
                                        loc = loc1
                                    else:
                                        event += f'>  ❌ {loc1} ✅ {loc2}\n'
                                        loc = loc2

                                    if loc in ['Тихий лес', "Забытый дом", "Лес забытых", "Пещеры славы",
                                               "Магический лес", 'Город воспоминаний', "Торговый городок",
                                               'Silent Forest', 'Forgotten House', 'Forest of the Forgotten',
                                               'Caves of Glory', 'Magic Forest', 'City of Memories', 'Trading Town']:
                                        eve_l = ['sunny', 'breeze', '+eat', 'sleep', 'friend_meet', 'random_items',
                                                 'random_items_leg']
                                        eve = random.choice(eve_l)

                                        if user['language_code'] == 'ru':
                                            event += f'>  Динозавр выбрал путь ведущий в {loc}, и вот что случилось когда он туда пришёл >'
                                        else:
                                            event += f">  The dinosaur chose the path leading to {loc}, and that's what happened when he got there >"

                                    elif loc in ["Торговый путь", "Trade way"]:
                                        eve_l = ['b_coins', 'y_coins', 'random_items', 'l_coins', 'friend_meet', '+eat',
                                                 'sunny', 'breeze']
                                        eve = random.choice(eve_l)
                                        if user['language_code'] == 'ru':
                                            event += f'>  Динозавр выбрал {loc}, и вот что случилось пока он по нему шёл >'
                                        else:
                                            event += f">  The dinosaur chose {loc}, and that's what happened while he was walking on it >"

                                    else:
                                        eve_l = ['sunny', 'breeze', '+eat', 'sleep', 'friend_meet']
                                        eve = random.choice(eve_l)

                                        if user['language_code'] == 'ru':
                                            event += f'>  Динозавр выбрал {loc}, и вот что случилось пока он по нему шёл >'
                                        else:
                                            event += f">  The dinosaur chose {loc}, and that's what happened while he was walking on it >"

                                    users.update_one({"userid": user['userid']},
                                        {"$push": {f'dinos.{dino_id}.journey_log': event}})
                                    event = eve

                            if event == 'friend_game':
                                fr_d = {}

                                sh_friends = user['friends']['friends_list']
                                random.shuffle(sh_friends)
                                for friend in sh_friends:

                                    if fr_d == {}:
                                        bd_friend = users.find_one({"userid": int(friend)})
                                        if bd_friend != None:

                                            try:
                                                bot_friend = bot.get_chat(bd_friend['userid'])
                                            except:
                                                bot_friend = None

                                            if bot_friend != None:
                                                for k_dino in bd_friend['dinos'].keys():
                                                    fr_dino = bd_friend['dinos'][k_dino]
                                                    if 'activ_status' in fr_dino.keys() and fr_dino[
                                                        'activ_status'] == 'journey':
                                                        fr_d['friend_bd'] = bd_friend
                                                        fr_d['friend_in_bot'] = bot_friend
                                                        fr_d['dino_id'] = k_dino

                                    if fr_d != {}:
                                        break

                                if fr_d == {}:

                                    if user['language_code'] == 'ru':
                                        event = f'🎮 🦕 | Динозавр забрёл на игровую площадку, но она оказалась пуста...'
                                    else:
                                        event = f"🎮 🦕 | The dinosaur wandered into the playground, but it turned out to be empty..."

                                else:
                                    try:
                                        this_user = bot.get_chat(user['userid'])
                                    except:
                                        this_user = None

                                    if this_user != None:
                                        game_p = random.randint(1, 10)
                                        dinos_stats['game'] += game_p
                                        fr_d['friend_bd']['dinos'][fr_d['dino_id']]['stats']['game'] += game_p

                                        if user['language_code'] == 'ru':
                                            game = random.choice(
                                                ['нарды', "шашки", "карты", "мяч", "футбол", "лото", "d&d",
                                                 "воздушного змея"])

                                            event = f"🎮 🦕 | Динозавр забрёл на игровую площадку, на ней оказался {fr_d['friend_bd']['dinos'][fr_d['dino_id']]['name']} (динозавр игрока {fr_d['friend_in_bot'].first_name})\n> Динозавры решили сыграть в {game}!\n  > Динозавры получают бонус {game_p}% к игре!"

                                        else:

                                            game = random.choice(
                                                ['backgammon', "checkers", "cards", "ball", "football", "lotto", "d&d",
                                                 "kite"])

                                            event = f"🦕 | The dinosaur wandered into the playground, found himself on it {fr_d['friend_bd']['dinos'][fr_d['dino_id']]['name']} (the player's dinosaur {fr_d['friend_in_bot'].first_name})\n> Dinosaurs decided to play in {game}!\n  > Dinosaurs get a bonus {game_p}% to the game!"

                                        if fr_d['friend_bd']['language_code'] == 'ru':
                                            game = random.choice(
                                                ['нарды', "шашки", "карты", "мяч", "футбол", "лото", "d&d",
                                                 "воздушного змея"])

                                            fr_event = f"🎮 🦕 | Динозавр забрёл на игровую площадку, на ней оказался {user['dinos'][dino_id]['name']} (динозавр игрока {this_user.first_name})\n> Динозавры решили сыграть в {game}!\n  > Динозавры получают бонус {game_p}% к игре!"

                                        else:
                                            game = random.choice(
                                                ['backgammon', "checkers", "cards", "ball", "football", "lotto", "d&d",
                                                 "kite"])

                                            fr_event = f"🦕 | The dinosaur wandered into the playground, found himself on it {user['dinos'][dino_id]['name']} (the player's dinosaur {this_user.first_name})\n> Dinosaurs decided to play in {game}!\n  > Dinosaurs get a bonus {game_p}% to the game!"

                                        users.update_one({"userid": fr_d['friend_bd']['userid']},
                                                         {"$push": {f'dinos.{fr_d["dino_id"]}.journey_log': fr_event}})

                                    else:

                                        if user['language_code'] == 'ru':
                                            event = f'🎮 🦕 | Динозавр забрёл на игровую площадку, но она оказалась пуста...'
                                        else:
                                            event = f"🎮 🦕 | The dinosaur wandered into the playground, but it turned out to be empty..."

                            if event == 'friend_meet':
                                fr_d = {}

                                sh_friends = user['friends']['friends_list']
                                random.shuffle(sh_friends)
                                for friend in sh_friends:
                                    if fr_d == {}:
                                        bd_friend = users.find_one({"userid": int(friend)})
                                        if bd_friend != None:

                                            try:
                                                bot_friend = bot.get_chat(bd_friend['userid'])
                                            except:
                                                bot_friend = None

                                            if bot_friend != None:
                                                for k_dino in bd_friend['dinos'].keys():
                                                    fr_dino = bd_friend['dinos'][k_dino]
                                                    if 'activ_status' in fr_dino.keys() and fr_dino[
                                                        'activ_status'] == 'journey':
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
                                        fr_d['friend_bd']['dinos'][fr_d['dino_id']]['stats']['mood'] += mood

                                        if user['language_code'] == 'ru':
                                            event = f"🦕 | Гуляя по знакомым тропинкам, динозавр встречает {fr_d['friend_bd']['dinos'][fr_d['dino_id']]['name']} (динозавр игрока {fr_d['friend_in_bot'].first_name})\n> Динозавры крайне рады друг другу!\n   > Динозавры получают бонус {mood}% к настроению!"
                                        else:
                                            event = f"🦕 | Walking along familiar paths, the dinosaur meets {fr_d['friend_bd']['dinos'][fr_d['dino_id']]['name']} (the player's dinosaur {fr_d['friend_in_bot'].first_name})\n> Dinosaurs are extremely happy with each other!\n > Dinosaurs get a bonus {mood}% to mood!"

                                        if fr_d['friend_bd']['language_code'] == 'ru':
                                            fr_event = f"🦕 | Гуляя по знакомым тропинкам, динозавр встречает {user['dinos'][dino_id]['name']} (динозавр игрока {this_user.first_name})\n> Динозавры крайне рады друг другу!\n   > Динозавры получают бонус {mood}% к настроению!"
                                        else:
                                            fr_event = f"🦕 | Walking along familiar paths, the dinosaur meets {user['dinos'][dino_id]['name']} (the player's dinosaur {this_user.first_name})\n> Dinosaurs are extremely happy with each other!\n > Dinosaurs get a bonus {mood}% to mood!"

                                        users.update_one({"userid": fr_d['friend_bd']['userid']},
                                            {"$push": {f'dinos.{fr_d["dino_id"]}.journey_log': fr_event}})

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

                            if event == 'breeze':
                                mood = random.randint(1, 15)
                                dinos_stats['mood'] += mood

                                if user['language_code'] == 'ru':
                                    event = f'🍃 | Подул приятный ветерок, настроение динозавра повышено на {mood}%'
                                else:
                                    event = f"🍃 | A pleasant breeze has blown, the dinosaur's mood has been raised by {mood}%"

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
                                    event = f"💭 | The dinosaur was able to take a nap along the road."

                            elif event == 'random_items':

                                items_dd = {
                                    "com": ["1", "2", '25', '4'],
                                    'unc': ["1", "2", '17', '25', '18', '19', '34', "70", "107", '4', '32'],
                                    'rar': ['17', '18', '19', '26', '27', '28', "84", "73"],
                                    'myt': ['26', '27', '28', '41', '32', "73", "93", "97"],
                                    'leg': ['43', '41', '35', '34', '56', "109", "70", "89"]
                                }

                                item = Functions.random_items(items_dd)

                                if mood_n == True:
                                    iname = Functions.item_name(str(item), user['language_code'])

                                    if user['language_code'] == 'ru':
                                        event = f"🧸 | Бегая по лесам, динозавр видит что-то похожее на сундук.\n>  Открыв его, он находит: {iname}!"
                                    else:
                                        event = f"🧸 | Running through the woods, the dinosaur sees something that looks like a chest.\n> Opening it, he finds: {iname}!"

                                    Functions.add_item_to_user(user, item)

                                if mood_n == False:

                                    if user['language_code'] == 'ru':
                                        event = '❌ | Редкое событие отменено из-за плохого настроения!'
                                    else:
                                        event = '❌ | A rare event has been canceled due to a bad mood!'

                            elif event == 'random_items_leg':

                                items_dd = {
                                    "com": ['14', "15", "16", '17', '18', '19', '30', '32', "56", "81", "89", "93",
                                            "97", '4'],
                                    'unc': ["15", "16", '17', '18', '19', '34', '39', "44", "75", "78", '102', "105"],
                                    'rar': ["16", '17', '18', '19', '41', "68", '43', "78", "87", "91", "97", '101',
                                            "109"],
                                    'myt': ['17', '18', '19', "68", '37', '46', '56', "87", "89", "91", '103', "107"],
                                    'leg': ['30', '32', '34', '37', '39', '41', "70", '43', '46', "56", "75", "78",
                                            "84", "87", "89", "91", "93", "97", '101', '102', '103', "105", "107",
                                            "109"]
                                }

                                item = Functions.random_items(items_dd)

                                if mood_n == True:
                                    iname = Functions.item_name(item, user['language_code'])

                                    if user['language_code'] == 'ru':
                                        event = f"🧸 | Бегая по горам, динозавр видит что-то похожее на сундук.\n>  Открыв его, он находит: {iname}!"
                                    else:
                                        event = f"🧸 | Running through the mountains, the dinosaur sees something similar to a chest.\n> Opening it, he finds: {iname}!"

                                    Functions.add_item_to_user(user, item)

                                if mood_n == False:

                                    if user['language_code'] == 'ru':
                                        event = '❌ | Мистическое событие отменено из-за плохого настроения!'
                                    else:
                                        event = '❌ | The mystical event has been canceled due to a bad mood!'

                            elif event == 'egg':
                                egg_d = {
                                    'com': ['21', "3"],
                                    'unc': ['20', "3"],
                                    'rar': ['22', "3"],
                                    'myt': ['23', "3"],
                                    'leg': ['24', "3"]
                                }

                                egg = Functions.random_items(egg_d)

                                if mood_n == True:
                                    iname = Functions.item_name(egg, user['language_code'])

                                    if user['language_code'] == 'ru':
                                        event = f"🧸 | Бегая по по пещерам, динозавр видит что-то похожее на сундук.\n>  Открыв его, он находит: {iname}!"
                                    else:
                                        event = f"🧸 | Running through the caves, the dinosaur sees something similar to a chest.\n> Opening it, he finds: {iname}!"

                                    Functions.add_item_to_user(user, egg)

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

                                    users.update_one({"userid": user['userid']}, {"$inc": {'coins': coins}})

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
                            nd = random.randint(40, 75)
                            if dino['stats']['mood'] >= nd:
                                mood_n = False
                            else:
                                mood_n = True

                            r_event = random.randint(1, 100)
                            if r_event in list(range(1, 51)):  # обычное соб
                                events = ['rain', 'm_coins', 'snow', 'hot_weather']
                            elif r_event in list(range(51, 76)):  # необычное соб
                                events = ['fight', '-eat', 'u_coins']
                            elif r_event in list(range(76, 91)):  # редкое соб
                                events = ['b_coins']
                            elif r_event in list(range(91, 100)):  # мистическое соб
                                events = ['toxic_rain', 'y_coins']
                            else:  # легендарное соб
                                events = ['l_coins'] #'lose_items'

                            event = random.choice(events)
                            if event == 'rain':
                                if Functions.acc_check(bot, user, '14', dino_id, True) == False:

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

                            if event == 'hot_weather':

                                mood = random.randint(1, 15)
                                temp = random.randint(39, 60)
                                dinos_stats['mood'] -= mood

                                if user['language_code'] == 'ru':
                                    event = f'☀ | Температура поднялась до {temp} ℃, динозавру жарко, его настроение понижено на {mood}%'
                                else:
                                    event = f"☀ | The temperature has risen to {temp} ℃, the dinosaur is hot, his mood is lowered by {mood}%"

                            if event == 'snow':

                                mood = random.randint(1, 15)
                                dinos_stats['mood'] -= mood

                                if user['language_code'] == 'ru':
                                    event = f'❄ | Вдруг начал идти снег! Динозавр замёрз, его настроение понижено на {mood}%'
                                else:
                                    event = f"❄ | Suddenly it started snowing! The dinosaur is frozen, his mood is lowered by {mood}%"

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

                                if Functions.acc_check(bot, user, '29', dino_id, True) == False and random.randint(1, 2) == 1:
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

                            # if event == 'lose_items':
                            #     user = users.find_one({"userid": user['userid']})
                            #     items = user['inventory']
                            #     item = random.choice(items)

                            #     if mood_n == True:
                            #         iname = Functions.item_name(item, user['language_code'])

                            #         if user['language_code'] == 'ru':
                            #             event = f"❗ | Бегая по лесам, динозавр обронил {iname}\n>  Предмет потерян!"
                            #         else:
                            #             event = f"❗ | Running through the woods, the dinosaur dropped {iname}\n>  The item is lost!"

                            #         user['inventory'].remove(item)
                            #         users.update_one({"userid": user['userid']},
                            #             {"$set": {'inventory': user['inventory']}})

                            #     if mood_n == False:

                            #         if user['language_code'] == 'ru':
                            #             event = '🍭 | Отрицательное событие отменено из-за хорошего настроения!'
                            #         else:
                            #             event = '🍭 | Negative event canceled due to good mood!'

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

                                    users.update_one({"userid": user['userid']}, {"$inc": {'coins': coins * -1}})

                                    if user['language_code'] == 'ru':
                                        event = f'💎 | Ходя по тропинкам, динозавр обронил несколько монет из рюкзака\n>   Вы потеряли {coins} монет.'
                                    else:
                                        event = f'💎 | Walking along the paths, the dinosaur dropped some coins from his backpack.   You have lost {coins} coins.'

                                if mood_n == False:
                                    if user['language_code'] == 'ru':
                                        event = '🍭 | Отрицательное событие отменено из-за хорошего настроения!'
                                    else:
                                        event = '🍭 | Negative event canceled due to good mood!'

                        users.update_one({"userid": user['userid']}, {"$push": {f'dinos.{dino_id}.journey_log': event}})

                    bd_user = users.find_one({"userid": user['userid']})
                    if bd_user != None:
                        if len(bd_user['dinos']) != 0:
                            for i in dinos_stats.keys():
                                if dinos_stats[i] != 0 or bd_user['dinos'][dino_id]['stats'][i] > 100 or \
                                        bd_user['dinos'][dino_id]['stats'][i] < 0:
                                    if dinos_stats[i] + bd_user['dinos'][dino_id]['stats'][i] > 100:
                                        users.update_one({"userid": user['userid']},
                                            {"$set": {f'dinos.{dino_id}.stats.{i}': 100}})

                                    elif dinos_stats[i] + bd_user['dinos'][dino_id]['stats'][i] < 0:
                                        users.update_one({"userid": user['userid']},
                                            {"$set": {f'dinos.{dino_id}.stats.{i}': 0}})

                                    else:
                                        users.update_one({"userid": user['userid']},
                                            {"$inc": {f'dinos.{dino_id}.stats.{i}': dinos_stats[i]}})

    def user_hunt(bot, user):
        dns_l = list(user['dinos'].keys()).copy()

        for dino_id in dns_l:
            dino = user['dinos'][dino_id]
            dinos_stats = {'unv': 0}

            if dino.get('status', 0) == 'dino':  # дино

                if dino['activ_status'] == 'hunting':

                    if random.randint(1, 8) == 4:
                        user['lvl'][1] += random.randint(0, 20)
                        users.update_one({"userid": user['userid']}, {"$set": {'lvl': user['lvl']}})

                    if random.randint(1, 13) == 7:  # unv
                        dinos_stats['unv'] -= random.randint(0, 1)

                    if Functions.acc_check(bot, user, '15', dino_id, False):
                        pr_hunt = 4
                    else:
                        pr_hunt = 5

                    r = random.randint(1, pr_hunt)
                    if r == 1:

                        Functions.acc_check(bot, user, '15', dino_id, True)  # понижение прочности для инструментов

                        col_d = {
                            'com': ['9', "71"],  # 🌾 🌽
                            'unc': ['9', "79", "95"],  # 🌾 🍌 🥜
                            'rar': ['27', '11'],  # 🥢 🍒
                            'myt': ['6', '11', "85"],  # 🌿  🍒 🍚
                            'leg': ['6', "76", "82"]  # 🌿 🌶️
                        }

                        hun_d = {
                            'com': ['8'],  # 🥩
                            'unc': ['8'],  # 🥩
                            'rar': ["26", "12"],  # 👢 🍗
                            'myt': ['5', "12"],  # 🍖 🍗
                            'leg': ['5']  # 🍖
                        }

                        fis_d = {
                            'com': ["10"],  # 🍣
                            'unc': ["10"],  # 🍣
                            'rar': ["28", "13"],  # 🐡 🦪
                            'myt': ["13", '7', "13"],  # 🦪 🍤 🦪
                            'leg': ['7', "80"]  # 🍤 🦀
                        }

                        all_d = {
                            'com': col_d['com'] + hun_d['com'] + fis_d['com'] +
                                   ['2', "68"],  # 🍪 🍫

                            'unc': col_d['unc'] + hun_d['unc'] + fis_d['unc'] +
                                   ['2', "68"],  # 🍪 🍫

                            'rar': col_d['rar'] + hun_d['rar'] + fis_d['rar'] +
                                   ['2', "94"],  # 🍪 🍡

                            'myt': col_d['myt'] + hun_d['myt'] + fis_d['myt'] +
                                   ["19", '18'],  # 🥞 🍕

                            'leg': col_d['leg'] + hun_d['leg'] + fis_d['leg'] +
                                   ['18', "81"]  # 🍕 ☕️

                        }

                        icon_d = {
                            'com': list(range(1, 2)),
                            'unc': list(range(1, 3)),
                            'rar': list(range(1, 4)),
                            'myt': list(range(1, 5)),
                            'leg': list(range(1, 6))
                        }

                        if Functions.acc_check(bot, user, '31', dino_id, False):

                            for i in [col_d['rar'], col_d['myt'], col_d['leg'], all_d['rar'], all_d['myt'],
                                      all_d['leg']]:
                                i.append('35')

                        if dino['h_type'] == 'all':
                            item = Functions.random_items(all_d)

                        if dino['h_type'] == 'collecting':
                            item = Functions.random_items(col_d)

                        if dino['h_type'] == 'hunting':
                            item = Functions.random_items(hun_d)

                        if dino['h_type'] == 'fishing':
                            item = Functions.random_items(fis_d)

                        if item == '35':
                            Functions.acc_check(bot, user, '31', dino_id, True)

                        tg = 0
                        i_count = Functions.random_items(icon_d)

                        for i in list(range(i_count)):
                            dino['target'][0] += 1
                            tg += 1

                            Functions.add_item_to_user(user, item)

                        users.update_one({"userid": user['userid']},
                                         {"$set": {f'dinos.{dino_id}.target': dino['target']}})

                        # квесты
                        if dino['h_type'] != 'all':
                            Dungeon.check_quest(bot, user, met='check',
                                quests_type='do',
                                kwargs={'dp_type': dino['h_type'], 'act': tg})

                    bd_user = users.find_one({"userid": user['userid']})
                    if bd_user != None:
                        if len(bd_user['dinos']) != 0:
                            for i in dinos_stats.keys():
                                if dinos_stats[i] != 0:
                                    users.update_one({"userid": user['userid']},
                                        {"$inc": {f'dinos.{dino_id}.stats.{i}': dinos_stats[i]}})

    def user_game(bot, user):
        dns_l = list(user['dinos'].keys()).copy()

        for dino_id in dns_l:
            dino = user['dinos'][dino_id]
            dinos_stats = {'game': 0, 'unv': 0}

            if dino.get('status', 0) == 'dino':  # дино

                if dino['activ_status'] == 'game':


                    if random.randint(1, 13) == 7:  # unv
                        dinos_stats['unv'] -= random.randint(0, 1)

                    if random.randint(1, 8) == 4:  # unv

                        user['lvl'][1] += random.randint(0, 20)
                        users.update_one({"userid": user['userid']}, {"$set": {'lvl': user['lvl']}})

                    if user['dinos'][dino_id]['stats']['game'] < 100:
                        if random.randint(1, 5) == 1:
                            dinos_stats['game'] += int(random.randint(2, 15) * user['dinos'][dino_id]['game_%'])

                    bd_user = users.find_one({"userid": user['userid']})
                    if bd_user != None:
                        if len(bd_user['dinos']) != 0:
                            for i in dinos_stats.keys():
                                if dinos_stats[i] != 0:
                                    users.update_one({"userid": user['userid']},
                                        {"$inc": {f'dinos.{dino_id}.stats.{i}': dinos_stats[i]}})


    def user_sleep(bot, user):
        dns_l = list(user['dinos'].keys()).copy()

        for dino_id in dns_l:
            dino = user['dinos'][dino_id]
            dinos_stats = {'game': 0, 'unv': 0, 'mood': 0, 'heal': 0, 'eat': 0}

            if dino.get('status', 0) == 'dino':  # дино

                if dino['activ_status'] == 'sleep':

                    if 'sleep_type' not in user['dinos'][dino_id].keys() or user['dinos'][dino_id][
                        'sleep_type'] == 'long':

                        if user['dinos'][dino_id]['stats']['unv'] < 100:
                            if random.randint(1, 13) == 7:
                                dinos_stats['unv'] += random.randint(1, 2)

                    else:
                        if user['dinos'][dino_id]['stats']['unv'] < 100:
                            if random.randint(1, 5) == 2:
                                dinos_stats['unv'] += random.randint(1, 2)

                    if user['dinos'][dino_id]['stats']['game'] < 40:
                        if random.randint(1, 7) == 3:
                            dinos_stats['game'] += random.randint(1, 2)

                    if user['dinos'][dino_id]['stats']['mood'] < 50:
                        if random.randint(1, 7) == 3:
                            dinos_stats['mood'] += random.randint(1, 2)

                    if user['dinos'][dino_id]['stats']['heal'] < 100:
                        if user['dinos'][dino_id]['stats']['eat'] > 50:
                            if random.randint(1, 8) == 1:
                                dinos_stats['heal'] += random.randint(1, 5)
                                dinos_stats['eat'] -= random.randint(0, 1)

                    bd_user = users.find_one({"userid": user['userid']})
                    if bd_user != None:
                        if len(bd_user['dinos']) != 0:
                            for i in dinos_stats.keys():
                                if dinos_stats[i] != 0:
                                    users.update_one({"userid": user['userid']},
                                        {"$inc": {f'dinos.{dino_id}.stats.{i}': dinos_stats[i]}})

    def user_pass(user):
        dns_l = list(user['dinos'].keys()).copy()

        for dino_id in dns_l:
            dino = user['dinos'][dino_id]
            dinos_stats = {'mood': 0}

            if dino.get('status', 0) == 'dino':  # дино

                if dino['activ_status'] == 'pass_active':

                    if user['dinos'][dino_id]['stats']['game'] >= 90:
                        if dino['stats']['mood'] < 100:
                            if random.randint(1, 3) == 2:
                                dinos_stats['mood'] += random.randint(1, 15)

                            if random.randint(1, 10) == 5:
                                users.update_one({"userid": user['userid']}, {"$inc": {'coins': random.randint(0, 20)}})

                    if user['dinos'][dino_id]['stats']['mood'] >= 80:
                        if random.randint(1, 10) == 5:
                            users.update_one({"userid": user['userid']}, {"$inc": {'coins': random.randint(0, 10)}})

                    if user['dinos'][dino_id]['stats']['unv'] <= 20 and user['dinos'][dino_id]['stats']['unv'] != 0:
                        if dino['stats']['mood'] > 0:
                            if random.randint(1, 5) == 2:
                                dinos_stats['mood'] -= random.randint(1, 2)

                    bd_user = users.find_one({"userid": user['userid']})
                    if bd_user != None:
                        if len(bd_user['dinos']) != 0:
                            for i in dinos_stats.keys():
                                if dinos_stats[i] != 0:
                                    users.update_one({"userid": user['userid']},
                                        {"$inc": {f'dinos.{dino_id}.stats.{i}': dinos_stats[i]}})


    def user_incub(bot, user):
        dns_l = list(user['dinos'].keys()).copy()

        for dino_id in dns_l:
            dino = user['dinos'][dino_id]
            if dino.get('status', 0) == 'incubation':  # инкубация

                if dino['incubation_time'] - int(time.time()) <= 60 * 5 and dino['incubation_time'] - int(
                        time.time()) > 0:  # уведомление за 5 минут

                    if Functions.notifications_manager(bot, '5_min_incub', user, None, dino_id, 'check') == False:
                        Functions.notifications_manager(bot, "5_min_incub", user, dino, dino_id)


                elif dino['incubation_time'] - int(time.time()) <= 0:

                    Functions.notifications_manager(bot, "5_min_incub", user, dino, dino_id, met='delete')

                    if 'quality' in dino.keys():
                        Functions.random_dino(user, dino_id, dino['quality'])
                    else:
                        Functions.random_dino(user, dino_id)
                    Functions.notifications_manager(bot, "incub", user, dino_id)

    def user_notif(bot, user):
        dns_l = list(user['dinos'].keys()).copy()

        for dino_id in dns_l:
            dino = user['dinos'][dino_id]
            if dino.get('status', 0) == 'dino':  # дино

                if dino['activ_status'] == 'sleep':

                    if user['dinos'][dino_id]['stats']['unv'] >= 100:
                        user['dinos'][dino_id]['activ_status'] = 'pass_active'
                        Functions.notifications_manager(bot, 'woke_up', user, None, dino_id, 'send')

                        try:
                            del user['dinos'][dino_id]['sleep_start']
                        except:
                            pass

                        users.update_one({"userid": user['userid']},
                                         {"$set": {f'dinos.{dino_id}': user['dinos'][dino_id]}})

                    if 'sleep_type' in user['dinos'][dino_id].keys() and user['dinos'][dino_id][
                        'sleep_type'] == 'short':

                        if user['dinos'][dino_id]['sleep_time'] - int(time.time()) <= 0:
                            user['dinos'][dino_id]['activ_status'] = 'pass_active'
                            Functions.notifications_manager(bot, 'woke_up', user, None, dino_id, 'send')

                            del user['dinos'][dino_id]['sleep_type']
                            del user['dinos'][dino_id]['sleep_time']
                            users.update_one({"userid": user['userid']},
                                             {"$set": {f'dinos.{dino_id}': user['dinos'][dino_id]}})


                elif dino['activ_status'] == 'game':

                    if int(dino['game_time'] - time.time()) <= 0:
                        user['dinos'][dino_id]['activ_status'] = 'pass_active'

                        Functions.notifications_manager(bot, 'game_end', user, None, dino_id, 'send')

                        gm = user['dinos'][dino_id]['game_start']

                        try:
                            del user['dinos'][dino_id]['game_time']
                            del user['dinos'][dino_id]['game_%']
                            del user['dinos'][dino_id]['game_start']
                        except:
                            pass

                        users.update_one({"userid": user['userid']},
                                         {"$set": {f'dinos.{dino_id}': user['dinos'][dino_id]}})

                        try:
                            game_time = (int(time.time()) - gm) // 60

                            Dungeon.check_quest(bot, user, met='check', quests_type='do',
                                                kwargs={'dp_type': 'game', 'act': game_time})
                        except Exception as e:
                            print(f"Check quest error: {e}")

                elif dino['activ_status'] == 'journey':

                    if int(dino['journey_time'] - time.time()) <= 0:
                        user['dinos'][dino_id]['activ_status'] = 'pass_active'

                        Functions.notifications_manager(bot, "journey_end", user, user['dinos'][dino_id]['journey_log'],
                                dino_id=dino_id)

                        del user['dinos'][dino_id]['journey_time']
                        del user['dinos'][dino_id]['journey_log']

                        users.update_one({"userid": user['userid']},
                                         {"$set": {f'dinos.{dino_id}': user['dinos'][dino_id]}})

                        Dungeon.check_quest(bot, user, met='check', quests_type='do',
                                kwargs={'dp_type': 'journey', 'act': 1})

                elif dino['activ_status'] == 'hunting':
                    if dino['target'][0] >= dino['target'][1]:
                        del user['dinos'][dino_id]['target']
                        del user['dinos'][dino_id]['h_type']
                        user['dinos'][dino_id]['activ_status'] = 'pass_active'

                        Functions.notifications_manager(bot, "hunting_end", user, dino_id=dino_id)
                        users.update_one({"userid": user['userid']},
                                         {"$set": {f'dinos.{dino_id}': user['dinos'][dino_id]}})

                if user['dinos'][dino_id]['stats']['mood'] <= 50:
                    if user['dinos'][dino_id]['activ_status'] != 'sleep':
                        if Functions.notifications_manager(bot, "need_mood", user, dino_id=dino_id,
                                met='check') == False:
                            Functions.notifications_manager(bot, "need_mood", user,
                                    user['dinos'][dino_id]['stats']['mood'], dino_id=dino_id)

                if user['dinos'][dino_id]['stats']['game'] <= 50:
                    if user['dinos'][dino_id]['activ_status'] != 'sleep':
                        if Functions.notifications_manager(bot, "need_game", user, dino_id=dino_id,
                                    met='check') == False:
                            Functions.notifications_manager(bot, "need_game", user,
                                    user['dinos'][dino_id]['stats']['game'], dino_id=dino_id)

                if user['dinos'][dino_id]['stats']['eat'] <= 40:
                    if user['dinos'][dino_id]['activ_status'] != 'sleep':
                        if Functions.notifications_manager(bot, "need_eat", user, dino_id=dino_id,
                                        met='check') == False:
                            Functions.notifications_manager(bot, "need_eat", user,
                                    user['dinos'][dino_id]['stats']['eat'], dino_id=dino_id)

                if user['dinos'][dino_id]['stats']['unv'] <= 30:
                    if user['dinos'][dino_id]['activ_status'] != 'sleep':
                        if Functions.notifications_manager(bot, "need_unv", user, dino_id=dino_id,
                                     met='check') == False:
                            Functions.notifications_manager(bot, "need_unv", user,
                                    user['dinos'][dino_id]['stats']['unv'], dino_id=dino_id)

                if user['dinos'][dino_id]['stats']['heal'] <= 30:
                    if Functions.notifications_manager(bot, "need_heal", user, dino_id=dino_id, met='check') == False:
                        Functions.notifications_manager(bot, "need_heal", user, user['dinos'][dino_id]['stats']['heal'],
                                dino_id=dino_id)

                if user['dinos'][dino_id]['stats']['heal'] <= 10:
                    if Functions.notifications_manager(bot, "need_heal!", user, dino_id=dino_id, met='check') == False:
                        Functions.notifications_manager(bot, "need_heal!", user,
                                user['dinos'][dino_id]['stats']['heal'], dino_id=dino_id)

                if user['dinos'][dino_id]['stats']['heal'] >= 50:
                    Functions.notifications_manager(bot, 'need_heal', user, dino_id=dino_id, met='delete')

                if user['dinos'][dino_id]['stats']['heal'] >= 30:
                    Functions.notifications_manager(bot, 'need_heal!', user, dino_id=dino_id, met='delete')

                if user['dinos'][dino_id]['stats']['mood'] >= 60:
                    Functions.notifications_manager(bot, 'need_mood', user, dino_id=dino_id, met='delete')

                if user['dinos'][dino_id]['stats']['game'] >= 60:
                    Functions.notifications_manager(bot, 'need_game', user, dino_id=dino_id, met='delete')

                if user['dinos'][dino_id]['stats']['eat'] >= 50:
                    Functions.notifications_manager(bot, 'need_eat', user, dino_id=dino_id, met='delete')

                if user['dinos'][dino_id]['stats']['unv'] >= 40:
                    Functions.notifications_manager(bot, 'need_unv', user, dino_id=dino_id, met='delete')

                if user['dinos'][dino_id]['stats']['heal'] <= 0:

                    if user['dinos'][dino_id]['activ_status'] == 'dungeon':
                        dungeonid = user['dinos'][dino_id]['dungeon_id']
                        dung = dungeons.find_one({"dungeonid": dungeonid})

                        if dung != None:
                            user['dinos'][dino_id]['activ_status'] = 'pass_active'
                            users.update_one({"userid": user['userid']},
                                             {"$set": {f'dinos.{dino_id}': user['dinos'][dino_id]}})

                            del dung['users'][user['userid']]['dinos'][dino_id]
                            dungeons.update_one({"dungeonid": dungeonid}, {"$set": {f'users': dung['users']}})

                            inf = Dungeon.message_upd(bot, userid=user['userid'], dungeonid=user['userid'])

                            if user['userid'] == dung['dungeonid'] and len(
                                    dung['users'][str(user['userid'])]['dinos']) == 0:

                                for uk in dung['users'].keys():
                                    Dungeon.user_dungeon_stat(int(uk), dungeonid)

                                inf = Dungeon.message_upd(bot, dungeonid=int(uk), type='delete_dungeon')
                                kwargs = {'save_inv': False}
                                dng, inf = Dungeon.base_upd(dungeonid=user['userid'], type='delete_dungeon',
                                                            kwargs=kwargs)

                    del user['dinos'][dino_id]
                    Functions.notifications_manager(bot, 'dead', user, dino_id=dino_id, met='delete')

                    if Functions.notifications_manager(bot, "dead", user, dino_id=dino_id, met='check') == False:

                        if user['lvl'][0] >= 5:
                            Functions.add_item_to_user(user, '21')

                        if len(user['dinos']) > 0:
                            user['settings']['dino_id'] = list(user['dinos'].keys())[0]
                            users.update_one({"userid": user['userid']}, {"$set": {'settings': user['settings']}})

                        Functions.notifications_manager(bot, "dead", user, dino_id=dino_id)

                    users.update_one({"userid": user['userid']}, {"$set": {f'dinos': user['dinos']}})
                    users.update_one({"userid": user['userid']}, {"$inc": {'dead_dinos': 1}})
    
    def events(bot):
        events_data = management.find_one({"_id": 'events'})

        Functions.auto_event("time_year")
        Functions.auto_event("new_year")
        events = events_data['activ']

        for event in events:
            if event['time_end'] != None:
                if event['time_end'] - int(time.time()) <= 0:
                    Functions.delete_event(eid=event['id'])


class Checks:

    @staticmethod
    def check_dead_users(bot):
        act1, act2, act3 = 0, 0, 0

        members = users.find({'dinos': {'$eq': {}}})

        for user in members:

            try:
                notactivity_time = int(time.time()) - int(user['last_m'])
            except:
                users.update_one({"userid": user['userid']}, {"$set": {'last_m': int(time.time()) - 604800}})
                user['last_m'] = int(time.time()) - 604800
                notactivity_time = int(time.time()) - int(user['last_m'])

            if notactivity_time >= 604800 and len(user['dinos']) == 0:  # 7 дней не активности

                try:

                    if user['language_code'] == 'ru':
                        text = f"🦕 | {bot.get_chat(user['userid']).first_name}, мы скучаем по тебе 😥, ты уже очень давно не пользовался ботом ({Functions.time_end(notactivity_time)})!\n\n❤ | Давай сного будем играть, путешествовать и развлекаться вместе! Мы с нетерпением ждём тебя!"
                    else:
                        text = f"🦕 | {bot.get_chat(user['userid']).first_name}, we miss you 😥, you haven't used the bot for a long time ({Functions.time_end(notactivity_time, True)})!\n\n❤ | Let's play, travel and have fun together! We are looking forward to seeing you!"

                    bot.send_message(user['userid'], text)
                    act3 += 1

                    users.update_one({"userid": user['userid']}, {"$set": {'last_m': int(time.time())}})
                    user['notifications']['dead_user'] = False

                    users.update_one({"userid": user['userid']}, {"$set": {'notifications': user['notifications']}})


                except Exception as error:

                    if str(error) in [
                        'A request to the Telegram API was unsuccessful. Error code: 403. Description: Forbidden: bot was blocked by the user',
                        'A request to the Telegram API was unsuccessful. Error code: 403. Description: Forbidden: user is deactivated']:
                        # пользователь заблокировал бота, удаляем из базы.
                        users.delete_one({"userid": user['userid']})
                        act2 += 1


                    else:
                        Functions.console_message(f"WARNING in dead check users, 7 days check\n{error}\n{user['userid']}", 2)


            elif notactivity_time >= 172800 and len(user['dinos']) == 0:  # 2 дня не активнсоти

                if 'dead_user' not in user['notifications'].keys() or user['notifications']['dead_user'] == False:

                    try:

                        if user['language_code'] == 'ru':
                            text = f"🦕 | Хей {bot.get_chat(user['userid']).first_name}, мы уже довольно давно с тобой не виделись ({Functions.time_end(notactivity_time)})!\n\n🦄 | Пока тебя не было, в боте появилось куча всего интересного и произошло много событий! Мы сного ждём тебя в игре и будем рады твоей активности! ❤"
                        else:
                            text = f"🦕 | Hey {bot.get_chat(user['userid']).first_name}, we haven't seen you for quite a while ({Functions.time_end(notactivity_time, True)})!\n\n🦄 | When you weren't there, a bunch of interesting things appeared in the bot and a lot of events happened! We are waiting for you a lot in the game and we will be glad of your activity! ❤"

                        bot.send_message(user['userid'], text)
                        act3 += 1
                        user['notifications']['dead_user'] = True

                        users.update_one({"userid": user['userid']}, {"$set": {'notifications': user['notifications']}})

                    except Exception as error:
                        if str(error) in [
                            'A request to the Telegram API was unsuccessful. Error code: 403. Description: Forbidden: bot was blocked by the user',
                            'A request to the Telegram API was unsuccessful. Error code: 403. Description: Forbidden: user is deactivated']:
                            # пользователь заблокировал бота, дадим ему возможность подумать ещё пару дней.
                            act1 += 1


                        else:

                            Functions.console_message(f"WARNING in dead check users, 2 days check\n{error}\n{user['userid']}", 2)

    @staticmethod
    def check_incub(bot):  # проверка каждые 5 секунд

        members = users.find(filter={'dinos': {'$ne': {}}}, projection={'dinos': 1, 'notifications': 1, 'userid': 1, 'settings': 1, 'language_code': 1})

        for user in members:
            try:
                CheckFunction.user_incub(bot, user)
            except Exception as err:
                Functions.console_message(f'Error in user_incub\nError: {err}\nUser id: {user["userid"]}', 2)

    @staticmethod
    def rayt(members):
        mr_l, lv_l, dng_fl = [], [], {}
        loc_users = list(members).copy()

        mr_l_r = list(sorted(loc_users, key=lambda x: x['coins'], reverse=True))
        lv_l_r = list(sorted(loc_users, key=lambda x: (x['lvl'][0] - 1) * (
                    5 * x['lvl'][0] * x['lvl'][0] + 50 * x['lvl'][0] + 100) + x['lvl'][1], reverse=True))

        for i in mr_l_r:
            mr_l.append({'userid': i['userid'], 'coins': i['coins']})

        for i in lv_l_r:
            lv_l.append({'userid': i['userid'], 'lvl': i['lvl']})

        for us in loc_users:

            if 'user_dungeon' in us.keys():
                ns_res = None
                st = us['user_dungeon']['statistics']

                for i in st:

                    if ns_res == None:
                        ns_res = i

                    else:
                        if i['end_floor'] >= ns_res['end_floor']:
                            ns_res = i

                if ns_res != None:

                    if str(ns_res['end_floor']) not in dng_fl.keys():
                        dng_fl[str(ns_res['end_floor'])] = [us['userid']]

                    else:
                        dng_fl[str(ns_res['end_floor'])].append(us['userid'])

        Functions.rayt_update('save', [mr_l, lv_l, dng_fl])

    @staticmethod
    def check_notif(bot, members):

        for user in members:
            try:
                CheckFunction.user_notif(bot, user)
            except Exception as err:
                Functions.console_message(f'Error in user_notif\nError: {err}\nUser id: {user["userid"]}', 3)

    @staticmethod
    def main_pass(bot, members):

        for user in members:

            try:
                CheckFunction.user_pass(user)
            except Exception as err:
                Functions.console_message(f'Error in user_pass\nError: {err}\nUser id: {user["userid"]}', 3)

    @staticmethod
    def main_sleep(bot, members):

        for user in members:

            try:
                CheckFunction.user_sleep(bot, user)
            except Exception as err:
                Functions.console_message(f'Error in user_sleep\nError: {err}\nUser id: {user["userid"]}', 3)

    @staticmethod
    def main_game(bot, members):

        for user in members:

            try:
                CheckFunction.user_game(bot, user)
            except Exception as err:
                Functions.console_message(f'Error in user_game\nError: {err}\nUser id: {user["userid"]}', 3)

    @staticmethod
    def main_hunting(bot, members):

        for user in members:

            try:
                CheckFunction.user_hunt(bot, user)
            except Exception as err:
                Functions.console_message(f'Error in user_hunt\nError: {err}\nUser id: {user["userid"]}', 3)

    @staticmethod
    def main_journey(bot, members):

        for user in members:

            try:
                CheckFunction.user_journey(bot, user)
            except Exception as err:
                Functions.console_message(f'Error in user_journey\nError: {err}\nUser id: {user["userid"]}', 3)

    @staticmethod
    def main(bot, members):

        for user in members:
            try:
                CheckFunction.main(bot, user)
            except Exception as err:
                Functions.console_message(f'Error in MAIN\nError: {err}\nUser id: {user["userid"]}', 3)
    
    @staticmethod
    def events(bot):
        try:
            CheckFunction.events(bot)
        except Exception as err:
            Functions.console_message(f'Error in events\nError: {err}', 3)

    @staticmethod
    def dungeons_check(bot):
        dngs = list(dungeons.find({})).copy()

        for dng in dngs:
            dungeonid = dng['dungeonid']

            if 'create_time' in dng.keys():
                crt = dng['create_time']

                if dng['dungeon_stage'] == 'preparation':

                    if int(time.time()) - crt >= 1800:
                        Dungeon.message_upd(bot, dungeonid=dungeonid, type='delete_dungeon')
                        Dungeon.base_upd(dungeonid=dungeonid, type='delete_dungeon')
                
                if int(time.time()) - crt >= 86400:
                    Dungeon.message_upd(bot, dungeonid=dungeonid, type='delete_dungeon')
                    Dungeon.base_upd(dungeonid=dungeonid, type='delete_dungeon')

            else:
                dungeons.update_one({"dungeonid": dungeonid}, {"$set": {f'create_time': int(time.time())}})

    @staticmethod
    def quests(bot):

        uss = list(users.find({'settings.last_markup': 'dino-tavern'}))

        for user in uss:
            try:
                CheckFunction.pre_quest(bot, user, uss)
            except Exception as e:
                print('QUESTS err ', e)