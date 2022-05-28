import telebot
from telebot import types
import random
import json
import pymongo
from PIL import Image, ImageFont, ImageDraw, ImageOps, ImageSequence, ImageFilter
import io
from io import BytesIO
import time
import os
import threading
import sys
from memory_profiler import memory_usage
import pprint
from fuzzywuzzy import fuzz

from functions import functions

sys.path.append("..")
import config


client = pymongo.MongoClient(config.CLUSTER_TOKEN)
users = client.bot.users
referal_system = client.bot.referal_system
market = client.bot.market

with open('data/items.json', encoding='utf-8') as f:
    items_f = json.load(f)

with open('data/dino_data.json', encoding='utf-8') as f:
    json_f = json.load(f)

class commands:
    users = users
    referal_system = referal_system
    market = market
    items_f = items_f
    json_f = json_f

    @staticmethod
    def start_game(bot, message, user):

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

    @staticmethod
    def project_reb(bot, message, user):

        bd_user = users.find_one({"userid": user.id})
        if bd_user != None:
            if bd_user != None and len(bd_user['dinos']) == 0 and functions.inv_egg(bd_user) == False and bd_user['lvl'][0] < 5:

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

    @staticmethod
    def faq(bot, message, user):
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

    @staticmethod
    def not_set(bot, message, user):

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
                    bot.send_message(message.chat.id, f'❌', reply_markup = functions.markup(bot, 'settings', user))
                    return

                if res in ['✅ Enable', '✅ Включить']:

                    bd_user['settings']['notifications'] = True
                    users.update_one( {"userid": bd_user['userid']}, {"$set": {'settings': bd_user['settings'] }} )

                    if bd_user['language_code'] == 'ru':
                        text = '🔧 Уведомления были активированы!'
                    else:
                        text = '🔧 Notifications have been activated!'

                    bot.send_message(message.chat.id, text, reply_markup = functions.markup(bot, "settings", user))

                if res in ['❌ Disable', '❌ Выключить']:

                    bd_user['settings']['notifications'] = False
                    users.update_one( {"userid": bd_user['userid']}, {"$set": {'settings': bd_user['settings'] }} )

                    if bd_user['language_code'] == 'ru':
                        text = '🔧 Уведомления были отключены!'
                    else:
                        text = '🔧 Notifications have been disabled!'

                    bot.send_message(message.chat.id, text, reply_markup = functions.markup(bot, "settings", user))

                else:
                    return

            msg = bot.send_message(message.chat.id, text, reply_markup = rmk)
            bot.register_next_step_handler(msg, ret, ans, bd_user)

    @staticmethod
    def lang_set(bot, message, user):

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
                    bot.send_message(message.chat.id, f'❌', reply_markup = functions.markup(bot, 'settings', user))
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

                bot.send_message(message.chat.id, text, reply_markup = functions.markup(bot, "settings", user))

            msg = bot.send_message(message.chat.id, text, reply_markup = rmk)
            bot.register_next_step_handler(msg, ret, ans, bd_user)

    @staticmethod
    def dino_prof(bot, message, user):

        bd_user = users.find_one({"userid": user.id})
        if bd_user != None:

            if len(bd_user['dinos'].keys()) == 0:

                if bd_user['language_code'] == 'ru':
                    text = f'🥚 | В данный момент у вас нету динозавров, пожалуйста проверьте свой инвентарь. В инвентаре у вас должно быть яйцо, которое вы можете инкубировать!'
                else:
                    text = f"🥚 | You don't have any dinosaurs at the moment, please check your inventory. You must have an egg in your inventory that you can incubate!"

                bot.send_message(message.chat.id, text)

            elif len(bd_user['dinos'].keys()) > 0:

                n_dp, dp_a = functions.dino_pre_answer(bot, message)
                if n_dp == 1:

                    bot.send_message(message.chat.id, f'❌', reply_markup = functions.markup(bot, 1, user))
                    return

                if n_dp == 2:
                    bd_dino = dp_a
                    try:
                        functions.p_profile(bot, message, bd_dino, user, bd_user, list(bd_user['dinos'].keys())[0])
                    except Exception as error:
                        print('Ошибка в профиле2\n', error)

                if n_dp == 3:
                    rmk = dp_a[0]
                    text = dp_a[1]
                    dino_dict = dp_a[2]

                    def ret(message, dino_dict, user, bd_user):
                        if message.text in dino_dict.keys():
                            try:
                                functions.p_profile(bot, message, dino_dict[message.text][0], user, bd_user, dino_dict[message.text][1])
                            except Exception as error:
                                print('Ошибка в профиле1\n', error)

                        else:
                            bot.send_message(message.chat.id, '❌', reply_markup = functions.markup(bot, functions.last_markup(bd_user), bd_user ))

                    msg = bot.send_message(message.chat.id, text, reply_markup = rmk)
                    bot.register_next_step_handler(msg, ret, dino_dict, user, bd_user)
