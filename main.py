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

bot = telebot.TeleBot(config.TOKEN)

client = pymongo.MongoClient(config.CLUSTER_TOKEN)
users = client.bot.users
referal_system = client.bot.referal_system
market = client.bot.market

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


# @bot.message_handler(commands=['nw'])
# def command_n(message):
#     user = message.from_user
#     if user.id in [5279769615, 1191252229]:
#
#         def work(members, n):
#             for bd_user in members:
#                 nw_inv = bd_user['inventory'].copy()
#
#                 for i in bd_user['inventory']:
#                     if 'abilities' in i.keys():
#                         dt_it = items_f['items'][i['item_id']]
#                         if dt_it['abilities'] != i['abilities']:
#                             nw_inv.remove(i)
#
#                 if nw_inv != bd_user['inventory']:
#                     users.update_one( {"userid": bd_user['userid']}, {"$set": {'inventory': nw_inv }} )
#
#             print(f'Программа обновления №{n} завершила работу.')
#
#         non_members = users.find({ })
#         chunks_users = list(functions.chunks( list(non_members), 10 ))
#
#         n = 0
#         for members in chunks_users:
#             n += 1
#             main = threading.Thread(target = work, daemon=True, kwargs = { 'members': members, 'n': n}).start()

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

@bot.message_handler(commands=['add_item'])
def command(message):
    user = message.from_user
    if user.id in [5279769615, 1191252229]:
        msg_args = message.text.split()
        bd = users.find_one({"userid": int(msg_args[3])})

        tr = functions.add_item_to_user(bd, msg_args[1], int(msg_args[2]))
        bot.send_message(user.id, str(msg_args))

@bot.message_handler(commands=['dns'])
def command(message):
    user = message.from_user

    for i in users.find({}):

        for ii in i['activ_items'].keys():
            d = i['activ_items'][ii].keys()
            if '1' in d:
                print(i['userid'], 'l-34')
            if '2' in d:
                print(i['userid'], 'l-3934')

    print('all')


# @bot.message_handler(commands=['des_qr'])
# def command(message):
#     user = message.from_user
#     text = functions.des_qr('i23.u12')
#     bot.send_message(user.id, str(text))

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

        bot.reply_to(message, text, parse_mode = 'Markdown')

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

    if users.find_one({"userid": user.id}) != None:
        bd_user = users.find_one({"userid": user.id})

        # последняя активность
        users.update_one( {"userid": bd_user['userid']}, {"$set": {'last_m': int(time.time()) }} )

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

                commands.start_game(bot, message, user)

            if message.text in ["🧩 Проект: Возрождение", '🧩 Project: Rebirth']:

                commands.project_reb(bot, message, user)

            if message.text in ['🦖 Динозавр', '🦖 Dinosaur']:

                commands.dino_prof(bot, message, user)

            if message.text in ['🔧 Настройки', '🔧 Settings']:
                bd_user = users.find_one({"userid": user.id})

                if bd_user != None:

                    if bd_user['language_code'] == 'ru':
                        text = '🔧 Меню настроек активировано'
                    else:
                        text = '🔧 The settings menu is activated'


                    bot.send_message(message.chat.id, text, reply_markup = functions.markup(bot, 'settings', user))

            if message.text in ['↪ Назад', '↪ Back']:
                bd_user = users.find_one({"userid": user.id})
                if bd_user != None:

                    if bd_user['language_code'] == 'ru':
                        text = '↪ Возврат в главное меню'
                    else:
                        text = '↪ Return to the main menu'

                    bot.send_message(message.chat.id, text, reply_markup = functions.markup(bot, 1, user))

            if message.text in ['👥 Друзья', '👥 Friends']:
                bd_user = users.find_one({"userid": user.id})
                if bd_user != None:

                    if bd_user['language_code'] == 'ru':
                        text = '👥 | Перенаправление в меню друзей!'
                    else:
                        text = '👥 | Redirecting to the friends menu!'

                    bot.send_message(message.chat.id, text, reply_markup = functions.markup(bot, "friends-menu", user))

            if message.text in ['❗ FAQ']:

                commands.faq(bot, message, user)

            if message.text in ['❗ Notifications', '❗ Уведомления']:

                commands.not_set(bot, message, user)

            if message.text in ["👅 Язык", "👅 Language"]:

                commands.lang_set(bot, message, user)

            if message.text in ['⁉ Видимость FAQ', '⁉ Visibility FAQ']:
                bd_user = users.find_one({"userid": user.id})
                if bd_user != None:

                    if bd_user['language_code'] == 'ru':
                        ans = ['✅ Включить', '❌ Выключить', '↪ Назад']
                        text = '❗ Взаимодействие с настройкой видимости FAQ, выберите видимость >'
                    else:
                        ans = ['✅ Enable', '❌ Disable', '↪ Back']
                        text = '❗ Interaction with the FAQ visibility setting, select visibility >'

                    rmk = types.ReplyKeyboardMarkup(resize_keyboard = True)
                    rmk.add(ans[0], ans[1])
                    rmk.add(ans[2])

                    def ret(message, ans, bd_user):

                        if message.text not in ans or message.text == ans[2]:
                            res = None
                        else:
                            res = message.text

                        if res == None:
                            bot.send_message(message.chat.id, f'❌', reply_markup = functions.markup(bot, 'settings', user))
                            return

                        if res in ['✅ Enable', '✅ Включить']:

                            bd_user['settings']['vis.faq'] = True
                            users.update_one( {"userid": bd_user['userid']}, {"$set": {'settings': bd_user['settings'] }} )

                            if bd_user['language_code'] == 'ru':
                                text = '🔧 FAQ был активирован!'
                            else:
                                text = '🔧 The FAQ has been activated!'

                            bot.send_message(message.chat.id, text, reply_markup = functions.markup(bot, "settings", user))

                        if res in ['❌ Disable', '❌ Выключить']:

                            bd_user['settings']['vis.faq'] = False
                            users.update_one( {"userid": bd_user['userid']}, {"$set": {'settings': bd_user['settings'] }} )

                            if bd_user['language_code'] == 'ru':
                                text = '🔧 FAQ был отключен!'
                            else:
                                text = '🔧 The FAQ has been disabled!'

                            bot.send_message(message.chat.id, text, reply_markup = functions.markup(bot, "settings", user))

                        else:
                            return

                    msg = bot.send_message(message.chat.id, text, reply_markup = rmk)
                    bot.register_next_step_handler(msg, ret, ans, bd_user)

            if message.text in ["➕ Добавить", "➕ Add"]:
                bd_user = users.find_one({"userid": user.id})
                if bd_user != None:

                    if bd_user['language_code'] == 'ru':
                        ans = ['↪ Назад']
                        text = '➡ | Перешлите мне любое сообщение от человека (в разделе конфиденциальность > пересылка сообщений - должно быть разрешение), с которым вы хотите стать друзьями или отправте мне его id (можно узнать в своём профиле у бота).\nВажно! Ваш друг должен быть зарегистрирован в боте!'
                    else:
                        ans = ['↪ Back']
                        text = '➡ | Forward me any message from the person (in the privacy section > message forwarding - there must be permission) with whom you want to become friends or send me his id (you can find out in your bot profile).\nImportant! Your friend must be registered in the bot!'

                    rmk = types.ReplyKeyboardMarkup(resize_keyboard = True)
                    rmk.add(ans[0])

                    def ret(message, ans, bd_user):
                        res = message

                        if message.text in ans:
                            bot.send_message(message.chat.id, f'❌', reply_markup = functions.markup(bot, 'friends-menu', user))
                            return

                        try:
                            fr_id = int(res.text)
                        except:

                            if res.text == ans[0] or res.forward_from == None:
                                bot.send_message(message.chat.id, f'❌ user forward not found', reply_markup = functions.markup(bot, 'friends-menu', user))
                                fr_id = None

                            else:
                                fr_id = res.forward_from.id


                        two_user = users.find_one({"userid": fr_id})

                        if two_user == None:
                            bot.send_message(message.chat.id, f'❌ user not found in base', reply_markup = functions.markup(bot, 'friends-menu', user))
                            return

                        if two_user == bd_user:
                            bot.send_message(message.chat.id, f'❌ user == friend', reply_markup = functions.markup(bot, 'friends-menu', user))

                        else:

                            if 'friends_list' not in bd_user['friends']:
                                bd_user['friends']['friends_list'] = []
                                bd_user['friends']['requests'] = []
                                users.update_one( {"userid": bd_user['userid']}, {"$set": {'friends': bd_user['friends'] }} )

                            if 'friends_list' not in two_user['friends']:
                                two_user['friends']['friends_list'] = []
                                two_user['friends']['requests'] = []
                                users.update_one( {"userid": two_user['userid']}, {"$set": {'friends': two_user['friends'] }} )

                            if bd_user['userid'] not in two_user['friends']['requests'] and bd_user['userid'] not in two_user['friends']['friends_list'] and two_user['userid'] not in bd_user['friends']['requests']:

                                two_user['friends']['requests'].append(bd_user['userid'])
                                users.update_one( {"userid": two_user['userid']}, {"$set": {'friends': two_user['friends'] }} )

                                bot.send_message(message.chat.id, f'✔', reply_markup = functions.markup(bot, 'friends-menu', user))
                                functions.notifications_manager(bot, 'friend_request', two_user)

                            else:

                                if bd_user['language_code'] == 'ru':
                                    text = f"📜 | Данный пользователь уже в друзьях / получил запрос от вас!"

                                else:
                                    text = f"📜 | This user is already a friend / has received a request from you!"

                                bot.send_message(message.chat.id, text, reply_markup = functions.markup(bot, 'friends-menu', user))

                    msg = bot.send_message(message.chat.id, text, reply_markup = rmk)
                    bot.register_next_step_handler(msg, ret, ans, bd_user)

            if message.text in ["📜 Список", "📜 List"]:
                bd_user = users.find_one({"userid": user.id})
                if bd_user != None:

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

                            bot.send_message(message.chat.id, text, reply_markup = functions.markup(bot, 'friends-menu', user))

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

                                    bot.send_message(message.chat.id, text, reply_markup = functions.markup(bot, 'friends-menu', user))

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
                                            text = functions.member_profile(bot, fr_id, bd_user['language_code'])

                                            mms = bot.send_message(message.chat.id, text, parse_mode = 'Markdown')

                                    work_pr(message, friends_id, page, friends_chunks, friends_id_d, mms = mms)

                            if mms == None:
                                msg = bot.send_message(message.chat.id, text, reply_markup = rmk)
                            else:
                                msg = mms
                            bot.register_next_step_handler(msg, ret, bd_user, page, friends_chunks, friends_id, friends_id_d)

                    work_pr(message, friends_id, page, friends_chunks, friends_id_d)

            if message.text in ["💌 Запросы", "💌 Inquiries"]:

                functions.user_requests(bot, user, message)

            if message.text in ['➖ Удалить', '➖ Delete']:
                bd_user = users.find_one({"userid": user.id})
                if bd_user != None:

                    friends_id = bd_user['friends']['friends_list']
                    page = 1
                    friends_name = []
                    id_names = {}

                    for i in friends_id:
                        try:
                            fr_name = bot.get_chat(int(i)).first_name
                            friends_name.append(fr_name)
                            id_names[bot.get_chat(int(i)).first_name] = i
                        except:
                            pass

                    friends_chunks = list(functions.chunks(list(functions.chunks(friends_name, 2)), 3))

                    if friends_chunks == []:

                        if bd_user['language_code'] == 'ru':
                            text = "👥 | Список пуст!"
                        else:
                            text = "👥 | The list is empty!"

                        bot.send_message(message.chat.id, text, reply_markup = functions.markup(bot, 'friends-menu', user))
                        return

                    else:
                        if bd_user['language_code'] == 'ru':
                            text = "➖ | Выберите пользователя для удаления из друзей > "
                        else:
                            text = "➖ | Select the user to remove from friends >"
                        bot.send_message(message.chat.id, text, reply_markup = functions.markup(bot, 'friends-menu', user))

                    def work_pr(message, friends_id, page):

                        if bd_user['language_code'] == 'ru':
                            text = "💌 | Обновление..."
                        else:
                            text = "💌 | Update..."

                        rmk = types.ReplyKeyboardMarkup(resize_keyboard = True, row_width = 3)

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

                                bot.send_message(message.chat.id, text, reply_markup = functions.markup(bot, 'friends-menu', user))
                                return None
                            else:
                                if res == '◀':
                                    if page - 1 == 0:
                                        page = 1
                                    else:
                                        page -= 1

                                elif res == '▶':
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

                                    try:
                                        bd_user['friends']['friends_list'].remove(uid)
                                        users.update_one( {"userid": bd_user['userid']}, {"$pull": {'friends.friends_list': uid }} )

                                    except:
                                        pass

                                    try:
                                        users.update_one( {"userid": uid}, {"$pull": {'friends.friends_list': bd_user['userid'] }} )
                                    except:
                                        pass

                                    if bd_user['friends']['friends_list'] == []:
                                        bot.send_message(message.chat.id, text, reply_markup = functions.markup(bot, 'friends-menu', user))
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

                    bot.send_message(message.chat.id, text, reply_markup = functions.markup(bot, "profile", user))


            if message.text in ['🎢 Рейтинг', '🎢 Rating']:
                if bd_user != None:

                    mr_l = functions.rayt_update('check')[0]#list(sorted(list(users.find({})), key=lambda x: x['coins'], reverse=True))
                    lv_l = functions.rayt_update('check')[1]#list(sorted(list(users.find({})), key=lambda x: (x['lvl'][0] - 1) * (5 * x['lvl'][0] * x['lvl'][0] + 50 * x['lvl'][0] + 100) +  x['lvl'][1], reverse=True))

                    du_mc, du_lv = [{}, {}, {}, {}, {}], [{}, {}, {}, {}, {}]


                    i = -1
                    us_i_l = []
                    while du_mc[0] == {} or du_mc[1] == {} or du_mc[2] == {} or du_mc[3] == {} or du_mc[4] == {}:
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

                        if du_mc[3] == {} and mr_l[i]['userid'] not in us_i_l:
                            try:
                                m = bot.get_chat(mr_l[i]['userid'])
                                du_mc[3] = {'ui': mr_l[i]['userid'], 'coins': mr_l[i]['coins'], 'mn': m.first_name}

                                us_i_l.append(mr_l[i]['userid'])
                            except:
                                pass

                        if du_mc[4] == {} and mr_l[i]['userid'] not in us_i_l:
                            try:
                                m = bot.get_chat(mr_l[i]['userid'])
                                du_mc[4] = {'ui': mr_l[i]['userid'], 'coins': mr_l[i]['coins'], 'mn': m.first_name}

                                us_i_l.append(mr_l[i]['userid'])
                            except:
                                pass

                    i = -1
                    us_i_m = []
                    while du_lv[0] == {} or du_lv[1] == {} or du_lv[2] == {} or du_lv[3] == {} or du_lv[4] == {}:
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

                        if du_lv[3] == {} and lv_l[i]['userid'] not in us_i_m:
                            try:
                                m = bot.get_chat(lv_l[i]['userid'])
                                x = lv_l[i]
                                du_lv[3] = {'ui': lv_l[i]['userid'], 'lvl': lv_l[i]['lvl'][0], 'exp': (x['lvl'][0] - 1) * (5 * x['lvl'][0] * x['lvl'][0] + 50 * x['lvl'][0] + 100) +  x['lvl'][1], 'mn': m.first_name }

                                us_i_m.append(lv_l[i]['userid'])
                            except:
                                pass

                        if du_lv[4] == {} and lv_l[i]['userid'] not in us_i_m:
                            try:
                                m = bot.get_chat(lv_l[i]['userid'])
                                x = lv_l[i]
                                du_lv[4] = {'ui': lv_l[i]['userid'], 'lvl': lv_l[i]['lvl'][0], 'exp': (x['lvl'][0] - 1) * (5 * x['lvl'][0] * x['lvl'][0] + 50 * x['lvl'][0] + 100) +  x['lvl'][1], 'mn': m.first_name }

                                us_i_m.append(lv_l[i]['userid'])
                            except:
                                pass

                    lv_ar_id = []
                    for i in lv_l:
                        lv_ar_id.append(i['userid'])

                    mr_ar_id = []
                    for i in mr_l:
                        mr_ar_id.append(i['userid'])


                    if bd_user['language_code'] == 'ru':
                        if bd_user['userid'] in lv_ar_id:
                            ind = lv_ar_id.index(bd_user['userid'])+1
                        else:
                            ind = '-'

                        text =  f'*┌* 🎢 Рейтинг по уровню:\n'
                        text += f"*├* Ваше место в рейтинге: #{ind}\n\n"

                        n = 0
                        for i in du_lv:
                            n += 1
                            if i == {}:
                                pass
                            else:
                                if n != 5:
                                    text += f"*├* #{n} *{i['mn']}*:\n      *└* Ур. {i['lvl']} (Всего опыта {i['exp']})\n"
                                else:
                                    text += f"*└* #{n} *{i['mn']}*:\n      *└* Ур. {i['lvl']} (Всего опыта {i['exp']})\n"

                        if bd_user['userid'] in mr_ar_id:
                            ind = mr_ar_id.index(bd_user['userid'])+1
                        else:
                            ind = '-'

                        text += f'\n\n*┌* 🎢 Рейтинг по монетам:\n'
                        text += f"*├* Ваше место в рейтинге: #{ind}\n\n"

                        n = 0
                        for i in du_mc:
                            n += 1
                            if i == {}:
                                pass
                            else:
                                if n != 5:
                                    text += f"*├* #{n} *{i['mn']}*:\n      *└* Монеты {i['coins']}\n"
                                else:
                                    text += f"*└* #{n} *{i['mn']}*:\n      *└* Монеты {i['coins']}\n"
                    else:
                        if bd_user['userid'] in lv_ar_id:
                            ind = lv_ar_id.index(bd_user['userid'])+1
                        else:
                            ind = '-'

                        text =  f'*┌* 🎢 Rating by level:\n'
                        text += f"*├* Your place in the ranking: #{ind}\n\n"

                        n = 0
                        for i in du_lv:
                            n += 1
                            if i == {}:
                                pass
                            else:
                                if n != 5:
                                    text += f"*├* #{n} *{i['mn']}*:\n      *└* lvl {i['lvl']} (Total experience {i['exp']})\n"
                                else:
                                    text += f"*└* #{n} *{i['mn']}*:\n      *└* lvl {i['lvl']} (Total experience {i['exp']})\n"

                        if bd_user['userid'] in mr_ar_id:
                            ind = mr_ar_id.index(bd_user['userid'])+1
                        else:
                            ind = '-'

                        text += f'\n\n*┌* 🎢 Coin Rating:\n'
                        text += f"*├* Your place in the ranking: #{ind}\n\n"

                        n = 0
                        for i in du_mc:
                            n += 1
                            if i == {}:
                                pass
                            else:
                                if n != 5:
                                    text += f"*├* #{n} *{i['mn']}*:\n      *└* Coins {i['coins']}\n"
                                else:
                                    text += f"*└* #{n} *{i['mn']}*:\n      *└* Coins {i['coins']}\n"

                    bot.send_message(message.chat.id, text, parse_mode = "Markdown")

            if message.text in ['🎮 Инвентарь', '🎮 Inventory']:

                functions.user_inventory(bot, user, message)

            if message.text in ['📜 Информация', '📜 Information']:
                bd_user = users.find_one({"userid": user.id})
                if bd_user != None:
                    text = functions.member_profile(bot, user.id, lang = bd_user['language_code'])
                    bot.send_message(message.chat.id, text, parse_mode = 'Markdown')

            if message.text in ['🕹 Действия', '🕹 Actions']:
                bd_user = users.find_one({"userid": user.id})
                if bd_user != None:

                    if bd_user['language_code'] == 'ru':
                        text = '🕹 Панель действий открыта!'
                    else:
                        text = '🕹 The action panel is open!'

                    bot.send_message(message.chat.id, text, reply_markup = functions.markup(bot, "actions", user))

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
                            if bd_user['dinos'][ str(bd_user['settings']['dino_id']) ]['status'] == 'incubation':
                                text = f"Вы выбрали динозавра 🥚"
                            else:
                                text = f"Вы выбрали динозавра {bd_user['dinos'][ str(bd_user['settings']['dino_id']) ]['name']}"
                        else:
                            if bd_user['dinos'][ str(bd_user['settings']['dino_id']) ]['status'] == 'incubation':
                                text = f"You have chosen 🥚"
                            else:
                                text = f"You have chosen a dinosaur {bd_user['dinos'][ str(bd_user['settings']['dino_id']) ]['name']}"

                        bot.send_message(message.chat.id, text , reply_markup = functions.markup(bot, 'actions', user))

            bd_user = users.find_one({"userid": user.id})
            tr_c = False
            if bd_user != None and len(list(bd_user['dinos'])) > 0:
                if ( len(list(bd_user['dinos'])) == 1 and bd_user['lvl'][0] > 1) :
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

                    bot.send_message(message.chat.id, text, reply_markup = functions.markup(bot, 'actions', user))

                if message.text in ['💬 Переименовать', '💬 Rename']:
                    bd_user = users.find_one({"userid": user.id})
                    if bd_user != None:
                        n_dp, dp_a = functions.dino_pre_answer(bot, message)

                        if bd_user['dinos'][ bd_user['settings']['dino_id'] ]['status'] == 'dino':

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
                                        bot.send_message(message.chat.id, f'❌', reply_markup = functions.markup(bot, 'settings', user))
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
                                                bot.send_message(message.chat.id, f'❌', reply_markup = functions.markup(bot, 'settings', user))
                                                return
                                            else:
                                                res = message.text

                                            if res in ['✅ Confirm', '✅ Подтверждаю']:

                                                bd_user['dinos'][str(dino_user_id)]['name'] = dino_name
                                                users.update_one( {"userid": bd_user['userid']}, {"$set": {f'dinos.{dino_user_id}': bd_user['dinos'][str(dino_user_id)] }} )

                                                bot.send_message(message.chat.id, f'✅', reply_markup = functions.markup(bot, 'settings', user))

                                        msg = bot.send_message(message.chat.id, text, reply_markup = rmk)
                                        bot.register_next_step_handler(msg, ret2, ans2, bd_user)

                                msg = bot.send_message(message.chat.id, text, reply_markup = rmk)
                                bot.register_next_step_handler(msg, ret, ans, bd_user)

                            if n_dp == 1:
                                bot.send_message(message.chat.id, f'❌', reply_markup = functions.markup(bot, 'settings', user))
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

                                    bot.send_message(message.chat.id, text, reply_markup = functions.markup(bot, "actions", user))

                                else:
                                    def dl_sleep(bd_user, message):
                                        d_id = bd_user['settings']['dino_id']
                                        bd_user['dinos'][ d_id ]['activ_status'] = 'sleep'
                                        bd_user['dinos'][ d_id ]['sleep_start'] = int(time.time())
                                        bd_user['dinos'][ d_id ]['sleep_type'] = 'long'
                                        users.update_one( {"userid": bd_user['userid']}, {"$set": {f'dinos.{d_id}': bd_user['dinos'][d_id] }} )

                                        if bd_user['language_code'] == 'ru':
                                            text = '🌙 Вы уложили динозавра спать!'
                                        else:
                                            text = "🌙 You put the dinosaur to sleep!"

                                        bot.send_message(message.chat.id, text , reply_markup = functions.markup(bot, 'actions', user))

                                    if functions.acc_check(bot, bd_user, '16', bd_user['settings']['dino_id'], True) == False:
                                        dl_sleep(bd_user, message)

                                    else:

                                        if bd_user['language_code'] == 'ru':
                                            ans = ['🛌 Длинный сон', '🛌 Короткий сон', '↪ Назад']
                                            text = '🌙 | Выберите вид сна для динозавра >'
                                        else:
                                            ans = ['🛌 Long Sleep', '🛌 Short Sleep', '↪ Back']
                                            text = '🌙 | Choose the type of sleep for the dinosaur >'

                                        rmk = types.ReplyKeyboardMarkup(resize_keyboard = True)
                                        rmk.add(ans[0], ans[1])
                                        rmk.add(ans[2])

                                        def ret(message, ans, bd_user):

                                            if message.text not in ans or message.text == ans[2]:
                                                res = None
                                            else:
                                                res = message.text

                                            if res == None:
                                                bot.send_message(message.chat.id, f'❌', reply_markup = functions.markup(bot, 'actions', user))
                                                return

                                            if res in ['🛌 Длинный сон', '🛌 Long Sleep']:

                                                dl_sleep(bd_user, message)

                                            if res in ['🛌 Короткий сон', '🛌 Short Sleep']:

                                                def ret2(message, ans, bd_user):

                                                    if message.text == ans[0]:
                                                        number = None
                                                    else:

                                                        try:
                                                            number = int(message.text)
                                                        except:
                                                            number = None


                                                    if number == None:
                                                        bot.send_message(message.chat.id, f'❌', reply_markup = functions.markup(bot, 'actions', user))
                                                        return

                                                    if number <= 5 or number > 480:

                                                        if bd_user['language_code'] == 'ru':
                                                            text = '❌ | Требовалось указать время в минутах больше 5-ти минут и меньше 8-ми часов (480)!'
                                                        else:
                                                            text = '❌ | It was required to specify the time in minutes more than 5 minutes and less than 8 hours (480)!'

                                                        bot.send_message(message.chat.id, text, reply_markup = functions.markup(bot, 'actions', user))

                                                    else:
                                                        d_id = bd_user['settings']['dino_id']
                                                        bd_user['dinos'][ d_id ]['activ_status'] = 'sleep'
                                                        bd_user['dinos'][ d_id ]['sleep_time'] = int(time.time()) + number * 60
                                                        bd_user['dinos'][ d_id ]['sleep_type'] = 'short'
                                                        users.update_one( {"userid": bd_user['userid']}, {"$set": {f'dinos.{d_id}': bd_user['dinos'][d_id] }} )

                                                        if bd_user['language_code'] == 'ru':
                                                            text = '🌙 Вы уложили динозавра спать!'
                                                        else:
                                                            text = "🌙 You put the dinosaur to sleep!"

                                                        bot.send_message(message.chat.id, text , reply_markup = functions.markup(bot, 'actions', user))



                                                if bd_user['language_code'] == 'ru':
                                                    ans = ['↪ Назад']
                                                    text = '🌙 | Укажите время быстрого сна (сон идёт в 2 раза быстрее длинного) в минутах > '
                                                else:
                                                    ans = ['↪ Back']
                                                    text = '🌙 | Specify the REM sleep time (sleep is 2 times faster than long sleep) in minutes >'

                                                rmk = types.ReplyKeyboardMarkup(resize_keyboard = True)
                                                rmk.add(ans[0])

                                                msg = bot.send_message(message.chat.id, text, reply_markup = rmk)
                                                bot.register_next_step_handler(msg, ret2, ans, bd_user)


                                        msg = bot.send_message(message.chat.id, text, reply_markup = rmk)
                                        bot.register_next_step_handler(msg, ret, ans, bd_user)



                        else:

                            if bd_user['language_code'] == 'ru':
                                text = f"❗ | Ваш динозавр уже чем то занят, проверьте профиль!"

                            else:
                                text = f"❗ | Your dinosaur is already busy with something, check the profile!"

                            bot.send_message(message.chat.id, text, reply_markup = functions.inline_markup(bot, f'open_dino_profile', message.chat.id, ['Открыть профиль', 'Open a profile'], str(bd_user['settings']['dino_id']) ))


                if message.text in ['🌙 Пробудить', '🌙 Awaken']:
                    bd_user = users.find_one({"userid": user.id})
                    if bd_user != None:
                        d_id = str(bd_user['settings']['dino_id'])
                        dino = bd_user['dinos'][ str(d_id) ]

                        if dino['activ_status'] == 'sleep' and dino != None:
                            r_n = random.randint(0, 20)
                            bd_user['dinos'][ d_id ]['activ_status'] = 'pass_active'

                            if 'sleep_type' in bd_user['dinos'][ d_id ] and bd_user['dinos'][ d_id ]['sleep_type'] == 'short':

                                del bd_user['dinos'][ d_id ]['sleep_time']

                                if bd_user['language_code'] == 'ru':
                                    text = f'🌙 Ваш динозавр пробудился.'
                                else:
                                    text = f"🌙 Your dinosaur has awakened."

                                bot.send_message(message.chat.id, text , reply_markup = functions.markup(bot, 'actions', user))

                                try:
                                    del bd_user['dinos'][ d_id ]['sleep_type']
                                except:
                                    pass

                                try:
                                    del bd_user['dinos'][ d_id ]['sleep_start']
                                except:
                                    pass

                                users.update_one( {"userid": bd_user['userid']}, {"$set": {f'dinos.{d_id}': bd_user['dinos'][d_id] }} )

                            elif 'sleep_type' not in bd_user['dinos'][ d_id ] or bd_user['dinos'][ d_id ]['sleep_type'] == 'long':

                                if 'sleep_start' in bd_user['dinos'][ d_id ].keys() and int(time.time()) - bd_user['dinos'][ d_id ]['sleep_start'] >= 8 * 3600:

                                    if bd_user['language_code'] == 'ru':
                                        text = f'🌙 Ваш динозавр пробудился.'
                                    else:
                                        text = f"🌙 Your dinosaur has awakened."

                                    bot.send_message(message.chat.id, text , reply_markup = functions.markup(bot, 'actions', user))

                                else:

                                    bd_user['dinos'][ d_id ]['stats']['mood'] -= r_n

                                    if bd_user['dinos'][ d_id ]['stats']['mood'] < 0:
                                        bd_user['dinos'][ d_id ]['stats']['mood'] = 0

                                    if bd_user['language_code'] == 'ru':
                                        text = f'🌙 Ваш динозавр пробудился. Он сильно не доволен что вы его разбудили!\nДинозавр потерял {r_n}% настроения.'
                                    else:
                                        text = f"🌙 Your dinosaur has awakened. He is very unhappy that you woke him up!\nDinosaur lost {r_n}% of mood."

                                    bot.send_message(message.chat.id, text , reply_markup = functions.markup(bot, 'actions', user))

                                try:
                                    del bd_user['dinos'][ d_id ]['sleep_type']
                                except:
                                    pass

                                try:
                                    del bd_user['dinos'][ d_id ]['sleep_start']
                                except:
                                    pass

                                users.update_one( {"userid": bd_user['userid']}, {"$set": {f'dinos.{d_id}': bd_user['dinos'][d_id] }} )

                        else:
                            bot.send_message(message.chat.id, f'❌', reply_markup = functions.markup(bot, 'actions', user))
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

                                item_4 = types.InlineKeyboardButton( text = '120 мин.', callback_data = f"12min_journey_{str(bd_user['settings']['dino_id'])}")

                            else:
                                text = "🌳 How long to send a dinosaur on a journey?"

                                item_0 = types.InlineKeyboardButton( text = '10 min.', callback_data = f"10min_journey_{str(bd_user['settings']['dino_id'])}")

                                item_1 = types.InlineKeyboardButton( text = '30 min.', callback_data = f"30min_journey_{str(bd_user['settings']['dino_id'])}")

                                item_2 = types.InlineKeyboardButton( text = '60 min.', callback_data = f"60min_journey_{str(bd_user['settings']['dino_id'])}")

                                item_3 = types.InlineKeyboardButton( text = '90 min.', callback_data = f"90min_journey_{str(bd_user['settings']['dino_id'])}")

                                item_4 = types.InlineKeyboardButton( text = '120 min.', callback_data = f"12min_journey_{str(bd_user['settings']['dino_id'])}")

                            markup_inline.add(item_0, item_1, item_2, item_3, item_4)

                            bot.send_message(message.chat.id, text, reply_markup = markup_inline)

                        else:

                            if bd_user['language_code'] == 'ru':
                                text = f"❗ | Ваш динозавр уже чем то занят, проверьте профиль!"

                            else:
                                text = f"❗ | Your dinosaur is already busy with something, check the profile!"

                            bot.send_message(message.chat.id, text, reply_markup = functions.inline_markup(bot, f'open_dino_profile', message.chat.id, ['Открыть профиль', 'Open a profile'], str(bd_user['settings']['dino_id']) ))


                if message.text in ['🎑 Вернуть', '🎑 Call']:
                    bd_user = users.find_one({"userid": user.id})
                    if bd_user != None:
                        dino = bd_user['dinos'][ str(bd_user['settings']['dino_id']) ]

                        if dino['activ_status'] == 'journey' and dino != None:
                            if random.randint(1,2) == 1:

                                if bd_user['language_code'] == 'ru':
                                    text = f'🦖 | Вы вернули динозавра из путешествия!\nВот что произошло в его путешествии:\n'

                                    if bd_user['dinos'][ bd_user['settings']['dino_id'] ]['journey_log'] == []:
                                        text += 'Ничего не произошло!'
                                    else:
                                        n = 1
                                        for el in bd_user['dinos'][ bd_user['settings']['dino_id'] ]['journey_log']:
                                            text += f'<b>{n}.</b> {el}\n\n'
                                            n += 1
                                else:
                                    text = f"🦖 | Turned the dinosaur out of the journey!\nHere's what happened on his journey:\n"

                                    if bd_user['dinos'][ bd_user['settings']['dino_id'] ]['journey_log'] == []:
                                        text += 'Nothing happened!'
                                    else:
                                        n = 1
                                        for el in bd_user['dinos'][ bd_user['settings']['dino_id'] ]['journey_log']:
                                            text += f'<b>{n}.</b> {el}\n\n'
                                            n += 1


                                bd_user['dinos'][ bd_user['settings']['dino_id'] ]['activ_status'] = 'pass_active'
                                del bd_user['dinos'][ bd_user['settings']['dino_id'] ]['journey_time']
                                del bd_user['dinos'][ bd_user['settings']['dino_id'] ]['journey_log']

                                users.update_one( {"userid": bd_user['userid']}, {"$set": {f"dinos.{bd_user['settings']['dino_id']}": bd_user['dinos'][ bd_user['settings']['dino_id'] ] }} )

                                bot.send_message(message.chat.id, text, reply_markup = functions.markup(bot, 'actions', user), parse_mode = 'html')


                            else:
                                if bd_user['language_code'] == 'ru':
                                    text = f'🔇 | Вы попробовали вернуть динозавра, но что-то пошло не так...'
                                else:
                                    text = f"🔇 | You tried to bring the dinosaur back, but something went wrong..."

                                bot.send_message(message.chat.id, text , reply_markup = functions.markup(bot, 'actions', user))
                        else:
                            bot.send_message(message.chat.id, f'❌', reply_markup = functions.markup(bot, 'actions', user))
                            return

                if message.text in ['🎮 Развлечения', '🎮 Entertainments']:
                    bd_user = users.find_one({"userid": user.id})
                    if bd_user != None:
                        dino = bd_user['dinos'][ str(bd_user['settings']['dino_id']) ]

                        if dino['activ_status'] == 'pass_active':

                            if bd_user['language_code'] == 'ru':
                                text = f"🎮 | Перенаправление в меню развлечений!"

                            else:
                                text = f"🎮 | Redirecting to the entertainment menu!"

                            bot.send_message(message.chat.id, text, reply_markup = functions.markup(bot, 'games', user))

                        else:

                            if bd_user['language_code'] == 'ru':
                                text = f"❗ | Ваш динозавр уже чем то занят, проверьте профиль!"

                            else:
                                text = f"❗ | Your dinosaur is already busy with something, check the profile!"

                            bot.send_message(message.chat.id, text, reply_markup = functions.inline_markup(bot, f'open_dino_profile', message.chat.id, ['Открыть профиль', 'Open a profile'], str(bd_user['settings']['dino_id']) ))


                if message.text in ['🎮 Консоль', '🪁 Змей', '🏓 Пинг-понг', '🏐 Мяч', '🎮 Console', '🪁 Snake', '🏓 Ping Pong', '🏐 Ball', '🧩 Пазлы', '♟ Шахматы', '🧱 Дженга', '🎲 D&D', '🧩 Puzzles', '♟ Chess', '🧱 Jenga']:
                    bd_user = users.find_one({"userid": user.id})
                    if bd_user != None:
                        dino = bd_user['dinos'][ str(bd_user['settings']['dino_id']) ]
                        if dino['activ_status'] == 'pass_active':

                            markup_inline = types.InlineKeyboardMarkup(row_width=2)

                            if bd_user['language_code'] == 'ru':
                                text = ['15 - 30 мин.', '30 - 60 мин.', '60 - 90 мин.']
                                m_text = '🎮 Укажите разрешённое время игры > '
                            else:
                                text = ['15 - 30 min.', '30 - 60 min.', '60 - 90 min.']
                                m_text = '🎮 Specify the allowed game time >'

                            if message.text in ['🎮 Консоль', '🎮 Console']:
                                g = 'con'
                            elif message.text in ['🪁 Змей', '🪁 Snake']:
                                g = 'sna'
                            elif message.text in ['🏓 Пинг-понг', '🏓 Ping Pong']:
                                g = 'pin'
                            elif message.text in ['🏐 Мяч', '🏐 Ball']:
                                g = 'bal'

                            else:
                                if functions.acc_check(bot, bd_user, '44', str(bd_user['settings']['dino_id']), True):

                                    if message.text in ['🧩 Пазлы', '🧩 Puzzles']:
                                        g = 'puz'
                                    elif message.text in ['♟ Шахматы', '♟ Chess']:
                                        g = 'che'
                                    elif message.text in ['🧱 Jenga', '🧱 Дженга']:
                                        g = 'jen'
                                    elif message.text in ['🎲 D&D']:
                                        g = 'ddd'

                                else:
                                    return

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
                                bot.send_message(message.chat.id, text, reply_markup = functions.markup(bot, 'games', user))

                            else:

                                if bd_user['language_code'] == 'ru':
                                    text = f"🎮 | Динозавра невозможно оторвать от игры, попробуйте ещё раз. Имейте ввиду, динозавр будет расстроен."

                                else:
                                    text = f"🎮 | It is impossible to tear the dinosaur away from the game, try again. Keep in mind, the dinosaur will be upset."

                                bot.send_message(message.chat.id, text, reply_markup = functions.markup(bot, 'games', user))

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
                            if data_items[str(i['item_id'])]['type'] == "+eat":
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
                            items_id[ items_f['items'][str(i['item_id'])][lg] ] = i
                            items_names.append( items_f['items'][str(i['item_id'])][lg] )

                        items_names.sort()

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

                        pages = list(functions.chunks(list(functions.chunks(items_sort, 2)), 3))

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

                                    bot.send_message(message.chat.id, text, reply_markup = functions.markup(bot, 'actions', user))
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
                                        item_id = items_id[ l_ind_sort_it[res] ]['item_id']
                                        user_item = items_id[ l_ind_sort_it[res] ]
                                        item = items_f['items'][item_id]

                                        bd_dino = bd_user['dinos'][ bd_user['settings']['dino_id'] ]
                                        d_dino = json_f['elements'][ str(bd_dino['dino_id']) ]
                                        col = 1
                                        mx_col = 0
                                        for item_c in bd_user['inventory']:
                                            if item_c == user_item:
                                                mx_col += 1

                                        if bd_user['language_code'] == 'ru':
                                            text_col = f"🧀 | Введите число использований или выберите его из списка >"
                                        else:
                                            text_col = f"🧀 | Enter the number of uses or select it from the list >"

                                        rmk = types.ReplyKeyboardMarkup(resize_keyboard = True, row_width = 3)

                                        col_to_full = int( (100 - bd_dino['stats']['eat']) / item['act'])
                                        bt_3 = None

                                        if col_to_full > mx_col:
                                            col_to_full = mx_col

                                        bt_1 = f"{bd_dino['stats']['eat'] + item['act']}% = {item['nameru'][:1]} x1"
                                        bt_2 = f"{bd_dino['stats']['eat'] + item['act'] * col_to_full}% = {item['nameru'][:1]} x{col_to_full}"

                                        col_l = [[], [1, col_to_full]]

                                        col_l[0].append(bt_1), col_l[0].append(bt_2)

                                        if bd_dino['stats']['eat'] + item['act'] * col_to_full < 100:

                                            bt_3 = f"{100}% = {item['nameru'][:1]} x{col_to_full+1}"

                                            col_l[0].append(bt_3)
                                            col_l[1].append(col_to_full+1)

                                        if col_to_full == 1:

                                            if bt_3 != None:
                                                rmk.add(bt_1, bt_3)

                                            else:
                                                rmk.add(bt_1)

                                        elif col_to_full != 1 and col_to_full != 0:

                                            if bt_3 != None:
                                                rmk.add(bt_1, bt_2, bt_3)

                                            else:
                                                rmk.add(bt_1, bt_2)

                                        if bd_user['language_code'] == 'ru':
                                            rmk.add('↩ Назад')
                                        else:
                                            rmk.add('↩ Back')


                                        def corm(message, bd_user, user_item, item, d_dino, mx_col, col_l):

                                            if message.text in ['↩ Back', '↩ Назад']:

                                                if bd_user['language_code'] == 'ru':
                                                    text = "👥 | Возвращение в меню активностей!"
                                                else:
                                                    text = "👥 | Return to the friends menu!"

                                                bot.send_message(message.chat.id, text, reply_markup = functions.markup(bot, 'actions', user))
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

                                                    bot.send_message(message.chat.id, text, reply_markup = functions.markup(bot, 'actions', user))
                                                    return

                                            if 'abilities' in user_item.keys():
                                                if 'uses' in user_item['abilities'].keys():
                                                    if col > user_item['abilities']['uses']:

                                                        if bd_user['language_code'] == 'ru':
                                                            text = f"Данный предмет нельзя использовать столько раз!"
                                                        else:
                                                            text = f"This item cannot be used so many times!"

                                                        bot.send_message(message.chat.id, text, reply_markup = functions.markup(bot, 'actions', user))

                                                        return

                                            if col > mx_col:

                                                if bd_user['language_code'] == 'ru':
                                                    text = f"У вас нет столько предметов в инвентаре!"
                                                else:
                                                    text = f"You don't have that many items in your inventory!"

                                                bot.send_message(message.chat.id, text, reply_markup = functions.markup(bot, 'actions', user))

                                                return


                                            if bd_user['language_code'] == 'ru':
                                                if item['class'] == 'ALL':

                                                    bd_user['dinos'][ bd_user['settings']['dino_id'] ]['stats']['eat'] += item['act'] * col

                                                    if bd_user['dinos'][ bd_user['settings']['dino_id'] ]['stats']['eat'] > 100:
                                                        bd_user['dinos'][ bd_user['settings']['dino_id'] ]['stats']['eat'] = 100

                                                    text = f"🍕 | Динозавр с удовольствием съел {item['nameru']}!\nДинозавр сыт на {bd_user['dinos'][ bd_user['settings']['dino_id'] ]['stats']['eat']}%"


                                                elif item['class'] == d_dino['class']:
                                                    bd_user['dinos'][ bd_user['settings']['dino_id'] ]['stats']['eat'] += item['act'] * col

                                                    if bd_user['dinos'][ bd_user['settings']['dino_id'] ]['stats']['eat'] > 100:
                                                        bd_user['dinos'][ bd_user['settings']['dino_id'] ]['stats']['eat'] = 100

                                                    text = f"🍕 | Динозавр с удовольствием съел {item['nameru']}!\nДинозавр сыт на {bd_user['dinos'][ bd_user['settings']['dino_id'] ]['stats']['eat']}%"


                                                else:
                                                    eatr = random.randint( 0, int(item['act'] / 2) )
                                                    moodr = random.randint( 1, 10 )
                                                    text = f"🍕 | Динозавру не по вкусу {item['nameru']}, он теряет {eatr}% сытости и {moodr}% настроения!"

                                                    bd_user['dinos'][ bd_user['settings']['dino_id'] ]['stats']['eat'] -= eatr
                                                    bd_user['dinos'][ bd_user['settings']['dino_id'] ]['stats']['mood'] -= moodr

                                            else:
                                                if item['class'] == 'ALL':

                                                    bd_user['dinos'][ bd_user['settings']['dino_id'] ]['stats']['eat'] += item['act'] * col

                                                    if bd_user['dinos'][ bd_user['settings']['dino_id'] ]['stats']['eat'] > 100:
                                                        bd_user['dinos'][ bd_user['settings']['dino_id'] ]['stats']['eat'] = 100

                                                    text = f"🍕 | The dinosaur ate it with pleasure {item['nameen']}!\nThe dinosaur is fed up on {bd_user['dinos'][ bd_user['settings']['dino_id'] ]['stats']['eat']}%"

                                                elif item['class'] == d_dino['class']:

                                                    bd_user['dinos'][ bd_user['settings']['dino_id'] ]['stats']['eat'] += item['act'] * col

                                                    if bd_user['dinos'][ bd_user['settings']['dino_id'] ]['stats']['eat'] > 100:
                                                        bd_user['dinos'][ bd_user['settings']['dino_id'] ]['stats']['eat'] = 100

                                                    text = f"🍕 | The dinosaur ate it with pleasure {item['nameen']}!\nThe dinosaur is fed up on {bd_user['dinos'][ bd_user['settings']['dino_id'] ]['stats']['eat']}%"

                                                else:
                                                    eatr = random.randint( 0, int(item['act'] / 2) )
                                                    moodr = random.randint( 1, 10 )
                                                    text = f"🍕 | The dinosaur doesn't like {item['nameen']}, it loses {eatr}% satiety and {mood}% mood!"

                                                    bd_user['dinos'][ bd_user['settings']['dino_id'] ]['stats']['eat'] -= eatr
                                                    bd_user['dinos'][ bd_user['settings']['dino_id'] ]['stats']['mood'] -= moodr

                                            if '+mood' in item.keys():
                                                bd_user['dinos'][ bd_user['settings']['dino_id'] ]['stats']['mood'] += item['+mood'] * col

                                            if '-mood' in item.keys():
                                                bd_user['dinos'][ bd_user['settings']['dino_id'] ]['stats']['mood'] -= item['-mood'] * col

                                            users.update_one( {"userid": bd_user['userid']}, {"$set": {f'dinos.{bd_user["settings"]["dino_id"]}': bd_user['dinos'][ bd_user['settings']['dino_id'] ] }} )

                                            if ('abilities' in user_item.keys() and 'uses' not in user_item['abilities'].keys()) or 'abilities' not in user_item.keys():

                                                for i in range(col):
                                                    bd_user['inventory'].remove(user_item)

                                                users.update_one( {"userid": bd_user['userid']}, {"$set": {'inventory': bd_user['inventory'] }} )

                                            else:
                                                bd_user['inventory'].remove(user_item)
                                                users.update_one( {"userid": bd_user['userid']}, {"$set": {'inventory': bd_user['inventory'] }} )

                                                user_item['abilities']['uses'] -= 1 * col
                                                if user_item['abilities']['uses'] > 0:
                                                    users.update_one( {"userid": user.id}, {"$push": {f'inventory': user_item }} )

                                            bot.send_message(message.chat.id, text, reply_markup = functions.markup(bot, 'actions', user))

                                        msg = bot.send_message(message.chat.id, text_col, reply_markup = rmk)
                                        bot.register_next_step_handler(msg, corm, bd_user, user_item, item, d_dino, mx_col, col_l)

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

                                bot.send_message(message.chat.id, text, reply_markup = functions.markup(bot, 'actions', user))

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

                                        bot.send_message(message.chat.id, text, reply_markup = functions.markup(bot, 'actions', user))

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
                                        bot.send_message(message.chat.id, text, reply_markup = functions.markup(bot, 'actions', user))

                                msg = bot.send_message(message.chat.id, text, reply_markup = rmk)
                                bot.register_next_step_handler(msg, ret2, ans, bd_user)

                        msg = bot.send_message(message.chat.id, text, reply_markup = rmk)
                        bot.register_next_step_handler(msg, ret, bbt, bd_user)

                    else:

                        if bd_user['language_code'] == 'ru':
                            text = f"❗ | Ваш динозавр уже чем то занят, проверьте профиль!"

                        else:
                            text = f"❗ | Your dinosaur is already busy with something, check the profile!"

                        bot.send_message(message.chat.id, text, reply_markup = functions.inline_markup(bot, f'open_dino_profile', message.chat.id, ['Открыть профиль', 'Open a profile'], str(bd_user['settings']['dino_id']) ))


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

                if message.text in ['🤍 Пригласи друга', '🤍 Invite a friend']:

                    bd_user = users.find_one({"userid": user.id})
                    if bd_user != None:
                        coins = 200

                        if bd_user['language_code'] == 'ru':
                            text = f"🤍 | Перенаправление в меню реферальной системы!\n\n💜 | При достижению 5-го уровня вашим другом, вы получите 🥚 Необычное/Редкое яйцо динозавра!\n\n❤ | Друг получит бонус в размере: {coins} монет,\n 🍯 Баночка мёда х2, 🧸 Мишка, 🍗 Куриная ножка x2, 🍒 Ягоды x2, 🦪 Мелкая рыба x2, 🍪 Печенье x2"

                        else:
                            text = f"🤍 | Redirection to the referral system menu!\n\n💜 | When your friend reaches the 5th level, you will receive an Unusual/Rare dinosaur egg!\n\n❤ | Friend will receive a bonus: {coins} coins,\n 🍯 Jar of honey x2, 🧸 Bear, 🍗 Chicken leg x2, 🍒 Berries x2, 🦪 Small fish x2, 🍪 Cookies x2"

                        bot.send_message(message.chat.id, text, reply_markup = functions.markup(bot, "referal-system", user))

                if message.text in ['👥 Меню друзей', '👥 Friends Menu']:

                    bd_user = users.find_one({"userid": user.id})
                    if bd_user != None:
                        dino = bd_user['dinos'][ str(bd_user['settings']['dino_id']) ]

                        if bd_user['language_code'] == 'ru':
                            text = f"👥 | Перенаправление в меню друзей!"

                        else:
                            text = f"👥 | Redirecting to the friends menu!"

                        bot.send_message(message.chat.id, text, reply_markup = functions.markup(bot, "friends-menu", user))

                if message.text in ['🎲 Сгенерировать код', '🎲 Generate Code']:
                    bd_user = users.find_one({"userid": user.id})
                    if bd_user != None:
                        if 'referal_system' not in bd_user.keys():
                            rf = referal_system.find_one({"id": 1})
                            def r_cod():
                                code_rf = ''
                                for i in range(6):
                                    code_rf += str(random.randint(0,9))
                                return code_rf

                            rf_code = r_cod()
                            while rf_code in rf['codes']:
                                rf_code = r_cod()

                            rf['codes'].append(rf_code)
                            referal_system.update_one( {"id": 1}, {"$set": {'codes': rf['codes'] }} )

                            bd_user['referal_system'] = {'my_cod': rf_code, 'friend_cod': None}
                            users.update_one( {"userid": bd_user['userid']}, {"$set": {'referal_system': bd_user['referal_system'] }} )

                            if bd_user['language_code'] == 'ru':
                                text = f"🎲 | Ваш код сгенерирован!\nКод: `{rf_code}`"

                            else:
                                text = f"🎲 | Your code is generated!\nСode: `{rf_code}`"

                            bot.send_message(message.chat.id, text, parse_mode = 'Markdown', reply_markup = functions.markup(bot, "referal-system", user))

                if message.text in ['🎞 Ввести код', '🎞 Enter Code']:
                    rf = referal_system.find_one({"id": 1})

                    def ret(message, bd_user):
                        if message.text in rf['codes']:
                            if str(bd_user['referal_system']['my_cod']) != message.text:
                                items = ['1', '1', '2', '2', '16', '12', '12', '11', '11', '13', '13']
                                coins = 200
                                bd_user['coins'] += coins
                                for i in items:
                                    functions.add_item_to_user(bd_user, i)

                                members = users.find({ })
                                fr_member = None

                                for i in members:
                                    if fr_member != None:
                                        break
                                    else:
                                        if 'referal_system' in i.keys():
                                            if i['referal_system']['my_cod'] == message.text:
                                                fr_member = i


                                if fr_member['userid'] not in bd_user['friends']['friends_list']:
                                    bd_user['friends']['friends_list'].append(i['userid'])
                                    users.update_one( {"userid": bd_user['userid']}, {"$set": {'friends': bd_user['friends'] }} )

                                if bd_user['userid'] not in fr_member['friends']['friends_list']:
                                    fr_member['friends']['friends_list'].append(bd_user['userid'])
                                    users.update_one( {"userid": fr_member['userid']}, {"$set": {'friends': fr_member['friends'] }} )

                                bd_user['referal_system']['friend_cod'] = message.text
                                bd_user['referal_system']['friend'] = fr_member['userid']

                                users.update_one( {"userid": bd_user['userid']}, {"$set": {'coins': bd_user['coins'] }} )

                                users.update_one( {"userid": bd_user['userid']}, {"$set": {'referal_system': bd_user['referal_system'] }} )

                                if bd_user['language_code'] == 'ru':
                                    text = f"❤🤍💜 | Код друга активирован!\n\n❤ | Спасибо что поддерживаете и помогаете развивать нашего бота, приглашая друзей!\n\n🤍 | По достижению 5-го уровня, ваш друг получит 🥚 Необычное/Редкое яйцо динозавра!\n\n💜 | Вы получаете бонус в размере: {coins} монет, 🍯 Баночка мёда х2, 🧸 Мишка, 🍗 Куриная ножка x2, 🍒 Ягоды x2, 🦪 Мелкая рыба x2, 🍪 Печенье x2"

                                else:
                                    text = f"❤🤍💜 | The friend's code is activated!\n\n❤ | Thank you for supporting and helping to develop our bot by inviting friends!\n\n🤍 | Upon reaching level 5, your friend will receive an 🥚 Unusual/Rare Dinosaur Egg!\n\n💜 | You get a bonus: {coins} coins, 🍯 Jar of honey x2, 🧸 Bear, 🍗 Chicken leg x2, 🍒 Berries x2, 🦪 Small fish x2, 🍪 Cookies x2"

                            else:
                                if bd_user['language_code'] == 'ru':
                                    text = f"❗ | Вы не можете активировать свой код друга!"

                                else:
                                    text = f"❗ | You can't activate your friend code!"
                        else:
                            if bd_user['language_code'] == 'ru':
                                text = f"❗ | Код не найден!"

                            else:
                                text = f"❗ | Code not found!"

                        bot.send_message(message.chat.id, text, reply_markup = functions.markup(bot, "referal-system", user))



                    bd_user = users.find_one({"userid": user.id})
                    if bd_user != None:
                        if 'referal_system' not in bd_user.keys():
                            rf = referal_system.find_one({"id": 1})
                            def r_cod():
                                code_rf = ''
                                for i in range(6):
                                    code_rf += str(random.randint(0,9))
                                return code_rf

                            rf_code = r_cod()
                            while rf_code in rf['codes']:
                                rf_code = r_cod()

                            rf['codes'].append(rf_code)
                            referal_system.update_one( {"id": 1}, {"$set": {'codes': rf['codes'] }} )

                            bd_user['referal_system'] = {'my_cod': rf_code, 'friend_cod': None}
                            users.update_one( {"userid": bd_user['userid']}, {"$set": {'referal_system': bd_user['referal_system'] }} )

                            if bd_user['language_code'] == 'ru':
                                text = f"🎲 | Ваш код сгенерирован!\nКод: `{rf_code}`"

                            else:
                                text = f"🎲 | Your code is generated!\nСode: `{rf_code}`"

                            bot.send_message(message.chat.id, text, parse_mode = 'Markdown', reply_markup = functions.markup(bot, "referal-system", user))

                            if bd_user['language_code'] == 'ru':
                                ans = ['↪ Назад']
                                text = '👥 | Введите код-приглашение друга > '
                            else:
                                ans = ['↪ Back']
                                text = "👥 | Enter a friend's invitation code >"

                            rmk = types.ReplyKeyboardMarkup(resize_keyboard = True)
                            rmk.add(ans[0])


                            msg = bot.send_message(message.chat.id, text, reply_markup = rmk)
                            bot.register_next_step_handler(msg, ret, bd_user)

                        else:
                            if bd_user['referal_system']['friend_cod'] == None:

                                if bd_user['language_code'] == 'ru':
                                    ans = ['↪ Назад']
                                    text = '👥 | Введите код-приглашение друга > '
                                else:
                                    ans = ['↪ Back']
                                    text = "👥 | Enter a friend's invitation code >"

                                rmk = types.ReplyKeyboardMarkup(resize_keyboard = True)
                                rmk.add(ans[0])


                                msg = bot.send_message(message.chat.id, text, reply_markup = rmk)
                                bot.register_next_step_handler(msg, ret, bd_user)

                            else:
                                if bd_user['language_code'] == 'ru':
                                    text = '👥 | Вы уже ввели код друга!'
                                else:
                                    text = "👥 | You have already entered a friend's code!"

                                msg = bot.send_message(message.chat.id, text)


                if message.text in ['💍 Аксессуары', '💍 Accessories']:
                    bd_user = users.find_one({"useriid": user.id})
                    if bd_user != None:

                        if len(bd_user['dinos']) > 1:
                            for i in bd_user['dinos'].keys():
                                if i not in bd_user['activ_items'].keys():

                                    users.update_one( {"userid": bd_user["userid"] }, {"$set": {f'activ_items.{i}': {'game': None, 'hunt': None, 'journey': None, 'unv': None} }} )

                        def acss(message, dino_id, user, bd_user):

                            if bd_user['dinos'][dino_id]['status'] != 'dino':

                                if bd_user['language_code'] == 'ru':
                                    text = '🎍 | Динозавр должен быть инкубирован!'
                                else:
                                    text = '🎍 | The dinosaur must be incubated!'

                                bot.send_message(message.chat.id, text)
                                return

                            if bd_user['dinos'][dino_id]['activ_status'] != 'pass_active':

                                if bd_user['language_code'] == 'ru':
                                    text = '🎍 | Во время игры / сна / путешествия и тд. - нельзя менять аксесcуар!'
                                else:
                                    text = '🎍 | While playing / sleeping / traveling, etc. - you can not change the accessory!'

                                bot.send_message(message.chat.id, text)
                                return


                            if bd_user['language_code'] == 'ru':
                                ans = ['🕹 Игра', '🌙 Сон', '🌿 Сбор пищи', '🏮 Путешествие', '↪ Назад']
                                text = '🎍 | Выберите какого аспекта должен быть аксесcуар >'
                            else:
                                ans = ['🕹 Game', '🌙 Dream', '🌿 Collecting food', '🏮 Journey', '↪ Back']
                                text = '🎍 | Choose which aspect the accessory should be >'

                            rmk = types.ReplyKeyboardMarkup(resize_keyboard = True)
                            rmk.add(ans[0], ans[1])
                            rmk.add(ans[2], ans[3])
                            rmk.add(ans[4])

                            def ret_zero(message, ans, bd_user):

                                if message.text not in ans or message.text == ans[4]:
                                    res = None
                                else:
                                    res = message.text

                                if res == None:
                                    bot.send_message(message.chat.id, f'❌', reply_markup = functions.markup(bot, 'profile', user))
                                    return

                                if message.text in ['🕹 Game', '🕹 Игра']:
                                    ac_type = 'game'
                                if message.text in ['🌙 Сон', '🌙 Dream']:
                                    ac_type = 'unv'
                                if message.text in ['🌿 Сбор пищи', '🌿 Collecting food']:
                                    ac_type = 'hunt'
                                if message.text in ['🏮 Путешествие', '🏮 Journey']:
                                    ac_type = 'journey'

                                if bd_user['language_code'] == 'ru':
                                    text = '🎴 | Выберите предмет из инвентаря, для установки его в активный слот >'
                                else:
                                    text = '🎴 | Select an item from the inventory to install it in the active slot >'

                                nitems = bd_user['inventory']

                                if nitems == []:

                                    if bd_user['language_code'] == 'ru':
                                        text = 'Инвентарь пуст.'
                                    else:
                                        text = 'Inventory is empty.'

                                    bot.send_message(message.chat.id, text, reply_markup = functions.markup(bot, 'profile', user))
                                    return

                                data_items = items_f['items']
                                items = []
                                items_id = {}
                                page = 1
                                items_names = []

                                for i in nitems:
                                    if data_items[str(i['item_id'])]['type'] == f"{ac_type}_ac":
                                        items.append(i)

                                if bd_user['language_code'] == 'ru':
                                    lg = "nameru"
                                else:
                                    lg = "nameen"

                                for i in items:
                                    items_id[ items_f['items'][str(i['item_id'])][lg] ] = i
                                    items_names.append( items_f['items'][str(i['item_id'])][lg] )

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

                                pages = list(functions.chunks(list(functions.chunks(items_sort, 2)), 2))

                                if len(pages) == 0:
                                    pages = [ [ ] ]

                                for i in pages:
                                    for ii in i:
                                        if len(ii) == 1:
                                            ii.append(' ')

                                    if len(i) != 2:
                                        for iii in range(2 - len(i)):
                                            i.append([' ', ' '])

                                def work_pr(message, pages, page, items_id, ind_sort_it, lg, ac_type):
                                    global l_pages, l_page, l_ind_sort_it
                                    a = []
                                    l_pages = pages
                                    l_page = page
                                    l_ind_sort_it = ind_sort_it

                                    def ret(message):
                                        global l_pages, l_page, l_ind_sort_it
                                        if message.text in ['↪ Назад', '↪ Back']:
                                            a.append(None)
                                            return False
                                        else:
                                            if message.text in list(l_ind_sort_it.keys()) or message.text in ['◀', '▶', '🔻 Снять аксесcуар', '🔻 Remove the accessory']:
                                                a.append(message.text)
                                            else:
                                                a.append(None)
                                            return False

                                    rmk = types.ReplyKeyboardMarkup(resize_keyboard = True, row_width = 3)
                                    for i in pages[page-1]:
                                        rmk.add(i[0], i[1])

                                    act_item = []
                                    if bd_user['activ_items'][ dino_id ][ac_type] == None:
                                        act_item = ['нет', 'no']
                                    else:
                                        act_item = [ items_f['items'][ bd_user['activ_items'][ dino_id ][ac_type]['item_id'] ] ['nameru'], items_f['items'][ bd_user['activ_items'][ dino_id ][ac_type]['item_id'] ]['nameen'] ]

                                    if len(pages) > 1:
                                        if bd_user['language_code'] == 'ru':
                                            com_buttons = ['◀', '↪ Назад', '▶', '🔻 Снять аксесcуар']
                                            textt = f'🎴 | Выберите аксессуар >\nАктивный: {act_item[0]}'
                                        else:
                                            com_buttons = ['◀', '↪ Back', '▶', '🔻 Remove the accessory']
                                            textt = f'🎴 | Choose an accessory >\nActive: {act_item[1]}'

                                        rmk.add(com_buttons[3])
                                        rmk.add(com_buttons[0], com_buttons[1], com_buttons[2])

                                    else:

                                        if bd_user['language_code'] == 'ru':
                                            com_buttons = ['↪ Назад', '🔻 Снять аксесcуар']
                                            textt = f'🎴 | Выберите аксессуар >\nАктивный: {act_item[0]}'
                                        else:
                                            textt = f'🎴 | Choose an accessory >\nActive: {act_item[1]}'
                                            com_buttons = ['↪ Back', '🔻 Remove the accessory']

                                        rmk.add(com_buttons[1])
                                        rmk.add(com_buttons[0])

                                    def ret(message, l_pages, l_page, l_ind_sort_it, bd_user, user, pages, page, items_id, ind_sort_it, lg, ac_type):
                                        if message.text in ['↩ Назад', '↩ Back']:
                                            res = None

                                        else:
                                            if message.text in list(l_ind_sort_it.keys()) or message.text in ['◀', '▶', '🔻 Снять аксесcуар', '🔻 Remove the accessory']:
                                                res = message.text
                                            else:
                                                res = None


                                        if res == None:
                                            if bd_user['language_code'] == 'ru':
                                                text = "👥 | Возвращение в меню профиля"
                                            else:
                                                text = "👥 | Return to the profile menu"

                                            bot.send_message(message.chat.id, text, reply_markup = functions.markup(bot, 'profile', user))
                                            return '12'

                                        else:
                                            if res == '◀':
                                                if page - 1 == 0:
                                                    page = 1
                                                else:
                                                    page -= 1

                                                work_pr(message, pages, page, items_id, ind_sort_it, lg, ac_type)

                                            elif res == '▶':
                                                if page + 1 > len(l_pages):
                                                    page = len(l_pages)
                                                else:
                                                    page += 1

                                                work_pr(message, pages, page, items_id, ind_sort_it, lg, ac_type)

                                            else:

                                                if res in ['🔻 Снять аксесcуар', '🔻 Remove the accessory']:
                                                    if bd_user['activ_items'][ dino_id ][ac_type] != None:
                                                        item = bd_user['activ_items'][ dino_id ][ac_type]
                                                        bd_user['activ_items'][ dino_id ][ac_type] = None

                                                        if bd_user['language_code'] == 'ru':
                                                            text = "🎴 | Активный предмет снят"
                                                        else:
                                                            text = "🎴 | Active item removed"

                                                        users.update_one( {"userid": bd_user['userid']}, {"$push": {'inventory': item }} )
                                                        users.update_one( {"userid": bd_user['userid']}, {"$set": {'activ_items': bd_user['activ_items'] }} )

                                                    else:
                                                        if bd_user['language_code'] == 'ru':
                                                            text = "🎴 | В данный момент нет активного предмета!"
                                                        else:
                                                            text = "🎴 | There is no active item at the moment!"

                                                    bot.send_message(message.chat.id, text, reply_markup = functions.markup(bot, 'profile', user))

                                                else:
                                                    if bd_user['activ_items'][ dino_id ][ac_type] != None:
                                                        bd_user['inventory'].append(bd_user['activ_items'][ dino_id ][ac_type])

                                                    item = items_id[ l_ind_sort_it[res] ]

                                                    bd_user['activ_items'][ dino_id ][ac_type] = item

                                                    if bd_user['language_code'] == 'ru':
                                                        text = "🎴 | Активный предмет установлен!"
                                                    else:
                                                        text = "🎴 | The active item is installed!"

                                                    bd_user['inventory'].remove(item)
                                                    users.update_one( {"userid": bd_user['userid']}, {"$set": {'inventory': bd_user['inventory'] }} )

                                                    users.update_one( {"userid": bd_user['userid']}, {"$set": {'activ_items': bd_user['activ_items'] }} )

                                                    bot.send_message(message.chat.id, text, reply_markup = functions.markup(bot, 'profile', user))

                                    msg = bot.send_message(message.chat.id, textt, reply_markup = rmk)
                                    bot.register_next_step_handler(msg, ret, l_pages, l_page, l_ind_sort_it, bd_user, user, pages, page, items_id, ind_sort_it, lg, ac_type)

                                work_pr(message, pages, page, items_id, ind_sort_it, lg, ac_type)

                            msg = bot.send_message(message.chat.id, text, reply_markup = rmk)
                            bot.register_next_step_handler(msg, ret_zero, ans, bd_user)

                        n_dp, dp_a = functions.dino_pre_answer(bot, message)
                        if n_dp == 1:

                            bot.send_message(message.chat.id, f'❌', reply_markup = functions.markup(bot, 1, user))
                            return

                        if n_dp == 2:

                            acss(message, list(bd_user['dinos'].keys())[0], user, bd_user)

                        if n_dp == 3:
                            rmk = dp_a[0]
                            text = dp_a[1]
                            dino_dict = dp_a[2]

                            def ret(message, dino_dict, user, bd_user):

                                try:

                                    acss(message, dino_dict[message.text][1], user, bd_user)
                                except:
                                    bot.send_message(message.chat.id, '❓', reply_markup = functions.markup(bot, "profile", user))

                            msg = bot.send_message(message.chat.id, text, reply_markup = rmk)
                            bot.register_next_step_handler(msg, ret, dino_dict, user, bd_user)

                if message.text in ['🛒 Рынок', '🛒 Market']:
                    bd_user = users.find_one({"userid": user.id})
                    if bd_user != None:

                        if bd_user['language_code'] == 'ru':
                            text = '🛒 Панель рынка открыта!'
                        else:
                            text = '🛒 The market panel is open!'

                        bot.send_message(message.chat.id, text, reply_markup = functions.markup(bot, "market", user))

                if message.text in ['➕ Добавить товар', '➕ Add Product']:

                    functions.user_inventory(bot, user, message, 'add_product')

                if message.text in ['📜 Мои товары', '📜 My products']:
                    bd_user = users.find_one({"userid": user.id})
                    if bd_user != None:

                        market_ = market.find_one({"id": 1})
                        if str(user.id) not in market_['products'].keys() or market_['products'][str(user.id)]['products'] == {}:

                            if bd_user['language_code'] == 'ru':
                                text = "🛒 | У вас нет продаваемых продуктов на рынке!"
                            else:
                                text = "🛒 | You don't have any saleable products on the market!"

                            bot.send_message(message.chat.id, text)

                        else:

                            products = []
                            page = 1

                            for i in market_['products'][str(user.id)]['products'].keys():
                                product = market_['products'][str(user.id)]['products'][i]
                                products.append(product)

                            pages = list(functions.chunks(products, 5))

                            if bd_user['language_code'] == 'ru':
                                text = '🛒 | *Ваши продукты*\n\n'
                            else:
                                text = '🛒 | *Your products*\n\n'

                            rmk = types.ReplyKeyboardMarkup(resize_keyboard = True, row_width = 3)

                            if len(pages) > 1:

                                if bd_user['language_code'] == 'ru':
                                    ans = ['◀', '🛒 Рынок', '▶']
                                else:
                                    ans = ['◀', '🛒 Market', '▶']

                                rmk.add(ans[0], ans[1], ans[2])

                            else:

                                if bd_user['language_code'] == 'ru':
                                    ans = ['🛒 Рынок']
                                else:
                                    ans = ['🛒 Market']

                                rmk.add(ans[0])

                            def work_pr(page, pages):

                                if bd_user['language_code'] == 'ru':
                                    text = '🛒 | *Ваши продукты*\n\n'
                                else:
                                    text = '🛒 | *Your products*\n\n'

                                w_page = pages[page-1]

                                nn = (page - 1) * 5
                                for pr in w_page:
                                    item = items_f['items'][ pr['item']['item_id'] ]
                                    nn += 1

                                    if int(w_page.index(pr)) == len(w_page) - 1:
                                        n = '└'
                                    elif int(w_page.index(pr)) == 0:
                                        n = '┌'
                                    else:
                                        n = '├'

                                    if bd_user['language_code'] == 'ru':
                                        text += f"*{n}* {nn}# {item['nameru']}\n    *└* Цена за 1х: {pr['price']}\n"
                                        text += f"       *└* Продано: {pr['col'][0]} / {pr['col'][1]}"

                                        if 'abilities' in pr['item'].keys():
                                            if 'uses' in pr['item']['abilities'].keys():
                                                text += f"\n           *└* Использований: {pr['item']['abilities']['uses']}"

                                            if 'endurance' in pr['item']['abilities'].keys():
                                                text += f"\n           *└* Прочность: {pr['item']['abilities']['endurance']}"

                                        text += '\n\n'

                                    else:
                                        text += f"*{n}* {nn}# {item['nameen']}\n    *└* Price pay for 1х: {pr['price']}\n"
                                        text += f"        *└* Sold: {pr['col'][0]} / {pr['col'][1]}"

                                        if 'abilities' in pr['item'].keys():
                                            if 'uses' in pr['item']['abilities'].keys():
                                                text += f"\n           *└* Uses: {pr['item']['abilities']['uses']}"

                                            if 'endurance' in pr['item']['abilities'].keys():
                                                text += f"\n           *└* Endurance: {pr['item']['abilities']['endurance']}"

                                        text += '\n\n'

                                if bd_user['language_code'] == 'ru':
                                    text += f'Страница: {page}'
                                else:
                                    text += f'Page: {page}'

                                return text

                            msg_g = bot.send_message(message.chat.id, work_pr(page, pages), reply_markup = rmk, parse_mode = 'Markdown')

                            def check_key(message, page, pages, ans):

                                if message.text in ['🛒 Рынок', '🛒 Market'] or message.text not in ans:

                                    if bd_user['language_code'] == 'ru':
                                        text = "🛒 | Возвращение в меню рынка!"
                                    else:
                                        text = "🛒 | Return to the market menu!"

                                    bot.send_message(message.chat.id, text, reply_markup = functions.markup(bot, 'market', user))
                                    return

                                if len(pages) > 1 and message.text in ['◀', '▶']:
                                    if message.text == '◀':

                                        if page - 1 == 0:
                                            page = 1
                                        else:
                                            page -= 1

                                    if message.text == '▶':

                                        if page + 1 > len(pages):
                                            page = len(pages)
                                        else:
                                            page += 1

                                msg = bot.send_message(message.chat.id, work_pr(page, pages), reply_markup = rmk, parse_mode = 'Markdown')
                                bot.register_next_step_handler(msg, check_key, page, pages, ans)

                            bot.register_next_step_handler(msg_g, check_key, page, pages, ans)

                if message.text in ['➖ Удалить товар', '➖ Delete Product']:
                    bd_user = users.find_one({"userid": user.id})
                    if bd_user != None:

                        market_ = market.find_one({"id": 1})
                        if str(user.id) not in market_['products'].keys() or market_['products'][str(user.id)]['products'] == {}:

                            if bd_user['language_code'] == 'ru':
                                text = "🛒 | У вас нет продаваемых продуктов на рынке!"
                            else:
                                text = "🛒 | You don't have any saleable products on the market!"

                            bot.send_message(message.chat.id, text)

                        else:

                            products = []
                            page = 1

                            for i in market_['products'][str(user.id)]['products'].keys():
                                product = market_['products'][str(user.id)]['products'][i]
                                products.append(product)

                            pages = list(functions.chunks(products, 5))

                            if bd_user['language_code'] == 'ru':
                                text = '🛒 | *Ваши продукты*\n\n'
                            else:
                                text = '🛒 | *Your products*\n\n'

                            rmk = types.ReplyKeyboardMarkup(resize_keyboard = True, row_width = 3)

                            lll = []
                            for i in range(1, len(pages[page-1])+1 ):
                                lll.append(str(i + 1 * page + (5 * (page-1))-1 * page ))

                            if len(lll) == 1:
                                rmk.add(lll[0])
                            if len(lll) == 2:
                                rmk.add(lll[0], lll[1])
                            if len(lll) == 3:
                                rmk.row(lll[0], lll[1], lll[2])
                            if len(lll) == 4:
                                rmk.row(lll[0], lll[1], lll[2], lll[3])
                            if len(lll) == 5:
                                rmk.row(lll[0], lll[1], lll[2], lll[3], lll[4])

                            if len(pages) > 1:

                                if bd_user['language_code'] == 'ru':
                                    ans = ['◀', '🛒 Рынок', '▶']
                                else:
                                    ans = ['◀', '🛒 Market', '▶']

                                rmk.add(ans[0], ans[1], ans[2])

                            else:

                                if bd_user['language_code'] == 'ru':
                                    ans = ['🛒 Рынок']
                                else:
                                    ans = ['🛒 Market']

                                rmk.add(ans[0])

                            def work_pr(page, pages):

                                if bd_user['language_code'] == 'ru':
                                    text = '🛒 | *Ваши продукты*\n\n'
                                else:
                                    text = '🛒 | *Your products*\n\n'

                                w_page = pages[page-1]

                                nn = (page - 1) * 5
                                for pr in w_page:
                                    item = items_f['items'][ pr['item']['item_id'] ]
                                    nn += 1

                                    if int(w_page.index(pr)) == len(w_page) - 1:
                                        n = '└'
                                    elif int(w_page.index(pr)) == 0:
                                        n = '┌'
                                    else:
                                        n = '├'

                                    if bd_user['language_code'] == 'ru':
                                        text += f"*{n}* {nn}# {item['nameru']}\n    *└* Цена за 1х: {pr['price']}\n"
                                        text += f"       *└* Продано: {pr['col'][0]} / {pr['col'][1]}"

                                        if 'abilities' in pr['item'].keys():
                                            if 'uses' in pr['item']['abilities'].keys():
                                                text += f"\n           *└* Использований: {pr['item']['abilities']['uses']}"

                                        text += '\n\n'

                                    else:
                                        text += f"*{n}* {nn}# {item['nameen']}\n    *└* Price pay for 1х: {pr['price']}\n"
                                        text += f"        *└* Sold: {pr['col'][0]} / {pr['col'][1]}"

                                        if 'abilities' in pr['item'].keys():
                                            if 'uses' in pr['item']['abilities'].keys():
                                                text += f"\n           *└* Uses: {pr['item']['abilities']['uses']}"

                                        text += '\n\n'

                                if bd_user['language_code'] == 'ru':
                                    text += f'Страница: {page}'
                                else:
                                    text += f'Page: {page}'

                                return text

                            msg_g = bot.send_message(message.chat.id, work_pr(page, pages), reply_markup = rmk, parse_mode = 'Markdown')

                            def check_key(message, page, pages, ans):
                                number = None

                                if message.text in ['🛒 Рынок', '🛒 Market']:

                                    if bd_user['language_code'] == 'ru':
                                        text = "🛒 | Возвращение в меню рынка!"
                                    else:
                                        text = "🛒 | Return to the market menu!"

                                    bot.send_message(message.chat.id, text, reply_markup = functions.markup(bot, 'market', user))
                                    return

                                if message.text not in ans:

                                    try:
                                        number = int(message.text)

                                    except:

                                        if bd_user['language_code'] == 'ru':
                                            text = "🛒 | Возвращение в меню рынка!"
                                        else:
                                            text = "🛒 | Return to the market menu!"

                                        bot.send_message(message.chat.id, text, reply_markup = functions.markup(bot, 'market', user))
                                        return

                                if number == None:
                                    if len(pages) > 1 and message.text in ['◀', '▶']:
                                        if message.text == '◀':

                                            if page - 1 == 0:
                                                page = 1
                                            else:
                                                page -= 1

                                        if message.text == '▶':

                                            if page + 1 > len(pages):
                                                page = len(pages)
                                            else:
                                                page += 1

                                    rmk = types.ReplyKeyboardMarkup(resize_keyboard = True, row_width = 3)

                                    lll = []
                                    for i in range(1, len(pages[page-1])+1 ):
                                        lll.append(str(i + 1 * page + (5 * (page-1))-1 * page ))

                                    if len(lll) == 1:
                                        rmk.add(lll[0])
                                    if len(lll) == 2:
                                        rmk.add(lll[0], lll[1])
                                    if len(lll) == 3:
                                        rmk.row(lll[0], lll[1], lll[2])
                                    if len(lll) == 4:
                                        rmk.row(lll[0], lll[1], lll[2], lll[3])
                                    if len(lll) == 5:
                                        rmk.row(lll[0], lll[1], lll[2], lll[3], lll[4])

                                    if len(pages) > 1:

                                        if bd_user['language_code'] == 'ru':
                                            ans = ['◀', '🛒 Рынок', '▶']
                                        else:
                                            ans = ['◀', '🛒 Market', '▶']

                                        rmk.add(ans[0], ans[1], ans[2])

                                    else:

                                        if bd_user['language_code'] == 'ru':
                                            ans = ['🛒 Рынок']
                                        else:
                                            ans = ['🛒 Market']

                                        rmk.add(ans[0])

                                    msg = bot.send_message(message.chat.id, work_pr(page, pages), reply_markup = rmk, parse_mode = 'Markdown')
                                    bot.register_next_step_handler(msg, check_key, page, pages, ans)

                                else:

                                    nn_number = list(market_['products'][str(user.id)]['products'].keys())[number-1]

                                    if nn_number not in market_['products'][str(user.id)]['products'].keys():

                                        if bd_user['language_code'] == 'ru':
                                            text = "🛒 | Объект с данным номером не найден в ваших продуктах!"
                                        else:
                                            text = "🛒 | The object with this number is not found in your products!"

                                        bot.send_message(message.chat.id, text, reply_markup = functions.markup(bot, 'market', user))

                                    else:

                                        prod = market_['products'][str(user.id)]['products'][nn_number]

                                        for i in range(prod['col'][1] - prod['col'][0]):
                                            bd_user['inventory'].append(prod['item'])

                                        del market_['products'][str(user.id)]['products'][nn_number]

                                        market.update_one( {"id": 1}, {"$set": {'products': market_['products'] }} )
                                        users.update_one( {"userid": user.id}, {"$set": {'inventory': bd_user['inventory']}} )

                                        if bd_user['language_code'] == 'ru':
                                            text = "🛒 | Продукт удалён!"
                                        else:
                                            text = "🛒 | The product has been removed!"

                                        bot.send_message(message.chat.id, text, reply_markup = functions.markup(bot, 'market', user))

                            bot.register_next_step_handler(msg_g, check_key, page, pages, ans)

                if message.text in [ '🔍 Поиск товара', '🔍 Product Search']:
                    bd_user = users.find_one({"userid": user.id})
                    if bd_user != None:

                        market_ = market.find_one({"id": 1})

                        rmk = types.ReplyKeyboardMarkup(resize_keyboard = True, row_width = 3)

                        if bd_user['language_code'] == 'ru':
                            ans = ['🛒 Рынок']
                            text = '🔍 | Введите имя предмета который вы ищите...'
                        else:
                            ans = ['🛒 Market']
                            text = '🔍 | Enter the name of the item you are looking for...'

                        rmk.add(ans[0])

                        def name_reg(message):
                            if message.text in ['🛒 Market', '🛒 Рынок']:

                                if bd_user['language_code'] == 'ru':
                                    text = "🛒 | Возвращение в меню рынка!"
                                else:
                                    text = "🛒 | Return to the market menu!"

                                bot.send_message(message.chat.id, text, reply_markup = functions.markup(bot, 'market', user))
                                return

                            else:
                                s_i = []
                                for i in items_f['items']:
                                    item = items_f['items'][i]

                                    for inn in [ item['nameru'], item['nameen'] ]:
                                        if fuzz.token_sort_ratio(message.text, inn) > 80 or fuzz.ratio(message.text, inn) > 80 or message.text == inn:
                                            s_i.append(i)

                                if s_i == []:

                                    if bd_user['language_code'] == 'ru':
                                        text = "🛒 | Предмет с таким именем не найден в базе продаваемых предметов!\nВозвращение в меню рынка!"
                                    else:
                                        text = "🛒 | An item with that name was not found in the database of sold items!\nreturn to the market menu!"

                                    bot.send_message(message.chat.id, text, reply_markup = functions.markup(bot, 'market', user))
                                    return


                                sear_items = []
                                for uid in market_['products']:
                                    if uid != str(bd_user['userid']):
                                        userser = market_['products'][uid]['products']
                                        for ki in userser:
                                            if userser[ki]['item']['item_id'] in s_i:
                                                sear_items.append( {'user': uid, 'key': ki, 'col': userser[ki]['col'], 'price': userser[ki]['price'], 'item': userser[ki]['item']} )

                                if sear_items == []:
                                    if bd_user['language_code'] == 'ru':
                                        text = "🛒 | Предмет с таким именем не найден в базе продаваемых предметов!\nВозвращение в меню рынка!"
                                    else:
                                        text = "🛒 | An item with that name was not found in the database of sold items!\nreturn to the market menu!"

                                    bot.send_message(message.chat.id, text, reply_markup = functions.markup(bot, 'market', user))
                                    return

                                random.shuffle(sear_items)
                                page = list(functions.chunks(sear_items, 10))[0]

                                text = ''
                                a = 0

                                markup_inline = types.InlineKeyboardMarkup()
                                in_l = []

                                if bd_user['language_code'] == 'ru':
                                    text += f"🔍 | По вашему запросу найдено {len(sear_items)} предметов(а) >\n\n"
                                    for i in page:
                                        a += 1
                                        text += f"*{a}#* {items_f['items'][i['item']['item_id']]['nameru']}\n     *└* Цена за 1х: {i['price']}\n         *└* Количество: {i['col'][1] - i['col'][0]}"

                                        if 'abilities' in i['item'].keys():
                                            if 'uses' in i['item']['abilities'].keys():
                                                text += f"\n           *└* Использований: {i['item']['abilities']['uses']}"

                                        text += '\n\n'
                                        in_l.append( types.InlineKeyboardButton( text = str(a) + '#', callback_data = f"market_buy_{i['user']} {i['key']}"))
                                else:
                                    text += f'🔍 | Your search found {len(search_items)} item(s) >\n\n'
                                    for i in page:
                                        a += 1
                                        text += f"*{a}#* {items_f['items'][i['item_id']]['nameen']}\n     *└* Price per 1x: {i['price']}\n         *└* Quantity: {i['col'][1] - i['col'][0]}"

                                        if 'abilities' in i['item'].keys():
                                            if 'uses' in i['item']['abilities'].keys():
                                                text += f"\n           *└* Uses: {i['item']['abilities']['uses']}"

                                        text += '\n\n'
                                        in_l.append( types.InlineKeyboardButton( text = str(a) + '#', callback_data = f"market_buy_{i['user']} {i['key']}"))


                                if len(in_l) == 1:
                                    markup_inline.add(in_l[0])
                                if len(in_l) == 2:
                                    markup_inline.add(in_l[0], in_l[1])
                                if len(in_l) == 3:
                                    markup_inline.add(in_l[0], in_l[1], in_l[2])
                                if len(in_l) == 4:
                                    markup_inline.add(in_l[0], in_l[1], in_l[2], in_l[3])
                                if len(in_l) == 5:
                                    markup_inline.add(in_l[0], in_l[1], in_l[2], in_l[3], in_l[4])
                                if len(in_l) == 6:
                                    markup_inline.add(in_l[0], in_l[1], in_l[2], in_l[3], in_l[4])
                                    markup_inline.add(in_l[5])
                                if len(in_l) == 7:
                                    markup_inline.add(in_l[0], in_l[1], in_l[2], in_l[3], in_l[4])
                                    markup_inline.add(in_l[5], in_l[6])
                                if len(in_l) == 8:
                                    markup_inline.add(in_l[0], in_l[1], in_l[2], in_l[3], in_l[4])
                                    markup_inline.add(in_l[5], in_l[6], in_l[7])
                                if len(in_l) == 9:
                                    markup_inline.add(in_l[0], in_l[1], in_l[2], in_l[3], in_l[4])
                                    markup_inline.add(in_l[5], in_l[6], in_l[7], in_l[8])
                                if len(in_l) == 10:
                                    markup_inline.add(in_l[0], in_l[1], in_l[2], in_l[3], in_l[4])
                                    markup_inline.add(in_l[5], in_l[6], in_l[7], in_l[8], in_l[9])

                                msg = bot.send_message(message.chat.id, text, parse_mode = 'Markdown', reply_markup = markup_inline)

                                if bd_user['language_code'] == 'ru':
                                    text = "🛒 | Возвращение в меню рынка!"
                                else:
                                    text = "🛒 | Return to the market menu!"

                                bot.send_message(message.chat.id, text, reply_markup = functions.markup(bot, 'market', user))
                                return


                        msg = bot.send_message(message.chat.id, text, reply_markup = rmk, parse_mode = 'Markdown')
                        bot.register_next_step_handler(msg, name_reg )

                if message.text in [ '🛒 Случайные товары', '🛒 Random Products']:
                    bd_user = users.find_one({"userid": user.id})
                    if bd_user != None:

                        market_ = market.find_one({"id": 1})

                        items = []

                        for usk in market_['products']:
                            if usk != str(user.id):
                                for prd in market_['products'][usk]['products']:
                                    market_['products'][usk]['products'][prd]['user'] = usk
                                    market_['products'][usk]['products'][prd]['key'] = prd
                                    items.append(market_['products'][usk]['products'][prd])

                        random.shuffle(items)

                        page = []
                        for i in items:
                            if len(page) != 10:
                                page.append(i)

                        text = ''
                        a = 0
                        markup_inline = types.InlineKeyboardMarkup()
                        in_l = []

                        if bd_user['language_code'] == 'ru':
                            text += f"🔍 | Случайные предметы с рынка >\n\n"
                            for i in page:
                                a += 1
                                text += f"*{a}#* {items_f['items'][i['item']['item_id']]['nameru']}\n     *└* Цена за 1х: {i['price']}\n         *└* Количесвто: {i['col'][1] - i['col'][0]}"

                                if 'abilities' in i['item'].keys():
                                    if 'uses' in i['item']['abilities'].keys():
                                        text += f"\n           *└* Использований: {i['item']['abilities']['uses']}"

                                    if 'endurance' in i['item']['abilities'].keys():
                                        text += f"\n           *└* Прочность: {i['item']['abilities']['endurance']}"

                                text += '\n\n'

                                in_l.append( types.InlineKeyboardButton( text = str(a) + '#', callback_data = f"market_buy_{i['user']} {i['key']}"))

                        else:
                            text += f'🔍 | Your search found {len(search_items)} item(s) >\n\n'
                            for i in page:
                                a += 1
                                text += f"*{a}#* {items_f['items'][i['item_id']]['nameen']}\n     *└* Price per 1x: {i['price']}\n         *└* Quantity: {i['col'][1] - i['col'][0]}"

                                if 'abilities' in i['item'].keys():
                                    if 'uses' in i['item']['abilities'].keys():
                                        text += f"\n           *└* Uses: {i['item']['abilities']['uses']}"

                                    if 'endurance' in i['item']['abilities'].keys():
                                        text += f"\n           *└* Endurance: {i['item']['abilities']['endurance']}"

                                text += '\n\n'

                                in_l.append( types.InlineKeyboardButton( text = str(a) + '#', callback_data = f"market_buy_{i['user']} {i['key']}"))

                        if len(in_l) == 1:
                            markup_inline.add(in_l[0])
                        if len(in_l) == 2:
                            markup_inline.add(in_l[0], in_l[1])
                        if len(in_l) == 3:
                            markup_inline.add(in_l[0], in_l[1], in_l[2])
                        if len(in_l) == 4:
                            markup_inline.add(in_l[0], in_l[1], in_l[2], in_l[3])
                        if len(in_l) == 5:
                            markup_inline.add(in_l[0], in_l[1], in_l[2], in_l[3], in_l[4])
                        if len(in_l) == 6:
                            markup_inline.add(in_l[0], in_l[1], in_l[2], in_l[3], in_l[4])
                            markup_inline.add(in_l[5])
                        if len(in_l) == 7:
                            markup_inline.add(in_l[0], in_l[1], in_l[2], in_l[3], in_l[4])
                            markup_inline.add(in_l[5], in_l[6])
                        if len(in_l) == 8:
                            markup_inline.add(in_l[0], in_l[1], in_l[2], in_l[3], in_l[4])
                            markup_inline.add(in_l[5], in_l[6], in_l[7])
                        if len(in_l) == 9:
                            markup_inline.add(in_l[0], in_l[1], in_l[2], in_l[3], in_l[4])
                            markup_inline.add(in_l[5], in_l[6], in_l[7], in_l[8])
                        if len(in_l) == 10:
                            markup_inline.add(in_l[0], in_l[1], in_l[2], in_l[3], in_l[4])
                            markup_inline.add(in_l[5], in_l[6], in_l[7], in_l[8], in_l[9])

                        msg = bot.send_message(message.chat.id, text, parse_mode = 'Markdown', reply_markup = markup_inline)

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
                    img = functions.trans_paste(fg_img, bg_img, 1.0, (i*512,0))

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

            users.insert_one({'userid': user.id, 'last_m': int(time.time()), 'dinos': {}, 'eggs': [], 'notifications': {}, 'settings': {'notifications': True, 'dino_id': '1', 'iid': 0}, 'language_code': lg, 'inventory': [], 'coins': 0, 'lvl': [1, 0], 'activ_items': { '1': {'game': None, 'hunt': None, 'journey': None, 'unv': None} }, 'friends': { 'friends_list': [], 'requests': [] } })

            markup_inline = types.InlineKeyboardMarkup()
            item_1 = types.InlineKeyboardButton( text = '🥚 1', callback_data = 'egg_answer_1')
            item_2 = types.InlineKeyboardButton( text = '🥚 2', callback_data = 'egg_answer_2')
            item_3 = types.InlineKeyboardButton( text = '🥚 3', callback_data = 'egg_answer_3')
            markup_inline.add(item_1, item_2, item_3)

            photo, id_l = photo()
            bot.send_photo(message.chat.id, photo, text, reply_markup = markup_inline)
            users.update_one( {"userid": user.id}, {"$set": {'eggs': id_l}} )

    elif call.data == 'checking_the_user_in_the_channel':
        if bot.get_chat_member(-1001673242031, user.id).status != 'left':

            if bd_user['language_code'] == 'ru':
                text = f'📜 | Уважаемый пользователь!\n\n*•* Для получения новостей и важных уведомлений по поводу бота, мы просим вас подписаться на телеграм канал бота!\n\n🟢 | Спасибо за понимание, приятного использования бота!'
            else:
                text = f"📜 | Dear user!\n\n*•* To receive news and important notifications about the bot, we ask you to subscribe to the bot's telegram channel!\n\n🟢 | Thank you for understanding, enjoy using the bot!"

            bot.edit_message_text(text, call.message.chat.id, call.message.message_id, parse_mode = 'Markdown')


    elif call.data in ['egg_answer_1', 'egg_answer_2', 'egg_answer_3']:

        if 'eggs' in list(bd_user.keys()):
            egg_n = call.data[11:]

            bd_user['dinos'][ functions.user_dino_pn(bd_user) ] = {'status': 'incubation', 'incubation_time': time.time() + 10 * 60, 'egg_id': bd_user['eggs'][int(egg_n)-1]}

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
            bot.send_message(call.message.chat.id, text2, parse_mode = 'Markdown', reply_markup = functions.markup(bot, 1, user))

    elif call.data[:13] in ['90min_journey', '60min_journey', '30min_journey', '10min_journey', '12min_journey']:

        if call.data[:13] == '12min_journey':
            jr_time = 120
        else:
            jr_time = int(call.data[:2])

        bd_user['dinos'][ call.data[14:] ]['activ_status'] = 'journey'
        bd_user['dinos'][ call.data[14:] ]['journey_time'] = time.time() + 60 * jr_time
        bd_user['dinos'][ call.data[14:] ]['journey_log'] = []
        users.update_one( {"userid": user.id}, {"$set": {'dinos': bd_user['dinos']}} )

        if bd_user['language_code'] == 'ru':
            text = f'🎈 | Если у динозавра хорошее настроение, он может принести обратно какие то вещи.\n\n🧶 | Во время путешествия, могут произойти разные ситуации, от них зависит результат путешествия.'
            text2 = f'🌳 | Вы отправили динозавра в путешествие на {jr_time} минут.'

        else:
            text = f"🎈 | If the dinosaur is in a good mood, he can bring back some things.\n\n🧶 | During the trip, different situations may occur, the result of the trip depends on them."
            text2 = f"🌳 | You sent a dinosaur on a journey for {jr_time} minutes."

        bot.edit_message_text(text2, call.message.chat.id, call.message.message_id)
        bot.send_message(call.message.chat.id, text, parse_mode = 'html', reply_markup = functions.markup(bot, "actions", user))

    elif call.data[:10] in ['1_con_game', '2_con_game', '3_con_game', '1_sna_game', '2_sna_game', '3_sna_game', '1_pin_game', '2_pin_game', '3_pin_game', '1_bal_game', '2_bal_game', '3_bal_game', '1_puz_game', '2_puz_game', '3_puz_game', '1_che_game', '2_che_game', '3_che_game', '1_jen_game', '2_jen_game', '3_jen_game', '1_ddd_game', '2_ddd_game', '3_ddd_game']:
        user = call.from_user
        bd_user = users.find_one({"userid": user.id})
        n_s = int(call.data[:1])
        dino_id = str(bd_user['settings']['dino_id'])
        if n_s == 1:
            time_m = random.randint(15, 30) * 60
        if n_s == 2:
            time_m = random.randint(30, 60) * 60
        if n_s == 3:
            time_m = random.randint(60, 90) * 60

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

        elif game == 'puz':
            game = 'puzzles'
            e_text = [ [ ['Динозавру надоело играть в пазлы...'], ['The dinosaur is tired of playing puzzles...'] ], [ ['Динозавру немного надоело играть в пазлы...'], ['The dinosaur got a little tired of playing puzzles...'] ], [ ['Динозавр довольно играет в пазлы!'], ['The dinosaur is pretty playing puzzles!'] ] ]

        elif game == 'che':
            game = 'сhess'
            e_text = [ [ ['Динозавру надоело играть в шахматы...'], ['The dinosaur is tired of playing chess...'] ], [ ['Динозавру немного надоело играть в шахматы...'], ['The dinosaur got a little tired of playing chess...'] ], [ ['Динозавр довольно играет в шахматы!'], ['Dinosaur is playing chess pretty!'] ] ]

        elif game == 'jen':
            game = 'jenga'
            e_text = [ [ ['Динозавру надоело играть в дженгу...'], ['The dinosaur is tired of playing jenga...'] ], [ ['Динозавру немного надоело играть в дженгу...'], ['The dinosaur got a little tired of playing jenga...'] ], [ ['Динозавр довольно играет в дженгу!'], ['Dinosaur is playing jenga pretty!'] ] ]

        elif game == 'ddd':
            game = 'd&d'
            e_text = [ [ ['Динозавру надоело играть в D&D...'], ['The dinosaur is tired of playing D&D...'] ], [ ['Динозавру немного надоело играть в D&D...'], ['The dinosaur got a little tired of playing D&D...'] ], [ ['Динозавр довольно играет в D&D!'], ['Dinosaur is playing D&D pretty!'] ] ]

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
                bd_user['dinos'][ dino_id ]['game_%'] = 0.9
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

            if games[2] == games[0] and games[2] == games[1]:
                bd_user['dinos'][ dino_id ]['game_%'] = 0.5

                if bd_user['language_code'] == 'ru':
                    text2 = f"🎮 | {e_text[0][0][0]}, он получает штраф {bd_user['dinos'][ dino_id ]['game_%']}% в получении удовольствия от игры!"

                else:
                    text2 = f"🎮 | {e_text[0][1][0]}, he gets a {bd_user['dinos'][ dino_id ]['game_%']}% penalty in enjoying the game!"

            if ( games[2] == games[0] and games[2] != games[1] ) or ( games[2] != games[0] and games[2] == games[1] ):
                bd_user['dinos'][ dino_id ]['game_%'] = 0.9

                if bd_user['language_code'] == 'ru':
                    text2 = f"🎮 | {e_text[1][0][0]}, он получает штраф {bd_user['dinos'][ dino_id ]['game_%']}% в получении удовольствия от игры!"

                else:
                    text2 = f"🎮 | {e_text[1][1][0]}, he gets a {bd_user['dinos'][ dino_id ]['game_%']}% penalty in enjoying the game!"

            if games[2] != games[0] and games[2] != games[1]:
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
        bot.send_message(call.message.chat.id, text, parse_mode = 'html', reply_markup = functions.markup(bot, "games", user))

    elif call.data in ['dead_answer1', 'dead_answer2', 'dead_answer3', 'dead_answer4']:

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
            text += f"{user.first_name} отдаёт: весь инвентарь, {int(mn)} монет\n"
            text += f"{user.first_name} получает: 1х яйцо динозавра"
            markup_inline.add( types.InlineKeyboardButton(text= '✒ Подписать', callback_data = 'dead_restart') )
        else:
            text += "\n\n\n"
            text += "     *Contract*\n"
            text += f"{user.first_name} gives: all inventory, {int(mn)} coins\n"
            text += f"{user.first_name} receives: 1x dinosaur egg"
            markup_inline.add( types.InlineKeyboardButton(text= '✒ Sign', callback_data = 'dead_restart') )

        bd_user['notifications']['ans_dead'] = int(mn)
        users.update_one( {"userid": user.id}, {"$set": {'notifications': bd_user['notifications']}} )

        try:
            bot.edit_message_text(text, call.message.chat.id, call.message.message_id, reply_markup = markup_inline, parse_mode = 'Markdown')
        except:
            bot.send_message(call.message.chat.id, text, reply_markup = markup_inline, parse_mode = 'Markdown')

    elif call.data == 'dead_restart':
        user = call.from_user
        bd_user = users.find_one({"userid": user.id})

        if bd_user != None and len(bd_user['dinos']) == 0 and functions.inv_egg(bd_user) == False and bd_user['lvl'][0] < 5:
            egg_n = str(random.choice(list(json_f['data']['egg'])))

            bd_user['dinos'][ functions.user_dino_pn(bd_user) ] = {'status': 'incubation', 'incubation_time': time.time() + 30 * 60, 'egg_id': egg_n}
            bd_user['coins'] -= int(bd_user['notifications']['ans_dead'])
            try:
                del bd_user['notifications']['ans_dead']
                del bd_user['notifications']['1']
            except:
                pass

            users.update_one( {"userid": user.id}, {"$set": {'dinos': bd_user['dinos']}} )
            users.update_one( {"userid": user.id}, {"$set": {'notifications': bd_user['notifications']}} )
            users.update_one( {"userid": user.id}, {"$set": {'coins': bd_user['coins']}} )
            users.update_one( {"userid": user.id}, {"$set": {'inventory': [] }} )

            bd_user = users.find_one({"userid": user.id})


            if bd_user['language_code'] == 'ru':
                text = '✒ | Контракт подписан, динозавр инкубируется.'
            else:
                text = '✒ | The contract is signed, the dinosaur is incubating.'

            bot.send_message(user.id, text, parse_mode = 'Markdown', reply_markup = functions.markup(bot, 1, user))

    elif call.data[:5] == 'item_':

        data = functions.des_qr(str(call.data[5:]))
        it_id = str(data['id'])
        list_inv = list(bd_user['inventory'])
        list_inv_id = []
        check_n = 0
        dino_id = 1
        col = 1

        for i in list_inv: list_inv_id.append(i['item_id'])

        def n_c_f():
            nonlocal check_n
            check_n += 1

        def re_item():
            nonlocal check_n, data_item

            if check_n == 1:

                if data_item['type'] == '+heal':
                    ans_dino()

                elif data_item['type'] == '+unv':
                    ans_dino()

                elif data_item['type'] == 'recipe':
                    ans_col()

                elif data_item['type'] == '+eat':
                    ans_dino()

                elif data_item['type'] in ['game_ac', "journey_ac", "hunt_ac", "unv_ac"]:
                    ans_dino()

                elif data_item['type'] == 'egg':
                    use_item()

            elif check_n == 2:

                if data_item['type'] == '+heal':
                    ans_col()

                if data_item['type'] == '+unv':
                    ans_col()

                elif data_item['type'] == 'recipe':
                    use_item()

                elif data_item['type'] == '+eat':
                    ans_col()

                elif data_item['type'] in ['game_ac', "journey_ac", "hunt_ac", "unv_ac"]:
                    use_item()

            elif check_n == 3:

                if data_item['type'] == '+heal':
                    use_item()

                elif data_item['type'] == '+unv':
                    use_item()

                elif data_item['type'] == '+eat':
                    use_item()

        def ans_dino():
            global dino_id

            def dino_reg(message, dino_dict):
                global dino_id
                if message.text in dino_dict.keys():
                    dino_id = dino_dict[message.text][1]
                    n_c_f(), re_item()

                else:
                    bot.send_message(user.id, f'❌', reply_markup = functions.markup(bot, functions.last_markup(bd_user, alternative = 'profile'), bd_user ))

            n_dp, dp_a = functions.dino_pre_answer(bot, call, 'noall')

            if n_dp == 1: #нет дино

                if functions.inv_egg(bd_user) == True and data_item['type'] == 'egg':
                    n_c_f(), re_item()

                else:
                    bot.send_message(user.id, f'❌', reply_markup = functions.markup(bot, functions.last_markup(bd_user, alternative = 1), bd_user ))

            if n_dp == 2: # 1 дино
                dino_dict = [dp_a, list(bd_user['dinos'].keys())[0] ]
                dino_id = list(bd_user['dinos'].keys())[0]
                n_c_f(), re_item()

            if n_dp == 3: # 2 и более
                rmk = dp_a[0]
                text = dp_a[1]
                dino_dict = dp_a[2]

                msg = bot.send_message(user.id, text, reply_markup = rmk)
                bot.register_next_step_handler(msg, dino_reg, dino_dict)

        def use_item():
            global col, dino_id
            fr_user = users.find_one({"userid": user.id})

            use_st = True

            if data_item['type'] == '+heal':

                if bd_user['language_code'] == 'ru':
                    text = f'❤ | Вы восстановили {data_item["act"] * col}% здоровья динозавра!'
                else:
                    text = f"❤ | You have restored {data_item['act'] * col}% of the dinosaur's health!"

                users.update_one( {"userid": user.id}, {"$inc": {f'dinos.{dino_id}.stats.heal': data_item['act'] * col }} )

            elif data_item['type'] == '+unv':

                if bd_user['language_code'] == 'ru':
                    text = f'⚡ | Вы восстановили {data_item["act"] * col}% энергии динозавра!'
                else:
                    text = f"⚡ | You have recovered {data_item['act'] * col}% of the dinosaur's energy!"

                users.update_one( {"userid": user.id}, {"$inc": {f'dinos.{dino_id}.stats.unv': data_item['act'] * col }} )

            elif data_item['type'] == 'recipe':
                ok = True

                for _ in range(col):
                    for i in data_item['materials']:
                        if i in list_inv_id:
                            try:
                                fr_user['inventory'].remove( fr_user['inventory'][list_inv_id.index(i)] )
                            except:
                                ok = False
                                break
                        else:
                            ok = False
                            break

                if ok == True:

                    if bd_user['language_code'] == 'ru':
                        text = f'🍡 | Предмет {data_item["nameru"]} x{col} создан!'
                    else:
                        text = f"🍡 | The item {data_item['nameen']} x{col} is created!"

                    fr_user = users.find_one({"userid": user.id})

                    for _ in range(col):
                        for i in data_item['materials']:
                            if i not in data_item['create']:
                                lst_ind = list_inv_id.index(i)

                                fr_user['inventory'].remove( fr_user['inventory'][lst_ind] )

                    res = users.update_one( {"userid": user.id}, {"$set": {'inventory': fr_user['inventory'] }} )

                    for i in data_item['create']:
                        if i not in data_item['materials']:
                            ok = functions.add_item_to_user(fr_user, i, col)

                else:

                    if bd_user['language_code'] == 'ru':
                        text = f'❗ | Материалов недостаточно!'
                    else:
                        text = f"❗ | Materials are not enough!"

                    use_st = False

            elif data_item['type'] == '+eat':
                d_dino = json_f['elements'][ str(bd_user['dinos'][dino_id]['dino_id']) ]

                if bd_user['language_code'] == 'ru':
                    if data_item['class'] == 'ALL':

                        bd_user['dinos'][ dino_id ]['stats']['eat'] += data_item['act'] * col

                        if bd_user['dinos'][ dino_id ]['stats']['eat'] > 100:
                            bd_user['dinos'][ dino_id ]['stats']['eat'] = 100

                        text = f"🍕 | Динозавр с удовольствием съел {data_item['nameru']}!\nДинозавр сыт на {bd_user['dinos'][ dino_id ]['stats']['eat']}%"


                    elif data_item['class'] == d_dino['class']:
                        bd_user['dinos'][ dino_id ]['stats']['eat'] += data_item['act'] * col

                        if bd_user['dinos'][ dino_id ]['stats']['eat'] > 100:
                            bd_user['dinos'][ dino_id ]['stats']['eat'] = 100

                        text = f"🍕 | Динозавр с удовольствием съел {data_item['nameru']}!\nДинозавр сыт на {bd_user['dinos'][ dino_id ]['stats']['eat']}%"


                    else:
                        eatr = random.randint( 0, int(data_item['act'] / 2) )
                        moodr = random.randint( 1, 10 )
                        text = f"🍕 | Динозавру не по вкусу {data_item['nameru']}, он теряет {eatr}% сытости и {moodr}% настроения!"

                        bd_user['dinos'][ dino_id ]['stats']['eat'] -= eatr
                        bd_user['dinos'][ dino_id ]['stats']['mood'] -= moodr

                else:
                    if data_item['class'] == 'ALL':

                        bd_user['dinos'][ dino_id ]['stats']['eat'] += data_item['act'] * col

                        if bd_user['dinos'][ dino_id ]['stats']['eat'] > 100:
                            bd_user['dinos'][ dino_id ]['stats']['eat'] = 100

                        text = f"🍕 | The dinosaur ate it with pleasure {data_item['nameen']}!\nThe dinosaur is fed up on {bd_user['dinos'][ dino_id ]['stats']['eat']}%"

                    elif data_item['class'] == d_dino['class']:

                        bd_user['dinos'][ dino_id ]['stats']['eat'] += data_item['act'] * col

                        if bd_user['dinos'][ dino_id ]['stats']['eat'] > 100:
                            bd_user['dinos'][ dino_id ]['stats']['eat'] = 100

                        text = f"🍕 | The dinosaur ate it with pleasure {data_item['nameen']}!\nThe dinosaur is fed up on {bd_user['dinos'][ dino_id ]['stats']['eat']}%"

                    else:
                        eatr = random.randint( 0, int(data_item['act'] / 2) )
                        moodr = random.randint( 1, 10 )
                        text = f"🍕 | The dinosaur doesn't like {data_item['nameen']}, it loses {eatr}% satiety and {mood}% mood!"

                        bd_user['dinos'][ dino_id ]['stats']['eat'] -= eatr
                        bd_user['dinos'][ dino_id ]['stats']['mood'] -= moodr

                users.update_one( {"userid": bd_user['userid']}, {"$set": {f'dinos.{dino_id}': bd_user['dinos'][ dino_id ] }} )

            elif data_item['type'] in ['game_ac', "journey_ac", "hunt_ac", "unv_ac"]:
                ac_type = data_item['type'][:-3]

                if bd_user['activ_items'][ dino_id ][ac_type] != None:
                    bd_user['inventory'].append(bd_user['activ_items'][ dino_id ][ac_type])

                bd_user['activ_items'][ dino_id ][ac_type] = user_item

                if bd_user['language_code'] == 'ru':
                    text = "🎴 | Активный предмет установлен!"
                else:
                    text = "🎴 | The active item is installed!"

                users.update_one( {"userid": bd_user['userid']}, {"$set": {'activ_items': bd_user['activ_items'] }} )

            elif data_item['type'] == 'egg':

                if bd_user['lvl'][0] < 20 and len(bd_user['dinos']) != 0:

                    if bd_user['language_code'] == 'ru':
                        text = f'🔔 | Вам недоступна данная технология!'
                    else:
                        text = f"🔔 | This technology is not available to you!"

                    use_st = False

                else:
                    if int(bd_user['lvl'][0] / 20 + 1) > len(bd_user['dinos']):

                        if data_item['time_tag'] == 'h':
                            inc_time = time.time() + data_item['incub_time'] * 3600

                        if data_item['time_tag'] == 'm':
                            inc_time = time.time() + data_item['incub_time'] * 60

                        if data_item['time_tag'] == 's':
                            inc_time = time.time() + data_item['incub_time']

                        egg_n = str(random.choice(list(json_f['data']['egg'])))

                        bd_user['dinos'][ functions.user_dino_pn(bd_user) ] = {'status': 'incubation', 'incubation_time': inc_time, 'egg_id': egg_n, 'quality': data_item['inc_type']}

                        users.update_one( {"userid": user.id}, {"$set": {'dinos': bd_user['dinos']}} )


                        if bd_user['language_code'] == 'ru':
                            text = f'🥚 | Яйцо отправлено на инкубацию!'
                        else:
                            text = f"🥚 | The egg has been sent for incubation!"

                    else:
                        if bd_user['language_code'] == 'ru':
                            text = f"🔔 | Вам доступна только {int(bd_user['lvl'][0] / 20)} динозавров!"
                        else:
                            text = f"🔔 | Only {int(bd_user['lvl'][0] / 20)} dinosaurs are available to you!"

                        use_st = False

            else:

                if bd_user['language_code'] == 'ru':
                    text = f'❗ | Данный предмет пока что недоступен для использования!'
                else:
                    text = f"❗ | This item is not yet available for use!"

                use_st = False


            if '+mood' in data_item.keys():
                users.update_one( {"userid": user.id}, {"$inc": {f'dinos.{dino_id}.stats.mood': data_item['+mood'] * col }} )

            if '-mood' in data_item.keys():
                users.update_one( {"userid": user.id}, {"$inc": {f'dinos.{dino_id}.stats.mood': (data_item['-mood'] * -1) * col }} )

            if '-eat' in data_item.keys():
                users.update_one( {"userid": user.id}, {"$inc": {f'dinos.{dino_id}.stats.eat': (data_item['-eat'] * -1) * col }} )

            if 'abilities' in user_item.keys():
                if 'uses' in user_item['abilities'].keys():
                    if use_st == True:

                        if user_item['abilities']['uses'] != -100:

                            s_col = user_item['abilities']['uses'] - col

                            if s_col > 0:
                                users.update_one( {"userid": user.id}, {"$set": {f'inventory.{fr_user["inventory"].index(user_item)}.abilities.uses': user_item['abilities']['uses'] - col}} )

                            else:
                                fr_user['inventory'].remove(user_item)
                                users.update_one( {"userid": user.id}, {"$set": {'inventory': fr_user['inventory'] }} )

            else:

                if use_st == True:
                    try:
                        for _ in range(col):
                            fr_user['inventory'].remove(user_item)
                    except:
                        fr_user['inventory'].remove(user_item)

                    users.update_one( {"userid": user.id}, {"$set": {'inventory': fr_user['inventory'] }} )


            bot.send_message(user.id, text, parse_mode = 'Markdown', reply_markup = functions.markup(bot, functions.last_markup(bd_user, alternative = 'profile'), bd_user ))

        def ent_col(message, col_l, mx_col):
            global col

            if message.text in ['↩️ Назад', '↩️ Back']:

                if bd_user['language_code'] == 'ru':
                    text = f"🎈 | Отмена использования!"
                else:
                    text = f"🎈 | Cancellation of use!"

                bot.send_message(message.chat.id, text, reply_markup = functions.markup(bot, functions.last_markup(bd_user, alternative = 'profile'), bd_user ))
                return

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

                    bot.send_message(message.chat.id, text, reply_markup = functions.markup(bot, functions.last_markup(bd_user, alternative = 'profile'), bd_user ))
                    return

            if col > mx_col:

                if bd_user['language_code'] == 'ru':
                    text = f"У вас нет столько предметов в инвентаре!"
                else:
                    text = f"You don't have that many items in your inventory!"

                bot.send_message(message.chat.id, text, reply_markup = functions.markup(bot, functions.last_markup(bd_user, alternative = 'profile'), bd_user ))
                return

            else:
                n_c_f(), re_item()

        def ans_col():

            col = 1
            mx_col = 0

            if 'abilities' in user_item.keys() and 'uses' in user_item['abilities'].keys():
                mx_col = user_item['abilities']['uses']

            else:
                mx_col = list_inv.count(user_item)

            if mx_col == 1:
                call.message.text = '1'
                ent_col(call.message, [[], []], mx_col)

            else:

                if bd_user['language_code'] == 'ru':
                    text_col = f"🕹 | Введите сколько вы хотите использовать или выберите из списка >"
                else:
                    text_col = f"🕹 | Enter how much you want to use or select from the list >"

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

                msg = bot.send_message(user.id, text_col, reply_markup = rmk)
                bot.register_next_step_handler(msg, ent_col, col_l, mx_col)

        if it_id in list_inv_id:
            data_item = items_f['items'][it_id]

            user_item = None
            if list(set(['abilities']) & set(list(data_item.keys()))) != []:

                abl_it = {}
                for i in data.keys(): abl_it[i] = data[i]
                del abl_it['id']

                for it in list_inv:
                    if user_item == None:
                        if str(it['item_id']) == str(it_id):
                            if 'abilities' in it.keys():
                                for key_c in data.keys():
                                    if key_c != 'id':
                                        if it['abilities'] == abl_it:
                                            user_item = it
                                            break

            else:
                user_item = list_inv[list_inv_id.index(it_id)]

            if user_item == None:

                if bd_user['language_code'] == 'ru':
                    text = f'❌ | Предмет не найден в инвентаре!'
                else:
                    text = f"❌ | Item not found in inventory!"

                bot.send_message(user.id, text, parse_mode = 'Markdown')

            if user_item != None:
                n_c_f(), re_item()



    elif call.data[:12] == 'remove_item_':
        data = functions.des_qr(str(call.data[12:]))

        it_id = str(data['id'])
        list_inv = list(bd_user['inventory'])
        list_inv_id = []
        for i in list_inv: list_inv_id.append(i['item_id'])

        if it_id in list_inv_id:
            data_item = items_f['items'][it_id]

            user_item = None
            if list(set(['abilities']) & set(list(data_item.keys()))) != []:

                abl_it = {}
                for i in data.keys(): abl_it[i] = data[i]
                del abl_it['id']

                for it in list_inv:
                    if user_item == None:
                        if str(it['item_id']) == str(it_id):
                            if 'abilities' in it.keys():
                                for key_c in data.keys():
                                    if key_c != 'id':
                                        if it['abilities'] == abl_it:
                                            user_item = it
                                            break

            else:
                user_item = list_inv[list_inv_id.index(it_id)]

            if user_item == None:

                if bd_user['language_code'] == 'ru':
                    text = f'❌ | Предмет не найден в инвентаре!'
                else:
                    text = f"❌ | Item not found in inventory!"

                bot.send_message(user.id, text, parse_mode = 'Markdown')

            if user_item != None:

                if bd_user['language_code'] == 'ru':
                    text = '🗑 | Вы уверены что хотите удалить данный предмет?'
                    in_text = ['✔ Удалить', '❌ Отмена']
                else:
                    text = '🗑 | Are you sure you want to delete this item?'
                    in_text = ['✔ Delete', '❌ Cancel']

                markup_inline = types.InlineKeyboardMarkup()
                markup_inline.add( types.InlineKeyboardButton( text = in_text[0], callback_data = f"remove_{functions.qr_item_code(user_item)}"),  types.InlineKeyboardButton( text = in_text[1], callback_data = f"cancel_remove") )

                bot.send_message(user.id, text, reply_markup = markup_inline)

    elif call.data[:7] == 'remove_':
        data = functions.des_qr(str(call.data[7:]))

        it_id = str(data['id'])
        list_inv = list(bd_user['inventory'])
        list_inv_id = []
        for i in list_inv: list_inv_id.append(i['item_id'])

        if it_id in list_inv_id:
            data_item = items_f['items'][it_id]

            user_item = None
            if list(set(['abilities']) & set(list(data_item.keys()))) != []:

                abl_it = {}
                for i in data.keys(): abl_it[i] = data[i]
                del abl_it['id']

                for it in list_inv:
                    if user_item == None:
                        if str(it['item_id']) == str(it_id):
                            if 'abilities' in it.keys():
                                for key_c in data.keys():
                                    if key_c != 'id':
                                        if it['abilities'] == abl_it:
                                            user_item = it
                                            break

            else:
                user_item = list_inv[list_inv_id.index(it_id)]

            if user_item == None:

                if bd_user['language_code'] == 'ru':
                    text = f'❌ | Предмет не найден в инвентаре!'
                else:
                    text = f"❌ | Item not found in inventory!"

                bot.send_message(user.id, text, parse_mode = 'Markdown')

            if user_item != None:
                col = 1
                mx_col = 0
                for item_c in bd_user['inventory']:
                    if item_c == user_item:
                        mx_col += 1

                bot.delete_message(user.id, call.message.message_id)

                if bd_user['language_code'] == 'ru':
                    text_col = f"🗑 | Введите какое количество предметов вы хотите удалить или выберите из списка >"
                else:
                    text_col = f"🗑 | Enter how many items you want to remove or select from the list >"

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


                def tr_complete(message, bd_user, user_item, mx_col, col_l):

                    if message.text in ['↩ Back', '↩ Назад']:

                        if bd_user['language_code'] == 'ru':
                            text = "👥 | Возвращение в меню активностей!"
                        else:
                            text = "👥 | Return to the friends menu!"

                        bot.send_message(message.chat.id, text, reply_markup = functions.markup(bot, 'actions', user))
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

                            bot.send_message(message.chat.id, text, reply_markup = functions.markup(bot, 'actions', user))
                            return

                    if col > mx_col:

                        if bd_user['language_code'] == 'ru':
                            text = f"У вас нет столько предметов в инвентаре!"
                        else:
                            text = f"You don't have that many items in your inventory!"

                        bot.send_message(message.chat.id, text, reply_markup = functions.markup(bot, 'actions', user))
                        return

                    for i in range(col):
                        bd_user['inventory'].remove(user_item)

                    users.update_one( {"userid": user.id}, {"$set": {f'inventory': bd_user['inventory'] }} )

                    if bd_user['language_code'] == 'ru':
                        text = '🗑 | Предмет удалён.'
                    else:
                        text = '🗑 | The item has been deleted.'

                    bot.send_message(message.chat.id, text, reply_markup = functions.markup(bot, 'profile', user))

                msg = bot.send_message(user.id, text_col, reply_markup = rmk)
                bot.register_next_step_handler(msg, tr_complete, bd_user, user_item, mx_col, col_l)


    elif call.data == "cancel_remove":
        bot.delete_message(user.id, call.message.message_id)

    elif call.data[:9] == 'exchange_':

        data = functions.des_qr(str(call.data[9:]))

        it_id = str(data['id'])
        list_inv = list(bd_user['inventory'])
        list_inv_id = []
        for i in list_inv: list_inv_id.append(i['item_id'])

        if it_id in list_inv_id:
            data_item = items_f['items'][it_id]

            user_item = None
            if list(set(['abilities']) & set(list(data_item.keys()))) != []:

                abl_it = {}
                for i in data.keys(): abl_it[i] = data[i]
                del abl_it['id']

                for it in list_inv:
                    if user_item == None:
                        if str(it['item_id']) == str(it_id):
                            if 'abilities' in it.keys():
                                for key_c in data.keys():
                                    if key_c != 'id':
                                        if it['abilities'] == abl_it:
                                            user_item = it
                                            break

            else:
                user_item = list_inv[list_inv_id.index(it_id)]

            if user_item == None:

                if bd_user['language_code'] == 'ru':
                    text = f'❌ | Предмет не найден в инвентаре!'
                else:
                    text = f"❌ | Item not found in inventory!"

                bot.send_message(user.id, text, parse_mode = 'Markdown')

            if user_item != None:

                functions.exchange(bot, call.message, user_item, bd_user)

    elif call.data[:11] == 'market_buy_':
        m_call = call.data.split()

        market_ = market.find_one({"id": 1})
        us_id = m_call[0][11:]
        key_i = m_call[1]

        if str(us_id) in market_['products'].keys():
            ma_d = market_['products'][str(us_id)]['products']

            if str(key_i) in ma_d.keys():
                mmd = market_['products'][str(us_id)]['products'][str(key_i)]

                if mmd['price'] <= bd_user['coins']:

                    def reg0(message, mmd, us_id, key_i):

                        def reg(message, mmd, us_id, key_i):

                            try:
                                number = int(message.text)
                            except:

                                if bd_user['language_code'] == 'ru':
                                    text = "🛒 | Возвращение в меню рынка!"
                                else:
                                    text = "🛒 | Return to the market menu!"

                                bot.send_message(message.chat.id, text, reply_markup = functions.markup(bot, 'market', user))
                                return

                            if number <= 0 or number > mmd['col'][1] - mmd['col'][0]:

                                if bd_user['language_code'] == 'ru':
                                    text = "🛒 | На рынке нет такого количества предмета!"
                                else:
                                    text = "🛒 | There is no such amount of item on the market!"

                                bot.send_message(message.chat.id, text, reply_markup = functions.markup(bot, 'market', user))
                                return

                            mr_user = users.find_one({"userid": us_id})

                            if mmd['price'] * number > bd_user['coins']:
                                if bd_user['language_code'] == 'ru':
                                    text = "🛒 | У вас нет столько монет!"
                                else:
                                    text = "🛒 | You don't have that many coins!"

                                bot.send_message(message.chat.id, text, reply_markup = functions.markup(bot, 'market', user))
                                return

                            for i in range(number):
                                bd_user['inventory'].append(mmd['item'])

                            if mr_user != None:
                                users.update_one( {"userid": us_id}, {"$inc": {'coins': mmd['price'] * number }} )

                            market_['products'][str(us_id)]['products'][str(key_i)]['col'][0] += number

                            if market_['products'][str(us_id)]['products'][str(key_i)]['col'][0] >= market_['products'][str(us_id)]['products'][str(key_i)]['col'][1]:
                                del market_['products'][str(us_id)]['products'][str(key_i)]


                            market.update_one( {"id": 1}, {"$set": {'products': market_['products'] }} )
                            users.update_one( {"userid": user.id}, {"$set": {'inventory': bd_user['inventory']}} )
                            users.update_one( {"userid": user.id}, {"$inc": {'coins': (mmd['price'] * number) * -1 }} )

                            if bd_user['language_code'] == 'ru':
                                text = "🛒 | Товар был куплен!"
                            else:
                                text = "🛒 | The product was purchased!"

                            bot.send_message(call.message.chat.id, text, reply_markup = functions.markup(bot, 'market', user))

                        if message.text in [f"Yes, purchase {items_f['items'][mmd['item']['item_id']]['nameru']}", f"Да, приобрести {items_f['items'][mmd['item']['item_id']]['nameru']}"]:
                            pass

                        elif message.text in [ '🛒 Рынок', '🛒 Market' ]:

                            if bd_user['language_code'] == 'ru':
                                text = "🛒 | Возвращение в меню рынка!"
                            else:
                                text = "🛒 | Return to the market menu!"

                            bot.send_message(message.chat.id, text, reply_markup = functions.markup(bot, 'market', user))
                            return

                        else:

                            if bd_user['language_code'] == 'ru':
                                text = "🛒 | Возвращение в меню рынка!"
                            else:
                                text = "🛒 | Return to the market menu!"

                            bot.send_message(message.chat.id, text, reply_markup = functions.markup(bot, 'market', user))
                            return


                        if bd_user['language_code'] == 'ru':
                            text = f"🛒 | Укажите сколько вы хотите купить >\nВведите число от {1} до {mmd['col'][1] - mmd['col'][0] }"
                            ans = ['🛒 Рынок']
                        else:
                            text = f"🛒 | Specify how much you want to buy >\enter a number from {1} to {mmd['col'][1] - mmd['col'][0] }"
                            ans = ['🛒 Market']

                        rmk = types.ReplyKeyboardMarkup(resize_keyboard = True, row_width = 1)
                        rmk.add(ans[0])

                        msg = bot.send_message(message.chat.id, text, reply_markup = rmk, parse_mode = 'Markdown')
                        bot.register_next_step_handler(msg, reg, mmd, us_id, key_i)

                    if bd_user['language_code'] == 'ru':
                        text = f"🛒 | Вы уверены что вы хотите купить {items_f['items'][mmd['item']['item_id']]['nameru']}?"
                        ans = [f"Да, приобрести {items_f['items'][mmd['item']['item_id']]['nameru']}", '🛒 Рынок']
                    else:
                        text = f"🛒 | Are you sure you want to buy {items_f['items'][mmd['item']['item_id']]['nameen']}?"
                        ans = [f"Yes, purchase {items_f['items'][mmd['item']['item_id']]['nameru']}", '🛒 Market']

                    rmk = types.ReplyKeyboardMarkup(resize_keyboard = True, row_width = 1)
                    rmk.add(ans[0], ans[1])

                    msg = bot.send_message(call.message.chat.id, text, reply_markup = rmk, parse_mode = 'Markdown')
                    bot.register_next_step_handler(msg, reg0, mmd, us_id, key_i)

                else:
                    if bd_user['language_code'] == 'ru':
                        text = "🛒 | У вас не хватает монет для покупки!"
                    else:
                        text = "🛒 | You don't have enough coins to buy!"

                    bot.send_message(call.message.chat.id, text)

            else:
                if bd_user['language_code'] == 'ru':
                    text = "🛒 | Предмет не найден на рынке, возможно он уже был куплен."
                else:
                    text = "🛒 | The item was not found on the market, it may have already been purchased."

                bot.send_message(call.message.chat.id, text)

        else:
            if bd_user['language_code'] == 'ru':
                text = "🛒 | Предмет не найден на рынке, возможно он уже был куплен."
            else:
                text = "🛒 | The item was not found on the market, it may have already been purchased."

            bot.send_message(call.message.chat.id, text)

    elif call.data[:7] == 'market_':
        m_call = call.data.split()

        market_ = market.find_one({"id": 1})
        us_id = m_call[0][7:]
        key_i = m_call[1]

        if str(us_id) in market_['products'].keys():
            ma_d = market_['products'][str(us_id)]['products']

            if str(key_i) in ma_d.keys():
                mmd = market_['products'][str(us_id)]['products'][str(key_i)]

            else:
                if bd_user['language_code'] == 'ru':
                    text = "🛒 | Предмет не найден на рынке, возможно он уже был куплен."
                else:
                    text = "🛒 | The item was not found on the market, it may have already been purchased."

                bot.send_message(call.message.chat.id, text)

        else:
            if bd_user['language_code'] == 'ru':
                text = "🛒 | Предмет не найден на рынке, возможно он уже был куплен."
            else:
                text = "🛒 | The item was not found on the market, it may have already been purchased."

            bot.send_message(call.message.chat.id, text)


    elif call.data[:9] == 'iteminfo_':

        item = functions.get_dict_item(call.data[9:])
        text= functions.item_info(item, bd_user['language_code'])

        bot.send_message(call.message.chat.id, text, parse_mode = 'Markdown')

    elif call.data == 'inventory':

        functions.user_inventory(bot, user, call.message)

    elif call.data == 'requests':

        functions.user_requests(bot, user, call.message)

    elif call.data == 'send_request':
        fr_user = call.message.reply_to_message.from_user

        if bd_user != None:
            two_user = users.find_one({"userid": fr_user.id })
            if two_user != None:
                if bd_user['userid'] != two_user['userid']:

                    if bd_user['userid'] not in two_user['friends']['requests'] and bd_user['userid'] not in two_user['friends']['friends_list'] and two_user['userid'] not in bd_user['friends']['requests']:

                        two_user['friends']['requests'].append(bd_user['userid'])
                        users.update_one( {"userid": two_user['userid']}, {"$set": {'friends': two_user['friends'] }} )

                        if bd_user['language_code'] == 'ru':
                            text = f"🎀 | {user.first_name} отправил запрос в друзья пользователю <a href='tg://user?id={fr_user.id}'>🌀 {fr_user.first_name}</a>"
                        else:
                            text = f"🎀 | {user.first_name} sent a friend request to the user <a href='tg://user?id={fr_user.id }'>🌀 {fr_user.first_name}</a>"

                        bot.reply_to(call.message, text, parse_mode = 'HTML')

    elif call.data[:18] == 'open_dino_profile_':
        did = call.data[18:]
        bd_dino = bd_user['dinos'][did]
        functions.p_profile(bot, call.message, bd_dino, user, bd_user, did)

    else:
        print(call.data, 'call.data')


print(f'Бот {bot.get_me().first_name} запущен!')
if bot.get_me().first_name == 'DinoGochi' or False:
    main_checks.start() # активация всех проверок и игрового процесса
    thr_notif.start() # активация уведомлений
    min10_thr.start() # пяти-минутный чек

bot.infinity_polling()
