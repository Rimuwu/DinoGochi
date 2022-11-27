import json
import random
import sys
import time

from fuzzywuzzy import fuzz
from telebot import types

from mods.classes import Dungeon, Functions

sys.path.append("..")
import config

client = config.CLUSTER_CLIENT
users, management, dungeons = client.bot.users, client.bot.management, client.bot.dungeons

with open('json/items.json', encoding='utf-8') as f: items_f = json.load(f)

with open('json/dino_data.json', encoding='utf-8') as f: json_f = json.load(f)

with open('json/mobs.json', encoding='utf-8') as f: mobs_f = json.load(f)

with open('json/settings.json', encoding='utf-8') as f: settings_f = json.load(f)


class Commands:

    @staticmethod
    def start_game(bot, message, user, bd_user):

        if bd_user == None:
            text = Functions.get_text(l_key=user.language_code, text_key="request_subscribe", dp_text_key="text")
            b1, b2 = Functions.get_text(user.language_code, "request_subscribe", "button")

            markup_inline = types.InlineKeyboardMarkup()

            markup_inline.add(types.InlineKeyboardButton(text=b1, url="https://t.me/DinoGochi"))
            markup_inline.add(types.InlineKeyboardButton(text=b2, url="https://t.me/+pq9_21HXXYY4ZGQy"))

            bot.send_message(message.chat.id, text, parse_mode='html', reply_markup=markup_inline)

            text = Functions.get_text(l_key=user.language_code, text_key="start_game")

            photo, markup_inline, id_l = Functions.create_egg_image()
            bot.send_photo(message.chat.id, photo, text, reply_markup=markup_inline)

            Functions.insert_user(user)
            users.update_one({"userid": user.id}, {"$set": {'eggs': id_l}})

    @staticmethod
    def project_reb(bot, message, user, bd_user):

        if bd_user != None:
            if bd_user != None and len(bd_user['dinos']) == 0 and Functions.inv_egg(bd_user) == False and \
                    bd_user['lvl'][0] <= 5:
                text_dict = Functions.get_text(l_key=bd_user['language_code'], text_key="project_reb")

                random1 = random.choice(text_dict['random1'])
                random2 = random.choice(text_dict['random2'])
                first_name = user.first_name
                last_name = user.last_name
                buttons = text_dict['buttons']

                text = text_dict['text'].format(random1=random1, random2=random2, first_name=first_name, last_name=last_name)

                markup_inline = types.InlineKeyboardMarkup()
                markup_inline.add(types.InlineKeyboardButton(text=buttons[0], callback_data='dead_answer1'))
                markup_inline.add(types.InlineKeyboardButton(text=buttons[1], callback_data='dead_answer2'))
                markup_inline.add(types.InlineKeyboardButton(text=buttons[2], callback_data='dead_answer3'))
                markup_inline.add(types.InlineKeyboardButton(text=buttons[3], callback_data='dead_answer4'))

                bot.reply_to(message, text, reply_markup=markup_inline, parse_mode="Markdown")

    @staticmethod
    def faq(bot, message, user, bd_user):
        markup_inline = types.InlineKeyboardMarkup(row_width=2)

        if bd_user != None:
            text_dict = Functions.get_text(l_key=bd_user['language_code'], text_key="faq")
            text = text_dict['text']
            inl_l = text_dict['inl_l']

            markup_inline.add(*[types.InlineKeyboardButton(text=inl, callback_data=inl_l[inl]) for inl in inl_l.keys()])
            bot.send_message(message.chat.id, text, parse_mode='Markdown', reply_markup=markup_inline)

    @staticmethod
    def not_set(bot, message, user, bd_user):

        if bd_user != None:
            text_dict = Functions.get_text(l_key=bd_user['language_code'], text_key="not_set")
            buttons = Functions.get_text(l_key=bd_user['language_code'], text_key="buttons_name")
            ans = [buttons['enable'], buttons['disable'], buttons['back']]
            text = text_dict['info']

            rmk = types.ReplyKeyboardMarkup(resize_keyboard=True)
            rmk.add(ans[0], ans[1])
            rmk.add(ans[2])

            def ret(message, ans, bd_user):

                if message.text not in ans or message.text == ans[2]:
                    res = None
                else:
                    res = message.text

                if res == None:
                    bot.send_message(message.chat.id, f'❌', reply_markup=Functions.markup(bot, 'settings', user))
                    return

                if res == buttons['enable']:

                    bd_user['settings']['notifications'] = True
                    users.update_one({"userid": bd_user['userid']}, {"$set": {'settings': bd_user['settings']}})

                    if bd_user['language_code'] == 'ru':
                        text = '🔧 Уведомления были активированы!'
                    else:
                        text = '🔧 Notifications have been activated!'

                    bot.send_message(message.chat.id, text, reply_markup=Functions.markup(bot, "settings", user))

                if res == buttons['disable']:

                    bd_user['settings']['notifications'] = False
                    users.update_one({"userid": bd_user['userid']}, {"$set": {'settings': bd_user['settings']}})

                    if bd_user['language_code'] == 'ru':
                        text = '🔧 Уведомления были отключены!'
                    else:
                        text = '🔧 Notifications have been disabled!'

                    bot.send_message(message.chat.id, text, reply_markup=Functions.markup(bot, "settings", user))

                else:
                    bot.send_message(message.chat.id, '❌', reply_markup=Functions.markup(bot, "settings", user))

            msg = bot.send_message(message.chat.id, text, reply_markup=rmk)
            bot.register_next_step_handler(msg, ret, ans, bd_user)

    @staticmethod
    def lang_set(bot, message, user, bd_user):

        bd_user = users.find_one({"userid": user.id})
        if bd_user != None:
            ans = []
            text_dict = Functions.get_text(l_key=bd_user['language_code'], text_key="lang_set")
            lg_dict = Functions.get_all_text_from_lkey('language_name')
            buttons_name = Functions.get_text(l_key=bd_user['language_code'], text_key="buttons_name")

            text = text_dict['interaction']

            for lkey in lg_dict:
                ans.append(lg_dict[lkey])

            rmk = types.ReplyKeyboardMarkup(resize_keyboard=True, row_width=3)
            rmk.add(*ans)
            rmk.add(buttons_name['back'])

            def ret(message, ans, bd_user):

                if message.text not in ans or message.text == buttons_name['back']:
                    res = None
                else:
                    res = message.text

                if res == None:
                    bot.send_message(message.chat.id, f'❌', reply_markup=Functions.markup(bot, 'settings', user))
                    return

                code = 'en'
                for i in lg_dict.keys():
                    if lg_dict[i] == res:
                        code = i

                users.update_one({"userid": bd_user['userid']}, {"$set": {'language_code': code}})

                text_dict = Functions.get_text(l_key=code, text_key="lang_set")
                text = text_dict['accept'] + res

                bot.send_message(message.chat.id, text, reply_markup=Functions.markup(bot, "settings", user))

            msg = bot.send_message(message.chat.id, text, reply_markup=rmk)
            bot.register_next_step_handler(msg, ret, ans, bd_user)

    @staticmethod
    def dino_prof(bot, message, user):

        bd_user = users.find_one({"userid": user.id})
        if bd_user != None:

            if len(bd_user['dinos']) > 1:
                for i in bd_user['dinos'].keys():
                    if i not in bd_user['activ_items'].keys():
                        users.update_one({"userid": bd_user["userid"]}, {
                            "$set": {f'activ_items.{i}': {'game': None, 'hunt': None, 'journey': None, 'unv': None}}})
                        bd_user = users.find_one({"userid": user.id})

            if len(bd_user['dinos'].keys()) == 0:

                text = Functions.get_text(l_key=bd_user['language_code'], text_key="command_dino_prof")

                bot.send_message(message.chat.id, text)

            elif len(bd_user['dinos'].keys()) > 0:

                n_dp, dp_a = Functions.dino_pre_answer(user)
                if n_dp == 1:
                    bot.send_message(message.chat.id, f'❌', reply_markup=Functions.markup(bot, 1, user))
                    return

                if n_dp == 2:
                    bd_dino = dp_a
                    try:
                        Functions.p_profile(bot, message, bd_dino, user, bd_user, list(bd_user['dinos'].keys())[0])

                    except Exception as error:
                        print('Ошибка в профиле2\n', error)

                        Functions.p_profile(bot, message, bd_dino, user, bd_user, list(bd_user['dinos'].keys())[0])

                if n_dp == 3:
                    rmk = dp_a[0]
                    text = dp_a[1]
                    dino_dict = dp_a[2]

                    def ret(message, dino_dict, user, bd_user):
                        if message.text in dino_dict.keys():
                            try:
                                Functions.p_profile(bot, message, dino_dict[message.text][0], user, bd_user,
                                        dino_dict[message.text][1])

                            except Exception as error:
                                print('Ошибка в профиле1\n', error)

                                Functions.p_profile(bot, message, dino_dict[message.text][0], user, bd_user,
                                        dino_dict[message.text][1])

                        else:
                            bot.send_message(message.chat.id, '❌',
                                             reply_markup=Functions.markup(bot, Functions.last_markup(bd_user), bd_user))

                    msg = bot.send_message(message.chat.id, text, reply_markup=rmk)
                    bot.register_next_step_handler(msg, ret, dino_dict, user, bd_user)

    @staticmethod
    def open_settings(bot, message, user, bd_user):

        if bd_user != None:
            settings = bd_user['settings']
            text = Functions.get_text(l_key=bd_user['language_code'], text_key="open_settings")

            if 'vis.faq' not in settings.keys():
                settings['vis.faq'] = True

            text = text.format(notif=str(settings["notifications"]), vis_faq=str(settings["vis.faq"]))
            text = text.replace("True", '✔').replace("False", '❌')

            bot.send_message(message.chat.id, text, reply_markup=Functions.markup(bot, 'settings', user))

    @staticmethod
    def back_open(bot, message, user, bd_user):

        if bd_user != None:
            text = Functions.get_text(l_key=bd_user['language_code'], text_key="back_open")

            bot.send_message(message.chat.id, text, reply_markup=Functions.markup(bot, 1, user))

    @staticmethod
    def friends_open(bot, message, user, bd_user):

        if bd_user != None:
            text = Functions.get_text(l_key=bd_user['language_code'], text_key="friends_open")

            bot.send_message(message.chat.id, text, reply_markup=Functions.markup(bot, "friends-menu", user))

    @staticmethod
    def settings_faq(bot, message, user, bd_user):

        if bd_user != None:
            buttons_name = Functions.get_text(l_key=bd_user['language_code'], text_key="buttons_name")
            ans = [buttons_name['enable'], buttons_name['disable'], buttons_name["back"]]
            text = Functions.get_text(l_key=bd_user['language_code'], text_key="settings_faq")

            rmk = types.ReplyKeyboardMarkup(resize_keyboard=True)
            rmk.add(ans[0], ans[1])
            rmk.add(ans[2])

            def ret(message, ans, bd_user):

                if message.text not in ans or message.text == ans[2]:
                    res = None
                else:
                    res = message.text

                if res == None:
                    bot.send_message(message.chat.id, f'❌', reply_markup=Functions.markup(bot, 'settings', user))
                    return

                if res == buttons_name['enable']:

                    bd_user['settings']['vis.faq'] = True
                    users.update_one({"userid": bd_user['userid']}, {"$set": {'settings': bd_user['settings']}})

                    if bd_user['language_code'] == 'ru':
                        text = '🔧 FAQ был активирован!'
                    else:
                        text = '🔧 The FAQ has been activated!'

                    bot.send_message(message.chat.id, text, reply_markup=Functions.markup(bot, "settings", user))

                if res == buttons_name['disable']:

                    bd_user['settings']['vis.faq'] = False
                    users.update_one({"userid": bd_user['userid']}, {"$set": {'settings': bd_user['settings']}})

                    if bd_user['language_code'] == 'ru':
                        text = '🔧 FAQ был отключен!'
                    else:
                        text = '🔧 The FAQ has been disabled!'

                    bot.send_message(message.chat.id, text, reply_markup=Functions.markup(bot, "settings", user))

                else:
                    bot.send_message(message.chat.id, f'❌', reply_markup=Functions.markup(bot, 'settings', user))

            msg = bot.send_message(message.chat.id, text, reply_markup=rmk)
            bot.register_next_step_handler(msg, ret, ans, bd_user)

    @staticmethod
    def inv_set_pages(bot, message, user, bd_user):

        if bd_user != None:

            gr, vr = bd_user['settings']['inv_view']
            buttons_name = Functions.get_text(l_key=bd_user['language_code'], text_key="buttons_name")
            text_dict = Functions.get_text(l_key=bd_user['language_code'], text_key="inv_set_pages")

            ans = ['2 | 3', '3 | 3', '2 | 2', '2 | 4', buttons_name["back"]]
            text = text_dict['info'].format(gr=gr, vr=vr)

            rmk = types.ReplyKeyboardMarkup(resize_keyboard=True, row_width=2)
            rmk.add(*[i for i in ans])

            def ret(message, ans, bd_user):

                if message.text not in ans or message.text in ['↪ Назад', '↪ Back']:
                    res = None
                else:
                    res = message.text

                if res == None:
                    bot.send_message(message.chat.id, f'❌', reply_markup=Functions.markup(bot, 'settings', user))
                    return

                vviw = res.split(' | ')
                v_list = []
                for i in vviw:
                    v_list.append(int(i))

                gr, vr = v_list
                text = text_dict['accept'].format(gr=gr, vr=vr)

                bd_user['settings']['inv_view'] = v_list
                users.update_one({"userid": bd_user['userid']}, {"$set": {'settings': bd_user['settings']}})

                bot.send_message(message.chat.id, text, reply_markup=Functions.markup(bot, "settings", user))

            msg = bot.send_message(message.chat.id, text, reply_markup=rmk)
            bot.register_next_step_handler(msg, ret, ans, bd_user)

    @staticmethod
    def add_friend(bot, message, user, bd_user):

        if bd_user != None:
            buttons_name = Functions.get_text(l_key=bd_user['language_code'], text_key="buttons_name")
            text_dict = Functions.get_text(l_key=bd_user['language_code'], text_key="add_friend")

            text = text_dict['info']

            rmk = types.ReplyKeyboardMarkup(resize_keyboard=True)
            rmk.add(buttons_name['back'])

            def ret(message, bd_user):
                res = message

                if message.text in buttons_name['back']:
                    bot.send_message(message.chat.id, f'❌', reply_markup=Functions.markup(bot, 'friends-menu', user))
                    return

                try:
                    fr_id = int(res.text)
                except:

                    if res.text == buttons_name['back'] or res.forward_from == None:
                        bot.send_message(message.chat.id, text_dict['not_f'],
                                         reply_markup=Functions.markup(bot, 'friends-menu', user))
                        fr_id = None

                    else:
                        fr_id = res.forward_from.id

                two_user = users.find_one({"userid": fr_id})

                if two_user == None:
                    bot.send_message(message.chat.id, text_dict['not_b'],
                                     reply_markup=Functions.markup(bot, 'friends-menu', user))
                    return

                if two_user == bd_user:
                    bot.send_message(message.chat.id, text_dict['me'],
                                     reply_markup=Functions.markup(bot, 'friends-menu', user))

                else:

                    if 'friends_list' not in bd_user['friends']:
                        bd_user['friends']['friends_list'] = []
                        bd_user['friends']['requests'] = []
                        users.update_one({"userid": bd_user['userid']}, {"$set": {'friends': bd_user['friends']}})

                    if 'friends_list' not in two_user['friends']:
                        two_user['friends']['friends_list'] = []
                        two_user['friends']['requests'] = []
                        users.update_one({"userid": two_user['userid']}, {"$set": {'friends': two_user['friends']}})

                    if bd_user['userid'] not in two_user['friends']['requests'] and bd_user['userid'] not in \
                            two_user['friends']['friends_list'] and two_user['userid'] not in bd_user['friends'][
                        'requests']:

                        two_user['friends']['requests'].append(bd_user['userid'])
                        users.update_one({"userid": two_user['userid']}, {"$set": {'friends': two_user['friends']}})

                        bot.send_message(message.chat.id, f'✔',
                                         reply_markup=Functions.markup(bot, 'friends-menu', user))
                        Functions.notifications_manager(bot, 'friend_request', two_user)

                    else:
                        text = text_dict['already']

                        bot.send_message(message.chat.id, text,
                                         reply_markup=Functions.markup(bot, 'friends-menu', user))

            msg = bot.send_message(message.chat.id, text, reply_markup=rmk)
            bot.register_next_step_handler(msg, ret, bd_user)

    @staticmethod
    def friends_list(bot, message, user, bd_user):

        if bd_user != None:

            friends_id = bd_user['friends']['friends_list']
            page = 1
            text_dict = Functions.get_text(l_key=bd_user['language_code'], text_key="friends")
            buttons_name = Functions.get_text(l_key=bd_user['language_code'], text_key="buttons_name")

            friends_name = []
            friends_id_d = {}

            text = text_dict['wait']

            bot.send_message(message.chat.id, text)

            for i in friends_id:
                try:
                    if users.find_one({"userid": int(i)}) != None:
                        fr_name = bot.get_chat(int(i)).first_name
                        friends_name.append(fr_name)
                        friends_id_d[fr_name] = i
                except:
                    pass

            friends_chunks = list(Functions.chunks(list(Functions.chunks(friends_name, 2)), 3))

            def work_pr(message, friends_id, page, friends_chunks, friends_id_d, mms=None):
                global pages

                text = text_dict['update']

                rmk = types.ReplyKeyboardMarkup(resize_keyboard=True, row_width=3)

                if friends_chunks == []:

                    text = text_dict['null_list']

                    bot.send_message(message.chat.id, text, reply_markup=Functions.markup(bot, 'friends-menu', user))

                else:

                    for el in friends_chunks[page - 1]:
                        if len(el) == 2:
                            rmk.add(el[0], el[1])
                        else:
                            rmk.add(el[0], ' ')

                    if 3 - len(friends_chunks[page - 1]) != 0:
                        for i in list(range(3 - len(friends_chunks[page - 1]))):
                            rmk.add(' ', ' ')

                    if len(friends_chunks) > 1:
                        rmk.add('◀', buttons_name['back'], '▶')

                    else:
                        rmk.add(buttons_name['back'])

                    def ret(message, bd_user, page, friends_chunks, friends_id, friends_id_d):
                        if message.text == buttons_name['back']:
                            res = None
                        else:
                            res = message.text

                        if res == None:
                            text = text_dict['return']

                            bot.send_message(message.chat.id, text,
                                             reply_markup=Functions.markup(bot, 'friends-menu', user))

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

                                    text = Functions.member_profile(bot, fr_id, bd_user['language_code'])

                                    try:
                                        mms = bot.send_message(message.chat.id, text, parse_mode='Markdown')
                                    except Exception as error:
                                        print(message.chat.id, 'ERROR Профиль', '\n', error)
                                        mms = bot.send_message(message.chat.id, text)

                            work_pr(message, friends_id, page, friends_chunks, friends_id_d, mms=mms)

                    if mms == None:
                        msg = bot.send_message(message.chat.id, text, reply_markup=rmk)
                    else:
                        msg = mms
                    bot.register_next_step_handler(msg, ret, bd_user, page, friends_chunks, friends_id, friends_id_d)

            work_pr(message, friends_id, page, friends_chunks, friends_id_d)

    @staticmethod
    def delete_friend(bot, message, user, bd_user):

        if bd_user != None:

            friends_id = bd_user['friends']['friends_list']
            page = 1
            friends_name = []
            id_names = {}
            text_dict = Functions.get_text(l_key=bd_user['language_code'], text_key="friends")
            buttons_name = Functions.get_text(l_key=bd_user['language_code'], text_key="buttons_name")

            for i in friends_id:
                try:
                    fr_name = bot.get_chat(int(i)).first_name
                    friends_name.append(fr_name)
                    id_names[bot.get_chat(int(i)).first_name] = i
                except:
                    pass

            friends_chunks = list(Functions.chunks(list(Functions.chunks(friends_name, 2)), 3))

            if friends_chunks == []:

                text = text_dict['null_list']
                bot.send_message(message.chat.id, text, reply_markup=Functions.markup(bot, 'friends-menu', user))
                return

            else:
                text = text_dict['delete_info']
                bot.send_message(message.chat.id, text, reply_markup=Functions.markup(bot, 'friends-menu', user))

            def work_pr(message, friends_id, page):
                text = text_dict['update']

                rmk = types.ReplyKeyboardMarkup(resize_keyboard=True, row_width=3)

                for el in friends_chunks[page - 1]:
                    if len(el) == 2:
                        rmk.add(el[0], el[1])
                    else:
                        rmk.add(el[0], ' ')

                if 3 - len(friends_chunks[page - 1]) != 0:
                    for i in list(range(3 - len(friends_chunks[page - 1]))):
                        rmk.add(' ', ' ')

                if len(friends_chunks) > 1:
                    rmk.add('◀', buttons_name['back'], '▶')
                else:
                    rmk.add(buttons_name['back'])

                def ret(message, friends_id, page, bd_user):
                    if message.text == buttons_name['back']:
                        res = None
                    else:
                        res = message.text

                    if res == None:
                        text = text_dict['return']

                        bot.send_message(message.chat.id, text, reply_markup=Functions.markup(bot, 'friends-menu', user))
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
                            text = text_dict['delete']

                            try:
                                bd_user['friends']['friends_list'].remove(uid)
                                users.update_one({"userid": bd_user['userid']},
                                                 {"$pull": {'friends.friends_list': uid}})

                            except:
                                pass

                            try:
                                users.update_one({"userid": uid},
                                                 {"$pull": {'friends.friends_list': bd_user['userid']}})
                            except:
                                pass

                            if bd_user['friends']['friends_list'] == []:
                                bot.send_message(message.chat.id, text,
                                                 reply_markup=Functions.markup(bot, 'friends-menu', user))
                                return
                            else:
                                bot.send_message(message.chat.id, text)

                    work_pr(message, friends_id, page)

                msg = bot.send_message(message.chat.id, text, reply_markup=rmk)
                bot.register_next_step_handler(msg, ret, friends_id, page, bd_user)

            work_pr(message, friends_id, page)

    @staticmethod
    def open_profile_menu(bot, message, user, bd_user):

        if bd_user != None:
            text = Functions.get_text(l_key=bd_user['language_code'], text_key="open_profile_menu")
            bot.send_message(message.chat.id, text, reply_markup=Functions.markup(bot, "profile", user))

    @staticmethod
    def rayting(bot, message, user, bd_user):
        markup_inline = types.InlineKeyboardMarkup(row_width=3)
        text_dict = Functions.get_text(l_key=bd_user['language_code'], text_key="rayting")

        text = text_dict['info']
        inl_l = {text_dict['lvl']: 'rayt_lvl', text_dict['money']: 'rayt_money', text_dict['dungeon']: 'rayt_dungeon'
                 }

        markup_inline.add(*[types.InlineKeyboardButton(text=inl, callback_data=inl_l[inl]) for inl in inl_l.keys()])

        bot.send_message(message.chat.id, text, reply_markup=markup_inline)

    @staticmethod
    def open_information(bot, message, user, bd_user):

        if bd_user != None:
            text = Functions.member_profile(bot, user.id, lang=bd_user['language_code'])

            try:
                bot.send_message(message.chat.id, text, parse_mode='Markdown')
            except Exception as error:
                print(message.chat.id, 'ERROR Profile', '\n', error)
                bot.send_message(message.chat.id, text)

    @staticmethod
    def open_action_menu(bot, message, user, bd_user):

        if bd_user != None:
            text = Functions.get_text(l_key=bd_user['language_code'], text_key="open_action_menu")

            bot.send_message(message.chat.id, text, reply_markup=Functions.markup(bot, "actions", user))

    @staticmethod
    def open_dino_tavern(bot, message, user, bd_user):

        if bd_user != None:
            text_dict = Functions.get_text(l_key=bd_user['language_code'], text_key="open_dino_tavern")
            text = text_dict['info']
            text2 = text_dict['friends']

            bot.send_message(message.chat.id, text, reply_markup=Functions.markup(bot, "dino-tavern", user))
            msg = bot.send_message(message.chat.id, text2)

            text = text_dict['friends2']

            fr_in_tav = []

            for fr_id in bd_user['friends']['friends_list']:
                fr_user = users.find_one({"userid": fr_id})
                if fr_user != None:

                    if 'last_markup' in fr_user['settings'].keys() and fr_user['settings'][
                        'last_markup'] == 'dino-tavern':
                        fr_in_tav.append(fr_user)

            if fr_in_tav == []:

                text += '❌'

            else:
                text += '\n'
                for fr_user in fr_in_tav:
                    fr_tel = bot.get_chat(fr_user['userid'])
                    if fr_tel != None:
                        text += f' ● {fr_tel.first_name}\n'

            bot.edit_message_text(text=text, chat_id=msg.chat.id, message_id=msg.message_id)

            for fr_user in fr_in_tav:
                text = Functions.get_text(l_key=fr_user['language_code'], text_key="open_dino_tavern", dp_text_key='went').format(first_name=user.first_name)
                

                time.sleep(0.5)
                bot.send_message(fr_user['userid'], text)

    @staticmethod
    def dino_action_ans(bot, message, user, bd_user):

        if bd_user != None:
            try:
                did = int(message.text.split()[2])

            except:
                pass

            else:
                text_dict = Functions.get_text(l_key=bd_user['language_code'], text_key="dino_action_ans")

                if did == int(bd_user['settings']['dino_id']):
                    ll = list(bd_user['dinos'].keys())
                    ind = list(bd_user['dinos'].keys()).index(str(did))

                    if ind + 1 != len(ll):
                        bd_user['settings']['dino_id'] = ll[ind + 1]

                    else:
                        bd_user['settings']['dino_id'] = ll[0]

                    users.update_one({"userid": bd_user['userid']}, {"$set": {'settings': bd_user['settings']}})

                    if bd_user['dinos'][str(bd_user['settings']['dino_id'])]['status'] == 'incubation':
                        text = text_dict['egg']
                    else:
                        dino_name = bd_user['dinos'][str(bd_user['settings']['dino_id'])]['name']
                        text = text_dict['dino'].format(dino_name=dino_name)

                    bot.send_message(message.chat.id, text, reply_markup=Functions.markup(bot, 'actions', user))

    @staticmethod
    def action_back(bot, message, user, bd_user):

        text = Functions.get_text(l_key=bd_user['language_code'], text_key="action_back")
        bot.send_message(message.chat.id, text, reply_markup=Functions.markup(bot, 'actions', user))

    @staticmethod
    def rename_dino(bot, message, user, bd_user):

        if bd_user != None:
            n_dp, dp_a = Functions.dino_pre_answer(user)
            text_dict = Functions.get_text(l_key=bd_user['language_code'], text_key="rename_dino")
            buttons_name = Functions.get_text(l_key=bd_user['language_code'], text_key="buttons_name")

            if bd_user['dinos'][bd_user['settings']['dino_id']]['status'] == 'dino':

                def rename(message, bd_user, user, dino_user_id, dino):
                    last_name = dino['name']
                    text = text_dict['info'].format(last_name=last_name)
                    ans = [buttons_name['back']]

                    rmk = types.ReplyKeyboardMarkup(resize_keyboard=True)
                    rmk.add(ans[0])

                    def ret(message, ans, bd_user):
                        if message.text == ans[0]:
                            bot.send_message(message.chat.id, f'❌',reply_markup=Functions.markup(bot, 'settings', user))
                            return

                        dino_name = message.text.replace('*', '').replace('`', '').replace('_', '').replace('\\', '').replace('~', '').replace('/', '')

                        if len(dino_name) > 20:
                            text = text_dict['err_more']
                            msg = bot.send_message(message.chat.id, text)

                        else:

                            text = text_dict['rename'].format(last_name=last_name, dino_name=dino_name)
                            ans2 = [buttons_name['confirm'], buttons_name['back']]

                            rmk = types.ReplyKeyboardMarkup(resize_keyboard=True)
                            rmk.add(ans2[0])
                            rmk.add(ans2[1])

                            def ret2(message, ans2, bd_user):
                                if message.text == ans2[1]:
                                    bot.send_message(message.chat.id, f'❌',reply_markup=Functions.markup(bot, 'settings', user))
                                    return
                                else:
                                    res = message.text

                                if res == buttons_name['confirm']:
                                    bd_user['dinos'][str(dino_user_id)]['name'] = dino_name
                                    users.update_one({"userid": bd_user['userid']}, {"$set": {f'dinos.{dino_user_id}': bd_user['dinos'][str(dino_user_id)]}})

                                    bot.send_message(message.chat.id, f'✅',reply_markup=Functions.markup(bot, 'settings', user))

                            msg = bot.send_message(message.chat.id, text, reply_markup=rmk)
                            bot.register_next_step_handler(msg, ret2, ans2, bd_user)

                    msg = bot.send_message(message.chat.id, text, reply_markup=rmk)
                    bot.register_next_step_handler(msg, ret, ans, bd_user)

                if n_dp == 1:
                    bot.send_message(message.chat.id, f'❌', reply_markup=Functions.markup(bot, 'settings', user))
                    return

                if n_dp == 2:
                    bd_dino = dp_a
                    rename(message, bd_user, user, list(bd_user['dinos'].keys())[0], bd_dino)

                if n_dp == 3:
                    rmk = dp_a[0]
                    text = dp_a[1]
                    dino_dict = dp_a[2]

                    def ret(message, dino_dict, user, bd_user):
                        if message.text not in dino_dict.keys():
                            bot.send_message(message.chat.id, f'❌', reply_markup=Functions.markup(bot, 'settings', user))

                        else:
                            rename(message, bd_user, user, dino_dict[message.text][1], dino_dict[message.text][0])

                    msg = bot.send_message(message.chat.id, text, reply_markup=rmk)
                    bot.register_next_step_handler(msg, ret, dino_dict, user, bd_user)

    @staticmethod
    def dino_sleep_ac(bot, message, user, bd_user):

        if bd_user != None:
            dino = bd_user['dinos'][str(bd_user['settings']['dino_id'])]
            text_dict = Functions.get_text(l_key=bd_user['language_code'], text_key="dino_sleep_ac")
            buttons_name = Functions.get_text(l_key=bd_user['language_code'], text_key="buttons_name")

            if dino != None:
                if dino['activ_status'] == 'pass_active':
                    if dino['stats']['unv'] >= 90:
                        text = text_dict['d_want']

                        bot.send_message(message.chat.id, text, reply_markup=Functions.markup(bot, "actions", user))

                    else:
                        def dl_sleep(bd_user, message):
                            d_id = bd_user['settings']['dino_id']
                            bd_user['dinos'][d_id]['activ_status'] = 'sleep'
                            bd_user['dinos'][d_id]['sleep_start'] = int(time.time())
                            bd_user['dinos'][d_id]['sleep_type'] = 'long'
                            users.update_one({"userid": bd_user['userid']},
                                             {"$set": {f'dinos.{d_id}': bd_user['dinos'][d_id]}})

                            text = text_dict['sleep']
                            bot.send_message(message.chat.id, text, reply_markup=Functions.markup(bot, 'actions', user))

                        if Functions.acc_check(bot, bd_user, '16', bd_user['settings']['dino_id'], True) == False:
                            dl_sleep(bd_user, message)

                        else:
                            text = text_dict['sleep']
                            ans = text_dict['buttons']
                            ans.append(buttons_name['back'])

                            rmk = types.ReplyKeyboardMarkup(resize_keyboard=True)
                            rmk.add(ans[0], ans[1])
                            rmk.add(ans[2])

                            def ret(message, ans, bd_user):

                                if message.text not in ans or message.text == ans[2]:
                                    res = None
                                else:
                                    res = message.text

                                if res == None:
                                    bot.send_message(message.chat.id, f'❌',
                                                     reply_markup=Functions.markup(bot, 'actions', user))
                                    return

                                if res == text_dict['buttons'][0]:
                                    dl_sleep(bd_user, message)

                                if res == text_dict['buttons'][1]:

                                    def ret2(message, ans, bd_user):

                                        if message.text == ans[0]:
                                            number = None
                                        else:

                                            try:
                                                number = int(message.text)
                                            except:
                                                number = None

                                        if number == None:
                                            bot.send_message(message.chat.id, f'❌',
                                                             reply_markup=Functions.markup(bot, 'actions', user))
                                            return

                                        if number <= 5 or number > 480:
                                            text = text_dict['err_time']

                                            bot.send_message(message.chat.id, text,
                                                             reply_markup=Functions.markup(bot, 'actions', user))

                                        else:
                                            d_id = bd_user['settings']['dino_id']
                                            bd_user['dinos'][d_id]['activ_status'] = 'sleep'
                                            bd_user['dinos'][d_id]['sleep_time'] = int(time.time()) + number * 60
                                            bd_user['dinos'][d_id]['sleep_type'] = 'short'
                                            users.update_one({"userid": bd_user['userid']},
                                                             {"$set": {f'dinos.{d_id}': bd_user['dinos'][d_id]}})

                                            text = text_dict['sleep']
                                            bot.send_message(message.chat.id, text,
                                                             reply_markup=Functions.markup(bot, 'actions', user))

                                    ans = [buttons_name['back']]
                                    text = text_dict['choice_time']

                                    rmk = types.ReplyKeyboardMarkup(resize_keyboard=True)
                                    rmk.add(ans[0])

                                    msg = bot.send_message(message.chat.id, text, reply_markup=rmk)
                                    bot.register_next_step_handler(msg, ret2, ans, bd_user)

                            msg = bot.send_message(message.chat.id, text, reply_markup=rmk)
                            bot.register_next_step_handler(msg, ret, ans, bd_user)

                else:
                    text = text_dict['alredy_busy']

                    bot.send_message(message.chat.id, text,
                                     reply_markup=Functions.inline_markup(bot, f'open_dino_profile', message.chat.id, ['Открыть профиль', 'Open a profile'], str(bd_user['settings']['dino_id'])))

    @staticmethod
    def dino_unsleep_ac(bot, message, user, bd_user):

        if bd_user != None:
            d_id = str(bd_user['settings']['dino_id'])
            dino = bd_user['dinos'][str(d_id)]

            text_dict = Functions.get_text(l_key=bd_user['language_code'], text_key="dino_unsleep_ac")

            if dino['activ_status'] == 'sleep' and dino != None:
                r_n = random.randint(0, 20)
                bd_user['dinos'][d_id]['activ_status'] = 'pass_active'

                if 'sleep_type' in bd_user['dinos'][d_id] and bd_user['dinos'][d_id]['sleep_type'] == 'short':

                    del bd_user['dinos'][d_id]['sleep_time']
                    text = text_dict['awaked']

                    bot.send_message(message.chat.id, text, reply_markup=Functions.markup(bot, 'actions', user))

                    try:
                        del bd_user['dinos'][d_id]['sleep_type']
                    except:
                        pass

                    try:
                        del bd_user['dinos'][d_id]['sleep_start']
                    except:
                        pass

                    users.update_one({"userid": bd_user['userid']}, {"$set": {f'dinos.{d_id}': bd_user['dinos'][d_id]}})

                elif 'sleep_type' not in bd_user['dinos'][d_id] or bd_user['dinos'][d_id]['sleep_type'] == 'long':

                    if 'sleep_start' in bd_user['dinos'][d_id].keys() and int(time.time()) - bd_user['dinos'][d_id][
                        'sleep_start'] >= 8 * 3600:
                        text = text_dict['awaked']

                        bot.send_message(message.chat.id, text, reply_markup=Functions.markup(bot, 'actions', user))

                    else:

                        bd_user['dinos'][d_id]['stats']['mood'] -= r_n

                        if bd_user['dinos'][d_id]['stats']['mood'] < 0:
                            bd_user['dinos'][d_id]['stats']['mood'] = 0

                        text = text_dict['awaked_mood'].format(r_n=r_n)

                        bot.send_message(message.chat.id, text, reply_markup=Functions.markup(bot, 'actions', user))

                    try:
                        del bd_user['dinos'][d_id]['sleep_type']
                    except:
                        pass

                    try:
                        del bd_user['dinos'][d_id]['sleep_start']
                    except:
                        pass

                    users.update_one({"userid": bd_user['userid']}, {"$set": {f'dinos.{d_id}': bd_user['dinos'][d_id]}})

            else:
                bot.send_message(message.chat.id, f'❌', reply_markup=Functions.markup(bot, 'actions', user))

    @staticmethod
    def dino_journey(bot, message, user, bd_user):

        if bd_user != None:
            dino = bd_user['dinos'][str(bd_user['settings']['dino_id'])]

            if dino['activ_status'] == 'pass_active' and dino != None:
                markup_inline = types.InlineKeyboardMarkup()

                if bd_user['language_code'] == 'ru':
                    text = '🌳 На какое время отправить динозавра в путешествие?'

                    item_0 = types.InlineKeyboardButton(text='10 мин.',
                                callback_data=f"10min_journey_{str(bd_user['settings']['dino_id'])}")

                    item_1 = types.InlineKeyboardButton(text='30 мин.',
                                callback_data=f"30min_journey_{str(bd_user['settings']['dino_id'])}")

                    item_2 = types.InlineKeyboardButton(text='60 мин.',
                                callback_data=f"60min_journey_{str(bd_user['settings']['dino_id'])}")

                    item_3 = types.InlineKeyboardButton(text='90 мин.',
                                callback_data=f"90min_journey_{str(bd_user['settings']['dino_id'])}")

                    item_4 = types.InlineKeyboardButton(text='120 мин.',
                                callback_data=f"12min_journey_{str(bd_user['settings']['dino_id'])}")

                    item_5 = types.InlineKeyboardButton(text='240 мин.',
                                callback_data=f"24min_journey_{str(bd_user['settings']['dino_id'])}")

                else:
                    text = "🌳 How long to send a dinosaur on a journey?"

                    item_0 = types.InlineKeyboardButton(text='10 min.',
                                callback_data=f"10min_journey_{str(bd_user['settings']['dino_id'])}")

                    item_1 = types.InlineKeyboardButton(text='30 min.',
                                callback_data=f"30min_journey_{str(bd_user['settings']['dino_id'])}")

                    item_2 = types.InlineKeyboardButton(text='60 min.',
                                callback_data=f"60min_journey_{str(bd_user['settings']['dino_id'])}")

                    item_3 = types.InlineKeyboardButton(text='90 min.',
                                callback_data=f"90min_journey_{str(bd_user['settings']['dino_id'])}")

                    item_4 = types.InlineKeyboardButton(text='120 min.',
                                callback_data=f"12min_journey_{str(bd_user['settings']['dino_id'])}")

                    item_5 = types.InlineKeyboardButton(text='240 min.',
                                callback_data=f"24min_journey_{str(bd_user['settings']['dino_id'])}")

                markup_inline.add(item_0, item_1, item_2, item_3, item_4)
                markup_inline.add(item_5)

                bot.send_message(message.chat.id, text, reply_markup=markup_inline)

            else:

                if bd_user['language_code'] == 'ru':
                    text = f"❗ | Ваш динозавр уже чем то занят, проверьте профиль!"

                else:
                    text = f"❗ | Your dinosaur is already busy with something, check the profile!"

                bot.send_message(message.chat.id, text,
                                 reply_markup=Functions.inline_markup(bot, f'open_dino_profile', message.chat.id, ['Открыть профиль', 'Open a profile'], str(bd_user['settings']['dino_id'])))

    @staticmethod
    def dino_unjourney(bot, message, user, bd_user):

        if bd_user != None:
            dino = bd_user['dinos'][str(bd_user['settings']['dino_id'])]

            if dino['activ_status'] == 'journey' and dino != None:
                if random.randint(1, 2) == 1:

                    dino_id = bd_user['settings']['dino_id']

                    Functions.journey_end_log(bot, bd_user['userid'], dino_id)

                    bd_user['dinos'][dino_id]['activ_status'] = 'pass_active'

                    del bd_user['dinos'][dino_id]['journey_time']
                    del bd_user['dinos'][dino_id]['journey_log']

                    users.update_one({"userid": bd_user['userid']},
                                     {"$set": {f"dinos.{dino_id}": bd_user['dinos'][dino_id]}})


                else:
                    if bd_user['language_code'] == 'ru':
                        text = f'🔇 | Вы попробовали вернуть динозавра, но что-то пошло не так...'
                    else:
                        text = f"🔇 | You tried to bring the dinosaur back, but something went wrong..."

                    bot.send_message(message.chat.id, text, reply_markup=Functions.markup(bot, 'actions', user))
            else:
                bot.send_message(message.chat.id, f'❌', reply_markup=Functions.markup(bot, 'actions', user))

    @staticmethod
    def dino_entert(bot, message, user, bd_user):

        if bd_user != None:
            dino = bd_user['dinos'][str(bd_user['settings']['dino_id'])]

            if dino['activ_status'] in ['pass_active', 'game']:

                if bd_user['language_code'] == 'ru':
                    text = f"🎮 | Перенаправление в меню развлечений!"

                else:
                    text = f"🎮 | Redirecting to the entertainment menu!"

                bot.send_message(message.chat.id, text, reply_markup=Functions.markup(bot, 'games', user))

            else:

                if bd_user['language_code'] == 'ru':
                    text = f"❗ | Ваш динозавр уже чем то занят, проверьте профиль!"

                else:
                    text = f"❗ | Your dinosaur is already busy with something, check the profile!"

                bot.send_message(message.chat.id, text,
                                 reply_markup=Functions.inline_markup(bot, f'open_dino_profile', message.chat.id, ['Открыть профиль', 'Open a profile'], str(bd_user['settings']['dino_id'])))

    @staticmethod
    def dino_entert_games(bot, message, user, bd_user):

        if bd_user != None:
            dino = bd_user['dinos'][str(bd_user['settings']['dino_id'])]
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
                    if Functions.acc_check(bot, bd_user, '44', str(bd_user['settings']['dino_id']), True):

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

                item_1 = types.InlineKeyboardButton(text=text[0],
                                callback_data=f"1_{g}_game_{str(bd_user['settings']['dino_id'])}")
                item_2 = types.InlineKeyboardButton(text=text[1],
                                callback_data=f"2_{g}_game_{str(bd_user['settings']['dino_id'])}")
                item_3 = types.InlineKeyboardButton(text=text[2],
                                callback_data=f"3_{g}_game_{str(bd_user['settings']['dino_id'])}")
                markup_inline.add(item_1, item_2, item_3)

                bot.send_message(message.chat.id, m_text, reply_markup=markup_inline)

    @staticmethod
    def dino_stop_games(bot, message, user, bd_user):

        if bd_user != None:
            dino = bd_user['dinos'][str(bd_user['settings']['dino_id'])]
            if dino['activ_status'] == 'game':

                if dino['game_%'] == 1:
                    rt = random.randint(1, 3)

                if dino['game_%'] == 0.5:
                    rt = 1

                if dino['game_%'] == 0.9:
                    rt = random.randint(1, 2)

                if rt == 1:

                    if dino['game_%'] == 1:
                        bd_user['dinos'][str(bd_user['settings']['dino_id'])]['stats']['mood'] -= 20

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
                        bd_user['dinos'][str(bd_user['settings']['dino_id'])]['stats']['mood'] -= 5

                        if bd_user['language_code'] == 'ru':
                            text = f"🎮 | Динозавр немного расстроен что вы его отвлекли, он теряет 5% настроения..."

                        else:
                            text = f"🎮 | The dinosaur is a little upset that you distracted him, he loses 5% of his mood..."

                    dino_id = str(bd_user['settings']['dino_id'])

                    game_time = (int(time.time()) - bd_user['dinos'][dino_id]['game_start']) // 60

                    Dungeon.check_quest(bot, bd_user, met='check', quests_type='do',
                                        kwargs={'dp_type': 'game', 'act': game_time})

                    bd_user['dinos'][dino_id]['activ_status'] = 'pass_active'

                    try:
                        del bd_user['dinos'][dino_id]['game_time']
                        del bd_user['dinos'][dino_id]['game_%']
                        del bd_user['dinos'][dino_id]['game_start']
                    except:
                        pass

                    users.update_one({"userid": bd_user['userid']},
                                     {"$set": {f'dinos.{dino_id}': bd_user['dinos'][dino_id]}})

                    bot.send_message(message.chat.id, text, reply_markup=Functions.markup(bot, 'games', user))

                else:

                    if bd_user['language_code'] == 'ru':
                        text = f"🎮 | Динозавра невозможно оторвать от игры, попробуйте ещё раз. Имейте ввиду, динозавр будет расстроен."

                    else:
                        text = f"🎮 | It is impossible to tear the dinosaur away from the game, try again. Keep in mind, the dinosaur will be upset."

                    bot.send_message(message.chat.id, text, reply_markup=Functions.markup(bot, 'games', user))

    @staticmethod
    def collecting_food(bot, message, user, bd_user):

        eat_c = Functions.items_counting(bd_user, '+eat')
        if eat_c >= settings_f['max_eat_items']:

            if bd_user['language_code'] == 'ru':
                text = f'🌴 | Ваш инвентарь ломится от количества еды! В данный момент у вас {eat_c} предметов которые можно съесть!'
            else:
                text = f'🌴 | Your inventory is bursting with the amount of food! At the moment you have {eat_c} items that can be eaten!'

            bot.send_message(message.chat.id, text, reply_markup=Functions.markup(bot, 'actions', user))
            return

        if bd_user['dinos'][bd_user['settings']['dino_id']]['activ_status'] == 'pass_active':

            if bd_user['language_code'] == 'ru':
                bbt = ['🌿 | Собирательство', '🍖 | Охота', '🍤 | Рыбалка', '🥗 | Все вместе', '↩ Назад']
                text = '🌴 | Выберите способ добычи продовольствия >'
            else:
                bbt = ['🌿 | Collecting', '🍖 | Hunting', '🍤 | Fishing', '🥗 | All together', '↩ Back']
                text = '🌴 | Choose a way to get food >'

            rmk = types.ReplyKeyboardMarkup(resize_keyboard=True)
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

                    bot.send_message(message.chat.id, text, reply_markup=Functions.markup(bot, 'actions', user))

                else:

                    if bd_user['language_code'] == 'ru':
                        ans = ['↩ Назад']
                        text = '🍽 | Введите число продуктов, которое должен собрать динозавр >'
                    else:
                        ans = ['↩ Back']
                        text = '🍽 | Enter the number of products that the dinosaur must collect >'

                    rmk = types.ReplyKeyboardMarkup(resize_keyboard=True)
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

                            bot.send_message(message.chat.id, text, reply_markup=Functions.markup(bot, 'actions', user))

                        else:
                            bd_user['dinos'][bd_user['settings']['dino_id']]['activ_status'] = 'hunting'
                            bd_user['dinos'][bd_user['settings']['dino_id']]['target'] = [0, number]

                            if res == bbt[0]:
                                bd_user['dinos'][bd_user['settings']['dino_id']]['h_type'] = 'collecting'

                                if bd_user['language_code'] == 'ru':
                                    text = f'🌿 | Сбор ягод и трав начат!\n♻ | Текущий прогресс: 0%\n🎲 | Цель: {number}'
                                else:
                                    text = f'🌿 | The gathering of berries and herbs has begun!\n♻ | Current progress: 0%\n🎲 | Goal: {number}'

                            if res == bbt[1]:
                                bd_user['dinos'][bd_user['settings']['dino_id']]['h_type'] = 'hunting'

                                if bd_user['language_code'] == 'ru':
                                    text = f'🍖 | Охота началась!\n♻ | Текущий прогресс: 0%\n🎲 | Цель: {number}'
                                else:
                                    text = f'🍖 | The hunt has begun!\n♻ | Current progress: 0%\n🎲 | Goal: {number}'

                            if res == bbt[2]:
                                bd_user['dinos'][bd_user['settings']['dino_id']]['h_type'] = 'fishing'

                                if bd_user['language_code'] == 'ru':
                                    text = f'🍣 | Рыбалка началась!\n♻ | Текущий прогресс: 0%\n🎲 | Цель: {number}'
                                else:
                                    text = f'🍣 | Fishing has begun!\n♻ | Current progress: 0%\n🎲 | Goal: {number}'

                            if res == bbt[3]:
                                bd_user['dinos'][bd_user['settings']['dino_id']]['h_type'] = 'all'

                                if bd_user['language_code'] == 'ru':
                                    text = f'🍱 | Общий сбор пищи начат!\n♻ | Текущий прогресс: 0%\n🎲 | Цель: {number}'
                                else:
                                    text = f'🍱 | The general food collection has begun!\n♻ | Current progress: 0%\n🎲 | Goal: {number}'

                            users.update_one({"userid": bd_user['userid']}, {"$set": {'dinos': bd_user['dinos']}})
                            bot.send_message(message.chat.id, text, reply_markup=Functions.markup(bot, 'actions', user))

                    msg = bot.send_message(message.chat.id, text, reply_markup=rmk)
                    bot.register_next_step_handler(msg, ret2, ans, bd_user)

            msg = bot.send_message(message.chat.id, text, reply_markup=rmk)
            bot.register_next_step_handler(msg, ret, bbt, bd_user)

        else:

            if bd_user['language_code'] == 'ru':
                text = f"❗ | Ваш динозавр уже чем то занят, проверьте профиль!"

            else:
                text = f"❗ | Your dinosaur is already busy with something, check the profile!"

            bot.send_message(message.chat.id, text,
                             reply_markup=Functions.inline_markup(bot, f'open_dino_profile', message.chat.id, ['Открыть профиль', 'Open a profile'], str(bd_user['settings']['dino_id'])))

    @staticmethod
    def coll_progress(bot, message, user, bd_user):
        markup_inline = types.InlineKeyboardMarkup()

        if bd_user['dinos'][bd_user['settings']['dino_id']]['activ_status'] == 'hunting':
            number = bd_user['dinos'][bd_user['settings']['dino_id']]['target'][0]
            tnumber = bd_user['dinos'][bd_user['settings']['dino_id']]['target'][1]
            prog = number / (tnumber / 100)

            if bd_user['language_code'] == 'ru':
                text = f'🍱 | Текущий прогресс: {int(prog)}%\n🎲 | Цель: {tnumber}'
                inl_l = {'❌ Отменить': f"cancel_progress {bd_user['settings']['dino_id']}"}

            else:
                text = f'🍱 | Current progress: {int(prog)}%\n🎲 | Goal: {tnumber}'
                inl_l = {'❌ Cancel': f"cancel_progress {bd_user['settings']['dino_id']}"}

            markup_inline.add(
                *[types.InlineKeyboardButton(text=inl, callback_data=f"{inl_l[inl]}") for inl in inl_l.keys()])
            bot.send_message(message.chat.id, text, reply_markup=markup_inline)

    @staticmethod
    def invite_friend(bot, message, user, bd_user):

        if bd_user != None:
            coins = 200

            if bd_user['language_code'] == 'ru':
                text = f"🤍 | Перенаправление в меню реферальной системы!\n\n💜 | При достижению 5-го уровня вашим другом, вы получите 🥚 Необычное/Редкое яйцо динозавра!\n\n❤ | Друг получит бонус в размере: {coins} монет, 🍯 Баночка мёда х2, 🧸 Мишка, 🍗 Куриная ножка x2, 🍒 Ягоды x2, 🦪 Мелкая рыба x2, 🍪 Печенье x2"

            else:
                text = f"🤍 | Redirection to the referral system menu!\n\n💜 | When your friend reaches the 5th level, you will receive an Unusual/Rare dinosaur egg!\n\n❤ | Friend will receive a bonus: {coins} coins, 🍯 Jar of honey x2, 🧸 Bear, 🍗 Chicken leg x2, 🍒 Berries x2, 🦪 Small fish x2, 🍪 Cookies x2"

            bot.send_message(message.chat.id, text, reply_markup=Functions.markup(bot, "referal-system", user))

    @staticmethod
    def friends_menu(bot, message, user, bd_user):

        if bd_user != None:

            if bd_user['language_code'] == 'ru':
                text = f"👥 | Перенаправление в меню друзей!"
            else:
                text = f"👥 | Redirecting to the friends menu!"

            bot.send_message(message.chat.id, text, reply_markup=Functions.markup(bot, "friends-menu", user))

    @staticmethod
    def generate_fr_code(bot, message, user, bd_user):

        if bd_user != None:
            if 'referal_system' not in bd_user.keys():
                rf = management.find_one({"_id": 'referal_system'})

                def r_cod():
                    code_rf = ''
                    for i in range(6):
                        code_rf += str(random.randint(0, 9))
                    return code_rf

                rf_code = r_cod()
                while rf_code in rf['codes']:
                    rf_code = r_cod()

                rf['codes'].append(rf_code)
                management.update_one({"_id": 'referal_system'}, {"$set": {'codes': rf['codes']}})

                bd_user['referal_system'] = {'my_cod': rf_code, 'friend_cod': None}
                users.update_one({"userid": bd_user['userid']}, {"$set": {'referal_system': bd_user['referal_system']}})

                if bd_user['language_code'] == 'ru':
                    text = f"🎲 | Ваш код сгенерирован!\nКод: `{rf_code}`"

                else:
                    text = f"🎲 | Your code is generated!\nСode: `{rf_code}`"

                bot.send_message(message.chat.id, text, parse_mode='Markdown',
                                 reply_markup=Functions.markup(bot, "referal-system", user))

    @staticmethod
    def enter_fr_code(bot, message, user, bd_user):

        rf = management.find_one({"_id": 'referal_system'})

        def ret(message, bd_user):
            if message.text in rf['codes']:
                if str(bd_user['referal_system']['my_cod']) != message.text:
                    items = ['1', '1', '2', '2', '16', '12', '12', '11', '11', '13', '13']
                    coins = 200
                    bd_user['coins'] += coins
                    for i in items:
                        Functions.add_item_to_user(bd_user, i)

                    members = users.find({})
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
                        users.update_one({"userid": bd_user['userid']}, {"$set": {'friends': bd_user['friends']}})

                    if bd_user['userid'] not in fr_member['friends']['friends_list']:
                        fr_member['friends']['friends_list'].append(bd_user['userid'])
                        users.update_one({"userid": fr_member['userid']}, {"$set": {'friends': fr_member['friends']}})

                    bd_user['referal_system']['friend_cod'] = message.text
                    bd_user['referal_system']['friend'] = fr_member['userid']

                    users.update_one({"userid": bd_user['userid']}, {"$set": {'coins': bd_user['coins']}})

                    users.update_one({"userid": bd_user['userid']},
                                     {"$set": {'referal_system': bd_user['referal_system']}})

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

            bot.send_message(message.chat.id, text, reply_markup=Functions.markup(bot, "referal-system", user))

        if bd_user != None:
            if 'referal_system' not in bd_user.keys():
                rf = management.find_one({"_id": 'referal_system'})

                def r_cod():
                    code_rf = ''
                    for i in range(6):
                        code_rf += str(random.randint(0, 9))
                    return code_rf

                rf_code = r_cod()
                while rf_code in rf['codes']:
                    rf_code = r_cod()

                rf['codes'].append(rf_code)
                management.update_one({"_id": 'referal_system'}, {"$set": {'codes': rf['codes']}})

                bd_user['referal_system'] = {'my_cod': rf_code, 'friend_cod': None}
                users.update_one({"userid": bd_user['userid']}, {"$set": {'referal_system': bd_user['referal_system']}})

                if bd_user['language_code'] == 'ru':
                    text = f"🎲 | Ваш код сгенерирован!\nКод: `{rf_code}`"

                else:
                    text = f"🎲 | Your code is generated!\nСode: `{rf_code}`"

                bot.send_message(message.chat.id, text, parse_mode='Markdown',
                                 reply_markup=Functions.markup(bot, "referal-system", user))

                if bd_user['language_code'] == 'ru':
                    ans = ['↪ Назад']
                    text = '👥 | Введите код-приглашение друга > '
                else:
                    ans = ['↪ Back']
                    text = "👥 | Enter a friend's invitation code >"

                rmk = types.ReplyKeyboardMarkup(resize_keyboard=True)
                rmk.add(ans[0])

                msg = bot.send_message(message.chat.id, text, reply_markup=rmk)
                bot.register_next_step_handler(msg, ret, bd_user)

            else:
                if bd_user['referal_system']['friend_cod'] == None:

                    if bd_user['language_code'] == 'ru':
                        ans = ['↪ Назад']
                        text = '👥 | Введите код-приглашение друга > '
                    else:
                        ans = ['↪ Back']
                        text = "👥 | Enter a friend's invitation code >"

                    rmk = types.ReplyKeyboardMarkup(resize_keyboard=True)
                    rmk.add(ans[0])

                    msg = bot.send_message(message.chat.id, text, reply_markup=rmk)
                    bot.register_next_step_handler(msg, ret, bd_user)

                else:
                    if bd_user['language_code'] == 'ru':
                        text = '👥 | Вы уже ввели код друга!'
                    else:
                        text = "👥 | You have already entered a friend's code!"

                    msg = bot.send_message(message.chat.id, text)

    @staticmethod
    def acss(bot, message, user, bd_user):

        if bd_user != None:

            if len(bd_user['dinos']) > 1:
                for i in bd_user['dinos'].keys():
                    if i not in bd_user['activ_items'].keys():
                        users.update_one({"userid": bd_user["userid"]}, {
                            "$set": {f'activ_items.{i}': {'game': None, 'hunt': None, 'journey': None, 'unv': None}}})

            def acss(message, dino_id, user, bd_user):

                if bd_user['dinos'][dino_id]['status'] != 'dino':

                    if bd_user['language_code'] == 'ru':
                        text = '🎍 | Динозавр должен быть инкубирован!'
                    else:
                        text = '🎍 | The dinosaur must be incubated!'

                    bot.send_message(message.chat.id, text, reply_markup=Functions.markup(bot, 'profile', user))
                    return

                if bd_user['dinos'][dino_id]['activ_status'] != 'pass_active':

                    if bd_user['language_code'] == 'ru':
                        text = '🎍 | Во время игры / сна / путешествия и тд. - нельзя менять аксесcуар!'
                    else:
                        text = '🎍 | While playing / sleeping / traveling, etc. - you can not change the accessory!'

                    bot.send_message(message.chat.id, text, reply_markup=Functions.markup(bot, 'profile', user))
                    return

                if bd_user['language_code'] == 'ru':
                    ans = ['🕹 Игра', '🌙 Сон', '🌿 Сбор пищи', '🏮 Путешествие', '↪ Назад']
                    text = '🎍 | Выберите какого аспекта должен быть аксесcуар >'
                else:
                    ans = ['🕹 Game', '🌙 Dream', '🌿 Collecting food', '🏮 Journey', '↪ Back']
                    text = '🎍 | Choose which aspect the accessory should be >'

                rmk = types.ReplyKeyboardMarkup(resize_keyboard=True)
                rmk.add(ans[0], ans[1])
                rmk.add(ans[2], ans[3])
                rmk.add(ans[4])

                def ret_zero(message, ans, bd_user):

                    if message.text not in ans or message.text == ans[4]:
                        res = None
                    else:
                        res = message.text

                    if res == None:
                        bot.send_message(message.chat.id, f'❌', reply_markup=Functions.markup(bot, 'profile', user))
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

                        bot.send_message(message.chat.id, text, reply_markup=Functions.markup(bot, 'profile', user))
                        return

                    data_items = items_f['items']
                    items = []
                    items_id = {}
                    page = 1
                    items_names = []

                    for i in nitems:
                        if data_items[str(i['item_id'])]['type'] == f"{ac_type}_ac":
                            items.append(i)

                    lg = bd_user['language_code']

                    for i in items:
                        items_id[items_f['items'][str(i['item_id'])]['name'][lg]] = i
                        items_names.append(items_f['items'][str(i['item_id'])]['name'][lg])

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

                    pages = list(Functions.chunks(list(Functions.chunks(items_sort, 2)), 2))

                    if len(pages) == 0:
                        pages = [[]]

                    for i in pages:
                        for ii in i:
                            if len(ii) == 1:
                                ii.append(' ')

                        if len(i) != 2:
                            for iii in range(2 - len(i)):
                                i.append([' ', ' '])

                    def work_pr(message, pages, page, items_id, ind_sort_it, lg, ac_type):

                        l_pages = pages
                        l_page = page
                        l_ind_sort_it = ind_sort_it

                        rmk = types.ReplyKeyboardMarkup(resize_keyboard=True, row_width=3)
                        for i in pages[page - 1]:
                            rmk.add(i[0], i[1])

                        act_item = []
                        if bd_user['activ_items'][dino_id][ac_type] == None:
                            act_item = ['нет', 'no']
                        else:
                            act_item = [
                                items_f['items'][bd_user['activ_items'][dino_id][ac_type]['item_id']]['name']['ru'],
                                items_f['items'][bd_user['activ_items'][dino_id][ac_type]['item_id']]['name']['en']]

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

                        def ret(message, l_pages, l_page, l_ind_sort_it, bd_user, user, pages, page, items_id,
                                ind_sort_it, lg, ac_type):
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

                                bot.send_message(message.chat.id, text,
                                                 reply_markup=Functions.markup(bot, 'profile', user))
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
                                        if bd_user['activ_items'][dino_id][ac_type] != None:
                                            item = bd_user['activ_items'][dino_id][ac_type]
                                            bd_user['activ_items'][dino_id][ac_type] = None

                                            if bd_user['language_code'] == 'ru':
                                                text = "🎴 | Активный предмет снят"
                                            else:
                                                text = "🎴 | Active item removed"

                                            users.update_one({"userid": bd_user['userid']},
                                                    {"$push": {'inventory': item}})
                                            users.update_one({"userid": bd_user['userid']},
                                                    {"$set": {'activ_items': bd_user['activ_items']}})

                                        else:
                                            if bd_user['language_code'] == 'ru':
                                                text = "🎴 | В данный момент нет активного предмета!"
                                            else:
                                                text = "🎴 | There is no active item at the moment!"

                                        bot.send_message(message.chat.id, text,
                                                         reply_markup=Functions.markup(bot, 'profile', user))

                                    else:
                                        if bd_user['activ_items'][dino_id][ac_type] != None:
                                            bd_user['inventory'].append(bd_user['activ_items'][dino_id][ac_type])

                                        item = items_id[l_ind_sort_it[res]]

                                        bd_user['activ_items'][dino_id][ac_type] = item

                                        if bd_user['language_code'] == 'ru':
                                            text = "🎴 | Активный предмет установлен!"
                                        else:
                                            text = "🎴 | The active item is installed!"

                                        bd_user['inventory'].remove(item)
                                        users.update_one({"userid": bd_user['userid']},
                                                         {"$set": {'inventory': bd_user['inventory']}})

                                        users.update_one({"userid": bd_user['userid']},
                                                         {"$set": {'activ_items': bd_user['activ_items']}})

                                        bot.send_message(message.chat.id, text,
                                                         reply_markup=Functions.markup(bot, 'profile', user))

                        msg = bot.send_message(message.chat.id, textt, reply_markup=rmk)
                        bot.register_next_step_handler(msg, ret, l_pages, l_page, l_ind_sort_it, bd_user, user, pages,
                                                       page, items_id, ind_sort_it, lg, ac_type)

                    work_pr(message, pages, page, items_id, ind_sort_it, lg, ac_type)

                msg = bot.send_message(message.chat.id, text, reply_markup=rmk)
                bot.register_next_step_handler(msg, ret_zero, ans, bd_user)

            n_dp, dp_a = Functions.dino_pre_answer(user)
            if n_dp == 1:
                bot.send_message(message.chat.id, f'❌', reply_markup=Functions.markup(bot, 1, user))
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
                        bot.send_message(message.chat.id, '❓', reply_markup=Functions.markup(bot, "profile", user))

                msg = bot.send_message(message.chat.id, text, reply_markup=rmk)
                bot.register_next_step_handler(msg, ret, dino_dict, user, bd_user)

    @staticmethod
    def open_market_menu(bot, message, user, bd_user):

        if bd_user != None:

            if bd_user['language_code'] == 'ru':
                text = '🛒 Панель рынка открыта!'
            else:
                text = '🛒 The market panel is open!'

            bot.send_message(message.chat.id, text, reply_markup=Functions.markup(bot, "market", user))

    @staticmethod
    def my_products(bot, message, user, bd_user):

        if bd_user != None:

            market_ = management.find_one({"_id": 'products'})
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

                pages = list(Functions.chunks(products, 5))

                if bd_user['language_code'] == 'ru':
                    text = '🛒 | *Ваши продукты*\n\n'
                else:
                    text = '🛒 | *Your products*\n\n'

                rmk = types.ReplyKeyboardMarkup(resize_keyboard=True, row_width=3)

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

                    w_page = pages[page - 1]

                    nn = (page - 1) * 5
                    for pr in w_page:
                        item = items_f['items'][pr['item']['item_id']]
                        nn += 1

                        if int(w_page.index(pr)) == len(w_page) - 1:
                            n = '└'
                        elif int(w_page.index(pr)) == 0:
                            n = '┌'
                        else:
                            n = '├'

                        if bd_user['language_code'] == 'ru':
                            text += f"*{n}* {nn}# {item['name']['ru']}\n    *└* Цена за 1х: {pr['price']}\n"
                            text += f"       *└* Продано: {pr['col'][0]} / {pr['col'][1]}"

                            if 'abilities' in pr['item'].keys():
                                if 'uses' in pr['item']['abilities'].keys():
                                    text += f"\n           *└* Использований: {pr['item']['abilities']['uses']}"

                                if 'endurance' in pr['item']['abilities'].keys():
                                    text += f"\n           *└* Прочность: {pr['item']['abilities']['endurance']}"

                            text += '\n\n'

                        else:
                            text += f"*{n}* {nn}# {item['name']['en']}\n    *└* Price pay for 1х: {pr['price']}\n"
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

                msg_g = bot.send_message(message.chat.id, work_pr(page, pages), reply_markup=rmk, parse_mode='Markdown')

                def check_key(message, page, pages, ans):

                    if message.text in ['🛒 Рынок', '🛒 Market'] or message.text not in ans:

                        if bd_user['language_code'] == 'ru':
                            text = "🛒 | Возвращение в меню рынка!"
                        else:
                            text = "🛒 | Return to the market menu!"

                        bot.send_message(message.chat.id, text, reply_markup=Functions.markup(bot, 'market', user))
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

                    msg = bot.send_message(message.chat.id, work_pr(page, pages), reply_markup=rmk,
                                           parse_mode='Markdown')
                    bot.register_next_step_handler(msg, check_key, page, pages, ans)

                bot.register_next_step_handler(msg_g, check_key, page, pages, ans)

    @staticmethod
    def delete_product(bot, message, user, bd_user):

        if bd_user != None:

            market_ = management.find_one({"_id": 'products'})
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

                pages = list(Functions.chunks(products, 5))

                if bd_user['language_code'] == 'ru':
                    text = '🛒 | *Ваши продукты*\n\n'
                else:
                    text = '🛒 | *Your products*\n\n'

                rmk = types.ReplyKeyboardMarkup(resize_keyboard=True, row_width=3)

                lll = []
                for i in range(1, len(pages[page - 1]) + 1):
                    lll.append(str(i + 1 * page + (5 * (page - 1)) - 1 * page))

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

                    w_page = pages[page - 1]

                    nn = (page - 1) * 5
                    for pr in w_page:
                        item = items_f['items'][pr['item']['item_id']]
                        nn += 1

                        if int(w_page.index(pr)) == len(w_page) - 1:
                            n = '└'
                        elif int(w_page.index(pr)) == 0:
                            n = '┌'
                        else:
                            n = '├'

                        if bd_user['language_code'] == 'ru':
                            text += f"*{n}* {nn}# {item['name']['ru']}\n    *└* Цена за 1х: {pr['price']}\n"
                            text += f"       *└* Продано: {pr['col'][0]} / {pr['col'][1]}"

                            if 'abilities' in pr['item'].keys():
                                if 'uses' in pr['item']['abilities'].keys():
                                    text += f"\n           *└* Использований: {pr['item']['abilities']['uses']}"

                            text += '\n\n'

                        else:
                            text += f"*{n}* {nn}# {item['name']['en']}\n    *└* Price pay for 1х: {pr['price']}\n"
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

                msg_g = bot.send_message(message.chat.id, work_pr(page, pages), reply_markup=rmk, parse_mode='Markdown')

                def check_key(message, page, pages, ans):
                    number = None

                    if message.text in ['🛒 Рынок', '🛒 Market']:

                        if bd_user['language_code'] == 'ru':
                            text = "🛒 | Возвращение в меню рынка!"
                        else:
                            text = "🛒 | Return to the market menu!"

                        bot.send_message(message.chat.id, text, reply_markup=Functions.markup(bot, 'market', user))
                        return

                    if message.text not in ans:

                        try:
                            number = int(message.text)

                        except:

                            if bd_user['language_code'] == 'ru':
                                text = "🛒 | Возвращение в меню рынка!"
                            else:
                                text = "🛒 | Return to the market menu!"

                            bot.send_message(message.chat.id, text, reply_markup=Functions.markup(bot, 'market', user))
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

                        rmk = types.ReplyKeyboardMarkup(resize_keyboard=True, row_width=3)

                        lll = []
                        for i in range(1, len(pages[page - 1]) + 1):
                            lll.append(str(i + 1 * page + (5 * (page - 1)) - 1 * page))

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

                        msg = bot.send_message(message.chat.id, work_pr(page, pages), reply_markup=rmk,
                                               parse_mode='Markdown')
                        bot.register_next_step_handler(msg, check_key, page, pages, ans)

                    else:

                        nn_number = list(market_['products'][str(user.id)]['products'].keys())[number - 1]

                        if nn_number not in market_['products'][str(user.id)]['products'].keys():

                            if bd_user['language_code'] == 'ru':
                                text = "🛒 | Объект с данным номером не найден в ваших продуктах!"
                            else:
                                text = "🛒 | The object with this number is not found in your products!"

                            bot.send_message(message.chat.id, text, reply_markup=Functions.markup(bot, 'market', user))

                        else:
                            data_items = items_f['items']
                            prod = market_['products'][str(user.id)]['products'][nn_number]

                            if data_items[prod['item']['item_id']]['type'] == '+eat':

                                eat_c = Functions.items_counting(bd_user, '+eat')
                                if eat_c >= settings_f['max_eat_items']:

                                    if bd_user['language_code'] == 'ru':
                                        text = f'🌴 | Ваш инвентарь ломится от количества еды! В данный момент у вас {eat_c} предметов которые можно съесть!'
                                    else:
                                        text = f'🌴 | Your inventory is bursting with the amount of food! At the moment you have {eat_c} items that can be eaten!'

                                    bot.send_message(message.chat.id, text,
                                                     reply_markup=Functions.markup(bot, 'market', user))
                                    return

                            for i in range(prod['col'][1] - prod['col'][0]):
                                bd_user['inventory'].append(prod['item'])

                            del market_['products'][str(user.id)]['products'][nn_number]

                            management.update_one({"_id": 'products'}, {"$set": {'products': market_['products']}})
                            users.update_one({"userid": user.id}, {"$set": {'inventory': bd_user['inventory']}})

                            if bd_user['language_code'] == 'ru':
                                text = "🛒 | Продукт удалён!"
                            else:
                                text = "🛒 | The product has been removed!"

                            bot.send_message(message.chat.id, text, reply_markup=Functions.markup(bot, 'market', user))

                bot.register_next_step_handler(msg_g, check_key, page, pages, ans)

    @staticmethod
    def search_pr(bot, message, user, bd_user):

        if bd_user != None:

            market_ = management.find_one({"_id": 'products'})

            rmk = types.ReplyKeyboardMarkup(resize_keyboard=True, row_width=3)

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

                    bot.send_message(message.chat.id, text, reply_markup=Functions.markup(bot, 'market', user))
                    return

                else:

                    dct_items = {}
                    
                    for i in items_f['items']:
                        item = items_f['items'][i]

                        for inn in [item['name']['ru'], item['name']['en']]:
                            tok_s = fuzz.token_sort_ratio(message.text, inn)
                            ratio = fuzz.ratio(message.text, inn)
                            
                            if tok_s > 30 or ratio > 30:
                                sr_z = (tok_s + ratio) // 2
                                dct_items[sr_z] = i
                        
                            elif message.text == i:
                                dct_items[100] = i

                    if dct_items == {}:

                        if bd_user['language_code'] == 'ru':
                            text = "🛒 | Предмет с таким именем не найден в базе продаваемых предметов!\nВозвращение в меню рынка!"
                        else:
                            text = "🛒 | An item with that name was not found in the database of sold items!\nreturn to the market menu!"

                        bot.send_message(message.chat.id, text, reply_markup=Functions.markup(bot, 'market', user))
                        return
                    
                    else:
                        s_i = []
                        for _ in range(2):
                            if dct_items != {}:
                                s_i.append(dct_items[max(dct_items.keys())])
                                del dct_items[max(dct_items.keys())]

                    sear_items = []
                    for uid in market_['products']:
                        if uid != str(bd_user['userid']):
                            userser = market_['products'][uid]['products']
                            for ki in userser:
                                if userser[ki]['item']['item_id'] in s_i:
                                    sear_items.append({
                                        'user': uid, 'key': ki, 
                                        'col': userser[ki]['col'],
                                        'price': userser[ki]['price'], 
                                        'item': userser[ki]['item']
                                    })

                    if sear_items == []:
                        if bd_user['language_code'] == 'ru':
                            text = "🛒 | Предмет с таким именем не найден в базе продаваемых предметов!\nВозвращение в меню рынка!"
                        else:
                            text = "🛒 | An item with that name was not found in the database of sold items!\nreturn to the market menu!"

                        bot.send_message(message.chat.id, text, reply_markup=Functions.markup(bot, 'market', user))
                        return

                    random.shuffle(sear_items)
                    page = list(Functions.chunks(sear_items, 10))[0]

                    text = ''
                    a = 0

                    markup_inline = types.InlineKeyboardMarkup()
                    in_l = []

                    if bd_user['language_code'] == 'ru':
                        text += f"🔍 | По вашему запросу найдено {len(sear_items)} предметов(а) >\n\n"
                        for i in page:
                            a += 1
                            text += f"*{a}#* {items_f['items'][i['item']['item_id']]['name']['ru']}\n     *└* Цена за 1х: {i['price']}\n         *└* Количество: {i['col'][1] - i['col'][0]}"

                            if 'abilities' in i['item'].keys():
                                if 'uses' in i['item']['abilities'].keys():
                                    text += f"\n           *└* Использований: {i['item']['abilities']['uses']}"

                            text += '\n\n'
                            in_l.append(types.InlineKeyboardButton(text=str(a) + '#',
                                    callback_data=f"market_buy_{i['user']} {i['key']}"))
                    else:
                        text += f'🔍 | Your search found {len(sear_items)} item(s) >\n\n'
                        for i in page:
                            a += 1
                            text += f"*{a}#* {items_f['items'][i['item']['item_id']]['name']['en']}\n     *└* Price per 1x: {i['price']}\n         *└* Quantity: {i['col'][1] - i['col'][0]}"

                            if 'abilities' in i['item'].keys():
                                if 'uses' in i['item']['abilities'].keys():
                                    text += f"\n           *└* Uses: {i['item']['abilities']['uses']}"

                            text += '\n\n'
                            in_l.append(types.InlineKeyboardButton(text=str(a) + '#',
                                    callback_data=f"market_buy_{i['user']} {i['key']}"))

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

                    msg = bot.send_message(message.chat.id, text, parse_mode='Markdown', reply_markup=markup_inline)

                    if bd_user['language_code'] == 'ru':
                        text = "🛒 | Возвращение в меню рынка!"
                    else:
                        text = "🛒 | Return to the market menu!"

                    bot.send_message(message.chat.id, text, reply_markup=Functions.markup(bot, 'market', user))
                    return

            msg = bot.send_message(message.chat.id, text, reply_markup=rmk, parse_mode='Markdown')
            bot.register_next_step_handler(msg, name_reg)

    @staticmethod
    def random_search(bot, message, user, bd_user):

        if bd_user != None:

            market_ = management.find_one({"_id": 'products'})

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
                    text += f"*{a}#* {items_f['items'][i['item']['item_id']]['name']['ru']}\n     *└* Цена за 1х: {i['price']}\n         *└* Количество: {i['col'][1] - i['col'][0]}"

                    if 'abilities' in i['item'].keys():
                        if 'uses' in i['item']['abilities'].keys():
                            text += f"\n           *└* Использований: {i['item']['abilities']['uses']}"

                        if 'endurance' in i['item']['abilities'].keys():
                            text += f"\n           *└* Прочность: {i['item']['abilities']['endurance']}"

                    text += '\n\n'

                    in_l.append(types.InlineKeyboardButton(text=str(a) + '#',
                                    callback_data=f"market_buy_{i['user']} {i['key']}"))

            else:
                text += f'🔍 | Random items from the market >\n\n'
                for i in page:
                    a += 1
                    text += f"*{a}#* {items_f['items'][i['item']['item_id']]['name']['en']}\n     *└* Price per 1x: {i['price']}\n         *└* Quantity: {i['col'][1] - i['col'][0]}"

                    if 'abilities' in i['item'].keys():
                        if 'uses' in i['item']['abilities'].keys():
                            text += f"\n           *└* Uses: {i['item']['abilities']['uses']}"

                        if 'endurance' in i['item']['abilities'].keys():
                            text += f"\n           *└* Endurance: {i['item']['abilities']['endurance']}"

                    text += '\n\n'

                    in_l.append(types.InlineKeyboardButton(text=str(a) + '#',
                                callback_data=f"market_buy_{i['user']} {i['key']}"))

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

            msg = bot.send_message(message.chat.id, text, parse_mode='Markdown', reply_markup=markup_inline)

    @staticmethod
    def rarity_change(bot, message, user, bd_user):

        bd_user = Functions.dino_q(bd_user)

        def inf_message(dino_id):

            data_q_r = settings_f['change_rarity']

            r_text = {'com': ['Обычный', 'Common'],
                      'unc': ['Необычный', 'Unusual'],
                      'rar': ['Редкий', 'Rare'],
                      'myt': ['Мистический', 'Mystical'],
                      'leg': ['Легендарный', 'Legendary'],
                      'ran': ['Случайный', 'Random'],
                      }

            ql = list(data_q_r.keys())

            if bd_user['language_code'] == 'ru':
                text_m = f" *┌* ♻ Возможная смена редкости для {bd_user['dinos'][dino_id]['name']}\n\n"
                lcode = 'ru'
                text_p2 = '✨ | Выберите в какую редкость вы хотите преобразовать динозавра, нажмите на кнопку и произойдёт магия! Также вы можете заменить динозавра на другого случайного!'
            else:
                text_m = f" *┌* ♻ Possible change of rarity for {bd_user['dinos'][dino_id]['name']}\n\n"
                lcode = 'en'
                text_p2 = '✨ | Choose which rarity you want to transform the dinosaur into, click on the button and magic will happen! You can also replace the dinosaur with another random one!'

            markup_inline = types.InlineKeyboardMarkup()
            cmm = []

            nn = 0
            for i in ql:
                nn += 1

                if bd_user['language_code'] == 'ru':
                    dino_q = r_text[i][0]
                else:
                    dino_q = r_text[i][1]

                if i == 'ran':
                    spl = '└'
                else:
                    spl = '├'

                text_m += f" *{spl}* *{nn}*. {', '.join(Functions.sort_items_col(data_q_r[i]['materials'], lcode))} + {data_q_r[i]['money']}💰 > {dino_q}🦕"

                if bd_user['dinos'][dino_id]['quality'] == i:
                    text_m += ' (✅)'

                text_m += '\n\n'

                cmm.append(types.InlineKeyboardButton(text=f'♻ {nn}', callback_data=f"change_rarity {dino_id} {i}"))

            markup_inline.add(*cmm)

            bot.send_message(message.chat.id, text_m, reply_markup=markup_inline, parse_mode='Markdown')
            bot.send_message(message.chat.id, text_p2, reply_markup=Functions.markup(bot, Functions.last_markup(bd_user, alternative='dino-tavern'), bd_user), parse_mode='Markdown')

        n_dp, dp_a = Functions.dino_pre_answer(user, type='noall')
        if n_dp == 1:
            bot.send_message(message.chat.id, f'❌', reply_markup=Functions.markup(bot, Functions.last_markup(bd_user, alternative='dino-tavern'), bd_user))
            return

        if n_dp == 2:
            inf_message(list(bd_user['dinos'].keys())[0])

        if n_dp == 3:
            rmk = dp_a[0]
            text = dp_a[1]
            dino_dict = dp_a[2]

            def ret(message, dino_dict, user, bd_user):

                if message.text in dino_dict.keys():

                    inf_message(dino_dict[message.text][1])

                else:
                    bot.send_message(message.chat.id, '❌',
                                     reply_markup=Functions.markup(bot, Functions.last_markup(bd_user), bd_user))

            msg = bot.send_message(message.chat.id, text, reply_markup=rmk)
            bot.register_next_step_handler(msg, ret, dino_dict, user, bd_user)

    @staticmethod
    def dungeon_menu(bot, message, user, bd_user):

        if bd_user != None:

            for din in bd_user['dinos']:

                if 'dungeon' not in bd_user['dinos'][din].keys():
                    bd_user['dinos'][din]['dungeon'] = {"equipment": {'armor': None, 'weapon': None}}

                    users.update_one({"userid": bd_user['userid']}, {"$set": {f'dinos.{din}': bd_user['dinos'][din]}})

            if 'user_dungeon' not in bd_user.keys():
                bd_user['user_dungeon'] = {"equipment": {'backpack': None}, 'statistics': []}

                users.update_one({"userid": bd_user['userid']}, {"$set": {f'user_dungeon': bd_user['user_dungeon']}})

            if bd_user['language_code'] == 'ru':
                text = f"🗻 | Вы перешли в меню подготовки к подземелью!"

            else:
                text = f"🗻 | You have moved to the dungeon preparation menu!"

            bot.send_message(message.chat.id, text, reply_markup=Functions.markup(bot, "dungeon_menu", user))

    @staticmethod
    def dungeon_rules(bot, message, user, bd_user):

        if bd_user != None:

            if bd_user['language_code'] == 'ru':
                text = (f'*📕 | Правила подземелья*\n\n'
                        f'1. *Предметы:*\n Все вещи и монеты взятые в подземелье, могут быть потерены, в случае "небезопасного выхода".\n\n'
                        f'2. *Безопасный выход:*\n Безопасно выйти по окончанию каждого этажа. При этом сохраняются все вещи и монеты.\n\n'
                        f'3. *НЕбезопасный выход:*\n Динозавры автоматически покидают подземелье в случае, когда здоровье опустилось до 10-ти. При этом теряются все вещи и монеты. Динозавр остаётся жив.\n\n'
                        f'4. *Боссы:*\n Каждые 10 этажей, расположен босс, его требуется победить для перехода на следующий этаж.\n\n'
                        f'5. *Конец подземелья:*\n Как говорят ранкеры: "У подземелья нет конца", оно спускается на многие киллометры вниз, кто знает, что вас там ожидает.\n\n'
                        f'6. *Награда:*\n Чем ниже вы спускаетесь, тем ценнее награда, и ресурсы которые можно добыть.\n\n'
                        f'7. *Рейтинг:*\n Ваш результат будет записан в таблицу рейтинга. Рейтинг сбрасывается 1 раз в 2-а месяца. А победители, получают награду.')

            else:
                text = (f'*📕 | Dungeon Rules*\n\n'
                        f'1. *Items:*\n All items and coins taken in the dungeon can be lost in case of an "unsafe exit".\n\n'
                        f'2. *Safe exit:*\n It is safe to exit at the end of each floor. At the same time, all items and coins are saved.\n\n'
                        f'3. *Unsafe exit:*\n Dinosaurs automatically leave the dungeon when their health drops to 10. At the same time, all things and coins are lost. The dinosaur remains alive.\n\n'
                        f'4. *Bosses:*\n Every 10 floors, there is a boss, it needs to be defeated to move to the next floor.\n\n'
                        f'5. * The end of the dungeon:*\n As the rankers say: "The dungeon has no end," it descends many kilometers down, who knows what awaits you there.\n\n'
                        f'6. *Reward:*\n The lower you go, the more valuable the reward and the resources that can be obtained.\n\n'
                        f'7. *Rating:*\n Your result will be recorded in the rating table. The rating is reset 1 time in 2 months. And the winners get a reward.')

            bot.send_message(message.chat.id, text, parse_mode='Markdown')

    @staticmethod
    def dungeon_create(bot, message, user, bd_user):

        if bd_user != None:

            dung = dungeons.find_one({"dungeonid": user.id})

            if dung == None:

                dungs = dungeons.find({})

                for dng in dungs:
                    if str(user.id) in dng['users'].keys():

                        if bd_user['language_code'] == 'ru':
                            text = f'❗ | Вы уже участвуете в подземелье!'

                        else:
                            text = f'❗ | You are already participating in the dungeon!'

                        bot.send_message(message.chat.id, text)
                        return

                if bd_user['language_code'] == 'ru':
                    text = f'⚙ | Генерация...'

                else:
                    text = f'⚙ | Generation...'

                mg = bot.send_message(message.chat.id, text, reply_markup=Functions.markup(bot, "dungeon", user))

                dng, inf = Dungeon.base_upd(userid=user.id)
                inf = Dungeon.message_upd(bot, userid=user.id, dungeonid=user.id)

                bot.delete_message(user.id, mg.message_id)

            else:
                if bd_user['language_code'] == 'ru':
                    text = f'❗ | У вас уже создано подземелье!'

                else:
                    text = f'❗ | You have already created a dungeon!'

                bot.send_message(message.chat.id, text)

    @staticmethod
    def dungeon_join(bot, message, user, bd_user):

        if bd_user != None:

            dung = dungeons.find_one({"dungeonid": user.id})

            if dung == None:

                dungs = dungeons.find({})

                for dng in dungs:
                    if str(user.id) in dng['users'].keys():

                        if bd_user['language_code'] == 'ru':
                            text = f'❗ | Вы уже участвуете в подземелье!'

                        else:
                            text = f'❗ | You are already participating in the dungeon!'

                        bot.send_message(message.chat.id, text)
                        return

                def join_dungeon(message, old_m):

                    try:
                        code = int(message.text)
                    except:
                        if bd_user['language_code'] == 'ru':
                            text = f'❗  | Введите корректный код!'

                        else:
                            text = f'❗  | Enter the correct code!'

                        bot.send_message(message.chat.id, text)

                    else:
                        dung = dungeons.find_one({"dungeonid": code})

                        if dung == None:

                            if bd_user['language_code'] == 'ru':
                                text = f'❗ | Введите корректный код!'

                            else:
                                text = f'❗ | Enter the correct code!'

                            bot.send_message(message.chat.id, text)

                        else:

                            if dung['dungeon_stage'] == 'preparation':

                                if bd_user['language_code'] == 'ru':
                                    text = f'⚙ | Генерация...'

                                else:
                                    text = f'⚙ | Generation...'

                                mg = bot.send_message(message.chat.id, text,
                                                      reply_markup=Functions.markup(bot, "dungeon", user))

                                dng, inf = Dungeon.base_upd(userid=user.id, dungeonid=code, type='add_user')

                                inf = Dungeon.message_upd(bot, userid=user.id, dungeonid=dng['dungeonid'],
                                                          upd_type='all')

                                bot.delete_message(user.id, mg.message_id)

                            else:

                                if bd_user['language_code'] == 'ru':
                                    text = f'❗ | На этой стадии нельзя присоединится к подземелью!'

                                else:
                                    text = f"❗ | You can't join the dungeon at this stage!"

                                bot.send_message(message.chat.id, text)

                if bd_user['language_code'] == 'ru':
                    text = f'🎟 | Введите код подключения > '

                else:
                    text = f'🎟 | Enter the connection code >'

                msg = bot.send_message(message.chat.id, text)
                bot.register_next_step_handler(msg, join_dungeon, msg)


            else:
                if bd_user['language_code'] == 'ru':
                    text = f'❗ | У вас уже создано подземелье!'

                else:
                    text = f'❗ | You have already created a dungeon!'

                bot.send_message(message.chat.id, text)

    @staticmethod
    def dungeon_equipment(bot, message, user, bd_user):

        def work_pr_zero(message, dino_id):
            data_items = items_f['items']

            type_eq = None

            if message.text in ['🗡 Оружие', '🛡 Броня', '🎒 Рюкзак', '🗡 Weapon', '🛡 Armor', '🎒 Backpack']:

                if message.text in ['🗡 Оружие', '🗡 Weapon']:
                    type_eq = 'weapon'

                elif message.text in ['🛡 Броня', '🛡 Armor']:
                    type_eq = 'armor'

                else:
                    type_eq = 'backpack'

            else:

                bot.send_message(message.chat.id, '❌',
                                 reply_markup=Functions.markup(bot, Functions.last_markup(bd_user), bd_user))
                return

            items = []

            for i in bd_user['inventory']:
                itm = data_items[i['item_id']]

                if itm['type'] == type_eq:
                    items.append(i)

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

                bot.send_message(message.chat.id, text, reply_markup=Functions.markup(bot, 'dungeon_menu', user))
                return

            data_items = items_f['items']
            items_id = {}
            page = 1
            items_names = []

            for i in items:
                iname = Functions.item_name(str(i['item_id']), bd_user['language_code'])

                items_id[iname] = i
                items_names.append(iname)

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
                items_sort.append(f'{n} x{col}')
                ind_sort_it[f'{n} x{col}'] = n

            pages = list(Functions.chunks(list(Functions.chunks(items_sort, 2)), 2))

            if len(pages) == 0:
                pages = [[]]

            for i in pages:
                for ii in i:
                    if len(ii) == 1:
                        ii.append(' ')

                if len(i) != 2:
                    for _ in range(2 - len(i)):
                        i.append([' ', ' '])

            def work_pr(message, pages, page, items_id, ind_sort_it, type_eq, dino_id):

                l_pages = pages
                l_page = page
                l_ind_sort_it = ind_sort_it

                rmk = types.ReplyKeyboardMarkup(resize_keyboard=True, row_width=3)
                for i in pages[page - 1]:
                    rmk.add(i[0], i[1])

                if len(pages) > 1:
                    if bd_user['language_code'] == 'ru':
                        com_buttons = ['◀', '↪ Назад', '▶', '🔻 Снять']
                        textt = f'🎴 | Выберите предмет >'
                    else:
                        com_buttons = ['◀', '↪ Back', '▶', '🔻 Remove']
                        textt = f'🎴 | Choose a subject >'

                    rmk.add(com_buttons[3])
                    rmk.add(com_buttons[0], com_buttons[1], com_buttons[2])

                else:

                    if bd_user['language_code'] == 'ru':
                        com_buttons = ['↪ Назад', '🔻 Снять']
                        textt = f'🎴 | Выберите предмет >'
                    else:
                        textt = f'🎴 | Choose a subject >'
                        com_buttons = ['↪ Back', '🔻 Remove']

                    rmk.add(com_buttons[1])
                    rmk.add(com_buttons[0])

                def ret(message, l_pages, l_page, l_ind_sort_it, bd_user, user, pages, page, items_id, ind_sort_it,
                        type_eq, dino_id):
                    if message.text in ['↩ Назад', '↩ Back']:
                        res = None

                    else:
                        if message.text in list(l_ind_sort_it.keys()) or message.text in ['◀', '▶', '🔻 Снять',
                                                                                          '🔻 Remove']:
                            res = message.text
                        else:
                            res = None

                    if res == None:
                        if bd_user['language_code'] == 'ru':
                            text = "⚙ | Возвращение"
                        else:
                            text = "⚙ | Return"

                        bot.send_message(message.chat.id, text,
                                         reply_markup=Functions.markup(bot, 'dungeon_menu', user))
                        return '12'

                    else:
                        if res == '◀':
                            if page - 1 == 0:
                                page = 1
                            else:
                                page -= 1

                            work_pr(message, pages, page, items_id, ind_sort_it, type_eq, dino_id)

                        elif res == '▶':
                            if page + 1 > len(l_pages):
                                page = len(l_pages)
                            else:
                                page += 1

                            work_pr(message, pages, page, items_id, ind_sort_it, type_eq, dino_id)

                        else:

                            if res in ['🔻 Снять', '🔻 Remove']:

                                if type_eq in ['weapon', 'armor']:
                                    item = bd_user['dinos'][dino_id]['dungeon']['equipment'][type_eq]

                                    if item != None:

                                        users.update_one({"userid": bd_user['userid']}, {"$push": {'inventory': item}})

                                        bd_user['dinos'][dino_id]['dungeon']['equipment'][type_eq] = None

                                        users.update_one({"userid": bd_user['userid']},
                                                         {"$set": {'dinos': bd_user['dinos']}})

                                        if bd_user['language_code'] == 'ru':
                                            text = "🎴 | Активный предмет снят"
                                        else:
                                            text = "🎴 | Active item removed"

                                    else:

                                        if bd_user['language_code'] == 'ru':
                                            text = "🎴 | В данный момент нет активного предмета!"
                                        else:
                                            text = "🎴 | There is no active item at the moment!"

                                if type_eq in ['backpack']:
                                    item = bd_user['user_dungeon']['equipment'][type_eq]

                                    if item != None:
                                        users.update_one({"userid": bd_user['userid']}, {"$push": {'inventory': item}})

                                        bd_user['user_dungeon']['equipment'][type_eq] = None

                                        users.update_one({"userid": bd_user['userid']},
                                                         {"$set": {'user_dungeon': bd_user['user_dungeon']}})

                                        if bd_user['language_code'] == 'ru':
                                            text = "🎴 | Активный предмет снят"
                                        else:
                                            text = "🎴 | Active item removed"

                                    else:

                                        if bd_user['language_code'] == 'ru':
                                            text = "🎴 | В данный момент нет активного предмета!"
                                        else:
                                            text = "🎴 | There is no active item at the moment!"

                                bot.send_message(message.chat.id, text,
                                                 reply_markup=Functions.markup(bot, 'dungeon_menu', user))

                            else:
                                if type_eq in ['weapon', 'armor']:
                                    item = bd_user['dinos'][dino_id]['dungeon']['equipment'][type_eq]

                                    if item != None:
                                        bd_user['inventory'].append(item)
                                        bd_user['dinos'][dino_id]['dungeon']['equipment'][type_eq] = None

                                    itemm = items_id[l_ind_sort_it[res]]
                                    bd_user['dinos'][dino_id]['dungeon']['equipment'][type_eq] = itemm

                                    users.update_one({"userid": bd_user['userid']},
                                                     {"$set": {'dinos': bd_user['dinos']}})

                                if type_eq in ['backpack']:
                                    item = bd_user['user_dungeon']['equipment'][type_eq]

                                    if item != None:
                                        bd_user['inventory'].append(item)
                                        bd_user['user_dungeon']['equipment'][type_eq] = None

                                    itemm = items_id[l_ind_sort_it[res]]
                                    bd_user['user_dungeon']['equipment'][type_eq] = itemm

                                    users.update_one({"userid": bd_user['userid']},
                                                     {"$set": {'user_dungeon': bd_user['user_dungeon']}})

                                if bd_user['language_code'] == 'ru':
                                    text = "🎴 | Активный предмет установлен!"
                                else:
                                    text = "🎴 | The active item is installed!"

                                bd_user['inventory'].remove(itemm)
                                users.update_one({"userid": bd_user['userid']},
                                                 {"$set": {'inventory': bd_user['inventory']}})

                                bot.send_message(message.chat.id, text,
                                                 reply_markup=Functions.markup(bot, 'dungeon_menu', user))

                msg = bot.send_message(message.chat.id, textt, reply_markup=rmk)
                bot.register_next_step_handler(msg, ret, l_pages, l_page, l_ind_sort_it, bd_user, user, pages, page,
                                               items_id, ind_sort_it, type_eq, dino_id)

            work_pr(message, pages, page, items_id, ind_sort_it, type_eq, dino_id)

        data_items = items_f['items']

        def type_answer(message, dino_id):
            dino = bd_user['dinos'][dino_id]

            if bd_user['language_code'] == 'ru':
                ans = ['🗡 Оружие', '🛡 Броня', '🎒 Рюкзак', '↪ Назад']
            else:
                ans = ['🗡 Weapon', '🛡 Armor', '🎒 Backpack', '↪ Back']

            rmk = types.ReplyKeyboardMarkup(resize_keyboard=True, row_width=2)
            rmk.add(ans[0], ans[1], ans[2])
            rmk.add(ans[3])

            if dino['dungeon']['equipment']['weapon'] != None:
                w_n = data_items[dino['dungeon']['equipment']['weapon']['item_id']]['name'][bd_user["language_code"]]
            else:
                w_n = '-'

            if dino['dungeon']['equipment']['armor'] != None:
                a_n = data_items[dino['dungeon']['equipment']['armor']['item_id']]['name'][bd_user["language_code"]]
            else:
                a_n = '-'

            if bd_user['user_dungeon']['equipment']['backpack'] != None:
                b_n = data_items[bd_user['user_dungeon']['equipment']['backpack']['item_id']]['name'][
                    bd_user["language_code"]]
            else:
                b_n = '-'

            if bd_user['language_code'] == 'ru':
                text = f'Экипированно:\n🗡: {w_n}\n🛡: {a_n}\n🎒: {b_n}\n\n⚙ | Выберите что вы хотите экипировать >'

            else:
                text = f'Equipped:\n🗡: {w_n}\n🛡: {a_n}\n🎒: {b_n}\n\n⚙ | Choose what you want to equip >'

            msg = bot.send_message(message.chat.id, text, reply_markup=rmk)
            bot.register_next_step_handler(msg, work_pr_zero, dino_id)

        n_dp, dp_a = Functions.dino_pre_answer(user, type='noall')
        if n_dp == 1:
            bot.send_message(message.chat.id, f'❌', reply_markup=Functions.markup(bot, Functions.last_markup(bd_user, alternative='dungeon_menu'), bd_user))
            return

        if n_dp == 2:
            bd_dino = dp_a

            type_answer(message, list(bd_user['dinos'].keys())[0])

        if n_dp == 3:
            rmk = dp_a[0]
            text = dp_a[1]
            dino_dict = dp_a[2]

            def ret(message, dino_dict, user, bd_user):

                if message.text in dino_dict.keys():

                    type_answer(message, dino_dict[message.text][1])

                else:
                    bot.send_message(message.chat.id, '❌',
                                     reply_markup=Functions.markup(bot, Functions.last_markup(bd_user), bd_user))

            msg = bot.send_message(message.chat.id, text, reply_markup=rmk)
            bot.register_next_step_handler(msg, ret, dino_dict, user, bd_user)

    @staticmethod
    def dungeon_statist(bot, message, user, bd_user):

        if 'user_dungeon' in bd_user.keys():
            ns_res =Dungeon.get_statics(bd_user, "max")
            st = bd_user['user_dungeon']['statistics']

            if ns_res != None:

                if bd_user['language_code'] == 'ru':
                    text = (f'*🗻 | Статистика в подземелье*\n'
                            f'🔥 Всего игр: {len(st)}\n\n'
                            f'*👑 | Лучшая игра*\n'
                            f'🧩 Начальный этаж: {ns_res["start_floor"]}\n'
                            f'🗝 Последний этаж: {ns_res["end_floor"]}\n'
                            f'🕰 Время: {Functions.time_end(ns_res["time"])}\n')

                else:
                    text = (f'*🗻 | Statistics in the dungeon*\n'
                            f'🔥 Total games: {len(st)}\n\n'
                            f'*👑 | Best game*\n'
                            f'🧩 Initial floor: {ns_res["start_floor"]}\n'
                            f'🗝 Last floor: {ns_res["end_floor"]}\n'
                            f'🕰 Time: {Functions.time_end(ns_res["time"], True)}\n')

            else:

                if bd_user['language_code'] == 'ru':
                    text = 'Статистика не собрана.'
                else:
                    text = 'Statistics are not collected.'

            bot.send_message(message.chat.id, text, parse_mode='Markdown')

    @staticmethod
    def quests(bot, message, user, bd_user):

        if 'user_dungeon' not in bd_user.keys():

            if bd_user['language_code'] == 'ru':
                text = 'Вы не авторизованы в системе подземелий!'
            else:
                text = 'You are not logged into the dungeon system!'

            bot.send_message(message.chat.id, text)

        else:

            if 'quests' not in bd_user['user_dungeon'].keys():
                bd_user['user_dungeon']['quests'] = {
                    'activ_quests': [],
                    'max_quests': 5,
                    'ended': 0,
                }

                users.update_one({"userid": bd_user['userid']},
                                 {"$set": {'user_dungeon.quests': bd_user['user_dungeon']['quests']}})

            if bd_user['language_code'] == 'ru':
                text = f"🎪 | Меню квестов\nЗавершено: {bd_user['user_dungeon']['quests']['ended']}\nКоличество активных квестов: {len(bd_user['user_dungeon']['quests']['activ_quests'])}"
            else:
                text = f"🎪 | Quest menu\nCompleted: {bd_user['user_dungeon']['quests']['ended']}\nNumber of active quests: {len(bd_user['user_dungeon']['quests']['activ_quests'])}"

            bot.send_message(message.chat.id, text)

            if bd_user['user_dungeon']['quests']['activ_quests'] != []:

                for quest in bd_user['user_dungeon']['quests']['activ_quests']:
                    text = f"🎪 | {quest['name']}\n"
                    markup_inline = types.InlineKeyboardMarkup()

                    if bd_user['language_code'] == 'ru':
                        text += f"Тип: "

                        if quest['type'] == 'get':
                            text += '🔎 Поиск\n'

                        if quest['type'] == 'kill':
                            text += '☠ Убийство\n'

                        if quest['type'] == 'come':
                            text += '🗻 Покорение\n'

                        if quest['type'] == 'do':
                            text += '🕰 Задание\n'

                    else:
                        text += f"Type: "

                        if quest['type'] == 'get':
                            text += '🔎 Search\n'

                        if quest['type'] == 'kill':
                            text += '☠ Murder\n'

                        if quest['type'] == 'come':
                            text += '🗻 Conquest\n'

                        if quest['type'] == 'do':
                            text += '🕰 Task\n'

                    if quest['type'] == 'get':

                        if bd_user['language_code'] == 'ru':
                            text += f'Достаньте: {", ".join(Functions.sort_items_col(quest["get_items"], "ru"))}'

                            inl_l = {
                                '📌 | Завершить': f"complete_quest {quest['id']}",
                                '🔗 | Удалить': f"delete_quest {quest['id']}"
                            }


                        else:
                            text += f'Достаньте: {", ".join(Functions.sort_items_col(quest["get_items"], "en"))}'

                            inl_l = {
                                '📌 | Finish': f"complete_quest {quest['id']}",
                                '🔗 | Delete': f"delete_quest {quest['id']}"
                            }

                    if quest['type'] == 'kill':

                        if bd_user['language_code'] == 'ru':
                            text += f"Убейте: {mobs_f['mobs'][quest['mob']]['name'][bd_user['language_code']]} {quest['col'][1]} / {quest['col'][0]}"

                            inl_l = {
                                '📌 | Завершить': f"complete_quest {quest['id']}",
                                '🔗 | Удалить': f"delete_quest {quest['id']}"
                            }
                        else:
                            text += f"Kill: {mobs_f['mobs'][quest['mob']]['name'][bd_user['language_code']]} {quest['col'][1]} / {quest['col'][0]}"

                            inl_l = {
                                '📌 | Finish': f"complete_quest {quest['id']}",
                                '🔗 | Delete': f"delete_quest {quest['id']}"
                            }

                    if quest['type'] == 'come':
                        markup_inline = types.InlineKeyboardMarkup(row_width=1)

                        if bd_user['language_code'] == 'ru':
                            text += f'Дойдите до этажа #{quest["lvl"]}'

                            inl_l = {
                                'Завершается автоматически': '-',
                                '🔗 | Удалить': f"delete_quest {quest['id']}"
                            }
                        else:
                            text += f'Get to the floor #{quest["lvl"]}'

                            inl_l = {
                                'Completed automatically': '-',
                                '🔗 | Delete': f"delete_quest {quest['id']}"
                            }

                    if quest['type'] == 'do':
                        target = quest['target']
                        dp_type = quest['dp_type']

                        if dp_type == 'game':

                            if bd_user['language_code'] == 'ru':
                                text += f'Поиграйте с динозавром: {target[1]} / {target[0]} мин.'
                            else:
                                text += f'Play with a dinosaur: {target[1]} / {target[0]} min.'

                        if dp_type == 'journey':

                            if bd_user['language_code'] == 'ru':
                                text += f'Отправьте динозавра в путешествие: {target[1]} / {target[0]} раз.'
                            else:
                                text += f'Send the dinosaur on a journey: {target[1]} / {target[0]} times.'

                        if dp_type == 'hunting':

                            if bd_user['language_code'] == 'ru':
                                text += f'Найдите предметов на охоте: {target[1]} / {target[0]}'
                            else:
                                text += f'Find items on the hunt: {target[1]} / {target[0]}'

                        if dp_type == 'fishing':

                            if bd_user['language_code'] == 'ru':
                                text += f'Выловите предметов: {target[1]} / {target[0]}'
                            else:
                                text += f'Catch items: {target[1]} / {target[0]}'

                        if dp_type == 'collecting':

                            if bd_user['language_code'] == 'ru':
                                text += f'Соберите предметов: {target[1]} / {target[0]}'
                            else:
                                text += f'Collect items: {target[1]} / {target[0]}'

                        if dp_type == 'feed':

                            lang = bd_user['language_code']

                            if bd_user['language_code'] == 'ru':
                                text += f'Накормите динозавра: \n\n'
                            else:
                                text += f'Feed the dinosaur: \n\n'

                            for i in target.keys():
                                item = items_f['items'][i]
                                target_item = target[i]

                                text += f'{item[f"name"][lang]}: {target_item[1]} / {target_item[0]}\n'

                        if bd_user['language_code'] == 'ru':
                            inl_l = {
                                '📌 | Завершить': f"complete_quest {quest['id']}",
                                '🔗 | Удалить': f"delete_quest {quest['id']}"
                            }

                        else:
                            inl_l = {
                                '📌 | Finish': f"complete_quest {quest['id']}",
                                '🔗 | Delete': f"delete_quest {quest['id']}"
                            }

                    markup_inline.add(
                        *[types.InlineKeyboardButton(text=inl, callback_data=f"{inl_l[inl]}") for inl in inl_l.keys()])

                    if bd_user['language_code'] == 'ru':
                        text += f'\n\n👑 | Награда\nМонеты: '
                    else:
                        text += f'\n\n👑 | Reward\Сoins: '

                    text += f"{quest['reward']['money']}💰"

                    if quest['reward']['items'] != []:

                        if bd_user['language_code'] == 'ru':
                            text += f"\nПредметы: {', '.join(Functions.sort_items_col(quest['reward']['items'], 'ru'))}"
                        else:
                            text += f"\nItems: {', '.join(Functions.sort_items_col(quest['reward']['items'], 'en'))}"

                    if bd_user['language_code'] == 'ru':
                        text += f"\n\n⏳ Осталось: {Functions.time_end(quest['time'] - int(time.time()), mini=False)}"

                    else:
                        text += f"\n\n⏳ Time left: {Functions.time_end(quest['time'] - int(time.time()), mini=True)}"

                    bot.send_message(message.chat.id, text, reply_markup=markup_inline)
                    time.sleep(0.5)
    
    def opne_inventory(bot, message, user, bd_user):

        rmk = types.ReplyKeyboardMarkup(resize_keyboard=True, row_width=3)
        data_items = items_f['items']
        text_dict = Functions.get_text(l_key=bd_user['language_code'], text_key="opne_inventory")
        buttons = Functions.get_text(l_key=bd_user['language_code'], text_key="buttons_name")

        text = text_dict['info']
        dct_filters = text_dict['dct_filters']
        bt_0, bt_last = text_dict['s_bt'], buttons['back']
        ans = []

        n_dct = {}
        for i in dct_filters.keys():
            dct = dct_filters[i]

            for kl in dct:
                n_dct[kl] = i
        
        for i in bd_user['inventory']:
            if len(ans) == len(dct_filters.keys()):
                break
            
            else:
                i_tp = data_items[i['item_id']]['type']
                type_word = n_dct[i_tp]

                if type_word not in ans:
                    ans.append(type_word)
        
        ans.sort()
        ans.insert(len(ans), bt_last)
        ans.insert(-1, bt_0)
        rmk.add(*[bt for bt in ans])

        def ret(message):
            if message.text in dct_filters.keys():
                
                inv_type = dct_filters[message.text]
                if inv_type == []:
                    Functions.user_inventory(bot, user, message, filter_type='all')
                else:
                    Functions.user_inventory(bot, user, message, filter_type='itemtype', i_filter=inv_type)

            else:
                bot.send_message(message.chat.id, '❌', reply_markup=Functions.markup(bot, 'profile', user))

        msg = bot.send_message(user.id, text, reply_markup=rmk)
        bot.register_next_step_handler(msg, ret)

