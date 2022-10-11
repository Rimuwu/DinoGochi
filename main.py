import telebot
from telebot import types
import random
import json
import pymongo
import time
import threading
import sys
from memory_profiler import memory_usage
import pprint
from fuzzywuzzy import fuzz

import config

sys.path.append("Cogs")
from commands import commands
from classes import Functions, Dungeon
from checks import Checks
from call_data import call_data


bot = telebot.TeleBot(config.TOKEN)

client = pymongo.MongoClient(config.CLUSTER_TOKEN)
users, referal_system, market, dungeons = client.bot.users, client.bot.referal_system, client.bot.market, client.bot.dungeons

with open('data/items.json', encoding='utf-8') as f:
    items_f = json.load(f)

with open('data/dino_data.json', encoding='utf-8') as f:
    json_f = json.load(f)

class SpamStop(telebot.custom_filters.AdvancedCustomFilter):
    key = 'spam_check'

    @staticmethod
    def check(message, text):
        user = message.from_user

        if Functions.spam_stop(user.id) == False:
            bot.delete_message(user.id, message.message_id)
            return False

        else:
            return True

class WC(telebot.custom_filters.AdvancedCustomFilter):
    key = 'wait_callback'

    @staticmethod
    def check(call, trt):
        return Functions.callback_spam_stop(call.from_user.id)

class Test_bot(telebot.custom_filters.AdvancedCustomFilter):
    key = 'test_bot'

    @staticmethod
    def check(message, text):
        user = message.from_user

        if bot.get_me().first_name != 'DinoGochi':
            print("Поймал", message.text, 'от ', user.first_name)
            if user.id in [5279769615, 1191252229]:
                return True

            else:
                print('Отмена команды')
                return False

class In_Dungeon(telebot.custom_filters.AdvancedCustomFilter):
    key = 'in_dungeon'

    @staticmethod
    def check(message, text):

        if message.chat.type == 'private':

            user = message.from_user
            bd_user = users.find_one({"userid": user.id})

            if bd_user != None:

                for dino_id in bd_user['dinos'].keys():
                    if bd_user['dinos'][str(dino_id)]['status'] == 'dino':
                        dino_st = bd_user['dinos'][str(dino_id)]['activ_status']

                        if dino_st == 'dungeon':

                            if bd_user['language_code'] == 'ru':
                                text = '❌ Во время нахождения в подземелье, используйте интерфейс подземелья!'
                            else:
                                text = '❌ While in the dungeon, use the dungeon interface!'
                            bot.reply_to(message, text)

                            return False

        return True

class In_channel(telebot.custom_filters.AdvancedCustomFilter):
    key = 'in_channel'

    @staticmethod
    def check(message, text):
        user = message.from_user
        bd_user = users.find_one({"userid": user.id})

        r = bot.get_chat_member(-1001673242031, user.id)
        if bd_user != None and r.status == 'left':

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
            return False

        else:
            return True

def check(): #проверка каждые 10 секунд

    def alpha(bot, members): Checks.main(bot, members)

    def beta(bot, members): Checks.main_hunting(bot, members)

    def beta2(bot, members): Checks.main_game(bot, members)

    def gamma(bot, members): Checks.main_sleep(bot, members)

    def gamma2(bot, members): Checks.main_pass(bot, members)

    def delta(bot, members): Checks.main_journey(bot, members)

    non_members = users.find({ })
    chunks_users = list(Functions.chunks( list(non_members), 20 ))
    Functions.check_data('col', None, int(len(chunks_users)) )

    while True:
        if int(memory_usage()[0]) < 1500:
            st_r_time = int(time.time())
            non_members = users.find({ })
            chunks_users = list(Functions.chunks( list(non_members), 20 ))
            sl_time = 10 - ( int(time.time()) - st_r_time )

            if sl_time < 0:
                sl_time = 0
                print(f'WARNING: sleep time: {sl_time}, time sleep skip to {sl_time}')

            for members in chunks_users:

                threading.Thread(target = alpha,  daemon=True, kwargs = {'bot': bot, 'members': members}).start()
                threading.Thread(target = beta,   daemon=True, kwargs = {'bot': bot, 'members': members} ).start()
                threading.Thread(target = beta2,  daemon=True, kwargs = {'bot': bot, 'members': members} ).start()
                threading.Thread(target = gamma,  daemon=True, kwargs = {'bot': bot, 'members': members} ).start()
                threading.Thread(target = gamma2, daemon=True, kwargs = {'bot': bot, 'members': members} ).start()
                threading.Thread(target = delta,  daemon=True, kwargs = {'bot': bot, 'members': members}).start()

        else:
            print(f'Использование памяти: {int(memory_usage()[0])}')

        time.sleep(sl_time)

main_checks = threading.Thread(target = check, daemon=True)

def check_notif(): #проверка каждые 5 секунд

    def alpha(bot, members): Checks.check_notif(bot, members)

    def beta(bot): Checks.check_incub(bot)

    def memory(): Checks.check_memory()

    while True:

        if int(memory_usage()[0]) < 1500:
            non_members = users.find({ })
            chunks_users = list(Functions.chunks( list(non_members), 25 ))

            for members in chunks_users:
                threading.Thread(target = alpha, daemon=True, kwargs = {'bot': bot, 'members': members}).start()

            threading.Thread(target = beta, daemon=True, kwargs = {'bot': bot}).start()

            threading.Thread(target = memory, daemon=True ).start()

        else:
            print(f'Использование памяти: {int(memory_usage()[0])}')

        time.sleep(5)

thr_notif = threading.Thread(target = check_notif, daemon=True)

def min10_check(): #проверка каждые 10 мин

    def alpha(users): Checks.rayt(users)

    def dead_users(bot): Checks.check_dead_users(bot)

    def dng_check(bot): Checks.dungeons_check(bot)

    while True:

        if int(memory_usage()[0]) < 1500:
            uss = users.find({ })
            threading.Thread(target = alpha, daemon=True, kwargs = {'users': uss}).start()

            if bot.get_me().first_name == 'DinoGochi':
                threading.Thread(target = dead_users, daemon=True, kwargs = {'bot': bot} ).start()
                threading.Thread(target = dng_check, daemon=True, kwargs = {'bot': bot}).start()

        else:
            print(f'Использование памяти: {int(memory_usage()[0])}')

        time.sleep(600)

min10_thr = threading.Thread(target = min10_check, daemon=True)

def min1_check(): #проверка каждую минуту

    def alpha(bot): Checks.quests(bot)

    while True:
        time.sleep(60)

        if int(memory_usage()[0]) < 1500:

            if bot.get_me().first_name == 'DinoGochi':
                threading.Thread(target = alpha, daemon = True, kwargs = {'bot': bot}).start()

        else:
            print(f'Использование памяти: {int(memory_usage()[0])}')

min1_thr = threading.Thread(target = min1_check, daemon=True)

@bot.message_handler(commands=['stats'])
def command(message):
    user = message.from_user
    checks_data = Functions.check_data(m = 'check')

    def ttx(tm, lst):
        lgs = []
        for i in lst:
            lgs.append(f'{int(tm) - i}s')
        return ', '.join(lgs)


    text = 'STATS\n\n'
    text += f"Memory: {checks_data['memory'][0]}mb\nLast {int(time.time() - checks_data['memory'][1])}s\n\n"
    text += f"Incub check: {checks_data['incub'][0]}s\nLast {int(time.time() - checks_data['incub'][1])}s\nUsers: {checks_data['incub'][2]}\n\n"
    text += f"Notifications check: {'s, '.join(str(i) for i in checks_data['notif'][0])}\nLast { ttx(time.time(), checks_data['notif'][1]) }\n\n"

    for cls in ['main', 'main_hunt', 'main_game', 'main_sleep', 'main_pass', 'main_journey']:
        text += f"{cls} check: {'s, '.join(str(i) for i in checks_data[cls][0])}\nLast { ttx(time.time(), checks_data[cls][1]) }\nUsers: {str(checks_data[cls][2])}\n\n"


    text += f'Thr.count: {threading.active_count()}'
    bot.send_message(user.id, text)
#
# @bot.message_handler(commands=['dinos'])
# def command(message):
#     user = message.from_user
#     bd_user = users.find_one({"userid": user.id})
#     text = ''
#     for i in bd_user['dinos']:
#         if 'journey_log' in bd_user["dinos"][i].keys():
#             bd_user["dinos"][i]['journey_log'] = f"{len(bd_user['dinos'][i]['journey_log'])} - событий"
#
#         text = f'{bd_user["dinos"][i]}\n\n'
#     bot.send_message(user.id, text)
#
# @bot.message_handler(commands=['iam'])
# def command(message):
#     user = message.from_user
#     bd_user = users.find_one({"userid": user.id})
#     pprint.pprint(bd_user)
#
#
# @bot.message_handler(commands=['check_inv'])
# def command(message):
#     user = message.from_user
#     msg_args = message.text.split()
#     bd_user = users.find_one({"userid": int(msg_args[1])})
#     print('id', msg_args[2], type(msg_args[2]))
#     for i in bd_user['inventory']:
#
#         if i['item_id'] == msg_args[2]:
#             print(' #                 ============================================= #')
#             print(i)
#             print(bd_user['inventory'].index(i))
#
#     print('all')
#
# @bot.message_handler(commands=['delete_dinos'])
# def command(message):
#     user = message.from_user
#     if user.id in [5279769615, 1191252229]:
#         bd_user = users.find_one({"userid": user.id})
#         users.update_one( {"userid": user.id}, {"$set": {f'dinos': {} }} )
#         print("all")
#

# @bot.message_handler(commands=['sbros_lvl'])
# def command_n(message):
#     user = message.from_user
#     if user.id in [5279769615, 1191252229]:
#
#         def work(members, n):
#             for bd_user in members:
#
#                 if bd_user['lvl'][0] == 10 and bd_user['lvl'][1] == 0 and len(bd_user['dinos']) == 0:
#                     bd_user['lvl'][0] = 2
#                     print(bd_user['lvl'][0], bd_user['lvl'][1])
#
#                     users.update_one( {"userid": bd_user['userid']}, {"$set": {f'lvl': bd_user['lvl'] }} )
#
#             print(f'Программа обновления №{n} завершила работу.')
#
#         non_members = users.find({ })
#         chunks_users = list(Functions.chunks( list(non_members), 10 ))
#
#         n = 0
#         for members in chunks_users:
#             n += 1
#             print(f'Программа обновления №{n} начала работу.')
#             main = threading.Thread(target = work, daemon=True, kwargs = { 'members': members, 'n': n}).start()


@bot.message_handler(commands=['add_item'])
def command(message):
    user = message.from_user
    if user.id in [5279769615, 1191252229]:
        msg_args = message.text.split()
        bd = users.find_one({"userid": int(msg_args[3])})

        tr = Functions.add_item_to_user(bd, msg_args[1], int(msg_args[2]))
        bot.send_message(user.id, str(msg_args))

@bot.message_handler(commands=['test_ad'])
def command(message):
    user = message.from_user
    if user.id in [5279769615, 1191252229]:
        msg_args = message.text.split()
        bd = users.find_one({"userid": user.id})

        for it_id in range(68, 110):
            tr = Functions.add_item_to_user(bd, str(it_id), 10, type = 'data')

            for i in tr:
                bd['inventory'].append(i)

        users.update_one( {"userid": bd['userid']}, {"$set": {f'inventory': bd['inventory'] }} )
        bot.send_message(user.id, '+')

@bot.message_handler(commands=['test_d'])
def command(message):
    user = message.from_user
    if user.id in [5279769615, 1191252229]:
        msg_args = message.text.split()
        bd = users.find_one({"userid": user.id})

        lt = list(range(68, 110))
        n = len(bd['inventory'])
        print('len', n)

        inv = bd['inventory'].copy()

        for item in inv:

            if int(item['item_id']) in lt:
                bd['inventory'].remove(item)

        print('len', len(bd['inventory']), 'l', n - len(bd['inventory']))
        print(len(lt) * 10)

        users.update_one( {"userid": bd['userid']}, {"$set": {f'inventory': bd['inventory'] }} )


# @bot.message_handler(commands=['quest'])
# def command(message):
#     user = message.from_user
#     if user.id in [5279769615, 1191252229]:
#         bd_user = users.find_one({"userid": user.id})
#
#         q = Dungeon.create_quest(bd_user)
#         print(q)
#
#         users.update_one( {"userid": user.id}, {"$push": {'user_dungeon.quests.activ_quests': q }} )


# @bot.message_handler(commands=['d_upd'])
# def command(message):
#     user = message.from_user
#     if user.id in [5279769615, 1191252229]:
#         inf =  Dungeon.message_upd(bot, userid = user.id, dungeonid = user.id, upd_type = 'all', image_update = True)
#         print(inf)
#

@bot.message_handler(commands=['dungeon_delete'])
def command(message):
    user = message.from_user
    if user.id in [5279769615, 1191252229]:
        inf =  Dungeon.message_upd(bot, dungeonid = user.id, type = 'delete_dungeon')
        print(inf)

        dng, inf =  Dungeon.base_upd(dungeonid = user.id, type = 'delete_dungeon')
        pprint.pprint(dng)
        print(inf)
#
@bot.message_handler(commands=['stats_100'])
def command(message):
    user = message.from_user
    if user.id in [5279769615, 1191252229]:
        bd_user = users.find_one({"userid": user.id})

        for dk in bd_user['dinos'].keys():
            dino = bd_user['dinos'][dk]
            ds = dino['stats'].copy()
            for st in ds:
                dino['stats'][st] = 100

        users.update_one( {"userid": user.id}, {"$set": {f"dinos": bd_user['dinos'] }} )
        print('ok')

# =========================================

@bot.message_handler(commands=['profile', 'профиль'])
def command(message):
    user = message.from_user
    bd_user = users.find_one({"userid": user.id})
    if bd_user != None:

        text = Functions.member_profile(bot, user.id, bd_user['language_code'])

        try:
            bot.reply_to(message, text, parse_mode = 'Markdown')
        except Exception as error:
            print(message.chat.id, 'ERROR Профиль', '\n', error)
            bot.reply_to(message, text)

    else:

        if user.language_code == 'ru':
            text = 'У вас нет зарегистрированного аккаунта в боте, пожалуйста перейдите в бота и зарегистрируйтесь для получения доступа к данной команде.'
        else:
            text = 'You do not have a registered account in the bot, please go to the bot and register to get access to this command.'

        bot.reply_to(message, text, parse_mode = 'Markdown')

@bot.message_handler(commands=['message_update'])
def command(message):
    user = message.from_user
    bd_user = users.find_one({"userid": user.id})
    if bd_user != None:

        if message.chat.type == 'private':

            dungs = dungeons.find({ })
            dungeonid = None

            for dng in dungs:
                if str(user.id) in dng['users'].keys():
                    dungeonid = dng['dungeonid']
                    break

            if dungeonid != None:
                image_way = 'images/dungeon/preparation/1.png'
                image = open(image_way, 'rb')
                text = '-'

                msg = bot.send_photo(int(user.id), image, text, parse_mode = 'Markdown')

                Dungeon.base_upd(userid = int(user.id), messageid = msg.id, dungeonid = dungeonid, type = 'edit_message')

                inf = Dungeon.message_upd(bot, userid = user.id, dungeonid = dungeonid, upd_type = 'one', image_update = True)

                try:
                    bot.delete_message(user.id, dng['users'][str(user.id)]['messageid'])
                except:
                    pass

@bot.message_handler(commands=['add_me', 'добавь_меня'])
def command(message):
    user = message.from_user
    bd_user = users.find_one({"userid": user.id})
    if message.chat.type != 'private':
        if bd_user != None:

            if bd_user['language_code'] == 'ru':
                text = f"❤ | Все желающие могут отправить запрос в друзья <a href='tg://user?id={user.id}'>🌀 {user.first_name}</a>, нажав на кнопку ниже!"
            else:
                text = f"❤ | Everyone can send a request to friends <a href='tg://user?id={user.id}'>🌀{user.first_name}</a> by clicking on the button below!"

            bot.reply_to(message, text, parse_mode = 'HTML', reply_markup = Functions.inline_markup(bot, 'send_request', user.id, ['Отправить запрос', 'Send a request']) )

        else:

            if user.language_code == 'ru':
                text = 'У вас нет зарегистрированного аккаунта в боте, пожалуйста перейдите в бота и зарегистрируйтесь для получения доступа к данной команде.'
            else:
                text = 'You do not have a registered account in the bot, please go to the bot and register to get access to this command.'

            bot.reply_to(message, text, parse_mode = 'Markdown')

@bot.message_handler(commands=['start', 'main-menu'])
def on_start(message):
    user = message.from_user
    if message.chat.type == 'private':
        if users.find_one({"userid": user.id}) == None:
            if user.language_code == 'ru':
                text = f"🎋 | Хей <b>{user.first_name}</b>, рад приветствовать тебя!\n"+ f"<b>•</b> Я маленький игровой бот по типу тамагочи, только с динозаврами!🦖\n\n"+f"<b>🕹 | Что такое тамагочи?</b>\n"+f'<b>•</b> Тамагочи - игра с виртуальным питомцем, которого надо кормить, ухаживать за ним, играть и тд.🥚\n'+f"<b>•</b> Соревнуйтесь в рейтинге и станьте лучшим!\n\n"+f"<b>🎮 | Как начать играть?</b>\n"+f'<b>•</b> Нажмите кномку <b>🍡 Начать играть</b>!\n\n'+f'<b>❤ | Ждём в игре!</b>\n'
            else:
                text = f"🎋 | Hey <b>{user.first_name}</b>, I am glad to welcome you!\n" +f"<b>•</b> I'm a small tamagotchi-type game bot, only with dinosaurs!🦖\n\n"+f"<b>🕹 | What is tamagotchi?</b>\n"+ f'<b>•</b> Tamagotchi is a game with a virtual pet that needs to be fed, cared for, played, and so on.🥚\n'+ f"<b>•</b> Compete in the ranking and become the best!\n\n"+ f"<b>🎮 | How to start playing?</b>\n" + f'<b>•</b> Press the button <b>🍡Start playing</b>!\n\n' + f'<b>❤ | Waiting in the game!</b>\n' +f'<b>❗ | In some places, the bot may not be translated!</b>\n'

            bot.reply_to(message, text, reply_markup = Functions.markup(bot, user = user), parse_mode = 'html')
        else:
            bot.reply_to(message, '👋', reply_markup = Functions.markup(bot, user = user), parse_mode = 'html')

@bot.message_handler( content_types = ['text'], spam_check = True, in_channel = True, in_dungeon = True)
def on_message(message):
    user = message.from_user

    if message.chat.type == 'private':

        bd_user = users.find_one({"userid": user.id})

        if message.text in ['🍡 Начать играть', '🍡 Start playing']:

            commands.start_game(bot, message, user, bd_user)

        if message.text in ["🧩 Проект: Возрождение", '🧩 Project: Rebirth']:

            commands.project_reb(bot, message, user, bd_user)

        if message.text in ['↪ Назад', '↪ Back', '❌ Cancel', '❌ Отмена']:

            commands.back_open(bot, message, user, bd_user)

        if message.text in ['👁‍🗨 Профиль', '👁‍🗨 Profile']:

            commands.open_profile_menu(bot, message, user, bd_user)

        if message.text in ['🎮 Инвентарь', '🎮 Inventory']:

            Functions.user_inventory(bot, user, message)

        if message.text in ['🦖 Динозавр', '🦖 Dinosaur']:

            commands.dino_prof(bot, message, user)

        if message.text in ['🔧 Настройки', '🔧 Settings']:

            commands.open_settings(bot, message, user, bd_user)

        elif message.text in ['👥 Друзья', '👥 Friends']:

            commands.friends_open(bot, message, user, bd_user)

        if message.text in ['❗ FAQ']:

            commands.faq(bot, message, user, bd_user)

        if message.text in ['🍺 Дино-таверна', '🍺 Dino-tavern'] and Functions.lst_m_f(bd_user) != 'dino-tavern':

            commands.open_dino_tavern(bot, message, user, bd_user)

        if Functions.tr_c_f(bd_user) and message.text in ['🕹 Действия', '🕹 Actions']:

            commands.open_action_menu(bot, message, user, bd_user)

        if message.text in ['❗ Notifications', '❗ Уведомления']:

            commands.not_set(bot, message, user, bd_user)

        if message.text in ["👅 Язык", "👅 Language"]:

            commands.lang_set(bot, message, user, bd_user)

        if message.text in ['🎞 Инвентарь', '🎞 Inventory']:

            commands.inv_set_pages(bot, message, user, bd_user)

        if message.text in ['⁉ Видимость FAQ', '⁉ Visibility FAQ']:

            commands.settings_faq(bot, message, user, bd_user)

        if Functions.tr_c_f(bd_user) and message.text in ['💬 Переименовать', '💬 Rename']:

            commands.rename_dino(bot, message, user, bd_user)

        if message.text in ["➕ Добавить", "➕ Add"]:

            commands.add_friend(bot, message, user, bd_user)

        if message.text in ["📜 Список", "📜 List"]:

            commands.friends_list(bot, message, user, bd_user)

        if message.text in ["💌 Запросы", "💌 Inquiries"]:

            Functions.user_requests(bot, user, message)

        if message.text in ['➖ Удалить', '➖ Delete']:

            commands.delete_friend(bot, message, user, bd_user)

        if message.text in ['🤍 Пригласи друга', '🤍 Invite a friend']:

            commands.invite_friend(bot, message, user, bd_user)

        if message.text in ['🎲 Сгенерировать код', '🎲 Generate Code']:

            commands.generate_fr_code(bot, message, user, bd_user)

        if message.text in ['🎞 Ввести код', '🎞 Enter Code']:

            commands.enter_fr_code(bot, message, user, bd_user)

        if message.text in ['👥 Меню друзей', '👥 Friends Menu']:

            commands.friends_menu(bot, message, user, bd_user)

        if Functions.tr_c_f(bd_user) and message.text in ['🌙 Уложить спать', '🌙 Put to bed']:

            commands.dino_sleep_ac(bot, message, user, bd_user)

        if Functions.tr_c_f(bd_user) and message.text in ['🌙 Пробудить', '🌙 Awaken']:

            commands.dino_unsleep_ac(bot, message, user, bd_user)

        if Functions.tr_c_f(bd_user) and message.text in ['🎑 Путешествие', '🎑 Journey']:

            commands.dino_journey(bot, message, user, bd_user)

        if Functions.tr_c_f(bd_user) and message.text in ['🎑 Вернуть', '🎑 Call']:

            commands.dino_unjourney(bot, message, user, bd_user)

        if Functions.tr_c_f(bd_user) and message.text in ['🎮 Развлечения', '🎮 Entertainments']:

            commands.dino_entert(bot, message, user, bd_user)

        if Functions.tr_c_f(bd_user) and message.text in ['🍣 Покормить', '🍣 Feed']:

            commands.dino_feed(bot, message, user, bd_user)

        if Functions.tr_c_f(bd_user) and message.text in ['🍕 Сбор пищи', '🍕 Collecting food']:

            commands.collecting_food(bot, message, user, bd_user)

        if Functions.tr_c_f(bd_user) and message.text in ['🍕 Прогресс', '🍕 Progress']:

            commands.coll_progress(bot, message, user, bd_user)

        if Functions.tr_c_f(bd_user) and (message.text[:11] in ['🦖 Динозавр:'] or message.text[:7] in [ '🦖 Dino:']):

            commands.dino_action_ans(bot, message, user, bd_user)

        if Functions.tr_c_f(bd_user) and message.text in ['↩ Назад', '↩ Back']:

            commands.action_back(bot, message, user, bd_user)

        if Functions.tr_c_f(bd_user) and message.text in ['🎮 Консоль', '🪁 Змей', '🏓 Пинг-понг', '🏐 Мяч', '🎮 Console', '🪁 Snake', '🏓 Ping Pong', '🏐 Ball', '🧩 Пазлы', '♟ Шахматы', '🧱 Дженга', '🎲 D&D', '🧩 Puzzles', '♟ Chess', '🧱 Jenga']:

            commands.dino_entert_games(bot, message, user, bd_user)

        if Functions.tr_c_f(bd_user) and message.text in ['❌ Остановить игру', '❌ Stop the game']:

            commands.dino_stop_games(bot, message, user, bd_user)

        if message.text in ['🎢 Рейтинг', '🎢 Rating']:

            commands.rayting(bot, message, user, bd_user)

        if message.text in ['📜 Информация', '📜 Information']:

            commands.open_information(bot, message, user, bd_user)

        if message.text in ['🛒 Рынок', '🛒 Market']:

            commands.open_market_menu(bot, message, user, bd_user)

        if message.text in ['💍 Аксессуары', '💍 Accessories']:

            commands.acss(bot, message, user, bd_user)

        if message.text in ['➕ Добавить товар', '➕ Add Product']:

            Functions.user_inventory(bot, user, message, 'add_product')

        if message.text in ['📜 Мои товары', '📜 My products']:

            commands.my_products(bot, message, user, bd_user)

        if message.text in ['➖ Удалить товар', '➖ Delete Product']:

            commands.delete_product(bot, message, user, bd_user)

        if message.text in [ '🔍 Поиск товара', '🔍 Product Search']:

            commands.search_pr(bot, message, user, bd_user)

        if message.text in [ '🛒 Случайные товары', '🛒 Random Products']:

            commands.random_search(bot, message, user, bd_user)

        if message.text in ['⛓ Квесты', '⛓ Quests']:

            commands.quests(bot, message, user, bd_user)

        if message.text in ['🎭 Навыки', '🎭 Skills']:

            bot.send_message(user.id, 'Данная функция находится в разработке, следите за новостями, дабы узнать когда команда заработает!\n\nThis feature is under development, follow the news in order to find out when the team will work!')

        if message.text in ['🦖 БИО', '🦖 BIO']:

            bot.send_message(user.id, 'Данная функция находится в разработке, следите за новостями, дабы узнать когда команда заработает!\n\nThis feature is under development, follow the news in order to find out when the team will work!')

        if message.text in [ '👁‍🗨 Динозавры в таверне', '👁‍🗨 Dinosaurs in the Tavern']:

            bot.send_message(user.id, 'Данная функция находится в разработке, следите за новостями, дабы узнать когда команда заработает!\n\nThis feature is under development, follow the news in order to find out when the team will work!')

        if message.text in [ '♻ Change Dinosaur', '♻ Изменение Динозавра']:

            commands.rarity_change(bot, message, user, bd_user)

        if message.text in [ '🥏 Дрессировка', '🥏 Training']:

            bot.send_message(user.id, 'Данная функция находится в разработке, следите за новостями, дабы узнать когда команда заработает!\n\nThis feature is under development, follow the news in order to find out when the team will work!')

        if message.text in [ "💡 Исследования", "💡 Research"]:

            bot.send_message(user.id, 'Данная функция находится в разработке, следите за новостями, дабы узнать когда команда заработает!\n\nThis feature is under development, follow the news in order to find out when the team will work!')

        if message.text in [ "🗻 Подземелья", "🗻 Dungeons"]:

            commands.dungeon_menu(bot, message, user, bd_user)

        if message.text in [ "🗻 Создать", "🗻 Create"]:

            commands.dungeon_create(bot, message, user, bd_user)

        if message.text in [ '🚪 Присоединиться', '🚪 Join']:

            commands.dungeon_join(bot, message, user, bd_user)

        if message.text in [ '⚔ Экипировка', '⚔ Equip']:

            commands.dungeon_equipment(bot, message, user, bd_user)

        if message.text in [ '📕 Правила подземелья', '📕 Dungeon Rules' ]:

            commands.dungeon_rules(bot, message, user, bd_user)

        if message.text in [ '🎮 Статистика', '🎮 Statistics' ]:

            commands.dungeon_statist(bot, message, user, bd_user)

        if bd_user != None:
            # последняя активность
            users.update_one( {"userid": bd_user['userid']}, {"$set": {'last_m': int(time.time()) }} )


@bot.callback_query_handler(wait_callback = True, func = lambda call: True)
def answer(call):
    user = call.from_user
    bd_user = users.find_one({"userid": user.id})

    if call.data == 'start':

        call_data.start(bot, bd_user, call, user)

    if call.data == 'checking_the_user_in_the_channel':

        call_data.checking_the_user_in_the_channel(bot, bd_user, call, user)

    if call.data in ['egg_answer_1', 'egg_answer_2', 'egg_answer_3']:

        call_data.egg_answer(bot, bd_user, call, user)

    if call.data[:13] in ['90min_journey', '60min_journey', '30min_journey', '10min_journey', '12min_journey', '24min_journey']:

        call_data.journey(bot, bd_user, call, user)

    if call.data[:10] in ['1_con_game', '2_con_game', '3_con_game', '1_sna_game', '2_sna_game', '3_sna_game', '1_pin_game', '2_pin_game', '3_pin_game', '1_bal_game', '2_bal_game', '3_bal_game', '1_puz_game', '2_puz_game', '3_puz_game', '1_che_game', '2_che_game', '3_che_game', '1_jen_game', '2_jen_game', '3_jen_game', '1_ddd_game', '2_ddd_game', '3_ddd_game']:

        call_data.game(bot, bd_user, call, user)

    if call.data in ['dead_answer1', 'dead_answer2', 'dead_answer3', 'dead_answer4']:

        call_data.dead_answer(bot, bd_user, call, user)

    if call.data == 'dead_restart':

        call_data.dead_restart(bot, bd_user, call, user)

    if call.data[:5] == 'item_':

        call_data.item_use(bot, bd_user, call, user)

    if call.data[:12] == 'remove_item_':

        call_data.remove_item(bot, bd_user, call, user)

    if call.data[:7] == 'remove_':

        call_data.remove(bot, bd_user, call, user)

    if call.data == "cancel_remove":

        bot.delete_message(user.id, call.message.message_id)

    if call.data[:9] == 'exchange_':

        call_data.exchange(bot, bd_user, call, user)

    if call.data[:11] == 'market_buy_':

        call_data.market_buy(bot, bd_user, call, user)

    if call.data[:7] == 'market_':

        call_data.market_inf(bot, bd_user, call, user)

    if call.data[:9] == 'iteminfo_':

        call_data.iteminfo(bot, bd_user, call, user)

    if call.data == 'inventory':

        Functions.user_inventory(bot, user, call.message)

    if call.data == 'requests':

        Functions.user_requests(bot, user, call.message)

    if call.data == 'send_request':

        call_data.send_request(bot, bd_user, call, user)

    if call.data[:18] == 'open_dino_profile_':

        did = call.data[18:]
        if did in bd_user['dinos'].keys():
            bd_dino = bd_user['dinos'][did]
            Functions.p_profile(bot, call.message, bd_dino, user, bd_user, did)

    if call.data[:8] == 'ns_craft':

        call_data.ns_craft(bot, bd_user, call, user)

    if call.data[:13] == 'change_rarity':

        call_data.change_rarity_call_data(bot, bd_user, call, user)

    if call.data.split()[0] == 'cancel_progress':

        call_data.cancel_progress(bot, bd_user, call, user)

    if call.data.split()[0] == 'message_delete':

        show_text = "✉ > 🗑"
        bot.answer_callback_query(call.id, show_text)

        try:
            bot.delete_message(user.id, call.message.message_id)
        except:
            pass

    if call.data.split()[0] == 'dungeon.settings':

        call_data.dungeon_settings(bot, bd_user, call, user)

    if call.data.split()[0] == 'dungeon.to_lobby':

        call_data.dungeon_to_lobby(bot, bd_user, call, user)

    if call.data.split()[0] == 'dungeon.settings_lang':

        call_data.dungeon_settings_lang(bot, bd_user, call, user)

    if call.data.split()[0] == 'dungeon.settings_batnotf':

        call_data.dungeon_settings_batnotf(bot, bd_user, call, user)

    if call.data.split()[0] == 'dungeon.leave':

        call_data.dungeon_leave(bot, bd_user, call, user)

    if call.data.split()[0] == 'dungeon.leave_True':

        call_data.dungeon_leave_True(bot, bd_user, call, user)

    if call.data.split()[0] == 'dungeon.leave_False':

        call_data.dungeon_leave_False(bot, bd_user, call, user)

    if call.data.split()[0] == 'dungeon.remove':

        call_data.dungeon_remove(bot, bd_user, call, user)

    if call.data.split()[0] == 'dungeon.remove_True':

        call_data.dungeon_remove_True(bot, bd_user, call, user)

    if call.data.split()[0] == 'dungeon.remove_False':

        call_data.dungeon_remove_False(bot, bd_user, call, user)

    if call.data.split()[0] == 'dungeon.menu.add_dino':

        call_data.dungeon_add_dino_menu(bot, bd_user, call, user)

    if call.data.split()[0] == 'dungeon.menu.remove_dino':

        call_data.dungeon_remove_dino_menu(bot, bd_user, call, user)

    if call.data.split()[0] == 'dungeon.action.add_dino':

        call_data.dungeon_add_dino(bot, bd_user, call, user)

    if call.data.split()[0] == 'dungeon.action.remove_dino':

        call_data.dungeon_remove_dino(bot, bd_user, call, user)

    if call.data.split()[0] == 'dungeon.ready':

        call_data.dungeon_ready(bot, bd_user, call, user)

    if call.data.split()[0] == 'dungeon.invite':

        call_data.dungeon_invite(bot, bd_user, call, user)

    if call.data.split()[0] == 'dungeon.supplies':

        call_data.dungeon_supplies(bot, bd_user, call, user)

    if call.data.split()[0] == 'dungeon.action.set_coins':

        call_data.dungeon_set_coins(bot, bd_user, call, user)

    if call.data.split()[0] == 'dungeon.action.add_item':

        call_data.dungeon_add_item_action(bot, bd_user, call, user)

    if call.data.split()[0] == 'dungeon.action.remove_item':

        call_data.dungeon_remove_item_action(bot, bd_user, call, user)

    if call.data.split()[0] == 'dungeon_add_item':

        call_data.dungeon_add_item(bot, bd_user, call, user)

    if call.data.split()[0] == 'dungeon_remove_item':

        call_data.dungeon_remove_item(bot, bd_user, call, user)

    if call.data.split()[0] == 'dungeon.start':

        call_data.dungeon_start_game(bot, bd_user, call, user)

    if call.data.split()[0] == 'dungeon.next_room':

        call_data.dungeon_next_room(bot, bd_user, call, user)

    if call.data.split()[0] == 'dungeon.action.battle_action':

        call_data.dungeon_battle_action(bot, bd_user, call, user)

    if call.data.split()[0] == 'dungeon.battle_action_attack':

        call_data.dungeon_battle_attack(bot, bd_user, call, user)

    if call.data.split()[0] == 'dungeon.battle_action_defend':

        call_data.dungeon_battle_defend(bot, bd_user, call, user)

    if call.data.split()[0] == 'dungeon.battle_action_idle':

        call_data.dungeon_battle_idle(bot, bd_user, call, user)

    if call.data.split()[0] == 'dungeon.next_room_ready':

        call_data.dungeon_next_room_ready(bot, bd_user, call, user)

    if call.data.split()[0] == 'dungeon.end_move':

        call_data.dungeon_end_move(bot, bd_user, call, user)

    if call.data.split()[0] == 'dungeon.dinos_stats':

        call_data.dungeon_dinos_stats(bot, bd_user, call, user)

    if call.data.split()[0] == 'dungeon.collect_reward':

        call_data.dungeon_collect_reward(bot, bd_user, call, user)

    if call.data.split()[0] == 'dungeon.item_from_reward':

        call_data.item_from_reward(bot, bd_user, call, user)

    if call.data.split()[0] == 'dungeon.inventory':

        call_data.dungeon_inventory(bot, bd_user, call, user)

    if call.data.split()[0] == '-' or call.data.split()[0] == ' ':
        pass

    if call.data.split()[0] == 'dungeon_use_item_info':

        call_data.dungeon_use_item_info(bot, bd_user, call, user)

    if call.data.split()[0] == 'dungeon_use_item':

        call_data.dungeon_use_item(bot, bd_user, call, user)

    if call.data.split()[0] == 'dungeon_use_item':

        call_data.dungeon_use_item(bot, bd_user, call, user)

    if call.data.split()[0] == 'dungeon_delete_item':

        call_data.dungeon_delete_item(bot, bd_user, call, user)

    if call.data.split()[0] == 'dungeon.kick_member':

        call_data.dungeon_kick_member(bot, bd_user, call, user)

    if call.data.split()[0] == 'dungeon_kick':

        call_data.dungeon_kick(bot, bd_user, call, user)

    if call.data.split()[0] == 'dungeon.leave_in_game':

        call_data.dungeon_leave_in_game(bot, bd_user, call, user)

    if call.data.split()[0] == 'dungeon.leave_in_game_answer':

        call_data.dungeon_leave_in_game_answer(bot, bd_user, call, user)

    if call.data.split()[0] == 'dungeon.fork_answer':

        call_data.dungeon_fork_answer(bot, bd_user, call, user)

    if call.data.split()[0] == 'dungeon.safe_exit':

        call_data.dungeon_safe_exit(bot, bd_user, call, user)

    if call.data.split()[0] == 'dungeon.mine':

        call_data.dungeon_mine(bot, bd_user, call, user)

    if call.data.split()[0] == 'dungeon.shop_menu':

        call_data.dungeon_shop_menu(bot, bd_user, call, user)

    if call.data.split()[0] == 'dungeon.shop_buy':

        call_data.dungeon_shop_buy(bot, bd_user, call, user)

    if call.data.split()[0] == 'dungeon.settings_start_floor':

        call_data.dungeon_settings_start_floor(bot, bd_user, call, user)

    if call.data.split()[0] == 'dungeon.start_floor':

        call_data.dungeon_start_floor(bot, bd_user, call, user)

    if call.data.split()[0] == 'rayt_lvl':

        call_data.rayt_lvl(bot, bd_user, call, user)

    if call.data.split()[0] == 'rayt_money':

        call_data.rayt_money(bot, bd_user, call, user)

    if call.data.split()[0] == 'rayt_dungeon':

        call_data.rayt_dungeon(bot, bd_user, call, user)

    if call.data.split()[0] == 'complete_quest':

        call_data.complete_quest(bot, bd_user, call, user)

    if call.data.split()[0] == 'delete_quest':

        call_data.delete_quest(bot, bd_user, call, user)


def start_all(bot):

    if bot.get_me().first_name == 'DinoGochi' or False:
        main_checks.start() # активация всех проверок и игрового процесса
        thr_notif.start() # активация уведомлений
        min10_thr.start() # десяти-минутный чек
        min1_thr.start() # 1-мин чек

    bot.add_custom_filter(SpamStop())
    bot.add_custom_filter(Test_bot())
    bot.add_custom_filter(In_channel())
    bot.add_custom_filter(WC())
    bot.add_custom_filter(In_Dungeon())

    try:
        Functions.clean_tmp()
    except:
        print('Временные изображения не были очищены.')

    print(f'Бот {bot.get_me().first_name} запущен!')
    bot.infinity_polling(skip_pending = False)

start_all(bot)
