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
dungeons = client.bot.dungeons

with open('data/items.json', encoding='utf-8') as f:
    items_f = json.load(f)

with open('data/dino_data.json', encoding='utf-8') as f:
    json_f = json.load(f)

class call_data:
    users = users
    referal_system = referal_system
    market = market
    items_f = items_f
    json_f = json_f
    dungeons = dungeons

    def start(bot, bd_user, call, user):

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

            users.insert_one({'userid': user.id, 'last_m': int(time.time()), 'dead_dinos': 0, 'dinos': {}, 'eggs': [], 'notifications': {}, 'settings': {'notifications': True, 'dino_id': '1', 'last_markup': 1}, 'language_code': lg, 'inventory': [], 'coins': 0, 'lvl': [1, 0], 'activ_items': { '1': {'game': None, 'hunt': None, 'journey': None, 'unv': None} }, 'friends': { 'friends_list': [], 'requests': [] } })

            markup_inline = types.InlineKeyboardMarkup()
            item_1 = types.InlineKeyboardButton( text = '🥚 1', callback_data = 'egg_answer_1')
            item_2 = types.InlineKeyboardButton( text = '🥚 2', callback_data = 'egg_answer_2')
            item_3 = types.InlineKeyboardButton( text = '🥚 3', callback_data = 'egg_answer_3')
            markup_inline.add(item_1, item_2, item_3)

            photo, id_l = photo()
            bot.send_photo(message.chat.id, photo, text, reply_markup = markup_inline)
            users.update_one( {"userid": user.id}, {"$set": {'eggs': id_l}} )

    def checking_the_user_in_the_channel(bot, bd_user, call, user):

        if bot.get_chat_member(-1001673242031, user.id).status != 'left':

            if bd_user['language_code'] == 'ru':
                text = f'📜 | Уважаемый пользователь!\n\n*•* Для получения новостей и важных уведомлений по поводу бота, мы просим вас подписаться на телеграм канал бота!\n\n🟢 | Спасибо за понимание, приятного использования бота!\n\n🍕 | Обсудить или спросить что-то, вы всегда можете в нашей оф. группе > https://t.me/+pq9_21HXXYY4ZGQy'
            else:
                text = f"📜 | Dear user!\n\n*•* To receive news and important notifications about the bot, we ask you to subscribe to the bot's telegram channel!\n\n🟢 | Thank you for understanding, enjoy using the bot!🍕 | To discuss or ask something, you can always in our of. group > https://t.me/+pq9_21HXXYY4ZGQy"

            bot.edit_message_text(text, call.message.chat.id, call.message.message_id, parse_mode = 'Markdown')

    def egg_answer(bot, bd_user, call, user):

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

    def journey(bot, bd_user, call, user):

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

            img.save('journey.png')
            profile = open(f"journey.png", 'rb')

            return profile

        if bd_user['dinos'][ call.data[14:] ]['activ_status'] == 'pass_active':

            profile_i = dino_journey(bd_user, user, call.data[14:])

            if call.data[:13] == '12min_journey':
                jr_time = 120
            else:
                jr_time = int(call.data[:2])

            bd_user['dinos'][ call.data[14:] ]['activ_status'] = 'journey'
            bd_user['dinos'][ call.data[14:] ]['journey_time'] = time.time() + 60 * jr_time
            bd_user['dinos'][ call.data[14:] ]['journey_log'] = []
            users.update_one( {"userid": user.id}, {"$set": {'dinos': bd_user['dinos']}} )

            if bd_user['language_code'] == 'ru':
                text = f'🎈 | Если у динозавра хорошее настроение, он может принести обратно какие то вещи.\n\n🧶 | Во время путешествия, могут произойти разные истории, от них зависит результат.'
                text2 = f'🌳 | Вы отправили динозавра в путешествие на {jr_time} минут.'

            else:
                text = f"🎈 | If the dinosaur is in a good mood, he can bring back some things.\n\n🧶 | During the journey, different stories can happen, the result depends on them."
                text2 = f"🌳 | You sent a dinosaur on a journey for {jr_time} minutes."

            bot.edit_message_text(text2, call.message.chat.id, call.message.message_id)
            bot.send_photo(call.message.chat.id, profile_i, text, reply_markup = functions.markup(bot, "actions", user) )

    def game(bot, bd_user, call, user):

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

        def dino_game(bd_user, user, dino_user_id):

            dino_id = str(bd_user['dinos'][ dino_user_id ]['dino_id'])
            dino = json_f['elements'][dino_id]
            n_img = random.randint(1,2)
            bg_p = Image.open(f"images/game/{n_img}.png")

            dino_image = Image.open("images/"+str(json_f['elements'][dino_id]['image']))
            sz = 412
            dino_image = dino_image.resize((sz, sz), Image.ANTIALIAS)
            dino_image = dino_image.transpose(Image.FLIP_LEFT_RIGHT)

            xy = random.randint(-65, -35)
            x2 = random.randint(20,340)
            img = functions.trans_paste(dino_image, bg_p, 1.0, (xy + x2, xy, sz + xy + x2, sz + xy ))

            img.save('game.png')
            profile = open(f"game.png", 'rb')

            return profile

        profile_i = dino_game(bd_user, user, dino_id)

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
        bot.send_photo(call.message.chat.id, profile_i, text, reply_markup = functions.markup(bot, "games", user), parse_mode = 'html' )

    def dead_answer(bot, bd_user, call, user):

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

    def dead_restart(bot, bd_user, call, user):

        if bd_user != None and len(bd_user['dinos']) == 0 and functions.inv_egg(bd_user) == False and bd_user['lvl'][0] <= 5:
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

    def item_use(bot, bd_user, call, user):

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
                end_ok = True
                list_inv_id = []
                list_inv_id_copy = []
                for i in fr_user['inventory']: list_inv_id.append(i['item_id']), list_inv_id_copy.append(i['item_id'])
                search_items = {}
                list_inv = fr_user['inventory'].copy()

                for _ in range(col):
                    for i in data_item['materials']:
                        if i['item'] in list_inv_id:

                            if i['type'] == 'delete':
                                list_inv_id.remove(i['item'])

                            if i['type'] == 'endurance':

                                itms_ind = []
                                sr_lst_id = list_inv_id_copy.copy()

                                for itm in sr_lst_id:
                                    if itm == i['item']:
                                        itms_ind.append( sr_lst_id.index(itm) )
                                        sr_lst_id[ sr_lst_id.index(itm) ] = None

                                end_ok = False
                                for end_i in itms_ind:
                                    ittm = fr_user['inventory'][end_i]

                                    if ittm['abilities']['endurance'] >= i['act'] * col:
                                        end_ok = True
                                        search_items[ str(list_inv_id_copy[end_i]) ] = fr_user['inventory'][end_i]
                                        break

                        else:
                            ok = False
                            break

                if ok == True and end_ok == True:

                    if bd_user['language_code'] == 'ru':
                        text = f'🍡 | Предмет {data_item["nameru"]} x{col} создан!'
                    else:
                        text = f"🍡 | The item {data_item['nameen']} x{col} is created!"

                    fr_user = users.find_one({"userid": user.id})

                    for _ in range(col):
                        for it_m in data_item['materials']:
                            if it_m['type'] == 'delete':

                                lst_ind = list_inv_id_copy.index(it_m['item'])
                                fr_user['inventory'].remove( list_inv[lst_ind] )

                            if it_m['type'] == 'endurance':
                                lst_i = search_items[ it_m['item'] ]

                                llst_i = fr_user['inventory'].index(lst_i)
                                fr_user['inventory'][ llst_i ]['abilities']['endurance'] -= it_m['act']
                                search_items[ it_m['item'] ]['abilities']['endurance']  -= it_m['act']

                                if fr_user['inventory'][ llst_i ]['abilities']['endurance'] == 0:
                                    fr_user['inventory'].remove( search_items[ it_m['item'] ] )


                    for it_c in data_item['create']:
                        dt = functions.add_item_to_user(fr_user, it_c, col, 'data')

                        for i in dt:
                            fr_user['inventory'].append(i)

                else:

                    if ok == False:

                        if bd_user['language_code'] == 'ru':
                            text = f'❗ | Материалов недостаточно!'
                        else:
                            text = f"❗ | Materials are not enough!"

                    if end_ok == False:

                        if bd_user['language_code'] == 'ru':
                            text = f'❗ | Нет ни одного предмета с требуемой прочностью!'
                        else:
                            text = f"❗ | There is not a single object with the required strength!"

                    use_st = False

            elif data_item['type'] == '+eat':
                d_dino = json_f['elements'][ str(bd_user['dinos'][dino_id]['dino_id']) ]

                if bd_user['dinos'][ dino_id ]['activ_status'] == 'sleep':

                    if bd_user['language_code'] == 'ru':
                        text = 'Во время сна нельзя кормить динозавра.'
                    else:
                        text = 'During sleep, you can not feed the dinosaur.'

                else:

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
                            text = f"🍕 | The dinosaur doesn't like {data_item['nameen']}, it loses {eatr * col}% satiety and {mood * col}% mood!"

                            bd_user['dinos'][ dino_id ]['stats']['eat'] -= eatr * col
                            bd_user['dinos'][ dino_id ]['stats']['mood'] -= moodr * col

                    users.update_one( {"userid": bd_user['userid']}, {"$set": {f'dinos.{dino_id}': bd_user['dinos'][ dino_id ] }} )

            elif data_item['type'] in ['game_ac', "journey_ac", "hunt_ac", "unv_ac"]:
                ac_type = data_item['type'][:-3]

                if bd_user['dinos'][ dino_id ]['activ_status'] != 'pass_active':

                    if bd_user['language_code'] == 'ru':
                        text = '🎍 | Во время игры / сна / путешествия и тд. - нельзя менять аксесcуар!'
                    else:
                        text = '🎍 | While playing / sleeping / traveling, etc. - you can not change the accessory!'

                    use_st = False

                else:

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
                                fr_user['inventory'][ fr_user['inventory'].index(user_item) ]['abilities']['uses'] = user_item['abilities']['uses'] - col

                            else:
                                fr_user['inventory'].remove(user_item)

            else:

                if use_st == True:
                    try:
                        for _ in range(col):
                            fr_user['inventory'].remove(user_item)
                    except:
                        try:
                            fr_user['inventory'].remove(user_item)
                        except Exception as error:
                            print(error, ' error - use item')
                            pass

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

            if col < 1:

                text = f"0 % 0 % 0 % 0 % 0 % 0 % 0 % 0 % 0 % 0 % 0 % 0 :)"

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

                def wrk_p(message):

                    if message.text in ['Да, я хочу это сделать', 'Yes, I want to do it']:
                        n_c_f(), re_item()

                    else:
                        bot.send_message(user.id, f'❌', reply_markup = functions.markup(bot, functions.last_markup(bd_user, alternative = 'profile'), bd_user ))

                markup = types.ReplyKeyboardMarkup(resize_keyboard = True, row_width = 1)

                if bd_user['language_code'] == 'ru':
                    markup.add( *[i for i in ['Да, я хочу это сделать', '❌ Отмена'] ] )
                    msg = bot.send_message(user.id, f'Вы уверены что хотите использовать {data_item["nameru"]} ?', reply_markup = markup)

                else:
                    markup.add( *[i for i in ['Yes, I want to do it', '❌ Cancel'] ] )
                    msg = bot.send_message(user.id, f'Are you sure you want to use {data_item["nameen"]} ?', reply_markup = markup)

                bot.register_next_step_handler(msg, wrk_p)

    def remove_item(bot, bd_user, call, user):

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

    def remove(bot, bd_user, call, user):

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

    def exchange(bot, bd_user, call, user):

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

    def market_buy(bot, bd_user, call, user):

        m_call = call.data.split()

        market_ = market.find_one({"id": 1})
        us_id = m_call[0][11:]
        key_i = m_call[1]

        if str(us_id) in market_['products'].keys():
            ma_d = market_['products'][str(us_id)]['products']

            if str(key_i) in ma_d.keys():
                mmd = market_['products'][str(us_id)]['products'][str(key_i)]
                data_items = items_f['items']

                if data_items[ mmd['item']['item_id'] ]['type'] == '+eat':

                    eat_c = functions.items_counting(bd_user, '+eat')
                    if eat_c >= 300:

                        if bd_user['language_code'] == 'ru':
                            text = f'🌴 | Ваш инвентарь ломится от количества еды! В данный момент у вас {eat_c} предметов которые можно съесть!'
                        else:
                            text = f'🌴 | Your inventory is bursting with the amount of food! At the moment you have {eat_c} items that can be eaten!'

                        bot.send_message(call.message.chat.id, text, reply_markup = functions.markup(bot, 'market', user))
                        return

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

                            mr_user = users.find_one({"userid": int(us_id)})

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
                                users.update_one( {"userid": int(us_id)}, {"$inc": {'coins': mmd['price'] * number }} )

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

    def market_inf(bot, bd_user, call, user):

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

    def iteminfo(bot, bd_user, call, user):

        item = functions.get_dict_item(call.data[9:])
        text, image  = functions.item_info(item, bd_user['language_code'], mark = False)

        if image == None:
            bot.send_message(call.message.chat.id, text, parse_mode = 'Markdown')
        else:
            bot.send_photo(call.message.chat.id, image, text, parse_mode = 'Markdown')

    def send_request(bot, bd_user, call, user):

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

    def ns_craft(bot, bd_user, call, user):

        did = call.data.split()
        data = functions.des_qr(did[1])
        cr_n = did[2]

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

                def wrk_p(message):

                    if message.text in ['Да, я хочу это сделать', 'Yes, I want to do it']:

                        fr_user = users.find_one({"userid": user.id })
                        ok = True
                        list_inv_id.clear()
                        for i in fr_user['inventory']: list_inv_id.append(i['item_id'])
                        list_inv = fr_user['inventory'].copy()

                        for i in data_item["ns_craft"][cr_n]['materials']:

                            if i in list_inv_id:
                                list_inv_id.remove(i)

                            else:
                                ok = False
                                break

                        if ok == True:

                            if bd_user['language_code'] == 'ru':
                                text = f'🍡 | Предмет {", ".join(functions.sort_items_col( data_item["ns_craft"][cr_n]["create"], "ru" ))} создан!'
                            else:
                                text = f'🍡 | The item {", ".join(functions.sort_items_col( data_item["ns_craft"][cr_n]["create"], "en" ))} is created!'

                            list_inv_id.clear()
                            for i in fr_user['inventory']: list_inv_id.append(i['item_id'])

                            for it_m in data_item["ns_craft"][cr_n]['materials']:
                                lst_ind = list_inv_id.index(it_m)
                                list_inv_id[lst_ind] = None
                                fr_user['inventory'].remove( list_inv[lst_ind] )

                            for it_c in data_item["ns_craft"][cr_n]['create']:
                                dt = functions.add_item_to_user(fr_user, it_c, 1, 'data')
                                for i in dt:
                                    fr_user['inventory'].append(i)

                            users.update_one( {"userid": bd_user['userid']}, {"$set": {'inventory': fr_user['inventory'] }} )

                        else:

                            if bd_user['language_code'] == 'ru':
                                text = f'❗ | Материалов недостаточно!'
                            else:
                                text = f"❗ | Materials are not enough!"

                        bot.send_message(user.id, text, reply_markup = functions.markup(bot, functions.last_markup(bd_user, alternative = 'profile'), bd_user ) )

                    else:
                        bot.send_message(user.id, f'❌', reply_markup = functions.markup(bot, functions.last_markup(bd_user, alternative = 'profile'), bd_user ))

                markup = types.ReplyKeyboardMarkup(resize_keyboard = True, row_width = 1)

                if bd_user['language_code'] == 'ru':
                    markup.add( *[i for i in ['Да, я хочу это сделать', '❌ Отмена'] ] )
                    msg = bot.send_message(user.id, f'Вы уверены что хотите создать {", ".join(functions.sort_items_col( data_item["ns_craft"][cr_n]["create"], "ru" ))}?', reply_markup = markup)

                else:
                    markup.add( *[i for i in ['Yes, I want to do it', '❌ Cancel'] ] )
                    msg = bot.send_message(user.id, f'Are you sure you want to create {", ".join(functions.sort_items_col( data_item["ns_craft"][cr_n]["create"], "en" ))}?', reply_markup = markup)

                bot.register_next_step_handler(msg, wrk_p)

    def cancel_progress(bot, bd_user, call, user):

        did = call.data.split()
        dino_id = did[1]

        if bd_user['dinos'][dino_id]['activ_status'] == 'hunting':

            del bd_user['dinos'][ dino_id ]['target']
            del bd_user['dinos'][ dino_id ]['h_type']
            bd_user['dinos'][dino_id]['activ_status'] = 'pass_active'

            functions.notifications_manager(bot, "hunting_end", bd_user, dino_id = dino_id)
            users.update_one( {"userid": bd_user['userid']}, {"$set": {f'dinos.{dino_id}': bd_user['dinos'][dino_id] }} )


    def change_rarity_call_data(bot, bd_user, call, user):

        did = call.data.split()
        dino_id = did[1]
        quality = did[2]

        data_q_r = { 'com': {'money': 4000,  'materials': ['21']  } ,
                     'unc': {'money': 10000, 'materials': ['20'] } ,
                     'rar': {'money': 20000, 'materials': ['22'] } ,
                     'myt': {'money': 40000, 'materials': ['23'] } ,
                     'leg': {'money': 75000, 'materials': ['24'] } ,
                     'ran': {'money': 15000, 'materials': ['3']  } ,
                   }

        def change_rarity(message):

            if message.text in ['Да, я хочу это сделать', 'Yes, I want to do it']:
                bd_user = users.find_one({"userid": user.id })
                bd_user = functions.dino_q(bd_user)

                if dino_id in bd_user['dinos'].keys():
                    if quality != bd_user['dinos'][dino_id]['quality']:
                        if bd_user['coins'] >= data_q_r[quality]['money']:
                            list_inv_id = []
                            for i in bd_user['inventory']: list_inv_id.append(i['item_id'])

                            for i in data_q_r[quality]['materials']:
                                if i not in list_inv_id:

                                    if bd_user['language_code'] == 'ru':
                                        text = f'❗ | Материалов недостаточно!'
                                    else:
                                        text = f"❗ | Materials are not enough!"

                                    bot.send_message(user.id, text, reply_markup = functions.markup(bot, functions.last_markup(bd_user, alternative = 'dino-tavern'), bd_user ))
                                    return

                            qul = quality
                            if quality == 'ran':
                                qul = functions.random_items(['com'], ['unc'], ['rar'], ['myt'], ['leg'])

                            bd_user['coins'] -= data_q_r[quality]['money']
                            bd_user['dinos'][dino_id]['quality'] = qul
                            for i in data_q_r[quality]['materials']:
                                ittm = functions.get_dict_item(i)
                                bd_user['inventory'].remove(ittm)

                            users.update_one( {"userid": bd_user['userid']}, {"$set": {'inventory': bd_user['inventory'] }} )
                            users.update_one( {"userid": bd_user['userid']}, {"$set": {f'dinos.{dino_id}': bd_user['dinos'][dino_id] }} )
                            users.update_one( {"userid": bd_user['userid']}, {"$inc": {'coins': data_q_r[quality]['money'] * -1 }} )

                            if bd_user['language_code'] == 'ru':
                                text = f'🔮 Происходит магия!\n\nВаш динозавр поменял редкость, скорее загляните в профиль!'
                                text2 = '🎗 | Вы были возвращены в прошлое меню!'
                            else:
                                text = f"🔮 Magic happens!\n\nYour dinosaur has changed the rarity, rather take a look at the profile!"
                                text2 = '🎗 | You have been returned to the last menu!'

                            bot.send_message(user.id, text, reply_markup = functions.inline_markup(bot, f'open_dino_profile', user.id, ['Открыть профиль', 'Open a profile'], dino_id))
                            bot.send_message(user.id, text2, reply_markup = functions.markup(bot, functions.last_markup(bd_user, alternative = 'dino-tavern'), bd_user ))

                        else:
                            if bd_user['language_code'] == 'ru':
                                text = f'❗ | Монет недостаточно!'
                            else:
                                text = f"❗ | Coins are not enough!"

                            bot.send_message(user.id, text, reply_markup = functions.markup(bot, functions.last_markup(bd_user, alternative = 'dino-tavern'), bd_user ))

            else:
                bot.send_message(user.id, f'❌', reply_markup = functions.markup(bot, functions.last_markup(bd_user, alternative = 'dino-tavern'), bd_user ))


        markup = types.ReplyKeyboardMarkup(resize_keyboard = True, row_width = 1)
        if bd_user['language_code'] == 'ru':
            markup.add( *[i for i in ['Да, я хочу это сделать', '❌ Отмена'] ] )
            msg = bot.send_message(user.id, f'Вы уверены что хотите изменить редкость своего динозавра?', reply_markup = markup)

        else:
            markup.add( *[i for i in ['Yes, I want to do it', '❌ Cancel'] ] )
            msg = bot.send_message(user.id, f'Are you sure you want to change the rarity of your dinosaur?', reply_markup = markup)

        bot.register_next_step_handler(msg, change_rarity)

    def dungeon_settings(bot, bd_user, call, user):

        dungeonid = int(call.data.split()[1])

        inf = functions.dungeon_message_upd(bot, userid = user.id, dungeonid = dungeonid, type = 'settings')
        print(inf)

    def dungeon_to_lobby(bot, bd_user, call, user):

        dungeonid = int(call.data.split()[1])

        inf = functions.dungeon_message_upd(bot, userid = user.id, dungeonid = dungeonid, image_update = True)
        print(inf)

    def dungeon_settings_lang(bot, bd_user, call, user):

        dungeonid = int(call.data.split()[1])
        dung = dungeons.find_one({"dungeonid": dungeonid})

        if dung != None:
            if dung['settings']['lang'] == 'ru':
                lang = 'en'
            else:
                lang = 'ru'

            dungeons.update_one( {"dungeonid": dungeonid}, {"$set": {f'settings.lang': lang }} )

            inf = functions.dungeon_message_upd(bot, userid = user.id, dungeonid = dungeonid, type = 'settings')
            inf = functions.dungeon_message_upd(bot, userid = user.id, dungeonid = dungeonid, upd_type = 'all', ignore_list = [user.id])
            print(inf)

    def dungeon_leave(bot, bd_user, call, user):

        dungeonid = int(call.data.split()[1])
        dung = dungeons.find_one({"dungeonid": dungeonid})

        if dung != None:

            markup_inline = types.InlineKeyboardMarkup(row_width = 2)

            if bd_user['language_code'] == 'ru':

                inl_l = {'✅ Да': 'dungeon.leave_True',
                         '❌ Нет':  'dungeon.leave_False',
                        }

                text = '🚪 | Вы уверены что хотите покинуть подземелье?'

                markup_inline.add( *[ types.InlineKeyboardButton( text = inl, callback_data = f"{inl_l[inl]} {dungeonid}") for inl in inl_l.keys() ])


            else:

                inl_l = {'✅ Yes': 'dungeon.leave_True',
                         '❌ No':  'dungeon.leave_False',
                        }

                text = '🚪 | Are you sure you want to leave the dungeon?'

                markup_inline.add( *[ types.InlineKeyboardButton( text = inl, callback_data = f"{inl_l[inl]} {dungeonid}") for inl in inl_l.keys() ])

            bot.edit_message_caption(text, user.id, int(dung['users'][str(user.id)]['messageid']), parse_mode = 'Markdown', reply_markup = markup_inline)

    def dungeon_leave_True(bot, bd_user, call, user):

        dungeonid = int(call.data.split()[1])
        dung = dungeons.find_one({"dungeonid": dungeonid})

        dng, inf = functions.dungeon_base_upd(userid = user.id, dungeonid = dungeonid, type = 'remove_user')
        pprint.pprint(dng)
        print(inf)

        bot.delete_message(user.id, dung['users'][str(user.id)]['messageid'])

        inf = functions.dungeon_message_upd(bot, userid = user.id, dungeonid = dungeonid, upd_type = 'all')
        print(inf)

    def dungeon_leave_False(bot, bd_user, call, user):

        dungeonid = int(call.data.split()[1])
        dung = dungeons.find_one({"dungeonid": dungeonid})

        inf = functions.dungeon_message_upd(bot, userid = user.id, dungeonid = dungeonid)
        print(inf)

    def dungeon_remove(bot, bd_user, call, user):

        dungeonid = int(call.data.split()[1])
        dung = dungeons.find_one({"dungeonid": dungeonid})

        if dung != None:

            markup_inline = types.InlineKeyboardMarkup(row_width = 2)

            if bd_user['language_code'] == 'ru':

                inl_l = {'✅ Да': 'dungeon.remove_True',
                         '❌ Нет':  'dungeon.remove_False',
                        }

                text = '🚪 | Вы уверены что хотите удалить подземелье?'

                markup_inline.add( *[ types.InlineKeyboardButton( text = inl, callback_data = f"{inl_l[inl]} {dungeonid}") for inl in inl_l.keys() ])

            else:

                inl_l = {'✅ Yes': 'dungeon.remove_True',
                         '❌ No':  'dungeon.remove_False',
                        }

                text = '🚪 | Are you sure you want to delete the dungeon?'

                markup_inline.add( *[ types.InlineKeyboardButton( text = inl, callback_data = f"{inl_l[inl]} {dungeonid}") for inl in inl_l.keys() ])

            bot.edit_message_caption(text, user.id, int(dung['users'][str(user.id)]['messageid']), parse_mode = 'Markdown', reply_markup = markup_inline)

    def dungeon_remove_True(bot, bd_user, call, user):

        dungeonid = int(call.data.split()[1])
        dung = dungeons.find_one({"dungeonid": dungeonid})

        inf = functions.dungeon_message_upd(bot, dungeonid = dungeonid, type = 'delete_dungeon')
        print(inf)

        dng, inf = functions.dungeon_base_upd(dungeonid = dungeonid, type = 'delete_dungeon')
        pprint.pprint(dng)
        print(inf)

    def dungeon_remove_False(bot, bd_user, call, user):

        dungeonid = int(call.data.split()[1])
        dung = dungeons.find_one({"dungeonid": dungeonid})

        inf = functions.dungeon_message_upd(bot, userid = user.id, dungeonid = dungeonid, type = 'settings')
        print(inf)

    def dungeon_add_dino_menu(bot, bd_user, call, user):

        dungeonid = int(call.data.split()[1])
        dung = dungeons.find_one({"dungeonid": dungeonid})

        inf = functions.dungeon_message_upd(bot, userid = user.id, dungeonid = dungeonid, type = 'add_dino')
        print(inf)

    def dungeon_remove_dino_menu(bot, bd_user, call, user):

        dungeonid = int(call.data.split()[1])
        dung = dungeons.find_one({"dungeonid": dungeonid})

        inf = functions.dungeon_message_upd(bot, userid = user.id, dungeonid = dungeonid, type = 'remove_dino')
        print(inf)

    def dungeon_add_dino(bot, bd_user, call, user):

        dungeonid = int(call.data.split()[1])
        dinoid = call.data.split()[2]
        dung = dungeons.find_one({"dungeonid": dungeonid})

        dng, inf = functions.dungeon_base_upd(userid = user.id, dungeonid = dungeonid, type = 'add_dino', dinosid = [dinoid])
        pprint.pprint(dng)
        print(inf)

        inf2 = functions.dungeon_message_upd(bot, userid = user.id, dungeonid = dungeonid, type = inf)
        print(inf2)

        if inf == 'add_dino':
            inf3 = functions.dungeon_message_upd(bot, userid = user.id, dungeonid = dungeonid, upd_type = 'all', ignore_list = [user.id])
            print(inf3)

    def dungeon_remove_dino(bot, bd_user, call, user):

        dungeonid = int(call.data.split()[1])
        dinoid = call.data.split()[2]
        dung = dungeons.find_one({"dungeonid": dungeonid})

        dng, inf = functions.dungeon_base_upd(userid = user.id, dungeonid = dungeonid, type = 'remove_dino', dinosid = [dinoid])
        pprint.pprint(dng)
        print(inf)

        inf = functions.dungeon_message_upd(bot, userid = user.id, dungeonid = dungeonid, type = 'remove_dino')
        print(inf)
        inf = functions.dungeon_message_upd(bot, userid = user.id, dungeonid = dungeonid, upd_type = 'all', ignore_list = [user.id])
        print(inf)

    def dungeon_ready(bot, bd_user, call, user):

        dungeonid = int(call.data.split()[1])
        dung = dungeons.find_one({"dungeonid": dungeonid})

        if dung != None:

            pprint.pprint(dung)

            if user.id not in dung['stage_data']['preparation']['ready']:

                if dung['users'][str(user.id)]['dinos'] != {}:
                    dung['stage_data']['preparation']['ready'].append(user.id)

            else:
                dung['stage_data']['preparation']['ready'].remove(user.id)

            dungeons.update_one( {"dungeonid": dungeonid}, {"$set": {f'stage_data': dung['stage_data'] }} )
            inf = functions.dungeon_message_upd(bot, userid = user.id, dungeonid = dungeonid, upd_type = 'all')
            print(inf)

    def dungeon_invite(bot, bd_user, call, user):

        dungeonid = int(call.data.split()[1])

        inf = functions.dungeon_message_upd(bot, userid = user.id, dungeonid = dungeonid, type = 'invite_room')
        print(inf)
