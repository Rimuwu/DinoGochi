import telebot
from telebot import types
import config
import random
import json
import pymongo
from PIL import Image, ImageFont, ImageDraw, ImageOps, ImageSequence, ImageFilter
import io
from io import BytesIO
import time
import threading
import sys
from memory_profiler import memory_usage
import pprint
from fuzzywuzzy import fuzz

sys.path.append("Cogs")
from commands import commands
from functions import functions
from checks import checks
from call_data import call_data

bot = telebot.TeleBot(config.TOKEN)

client = pymongo.MongoClient(config.CLUSTER_TOKEN)
users = client.bot.users
referal_system = client.bot.referal_system
market = client.bot.market
dungeons = client.bot.dungeons

with open('data/items.json', encoding='utf-8') as f:
    items_f = json.load(f)

with open('data/dino_data.json', encoding='utf-8') as f:
    json_f = json.load(f)


def check(): #проверка каждые 10 секунд

    def alpha(bot, members): checks.main(bot, members)

    def beta(bot, members): checks.main_hunting(bot, members)

    def beta2(bot, members): checks.main_game(bot, members)

    def gamma(bot, members): checks.main_sleep(bot, members)

    def gamma2(bot, members): checks.main_pass(bot, members)

    def delta(bot, members): checks.main_journey(bot, members)

    def memory(): checks.check_memory()

    non_members = users.find({ })
    chunks_users = list(functions.chunks( list(non_members), 50 ))
    functions.check_data('col', None, int(len(chunks_users)) )

    while True:
        if int(memory_usage()[0]) < 1500:
            st_r_time = int(time.time())
            non_members = users.find({ })
            chunks_users = list(functions.chunks( list(non_members), 50 ))
            sl_time = 10 - ( int(time.time()) - st_r_time )

            if sl_time <= 0:
                print(f'WARNING: sleep time: {sl_time}, time sleep skip to 10')
                sl_time = 10

            for members in chunks_users:

                threading.Thread(target = alpha,  daemon=True, kwargs = {'bot': bot, 'members': members}).start()
                threading.Thread(target = beta,   daemon=True, kwargs = {'bot': bot, 'members': members} ).start()
                threading.Thread(target = beta2,  daemon=True, kwargs = {'bot': bot, 'members': members} ).start()
                threading.Thread(target = gamma,  daemon=True, kwargs = {'bot': bot, 'members': members} ).start()
                threading.Thread(target = gamma2, daemon=True, kwargs = {'bot': bot, 'members': members} ).start()
                threading.Thread(target = delta,  daemon=True, kwargs = {'bot': bot, 'members': members}).start()

            threading.Thread(target = memory, daemon=True ).start()

        else:
            print(f'Использование памяти: {int(memory_usage()[0])}')

        time.sleep(sl_time)

main_checks = threading.Thread(target = check, daemon=True)

def check_notif(): #проверка каждые 5 секунд

    def alpha(bot, members): checks.check_notif(bot, members)

    def beta(bot): checks.check_incub(bot)

    while True:

        if int(memory_usage()[0]) < 1500:
            non_members = users.find({ })
            chunks_users = list(functions.chunks( list(non_members), 50 ))

            for members in chunks_users:
                threading.Thread(target = alpha, daemon=True, kwargs = {'bot': bot, 'members': members}).start()

            threading.Thread(target = beta, daemon=True, kwargs = {'bot': bot}).start()

        else:
            print(f'Использование памяти: {int(memory_usage()[0])}')

        time.sleep(5)

thr_notif = threading.Thread(target = check_notif, daemon=True)

def min10_check(): #проверка каждые 10 мин

    def alpha(users): checks.rayt(users)

    def dead_users(bot): checks.check_dead_users(bot)

    while True:

        if int(memory_usage()[0]) < 1500:
            uss = users.find({ })
            threading.Thread(target = alpha, daemon=True, kwargs = {'users': uss}).start()

            if bot.get_me().first_name == 'DinoGochi':
                threading.Thread(target = dead_users, daemon=True, kwargs = {'bot': bot} ).start()

        else:
            print(f'Использование памяти: {int(memory_usage()[0])}')

        time.sleep(600)

min10_thr = threading.Thread(target = min10_check, daemon=True)

@bot.message_handler(commands=['stats'])
def command(message):
    user = message.from_user
    checks_data = functions.check_data(m = 'check')

    def ttx(tm, lst):
        lgs = []
        for i in lst:
            lgs.append(f'{int(tm) - i}s')
        return ', '.join(lgs)


    text = 'STATS\n\n'
    text += f"Memory: {checks_data['memory'][0]}mb\nLast {int(time.time() - checks_data['memory'][1]) }s\n\n"
    text += f"Incub check: {checks_data['incub'][0]}s\nLast {int(time.time() - checks_data['incub'][1])}s\nUsers: {checks_data['incub'][2]}\n\n"
    text += f"Notifications check: {'s, '.join(str(i) for i in checks_data['notif'][0])}\nLast { ttx(time.time(), checks_data['notif'][1]) }\n\n"

    for cls in ['main', 'main_hunt', 'main_game', 'main_sleep', 'main_pass', 'main_journey']:
        text += f"{cls} check: {'s, '.join(str(i) for i in checks_data[cls][0])}\nLast { ttx(time.time(), checks_data[cls][1]) }\nUsers: {str(checks_data[cls][2])}\n\n"


    text += f'Thr.count: {threading.active_count()}'
    bot.send_message(user.id, text)


@bot.message_handler(commands=['dinos'])
def command(message):
    user = message.from_user
    bd_user = users.find_one({"userid": user.id})
    text = ''
    for i in bd_user['dinos']:
        if 'journey_log' in bd_user["dinos"][i].keys():
            bd_user["dinos"][i]['journey_log'] = f"{len(bd_user['dinos'][i]['journey_log'])} - событий"

        text = f'{bd_user["dinos"][i]}\n\n'
    bot.send_message(user.id, text)

@bot.message_handler(commands=['iam'])
def command(message):
    user = message.from_user
    bd_user = users.find_one({"userid": user.id})
    pprint.pprint(bd_user)

@bot.message_handler(commands=['d_journey'])
def command(message):
    user = message.from_user
    bd_user = users.find_one({"userid": user.id})

    if user.id in [5279769615, 1191252229]:

        def dino_journey(bd_user, user, dino_user_id):

            dino_id = str(bd_user['dinos'][ dino_user_id ]['dino_id'])
            dino = json_f['elements'][dino_id]
            n_img = random.randint(1,5)
            bg_p = Image.open(f"images/journey/{n_img}.png")

            dino_image = Image.open("images/"+str(json_f['elements'][dino_id]['image']))
            sz = 412
            dino_image = dino_image.resize((sz, sz), Image.ANTIALIAS)
            dino_image = dino_image.transpose(Image.FLIP_LEFT_RIGHT)

            xy = -35
            x2 = random.randint(80,120)
            img = functions.trans_paste(dino_image, bg_p, 1.0, (xy + x2, xy, sz + xy + x2, sz + xy ))

            img.save('profile.png')
            profile = open(f"profile.png", 'rb')

            return profile

        profile_i = dino_journey(bd_user, user, '1')

        text = f'🎈 | Если у динозавра хорошее настроение, он может принести обратно какие то вещи.\n\n🧶 | Во время путешествия, могут произойти разные ситуации, от них зависит результат путешествия.'

        bot.send_photo(message.chat.id, profile_i, text )

@bot.message_handler(commands=['check_inv'])
def command(message):
    user = message.from_user
    msg_args = message.text.split()
    bd_user = users.find_one({"userid": int(msg_args[1])})
    print('id', msg_args[2], type(msg_args[2]))
    for i in bd_user['inventory']:

        if i['item_id'] == msg_args[2]:
            print(' #                 ============================================= #')
            print(i)
            print(bd_user['inventory'].index(i))

    print('all')

@bot.message_handler(commands=['test_edit'])
def command(message):
    user = message.from_user
    if user.id in [5279769615, 1191252229]:

        markup = types.ReplyKeyboardMarkup(resize_keyboard = True)
        markup.add(* [x for x in ['кнопка1', 'кнопка2']] )

        msg = bot.send_message(message.chat.id, 'текст1', reply_markup = markup)
        bot.edit_message_text(text = 'text2', chat_id = msg.chat.id, message_id = msg.message_id)

@bot.message_handler(commands=['delete_dinos_check_acc'])
def command(message):
    user = message.from_user
    if user.id in [5279769615, 1191252229]:
        bd_user = users.find_one({"userid": user.id})
        users.update_one( {"userid": user.id}, {"$set": {f'dinos': {} }} )
        print("all")

@bot.message_handler(commands=['quality_edit'])
def command(message):

    user = message.from_user
    if user.id in [5279769615, 1191252229]:
        bd_user = users.find_one({"userid": user.id})
        for i in bd_user['dinos']:
            dino = bd_user['dinos'][i]
            dino_data = json_f['elements'][str(dino['dino_id'])]

            print(dino_data)
            users.update_one( {"userid": user.id}, {"$set": {f'dinos.{i}.quality': dino_data['image'][5:8] }} )

        print("all")

# @bot.message_handler(commands=['add_quality_to_all'])
# def command_n(message):
#     user = message.from_user
#     if user.id in [5279769615, 1191252229]:
#
#         def work(members, n):
#             for bd_user in members:
#                 print(bd_user['userid'])
#                 for i in bd_user['dinos']:
#                     dino = {}
#                     dino = bd_user['dinos'][i]
#                     dino_data = json_f['elements'][str(dino['dino_id'])]
#
#                     users.update_one( {"userid": user.id}, {"$set": {f'dinos.{i}.quality': dino_data['image'][5:8] }} )
#
#             print(f'Программа обновления №{n} завершила работу.')
#
#         non_members = [users.find_one({"userid": 1191252229}), users.find_one({"userid": 5279769615})] #users.find({ })
#         chunks_users = list(functions.chunks( list(non_members), 1 ))
#
#         n = 0
#         for members in chunks_users:
#             n += 1
#             main = threading.Thread(target = work, daemon=True, kwargs = { 'members': members, 'n': n}).start()
#             print(f'Программа обновления №{n} начала работу.')

@bot.message_handler(commands=['add_item'])
def command(message):
    user = message.from_user
    if user.id in [5279769615, 1191252229]:
        msg_args = message.text.split()
        bd = users.find_one({"userid": int(msg_args[3])})

        tr = functions.add_item_to_user(bd, msg_args[1], int(msg_args[2]))
        bot.send_message(user.id, str(msg_args))

@bot.message_handler(commands=['events'])
def command(message):
    user = message.from_user
    if user.id in [5279769615, 1191252229]:
        bd_user = users.find_one({"userid": user.id})

        functions.journey_end_log(bot, user.id, bd_user['settings']['dino_id'])

@bot.message_handler(commands=['events_clear'])
def command(message):
    user = message.from_user
    if user.id in [5279769615, 1191252229]:
        bd_user = users.find_one({"userid": user.id})

        users.update_one( {"userid": user.id}, {"$set": {f"dinos.{bd_user['settings']['dino_id']}.journey_log": [] }} )

        print(';;; all')

@bot.message_handler(commands=['reply_id'])
def command(message):
    user = message.from_user
    if user.id in [5279769615, 1191252229]:
        msg = message.reply_to_message
        if msg != None:
            bot.reply_to(message, msg.message_id)
            print(msg.message_id)

@bot.message_handler(commands=['dungeon'])
def command(message):
    user = message.from_user
    if user.id in [5279769615, 1191252229]:
        dng, inf = functions.dungeon_base_upd(userid = user.id, dinosid = ['1', '2'])
        pprint.pprint(dng)
        print(inf)

        inf = functions.dungeon_message_upd(bot, userid = user.id, dungeonid = user.id)
        print(inf)

@bot.message_handler(commands=['dungeon_add'])
def command(message):
    user = message.from_user
    msg_args = message.text.split()
    if user.id in [5279769615, 1191252229]:

        dng, inf = functions.dungeon_base_upd(userid = user.id, dinosid = ['1'], dungeonid = int(msg_args[1]), type = 'add_user')
        pprint.pprint(dng)
        print(inf)

        inf = functions.dungeon_message_upd(bot, userid = user.id, dungeonid = dng['dungeonid'], upd_type = 'all')
        print(inf)

@bot.message_handler(commands=['dungeon_delete'])
def command(message):
    user = message.from_user
    if user.id in [5279769615, 1191252229]:
        inf = functions.dungeon_message_upd(bot, dungeonid = user.id, type = 'delete_dungeon')
        print(inf)

        dng, inf = functions.dungeon_base_upd(dungeonid = user.id, type = 'delete_dungeon')
        pprint.pprint(dng)
        print(inf)


# =========================================

@bot.message_handler(commands=['emulate_not'])
def command(message):
    print('emulate_not')
    msg_args = message.text.split()
    user = message.from_user
    bd_user = users.find_one({"userid": user.id})
    functions.notifications_manager(bot, msg_args[1], bd_user, msg_args[2], dino_id = '1')

@bot.message_handler(commands=['profile', 'профиль'])
def command(message):
    user = message.from_user
    bd_user = users.find_one({"userid": user.id})
    if bd_user != None:

        text = functions.member_profile(bot, user.id, bd_user['language_code'])

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

            bot.reply_to(message, text, parse_mode = 'HTML', reply_markup = functions.inline_markup(bot, 'send_request', user.id, ['Отправить запрос', 'Send a request']) )

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

            bot.reply_to(message, text, reply_markup = functions.markup(bot, user = user), parse_mode = 'html')
        else:
            bot.reply_to(message, '👋', reply_markup = functions.markup(bot, user = user), parse_mode = 'html')


@bot.message_handler(content_types = ['text'])
def on_message(message):

    user = message.from_user
    bd_user = users.find_one({"userid": user.id})

    def tr_c_f():
        tr_c = False
        stats_list = []
        if bd_user != None and len(list(bd_user['dinos'])) > 0:
            for i in bd_user['dinos'].keys():
                dd = bd_user['dinos'][i]
                stats_list.append(dd['status'])

            if 'dino' in stats_list:
                tr_c = True

        return tr_c

    def lst_m_f():

        if bd_user != None:
            last_mrk = functions.last_markup(bd_user, alternative = 1)
        else:
            last_mrk = None

        return last_mrk

    if bot.get_me().first_name != 'DinoGochi':
        print("Поймал", message.text, 'от ', user.first_name)
        if user.id not in [5279769615, 1191252229]:
            return print('Отмена команды')

    if message.chat.type == 'private':
        if functions.spam_stop(user.id) == False:
            bot.delete_message(user.id, message.message_id)
            return

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

        else:

            if message.text in ['🍡 Начать играть', '🍡 Start playing']:

                commands.start_game(bot, message, user, bd_user)

            elif message.text in ["🧩 Проект: Возрождение", '🧩 Project: Rebirth']:

                commands.project_reb(bot, message, user, bd_user)

            elif message.text in ['↪ Назад', '↪ Back', '❌ Cancel', '❌ Отмена']:

                commands.back_open(bot, message, user, bd_user)

            elif message.text in ['👁‍🗨 Профиль', '👁‍🗨 Profile']:

                commands.open_profile_menu(bot, message, user, bd_user)

            elif message.text in ['🎮 Инвентарь', '🎮 Inventory']:

                functions.user_inventory(bot, user, message)

            elif message.text in ['🦖 Динозавр', '🦖 Dinosaur']:

                commands.dino_prof(bot, message, user)

            elif message.text in ['🔧 Настройки', '🔧 Settings']:

                commands.open_settings(bot, message, user, bd_user)

            elif message.text in ['👥 Друзья', '👥 Friends']:

                commands.friends_open(bot, message, user, bd_user)

            elif message.text in ['❗ FAQ']:

                commands.faq(bot, message, user, bd_user)

            elif message.text in ['🍺 Дино-таверна', '🍺 Dino-tavern'] and lst_m_f() != 'dino-tavern':

                commands.open_dino_tavern(bot, message, user, bd_user)

            elif tr_c_f() and message.text in ['🕹 Действия', '🕹 Actions']:

                commands.open_action_menu(bot, message, user, bd_user)

            elif message.text in ['❗ Notifications', '❗ Уведомления']:

                commands.not_set(bot, message, user, bd_user)

            elif message.text in ["👅 Язык", "👅 Language"]:

                commands.lang_set(bot, message, user, bd_user)

            elif message.text in ['⁉ Видимость FAQ', '⁉ Visibility FAQ']:

                commands.settings_faq(bot, message, user, bd_user)

            elif tr_c_f() and message.text in ['💬 Переименовать', '💬 Rename']:

                commands.rename_dino(bot, message, user, bd_user)

            elif message.text in ["➕ Добавить", "➕ Add"]:

                commands.add_friend(bot, message, user, bd_user)

            elif message.text in ["📜 Список", "📜 List"]:

                commands.friends_list(bot, message, user, bd_user)

            elif message.text in ["💌 Запросы", "💌 Inquiries"]:

                functions.user_requests(bot, user, message)

            elif message.text in ['➖ Удалить', '➖ Delete']:

                commands.delete_friend(bot, message, user, bd_user)

            elif message.text in ['🤍 Пригласи друга', '🤍 Invite a friend']:

                commands.invite_friend(bot, message, user, bd_user)

            elif message.text in ['🎲 Сгенерировать код', '🎲 Generate Code']:

                commands.generate_fr_code(bot, message, user, bd_user)

            elif message.text in ['🎞 Ввести код', '🎞 Enter Code']:

                commands.enter_fr_code(bot, message, user, bd_user)

            elif message.text in ['👥 Меню друзей', '👥 Friends Menu']:

                commands.friends_menu(bot, message, user, bd_user)

            elif tr_c_f() and message.text in ['🌙 Уложить спать', '🌙 Put to bed']:

                commands.dino_sleep_ac(bot, message, user, bd_user)

            elif tr_c_f() and message.text in ['🌙 Пробудить', '🌙 Awaken']:

                commands.dino_unsleep_ac(bot, message, user, bd_user)

            elif tr_c_f() and message.text in ['🎑 Путешествие', '🎑 Journey']:

                commands.dino_journey(bot, message, user, bd_user)

            elif tr_c_f() and message.text in ['🎑 Вернуть', '🎑 Call']:

                commands.dino_unjourney(bot, message, user, bd_user)

            elif tr_c_f() and message.text in ['🎮 Развлечения', '🎮 Entertainments']:

                commands.dino_entert(bot, message, user, bd_user)

            elif tr_c_f() and message.text in ['🍣 Покормить', '🍣 Feed']:

                commands.dino_feed(bot, message, user, bd_user)

            elif tr_c_f() and message.text in ['🍕 Сбор пищи', '🍕 Collecting food']:

                commands.collecting_food(bot, message, user, bd_user)

            elif tr_c_f() and message.text in ['🍕 Прогресс', '🍕 Progress']:

                commands.coll_progress(bot, message, user, bd_user)

            elif tr_c_f() and (message.text[:11] in ['🦖 Динозавр:'] or message.text[:7] in [ '🦖 Dino:']):

                commands.dino_action_ans(bot, message, user, bd_user)

            elif tr_c_f() and message.text in ['↩ Назад', '↩ Back']:

                commands.action_back(bot, message, user, bd_user)

            elif tr_c_f() and message.text in ['🎮 Консоль', '🪁 Змей', '🏓 Пинг-понг', '🏐 Мяч', '🎮 Console', '🪁 Snake', '🏓 Ping Pong', '🏐 Ball', '🧩 Пазлы', '♟ Шахматы', '🧱 Дженга', '🎲 D&D', '🧩 Puzzles', '♟ Chess', '🧱 Jenga']:

                commands.dino_entert_games(bot, message, user, bd_user)

            elif tr_c_f() and message.text in ['❌ Остановить игру', '❌ Stop the game']:

                commands.dino_stop_games(bot, message, user, bd_user)

            elif message.text in ['🎢 Рейтинг', '🎢 Rating']:

                commands.rayting(bot, message, user, bd_user)

            elif message.text in ['📜 Информация', '📜 Information']:

                commands.open_information(bot, message, user, bd_user)

            elif message.text in ['🛒 Рынок', '🛒 Market']:

                commands.open_market_menu(bot, message, user, bd_user)

            elif message.text in ['💍 Аксессуары', '💍 Accessories']:

                commands.acss(bot, message, user, bd_user)

            elif message.text in ['➕ Добавить товар', '➕ Add Product']:

                functions.user_inventory(bot, user, message, 'add_product')

            elif message.text in ['📜 Мои товары', '📜 My products']:

                commands.my_products(bot, message, user, bd_user)

            elif message.text in ['➖ Удалить товар', '➖ Delete Product']:

                commands.delete_product(bot, message, user, bd_user)

            elif message.text in [ '🔍 Поиск товара', '🔍 Product Search']:

                commands.search_pr(bot, message, user, bd_user)

            elif message.text in [ '🛒 Случайные товары', '🛒 Random Products']:

                commands.random_search(bot, message, user, bd_user)

            elif message.text in ['⛓ Квесты', '⛓ Quests']:

                bot.send_message(user.id, 'Данная функция находится в разработке, следите за новостями, дабы узнать когда команда заработает!\n\nThis feature is under development, follow the news in order to find out when the team will work!')

            elif message.text in ['🎭 Навыки', '🎭 Skills']:

                bot.send_message(user.id, 'Данная функция находится в разработке, следите за новостями, дабы узнать когда команда заработает!\n\nThis feature is under development, follow the news in order to find out when the team will work!')

            elif message.text in ['🦖 БИО', '🦖 BIO']:

                bot.send_message(user.id, 'Данная функция находится в разработке, следите за новостями, дабы узнать когда команда заработает!\n\nThis feature is under development, follow the news in order to find out when the team will work!')

            elif message.text in [ '👁‍🗨 Динозавры в таверне', '👁‍🗨 Dinosaurs in the Tavern']:

                bot.send_message(user.id, 'Данная функция находится в разработке, следите за новостями, дабы узнать когда команда заработает!\n\nThis feature is under development, follow the news in order to find out when the team will work!')

            elif message.text in [ '♻ Rarity Change', '♻ Изменение редкости']:

                commands.rarity_change(bot, message, user, bd_user)

            elif message.text in [ '🥏 Дрессировка', '🥏 Training']:

                bot.send_message(user.id, 'Данная функция находится в разработке, следите за новостями, дабы узнать когда команда заработает!\n\nThis feature is under development, follow the news in order to find out when the team will work!')

            elif message.text in [ "💡 Исследования", "💡 Research"]:

                bot.send_message(user.id, 'Данная функция находится в разработке, следите за новостями, дабы узнать когда команда заработает!\n\nThis feature is under development, follow the news in order to find out when the team will work!')

    if bd_user != None:
        # последняя активность
        users.update_one( {"userid": bd_user['userid']}, {"$set": {'last_m': int(time.time()) }} )


@bot.callback_query_handler(func = lambda call: True)
def answer(call):
    user = call.from_user
    bd_user = users.find_one({"userid": user.id})

    if call.data == 'start':

        call_data.start(bot, bd_user, call, user)

    elif call.data == 'checking_the_user_in_the_channel':

        call_data.checking_the_user_in_the_channel(bot, bd_user, call, user)

    elif call.data in ['egg_answer_1', 'egg_answer_2', 'egg_answer_3']:

        call_data.egg_answer(bot, bd_user, call, user)

    elif call.data[:13] in ['90min_journey', '60min_journey', '30min_journey', '10min_journey', '12min_journey']:

        call_data.journey(bot, bd_user, call, user)

    elif call.data[:10] in ['1_con_game', '2_con_game', '3_con_game', '1_sna_game', '2_sna_game', '3_sna_game', '1_pin_game', '2_pin_game', '3_pin_game', '1_bal_game', '2_bal_game', '3_bal_game', '1_puz_game', '2_puz_game', '3_puz_game', '1_che_game', '2_che_game', '3_che_game', '1_jen_game', '2_jen_game', '3_jen_game', '1_ddd_game', '2_ddd_game', '3_ddd_game']:

        call_data.game(bot, bd_user, call, user)

    elif call.data in ['dead_answer1', 'dead_answer2', 'dead_answer3', 'dead_answer4']:

        call_data.dead_answer(bot, bd_user, call, user)

    elif call.data == 'dead_restart':

        call_data.dead_restart(bot, bd_user, call, user)

    elif call.data[:5] == 'item_':

        call_data.item_use(bot, bd_user, call, user)

    elif call.data[:12] == 'remove_item_':

        call_data.remove_item(bot, bd_user, call, user)

    elif call.data[:7] == 'remove_':

        call_data.remove(bot, bd_user, call, user)

    elif call.data == "cancel_remove":

        bot.delete_message(user.id, call.message.message_id)

    elif call.data[:9] == 'exchange_':

        call_data.exchange(bot, bd_user, call, user)

    elif call.data[:11] == 'market_buy_':

        call_data.market_buy(bot, bd_user, call, user)

    elif call.data[:7] == 'market_':

        call_data.market_inf(bot, bd_user, call, user)

    elif call.data[:9] == 'iteminfo_':

        call_data.iteminfo(bot, bd_user, call, user)

    elif call.data == 'inventory':

        functions.user_inventory(bot, user, call.message)

    elif call.data == 'requests':

        functions.user_requests(bot, user, call.message)

    elif call.data == 'send_request':

        call_data.send_request(bot, bd_user, call, user)

    elif call.data[:18] == 'open_dino_profile_':

        did = call.data[18:]
        if did in bd_user['dinos'].keys():
            bd_dino = bd_user['dinos'][did]
            functions.p_profile(bot, call.message, bd_dino, user, bd_user, did)

    elif call.data[:8] == 'ns_craft':

        call_data.ns_craft(bot, bd_user, call, user)

    elif call.data[:13] == 'change_rarity':

        call_data.change_rarity_call_data(bot, bd_user, call, user)

    elif call.data.split()[0] == 'dungeon.settings':

        call_data.dungeon_settings(bot, bd_user, call, user)

    elif call.data.split()[0] == 'dungeon.to_lobby':

        call_data.dungeon_to_lobby(bot, bd_user, call, user)

    elif call.data.split()[0] == 'dungeon.settings_lang':

        call_data.dungeon_settings_lang(bot, bd_user, call, user)

    elif call.data.split()[0] == 'dungeon.leave':

        call_data.dungeon_leave(bot, bd_user, call, user)

    elif call.data.split()[0] == 'dungeon.leave_True':

        call_data.dungeon_leave_True(bot, bd_user, call, user)

    elif call.data.split()[0] == 'dungeon.leave_False':

        call_data.dungeon_leave_False(bot, bd_user, call, user)

    elif call.data.split()[0] == 'dungeon.remove':

        call_data.dungeon_remove(bot, bd_user, call, user)

    elif call.data.split()[0] == 'dungeon.remove_True':

        call_data.dungeon_remove_True(bot, bd_user, call, user)

    elif call.data.split()[0] == 'dungeon.remove_False':

        call_data.dungeon_remove_False(bot, bd_user, call, user)

    else:
        print(call.data, 'call.data')

if bot.get_me().first_name == 'DinoGochi' or False:
    main_checks.start() # активация всех проверок и игрового процесса
    thr_notif.start() # активация уведомлений
    min10_thr.start() # десяти-минутный чек

print(f'Бот {bot.get_me().first_name} запущен!')
bot.infinity_polling()
