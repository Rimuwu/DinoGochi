import telebot
from telebot import types
import random
import json
import pymongo
from PIL import Image, ImageFont, ImageDraw, ImageOps, ImageSequence, ImageFilter
import time
import sys
from pprint import pprint
from fuzzywuzzy import fuzz

from classes import Functions, Dungeon

sys.path.append("..")
import config

client = pymongo.MongoClient(config.CLUSTER_TOKEN)
users = client.bot.users
referal_system = client.bot.referal_system
market = client.bot.market
dungeons = client.bot.dungeons

with open('data/items.json', encoding='utf-8') as f: items_f = json.load(f)

with open('data/dino_data.json', encoding='utf-8') as f: json_f = json.load(f)

with open('data/mobs.json', encoding='utf-8') as f: mobs_f = json.load(f)

class commands:

    @staticmethod
    def start_game(bot, message, user, bd_user):

        if bd_user == None:

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
    def project_reb(bot, message, user, bd_user):

        if bd_user != None:
            if bd_user != None and len(bd_user['dinos']) == 0 and Functions.inv_egg(bd_user) == False and bd_user['lvl'][0] <= 5:

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
    def faq(bot, message, user, bd_user):

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
                text2 += "*├*  3. Для повышения настроения динозавра требуется времени от времени развлекать динозавра. Перейдите `🕹 Действия` > `🎮 Развлечения` и следуйте указаниям.\n\n"
                text2 += "*├*  4. Чтобы возобновить силы динозавра, отправляйте его спать, `🕹 Действия` > `🌙 Уложить спать`\n\n"
                text2 += "*└*  5. Для повышения настроения, требуется держать потребность в еде, игры, сна в норме.\n\n"
                text2 += "*┌* *Профиль 🎮*\n\n"
                text2 += "*└*  Чтобы посмотреть инвентарь или узнать свою статистику, перейдите в `👁‍🗨 Профиль`\n\n"
                text2 += "*┌* *Настройки 🔧*\n\n"
                text2 += "*└*  В настройках вы можете переименовать динозавра, отключить уведомления или переключить язык.\n\n"
                text2 += "*┌* *Еда 🍕*\n\n"
                text2 += "*└*  Какой вид пищи подойдёт вашему динозавру, можно узнать по заднему фону профиля.\n\n"
                text2 += "*┌* *Рынок 🛒*\n\n"
                text2 += "*└*  На рынке можно продать или приобрести нужные вам вещи.\n\n"
                text2 += "*┌* *Аксессуары 🏓*\n\n"
                text2 += "*└*  Аксессуары открывают дополнительные возможности или ускоряют вид деятельности. Аксессуары можно установить пока динозавр ничего не делает в меню `👁‍🗨 Профиль`\n\n"
                text2 += "*┌* *Друзья 👥*\n\n"
                text2 += "*└*  В меню друзей вы можете управлять своими друзьями и реферальной системой. Чем больше друзей, тем болше возможностей получить какие то бонусы. Так же пригласив друга через реферальную систему, вы и ваш друг получат приятные бонусы.\n\n"
                text2 += "*┌* *Количество динозавров 🦕*\n\n"
                text2 += "*├*  Каждый 20-ый уровень количество динозавров увеличивается на 1.\n*├*  20ый уровень - 2 динозавра.\n*└*  40ой уровень - 3 динозавра...\n\n"
                text2 += "*┌* *Дино-таверна ‍🍺*\n\n"
                text2 += "*└* Загляните в `‍🍺 Дино-таверна`, там вы сможете узнать информацию от посетителей, найти других игроков. А также получить квесты!\n\n"
                text2 += "*┌* *Квесты 📜*\n\n"
                text2 += "*└* В таверне вы можете получить квест (просто ожидайте в ней), квесты дают интересные бонусы за самые обычные действия!\n\n"
                text2 += "*┌* *Подземелья 🗻*\n\n"
                text2 += "*└* Отправляйтесь в захватывающее приключение вместе со своими друзьями! Приключения, боссы, уникальные предметы!\n\n"
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
                text2 += "*┌* *Profile 🎮*\n\n"
                text2+= "*└* To view inventory or find out your stats, go to `👁🗨 Profile`\n\n"
                text2 += "*┌**Settings 🔧*\n\n"
                text2 += "*└*  In the settings, you can rename the dinosaur, disable notifications, or switch the language.\n\n"
                text2 += "*┌* *Food 🍕*\n\n"
                text2 += "*└* What kind of food will suit your dinosaur, you can find out by the background of the profile.\n\n"
                text2 += "*┌* *Market 🛒*\n\n"
                text2 += "*└* You can sell or buy the things you need on the market.\n\n"
                text2 += "*┌* *Accessories 🏓*\n\n"
                text2 += "*└* Accessories open up additional opportunities or accelerate the type of activity. Accessories can be installed while the dinosaur does nothing in the menu `👁‍ Profile'`\n\n"
                text2 += "*┌**Friends 👥*\n\n"
                text2+= "*└* In the friends menu, you can manage your friends and referral system. The more friends there are, the more opportunities there are to get some bonuses. Also, by inviting a friend through the referral system, you and your friend will receive pleasant bonuses.\n\n"
                text2 += "*┌* *Number of dinosaurs 🦕*\n\n"
                text2 += "*├* Every 20th level the number of dinosaurs increases by 1.\n*├* 20th level - 2 dinosaurs.\n*└* 40th level - 3 dinosaurs...\n\n"
                text2 += "*┌* *Dino-tavern ‍🍺*\n\n"
                text2 += "*└*Take a look at the `Dino-tavern`, there you can find out information from visitors, find other players. And also get quests!\n\n"
                text2 += "*┌* *Quests 📜*\n\n"
                text2 += "*└* In the tavern you can get a quest (just wait in it), quests give interesting bonuses for the most ordinary actions!\n\n"
                text2 += "*┌* *Dungeons 🗻*\n\n"
                text2 += "*└* Embark on an exciting adventure with your friends! Adventures, bosses, unique items!\n\n"

            bot.send_message(message.chat.id, text2, parse_mode = 'Markdown')

    @staticmethod
    def not_set(bot, message, user, bd_user):

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
                    bot.send_message(message.chat.id, f'❌', reply_markup = Functions.markup(bot, 'settings', user))
                    return

                if res in ['✅ Enable', '✅ Включить']:

                    bd_user['settings']['notifications'] = True
                    users.update_one( {"userid": bd_user['userid']}, {"$set": {'settings': bd_user['settings'] }} )

                    if bd_user['language_code'] == 'ru':
                        text = '🔧 Уведомления были активированы!'
                    else:
                        text = '🔧 Notifications have been activated!'

                    bot.send_message(message.chat.id, text, reply_markup = Functions.markup(bot, "settings", user))

                if res in ['❌ Disable', '❌ Выключить']:

                    bd_user['settings']['notifications'] = False
                    users.update_one( {"userid": bd_user['userid']}, {"$set": {'settings': bd_user['settings'] }} )

                    if bd_user['language_code'] == 'ru':
                        text = '🔧 Уведомления были отключены!'
                    else:
                        text = '🔧 Notifications have been disabled!'

                    bot.send_message(message.chat.id, text, reply_markup = Functions.markup(bot, "settings", user))

                else:
                    return

            msg = bot.send_message(message.chat.id, text, reply_markup = rmk)
            bot.register_next_step_handler(msg, ret, ans, bd_user)

    @staticmethod
    def lang_set(bot, message, user, bd_user):

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
                    bot.send_message(message.chat.id, f'❌', reply_markup = Functions.markup(bot, 'settings', user))
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

                bot.send_message(message.chat.id, text, reply_markup = Functions.markup(bot, "settings", user))

            msg = bot.send_message(message.chat.id, text, reply_markup = rmk)
            bot.register_next_step_handler(msg, ret, ans, bd_user)

    @staticmethod
    def dino_prof(bot, message, user):

        bd_user = users.find_one({"userid": user.id})
        if bd_user != None:

            if len(bd_user['dinos']) > 1:
                for i in bd_user['dinos'].keys():
                    if i not in bd_user['activ_items'].keys():

                        users.update_one( {"userid": bd_user["userid"] }, {"$set": {f'activ_items.{i}': {'game': None, 'hunt': None, 'journey': None, 'unv': None} }} )
                        bd_user = users.find_one({"userid": user.id})

            if len(bd_user['dinos'].keys()) == 0:

                if bd_user['language_code'] == 'ru':
                    text = f'🥚 | В данный момент у вас нету динозавров, пожалуйста проверьте свой инвентарь. В инвентаре у вас должно быть яйцо, которое вы можете инкубировать!'
                else:
                    text = f"🥚 | You don't have any dinosaurs at the moment, please check your inventory. You must have an egg in your inventory that you can incubate!"

                bot.send_message(message.chat.id, text)

            elif len(bd_user['dinos'].keys()) > 0:

                n_dp, dp_a = Functions.dino_pre_answer(bot, message)
                if n_dp == 1:

                    bot.send_message(message.chat.id, f'❌', reply_markup = Functions.markup(bot, 1, user))
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
                                Functions.p_profile(bot, message, dino_dict[message.text][0], user, bd_user, dino_dict[message.text][1])

                            except Exception as error:
                                print('Ошибка в профиле1\n', error)

                                Functions.p_profile(bot, message, dino_dict[message.text][0], user, bd_user, dino_dict[message.text][1])

                        else:
                            bot.send_message(message.chat.id, '❌', reply_markup = Functions.markup(bot, Functions.last_markup(bd_user), bd_user ))

                    msg = bot.send_message(message.chat.id, text, reply_markup = rmk)
                    bot.register_next_step_handler(msg, ret, dino_dict, user, bd_user)

    @staticmethod
    def open_settings(bot, message, user, bd_user):

        if bd_user != None:
            settings = bd_user['settings']

            if 'vis.faq' not in settings.keys():
                settings['vis.faq'] = True

            if 'inv_view' not in settings.keys():
                settings['inv_view'] = [2, 3]

            if bd_user['language_code'] == 'ru':
                text = f'🔧 Меню настроек активировано\n\nУведомления: {settings["notifications"]}\nВидимость справочника: {settings["vis.faq"]}'.replace("True", '✔').replace("False", '❌')

            else:
                text = f'🔧 The settings menu is activated\n\nNotifications: {settings["notifications"]}\nFAQ: {settings["vis.faq"]}'.replace("True", '✔').replace("False", '❌')

            bot.send_message(message.chat.id, text, reply_markup = Functions.markup(bot, 'settings', user))

    @staticmethod
    def back_open(bot, message, user, bd_user):

        if bd_user != None:

            if bd_user['language_code'] == 'ru':
                text = '↪ Возврат в главное меню'
            else:
                text = '↪ Return to the main menu'

            bot.send_message(message.chat.id, text, reply_markup = Functions.markup(bot, 1, user))

    @staticmethod
    def friends_open(bot, message, user, bd_user):

        if bd_user != None:

            if bd_user['language_code'] == 'ru':
                text = '👥 | Перенаправление в меню друзей!'
            else:
                text = '👥 | Redirecting to the friends menu!'

            bot.send_message(message.chat.id, text, reply_markup = Functions.markup(bot, "friends-menu", user))

    @staticmethod
    def settings_faq(bot, message, user, bd_user):

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
                    bot.send_message(message.chat.id, f'❌', reply_markup = Functions.markup(bot, 'settings', user))
                    return

                if res in ['✅ Enable', '✅ Включить']:

                    bd_user['settings']['vis.faq'] = True
                    users.update_one( {"userid": bd_user['userid']}, {"$set": {'settings': bd_user['settings'] }} )

                    if bd_user['language_code'] == 'ru':
                        text = '🔧 FAQ был активирован!'
                    else:
                        text = '🔧 The FAQ has been activated!'

                    bot.send_message(message.chat.id, text, reply_markup = Functions.markup(bot, "settings", user))

                if res in ['❌ Disable', '❌ Выключить']:

                    bd_user['settings']['vis.faq'] = False
                    users.update_one( {"userid": bd_user['userid']}, {"$set": {'settings': bd_user['settings'] }} )

                    if bd_user['language_code'] == 'ru':
                        text = '🔧 FAQ был отключен!'
                    else:
                        text = '🔧 The FAQ has been disabled!'

                    bot.send_message(message.chat.id, text, reply_markup = Functions.markup(bot, "settings", user))

                else:
                    return

            msg = bot.send_message(message.chat.id, text, reply_markup = rmk)
            bot.register_next_step_handler(msg, ret, ans, bd_user)

    @staticmethod
    def inv_set_pages(bot, message, user, bd_user):

        if bd_user != None:

            gr, vr = bd_user['settings']['inv_view']

            if bd_user['language_code'] == 'ru':
                ans = ['2 | 3', '3 | 3', '2 | 2', '2 | 4', '↪ Назад']
                text = f'🎞 Режим в данный момент:\n♠ По горизонтали: {gr}\n♣ По вертикали: {vr}\n\nВыберите режим отображения инвентаря (Стандарт 2 | 3)'
            else:
                ans = ['2 | 3', '3 | 3', '2 | 2', '2 | 4', '↪ Back']
                text = f'🎞 Current mode:\n♠ Horizontally: {gr}\n♣ Vertically: {vr}\n\n Select the inventory display mode (Standard 2 | 3)'

            rmk = types.ReplyKeyboardMarkup(resize_keyboard = True, row_width = 2)
            rmk.add( *[ i for i in ans] )

            def ret(message, ans, bd_user):

                if message.text not in ans or message.text in ['↪ Назад', '↪ Back']:
                    res = None
                else:
                    res = message.text

                if res == None:
                    bot.send_message(message.chat.id, f'❌', reply_markup = Functions.markup(bot, 'settings', user))
                    return

                vviw = res.split(' | ')
                v_list = []
                for i in vviw:
                    v_list.append(int(i))

                gr, vr = v_list

                if bd_user['language_code'] == 'ru':
                    text = f'♠ По горизонтали: {gr}\n♣ По вертикали: {vr}'
                else:
                    text = f'♠ Horizontally: {gr}\n♣ Vertically: {vr}'

                bd_user['settings']['inv_view'] = v_list
                users.update_one( {"userid": bd_user['userid']}, {"$set": {'settings': bd_user['settings'] }} )

                bot.send_message(message.chat.id, text, reply_markup = Functions.markup(bot, "settings", user))

                #
                #     bd_user['settings']['vis.faq'] = True
                #     users.update_one( {"userid": bd_user['userid']}, {"$set": {'settings': bd_user['settings'] }} )
                #
                #     if bd_user['language_code'] == 'ru':
                #         text = '🔧 FAQ был активирован!'
                #     else:
                #         text = '🔧 The FAQ has been activated!'
                #
                #     bot.send_message(message.chat.id, text, reply_markup = Functions.markup(bot, "settings", user))
                #
                # if res in ['❌ Disable', '❌ Выключить']:
                #
                #     bd_user['settings']['vis.faq'] = False
                #     users.update_one( {"userid": bd_user['userid']}, {"$set": {'settings': bd_user['settings'] }} )
                #
                #     if bd_user['language_code'] == 'ru':
                #         text = '🔧 FAQ был отключен!'
                #     else:
                #         text = '🔧 The FAQ has been disabled!'
                #
                #     bot.send_message(message.chat.id, text, reply_markup = Functions.markup(bot, "settings", user))
                #
                # else:
                #     return

            msg = bot.send_message(message.chat.id, text, reply_markup = rmk)
            bot.register_next_step_handler(msg, ret, ans, bd_user)

    @staticmethod
    def add_friend(bot, message, user, bd_user):

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
                    bot.send_message(message.chat.id, f'❌', reply_markup = Functions.markup(bot, 'friends-menu', user))
                    return

                try:
                    fr_id = int(res.text)
                except:

                    if res.text == ans[0] or res.forward_from == None:
                        bot.send_message(message.chat.id, f'❌ user forward not found', reply_markup = Functions.markup(bot, 'friends-menu', user))
                        fr_id = None

                    else:
                        fr_id = res.forward_from.id


                two_user = users.find_one({"userid": fr_id})

                if two_user == None:
                    bot.send_message(message.chat.id, f'❌ user not found in base', reply_markup = Functions.markup(bot, 'friends-menu', user))
                    return

                if two_user == bd_user:
                    bot.send_message(message.chat.id, f'❌ user == friend', reply_markup = Functions.markup(bot, 'friends-menu', user))

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

                        bot.send_message(message.chat.id, f'✔', reply_markup = Functions.markup(bot, 'friends-menu', user))
                        Functions.notifications_manager(bot, 'friend_request', two_user)

                    else:

                        if bd_user['language_code'] == 'ru':
                            text = f"📜 | Данный пользователь уже в друзьях / получил запрос от вас!"

                        else:
                            text = f"📜 | This user is already a friend / has received a request from you!"

                        bot.send_message(message.chat.id, text, reply_markup = Functions.markup(bot, 'friends-menu', user))

            msg = bot.send_message(message.chat.id, text, reply_markup = rmk)
            bot.register_next_step_handler(msg, ret, ans, bd_user)

    @staticmethod
    def friends_list(bot, message, user, bd_user):

        if bd_user != None:

            friends_id = bd_user['friends']['friends_list']
            page = 1

            friends_name = []
            friends_id_d = {}

            if bd_user['language_code'] == 'ru':
                text = "👥 | Ожидайте..."
            else:
                text = "👥 | Wait..."

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

                    bot.send_message(message.chat.id, text, reply_markup = Functions.markup(bot, 'friends-menu', user))

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

                            bot.send_message(message.chat.id, text, reply_markup = Functions.markup(bot, 'friends-menu', user))

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
                                        mms = bot.send_message(message.chat.id, text, parse_mode = 'Markdown')
                                    except Exception as error:
                                        print(message.chat.id, 'ERROR Профиль', '\n', error)
                                        mms = bot.send_message(message.chat.id, text)

                            work_pr(message, friends_id, page, friends_chunks, friends_id_d, mms = mms)

                    if mms == None:
                        msg = bot.send_message(message.chat.id, text, reply_markup = rmk)
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

            for i in friends_id:
                try:
                    fr_name = bot.get_chat(int(i)).first_name
                    friends_name.append(fr_name)
                    id_names[bot.get_chat(int(i)).first_name] = i
                except:
                    pass

            friends_chunks = list(Functions.chunks(list(Functions.chunks(friends_name, 2)), 3))

            if friends_chunks == []:

                if bd_user['language_code'] == 'ru':
                    text = "👥 | Список пуст!"
                else:
                    text = "👥 | The list is empty!"

                bot.send_message(message.chat.id, text, reply_markup = Functions.markup(bot, 'friends-menu', user))
                return

            else:
                if bd_user['language_code'] == 'ru':
                    text = "➖ | Выберите пользователя для удаления из друзей > "
                else:
                    text = "➖ | Select the user to remove from friends >"
                bot.send_message(message.chat.id, text, reply_markup = Functions.markup(bot, 'friends-menu', user))

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

                        bot.send_message(message.chat.id, text, reply_markup = Functions.markup(bot, 'friends-menu', user))
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
                                bot.send_message(message.chat.id, text, reply_markup = Functions.markup(bot, 'friends-menu', user))
                                return
                            else:
                                bot.send_message(message.chat.id, text)

                    work_pr(message, friends_id, page)

                msg = bot.send_message(message.chat.id, text, reply_markup = rmk)
                bot.register_next_step_handler(msg, ret, friends_id, page, bd_user)

            work_pr(message, friends_id, page)

    @staticmethod
    def open_profile_menu(bot, message, user, bd_user):

        if bd_user != None:

            if bd_user['language_code'] == 'ru':
                text = '👁‍🗨 | Панель профиля открыта!'
            else:
                text = '👁‍🗨 | The profile panel is open!'

            bot.send_message(message.chat.id, text, reply_markup = Functions.markup(bot, "profile", user))

    @staticmethod
    def rayting(bot, message, user, bd_user):
        markup_inline = types.InlineKeyboardMarkup(row_width = 3)

        if bd_user['language_code'] == 'ru':
            text = '👁‍🗨 | Какой рейтинг вас интересует?'

            inl_l = { '🎢 Уровень': 'rayt_lvl', '🗝 Монеты': 'rayt_money', '🗻 Подземелье': 'rayt_dungeon'
                    }

        else:
            text = '👁‍🗨 | What rating are you interested in?'

            inl_l = { '🎢 Level': 'rayt_lvl', '🗝 Coins': 'rayt_money', '🗻 Dungeon': 'rayt_dungeon'
                    }

        markup_inline.add( *[ types.InlineKeyboardButton( text = inl, callback_data = inl_l[inl]) for inl in inl_l.keys() ])

        bot.send_message(message.chat.id, text, reply_markup = markup_inline)

    @staticmethod
    def open_information(bot, message, user, bd_user):

        if bd_user != None:
            text = Functions.member_profile(bot, user.id, lang = bd_user['language_code'])

            try:
                bot.send_message(message.chat.id, text, parse_mode = 'Markdown')
            except Exception as error:
                print(message.chat.id, 'ERROR Профиль', '\n', error)
                bot.send_message(message.chat.id, text)

    @staticmethod
    def open_action_menu(bot, message, user, bd_user):

        if bd_user != None:

            if bd_user['language_code'] == 'ru':
                text = '🕹 Панель действий открыта!'
            else:
                text = '🕹 The action panel is open!'

            bot.send_message(message.chat.id, text, reply_markup = Functions.markup(bot, "actions", user))

    @staticmethod
    def open_dino_tavern(bot, message, user, bd_user):

        if bd_user != None:

            if bd_user['language_code'] == 'ru':
                text = '🍺 Вы вошли в дино-таверну!\n\n📜 Во время нахождения в таверне вы можете получить квест или услышать полезную информацию!'
                text2 = '🍺 Друзья в таверне: Поиск среди толпы...'
            else:
                text = '🍺 You have entered the dino-tavern!\n\n📜 While staying in the tavern, you can get a quest or hear useful information!'
                text2 = '🍺 Friends in the tavern: Search among the crowd...'

            bot.send_message(message.chat.id, text, reply_markup = Functions.markup(bot, "dino-tavern", user))
            msg = bot.send_message(message.chat.id, text2)

            if bd_user['language_code'] == 'ru':
                text = '🍺 Друзья в таверне: '
            else:
                text = '🍺 Friends in the tavern: '

            fr_in_tav = []

            for fr_id in bd_user['friends']['friends_list']:
                fr_user = users.find_one({"userid": fr_id})
                if fr_user != None:

                    if 'last_markup' in fr_user['settings'].keys() and fr_user['settings']['last_markup'] == 'dino-tavern':

                        fr_in_tav.append(fr_user)

            if fr_in_tav == []:

                text += '❌'

            else:
                text += '\n'
                for fr_user in fr_in_tav:
                    fr_tel = bot.get_chat(fr_user['userid'])
                    if fr_tel != None:
                        text += f' ● {fr_tel.first_name}\n'

            bot.edit_message_text(text = text, chat_id = msg.chat.id, message_id = msg.message_id)

            for fr_user in fr_in_tav:

                if fr_user['language_code'] == 'ru':
                    text = f'🍺 {user.first_name} зашёл в таверну...'
                else:
                    text = f'🍺 {user.first_name} went into the tavern...'

                time.sleep(0.5)
                bot.send_message(fr_user['userid'], text)

    @staticmethod
    def dino_action_ans(bot, message, user, bd_user):

        if bd_user != None:
            if bd_user['language_code'] == 'ru':
                did = int(message.text[12:])
            else:
                did = int(message.text[8:])

            if did == int(bd_user['settings']['dino_id']):
                ll = list(bd_user['dinos'].keys())
                ind = list(bd_user['dinos'].keys()).index(str(did))

                if ind + 1 != len(ll):
                    bd_user['settings']['dino_id'] = ll[ind + 1]

                else:
                    bd_user['settings']['dino_id'] = ll[0]

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

                bot.send_message(message.chat.id, text , reply_markup = Functions.markup(bot, 'actions', user))

    @staticmethod
    def action_back(bot, message, user, bd_user):

        if bd_user['language_code'] == 'ru':
            text = '↩ Возврат в меню активностей'
        else:
            text = '↩ Return to the activity menu'

        bot.send_message(message.chat.id, text, reply_markup = Functions.markup(bot, 'actions', user))

    @staticmethod
    def rename_dino(bot, message, user, bd_user):

        if bd_user != None:
            n_dp, dp_a = Functions.dino_pre_answer(bot, message)

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
                            bot.send_message(message.chat.id, f'❌', reply_markup = Functions.markup(bot, 'settings', user))
                            return

                        dino_name = message.text.replace('*', '').replace('`', '')

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
                                    bot.send_message(message.chat.id, f'❌', reply_markup = Functions.markup(bot, 'settings', user))
                                    return
                                else:
                                    res = message.text

                                if res in ['✅ Confirm', '✅ Подтверждаю']:

                                    bd_user['dinos'][str(dino_user_id)]['name'] = dino_name
                                    users.update_one( {"userid": bd_user['userid']}, {"$set": {f'dinos.{dino_user_id}': bd_user['dinos'][str(dino_user_id)] }} )

                                    bot.send_message(message.chat.id, f'✅', reply_markup = Functions.markup(bot, 'settings', user))

                            msg = bot.send_message(message.chat.id, text, reply_markup = rmk)
                            bot.register_next_step_handler(msg, ret2, ans2, bd_user)

                    msg = bot.send_message(message.chat.id, text, reply_markup = rmk)
                    bot.register_next_step_handler(msg, ret, ans, bd_user)

                if n_dp == 1:
                    bot.send_message(message.chat.id, f'❌', reply_markup = Functions.markup(bot, 'settings', user))
                    return

                if n_dp == 2:
                    bd_dino = dp_a
                    rename(message, bd_user, user, list(bd_user['dinos'].keys())[0], dp_a)

                if n_dp == 3:
                    rmk = dp_a[0]
                    text = dp_a[1]
                    dino_dict = dp_a[2]

                    def ret(message, dino_dict, user, bd_user):
                        if message.text not in dino_dict.keys():
                            bot.send_message(message.chat.id, f'❌', reply_markup = Functions.markup(bot, 'settings', user))

                        else:
                            rename(message, bd_user, user, dino_dict[message.text][1], dino_dict[message.text][0])

                    msg = bot.send_message(message.chat.id, text, reply_markup = rmk)
                    bot.register_next_step_handler(msg, ret, dino_dict, user, bd_user)

    @staticmethod
    def dino_sleep_ac(bot, message, user, bd_user):

        if bd_user != None:
            dino = bd_user['dinos'][ str(bd_user['settings']['dino_id']) ]

            if dino != None:
                if dino['activ_status'] == 'pass_active':
                    if dino['stats']['unv'] >= 90:

                        if bd_user['language_code'] == 'ru':
                            text = '🌙 Динозавр не хочет спать!'
                        else:
                            text = "🌙 The dinosaur doesn't want to sleep!"

                        bot.send_message(message.chat.id, text, reply_markup = Functions.markup(bot, "actions", user))

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

                            bot.send_message(message.chat.id, text , reply_markup = Functions.markup(bot, 'actions', user))

                        if Functions.acc_check(bot, bd_user, '16', bd_user['settings']['dino_id'], True) == False:
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
                                    bot.send_message(message.chat.id, f'❌', reply_markup = Functions.markup(bot, 'actions', user))
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
                                            bot.send_message(message.chat.id, f'❌', reply_markup = Functions.markup(bot, 'actions', user))
                                            return

                                        if number <= 5 or number > 480:

                                            if bd_user['language_code'] == 'ru':
                                                text = '❌ | Требовалось указать время в минутах больше 5-ти минут и меньше 8-ми часов (480)!'
                                            else:
                                                text = '❌ | It was required to specify the time in minutes more than 5 minutes and less than 8 hours (480)!'

                                            bot.send_message(message.chat.id, text, reply_markup = Functions.markup(bot, 'actions', user))

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

                                            bot.send_message(message.chat.id, text , reply_markup = Functions.markup(bot, 'actions', user))



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

                    bot.send_message(message.chat.id, text, reply_markup = Functions.inline_markup(bot, f'open_dino_profile', message.chat.id, ['Открыть профиль', 'Open a profile'], str(bd_user['settings']['dino_id']) ))

    @staticmethod
    def dino_unsleep_ac(bot, message, user, bd_user):

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

                    bot.send_message(message.chat.id, text , reply_markup = Functions.markup(bot, 'actions', user))

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

                        bot.send_message(message.chat.id, text , reply_markup = Functions.markup(bot, 'actions', user))

                    else:

                        bd_user['dinos'][ d_id ]['stats']['mood'] -= r_n

                        if bd_user['dinos'][ d_id ]['stats']['mood'] < 0:
                            bd_user['dinos'][ d_id ]['stats']['mood'] = 0

                        if bd_user['language_code'] == 'ru':
                            text = f'🌙 Ваш динозавр пробудился. Он сильно не доволен что вы его разбудили!\nДинозавр потерял {r_n}% настроения.'
                        else:
                            text = f"🌙 Your dinosaur has awakened. He is very unhappy that you woke him up!\nDinosaur lost {r_n}% of mood."

                        bot.send_message(message.chat.id, text , reply_markup = Functions.markup(bot, 'actions', user))

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
                bot.send_message(message.chat.id, f'❌', reply_markup = Functions.markup(bot, 'actions', user))

    @staticmethod
    def dino_journey(bot, message, user, bd_user):

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

                    item_5 = types.InlineKeyboardButton( text = '240 мин.', callback_data = f"24min_journey_{str(bd_user['settings']['dino_id'])}")

                else:
                    text = "🌳 How long to send a dinosaur on a journey?"

                    item_0 = types.InlineKeyboardButton( text = '10 min.', callback_data = f"10min_journey_{str(bd_user['settings']['dino_id'])}")

                    item_1 = types.InlineKeyboardButton( text = '30 min.', callback_data = f"30min_journey_{str(bd_user['settings']['dino_id'])}")

                    item_2 = types.InlineKeyboardButton( text = '60 min.', callback_data = f"60min_journey_{str(bd_user['settings']['dino_id'])}")

                    item_3 = types.InlineKeyboardButton( text = '90 min.', callback_data = f"90min_journey_{str(bd_user['settings']['dino_id'])}")

                    item_4 = types.InlineKeyboardButton( text = '120 min.', callback_data = f"12min_journey_{str(bd_user['settings']['dino_id'])}")

                    item_5 = types.InlineKeyboardButton( text = '240 min.', callback_data = f"24min_journey_{str(bd_user['settings']['dino_id'])}")

                markup_inline.add(item_0, item_1, item_2, item_3, item_4)
                markup_inline.add(item_5)

                bot.send_message(message.chat.id, text, reply_markup = markup_inline)

            else:

                if bd_user['language_code'] == 'ru':
                    text = f"❗ | Ваш динозавр уже чем то занят, проверьте профиль!"

                else:
                    text = f"❗ | Your dinosaur is already busy with something, check the profile!"

                bot.send_message(message.chat.id, text, reply_markup = Functions.inline_markup(bot, f'open_dino_profile', message.chat.id, ['Открыть профиль', 'Open a profile'], str(bd_user['settings']['dino_id']) ))

    @staticmethod
    def dino_unjourney(bot, message, user, bd_user):

        if bd_user != None:
            dino = bd_user['dinos'][ str(bd_user['settings']['dino_id']) ]

            if dino['activ_status'] == 'journey' and dino != None:
                if random.randint(1,2) == 1:

                    dino_id = bd_user['settings']['dino_id']

                    Functions.journey_end_log(bot, bd_user['userid'], dino_id)

                    bd_user['dinos'][ dino_id ]['activ_status'] = 'pass_active'

                    del bd_user['dinos'][ dino_id ]['journey_time']
                    del bd_user['dinos'][ dino_id ]['journey_log']

                    users.update_one( {"userid": bd_user['userid']}, {"$set": {f"dinos.{dino_id}": bd_user['dinos'][dino_id] }} )


                else:
                    if bd_user['language_code'] == 'ru':
                        text = f'🔇 | Вы попробовали вернуть динозавра, но что-то пошло не так...'
                    else:
                        text = f"🔇 | You tried to bring the dinosaur back, but something went wrong..."

                    bot.send_message(message.chat.id, text , reply_markup = Functions.markup(bot, 'actions', user))
            else:
                bot.send_message(message.chat.id, f'❌', reply_markup = Functions.markup(bot, 'actions', user))

    @staticmethod
    def dino_entert(bot, message, user, bd_user):

        if bd_user != None:
            dino = bd_user['dinos'][ str(bd_user['settings']['dino_id']) ]

            if dino['activ_status'] in ['pass_active', 'game']:

                if bd_user['language_code'] == 'ru':
                    text = f"🎮 | Перенаправление в меню развлечений!"

                else:
                    text = f"🎮 | Redirecting to the entertainment menu!"

                bot.send_message(message.chat.id, text, reply_markup = Functions.markup(bot, 'games', user))

            else:

                if bd_user['language_code'] == 'ru':
                    text = f"❗ | Ваш динозавр уже чем то занят, проверьте профиль!"

                else:
                    text = f"❗ | Your dinosaur is already busy with something, check the profile!"

                bot.send_message(message.chat.id, text, reply_markup = Functions.inline_markup(bot, f'open_dino_profile', message.chat.id, ['Открыть профиль', 'Open a profile'], str(bd_user['settings']['dino_id']) ))

    @staticmethod
    def dino_entert_games(bot, message, user, bd_user):

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

                item_1 = types.InlineKeyboardButton( text = text[0], callback_data = f"1_{g}_game_{str(bd_user['settings']['dino_id'])}")
                item_2 = types.InlineKeyboardButton( text = text[1], callback_data = f"2_{g}_game_{str(bd_user['settings']['dino_id'])}")
                item_3 = types.InlineKeyboardButton( text = text[2], callback_data = f"3_{g}_game_{str(bd_user['settings']['dino_id'])}")
                markup_inline.add(item_1, item_2, item_3)

                bot.send_message(message.chat.id, m_text, reply_markup = markup_inline)

    @staticmethod
    def dino_stop_games(bot, message, user, bd_user):

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

                    dino_id = str(bd_user['settings']['dino_id'])

                    game_time = (int(time.time()) - bd_user['dinos'][ dino_id ]['game_start']) // 60

                    Dungeon.check_quest(bot, bd_user, met = 'check', quests_type = 'do', kwargs = {'dp_type': 'game', 'act': game_time } )

                    bd_user['dinos'][ dino_id ]['activ_status'] = 'pass_active'

                    try:
                        del bd_user['dinos'][ dino_id ]['game_time']
                        del bd_user['dinos'][ dino_id ]['game_%']
                        del bd_user['dinos'][ dino_id ]['game_start']
                    except:
                        pass

                    users.update_one( {"userid": bd_user['userid']}, {"$set": {f'dinos.{dino_id}': bd_user['dinos'][dino_id] }} )

                    bot.send_message(message.chat.id, text, reply_markup = Functions.markup(bot, 'games', user))

                else:

                    if bd_user['language_code'] == 'ru':
                        text = f"🎮 | Динозавра невозможно оторвать от игры, попробуйте ещё раз. Имейте ввиду, динозавр будет расстроен."

                    else:
                        text = f"🎮 | It is impossible to tear the dinosaur away from the game, try again. Keep in mind, the dinosaur will be upset."

                    bot.send_message(message.chat.id, text, reply_markup = Functions.markup(bot, 'games', user))

    @staticmethod
    def dino_feed(bot, message, user, bd_user):

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
                if Functions.item_authenticity(i) == True:
                    items_id[ items_f['items'][ i['item_id'] ][lg] ] = i
                    items_names.append( items_f['items'][ i['item_id'] ][lg] )

                else:

                    items_id[ items_f['items'][ i['item_id'] ][lg] + f" ({Functions.qr_item_code(i, False)})" ] = i
                    items_names.append( items_f['items'][ i['item_id'] ][lg] + f" ({Functions.qr_item_code(i, False)})" )

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

            pages = list(Functions.chunks(list(Functions.chunks(items_sort, 2)), 3))

            for i in pages:
                for ii in i:
                    if len(ii) == 1:
                        ii.append(' ')

                if len(i) != 3:
                    for iii in range(3 - len(i)):
                        i.append([' ', ' '])

            def work_pr(message, pages, page, items_id, ind_sort_it):
                global l_pages, l_page, l_ind_sort_it

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

                        bot.send_message(message.chat.id, text, reply_markup = Functions.markup(bot, 'actions', user))
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

                                    bot.send_message(message.chat.id, text, reply_markup = Functions.markup(bot, 'actions', user))
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

                                        bot.send_message(message.chat.id, text, reply_markup = Functions.markup(bot, 'actions', user))
                                        return

                                if col < 1:

                                    if bd_user['language_code'] == 'ru':
                                        text = f"Введите корректное число!"
                                    else:
                                        text = f"Enter the correct number!"

                                    bot.send_message(message.chat.id, text, reply_markup = Functions.markup(bot, 'actions', user))
                                    return

                                if 'abilities' in user_item.keys():
                                    if 'uses' in user_item['abilities'].keys():
                                        if col > user_item['abilities']['uses']:

                                            if bd_user['language_code'] == 'ru':
                                                text = f"Данный предмет нельзя использовать столько раз!"
                                            else:
                                                text = f"This item cannot be used so many times!"

                                            bot.send_message(message.chat.id, text, reply_markup = Functions.markup(bot, 'actions', user))
                                            return

                                if 'abilities' not in user_item.keys() or 'uses' not in user_item['abilities'].keys():

                                    if col > mx_col:

                                        if bd_user['language_code'] == 'ru':
                                            text = f"У вас нет столько предметов в инвентаре!"
                                        else:
                                            text = f"You don't have that many items in your inventory!"

                                        bot.send_message(message.chat.id, text, reply_markup = Functions.markup(bot, 'actions', user))

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

                                if 'abilities' in user_item.keys():
                                    if 'uses' in user_item['abilities'].keys():

                                        if user_item['abilities']['uses'] != -100:

                                            s_col = user_item['abilities']['uses'] - col

                                            if s_col > 0:
                                                users.update_one( {"userid": user.id}, {"$set": {f'inventory.{bd_user["inventory"].index(user_item)}.abilities.uses': user_item['abilities']['uses'] - col}} )

                                            else:
                                                bd_user['inventory'].remove(user_item)
                                                users.update_one( {"userid": user.id}, {"$set": {'inventory': bd_user['inventory'] }} )

                                else:

                                    for i in range(col):
                                        bd_user['inventory'].remove(user_item)

                                    users.update_one( {"userid": bd_user['userid']}, {"$set": {'inventory': bd_user['inventory'] }} )

                                bot.send_message(message.chat.id, text, reply_markup = Functions.markup(bot, 'actions', user))

                                Dungeon.check_quest(bot, bd_user, met = 'check', quests_type = 'do', kwargs = {'dp_type': 'feed', 'act': col, 'item': str(item_id) } )

                            msg = bot.send_message(message.chat.id, text_col, reply_markup = rmk)
                            bot.register_next_step_handler(msg, corm, bd_user, user_item, item, d_dino, mx_col, col_l)

                msg = bot.send_message(message.chat.id, textt, reply_markup = rmk)
                bot.register_next_step_handler(msg, ret, l_pages, l_page, l_ind_sort_it, bd_user, user, pages, page, items_id, ind_sort_it)

            work_pr(message, pages, page, items_id, ind_sort_it)

    @staticmethod
    def collecting_food(bot, message, user, bd_user):

        eat_c = Functions.items_counting(bd_user, '+eat')
        if eat_c >= 300:

            if bd_user['language_code'] == 'ru':
                text = f'🌴 | Ваш инвентарь ломится от количества еды! В данный момент у вас {eat_c} предметов которые можно съесть!'
            else:
                text = f'🌴 | Your inventory is bursting with the amount of food! At the moment you have {eat_c} items that can be eaten!'

            bot.send_message(message.chat.id, text, reply_markup = Functions.markup(bot, 'actions', user))
            return

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

                    bot.send_message(message.chat.id, text, reply_markup = Functions.markup(bot, 'actions', user))

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

                            bot.send_message(message.chat.id, text, reply_markup = Functions.markup(bot, 'actions', user))

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
                            bot.send_message(message.chat.id, text, reply_markup = Functions.markup(bot, 'actions', user))

                    msg = bot.send_message(message.chat.id, text, reply_markup = rmk)
                    bot.register_next_step_handler(msg, ret2, ans, bd_user)

            msg = bot.send_message(message.chat.id, text, reply_markup = rmk)
            bot.register_next_step_handler(msg, ret, bbt, bd_user)

        else:

            if bd_user['language_code'] == 'ru':
                text = f"❗ | Ваш динозавр уже чем то занят, проверьте профиль!"

            else:
                text = f"❗ | Your dinosaur is already busy with something, check the profile!"

            bot.send_message(message.chat.id, text, reply_markup = Functions.inline_markup(bot, f'open_dino_profile', message.chat.id, ['Открыть профиль', 'Open a profile'], str(bd_user['settings']['dino_id']) ))

    @staticmethod
    def coll_progress(bot, message, user, bd_user):
        markup_inline = types.InlineKeyboardMarkup()

        if bd_user['dinos'][ bd_user['settings']['dino_id'] ]['activ_status'] == 'hunting':
            number = bd_user['dinos'][ bd_user['settings']['dino_id'] ]['target'][0]
            tnumber = bd_user['dinos'][ bd_user['settings']['dino_id'] ]['target'][1]
            prog = number / (tnumber / 100)

            if bd_user['language_code'] == 'ru':
                text = f'🍱 | Текущий прогресс: {int( prog )}%\n🎲 | Цель: {tnumber}'
                inl_l = {'❌ Отменить': f"cancel_progress {bd_user['settings']['dino_id']}" }

            else:
                text = f'🍱 | Current progress: {int( prog )}%\n🎲 | Goal: {tnumber}'
                inl_l = {'❌ Cancel': f"cancel_progress {bd_user['settings']['dino_id']}" }

            markup_inline.add( *[ types.InlineKeyboardButton( text = inl, callback_data = f"{inl_l[inl]}") for inl in inl_l.keys() ])
            bot.send_message(message.chat.id, text, reply_markup = markup_inline)

    @staticmethod
    def invite_friend(bot, message, user, bd_user):

        if bd_user != None:
            coins = 200

            if bd_user['language_code'] == 'ru':
                text = f"🤍 | Перенаправление в меню реферальной системы!\n\n💜 | При достижению 5-го уровня вашим другом, вы получите 🥚 Необычное/Редкое яйцо динозавра!\n\n❤ | Друг получит бонус в размере: {coins} монет, 🍯 Баночка мёда х2, 🧸 Мишка, 🍗 Куриная ножка x2, 🍒 Ягоды x2, 🦪 Мелкая рыба x2, 🍪 Печенье x2"

            else:
                text = f"🤍 | Redirection to the referral system menu!\n\n💜 | When your friend reaches the 5th level, you will receive an Unusual/Rare dinosaur egg!\n\n❤ | Friend will receive a bonus: {coins} coins, 🍯 Jar of honey x2, 🧸 Bear, 🍗 Chicken leg x2, 🍒 Berries x2, 🦪 Small fish x2, 🍪 Cookies x2"

            bot.send_message(message.chat.id, text, reply_markup = Functions.markup(bot, "referal-system", user))

    @staticmethod
    def friends_menu(bot, message, user, bd_user):

        if bd_user != None:
            dino = bd_user['dinos'][ str(bd_user['settings']['dino_id']) ]

            if bd_user['language_code'] == 'ru':
                text = f"👥 | Перенаправление в меню друзей!"

            else:
                text = f"👥 | Redirecting to the friends menu!"

            bot.send_message(message.chat.id, text, reply_markup = Functions.markup(bot, "friends-menu", user))

    @staticmethod
    def generate_fr_code(bot, message, user, bd_user):

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

                bot.send_message(message.chat.id, text, parse_mode = 'Markdown', reply_markup = Functions.markup(bot, "referal-system", user))

    @staticmethod
    def enter_fr_code(bot, message, user, bd_user):

        rf = referal_system.find_one({"id": 1})

        def ret(message, bd_user):
            if message.text in rf['codes']:
                if str(bd_user['referal_system']['my_cod']) != message.text:
                    items = ['1', '1', '2', '2', '16', '12', '12', '11', '11', '13', '13']
                    coins = 200
                    bd_user['coins'] += coins
                    for i in items:
                        Functions.add_item_to_user(bd_user, i)

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

            bot.send_message(message.chat.id, text, reply_markup = Functions.markup(bot, "referal-system", user))


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

                bot.send_message(message.chat.id, text, parse_mode = 'Markdown', reply_markup = Functions.markup(bot, "referal-system", user))

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

    @staticmethod
    def acss(bot, message, user, bd_user):

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
                        bot.send_message(message.chat.id, f'❌', reply_markup = Functions.markup(bot, 'profile', user))
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

                        bot.send_message(message.chat.id, text, reply_markup = Functions.markup(bot, 'profile', user))
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

                    pages = list(Functions.chunks(list(Functions.chunks(items_sort, 2)), 2))

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

                        l_pages = pages
                        l_page = page
                        l_ind_sort_it = ind_sort_it

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

                                bot.send_message(message.chat.id, text, reply_markup = Functions.markup(bot, 'profile', user))
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

                                        bot.send_message(message.chat.id, text, reply_markup = Functions.markup(bot, 'profile', user))

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

                                        bot.send_message(message.chat.id, text, reply_markup = Functions.markup(bot, 'profile', user))

                        msg = bot.send_message(message.chat.id, textt, reply_markup = rmk)
                        bot.register_next_step_handler(msg, ret, l_pages, l_page, l_ind_sort_it, bd_user, user, pages, page, items_id, ind_sort_it, lg, ac_type)

                    work_pr(message, pages, page, items_id, ind_sort_it, lg, ac_type)

                msg = bot.send_message(message.chat.id, text, reply_markup = rmk)
                bot.register_next_step_handler(msg, ret_zero, ans, bd_user)

            n_dp, dp_a = Functions.dino_pre_answer(bot, message)
            if n_dp == 1:

                bot.send_message(message.chat.id, f'❌', reply_markup = Functions.markup(bot, 1, user))
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
                        bot.send_message(message.chat.id, '❓', reply_markup = Functions.markup(bot, "profile", user))

                msg = bot.send_message(message.chat.id, text, reply_markup = rmk)
                bot.register_next_step_handler(msg, ret, dino_dict, user, bd_user)

    @staticmethod
    def open_market_menu(bot, message, user, bd_user):

        if bd_user != None:

            if bd_user['language_code'] == 'ru':
                text = '🛒 Панель рынка открыта!'
            else:
                text = '🛒 The market panel is open!'

            bot.send_message(message.chat.id, text, reply_markup = Functions.markup(bot, "market", user))

    @staticmethod
    def my_products(bot, message, user, bd_user):

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

                pages = list(Functions.chunks(products, 5))

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

                        bot.send_message(message.chat.id, text, reply_markup = Functions.markup(bot, 'market', user))
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

    @staticmethod
    def delete_product(bot, message, user, bd_user):

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

                pages = list(Functions.chunks(products, 5))

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

                        bot.send_message(message.chat.id, text, reply_markup = Functions.markup(bot, 'market', user))
                        return

                    if message.text not in ans:

                        try:
                            number = int(message.text)

                        except:

                            if bd_user['language_code'] == 'ru':
                                text = "🛒 | Возвращение в меню рынка!"
                            else:
                                text = "🛒 | Return to the market menu!"

                            bot.send_message(message.chat.id, text, reply_markup = Functions.markup(bot, 'market', user))
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

                            bot.send_message(message.chat.id, text, reply_markup = Functions.markup(bot, 'market', user))

                        else:
                            data_items = items_f['items']
                            prod = market_['products'][str(user.id)]['products'][nn_number]

                            if data_items[ prod['item']['item_id'] ]['type'] == '+eat':

                                eat_c = Functions.items_counting(bd_user, '+eat')
                                if eat_c >= 300:

                                    if bd_user['language_code'] == 'ru':
                                        text = f'🌴 | Ваш инвентарь ломится от количества еды! В данный момент у вас {eat_c} предметов которые можно съесть!'
                                    else:
                                        text = f'🌴 | Your inventory is bursting with the amount of food! At the moment you have {eat_c} items that can be eaten!'

                                    bot.send_message(message.chat.id, text, reply_markup = Functions.markup(bot, 'market', user))
                                    return

                            for i in range(prod['col'][1] - prod['col'][0]):
                                bd_user['inventory'].append(prod['item'])

                            del market_['products'][str(user.id)]['products'][nn_number]

                            market.update_one( {"id": 1}, {"$set": {'products': market_['products'] }} )
                            users.update_one( {"userid": user.id}, {"$set": {'inventory': bd_user['inventory']}} )

                            if bd_user['language_code'] == 'ru':
                                text = "🛒 | Продукт удалён!"
                            else:
                                text = "🛒 | The product has been removed!"

                            bot.send_message(message.chat.id, text, reply_markup = Functions.markup(bot, 'market', user))

                bot.register_next_step_handler(msg_g, check_key, page, pages, ans)

    @staticmethod
    def search_pr(bot, message, user, bd_user):

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

                    bot.send_message(message.chat.id, text, reply_markup = Functions.markup(bot, 'market', user))
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

                        bot.send_message(message.chat.id, text, reply_markup = Functions.markup(bot, 'market', user))
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

                        bot.send_message(message.chat.id, text, reply_markup = Functions.markup(bot, 'market', user))
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

                    bot.send_message(message.chat.id, text, reply_markup = Functions.markup(bot, 'market', user))
                    return


            msg = bot.send_message(message.chat.id, text, reply_markup = rmk, parse_mode = 'Markdown')
            bot.register_next_step_handler(msg, name_reg )

    @staticmethod
    def random_search(bot, message, user, bd_user):

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
                    text += f"*{a}#* {items_f['items'][i['item']['item_id']]['nameru']}\n     *└* Цена за 1х: {i['price']}\n         *└* Количество: {i['col'][1] - i['col'][0]}"

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

    @staticmethod
    def rarity_change(bot, message, user, bd_user):

        data_items = items_f['items']
        bd_user = Functions.dino_q(bd_user)

        def inf_message(dino_id):

            data_q_r = { 'com': {'money': 2000,  'materials': ['21']  } ,
                         'unc': {'money': 4000, 'materials': ['20'] } ,
                         'rar': {'money': 8000, 'materials': ['22'] } ,
                         'myt': {'money': 16000, 'materials': ['23'] } ,
                         'leg': {'money': 32000, 'materials': ['24'] } ,
                         'ran': {'money': 5000, 'materials': ['3']  } ,
                       }

            r_text = { 'com': ['Обычный', 'Common'] ,
                       'unc': ['Необычный', 'Unusual'] ,
                       'rar': ['Редкий', 'Rare'] ,
                       'myt': ['Мистический', 'Mystical'] ,
                       'leg': ['Легендарный', 'Legendary'] ,
                       'ran': ['Случайный', 'Random'] ,
                       }

            ql = list( data_q_r.keys() )

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

                cmm.append(types.InlineKeyboardButton( text = f'♻ {nn}', callback_data = f"change_rarity {dino_id} {i}"))

            markup_inline.add( *cmm )

            bot.send_message(message.chat.id, text_m, reply_markup = markup_inline, parse_mode = 'Markdown')
            bot.send_message(message.chat.id, text_p2, reply_markup = Functions.markup(bot, Functions.last_markup(bd_user, alternative = 'dino-tavern'), bd_user ), parse_mode = 'Markdown')

        n_dp, dp_a = Functions.dino_pre_answer(bot, message, type = 'noall')
        if n_dp == 1:

            bot.send_message(message.chat.id, f'❌', reply_markup = Functions.markup(bot, Functions.last_markup(bd_user, alternative = 'dino-tavern'), bd_user ))
            return

        if n_dp == 2:
            bd_dino = dp_a

            inf_message(  list(bd_user['dinos'].keys())[0]  )

        if n_dp == 3:
            rmk = dp_a[0]
            text = dp_a[1]
            dino_dict = dp_a[2]

            def ret(message, dino_dict, user, bd_user):

                if message.text in dino_dict.keys():

                    inf_message( dino_dict[message.text][1] )

                else:
                    bot.send_message(message.chat.id, '❌', reply_markup = Functions.markup(bot, Functions.last_markup(bd_user), bd_user ))

            msg = bot.send_message(message.chat.id, text, reply_markup = rmk)
            bot.register_next_step_handler(msg, ret, dino_dict, user, bd_user)

    @staticmethod
    def dungeon_menu(bot, message, user, bd_user):

        if bd_user != None:

            for din in bd_user['dinos']:

                if 'dungeon' not in bd_user['dinos'][din].keys():
                    bd_user['dinos'][din]['dungeon'] = {"equipment": {'armor': None, 'weapon': None}}

                    users.update_one( {"userid": bd_user['userid']}, {"$set": {f'dinos.{din}': bd_user['dinos'][din] }} )

            if 'user_dungeon' not in bd_user.keys():
                bd_user['user_dungeon'] = { "equipment": {'backpack': None}, 'statistics': [] }

                users.update_one( {"userid": bd_user['userid']}, {"$set": {f'user_dungeon': bd_user['user_dungeon'] }} )


            if bd_user['language_code'] == 'ru':
                text = f"🗻 | Вы перешли в меню подготовки к подземелью!"

            else:
                text = f"🗻 | You have moved to the dungeon preparation menu!"

            bot.send_message(message.chat.id, text, reply_markup = Functions.markup(bot, "dungeon_menu", user))

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

            bot.send_message(message.chat.id, text, parse_mode = 'Markdown')

    @staticmethod
    def dungeon_create(bot, message, user, bd_user):

        if bd_user != None:

            dung = dungeons.find_one({"dungeonid": user.id})

            if dung == None:

                dungs = dungeons.find({ })

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

                mg = bot.send_message(message.chat.id, text, reply_markup = Functions.markup(bot, "dungeon", user))

                dng, inf = Dungeon.base_upd(userid = user.id)
                inf = Dungeon.message_upd(bot, userid = user.id, dungeonid = user.id)

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

                dungs = dungeons.find({ })

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

                        msg = bot.send_message(message.chat.id, text)

                    else:
                        dung = dungeons.find_one({"dungeonid": code})

                        if dung == None:

                            if bd_user['language_code'] == 'ru':
                                text = f'❗ | Введите корректный код!'

                            else:
                                text = f'❗ | Enter the correct code!'

                            msg = bot.send_message(message.chat.id, text)

                        else:

                            if dung['dungeon_stage'] == 'preparation':

                                if bd_user['language_code'] == 'ru':
                                    text = f'⚙ | Генерация...'

                                else:
                                    text = f'⚙ | Generation...'

                                mg = bot.send_message(message.chat.id, text, reply_markup = Functions.markup(bot, "dungeon", user))

                                dng, inf = Dungeon.base_upd(userid = user.id, dungeonid = code, type = 'add_user')

                                inf = Dungeon.message_upd(bot, userid = user.id, dungeonid = dng['dungeonid'], upd_type = 'all')

                                bot.delete_message(user.id, mg.message_id)

                            else:

                                if bd_user['language_code'] == 'ru':
                                    text = f'❗ | На этой стадии нельзя присоединится к подземелью!'

                                else:
                                    text = f"❗ | You can't join the dungeon at this stage!"

                                msg = bot.send_message(message.chat.id, text)


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

                bot.send_message(message.chat.id, '❌', reply_markup = Functions.markup(bot, Functions.last_markup(bd_user), bd_user ))
                return

            items = []

            for i in bd_user['inventory']:
                itm = data_items[ i['item_id'] ]

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

                bot.send_message(message.chat.id, text, reply_markup = Functions.markup(bot, 'dungeon_menu', user))
                return

            data_items = items_f['items']
            items_id = {}
            page = 1
            items_names = []

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

            pages = list(Functions.chunks(list(Functions.chunks(items_sort, 2)), 2))

            if len(pages) == 0:
                pages = [ [ ] ]

            for i in pages:
                for ii in i:
                    if len(ii) == 1:
                        ii.append(' ')

                if len(i) != 2:
                    for iii in range(2 - len(i)):
                        i.append([' ', ' '])

            def work_pr(message, pages, page, items_id, ind_sort_it, lg, type_eq, dino_id):

                l_pages = pages
                l_page = page
                l_ind_sort_it = ind_sort_it

                rmk = types.ReplyKeyboardMarkup(resize_keyboard = True, row_width = 3)
                for i in pages[page-1]:
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

                def ret(message, l_pages, l_page, l_ind_sort_it, bd_user, user, pages, page, items_id, ind_sort_it, lg, type_eq, dino_id):
                    if message.text in ['↩ Назад', '↩ Back']:
                        res = None

                    else:
                        if message.text in list(l_ind_sort_it.keys()) or message.text in ['◀', '▶', '🔻 Снять', '🔻 Remove']:
                            res = message.text
                        else:
                            res = None

                    if res == None:
                        if bd_user['language_code'] == 'ru':
                            text = "⚙ | Возвращение"
                        else:
                            text = "⚙ | Return"

                        bot.send_message(message.chat.id, text, reply_markup = Functions.markup(bot, 'dungeon_menu', user))
                        return '12'

                    else:
                        if res == '◀':
                            if page - 1 == 0:
                                page = 1
                            else:
                                page -= 1

                            work_pr(message, pages, page, items_id, ind_sort_it, lg, type_eq, dino_id)

                        elif res == '▶':
                            if page + 1 > len(l_pages):
                                page = len(l_pages)
                            else:
                                page += 1

                            work_pr(message, pages, page, items_id, ind_sort_it, lg, type_eq, dino_id)

                        else:

                            if res in ['🔻 Снять', '🔻 Remove']:

                                if type_eq in ['weapon', 'armor']:
                                    item = bd_user['dinos'][dino_id]['dungeon']['equipment'][type_eq]

                                    if item != None:

                                        users.update_one( {"userid": bd_user['userid']}, {"$push": {'inventory': item }} )

                                        bd_user['dinos'][dino_id]['dungeon']['equipment'][type_eq] = None

                                        users.update_one( {"userid": bd_user['userid']}, {"$set": {'dinos': bd_user['dinos'] }} )

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
                                        users.update_one( {"userid": bd_user['userid']}, {"$push": {'inventory': item }} )

                                        bd_user['user_dungeon']['equipment'][type_eq] = None

                                        users.update_one( {"userid": bd_user['userid']}, {"$set": {'user_dungeon': bd_user['user_dungeon'] }} )

                                        if bd_user['language_code'] == 'ru':
                                            text = "🎴 | Активный предмет снят"
                                        else:
                                            text = "🎴 | Active item removed"

                                    else:

                                        if bd_user['language_code'] == 'ru':
                                            text = "🎴 | В данный момент нет активного предмета!"
                                        else:
                                            text = "🎴 | There is no active item at the moment!"

                                bot.send_message(message.chat.id, text, reply_markup = Functions.markup(bot, 'dungeon_menu', user))

                            else:
                                if type_eq in ['weapon', 'armor']:
                                    item = bd_user['dinos'][dino_id]['dungeon']['equipment'][type_eq]

                                    if item != None:

                                        bd_user['inventory'].append(item)
                                        bd_user['dinos'][dino_id]['dungeon']['equipment'][type_eq] = None


                                    itemm = items_id[ l_ind_sort_it[res] ]
                                    bd_user['dinos'][dino_id]['dungeon']['equipment'][type_eq] = itemm

                                    users.update_one( {"userid": bd_user['userid']}, {"$set": {'dinos': bd_user['dinos'] }} )

                                if type_eq in ['backpack']:
                                    item = bd_user['user_dungeon']['equipment'][type_eq]

                                    if item != None:

                                        bd_user['inventory'].append(item)
                                        bd_user['user_dungeon']['equipment'][type_eq] = None

                                    itemm = items_id[ l_ind_sort_it[res] ]
                                    bd_user['user_dungeon']['equipment'][type_eq] = itemm

                                    users.update_one( {"userid": bd_user['userid']}, {"$set": {'user_dungeon': bd_user['user_dungeon'] }} )

                                if bd_user['language_code'] == 'ru':
                                    text = "🎴 | Активный предмет установлен!"
                                else:
                                    text = "🎴 | The active item is installed!"

                                bd_user['inventory'].remove(itemm)
                                users.update_one( {"userid": bd_user['userid']}, {"$set": {'inventory': bd_user['inventory'] }} )

                                bot.send_message(message.chat.id, text, reply_markup = Functions.markup(bot, 'dungeon_menu', user))

                msg = bot.send_message(message.chat.id, textt, reply_markup = rmk)
                bot.register_next_step_handler(msg, ret, l_pages, l_page, l_ind_sort_it, bd_user, user, pages, page, items_id, ind_sort_it, lg, type_eq, dino_id)

            work_pr(message, pages, page, items_id, ind_sort_it, lg, type_eq, dino_id)

        data_items = items_f['items']

        def type_answer(message, dino_id):
            dino = bd_user['dinos'][dino_id]

            if bd_user['language_code'] == 'ru':
                ans = [ '🗡 Оружие', '🛡 Броня', '🎒 Рюкзак', '↪ Назад' ]
            else:
                ans = [ '🗡 Weapon', '🛡 Armor', '🎒 Backpack', '↪ Back' ]

            rmk = types.ReplyKeyboardMarkup(resize_keyboard = True, row_width = 2)
            rmk.add(ans[0], ans[1], ans[2])
            rmk.add(ans[3])

            if dino['dungeon']['equipment']['weapon'] != None: w_n = data_items[ dino['dungeon']['equipment']['weapon']['item_id'] ][ f'name{ bd_user["language_code"] }' ]
            else: w_n = '-'

            if dino['dungeon']['equipment']['armor'] != None: a_n = data_items[ dino['dungeon']['equipment']['armor']['item_id'] ][ f'name{ bd_user["language_code"] }' ]
            else: a_n = '-'

            if bd_user['user_dungeon']['equipment']['backpack'] != None: b_n = data_items[ bd_user['user_dungeon']['equipment']['backpack']['item_id'] ][ f'name{ bd_user["language_code"] }' ]
            else: b_n = '-'

            if bd_user['language_code'] == 'ru':
                text = f'Экипированно:\n🗡: {w_n}\n🛡: {a_n}\n🎒: {b_n}\n\n⚙ | Выберите что вы хотите экипировать >'

            else:
                text = f'Equipped:\n🗡: {w_n}\n🛡: {a_n}\n🎒: {b_n}\n\n⚙ | Choose what you want to equip >'

            msg = bot.send_message(message.chat.id, text, reply_markup = rmk)
            bot.register_next_step_handler(msg, work_pr_zero, dino_id)

        n_dp, dp_a = Functions.dino_pre_answer(bot, message, type = 'noall')
        if n_dp == 1:

            bot.send_message(message.chat.id, f'❌', reply_markup = Functions.markup(bot, Functions.last_markup(bd_user, alternative = 'dungeon_menu'), bd_user ))
            return

        if n_dp == 2:
            bd_dino = dp_a

            type_answer( message, list(bd_user['dinos'].keys())[0]  )

        if n_dp == 3:
            rmk = dp_a[0]
            text = dp_a[1]
            dino_dict = dp_a[2]

            def ret(message, dino_dict, user, bd_user):

                if message.text in dino_dict.keys():

                    type_answer( message, dino_dict[message.text][1] )

                else:
                    bot.send_message(message.chat.id, '❌', reply_markup = Functions.markup(bot, Functions.last_markup(bd_user), bd_user ))

            msg = bot.send_message(message.chat.id, text, reply_markup = rmk)
            bot.register_next_step_handler(msg, ret, dino_dict, user, bd_user)

    @staticmethod
    def dungeon_statist(bot, message, user, bd_user):

        if 'user_dungeon' in bd_user.keys():
            ns_res = None
            st = bd_user['user_dungeon']['statistics']

            for i in st:

                if ns_res == None:
                    ns_res = i

                else:
                    if i['end_floor'] >= ns_res['end_floor']:
                        ns_res = i


            if ns_res != None:

                if bd_user['language_code'] == 'ru':
                    text = (f'*🗻 | Статистика в подземелье*\n'
                            f'🔥 Всего игр: {len(st)}\n\n'
                            f'*👑 | Лучшая игра*\n'
                            f'🧩 Начальный этаж: {ns_res["start_floor"]}\n'
                            f'🗝 Последний этаж: {ns_res["end_floor"]}\n'
                            f'🕰 Время: { Functions.time_end(ns_res["time"]) }\n')

                else:
                    text = (f'*🗻 | Statistics in the dungeon*\n'
                            f'🔥 Total games: { len(st) }\n\n'
                            f'*👑 | Best game*\n'
                            f'🧩 Initial floor: { ns_res["start_floor"] }\n'
                            f'🗝 Last floor: { ns_res["end_floor"] }\n'
                            f'🕰 Time: { Functions.time_end(ns_res["time"], True) }\n')

            else:

                if bd_user['language_code'] == 'ru':
                    text = 'Статистика не собрана.'
                else:
                    text = 'Statistics are not collected.'

            msg = bot.send_message(message.chat.id, text, parse_mode = 'Markdown')

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

                users.update_one( {"userid": bd_user['userid']}, {"$set": {'user_dungeon.quests': bd_user['user_dungeon']['quests'] }} )

            if bd_user['language_code'] == 'ru':
                text = f"🎪 | Меню квестов\nЗавершено: {bd_user['user_dungeon']['quests']['ended']}\nКоличество активных квестов: {len(bd_user['user_dungeon']['quests']['activ_quests'])}"
            else:
                text = f"🎪 | Quest menu\nCompleted: {bd_user['user_dungeon']['quests']['ended']}\nNumber of active quests: {len(bd_user['user_dungeon']['quests']['activ_quests'])}"

            msg = bot.send_message(message.chat.id, text)

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
                            text += f'Достаньте: {", ".join(Functions.sort_items_col(quest["get_items"], "ru") )}'

                            inl_l = {
                            '📌 | Завершить': f"complete_quest {quest['id']}",
                            '🔗 | Удалить': f"delete_quest {quest['id']}"
                            }


                        else:
                            text += f'Достаньте: {", ".join(Functions.sort_items_col(quest["get_items"], "en") )}'

                            inl_l = {
                            '📌 | Finish': f"complete_quest {quest['id']}",
                            '🔗 | Delete': f"delete_quest {quest['id']}"
                            }

                    if quest['type'] == 'kill':

                        if bd_user['language_code'] == 'ru':
                            text += f"Убейте: { mobs_f['mobs'][ quest['mob'] ]['name'][bd_user['language_code']]} {quest['col'][1]} / {quest['col'][0]}"

                            inl_l = {
                            '📌 | Завершить': f"complete_quest {quest['id']}",
                            '🔗 | Удалить': f"delete_quest {quest['id']}"
                            }
                        else:
                            text += f"Kill: { mobs_f['mobs'][ quest['mob'] ]['name'][bd_user['language_code']]} {quest['col'][1]} / {quest['col'][0]}"

                            inl_l = {
                            '📌 | Finish': f"complete_quest {quest['id']}",
                            '🔗 | Delete': f"delete_quest {quest['id']}"
                            }

                    if quest['type'] == 'come':
                        markup_inline = types.InlineKeyboardMarkup(row_width = 1)

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

                                text += f'{item[f"name{lang}"]}: {target_item[1]} / {target_item[0]}\n'

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


                    markup_inline.add( *[ types.InlineKeyboardButton( text = inl, callback_data = f"{inl_l[inl]}") for inl in inl_l.keys() ])

                    if bd_user['language_code'] == 'ru':
                        text += f'\n\n👑 | Награда\nМонеты: '
                    else:
                        text += f'\n\n👑 | Reward\nМонеты: '

                    text += f"{quest['reward']['money']}💰"

                    if quest['reward']['items'] != []:

                        if bd_user['language_code'] == 'ru':
                            text += f"\nПредметы: {', '.join(Functions.sort_items_col(quest['reward']['items'], 'ru') )}"
                        else:
                            text += f"\nItems: {', '.join(Functions.sort_items_col(quest['reward']['items'], 'en') )}"

                    if bd_user['language_code'] == 'ru':
                        text += f"\n\n⏳ Осталось: {Functions.time_end(quest['time'] - int(time.time()), mini = False)}"

                    else:
                        text += f"\n\n⏳ Time left: {Functions.time_end(quest['time']  - int(time.time()), mini = True)}"

                    bot.send_message(message.chat.id, text, reply_markup = markup_inline)
                    time.sleep(0.5)
