import logging
import pprint
import random
import threading
import time

import telebot
from memory_profiler import memory_usage
from telebot import types

import config
import json
from mods.call_data import CallData
from mods.checks import Checks
from mods.classes import Dungeon, Functions
from mods.commands import Commands

bot = telebot.TeleBot(config.BOT_TOKEN)
client = config.CLUSTER_CLIENT
users, management, dungeons = client.bot.users, client.bot.management, client.bot.dungeons

with open('json/items.json', encoding='utf-8') as f: items_f = json.load(f)


class SpamStop(telebot.custom_filters.AdvancedCustomFilter):
    key = 'spam_check'

    @staticmethod
    def check(message, text):
        user = message.from_user

        if Functions.spam_stop(user.id) == False:
            try:
                bot.delete_message(user.id, message.message_id)
            except:
                pass

            return False

        else:
            return True


class WC(telebot.custom_filters.AdvancedCustomFilter):
    key = 'wait_callback'

    @staticmethod
    def check(call, trt):
        return Functions.callback_spam_stop(call.from_user.id)


class In_Dungeon(telebot.custom_filters.AdvancedCustomFilter):
    key = 'in_dungeon'

    @staticmethod
    def check(message, text):

        if message.chat.type == 'private':

            user = message.from_user
            otv = Functions.check_in_dungeon(bot, user.id)

            if otv:
                text = Functions.get_text(user.language_code, "no_use_interface")
                bot.reply_to(message, text)
                return False

            else:
                return True


def check():  # проверка каждые 10 секунд

    def alpha(bot, members):
        Checks.main(bot, members)

    def beta(bot, members):
        Checks.main_hunting(bot, members)

    def beta2(bot, members):
        Checks.main_game(bot, members)

    def gamma(bot, members):
        Checks.main_sleep(bot, members)

    def gamma2(bot, members):
        Checks.main_pass(bot, members)

    def delta(bot, members):
        Checks.main_journey(bot, members)

    while True:
        if int(memory_usage()[0]) < 1500:
            st_r_time = int(time.time())
            non_members = users.find({})
            chunks_users = list(Functions.chunks(list(non_members), 50))
            sl_time = 10 - (int(time.time()) - st_r_time)
            Functions.check_data('col', None, int(len(chunks_users)))

            if sl_time < 0:
                sl_time = 0
                print(f'WARNING: sleep time: {sl_time}, time sleep skip to {sl_time}')
                logging.warning(f'sleep time: {sl_time}, time sleep skip to {sl_time}')

            for members in chunks_users:
                threading.Thread(target=alpha, daemon=True, kwargs={'bot': bot, 'members': members}).start()
                threading.Thread(target=beta, daemon=True, kwargs={'bot': bot, 'members': members}).start()
                threading.Thread(target=beta2, daemon=True, kwargs={'bot': bot, 'members': members}).start()
                threading.Thread(target=gamma, daemon=True, kwargs={'bot': bot, 'members': members}).start()
                threading.Thread(target=gamma2, daemon=True, kwargs={'bot': bot, 'members': members}).start()
                threading.Thread(target=delta, daemon=True, kwargs={'bot': bot, 'members': members}).start()

        else:
            print(f'Использование памяти: {int(memory_usage()[0])}')
            logging.warning(f'Использование памяти: {int(memory_usage()[0])}')

        time.sleep(sl_time)


main_checks = threading.Thread(target=check, daemon=True)


def check_notif():  # проверка каждые 5 секунд

    def alpha(bot, members):
        Checks.check_notif(bot, members)

    def beta(bot):
        Checks.check_incub(bot)

    def memory():
        Checks.check_memory()

    while True:

        if int(memory_usage()[0]) < 1500:
            non_members = users.find({})
            chunks_users = list(Functions.chunks(list(non_members), 50))

            for members in chunks_users:
                threading.Thread(target=alpha, daemon=True, kwargs={'bot': bot, 'members': members}).start()

            threading.Thread(target=beta, daemon=True, kwargs={'bot': bot}).start()

            threading.Thread(target=memory, daemon=True).start()

        else:
            print(f'Использование памяти: {int(memory_usage()[0])}')
            logging.warning(f'Использование памяти: {int(memory_usage()[0])}')

        time.sleep(5)


thr_notif = threading.Thread(target=check_notif, daemon=True)


def min10_check():  # проверка каждые 10 мин

    def alpha(users):
        Checks.rayt(users)

    def dead_users(bot):
        Checks.check_dead_users(bot)

    def dng_check(bot):
        Checks.dungeons_check(bot)

    def events_check(bot):
        Checks.events(bot)

    while True:

        if int(memory_usage()[0]) < 1500:
            uss = users.find({})
            threading.Thread(target=alpha, daemon=True, kwargs={'users': uss}).start()

            threading.Thread(target=dead_users, daemon=True, kwargs={'bot': bot}).start()
            threading.Thread(target=dng_check, daemon=True, kwargs={'bot': bot}).start()
            threading.Thread(target=events_check, daemon=True, kwargs={'bot': bot}).start()

        else:
            print(f'Использование памяти: {int(memory_usage()[0])}')
            logging.warning(f'Использование памяти: {int(memory_usage()[0])}')

        time.sleep(600)


min10_thr = threading.Thread(target=min10_check, daemon=True)


def min1_check():  # проверка каждую минуту

    def alpha(bot):
        Checks.quests(bot)

    while True:
        time.sleep(60)

        if int(memory_usage()[0]) < 1500:

            if bot.get_me().first_name == config.BOT_NAME:
                threading.Thread(target=alpha, daemon=True, kwargs={'bot': bot}).start()

        else:
            print(f'Использование памяти: {int(memory_usage()[0])}')
            logging.warning(f'Использование памяти: {int(memory_usage()[0])}')


min1_thr = threading.Thread(target=min1_check, daemon=True)


@bot.message_handler(commands=['stats'])
def command(message):
    user = message.from_user
    checks_data = Functions.check_data(m='check')

    def ttx(tm, lst):
        lgs = []
        for i in lst:
            lgs.append(f'{int(tm) - i}s')
        return ', '.join(lgs)

    text = 'STATS\n\n'
    text += f"Memory: {checks_data['memory'][0]}mb\nLast {int(time.time() - checks_data['memory'][1])}s\n\n"
    text += f"Incub check: {checks_data['incub'][0]}s\nLast {int(time.time() - checks_data['incub'][1])}s\nUsers: {checks_data['incub'][2]}\n\n"
    text += f"Notifications check: {'s, '.join(str(i) for i in checks_data['notif'][0])}\nLast {ttx(time.time(), checks_data['notif'][1])}\n\n"

    for cls in ['main', 'main_hunt', 'main_game', 'main_sleep', 'main_pass', 'main_journey']:
        text += f"{cls} check: {'s, '.join(str(i) for i in checks_data[cls][0])}\nLast {ttx(time.time(), checks_data[cls][1])}\nUsers: {str(checks_data[cls][2])}\n\n"

    text += f'Thr.count: {threading.active_count()}'
    bot.send_message(user.id, text)


@bot.message_handler(commands=['add_item'])
def command(message):
    user = message.from_user
    if user.id in config.BOT_DEVS:
        msg_args = message.text.split()

        if len(msg_args) < 4:

            text = Functions.get_text(user.language_code, "additem_command", 'err')
            bot.send_message(user.id, text)

        else:

            items = items_f['items']

            ad_user = int(msg_args[3])
            item_id = msg_args[1]
            col = int(msg_args[2])
            bd = users.find_one({"userid": ad_user})

            item_name = items[item_id]['name'][bd['language_code']]
            chat = bot.get_chat(ad_user)

            Functions.add_item_to_user(bd, item_id, col)
            text_user = Functions.get_text(user.language_code, "additem_command", 'user').format(
                item=f'{item_name} x{col}')

            try:
                bot.send_message(chat.id, text_user)
                ms_status = True
            except:
                ms_status = False

            text_dev = Functions.get_text(user.language_code, "additem_command", 'dev').format(
                item=f'{item_name} x{col}', username=chat.first_name, message_status=ms_status)
            bot.send_message(user.id, text_dev)


@bot.message_handler(commands=['dungeon_delete'])
def command(message):
    user = message.from_user
    if user.id in config.BOT_DEVS:
        inf = Dungeon.message_upd(bot, dungeonid=user.id, type='delete_dungeon')
        print(inf)

        dng, inf = Dungeon.base_upd(dungeonid=user.id, type='delete_dungeon')
        pprint.pprint(dng)
        print(inf)


@bot.message_handler(commands=['stats_100'])
def command(message):
    user = message.from_user
    if user.id in config.BOT_DEVS:
        bd_user = users.find_one({"userid": user.id})

        for dk in bd_user['dinos'].keys():
            dino = bd_user['dinos'][dk]
            ds = dino['stats'].copy()
            for st in ds:
                dino['stats'][st] = 100

        users.update_one({"userid": user.id}, {"$set": {f"dinos": bd_user['dinos']}})
        print('ok')


@bot.message_handler(commands=['check_items'])
def command(message):
    user = message.from_user
    if user.id in config.BOT_DEVS:

        items_col = {}
        for i in items_f['items'].keys():
            items_col[i] = []

        uss = users.find({})

        for t_user in uss:
            for item in t_user['inventory']:
                if t_user['userid'] not in items_col[item['item_id']]:
                    items_col[item['item_id']].append(t_user['userid'])

        text = ''
        a = 0
        for i in items_col:
            if a == 3:
                a = 0
                text += '\n'

            text += f'*{i}*: {len(items_col[i])}  \|  '
            a += 1

        bot.send_message(user.id, text, parse_mode="MarkdownV2")
        print(text)


@bot.message_handler(commands=['events'])
def command(message):

    Functions.auto_event('time_year')

    print(Functions.get_event("time_year"))

# =========================================

@bot.message_handler(commands=['link_promo'])
def command(message):
    user = message.from_user
    msg_args = message.text.split()

    if user.id in config.BOT_DEVS:
        text_dict = Functions.get_text(user.language_code, "promo_commands", 'link')

        if len(msg_args) > 1:

            promo_code = msg_args[1]
            promo_data = management.find_one({"_id": 'promo_codes'})['codes']

            if promo_code in promo_data.keys():

                fw = message.reply_to_message

                if fw != None:
                    fw_ms_id = fw.forward_from_message_id
                    fw_chat_id = fw.forward_from_chat.id

                    markup_inline = types.InlineKeyboardMarkup()
                    markup_inline.add(types.InlineKeyboardButton(text=text_dict['button_name'], callback_data=f'promo_activ {promo_code} use'))

                    bot.edit_message_reply_markup(fw_chat_id, fw_ms_id, reply_markup=markup_inline)
                    bot.send_message(user.id, text_dict['create'])

            else:
                bot.send_message(user.id, text_dict['not_found'])


@bot.message_handler(commands=['unlink_promo'])
def command(message):
    user = message.from_user

    if user.id in config.BOT_DEVS:
        text_dict = Functions.get_text(user.language_code, "promo_commands", 'unlink')

        fw = message.reply_to_message
        if fw != None:
            fw_ms_id = fw.forward_from_message_id
            fw_chat_id = fw.forward_from_chat.id

            bot.edit_message_reply_markup(fw_chat_id, fw_ms_id, reply_markup=None)
            bot.send_message(user.id, text_dict['delete'])

        else:
            bot.send_message(user.id, text_dict['not_found'])


@bot.message_handler(commands=['promo'])
def command(message):
    user = message.from_user
    msg_args = message.text.split()
    if len(msg_args) > 1:
        promo_code = msg_args[1]

        ret_code, text = Functions.promo_use(promo_code, user)
        bot.send_message(user.id, text)


@bot.message_handler(commands=['create_promo'])
def command(message):
    user = message.from_user
    if user.id in config.BOT_DEVS:
        msg_args = message.text.split()
        text_dict = Functions.get_text(user.language_code, "promo_commands", 'create_promo')

        if len(msg_args) < 4:

            text = text_dict['format']
            bot.send_message(user.id, text)

        else:

            col_use = msg_args[1]
            nt_time = msg_args[2]
            money = int(msg_args[3])

            if col_use != 'inf':
                col_use = int(col_use)

            if nt_time != 'inf':
                time_t = int(nt_time[:-1])
                nt_time = list(nt_time)

                if nt_time[-1] == 'm':
                    time_t = time_t * 60

                if nt_time[-1] == 'h':
                    time_t = time_t * 3600

                if nt_time[-1] == 'd':
                    time_t = time_t * 86400

            else:
                time_t = 'inf'

            col = random.randint(5, 10)
            promo_data = management.find_one({"_id": 'promo_codes'})
            codes = list(promo_data['codes'].keys())

            letters = [
                'a', 'b', 'c', 'd', 'e', 'f', 'g',
                'h', 'i', 'j', 'k', 'l', 'm', 'n',
                'o', 'p', 'q', 'r', 's', 't', 'u',
                'v', 'w', 'x', 'y', 'z', '!', '$',
                '%', '.', '<', ">", ';']
            random.shuffle(letters)

            def create_code():
                pr_code = ''
                while len(pr_code) < col:

                    if random.randint(0, 1):
                        random.shuffle(letters)
                        pr_code += random.choice(letters)

                    else:
                        pr_code += str(random.randint(0, 9))

                return pr_code

            pr_code = create_code()
            if pr_code in codes:
                while pr_code in codes:
                    pr_code = create_code()

            def reg_items(msg):
                ok = True
                iims = []
                content = ''

                if msg.text != '-':

                    items = items_f['items'].keys()
                    content = msg.text.split()

                    for i in content:

                        if i not in items:
                            msg = bot.send_message(user.id, text_dict['not_item'].format(i=i))
                            ok = False
                            break

                        else:
                            iims.append(i)

                if ok:

                    data = {
                        'users': [],
                        'col': col_use,
                        'time_end': time_t,
                        'time_d': time_t,
                        'money': money,
                        'items': iims,
                        'active': False
                    }

                    if time_t != 'inf':
                        txt_time = Functions.time_end(data['time_end'], True)
                    else:
                        txt_time = time_t

                    i_names = ', '.join(Functions.sort_items_col(iims, user.language_code))

                    text = text_dict['create'].format(pr_code=pr_code, col_use=col_use, txt_time=txt_time, money=money,
                                                      i_names=i_names)

                    markup_inline = types.InlineKeyboardMarkup(row_width=2)
                    bs = text_dict['buttons']

                    inl_l = {
                        bs[0]: f'promo_activ {pr_code} activ',
                        bs[1]: f'promo_activ {pr_code} delete',
                        bs[2]: f'promo_activ {pr_code} use'
                    }

                    markup_inline.add(
                        *[types.InlineKeyboardButton(text=inl, callback_data=inl_l[inl]) for inl in inl_l])

                    management.update_one({"_id": 'promo_codes'}, {"$set": {f'codes.{pr_code}': data}})
                    bot.send_message(user.id, text, parse_mode='markdown', reply_markup=markup_inline)

            msg = bot.send_message(user.id, text_dict['enter_items'])
            bot.register_next_step_handler(msg, reg_items)


@bot.message_handler(commands=['help'])
def command(message):
    user = message.from_user

    text = Functions.get_text(user.language_code, "help_command", "all")

    if user.id in config.BOT_DEVS:
        text += Functions.get_text(user.language_code, "help_command", "dev")

    bot.reply_to(message, text, parse_mode='html')


@bot.message_handler(commands=['profile', 'профиль'])
def command(message):
    user = message.from_user
    bd_user = users.find_one({"userid": user.id})
    if bd_user != None:

        text = Functions.member_profile(bot, user.id, bd_user['language_code'])

        try:
            bot.reply_to(message, text, parse_mode='Markdown')
        except Exception as error:
            print(message.chat.id, 'ERROR Профиль', '\n', error)
            bot.reply_to(message, text)

    else:

        text = Functions.get_text(l_key=user.language_code, text_key="no_account")
        bot.reply_to(message, text, parse_mode='Markdown')


@bot.message_handler(commands=["settings"])
def command(message):
    user = message.from_user
    bd_user = users.find_one({"userid": user.id})

    if bd_user != None:
        Commands.open_settings(bot, message, user, bd_user)
    else:
        text = Functions.get_text(l_key=user.language_code, text_key="no_account")
        bot.reply_to(message, text, parse_mode='Markdown')


@bot.message_handler(commands=['message_update'])
def command(message):
    user = message.from_user
    bd_user = users.find_one({"userid": user.id})
    if bd_user != None:

        if message.chat.type == 'private':

            dungs = dungeons.find({})
            dungeonid = None

            for dng in dungs:
                if str(user.id) in dng['users'].keys():
                    dungeonid = dng['dungeonid']
                    break

            if dungeonid != None:
                image_way = 'images/dungeon/preparation/1.png'
                image = open(image_way, 'rb')
                text = '-'

                msg = bot.send_photo(user.id, image, text, parse_mode='Markdown')

                Dungeon.base_upd(userid=user.id, messageid=msg.id, dungeonid=dungeonid, type='edit_message')

                Dungeon.message_upd(bot, userid=user.id, dungeonid=dungeonid, upd_type='one', image_update=True)

                try:
                    bot.delete_message(user.id, dng['users'][str(user.id)]['messageid'])
                except:
                    pass


@bot.message_handler(commands=['check_dinos'])
def command(message):
    user = message.from_user
    bd_user = users.find_one({"userid": user.id})
    if message.chat.type == 'private':
        if bd_user != None:
            bd_user = users.find_one({"userid": user.id})

            for dk in bd_user['dinos'].keys():
                dino = bd_user['dinos'][dk]

                if dino['activ_status'] == 'dungeon':

                    if 'dungeon_id' not in dino.keys():
                        dino['activ_status'] = 'pass_active'
                        del dino["dungeon_id"]

                    elif 'dungeon_id' in dino.keys():
                        dng = dungeons.find_one({"dungeonid": dino['dungeon_id']})

                        if dng == None:
                            dino['activ_status'] = 'pass_active'
                            del dino["dungeon_id"]

            users.update_one({"userid": user.id}, {"$set": {f"dinos": bd_user['dinos']}})

            text = Functions.get_text(l_key=user.language_code, text_key="dungeon_err")
            bot.reply_to(message, text)


@bot.message_handler(commands=['add_me', 'добавь_меня'])
def command(message):
    user = message.from_user
    bd_user = users.find_one({"userid": user.id})
    if message.chat.type != 'private':
        if bd_user != None:

            text = Functions.get_text(l_key=user.language_code, text_key="add_me").format(userid=user.id, username=user.first_name)

            bot.reply_to(message, text, parse_mode='HTML',
                         reply_markup=Functions.inline_markup(bot, 'send_request', user.id, ['Отправить запрос', 'Send a request']))

        else:

            text = Functions.get_text(l_key=user.language_code, text_key="no_account")
            bot.reply_to(message, text, parse_mode='Markdown')


@bot.message_handler(commands=['start', 'main-menu'])
def on_start(message):
    user = message.from_user
    if message.chat.type == 'private':
        if users.find_one({"userid": user.id}) == None:

            text = Functions.get_text(l_key=user.language_code, text_key="start_menu").format(username=user.first_name)

            bot.reply_to(message, text, reply_markup=Functions.markup(bot, user=user), parse_mode='html')

        else:
            bot.reply_to(message, '👋', reply_markup=Functions.markup(bot, user=user), parse_mode='html')


@bot.message_handler(content_types=['text'], spam_check=True, in_dungeon=True)
def on_message(message):
    user = message.from_user

    if message.chat.type == 'private':
        bd_user = users.find_one({"userid": user.id})

        if message.text in ['🍡 Начать играть', '🍡 Start playing']:

            Commands.start_game(bot, message, user, bd_user)

        elif message.text in ["🧩 Проект: Возрождение", '🧩 Project: Rebirth']:

            Commands.project_reb(bot, message, user, bd_user)

        elif message.text in ['↪ Назад', '↪ Back', '❌ Cancel', '❌ Отмена']:

            Commands.back_open(bot, message, user, bd_user)

        elif message.text in ['👁‍🗨 Профиль', '👁‍🗨 Profile']:

            Commands.open_profile_menu(bot, message, user, bd_user)

        elif message.text in ['🎮 Инвентарь', '🎮 Inventory']:

            Commands.opne_inventory(bot, message, user, bd_user)

        elif message.text in ['🦖 Динозавр', '🦖 Dinosaur']:

            Commands.dino_prof(bot, message, user)

        elif message.text in ['🔧 Настройки', '🔧 Settings']:

            Commands.open_settings(bot, message, user, bd_user)

        elif message.text in ['👥 Друзья', '👥 Friends']:

            Commands.friends_open(bot, message, user, bd_user)

        elif message.text in ['❗ FAQ']:

            Commands.faq(bot, message, user, bd_user)

        elif message.text in ['🍺 Дино-таверна', '🍺 Dino-tavern'] and Functions.lst_m_f(bd_user) != 'dino-tavern':

            Commands.open_dino_tavern(bot, message, user, bd_user)

        elif Functions.tr_c_f(bd_user) and message.text in ['🕹 Действия', '🕹 Actions']:

            Commands.open_action_menu(bot, message, user, bd_user)

        elif message.text in ['❗ Notifications', '❗ Уведомления']:

            Commands.not_set(bot, message, user, bd_user)

        elif message.text in ["👅 Язык", "👅 Language"]:

            Commands.lang_set(bot, message, user, bd_user)

        elif message.text in ['🎞 Инвентарь', '🎞 Inventory']:

            Commands.inv_set_pages(bot, message, user, bd_user)

        elif message.text in ['⁉ Видимость FAQ', '⁉ Visibility FAQ']:

            Commands.settings_faq(bot, message, user, bd_user)

        elif Functions.tr_c_f(bd_user) and message.text in ['💬 Переименовать', '💬 Rename']:

            Commands.rename_dino(bot, message, user, bd_user)

        elif message.text in ["➕ Добавить", "➕ Add"]:

            Commands.add_friend(bot, message, user, bd_user)

        elif message.text in ["📜 Список", "📜 List"]:

            Commands.friends_list(bot, message, user, bd_user)

        elif message.text in ["💌 Запросы", "💌 Inquiries"]:

            Functions.user_requests(bot, user, message)

        elif message.text in ['➖ Удалить', '➖ Delete']:

            Commands.delete_friend(bot, message, user, bd_user)

        elif message.text in ['🤍 Пригласи друга', '🤍 Invite a friend']:

            Commands.invite_friend(bot, message, user, bd_user)

        elif message.text in ['🎲 Сгенерировать код', '🎲 Generate Code']:

            Commands.generate_fr_code(bot, message, user, bd_user)

        elif message.text in ['🎞 Ввести код', '🎞 Enter Code']:

            Commands.enter_fr_code(bot, message, user, bd_user)

        elif message.text in ['👥 Меню друзей', '👥 Friends Menu']:

            Commands.friends_menu(bot, message, user, bd_user)

        elif Functions.tr_c_f(bd_user) and message.text in ['🌙 Уложить спать', '🌙 Put to bed']:

            Commands.dino_sleep_ac(bot, message, user, bd_user)

        elif Functions.tr_c_f(bd_user) and message.text in ['🌙 Пробудить', '🌙 Awaken']:

            Commands.dino_unsleep_ac(bot, message, user, bd_user)

        elif Functions.tr_c_f(bd_user) and message.text in ['🎑 Путешествие', '🎑 Journey']:

            Commands.dino_journey(bot, message, user, bd_user)

        elif Functions.tr_c_f(bd_user) and message.text in ['🎑 Вернуть', '🎑 Call']:

            Commands.dino_unjourney(bot, message, user, bd_user)

        elif Functions.tr_c_f(bd_user) and message.text in ['🎮 Развлечения', '🎮 Entertainments']:

            Commands.dino_entert(bot, message, user, bd_user)

        elif Functions.tr_c_f(bd_user) and message.text in ['🍣 Покормить', '🍣 Feed']:

            Functions.user_inventory(bot, user, message, 'use_item', 'itemtype', ["+eat"])

        elif Functions.tr_c_f(bd_user) and message.text in ['🍕 Сбор пищи', '🍕 Collecting food']:

            Commands.collecting_food(bot, message, user, bd_user)

        elif Functions.tr_c_f(bd_user) and message.text in ['🍕 Прогресс', '🍕 Progress']:

            Commands.coll_progress(bot, message, user, bd_user)

        elif Functions.tr_c_f(bd_user) and (message.text[:11] in ['🦖 Динозавр:'] or message.text[:7] in ['🦖 Dino:']):

            Commands.dino_action_ans(bot, message, user, bd_user)

        elif Functions.tr_c_f(bd_user) and message.text in ['↩ Назад', '↩ Back']:

            Commands.action_back(bot, message, user, bd_user)

        elif Functions.tr_c_f(bd_user) and message.text in ['🎮 Консоль', '🪁 Змей', '🏓 Пинг-понг', '🏐 Мяч', '🎮 Console', '🪁 Snake', '🏓 Ping Pong', '🏐 Ball', '🧩 Пазлы', '♟ Шахматы', '🧱 Дженга', '🎲 D&D', '🧩 Puzzles', '♟ Chess', '🧱 Jenga']:

            Commands.dino_entert_games(bot, message, user, bd_user)

        elif Functions.tr_c_f(bd_user) and message.text in ['❌ Остановить игру', '❌ Stop the game']:

            Commands.dino_stop_games(bot, message, user, bd_user)

        elif message.text in ['🎢 Рейтинг', '🎢 Rating']:

            Commands.rayting(bot, message, user, bd_user)

        elif message.text in ['📜 Информация', '📜 Information']:

            Commands.open_information(bot, message, user, bd_user)

        elif message.text in ['🛒 Рынок', '🛒 Market']:

            Commands.open_market_menu(bot, message, user, bd_user)

        elif message.text in ['💍 Аксессуары', '💍 Accessories']:

            Commands.acss(bot, message, user, bd_user)

        elif message.text in ['➕ Добавить товар', '➕ Add Product']:

            Functions.user_inventory(bot, user, message, 'add_product')

        elif message.text in ['📜 Мои товары', '📜 My products']:

            Commands.my_products(bot, message, user, bd_user)

        elif message.text in ['➖ Удалить товар', '➖ Delete Product']:

            Commands.delete_product(bot, message, user, bd_user)

        elif message.text in ['🔍 Поиск товара', '🔍 Product Search']:

            Commands.search_pr(bot, message, user, bd_user)

        elif message.text in ['🛒 Случайные товары', '🛒 Random Products']:

            Commands.random_search(bot, message, user, bd_user)

        elif message.text in ['⛓ Квесты', '⛓ Quests']:

            Commands.quests(bot, message, user, bd_user)

        elif message.text in ['🎭 Навыки', '🎭 Skills']:

            text = Functions.get_text(user.language_code, "in_development")
            bot.send_message(user.id, text)

        elif message.text in ['🦖 БИО', '🦖 BIO']:

            text = Functions.get_text(user.language_code, "in_development")
            bot.send_message(user.id, text)

        elif message.text in ['👁‍🗨 Динозавры в таверне', '👁‍🗨 Dinosaurs in the Tavern']:

            text = Functions.get_text(user.language_code, "in_development")
            bot.send_message(user.id, text)

        elif message.text in ['♻ Change Dinosaur', '♻ Изменение Динозавра']:

            Commands.rarity_change(bot, message, user, bd_user)

        elif message.text in ['🥏 Дрессировка', '🥏 Training']:

            text = Functions.get_text(user.language_code, "in_development")
            bot.send_message(user.id, text)

        elif message.text in ["💡 Исследования", "💡 Research"]:

            text = Functions.get_text(user.language_code, "in_development")
            bot.send_message(user.id, text)

        elif message.text in ["🗻 Подземелья", "🗻 Dungeons"]:

            Commands.dungeon_menu(bot, message, user, bd_user)

        elif message.text in ["🗻 Создать", "🗻 Create"]:

            Commands.dungeon_create(bot, message, user, bd_user)

        elif message.text in ['🚪 Присоединиться', '🚪 Join']:

            Commands.dungeon_join(bot, message, user, bd_user)

        elif message.text in ['⚔ Экипировка', '⚔ Equip']:

            Commands.dungeon_equipment(bot, message, user, bd_user)

        elif message.text in ['📕 Правила подземелья', '📕 Dungeon Rules']:

            Commands.dungeon_rules(bot, message, user, bd_user)

        elif message.text in ['🎮 Статистика', '🎮 Statistics']:

            Commands.dungeon_statist(bot, message, user, bd_user)

        if bd_user != None:
            # последняя активность
            users.update_one({"userid": bd_user['userid']}, {"$set": {'last_m': int(time.time())}})


@bot.callback_query_handler(wait_callback=True, func=lambda call: True)
def answer(call):
    user = call.from_user
    bd_user = users.find_one({"userid": user.id})

    if call.data.split()[0] == 'egg_answer':

        CallData.egg_answer(bot, bd_user, call, user)

    elif call.data[:13] in ['90min_journey', '60min_journey', '30min_journey', '10min_journey', '12min_journey',
                            '24min_journey']:

        CallData.journey(bot, bd_user, call, user)

    elif call.data[:10] in ['1_con_game', '2_con_game', '3_con_game', '1_sna_game', '2_sna_game', '3_sna_game',
                            '1_pin_game', '2_pin_game', '3_pin_game', '1_bal_game', '2_bal_game', '3_bal_game',
                            '1_puz_game', '2_puz_game', '3_puz_game', '1_che_game', '2_che_game', '3_che_game',
                            '1_jen_game', '2_jen_game', '3_jen_game', '1_ddd_game', '2_ddd_game', '3_ddd_game']:

        CallData.game(bot, bd_user, call, user)

    elif call.data in ['dead_answer1', 'dead_answer2', 'dead_answer3', 'dead_answer4']:

        CallData.dead_answer(bot, bd_user, call, user)

    elif call.data == 'dead_restart':

        CallData.dead_restart(bot, bd_user, call, user)

    elif call.data[:5] == 'item_':

        CallData.item_use(bot, bd_user, call, user)

    elif call.data[:12] == 'remove_item_':

        CallData.remove_item(bot, bd_user, call, user)

    elif call.data[:7] == 'remove_':

        CallData.remove(bot, bd_user, call, user)

    elif call.data == "cancel_remove":

        bot.delete_message(user.id, call.message.message_id)

    elif call.data[:9] == 'exchange_':

        CallData.exchange(bot, bd_user, call, user)

    elif call.data[:11] == 'market_buy_':

        CallData.market_buy(bot, bd_user, call, user)

    # if call.data[:7] == 'market_':

    #     CallData.market_inf(bot, bd_user, call, user)

    elif call.data[:9] == 'iteminfo_':

        CallData.iteminfo(bot, bd_user, call, user)

    elif call.data == 'inventory':

        Functions.user_inventory(bot, user, call.message)

    elif call.data == 'requests':

        Functions.user_requests(bot, user, call.message)

    elif call.data == 'send_request':

        CallData.send_request(bot, bd_user, call, user)

    elif call.data[:18] == 'open_dino_profile_':

        did = call.data[18:]
        if did in bd_user['dinos'].keys():
            bd_dino = bd_user['dinos'][did]
            Functions.p_profile(bot, call.message, bd_dino, user, bd_user, did)

    elif call.data[:8] == 'ns_craft':

        CallData.ns_craft(bot, bd_user, call, user)

    elif call.data[:13] == 'change_rarity':

        CallData.change_rarity_call_data(bot, bd_user, call, user)

    elif call.data.split()[0] == 'faq':

        CallData.faq(bot, bd_user, call, user)

    elif call.data.split()[0] == 'cancel_progress':

        CallData.cancel_progress(bot, bd_user, call, user)

    elif call.data.split()[0] == 'message_delete':

        show_text = "✉ > 🗑"
        bot.answer_callback_query(call.id, show_text)

        try:
            bot.delete_message(user.id, call.message.message_id)
        except:
            pass

    elif call.data.split()[0] == 'dungeon.settings':

        CallData.dungeon_settings(bot, bd_user, call, user)

    elif call.data.split()[0] == 'dungeon.to_lobby':

        CallData.dungeon_to_lobby(bot, bd_user, call, user)

    elif call.data.split()[0] == 'dungeon.settings_lang':

        CallData.dungeon_settings_lang(bot, bd_user, call, user)

    elif call.data.split()[0] == 'dungeon.settings_batnotf':

        CallData.dungeon_settings_batnotf(bot, bd_user, call, user)

    elif call.data.split()[0] == 'dungeon.leave':

        CallData.dungeon_leave(bot, bd_user, call, user)

    elif call.data.split()[0] == 'dungeon.leave_True':

        CallData.dungeon_leave_True(bot, bd_user, call, user)

    elif call.data.split()[0] == 'dungeon.leave_False':

        CallData.dungeon_leave_False(bot, bd_user, call, user)

    elif call.data.split()[0] == 'dungeon.remove':

        CallData.dungeon_remove(bot, bd_user, call, user)

    elif call.data.split()[0] == 'dungeon.remove_True':

        CallData.dungeon_remove_True(bot, bd_user, call, user)

    elif call.data.split()[0] == 'dungeon.remove_False':

        CallData.dungeon_remove_False(bot, bd_user, call, user)

    elif call.data.split()[0] == 'dungeon.menu.add_dino':

        CallData.dungeon_add_dino_menu(bot, bd_user, call, user)

    elif call.data.split()[0] == 'dungeon.menu.remove_dino':

        CallData.dungeon_remove_dino_menu(bot, bd_user, call, user)

    elif call.data.split()[0] == 'dungeon.action.add_dino':

        CallData.dungeon_add_dino(bot, bd_user, call, user)

    elif call.data.split()[0] == 'dungeon.action.remove_dino':

        CallData.dungeon_remove_dino(bot, bd_user, call, user)

    elif call.data.split()[0] == 'dungeon.ready':

        CallData.dungeon_ready(bot, bd_user, call, user)

    elif call.data.split()[0] == 'dungeon.invite':

        CallData.dungeon_invite(bot, bd_user, call, user)

    elif call.data.split()[0] == 'dungeon.supplies':

        CallData.dungeon_supplies(bot, bd_user, call, user)

    elif call.data.split()[0] == 'dungeon.action.set_coins':

        CallData.dungeon_set_coins(bot, bd_user, call, user)

    elif call.data.split()[0] == 'dungeon.action.add_item':

        CallData.dungeon_add_item_action(bot, bd_user, call, user)

    elif call.data.split()[0] == 'dungeon.action.remove_item':

        CallData.dungeon_remove_item_action(bot, bd_user, call, user)

    elif call.data.split()[0] == 'dungeon_add_item':

        CallData.dungeon_add_item(bot, bd_user, call, user)

    elif call.data.split()[0] == 'dungeon_remove_item':

        CallData.dungeon_remove_item(bot, bd_user, call, user)

    elif call.data.split()[0] == 'dungeon.start':

        CallData.dungeon_start_game(bot, bd_user, call, user)

    elif call.data.split()[0] == 'dungeon.next_room':

        CallData.dungeon_next_room(bot, bd_user, call, user)

    elif call.data.split()[0] == 'dungeon.action.battle_action':

        CallData.dungeon_battle_action(bot, bd_user, call, user)

    elif call.data.split()[0] == 'dungeon.battle_action_attack':

        CallData.dungeon_battle_attack(bot, bd_user, call, user)

    elif call.data.split()[0] == 'dungeon.battle_action_defend':

        CallData.dungeon_battle_defend(bot, bd_user, call, user)

    elif call.data.split()[0] == 'dungeon.battle_action_idle':

        CallData.dungeon_battle_idle(bot, bd_user, call, user)

    elif call.data.split()[0] == 'dungeon.next_room_ready':

        CallData.dungeon_next_room_ready(bot, bd_user, call, user)

    elif call.data.split()[0] == 'dungeon.end_move':

        CallData.dungeon_end_move(bot, bd_user, call, user)

    elif call.data.split()[0] == 'dungeon.dinos_stats':

        CallData.dungeon_dinos_stats(bot, bd_user, call, user)

    elif call.data.split()[0] == 'dungeon.collect_reward':

        CallData.dungeon_collect_reward(bot, bd_user, call, user)

    elif call.data.split()[0] == 'dungeon.item_from_reward':

        CallData.item_from_reward(bot, bd_user, call, user)

    elif call.data.split()[0] == 'dungeon.inventory':

        CallData.dungeon_inventory(bot, bd_user, call, user)

    elif call.data.split()[0] == '-' or call.data.split()[0] == ' ':
        pass

    elif call.data.split()[0] == 'dungeon_use_item_info':

        CallData.dungeon_use_item_info(bot, bd_user, call, user)

    elif call.data.split()[0] == 'dungeon_use_item':

        CallData.dungeon_use_item(bot, bd_user, call, user)

    elif call.data.split()[0] == 'dungeon_use_item':

        CallData.dungeon_use_item(bot, bd_user, call, user)

    elif call.data.split()[0] == 'dungeon_delete_item':

        CallData.dungeon_delete_item(bot, bd_user, call, user)

    elif call.data.split()[0] == 'dungeon.kick_member':

        CallData.dungeon_kick_member(bot, bd_user, call, user)

    elif call.data.split()[0] == 'dungeon_kick':

        CallData.dungeon_kick(bot, bd_user, call, user)

    elif call.data.split()[0] == 'dungeon.leave_in_game':

        CallData.dungeon_leave_in_game(bot, bd_user, call, user)

    elif call.data.split()[0] == 'dungeon.leave_in_game_answer':

        CallData.dungeon_leave_in_game_answer(bot, bd_user, call, user)

    elif call.data.split()[0] == 'dungeon.fork_answer':

        CallData.dungeon_fork_answer(bot, bd_user, call, user)

    elif call.data.split()[0] == 'dungeon.safe_exit':

        CallData.dungeon_safe_exit(bot, bd_user, call, user)

    elif call.data.split()[0] == 'dungeon.mine':

        CallData.dungeon_mine(bot, bd_user, call, user)

    elif call.data.split()[0] == 'dungeon.shop_menu':

        CallData.dungeon_shop_menu(bot, bd_user, call, user)

    elif call.data.split()[0] == 'dungeon.shop_buy':

        CallData.dungeon_shop_buy(bot, bd_user, call, user)

    elif call.data.split()[0] == 'dungeon.settings_start_floor':

        CallData.dungeon_settings_start_floor(bot, bd_user, call, user)

    elif call.data.split()[0] == 'dungeon.start_floor':

        CallData.dungeon_start_floor(bot, bd_user, call, user)

    elif call.data.split()[0] == 'rayt_lvl':

        CallData.rayt_lvl(bot, bd_user, call, user)

    elif call.data.split()[0] == 'rayt_money':

        CallData.rayt_money(bot, bd_user, call, user)

    elif call.data.split()[0] == 'rayt_dungeon':

        CallData.rayt_dungeon(bot, bd_user, call, user)

    elif call.data.split()[0] == 'complete_quest':

        CallData.complete_quest(bot, bd_user, call, user)

    elif call.data.split()[0] == 'delete_quest':

        CallData.delete_quest(bot, bd_user, call, user)

    elif call.data.split()[0] == 'egg_use':

        CallData.egg_use(bot, bd_user, call, user)

    elif call.data.split()[0] == 'promo_activ':

        CallData.promo_activ(bot, bd_user, call, user)


def start_all(bot):
    try:
        Functions.create_logfile()
    except Exception as e:
        print('Система: Файл логирования не был создан >', e)
        logging.critical(f'Файл логирования не был создан > {e}')

    if bot.get_me().first_name == config.BOT_NAME or False:
        main_checks.start()  # активация всех проверок и игрового процесса
        thr_notif.start()  # активация уведомлений
        min10_thr.start()  # десяти-минутный чек
        min1_thr.start()  # 1-мин чек

        print('Система: Жизненный процессы запущены')
        logging.info('Жизненный процессы запущены')

    else:
        print('Система: Жизненные процессы не запущены')
        logging.warning('Жизненные процессы не запущены')

    try:
        bot.add_custom_filter(SpamStop())
        bot.add_custom_filter(WC())
        bot.add_custom_filter(In_Dungeon())
    except Exception as e:
        print('Система: Фильтры не были определены >', e)
        logging.error(f'Фильтры не были определены > {e}')

    try:
        Functions.clean_tmp()
    except Exception as e:
        print('Система: Временные изображения не были очищены >', e)
        logging.warning(f'Временные изображения не были очищены > {e}')

    try:
        Functions.load_languages()
    except Exception as e:
        print('Система: Локализация не была загружена >', e)
        logging.warning(f'Локализация не была загружена > {e}')

    print(f'Система: Бот {bot.get_me().first_name} запущен!')
    logging.info(f'Бот {bot.get_me().first_name} запущен!')

    bot.infinity_polling(skip_pending=False, timeout=600)


if __name__ == '__main__':
    start_all(bot)
