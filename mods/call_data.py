import json
import random
import sys
import time

from fuzzywuzzy import fuzz
from PIL import Image
from telebot import types

from mods.classes import Dungeon, Functions

sys.path.append("..")
import config

client = config.CLUSTER_CLIENT
users, management, dungeons = client.bot.users, client.bot.management, client.bot.dungeons

with open('json/items.json', encoding='utf-8') as f: items_f = json.load(f)

with open('json/dino_data.json', encoding='utf-8') as f: json_f = json.load(f)

with open('json/settings.json', encoding='utf-8') as f: settings_f = json.load(f)

class CallData:

    def egg_answer(bot, bd_user, call, user):

        if 'eggs' in list(bd_user.keys()):
            egg_n = call.data.split()[1]

            bd_user['dinos'][ Functions.user_dino_pn(bd_user) ] = {'status': 'incubation', 'incubation_time': time.time() + 10 * 60, 'egg_id': egg_n}

            users.update_one( {"userid": user.id}, {"$unset": {'eggs': None}} )
            users.update_one( {"userid": user.id}, {"$set": {'dinos': bd_user['dinos']}} )

            if bd_user['language_code'] == 'ru':
                text = f'🥚 | Выберите яйцо с динозавром!\n🦖 | Вы выбрали яйцо 🥚{egg_n}!'

                text2 = f'🧸 | Поздравляем, у вас появился свой первый динозавр!\n\n🎇 | В данный момент яйцо инкубируется, а через 10 минут из него вылупится динозаврик!\n\n🎮 | Чтобы посмотреть актуальную информацию о яйце, нажмите кнопку `🦖 Динозавр`!\n\n🧨 | Пока ждёте, изучите интерфейс, прочитайте FAQ, настройте бота под себя!'
            else:
                text = f'🥚 | Choose a dinosaur egg!\n🦖 | You have chosen an egg 🥚{egg_n}!'

                text2 = f'🧸 | Congratulations, you have your first dinosaur!\n\n🎇 | At the moment, the egg is incubating, and in 10 minutes a dinosaur will hatch out of it!\n\n🎮 | To view up-to-date information about the egg, click the `🦖 Dinosaur` button!\n\n🧨 | While you are waiting, study the interface, read the FAQ, configure the bot for yourself!'

            bot.edit_message_caption(text, call.message.chat.id, call.message.message_id)
            bot.send_message(call.message.chat.id, text2, parse_mode = 'Markdown', reply_markup = Functions.markup(bot, 1, user))

    def journey(bot, bd_user, call, user):

        def dino_journey(bd_user, user, dino_user_id):

            dino_id = str(bd_user['dinos'][ dino_user_id ]['dino_id'])
            n_img = random.randint(1,5)
            bg_p = Image.open(f"images/journey/{n_img}.png")

            dino_image = Image.open("images/"+str(json_f['elements'][dino_id]['image']))
            sz = 412
            dino_image = dino_image.resize((sz, sz), Image.ANTIALIAS)
            dino_image = dino_image.transpose(Image.FLIP_LEFT_RIGHT)

            xy = -35
            x2 = random.randint(80,120)
            img = Functions.trans_paste(dino_image, bg_p, 1.0, (xy + x2, xy, sz + xy + x2, sz + xy ))

            img.save(f'{config.TEMP_DIRECTION}/journey.png')
            profile = open(f"{config.TEMP_DIRECTION}/journey.png", 'rb')

            return profile

        if bd_user['dinos'][ call.data[14:] ]['activ_status'] == 'pass_active':

            profile_i = dino_journey(bd_user, user, call.data[14:])

            if call.data[:13] == '12min_journey':
                jr_time = 120

            elif call.data[:13] == '24min_journey':
                jr_time = 240
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
            bot.send_photo(call.message.chat.id, profile_i, text, reply_markup = Functions.markup(bot, "actions", user) )

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
            img = Functions.trans_paste(dino_image, bg_p, 1.0, (xy + x2, xy, sz + xy + x2, sz + xy ))

            img.save(f'{config.TEMP_DIRECTION}/game.png')
            profile = open(f"{config.TEMP_DIRECTION}/game.png", 'rb')

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


        bd_user['dinos'][ dino_id ]['game_time'] = int(time.time()) + time_m
        bd_user['dinos'][ dino_id ]['game_start'] = int(time.time())
        users.update_one( {"userid": user.id}, {"$set": {'dinos': bd_user['dinos']}} )

        if bd_user['language_code'] == 'ru':

            text = f'🎮 | Чередуйте игры для избежания штрафа!'

        else:

            text = f"🎮 | Alternate games to avoid a penalty!"

        bot.edit_message_text(text2, call.message.chat.id, call.message.message_id)
        bot.send_photo(call.message.chat.id, profile_i, text, reply_markup = Functions.markup(bot, "games", user), parse_mode = 'html' )

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

        if bd_user != None and len(bd_user['dinos']) == 0 and Functions.inv_egg(bd_user) == False and bd_user['lvl'][0] <= 5:
            egg_n = str(random.choice(list(json_f['data']['egg'])))

            bd_user['dinos'][ Functions.user_dino_pn(bd_user) ] = {'status': 'incubation', 'incubation_time': time.time() + 30 * 60, 'egg_id': egg_n}
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

            bot.send_message(user.id, text, parse_mode = 'Markdown', reply_markup = Functions.markup(bot, 1, user))

    def item_use(bot, bd_user, call, user):

        data = Functions.des_qr(str(call.data[5:]), True )
        it_id = str(data['item_id'])
        check_n = 0
        dino_id = 1
        col = 1

        def cannot_use():

            if bd_user['language_code'] == 'ru':
                text = f'❌ | Этот предмет не может быть использован самостоятельно!'
            else:
                text = f"❌ | This item cannot be used on its own!"

            bot.send_message(user.id, text, parse_mode = 'Markdown', reply_markup = Functions.markup(bot, Functions.last_markup(bd_user, alternative = 'profile'), bd_user ))

        def n_c_f():
            nonlocal check_n
            check_n += 1

        def re_item():
            nonlocal check_n, data_item

            if check_n == 1:

                if data_item['type'] == '+unv':
                    ans_dino()

                elif data_item['type'] == 'recipe':
                    ans_col()

                elif data_item['type'] == '+eat':
                    ans_dino()

                elif data_item['type'] in ['game_ac', "journey_ac", "hunt_ac", "unv_ac"]:
                    ans_dino()

                elif data_item['type'] == 'egg':
                    use_item()

                elif data_item['type'] in ['weapon', "armor"]:
                    ans_dino()

                elif data_item['type'] == "backpack":
                    use_item()

                elif data_item['type'] in ['material', 'none']:
                    cannot_use()

                elif data_item['type'] == "ammunition":
                    use_item()

                elif data_item['type'] in ['freezing', 'defrosting']:
                    ans_dino()

                else:
                    print(f'Первый этап не найден {data_item["type"]}')
                    cannot_use()

            elif check_n == 2:

                if data_item['type'] == '+unv':
                    ans_col()

                elif data_item['type'] == 'recipe':
                    use_item()

                elif data_item['type'] == '+eat':
                    ans_col()

                elif data_item['type'] in ['game_ac', "journey_ac", "hunt_ac", "unv_ac"]:
                    use_item()

                elif data_item['type'] in ['weapon', "armor"]:
                    use_item()

                elif data_item['type'] in ['freezing', 'defrosting']:
                    use_item()

                else:
                    print(f'Второй этап не найден {data_item["type"]}')

            elif check_n == 3:

                if data_item['type'] == '+unv':
                    use_item()

                elif data_item['type'] == '+eat':
                    use_item()

                else:
                    print(f'Третий этап не найден {data_item["type"]}')

        def ans_dino():
            global dino_id

            def dino_reg(message, dino_dict):
                global dino_id

                if message.text in dino_dict.keys():
                    dino_id = dino_dict[message.text][1]

                    dino_st = bd_user['dinos'][str(dino_id)]['activ_status']

                    if dino_st != 'dungeon':

                        n_c_f(), re_item()

                    else:
                        bot.send_message(user.id, f'❌', reply_markup = Functions.markup(bot, Functions.last_markup(bd_user, alternative = 'profile'), bd_user ))

                else:
                    bot.send_message(user.id, f'❌', reply_markup = Functions.markup(bot, Functions.last_markup(bd_user, alternative = 'profile'), bd_user ))

            n_dp, dp_a = Functions.dino_pre_answer(bot, call, 'noall')

            if n_dp == 1: #нет дино

                if Functions.inv_egg(bd_user) == True and data_item['type'] == 'egg':
                    n_c_f(), re_item()

                else:
                    bot.send_message(user.id, f'❌', reply_markup = Functions.markup(bot, Functions.last_markup(bd_user, alternative = 1), bd_user ))

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
            send_status = True
            text = ''

            if data_item['type'] == 'freezing':

                dino = fr_user['dinos'][dino_id]

                if dino['status'] == 'dino':
                    if dino['activ_status'] != 'freezing':

                        dino['activ_status'] = 'freezing'

                        if bd_user['language_code'] == 'ru':
                            text = f'❄ | Метаболизм динозавра был остановлен!'
                        else:
                            text = f"❄ | The dinosaur's metabolism has been stopped!"

                        users.update_one( {"userid": user.id}, {"$set": {f'dinos.{dino_id}': dino }} )

                    else:
                        use_st = False
                        text = f'❌'

                else:
                    use_st = False
                    text = f'❌'

            elif data_item['type'] == 'defrosting':

                dino = fr_user['dinos'][dino_id]

                if dino['status'] == 'dino':
                    if dino['activ_status'] == 'freezing':

                        dino['activ_status'] = 'pass_active'

                        if bd_user['language_code'] == 'ru':
                            text = f'🔥 | Метаболизм динозавра был восстановлен!'
                        else:
                            text = f"🔥 | The dinosaur's metabolism has been restored!"

                        users.update_one( {"userid": user.id}, {"$set": {f'dinos.{dino_id}': dino }} )

                    else:
                        use_st = False
                        text = f'❌'

                else:
                    use_st = False
                    text = f'❌'

            elif data_item['type'] == 'recipe':
                ok = True
                end_ok = True
                list_inv_id = []
                list_inv_id_copy = []
                search_items = {}

                for i in fr_user['inventory']: list_inv_id.append(i['item_id']), list_inv_id_copy.append(i['item_id'])
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

                    iname = Functions.item_name(user_item['item_id'], fr_user['language_code'])

                    if bd_user['language_code'] == 'ru':
                        text = f'🍡 | Предмет {iname} x{col} создан!'
                    else:
                        text = f"🍡 | The item {iname} x{col} is created!"

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
                        dp_col = 1

                        if it_c['type'] == 'create':

                            if 'col' in it_c.keys():
                                dp_col = it_c['col']

                            if 'abilities' in it_c.keys():
                                preabil = it_c['abilities']
                            else:
                                preabil = None

                            dt = Functions.add_item_to_user(fr_user, it_c['item'], col * dp_col, 'data', preabil)

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
                iname = Functions.item_name(user_item['item_id'], bd_user['language_code'])

                if bd_user['dinos'][ dino_id ]['activ_status'] == 'sleep':

                    if bd_user['language_code'] == 'ru':
                        text = 'Во время сна нельзя кормить динозавра.'
                    else:
                        text = 'During sleep, you can not feed the dinosaur.'
                        use_st = False

                else:

                    if bd_user['language_code'] == 'ru':
                        if data_item['class'] == 'ALL':

                            bd_user['dinos'][ dino_id ]['stats']['eat'] += data_item['act'] * col

                            if bd_user['dinos'][ dino_id ]['stats']['eat'] > 100:
                                bd_user['dinos'][ dino_id ]['stats']['eat'] = 100

                            text = f"🍕 | Динозавр с удовольствием съел {iname}!\nДинозавр сыт на {bd_user['dinos'][ dino_id ]['stats']['eat']}%"


                        elif data_item['class'] == d_dino['class']:
                            bd_user['dinos'][ dino_id ]['stats']['eat'] += data_item['act'] * col

                            if bd_user['dinos'][ dino_id ]['stats']['eat'] > 100:
                                bd_user['dinos'][ dino_id ]['stats']['eat'] = 100

                            text = f"🍕 | Динозавр с удовольствием съел {iname}!\nДинозавр сыт на {bd_user['dinos'][ dino_id ]['stats']['eat']}%"


                        else:
                            eatr = random.randint( 0, int(data_item['act'] / 2) )
                            moodr = random.randint( 1, 10 )
                            text = f"🍕 | Динозавру не по вкусу {iname}, он теряет {eatr}% сытости и {moodr}% настроения!"

                            bd_user['dinos'][ dino_id ]['stats']['eat'] -= eatr
                            bd_user['dinos'][ dino_id ]['stats']['mood'] -= moodr

                    else:
                        if data_item['class'] == 'ALL':

                            bd_user['dinos'][ dino_id ]['stats']['eat'] += data_item['act'] * col

                            if bd_user['dinos'][ dino_id ]['stats']['eat'] > 100:
                                bd_user['dinos'][ dino_id ]['stats']['eat'] = 100

                            text = f"🍕 | The dinosaur ate it with pleasure {iname}!\nThe dinosaur is fed up on {bd_user['dinos'][ dino_id ]['stats']['eat']}%"

                        elif data_item['class'] == d_dino['class']:

                            bd_user['dinos'][ dino_id ]['stats']['eat'] += data_item['act'] * col

                            if bd_user['dinos'][ dino_id ]['stats']['eat'] > 100:
                                bd_user['dinos'][ dino_id ]['stats']['eat'] = 100

                            text = f"🍕 | The dinosaur ate it with pleasure {iname}!\nThe dinosaur is fed up on {bd_user['dinos'][ dino_id ]['stats']['eat']}%"

                        else:
                            eatr = random.randint( 0, int(data_item['act'] / 2) )
                            moodr = random.randint( 1, 10 )
                            text = f"🍕 | The dinosaur doesn't like {iname}, it loses {eatr * col}% satiety and {moodr * col}% mood!"

                            bd_user['dinos'][ dino_id ]['stats']['eat'] -= eatr * col
                            bd_user['dinos'][ dino_id ]['stats']['mood'] -= moodr * col

                    users.update_one( {"userid": bd_user['userid']}, {"$set": {f'dinos.{dino_id}': bd_user['dinos'][ dino_id ] }} )

            elif data_item['type'] in ['weapon', 'armor', 'backpack']:
                type_eq = data_item['type']
                item = None

                if type_eq in ['weapon', 'armor']:
                    item = bd_user['dinos'][dino_id]['dungeon']['equipment'][type_eq]

                    if item != None:

                        fr_user['inventory'].append(item)
                        bd_user['dinos'][dino_id]['dungeon']['equipment'][type_eq] = None

                    bd_user['dinos'][dino_id]['dungeon']['equipment'][type_eq] = user_item

                    users.update_one( {"userid": bd_user['userid']}, {"$set": {'dinos': bd_user['dinos'] }} )

                if type_eq in ['backpack']:
                    item = bd_user['user_dungeon']['equipment'][type_eq]

                    if item != None:

                        fr_user['inventory'].append(item)
                        bd_user['user_dungeon']['equipment'][type_eq] = None

                    bd_user['user_dungeon']['equipment'][type_eq] = user_item

                    users.update_one( {"userid": bd_user['userid']}, {"$set": {'user_dungeon': bd_user['user_dungeon'] }} )

                if bd_user['language_code'] == 'ru':
                    text = "🎴 | Активный предмет установлен!"
                else:
                    text = "🎴 | The active item is installed!"

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
                        fr_user['inventory'].append(bd_user['activ_items'][ dino_id ][ac_type])

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
                        use_st = False

                        if user.language_code == 'ru':
                            text2 = '🥚 | Выберите яйцо с динозавром!'
                            text = '🎨 | Профиль открыт!'
                        else:
                            text2 = '🥚 | Choose a dinosaur egg!'
                            text = '🎨 | Profile is open!'

                        if 'eggs' in bd_user.keys():
                            id_l = bd_user['eggs']
                        else:
                            id_l = None

                        photo, markup_inline, id_l = Functions.create_egg_image(id_l, 'egg_use')
                        bot.send_photo(call.message.chat.id, photo, text2, reply_markup = markup_inline)

                        users.update_one( {"userid": user.id}, {"$set": {'eggs': id_l}} )
                        users.update_one( {"userid": user.id}, {"$set": {'egg_item': user_item }} )

                    else:
                        if bd_user['language_code'] == 'ru':
                            text = f"🔔 | Вам доступна только {int(bd_user['lvl'][0] / 20)} динозавров!"
                        else:
                            text = f"🔔 | Only {int(bd_user['lvl'][0] / 20)} dinosaurs are available to you!"

                        use_st = False

            elif data_item['type'] == "ammunition":

                list_inv_id = []
                for i in fr_user['inventory']: list_inv_id.append(i['item_id'])
                standart_i_id = user_item['item_id']
                standart_index = fr_user['inventory'].index(user_item)
                csh = list_inv_id.count(standart_i_id)
                list_inv_id[standart_index] = 0
                use_st = 'update_only'

                if csh > 0:

                    two_item_ind = list_inv_id.index(standart_i_id)
                    two_item = fr_user['inventory'][two_item_ind]

                    if user_item['abilities']['stack'] + two_item['abilities']['stack'] > data_item["max_stack"]:

                        if bd_user['language_code'] == 'ru':
                            text = f'❗ | Этот набор не может быть соединён ни с одним предметом в инвентаре!'
                        else:
                            text = f"❗ | This set cannot be connected to any item in the inventory!"

                        use_st = False

                    else:

                        preabil = {'stack': user_item['abilities']['stack'] + two_item['abilities']['stack'] }
                        fr_user['inventory'].append( Functions.get_dict_item(standart_i_id, preabil) )

                        fr_user['inventory'].remove(two_item)
                        fr_user['inventory'].remove(user_item)

                        if bd_user['language_code'] == 'ru':
                            text = f'🏹 | Предметы были соединены!'
                        else:
                            text = f"🏹 | The items were connected!"

                else:

                    if bd_user['language_code'] == 'ru':
                        text = f'❗ | В инвентаре нет предметов для соединения!'
                    else:
                        text = f"❗ | There are no items in the inventory to connect!"

                    use_st = False

            else:

                if bd_user['language_code'] == 'ru':
                    text = f'❗ | Данный предмет пока что недоступен для использования!'
                else:
                    text = f"❗ | This item is not yet available for use!"

                use_st = False

            if list(set([ '+mood', '-mood', '-eat', '+eat', '+energy', '-energy', '+hp', '-hp']) & set(data_item.keys())) != [] and use_st == True:

                text += '\n\n'

                if '+mood' in data_item.keys():
                    users.update_one( {"userid": user.id}, {"$inc": {f'dinos.{dino_id}.stats.mood': data_item['+mood'] * col }} )

                    if bd_user['language_code'] == 'ru':
                        text += f'😀 | Динозавр получил +{data_item["+mood"] * col}% к настроению!\n'
                    else:
                        text += f'😀 | Dinosaur got +{data_item["+mood"] * col}% to mood!\n'

                if '-mood' in data_item.keys():
                    users.update_one( {"userid": user.id}, {"$inc": {f'dinos.{dino_id}.stats.mood': (data_item['-mood'] * -1) * col }} )

                    if bd_user['language_code'] == 'ru':
                        text += f'😥 | Динозавр получил -{data_item["-mood"] * col}% к настроению!\n'
                    else:
                        text += f'😥 | Dinosaur got -{data_item["-mood"] * col}% to mood!\n'

                if '+eat' in data_item.keys():
                    users.update_one( {"userid": user.id}, {"$inc": {f'dinos.{dino_id}.stats.eat': (data_item['+eat']) * col }} )

                    if bd_user['language_code'] == 'ru':
                        text += f'🥪 | Динозавр восстановил {data_item["+eat"] * col}% сытости!\n'
                    else:
                        text += f'🥪 | The dinosaur has restored {data_item["+eat"] * col}% satiety!\n'

                if '-eat' in data_item.keys():
                    users.update_one( {"userid": user.id}, {"$inc": {f'dinos.{dino_id}.stats.eat': (data_item['-eat'] * -1) * col }} )

                    if bd_user['language_code'] == 'ru':
                        text += f'🥪 | Динозавр потерял {data_item["-eat"] * col}% сытости!\n'
                    else:
                        text += f'🥪 | Dinosaur lost {data_item["-eat"] * col}% satiety!\n'

                if '+energy' in data_item.keys():
                    users.update_one( {"userid": user.id}, {"$inc": {f'dinos.{dino_id}.stats.unv': (data_item['+energy']) * col }} )

                    if bd_user['language_code'] == 'ru':
                        text += f'⚡ | Вы восстановили {data_item["+energy"] * col}% энергии динозавра!\n'
                    else:
                        text += f"⚡ | You have recovered {data_item['+energy'] * col}% of the dinosaur's energy!\n"

                if '-energy' in data_item.keys():
                    users.update_one( {"userid": user.id}, {"$inc": {f'dinos.{dino_id}.stats.unv': (data_item['-energy'] * -1) * col }} )

                    if bd_user['language_code'] == 'ru':
                        text += f'⚡ | Динозавр потерял {data_item["-energy"] * col}% энергии!\n'
                    else:
                        text += f'⚡ | Dinosaur lost {data_item["-energy"] * col}% energy!\n'

                if '+hp' in data_item.keys():
                    users.update_one( {"userid": user.id}, {"$inc": {f'dinos.{dino_id}.stats.heal': (data_item['+hp']) * col }} )

                    if bd_user['language_code'] == 'ru':
                        text += f'❤ | Вы восстановили {data_item["+hp"] * col}% здоровья динозавра!'
                    else:
                        text += f"❤ | You have restored {data_item['+hp'] * col}% of the dinosaur's health!"

                if '-hp' in data_item.keys():
                    users.update_one( {"userid": user.id}, {"$inc": {f'dinos.{dino_id}.stats.heal': (data_item['-hp']) * col }} )

                    if bd_user['language_code'] == 'ru':
                        text += f'❤ | Ваш динозавр потерял {data_item["-hp"] * col}% здоровья!\n'
                    else:
                        text += f'❤ | Your dinosaur lost {data_item["-hp"] * col}% health!\n'

            if 'abilities' in user_item.keys() and 'uses' in user_item['abilities'].keys():
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

            if use_st == True or use_st == 'update_only':
                users.update_one( {"userid": user.id}, {"$set": {'inventory': fr_user['inventory'] }} )
            
            if send_status == True:
                bot.send_message(user.id, text, parse_mode = 'Markdown', reply_markup = Functions.markup(bot, Functions.last_markup(bd_user, alternative = 'profile'), bd_user ))

        def ent_col(message, col_l, mx_col):
            global col

            if message.text in ['↩️ Назад', '↩️ Back']:

                if bd_user['language_code'] == 'ru':
                    text = f"🎈 | Отмена использования!"
                else:
                    text = f"🎈 | Cancellation of use!"

                bot.send_message(message.chat.id, text, reply_markup = Functions.markup(bot, Functions.last_markup(bd_user, alternative = 'profile'), bd_user ))
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

                    bot.send_message(message.chat.id, text, reply_markup = Functions.markup(bot, Functions.last_markup(bd_user, alternative = 'profile'), bd_user ))
                    return

            if col < 1:

                text = f"0 % 0 % 0 % 0 % 0 % 0 :)"

                bot.send_message(message.chat.id, text, reply_markup = Functions.markup(bot, Functions.last_markup(bd_user, alternative = 'profile'), bd_user ))
                return

            if col > mx_col:

                if bd_user['language_code'] == 'ru':
                    text = f"У вас нет столько предметов в инвентаре!"
                else:
                    text = f"You don't have that many items in your inventory!"

                bot.send_message(message.chat.id, text, reply_markup = Functions.markup(bot, Functions.last_markup(bd_user, alternative = 'profile'), bd_user ))
                return

            else:
                n_c_f(), re_item()

        def ans_col():

            col = 1
            mx_col = 0

            if 'abilities' in user_item.keys() and 'uses' in user_item['abilities'].keys():
                mx_col = user_item['abilities']['uses']

            else:
                mx_col = bd_user['inventory'].count(user_item)

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

        data_item = items_f['items'][it_id]
        user_item = None
        iname = Functions.item_name(str(it_id), bd_user['language_code'])

        if data in bd_user['inventory']:
            user_item = data

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
                    bot.send_message(user.id, f'❌', reply_markup = Functions.markup(bot, Functions.last_markup(bd_user, alternative = 'profile'), bd_user ))

            markup = types.ReplyKeyboardMarkup(resize_keyboard = True, row_width = 1)

            if bd_user['language_code'] == 'ru':
                markup.add( *[i for i in ['Да, я хочу это сделать', '❌ Отмена'] ] )
                msg = bot.send_message(user.id, f'Вы уверены что хотите использовать {iname} ?', reply_markup = markup)

            else:
                markup.add( *[i for i in ['Yes, I want to do it', '❌ Cancel'] ] )
                msg = bot.send_message(user.id, f'Are you sure you want to use {iname} ?', reply_markup = markup)

            bot.register_next_step_handler(msg, wrk_p)

    def remove_item(bot, bd_user, call, user):

        data = Functions.des_qr(str(call.data[12:]), True)
        it_id = str(data['item_id'])
        user_item = None

        if data in bd_user['inventory']:
            user_item = data

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
            markup_inline.add( types.InlineKeyboardButton( text = in_text[0], callback_data = f"remove_{Functions.qr_item_code(user_item)}"),  types.InlineKeyboardButton( text = in_text[1], callback_data = f"cancel_remove") )

            bot.send_message(user.id, text, reply_markup = markup_inline)

    def remove(bot, bd_user, call, user):

        data = Functions.des_qr(str(call.data[7:]), True)
        user_item = None

        if data in bd_user['inventory']:
            user_item = data

        if user_item == None:

            if bd_user['language_code'] == 'ru':
                text = f'❌ | Предмет не найден в инвентаре!'
            else:
                text = f"❌ | Item not found in inventory!"

            bot.send_message(user.id, text, parse_mode = 'Markdown')

        if user_item != None:
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

                if col > mx_col:

                    if bd_user['language_code'] == 'ru':
                        text = f"У вас нет столько предметов в инвентаре!"
                    else:
                        text = f"You don't have that many items in your inventory!"

                    bot.send_message(message.chat.id, text, reply_markup = Functions.markup(bot, 'actions', user))
                    return

                for _ in range(col):
                    bd_user['inventory'].remove(user_item)

                users.update_one( {"userid": user.id}, {"$set": {f'inventory': bd_user['inventory'] }} )

                if bd_user['language_code'] == 'ru':
                    text = '🗑 | Предмет удалён.'
                else:
                    text = '🗑 | The item has been deleted.'

                bot.send_message(message.chat.id, text, reply_markup = Functions.markup(bot, 'profile', user))

            msg = bot.send_message(user.id, text_col, reply_markup = rmk)
            bot.register_next_step_handler(msg, tr_complete, bd_user, user_item, mx_col, col_l)

    def exchange(bot, bd_user, call, user):

        data = Functions.des_qr(str(call.data[9:]), True)
        it_id = str(data['item_id'])
        user_item = None

        if data in bd_user['inventory']:
            user_item = data

        if user_item == None:

            if bd_user['language_code'] == 'ru':
                text = f'❌ | Предмет не найден в инвентаре!'
            else:
                text = f"❌ | Item not found in inventory!"

            bot.send_message(user.id, text, parse_mode = 'Markdown')

        if user_item != None:

            Functions.exchange(bot, call.message, user_item, bd_user, user)

    def market_buy(bot, bd_user, call, user):

        m_call = call.data.split()

        market_ = management.find_one({"_id": 'products'})
        us_id = m_call[0][11:]
        key_i = m_call[1]

        if str(us_id) in market_['products'].keys():
            ma_d = market_['products'][str(us_id)]['products']

            if str(key_i) in ma_d.keys():
                mmd = market_['products'][str(us_id)]['products'][str(key_i)]
                data_items = items_f['items']

                if data_items[ mmd['item']['item_id'] ]['type'] == '+eat':

                    eat_c = Functions.items_counting(bd_user, '+eat')
                    if eat_c >= settings_f['max_eat_items']:

                        if bd_user['language_code'] == 'ru':
                            text = f'🌴 | Ваш инвентарь ломится от количества еды! В данный момент у вас {eat_c} предметов которые можно съесть!'
                        else:
                            text = f'🌴 | Your inventory is bursting with the amount of food! At the moment you have {eat_c} items that can be eaten!'

                        bot.send_message(call.message.chat.id, text, reply_markup = Functions.markup(bot, 'market', user))
                        return

                if mmd['price'] <= bd_user['coins']:
                    iname = Functions.item_name(str(mmd['item']['item_id']), bd_user['language_code'])

                    def reg0(message, mmd, us_id, key_i):

                        def reg(message, mmd, us_id, key_i):

                            try:
                                number = int(message.text)
                            except:

                                if bd_user['language_code'] == 'ru':
                                    text = "🛒 | Возвращение в меню рынка!"
                                else:
                                    text = "🛒 | Return to the market menu!"

                                bot.send_message(message.chat.id, text, reply_markup = Functions.markup(bot, 'market', user))
                                return

                            if number <= 0 or number > mmd['col'][1] - mmd['col'][0]:

                                if bd_user['language_code'] == 'ru':
                                    text = "🛒 | На рынке нет такого количества предмета!"
                                else:
                                    text = "🛒 | There is no such amount of item on the market!"

                                bot.send_message(message.chat.id, text, reply_markup = Functions.markup(bot, 'market', user))
                                return

                            mr_user = users.find_one({"userid": int(us_id)})

                            if mmd['price'] * number > bd_user['coins']:
                                if bd_user['language_code'] == 'ru':
                                    text = "🛒 | У вас нет столько монет!"
                                else:
                                    text = "🛒 | You don't have that many coins!"

                                bot.send_message(message.chat.id, text, reply_markup = Functions.markup(bot, 'market', user))
                                return

                            for _ in range(number):
                                bd_user['inventory'].append(mmd['item'])

                            if mr_user != None:
                                users.update_one( {"userid": int(us_id)}, {"$inc": {'coins': mmd['price'] * number }} )

                            market_['products'][str(us_id)]['products'][str(key_i)]['col'][0] += number

                            if market_['products'][str(us_id)]['products'][str(key_i)]['col'][0] >= market_['products'][str(us_id)]['products'][str(key_i)]['col'][1]:
                                del market_['products'][str(us_id)]['products'][str(key_i)]


                            management.update_one( {"_id": 'products'}, {"$set": {'products': market_['products'] }} )
                            users.update_one( {"userid": user.id}, {"$set": {'inventory': bd_user['inventory']}} )
                            users.update_one( {"userid": user.id}, {"$inc": {'coins': (mmd['price'] * number) * -1 }} )

                            if bd_user['language_code'] == 'ru':
                                text = "🛒 | Товар был куплен!"
                            else:
                                text = "🛒 | The product was purchased!"

                            bot.send_message(call.message.chat.id, text, reply_markup = Functions.markup(bot, 'market', user))

                            Functions.notifications_manager(bot, "product_bought", mr_user, mmd['price'] * number )

                        if message.text in [f"Yes, purchase {iname}", f"Да, приобрести {iname}"]:
                            pass

                        elif message.text in [ '🛒 Рынок', '🛒 Market' ]:

                            if bd_user['language_code'] == 'ru':
                                text = "🛒 | Возвращение в меню рынка!"
                            else:
                                text = "🛒 | Return to the market menu!"

                            bot.send_message(message.chat.id, text, reply_markup = Functions.markup(bot, 'market', user))
                            return

                        else:

                            if bd_user['language_code'] == 'ru':
                                text = "🛒 | Возвращение в меню рынка!"
                            else:
                                text = "🛒 | Return to the market menu!"

                            bot.send_message(message.chat.id, text, reply_markup = Functions.markup(bot, 'market', user))
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
                        text = f"🛒 | Вы уверены что вы хотите купить {iname}?"
                        ans = [f"Да, приобрести {iname}", '🛒 Рынок']
                    else:
                        text = f"🛒 | Are you sure you want to buy {iname}?"
                        ans = [f"Yes, purchase {iname}", '🛒 Market']

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

    # def market_inf(bot, bd_user, call, user):

    #     m_call = call.data.split()

    #     market_ = management.find_one({"_id": 'products'})
    #     us_id = m_call[0][7:]
    #     key_i = m_call[1]

    #     if str(us_id) in market_['products'].keys():
    #         ma_d = market_['products'][str(us_id)]['products']

    #         if str(key_i) in ma_d.keys():
    #             mmd = market_['products'][str(us_id)]['products'][str(key_i)]

    #         else:
    #             if bd_user['language_code'] == 'ru':
    #                 text = "🛒 | Предмет не найден на рынке, возможно он уже был куплен."
    #             else:
    #                 text = "🛒 | The item was not found on the market, it may have already been purchased."

    #             bot.send_message(call.message.chat.id, text)

    #     else:
    #         if bd_user['language_code'] == 'ru':
    #             text = "🛒 | Предмет не найден на рынке, возможно он уже был куплен."
    #         else:
    #             text = "🛒 | The item was not found on the market, it may have already been purchased."

    #         bot.send_message(call.message.chat.id, text)

    def iteminfo(bot, bd_user, call, user):

        item = Functions.get_dict_item(call.data[9:])
        text, image  = Functions.item_info(item, bd_user['language_code'], mark = False)

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
        data = Functions.des_qr(did[1], True)
        it_id = str(data['item_id'])
        cr_n = did[2]

        data_item = items_f['items'][it_id]
        user_item = None

        if data in bd_user['inventory']:
            user_item = data

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
                    list_inv_id = []
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
                            text = f'🍡 | Предмет {", ".join(Functions.sort_items_col( data_item["ns_craft"][cr_n]["create"], "ru" ))} создан!'
                        else:
                            text = f'🍡 | The item {", ".join(Functions.sort_items_col( data_item["ns_craft"][cr_n]["create"], "en" ))} is created!'

                        list_inv_id.clear()
                        for i in fr_user['inventory']: list_inv_id.append(i['item_id'])

                        for it_m in data_item["ns_craft"][cr_n]['materials']:
                            lst_ind = list_inv_id.index(it_m)
                            list_inv_id[lst_ind] = None
                            fr_user['inventory'].remove( list_inv[lst_ind] )

                        for it_c in data_item["ns_craft"][cr_n]['create']:
                            dt = Functions.add_item_to_user(fr_user, it_c, 1, 'data')
                            for i in dt:
                                fr_user['inventory'].append(i)

                        users.update_one( {"userid": bd_user['userid']}, {"$set": {'inventory': fr_user['inventory'] }} )

                    else:

                        if bd_user['language_code'] == 'ru':
                            text = f'❗ | Материалов недостаточно!'
                        else:
                            text = f"❗ | Materials are not enough!"

                    bot.send_message(user.id, text, reply_markup = Functions.markup(bot, Functions.last_markup(bd_user, alternative = 'profile'), bd_user ) )

                else:
                    bot.send_message(user.id, f'❌', reply_markup = Functions.markup(bot, Functions.last_markup(bd_user, alternative = 'profile'), bd_user ))

            markup = types.ReplyKeyboardMarkup(resize_keyboard = True, row_width = 1)

            if bd_user['language_code'] == 'ru':
                markup.add( *[i for i in ['Да, я хочу это сделать', '❌ Отмена'] ] )
                msg = bot.send_message(user.id, f'Вы уверены что хотите создать {", ".join(Functions.sort_items_col( data_item["ns_craft"][cr_n]["create"], "ru" ))}?', reply_markup = markup)

            else:
                markup.add( *[i for i in ['Yes, I want to do it', '❌ Cancel'] ] )
                msg = bot.send_message(user.id, f'Are you sure you want to create {", ".join(Functions.sort_items_col( data_item["ns_craft"][cr_n]["create"], "en" ))}?', reply_markup = markup)

            bot.register_next_step_handler(msg, wrk_p)

    def cancel_progress(bot, bd_user, call, user):

        did = call.data.split()
        dino_id = did[1]

        if bd_user['dinos'][dino_id]['activ_status'] == 'hunting':

            del bd_user['dinos'][ dino_id ]['target']
            del bd_user['dinos'][ dino_id ]['h_type']
            bd_user['dinos'][dino_id]['activ_status'] = 'pass_active'

            Functions.notifications_manager(bot, "hunting_end", bd_user, dino_id = dino_id)
            users.update_one( {"userid": bd_user['userid']}, {"$set": {f'dinos.{dino_id}': bd_user['dinos'][dino_id] }} )


    def change_rarity_call_data(bot, bd_user, call, user):

        did = call.data.split()
        dino_id = did[1]
        quality = did[2]

        data_q_r = settings_f['change_rarity']

        def change_rarity(message, chang_type):

            if message.text in ['Да, я хочу это сделать', 'Yes, I want to do it']:
                bd_user = users.find_one({"userid": user.id })
                bd_user = Functions.dino_q(bd_user)

                if dino_id in bd_user['dinos'].keys():
                    if bd_user['coins'] >= data_q_r[quality]['money']:
                        list_inv_id = []
                        for i in bd_user['inventory']: list_inv_id.append(i['item_id'])

                        for i in data_q_r[quality]['materials']:
                            if i not in list_inv_id:

                                if bd_user['language_code'] == 'ru':
                                    text = f'❗ | Материалов недостаточно!'
                                else:
                                    text = f"❗ | Materials are not enough!"

                                bot.send_message(user.id, text, reply_markup = Functions.markup(bot, Functions.last_markup(bd_user, alternative = 'dino-tavern'), bd_user ))
                                return

                        qul = quality
                        if quality == 'ran':
                            rd = {
                            'com': ['com'],
                            'unc': ['unc'],
                            'rar': ['rar'],
                            'myt': ['myt'],
                            'leg': ['leg']
                            }

                            qul = Functions.random_items(rd)

                        bd_user['coins'] -= data_q_r[quality]['money']
                        bd_user['dinos'][dino_id]['quality'] = qul

                        for i in data_q_r[quality]['materials']:
                            ittm = Functions.get_dict_item(i)
                            bd_user['inventory'].remove(ittm)

                        if chang_type == 'change_dino':

                            ndino_id = None
                            while ndino_id == None:
                                p_var = random.choice(json_f['data']['dino'])
                                dino = json_f['elements'][str(p_var)]
                                if dino['image'][5:8] == qul:
                                    if dino_id != p_var:
                                        ndino_id = p_var

                            bd_user['dinos'][dino_id]['dino_id'] = ndino_id

                        users.update_one( {"userid": bd_user['userid']}, {"$set": {'inventory': bd_user['inventory'] }} )
                        users.update_one( {"userid": bd_user['userid']}, {"$set": {f'dinos.{dino_id}': bd_user['dinos'][dino_id] }} )
                        users.update_one( {"userid": bd_user['userid']}, {"$inc": {'coins': data_q_r[quality]['money'] * -1 }} )

                        if bd_user['language_code'] == 'ru':
                            text = f'🔮 Происходит магия!\n\nВаш динозавр поменял редкость, скорее загляните в профиль!'
                            text2 = '🎗 | Вы были возвращены в прошлое меню!'
                        else:
                            text = f"🔮 Magic happens!\n\nYour dinosaur has changed the rarity, rather take a look at the profile!"
                            text2 = '🎗 | You have been returned to the last menu!'

                        bot.send_message(user.id, text, reply_markup = Functions.inline_markup(bot, f'open_dino_profile', user.id, ['Открыть профиль', 'Open a profile'], dino_id))
                        bot.send_message(user.id, text2, reply_markup = Functions.markup(bot, Functions.last_markup(bd_user, alternative = 'dino-tavern'), bd_user ))

                    else:
                        if bd_user['language_code'] == 'ru':
                            text = f'❗ | Монет недостаточно!'
                        else:
                            text = f"❗ | Coins are not enough!"

                        bot.send_message(user.id, text, reply_markup = Functions.markup(bot, Functions.last_markup(bd_user, alternative = 'dino-tavern'), bd_user ))

            else:
                bot.send_message(user.id, f'❌', reply_markup = Functions.markup(bot, Functions.last_markup(bd_user, alternative = 'dino-tavern'), bd_user ))

        def pre_change(message):

            if message.text in ['1️⃣', '2️⃣']:

                if message.text == '1️⃣':
                    chang_type = 'change_rarity'

                else:
                    chang_type = 'change_dino'

                markup = types.ReplyKeyboardMarkup(resize_keyboard = True, row_width = 1)
                if bd_user['language_code'] == 'ru':
                    markup.add( *[i for i in ['Да, я хочу это сделать', '❌ Отмена'] ] )
                    msg = bot.send_message(user.id, f'Вы уверены что хотите изменить редкость своего динозавра?', reply_markup = markup)

                else:
                    markup.add( *[i for i in ['Yes, I want to do it', '❌ Cancel'] ] )
                    msg = bot.send_message(user.id, f'Are you sure you want to change the rarity of your dinosaur?', reply_markup = markup)

                bot.register_next_step_handler(msg, change_rarity, chang_type)

            else:
                bot.send_message(user.id, f'❌', reply_markup = Functions.markup(bot, Functions.last_markup(bd_user, alternative = 'dino-tavern'), bd_user ))

        markup = types.ReplyKeyboardMarkup(resize_keyboard = True, row_width = 2)
        markup.add( *[i for i in ['1️⃣', '2️⃣', '❌'] ] )

        if bd_user['language_code'] == 'ru':
            text = f'❓ | Хотите ли вы поменять динозавра или улучшить его редкость?\n\n1️⃣ — Изменение редкости\n2️⃣ —  Измена редкости и динозавра'

        else:
            text = f'❓ | Do you want to change the dinosaur or improve its rarity?\n\n1️⃣ - Change of rarity\n2️⃣ — Change of rarity and dinosaur'

        msg = bot.send_message(user.id, text, reply_markup = markup)
        bot.register_next_step_handler(msg, pre_change)

    def dungeon_settings(bot, bd_user, call, user):

        dungeonid = int(call.data.split()[1])

        inf = Dungeon.message_upd(bot, userid = user.id, dungeonid = dungeonid, type = 'settings')
        dng, inf = Dungeon.base_upd(userid = user.id, messageid = 'settings', dungeonid = dungeonid, type = 'edit_last_page')

    def dungeon_to_lobby(bot, bd_user, call, user):

        dungeonid = int(call.data.split()[1])

        inf = Dungeon.message_upd(bot, userid = user.id, dungeonid = dungeonid, image_update = True)
        dng, inf = Dungeon.base_upd(userid = user.id, messageid = 'main', dungeonid = dungeonid, type = 'edit_last_page')

    def dungeon_settings_lang(bot, bd_user, call, user):

        dungeonid = int(call.data.split()[1])
        dung = dungeons.find_one({"dungeonid": dungeonid})

        if dung != None:

            if dung['settings']['lang'] == 'ru': lang = 'en'
            else: lang = 'ru'

            dungeons.update_one( {"dungeonid": dungeonid}, {"$set": {f'settings.lang': lang }} )

            inf = Dungeon.message_upd(bot, userid = user.id, dungeonid = dungeonid, type = 'settings')
            inf = Dungeon.message_upd(bot, userid = user.id, dungeonid = dungeonid, upd_type = 'all', ignore_list = [user.id])

    def dungeon_settings_batnotf(bot, bd_user, call, user):

        dungeonid = int(call.data.split()[1])
        dung = dungeons.find_one({"dungeonid": dungeonid})

        if dung != None:
            if dung['settings']['battle_notifications'] == True: ntf = False
            else: ntf = True

            dungeons.update_one( {"dungeonid": dungeonid}, {"$set": {f'settings.battle_notifications': ntf }} )

            inf = Dungeon.message_upd(bot, userid = user.id, dungeonid = dungeonid, type = 'settings')

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

        dng, inf = Dungeon.base_upd(userid = user.id, dungeonid = dungeonid, type = 'remove_user')

        bot.delete_message(user.id, dung['users'][str(user.id)]['messageid'])

        inf = Dungeon.message_upd(bot, userid = user.id, dungeonid = dungeonid, upd_type = 'all')

        bot.send_message(user.id, "✅", reply_markup = Functions.markup(bot, "dungeon_menu", user.id ))

    def dungeon_leave_False(bot, bd_user, call, user):

        dungeonid = int(call.data.split()[1])
        dung = dungeons.find_one({"dungeonid": dungeonid})

        inf = Dungeon.message_upd(bot, userid = user.id, dungeonid = dungeonid)

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

        inf = Dungeon.message_upd(bot, dungeonid = dungeonid, type = 'delete_dungeon')

        dng, inf = Dungeon.base_upd(dungeonid = dungeonid, type = 'delete_dungeon')


    def dungeon_remove_False(bot, bd_user, call, user):

        dungeonid = int(call.data.split()[1])
        dung = dungeons.find_one({"dungeonid": dungeonid})

        inf = Dungeon.message_upd(bot, userid = user.id, dungeonid = dungeonid, type = 'settings')


    def dungeon_add_dino_menu(bot, bd_user, call, user):

        dungeonid = int(call.data.split()[1])
        dung = dungeons.find_one({"dungeonid": dungeonid})

        inf = Dungeon.message_upd(bot, userid = user.id, dungeonid = dungeonid, type = 'add_dino')

        dng, inf = Dungeon.base_upd(userid = user.id, messageid = 'dino_control', dungeonid = dungeonid, type = 'edit_last_page')

    def dungeon_remove_dino_menu(bot, bd_user, call, user):

        dungeonid = int(call.data.split()[1])
        dung = dungeons.find_one({"dungeonid": dungeonid})

        inf = Dungeon.message_upd(bot, userid = user.id, dungeonid = dungeonid, type = 'remove_dino')

        dng, inf = Dungeon.base_upd(userid = user.id, messageid = 'dino_control', dungeonid = dungeonid, type = 'edit_last_page')

    def dungeon_add_dino(bot, bd_user, call, user):

        dungeonid = int(call.data.split()[1])
        dinoid = call.data.split()[2]
        dung = dungeons.find_one({"dungeonid": dungeonid})

        dng, inf = Dungeon.base_upd(userid = user.id, dungeonid = dungeonid, type = 'add_dino', dinosid = [dinoid])

        inf2 = Dungeon.message_upd(bot, userid = user.id, dungeonid = dungeonid, type = inf)

        if inf == 'add_dino':
            inf3 = Dungeon.message_upd(bot, userid = user.id, dungeonid = dungeonid, upd_type = 'all', ignore_list = [user.id])

    def dungeon_remove_dino(bot, bd_user, call, user):

        dungeonid = int(call.data.split()[1])
        dinoid = call.data.split()[2]
        dung = dungeons.find_one({"dungeonid": dungeonid})

        dng, inf = Dungeon.base_upd(userid = user.id, dungeonid = dungeonid, type = 'remove_dino', dinosid = [dinoid])

        inf = Dungeon.message_upd(bot, userid = user.id, dungeonid = dungeonid, type = 'remove_dino')

        inf = Dungeon.message_upd(bot, userid = user.id, dungeonid = dungeonid, upd_type = 'all', ignore_list = [user.id])

    def dungeon_invite(bot, bd_user, call, user):

        dungeonid = int(call.data.split()[1])

        inf = Dungeon.message_upd(bot, userid = user.id, dungeonid = dungeonid, type = 'invite_room')
        dng, inf = Dungeon.base_upd(userid = user.id, messageid = 'invite', dungeonid = dungeonid, type = 'edit_last_page')

    def dungeon_supplies(bot, bd_user, call, user):

        dungeonid = int(call.data.split()[1])

        inf = Dungeon.message_upd(bot, userid = user.id, dungeonid = dungeonid, type = 'supplies')
        dng, inf = Dungeon.base_upd(userid = user.id, messageid = 'supplies', dungeonid = dungeonid, type = 'edit_last_page')

    def dungeon_set_coins(bot, bd_user, call, user):

        dungeonid = int(call.data.split()[1])
        dung = dungeons.find_one({"dungeonid": dungeonid})

        min_coins = 150 + 50 * dung['settings']['start_floor']

        def set_coins(message, old_m):
            bot.delete_message(user.id, old_m.message_id)
            bot.delete_message(user.id, message.message_id)

            try:
                coins = int(message.text)
            except:

                if bd_user['language_code'] == 'ru':
                    show_text = '❗ | Требовалось указать число!'

                else:
                    show_text = "❗ | It was required to specify a number!"

                bot.answer_callback_query(call.id, show_text, show_alert = True)
                return

            else:

                if coins > bd_user['coins']:

                    if bd_user['language_code'] == 'ru':
                        show_text = '❗ | У вас нет столько монет!'

                    else:
                        show_text = "❗ | You don't have that many coins!"

                    bot.answer_callback_query(call.id, show_text, show_alert = True)

                elif coins < min_coins:

                    if bd_user['language_code'] == 'ru':
                        show_text = f'❗ | Требовалось указать число больше или равное {min_coins}!'

                    else:
                        show_text = f"❗ | It was required to specify a number greater than or equal to {min_coins}!"

                    bot.answer_callback_query(call.id, show_text, show_alert = True)

                else:

                    if bd_user['language_code'] == 'ru':
                        show_text = '✔ | Монеты установлены!'

                    else:
                        show_text = "✔ | Coins are installed!"

                    bot.answer_callback_query(call.id, show_text)
                    dungeons.update_one( {"dungeonid": dungeonid}, {"$set": {f'users.{user.id}.coins': coins }} )
                    inf = Dungeon.message_upd(bot, userid = user.id, dungeonid = dungeonid, type = 'supplies')


        if bd_user['language_code'] == 'ru':
            text = '🎲 | Укажите число монет, которое хотите взять с собой > '

        else:
            text = "🎲 | Specify the number of coins you want to take with you >"

        msg = bot.send_message(call.message.chat.id, text)
        bot.register_next_step_handler(msg, set_coins, msg)

    def dungeon_add_item_action(bot, bd_user, call, user):

        data_items = items_f['items']
        items = bd_user['inventory']

        dungeonid = int(call.data.split()[1])
        dung = dungeons.find_one({"dungeonid": dungeonid})

        list_items_id = []
        for i in items: list_items_id.append( i['item_id'] )

        lg_name = bd_user['language_code']
        if bd_user['language_code'] == 'ru':
            show_text = '🎴 | Ваш инвентарь пуст!'
            text = '🍨 | Введите название предмета, который вы хотите взять с собой >'
            text2 = '🔎 | Ожидание ввода...\n❌ | Введите "Отмена" для отмены поиска.'

        else:
            show_text = "🎴 | Your inventory is empty!"
            text = '🍨 | Enter the name of the item you want to take with you >'
            text2 = '🔎 | Waiting for input...\n❌ | Enter "Cancel" to cancel the search.'

        if items == []:

            bot.answer_callback_query(call.id, show_text, show_alert = True)

        else:

            bot.edit_message_caption(text, call.message.chat.id, call.message.message_id, parse_mode = 'Markdown')

            def search_item(message, old_m):
                bot.delete_message(user.id, old_m.message_id)

                if message.text in ['Отмена', 'Cancel']:
                    bot.delete_message(user.id, message.message_id)
                    inf = Dungeon.message_upd(bot, userid = user.id, dungeonid = dungeonid, type = 'supplies')

                else:

                    s_i = []
                    for i in items_f['items']:
                        item = items_f['items'][i]

                        for inn in [ item['name']['ru'], item['name']['en'] ]:
                            if fuzz.token_sort_ratio(message.text, inn) > 70 or fuzz.ratio(message.text, inn) > 70 or message.text == inn:
                                s_i.append(i)

                    bot.delete_message(user.id, message.message_id)

                    if s_i == []:

                        if bd_user['language_code'] == 'ru':
                            show_text2 = "🔎 | Предмет не найден, попробуйте ввести более правильное название!"
                        else:
                            show_text2 = "🔎 | The item is not found, try to enter a more correct name!"

                        Dungeon.message_upd(bot, userid = user.id, dungeonid = dungeonid, type = 'supplies')
                        bot.answer_callback_query(call.id, show_text2, show_alert = True)

                    else:
                        pr_l_s = list(set(list_items_id) & set(s_i) )

                        if pr_l_s == []:

                            if bd_user['language_code'] == 'ru':
                                show_text3 = "🔎 | Предмет не найден в вашем инвентаре!"
                            else:
                                show_text3 = "🔎 | The item is not found in your inventory!"

                            Dungeon.message_upd(bot, userid = user.id, dungeonid = dungeonid, type = 'supplies')
                            bot.answer_callback_query(call.id, show_text3, show_alert = True)

                        else:
                            inl_d = {}
                            for i in items:

                                if i['item_id'] in pr_l_s:

                                    if Functions.item_authenticity(i) == True:

                                        if data_items[i['item_id']]['name'][lg_name] not in inl_d.keys():
                                            inl_d[ data_items[i['item_id']]['name'][lg_name] ] = f"dungeon_add_item {dungeonid} {Functions.qr_item_code(i)}"

                                    else:
                                        if f"{data_items[i['item_id']]['name'][lg_name]} ({Functions.qr_item_code(i, False)})" not in inl_d.keys():

                                            inl_d[ f"{data_items[i['item_id']]['name'][lg_name]} ({Functions.qr_item_code(i, False)})" ] = f"dungeon_add_item {dungeonid} {Functions.qr_item_code(i)}"

                            markup_inline = types.InlineKeyboardMarkup(row_width = 3)

                            markup_inline.add( *[
                            types.InlineKeyboardButton(
                                text = inl,
                                callback_data = inl_d[inl] ) for inl in inl_d.keys()
                                                ])

                            if bd_user['language_code'] == 'ru':
                                text = "🔎 | Выберите подходящий предмет > "
                                inl = ['❌ Отмена', f'dungeon.supplies {dungeonid}']
                            else:
                                text = "🔎 | Choose the appropriate subject > "
                                inl = ['❌ Cancel', f'dungeon.supplies {dungeonid}']

                            markup_inline.add( types.InlineKeyboardButton(text = inl[0], callback_data = inl[1] ) )

                            bot.edit_message_caption(text, call.message.chat.id, call.message.message_id, parse_mode = 'Markdown', reply_markup = markup_inline)

            msg = bot.send_message(call.message.chat.id, text2)
            bot.register_next_step_handler(msg, search_item, msg)

    def dungeon_add_item(bot, bd_user, call, user):

        dungeonid = int(call.data.split()[1])
        data = Functions.des_qr(call.data.split()[2], True)
        dung = dungeons.find_one({"dungeonid": dungeonid})
        it_id = str(data['item_id'])

        data_item = items_f['items'][it_id]
        user_item = None

        if data in bd_user['inventory']:
            user_item = data

        if user_item == None:

            if bd_user['language_code'] == 'ru':
                text = f'❌ | Предмет не найден в инвентаре!'
            else:
                text = f"❌ | Enter the correct number!"

            bot.answer_callback_query(call.id, text, show_alert = True)
            inf = Dungeon.message_upd(bot, userid = user.id, dungeonid = dungeonid, type = 'supplies')

        if user_item != None:

            def item_count(message, old_m, max_count):
                bot.delete_message(user.id, old_m.message_id)
                bot.delete_message(user.id, message.message_id)

                try:
                    count = int(message.text)
                except:
                    count = None

                if count == None or count <= 0 or count > max_count:

                    if bd_user['language_code'] == 'ru':
                        text = f'❌ | Введите корректное число!'
                    else:
                        text = f"❌ | Item not found in inventory!"

                    bot.answer_callback_query(call.id, text, show_alert = True)
                    inf = Dungeon.message_upd(bot, userid = user.id, dungeonid = dungeonid, type = 'supplies')

                else:

                    if len(dung['users'][str(user.id)]['inventory']) + count > Dungeon.d_backpack(bd_user):

                        if bd_user['language_code'] == 'ru':
                            text = f'❌ | Ваш рюкзак не может вместить в себя столько предметов!'
                        else:
                            text = f"❌ | Your backpack can't hold so many items!"

                        bot.answer_callback_query(call.id, text, show_alert = True)
                        inf = Dungeon.message_upd(bot, userid = user.id, dungeonid = dungeonid, type = 'supplies')

                    else:

                        for _ in range(count):
                            bd_user['inventory'].remove(user_item)
                            dung['users'][str(user.id)]['inventory'].append(user_item)

                        users.update_one( {"userid": user.id}, {"$set": {'inventory': bd_user['inventory']}} )
                        dungeons.update_one( {"dungeonid": dungeonid}, {"$set": {f'users.{user.id}': dung['users'][str(user.id)] }} )

                    inf = Dungeon.message_upd(bot, userid = user.id, dungeonid = dungeonid, type = 'supplies')

            max_count = bd_user['inventory'].count(user_item)

            if max_count != 1:

                if bd_user['language_code'] == 'ru':
                    text = f'🎈 | Ожидание...'
                else:
                    text = f"🎈 | Wait..."

                bot.edit_message_caption(text, call.message.chat.id, call.message.message_id)

                if bd_user['language_code'] == 'ru':
                    text2 = f'🧶 | Введите количество предмета от 1 до {max_count} >'
                else:
                    text2 = f"🧶 | Enter the number of items from 1 to {max_count} >"

                msg = bot.send_message(call.message.chat.id, text2)
                bot.register_next_step_handler(msg, item_count, msg, max_count)

            else:

                if len(dung['users'][str(user.id)]['inventory']) + max_count > Dungeon.d_backpack(bd_user):

                    if bd_user['language_code'] == 'ru':
                        text = f'❌ | Ваш рюкзак не может вместить в себя столько предметов!'
                    else:
                        text = f"❌ | Your backpack can't hold so many items!"

                    bot.answer_callback_query(call.id, text, show_alert = True)
                    inf = Dungeon.message_upd(bot, userid = user.id, dungeonid = dungeonid, type = 'supplies')


                else:

                    for _ in range(max_count):
                        bd_user['inventory'].remove(user_item)
                        dung['users'][str(user.id)]['inventory'].append(user_item)

                    users.update_one( {"userid": user.id}, {"$set": {'inventory': bd_user['inventory']}} )
                    dungeons.update_one( {"dungeonid": dungeonid}, {"$set": {f'users.{user.id}': dung['users'][str(user.id)] }} )

                    inf = Dungeon.message_upd(bot, userid = user.id, dungeonid = dungeonid, type = 'supplies')

    def dungeon_remove_item_action(bot, bd_user, call, user):

        dungeonid = int(call.data.split()[1])
        dung = dungeons.find_one({"dungeonid": dungeonid})
        data_items = items_f['items']
        user_items = dung['users'][str(user.id)]['inventory']
        markup_inline = types.InlineKeyboardMarkup()
        mrk_d = {}

        lg_name = bd_user['language_code']

        for i in user_items:
            if Functions.item_authenticity(i) == True:
                ke = f"{data_items[ i['item_id'] ]['name'][lg_name]}  x{user_items.count(i)}"

                mrk_d[ ke ] = f'dungeon_remove_item {dungeonid} {Functions.qr_item_code(i)}'
            else:
                ke = f"{data_items[ i['item_id'] ]['name'][lg_name]}  x{user_items.count(i)} ({Functions.qr_item_code(i, False)})"

                mrk_d[ ke ] = f'dungeon_remove_item {dungeonid} {Functions.qr_item_code(i)}'

        markup_inline = types.InlineKeyboardMarkup(row_width = 1)

        markup_inline.add( *[
        types.InlineKeyboardButton( text = inl,
        callback_data = mrk_d[inl] ) for inl in mrk_d.keys()
                            ])

        if bd_user['language_code'] == 'ru':
            inl = ['❌ Отмена', f'dungeon.supplies {dungeonid}']
            text = '🧵 | Выберите предмет для удаления из инвентаря >'
        else:
            inl = ['❌ Cancel', f'dungeon.supplies {dungeonid}']
            text = '🧵 | Select an item to remove from inventory >'

        markup_inline.add( types.InlineKeyboardButton(text = inl[0], callback_data = inl[1] ) )

        bot.edit_message_caption(text, call.message.chat.id, call.message.message_id, reply_markup = markup_inline)

    def dungeon_remove_item(bot, bd_user, call, user):

        dungeonid = int(call.data.split()[1])
        dung = dungeons.find_one({"dungeonid": dungeonid})

        if dung != None:
            data = Functions.des_qr(call.data.split()[2], True)
            it_id = str(data['item_id'])

            data_item = items_f['items'][it_id]
            user_item = None

            if data in bd_user['inventory']:
                user_item = data

            if user_item == None:

                if bd_user['language_code'] == 'ru':
                    text = f'❌ | Предмет не найден в инвентаре!'
                else:
                    text = f"❌ | Enter the correct number!"

                bot.answer_callback_query(call.id, text, show_alert = True)
                inf = Dungeon.message_upd(bot, userid = user.id, dungeonid = dungeonid, type = 'supplies')

            if user_item != None:

                for i in bd_user['inventory']:
                    if i == user_item:
                        dung['users'][str(user.id)]['inventory'].remove(i)

                dungeons.update_one( {"dungeonid": dungeonid}, {"$set": {f'users.{user.id}.inventory': dung['users'][str(user.id)]['inventory'] }} )
                inf = Dungeon.message_upd(bot, userid = user.id, dungeonid = dungeonid, type = 'supplies')

    def dungeon_ready(bot, bd_user, call, user):

        dungeonid = int(call.data.split()[1])
        dung = dungeons.find_one({"dungeonid": dungeonid})
        ok = False

        min_coins = 150 + 50 * dung['settings']['start_floor']

        if dung != None:

            if user.id not in dung['stage_data']['preparation']['ready']:

                if dung['users'][str(user.id)]['dinos'] != {}:

                    if dung['users'][str(user.id)]['coins'] > bd_user['coins']:

                        if bd_user['language_code'] == 'ru':
                            show_text = '❗ | Вы указали недопустимое количество монет!'

                        else:
                            show_text = '❗ | You have specified an invalid number of coins!'

                        bot.answer_callback_query(call.id, show_text, show_alert = True)

                    else:
                        if dung['users'][str(user.id)]['coins'] < min_coins:

                            if bd_user['language_code'] == 'ru':
                                show_text = f'❗ | Вам необходимо взять как минимум {min_coins} монет для входа в подземелье! (они будут списаны)'

                            else:
                                show_text = f'❗ | You need to take at least {min_coins} coins to enter the dungeon! (they will be debited)'

                            bot.answer_callback_query(call.id, show_text, show_alert = True)


                        else:
                            dung['stage_data']['preparation']['ready'].append(user.id)
                            ok = True

                else:

                    if bd_user['language_code'] == 'ru':
                        show_text = '❗ | Вы не выбрали участвующих динозавров!'

                    else:
                        show_text = "❗ | You didn't choose the participating dinosaurs!"

                    bot.answer_callback_query(call.id, show_text, show_alert = True)

            else:
                dung['stage_data']['preparation']['ready'].remove(user.id)
                ok = True

            if ok == True:

                dungeons.update_one( {"dungeonid": dungeonid}, {"$set": {f'stage_data': dung['stage_data'] }} )
                inf = Dungeon.message_upd(bot, userid = user.id, dungeonid = dungeonid, upd_type = 'all')

            else:
                # print('-0-095')
                pass

    def dungeon_start_game(bot, bd_user, call, user):

        dungeonid = int(call.data.split()[1])
        dung = dungeons.find_one({"dungeonid": dungeonid})
        min_coins = 150 + 50 * dung['settings']['start_floor']

        if dung != None:

            if dung['users'][str(user.id)]['dinos'] != {}:

                if dung['users'][str(user.id)]['coins'] <= bd_user['coins']:

                    if dung['users'][str(user.id)]['coins'] >= min_coins:

                        if len(dung['stage_data']['preparation']['ready']) == len(dung['users']) - 1:

                            complexity = [0, 0] #игроков и динозавров изначально

                            for userid in dung['users'].keys():
                                complexity[0] += 1
                                userd = dung['users'][userid]
                                dg_user = users.find_one({"userid": int(userid)})
                                dung['users'][userid]['last_page'] = 'main'

                                for dk in userd['dinos'].keys():
                                    complexity[1] += 1
                                    dg_user['dinos'][dk]['activ_status'] = 'dungeon'
                                    dg_user['dinos'][dk]['dungeon_id'] = dungeonid

                                users.update_one( {"userid": int(userid) }, {"$inc": {f'coins': userd['coins'] * -1 }} )
                                users.update_one( {"userid": int(userid) }, {"$set": {f'dinos': dg_user['dinos'] }} )

                                userd['coins'] -= min_coins


                            dung['stage_data']['game'] = {
                                    'floor_n': dung['settings']['start_floor'],
                                    'room_n': 0,
                                    'player_move': [ list( dung['users'].keys() )[0], list( dung['users'].keys() ) ],
                                    'start_time': int(time.time()),
                                    'complexity': { 'users': complexity[0], 'dinos': complexity[1] },
                                    'floors_stat': {}
                                                         }

                            dungeons.update_one( {"dungeonid": dungeonid}, {"$set": {f'stage_data': dung['stage_data'] }} )
                            dungeons.update_one( {"dungeonid": dungeonid}, {"$set": {f'users': dung['users'] }} )
                            dungeons.update_one( {"dungeonid": dungeonid}, {"$set": {f'dungeon_stage': 'game' }} )

                            dng, inf = Dungeon.base_upd(dungeonid = dungeonid, type = 'create_floor')

                            inf = Dungeon.message_upd(bot, userid = user.id, dungeonid = dungeonid, upd_type = 'all', image_update = True)


                        else:

                            if bd_user['language_code'] == 'ru':
                                show_text = '❗ | Не все пользователи готовы к игре!'

                            else:
                                show_text = "❗ | Not all users are ready for the game!"

                            bot.answer_callback_query(call.id, show_text, show_alert = True)

                    else:

                        if bd_user['language_code'] == 'ru':
                            show_text = f'❗ | Вам необходимо взять как минимум {min_coins} монет для входа в подземелье! (они будут списаны)'

                        else:
                            show_text = f'❗ | You need to take at least {min_coins} coins to enter the dungeon! (they will be debited)'

                        bot.answer_callback_query(call.id, show_text, show_alert = True)

                else:

                    if bd_user['language_code'] == 'ru':
                        show_text = '❗ | Вы указали недопустимое количество монет!'

                    else:
                        show_text = '❗ | You have specified an invalid number of coins!'

                    bot.answer_callback_query(call.id, show_text, show_alert = True)

            else:

                if bd_user['language_code'] == 'ru':
                    show_text = '❗ | Вы не выбрали участвующих динозавров!'

                else:
                    show_text = "❗ | You didn't choose the participating dinosaurs!"

                bot.answer_callback_query(call.id, show_text, show_alert = True)

    def dungeon_next_room(bot, bd_user, call, user):

        dungeonid = int(call.data.split()[1])
        dung = dungeons.find_one({"dungeonid": dungeonid})

        if dung != None:

            room_n = str(dung['stage_data']['game']['room_n'])
            floor_n = str(dung['stage_data']['game']['floor_n'])
            if dung['floor'][room_n]['next_room'] == True:

                if len(dung['floor'][room_n]['ready']) >= len(dung['users']) - 1:

                    dung['stage_data']['game']['room_n'] += 1

                    for userid in dung['users'].keys():
                        dung['users'][userid]['last_page'] = 'main'

                    dungeons.update_one( {"dungeonid": dungeonid}, {"$set": {f'users': dung['users'] }} )

                    if dung['stage_data']['game']['room_n'] > dung['settings']['max_rooms'] + 1:

                        dng, inf = Dungeon.base_upd(dungeonid = dungeonid, type = 'create_floor')

                        for uk in dung['users'].keys():
                            uk = users.find_one({"userid": int(uk) })

                            Dungeon.check_quest(bot, uk, met = 'check', quests_type = 'come', kwargs = {'lvl': floor_n} )

                    else:

                        dungeons.update_one( {"dungeonid": dungeonid}, {"$set": {f'stage_data': dung['stage_data'] }} )

                    dungeons.update_one( {"dungeonid": dungeonid}, {"$set": {f'stage_data.game.floors_stat.{floor_n}.end_time': int(time.time()) }} )

                    inf = Dungeon.message_upd(bot, userid = user.id, dungeonid = dungeonid, upd_type = 'all', image_update = True)

                else:
                    if bd_user['language_code'] == 'ru':
                        show_text = '❗ | Не все пользователи подтвердили готовность перейти в следующую комнату!'

                    else:
                        show_text = "❗ | Not all users have confirmed their readiness to move to the next room!"

                    bot.answer_callback_query(call.id, show_text, show_alert = True)

            else:
                if bd_user['language_code'] == 'ru':
                    show_text = '❗ | Не выполнены все условия для перехода в следующую комнату!'

                else:
                    show_text = "❗ | All the conditions for moving to the next room are not met!"

                bot.answer_callback_query(call.id, show_text, show_alert = True)

    def dungeon_battle_action(bot, bd_user, call, user):

        dungeonid = int(call.data.split()[1])
        dinoid = int(call.data.split()[2])
        dung = dungeons.find_one({"dungeonid": dungeonid})
        din_name = bd_user['dinos'][str(dinoid)]['name']

        if bd_user['language_code'] == 'ru':
            text = f'⚔🛡 | Выберите действие для {din_name} >'
        else:
            text = f"⚔🛡 | Select an action for {din_name} >"

        bot.send_message(call.message.chat.id, text, reply_markup = Dungeon.inline(bot, user.id, dungeonid, 'battle_action', {'dinoid': dinoid}) )

    def dungeon_battle_attack(bot, bd_user, call, user):

        dungeonid = int(call.data.split()[1])
        dinoid = int(call.data.split()[2])
        dung = dungeons.find_one({"dungeonid": dungeonid})

        dung['users'][str(user.id)]['dinos'][str(dinoid)]['action'] = 'attack'
        dungeons.update_one( {"dungeonid": dungeonid}, {"$set": {f'users': dung['users'] }} )
        bot.delete_message(user.id, call.message.message_id)

        inf = Dungeon.message_upd(bot, userid = user.id, dungeonid = dungeonid, upd_type = 'all', image_update = False)

    def dungeon_battle_defend(bot, bd_user, call, user):

        dungeonid = int(call.data.split()[1])
        dinoid = int(call.data.split()[2])
        dung = dungeons.find_one({"dungeonid": dungeonid})

        dung['users'][str(user.id)]['dinos'][str(dinoid)]['action'] = 'defend'
        dungeons.update_one( {"dungeonid": dungeonid}, {"$set": {f'users': dung['users'] }} )
        bot.delete_message(user.id, call.message.message_id)

        inf = Dungeon.message_upd(bot, userid = user.id, dungeonid = dungeonid, upd_type = 'all', image_update = False)

    def dungeon_battle_idle(bot, bd_user, call, user):

        dungeonid = int(call.data.split()[1])
        dinoid = int(call.data.split()[2])
        dung = dungeons.find_one({"dungeonid": dungeonid})

        if 'action' in dung['users'][str(user.id)]['dinos'][str(dinoid)].keys():
            del dung['users'][str(user.id)]['dinos'][str(dinoid)]['action']
            dungeons.update_one( {"dungeonid": dungeonid}, {"$set": {f'users': dung['users'] }} )
            inf = Dungeon.message_upd(bot, userid = user.id, dungeonid = dungeonid, upd_type = 'all', image_update = False)

        bot.delete_message(user.id, call.message.message_id)

    def dungeon_next_room_ready(bot, bd_user, call, user):

        dungeonid = int(call.data.split()[1])
        dung = dungeons.find_one({"dungeonid": dungeonid})
        room_n = str(dung['stage_data']['game']['room_n'])

        if dung['floor'][room_n]['next_room'] == True:
            if user.id not in dung['floor'][room_n]['ready']:
                dung['floor'][room_n]['ready'].append(user.id)

            else:
                dung['floor'][room_n]['ready'].remove(user.id)

            dungeons.update_one( {"dungeonid": dungeonid}, {"$set": {f'floor': dung['floor'] }} )

        inf = Dungeon.message_upd(bot, userid = user.id, dungeonid = dungeonid, upd_type = 'all', image_update = False)

    def dungeon_end_move(bot, bd_user, call, user):

        dungeonid = int(call.data.split()[1])
        dung = dungeons.find_one({"dungeonid": dungeonid})

        if int(dung['stage_data']['game']['player_move'][0]) == user.id:

            sht, iff = Dungeon.battle_user_move(bot, dungeonid, user.id, bd_user, call)

            log, iff2 = Dungeon.battle_mob_move(bot, dungeonid, user.id, bd_user, call)

            dng, inf = Dungeon.base_upd(dungeonid = dungeonid, type = 'next_move')

            inf = Dungeon.message_upd(bot, userid = user.id, dungeonid = dungeonid, upd_type = 'all', image_update = True)


            if dung['settings']['battle_notifications'] == True:

                sw_text = sht + '\n'
                for i in log: sw_text += i + '\n'

                bot.send_message(user.id, sw_text, reply_markup = Functions.inline_markup(bot, f'delete_message', user.id) )

    def dungeon_dinos_stats(bot, bd_user, call, user):

        dungeonid = int(call.data.split()[1])
        dung = dungeons.find_one({"dungeonid": dungeonid})
        data_items = items_f['items']

        dinos_k = dung['users'][str(user.id)]['dinos'].keys()
        sw_text = ''

        if len(dinos_k) == 0:

            if bd_user['language_code'] == 'ru':
                sw_text = 'В подземелье нет ни одного вашего динозавра.'
            else:
                sw_text = "There aren't any of your dinosaurs in the dungeon."

        else:
            lgn = bd_user['language_code']

            for dkey in dinos_k:
                dino = bd_user['dinos'][dkey]
                dino_stats = dino['stats']
                d_eq = dino['dungeon']['equipment']
                if d_eq['weapon'] == None:
                    weap = ''
                else:
                    weap = f"\n{ data_items[ d_eq['weapon']['item_id'] ]['name'][lgn] } "

                sw_text += f"🦕 {dino['name']}\n❤ {dino_stats['heal']}%\n🍕 {dino_stats['eat']}%{weap}"
                sw_text += '\n\n'


        bot.send_message(user.id, sw_text, reply_markup = Functions.inline_markup(bot, f'delete_message', user.id) )

    def dungeon_collect_reward(bot, bd_user, call, user):

        dungeonid = int(call.data.split()[1])
        dung = dungeons.find_one({"dungeonid": dungeonid})

        room_n = str(dung['stage_data']['game']['room_n'])
        reward = dung['floor'][room_n]['reward']

        if dung['users'][str(user.id)]['dinos'] != {}:

            if user.id not in dung['floor'][room_n]['ready']:

                if str(user.id) not in reward['collected'].keys() or reward['collected'][str(user.id)] == {}:
                    reward['collected'][str(user.id)] = {}

                    reward['collected'][str(user.id)]['coins'] = True
                    reward['collected'][str(user.id)]['experience'] = True
                    reward['collected'][str(user.id)]['items'] = []

                    dung['users'][str(user.id)]['coins'] += reward['coins']
                    users.update_one( {"userid": user.id}, {"$inc": {'lvl.1': reward['experience'] }} )

                    dungeons.update_one( {"dungeonid": dungeonid}, {"$set": {f'floor.{room_n}.reward': reward }} )
                    dungeons.update_one( {"dungeonid": dungeonid}, {"$set": {f'users.{user.id}': dung['users'][str(user.id)] }} )

                inf = Dungeon.message_upd(bot, userid = user.id, dungeonid = dungeonid, type = 'collect_reward')
                dng, inf = Dungeon.base_upd(userid = user.id, messageid = 'collect_reward', dungeonid = dungeonid, type = 'edit_last_page')

            else:
                if bd_user['language_code'] == 'ru':
                    show_text = '❗ | Для взаимодействия, отмените готовность!'

                else:
                    show_text = "❗ | For interaction, cancel readiness!"

                bot.answer_callback_query(call.id, show_text, show_alert = True)


    def item_from_reward(bot, bd_user, call, user):

        dungeonid = int(call.data.split()[1])
        dung = dungeons.find_one({"dungeonid": dungeonid})
        user_dt = dung['users'][str(user.id)]

        room_n = str(dung['stage_data']['game']['room_n'])
        loot = dung['floor'][room_n]['reward']['items']
        room_rew = dung['floor'][room_n]['reward']

        inv = room_rew['collected'][ str(user.id) ]['items']
        d_items = []

        for itm in inv:

            if itm in loot:
                loot.remove(itm)

        item_dt = Functions.des_qr(call.data.split()[2], True)

        if item_dt in loot:

            if len(user_dt['inventory']) >= Dungeon.d_backpack(bd_user):

                if bd_user['language_code'] == 'ru':
                    show_text = '❗ | В вашем рюкзаке больше нет места! Освободите место, а после заберите награду.'

                else:
                    show_text = "❗ | There is no more space in your backpack! Make room, and then collect the reward."

                bot.answer_callback_query(call.id, show_text, show_alert = True)

            else:
                user_dt['inventory'].append(item_dt)
                dung['floor'][room_n]['reward']['collected'][str(user.id)]['items'].append(item_dt)

                dungeons.update_one( {"dungeonid": dungeonid}, {"$set": {f'floor':  dung['floor'] }} )
                dungeons.update_one( {"dungeonid": dungeonid}, {"$set": {f'users':  dung['users'] }} )

                inf = Dungeon.message_upd(bot, userid = user.id, dungeonid = dungeonid, type = 'collect_reward')


        else:
            inf = Dungeon.message_upd(bot, userid = user.id, dungeonid = dungeonid, type = 'collect_reward')

    def dungeon_inventory(bot, bd_user, call, user):

        dungeonid = int(call.data.split()[2])
        page = int(call.data.split()[1])
        dung = dungeons.find_one({"dungeonid": dungeonid})
        room_n = str(dung['stage_data']['game']['room_n'])

        if user.id not in dung['floor'][room_n]['ready']:

            Dungeon.message_upd(bot, userid = user.id, dungeonid = dungeonid, type = 'user_inventory', kwargs = {'page': page, 'bd_user': bd_user} )

        else:
            if bd_user['language_code'] == 'ru':
                show_text = '❗ | Для взаимодействия, отмените готовность!'

            else:
                show_text = "❗ | For interaction, cancel readiness!"

            bot.answer_callback_query(call.id, show_text, show_alert = True)

    def dungeon_use_item_info(bot, bd_user, call, user):

        dungeonid = int(call.data.split()[1])
        dung = dungeons.find_one({"dungeonid": dungeonid})
        dung_user = dung['users'][str(user.id)]

        data = Functions.des_qr(call.data.split()[2], True)
        it_id = str(data['item_id'])

        data_item = items_f['items'][it_id]
        user_item = None

        if data in dung['users'][str(user.id)]['inventory']:
            user_item = data

        if user_item == None:

            if bd_user['language_code'] == 'ru':
                text = f'❌ | Предмет не найден в инвентаре!'
            else:
                text = f"❌ | Item not found in inventory!"

            bot.send_message(user.id, text, reply_markup = Functions.inline_markup(bot, f'delete_message', user.id) )

        if user_item != None:

            text, image = Functions.item_info(user_item, bd_user['language_code'], mark = False)
            markup_inline = types.InlineKeyboardMarkup(row_width = 2)

            if bd_user['language_code'] == 'ru':
                inl_l = {
                    "🔮 Использовать": f'dungeon_use_item {dungeonid} {call.data.split()[2]}',
                    "🗑 Выбросить": f'dungeon_delete_item {dungeonid} {call.data.split()[2]}',
                    "⚙ Удалить сообщение": 'message_delete'
                }
                in_text = ['🔮 | Использовать', '🗑 | Выбросить', '🔁 | Передать', '🛠 | Создаваемый предмет']
            else:
                inl_l = {
                    "🔮 Use": f'dungeon_use_item {dungeonid} {call.data.split()[2]}',
                    "🗑 Delete": f'dungeon_delete_item {dungeonid} {call.data.split()[2]}',
                    "⚙ Delete a message": 'message_delete'
                }
                in_text = ['🔮 | Use', '🗑 | Delete', '🔁 | Transfer', '🛠 | Сreated item']

            markup_inline.add( *[ types.InlineKeyboardButton( text = inl, callback_data = inl_l[inl] ) for inl in inl_l.keys() ])

            bot.send_message(user.id, text, reply_markup = markup_inline, parse_mode = 'Markdown')

    def dungeon_delete_item(bot, bd_user, call, user):

        dungeonid = int(call.data.split()[1])
        dung = dungeons.find_one({"dungeonid": dungeonid})
        dung_user = dung['users'][str(user.id)]

        data = Functions.des_qr(call.data.split()[2], True)
        it_id = str(data['item_id'])

        data_item = items_f['items'][it_id]
        user_item = None

        if data in dung['users'][str(user.id)]['inventory']:
            user_item = data

        if user_item == None:

            if bd_user['language_code'] == 'ru':
                text = f'❌ | Предмет не найден в инвентаре!'
            else:
                text = f"❌ | Item not found in inventory!"

            bot.send_message(user.id, text, reply_markup = Functions.inline_markup(bot, f'delete_message', user.id) )

        if user_item != None:

            dung_user['inventory'].remove(user_item)
            dungeons.update_one( {"dungeonid": dungeonid}, {"$set": {f'users.{user.id}.inventory': dung_user['inventory'] }} )

            inf = Dungeon.message_upd(bot, userid = user.id, dungeonid = dungeonid, type = 'user_inventory', kwargs = {'page': 1, 'bd_user': bd_user} )

            if bd_user['language_code'] == 'ru':
                text = f'🗑 | Предмет был удалён!'
            else:
                text = f"🗑 | The item has been deleted!"

            bot.send_message(user.id, text, reply_markup = Functions.inline_markup(bot, f'delete_message', user.id) )

            try:
                bot.delete_message(user.id, call.message.message_id)
            except:
                pass

    def dungeon_use_item(bot, bd_user, call, user):

        dungeonid = int(call.data.split()[1])
        dung = dungeons.find_one({"dungeonid": dungeonid})
        dung_user = dung['users'][str(user.id)]

        data = Functions.des_qr(call.data.split()[2], True)
        it_id = str(data['item_id'])

        data_item = items_f['items'][it_id]
        user_item = None

        def item_use_dungeon(dino_id = None):
            dung = dungeons.find_one({"dungeonid": dungeonid})
            dung_user = dung['users'][str(user.id)]
            text = '-'
            rem_item = True

            if data_item['type'] == "ammunition":

                list_inv_id = []
                for i in dung_user['inventory']: list_inv_id.append(i['item_id'])
                standart_i_id = user_item['item_id']
                standart_index = dung_user['inventory'].index(user_item)
                csh = list_inv_id.count(standart_i_id)
                list_inv_id[standart_index] = 0

                rem_item = False

                if csh > 0:

                    two_item_ind = list_inv_id.index(standart_i_id)
                    two_item = dung_user['inventory'][two_item_ind]

                    if user_item['abilities']['stack'] + two_item['abilities']['stack'] > data_item["max_stack"]:

                        if bd_user['language_code'] == 'ru':
                            text = f'❗ | Этот набор не может быть соединён ни с одним предметом в инвентаре!'
                        else:
                            text = f"❗ | This set cannot be connected to any item in the inventory!"

                        rem_item = False

                    else:

                        preabil = {'stack': user_item['abilities']['stack'] + two_item['abilities']['stack'] }
                        dung_user['inventory'].append( Functions.get_dict_item(standart_i_id, preabil) )

                        dung_user['inventory'].remove(two_item)
                        dung_user['inventory'].remove(user_item)

                        if bd_user['language_code'] == 'ru':
                            text = f'🏹 | Предметы были соединены!'
                        else:
                            text = f"🏹 | The items were connected!"

                        dungeons.update_one( {"dungeonid": dungeonid}, {"$set": {f'users.{user.id}.inventory': dung_user['inventory'] }} )

                        inf = Dungeon.message_upd(bot, userid = user.id, dungeonid = dungeonid, type = 'user_inventory', kwargs = {'page': 1, 'bd_user': bd_user} )

                        try:
                            bot.delete_message(user.id, call.message.message_id)
                        except:
                            pass

                else:

                    if bd_user['language_code'] == 'ru':
                        text = f'❗ | В инвентаре нет предметов для соединения!'
                    else:
                        text = f"❗ | There are no items in the inventory to connect!"

                    rem_item = False

            elif data_item['type'] == "+eat":
                d_dino = json_f['elements'][ str(bd_user['dinos'][dino_id]['dino_id']) ]

                if bd_user['language_code'] == 'ru':
                    if data_item['class'] == 'ALL':

                        bd_user['dinos'][ dino_id ]['stats']['eat'] += data_item['act']

                        if bd_user['dinos'][ dino_id ]['stats']['eat'] > 100:
                            bd_user['dinos'][ dino_id ]['stats']['eat'] = 100

                        text = f"🍕 | Динозавр с удовольствием съел {data_item['name']['ru']}!\nДинозавр сыт на {bd_user['dinos'][ dino_id ]['stats']['eat']}%"


                    elif data_item['class'] == d_dino['class']:
                        bd_user['dinos'][ dino_id ]['stats']['eat'] += data_item['act']

                        if bd_user['dinos'][ dino_id ]['stats']['eat'] > 100:
                            bd_user['dinos'][ dino_id ]['stats']['eat'] = 100

                        text = f"🍕 | Динозавр с удовольствием съел {data_item['name']['ru']}!\nДинозавр сыт на {bd_user['dinos'][ dino_id ]['stats']['eat']}%"


                    else:
                        eatr = random.randint( 0, int(data_item['act'] / 2) )
                        moodr = random.randint( 1, 10 )
                        text = f"🍕 | Динозавру не по вкусу {data_item['name']['ru']}, он теряет {eatr}% сытости и {moodr}% настроения!"

                        bd_user['dinos'][ dino_id ]['stats']['eat'] -= eatr
                        bd_user['dinos'][ dino_id ]['stats']['mood'] -= moodr

                else:
                    if data_item['class'] == 'ALL':

                        bd_user['dinos'][ dino_id ]['stats']['eat'] += data_item['act']

                        if bd_user['dinos'][ dino_id ]['stats']['eat'] > 100:
                            bd_user['dinos'][ dino_id ]['stats']['eat'] = 100

                        text = f"🍕 | The dinosaur ate it with pleasure {data_item['name']['en']}!\nThe dinosaur is fed up on {bd_user['dinos'][ dino_id ]['stats']['eat']}%"

                    elif data_item['class'] == d_dino['class']:

                        bd_user['dinos'][ dino_id ]['stats']['eat'] += data_item['act']

                        if bd_user['dinos'][ dino_id ]['stats']['eat'] > 100:
                            bd_user['dinos'][ dino_id ]['stats']['eat'] = 100

                        text = f"🍕 | The dinosaur ate it with pleasure {data_item['name']['en']}!\nThe dinosaur is fed up on {bd_user['dinos'][ dino_id ]['stats']['eat']}%"

                    else:
                        eatr = random.randint( 0, int(data_item['act'] / 2) )
                        moodr = random.randint( 1, 10 )
                        text = f"🍕 | The dinosaur doesn't like {data_item['name']['en']}, it loses {eatr}% satiety and {moodr}% mood!"

                        bd_user['dinos'][ dino_id ]['stats']['eat'] -= eatr
                        bd_user['dinos'][ dino_id ]['stats']['mood'] -= moodr

                users.update_one( {"userid": bd_user['userid']}, {"$set": {f'dinos.{dino_id}': bd_user['dinos'][ dino_id ] }} )

            elif data_item['type'] in ['weapon', 'armor', 'backpack']:
                type_eq = data_item['type']
                item = None

                if type_eq in ['weapon', 'armor']:
                    item = bd_user['dinos'][dino_id]['dungeon']['equipment'][type_eq]

                    if item != None:

                        dung_user['inventory'].append(item)
                        bd_user['dinos'][dino_id]['dungeon']['equipment'][type_eq] = None

                    bd_user['dinos'][dino_id]['dungeon']['equipment'][type_eq] = user_item

                    users.update_one( {"userid": bd_user['userid']}, {"$set": {'dinos': bd_user['dinos'] }} )

                if type_eq in ['backpack']:
                    item = bd_user['user_dungeon']['equipment'][type_eq]

                    if item != None:

                        dung_user['inventory'].append(item)
                        bd_user['user_dungeon']['equipment'][type_eq] = None

                    bd_user['user_dungeon']['equipment'][type_eq] = user_item

                    users.update_one( {"userid": bd_user['userid']}, {"$set": {'user_dungeon': bd_user['user_dungeon'] }} )

                if bd_user['language_code'] == 'ru':
                    text = "🎴 | Активный предмет установлен!"
                else:
                    text = "🎴 | The active item is installed!"

            else:
                rem_item = False

                if bd_user['language_code'] == 'ru':
                    text = "❌"
                else:
                    text = "❌"

            if '+mood' in data_item.keys():
                users.update_one( {"userid": user.id}, {"$inc": {f'dinos.{dino_id}.stats.mood': data_item['+mood'] * col }} )

            if '-mood' in data_item.keys():
                users.update_one( {"userid": user.id}, {"$inc": {f'dinos.{dino_id}.stats.mood': (data_item['-mood'] * -1) * col }} )

            if '+eat' in data_item.keys():
                users.update_one( {"userid": user.id}, {"$inc": {f'dinos.{dino_id}.stats.eat': (data_item['+eat']) * col }} )

            if '-eat' in data_item.keys():
                users.update_one( {"userid": user.id}, {"$inc": {f'dinos.{dino_id}.stats.eat': (data_item['-eat'] * -1) * col }} )

            if '+energy' in data_item.keys():
                users.update_one( {"userid": user.id}, {"$inc": {f'dinos.{dino_id}.stats.unv': (data_item['+energy']) * col }} )

            if '-energy' in data_item.keys():
                users.update_one( {"userid": user.id}, {"$inc": {f'dinos.{dino_id}.stats.unv': (data_item['-energy'] * -1) * col }} )

            if '+hp' in data_item.keys():
                users.update_one( {"userid": user.id}, {"$inc": {f'dinos.{dino_id}.stats.heal': (data_item['+hp']) * col }} )

            if '-hp' in data_item.keys():
                users.update_one( {"userid": user.id}, {"$inc": {f'dinos.{dino_id}.stats.heal': (data_item['-hp']) * col }} )


            bot.send_message(user.id, text, reply_markup = Functions.inline_markup(bot, f'delete_message', user.id) )

            if rem_item == True:
                dung_user['inventory'].remove(user_item)
                dungeons.update_one( {"dungeonid": dungeonid}, {"$set": {f'users.{user.id}.inventory': dung_user['inventory'] }} )

                inf = Dungeon.message_upd(bot, userid = user.id, dungeonid = dungeonid, type = 'user_inventory', kwargs = {'page': 1, 'bd_user': bd_user} )

                try:
                    bot.delete_message(user.id, call.message.message_id)
                except:
                    pass


        if data in dung['users'][str(user.id)]['inventory']:
            user_item = data

        if user_item == None:

            if bd_user['language_code'] == 'ru':
                text = f'❌ | Предмет не найден в инвентаре!'
            else:
                text = f"❌ | Item not found in inventory!"

            bot.send_message(user.id, text, reply_markup = Functions.inline_markup(bot, f'delete_message', user.id) )

        if user_item != None:

            if data_item['type'] in ["+eat", "weapon", "armor"]:

                dins_k = dung_user['dinos'].keys()

                if len(dins_k) == 1:
                    dino_id = list(dins_k)[0]
                    item_use_dungeon(dino_id)

                elif len(dins_k) > 1:

                    if bd_user['language_code'] == 'ru':
                        text = f'🦕 | Выберите динозавра >'
                    else:
                        text = f"🦕 | Choose a dinosaur >"

                    din_n_k = {}
                    markup = types.ReplyKeyboardMarkup(resize_keyboard = True)

                    for dk in dins_k:
                        dinn = bd_user['dinos'][dk]['name']
                        din_n_k[dinn] = dk
                        markup.add(dinn)

                    markup.add('❌')


                    def dino_key(message, old_message):

                        try:
                            bot.delete_message(user.id, old_message.message_id)
                        except:
                            pass

                        try:
                            bot.delete_message(user.id, message.message_id)
                        except:
                            pass

                        if message.text in din_n_k.keys():
                            dino_id = din_n_k[message.text]
                            item_use_dungeon(dino_id)

                        else:
                            bot.send_message(user.id, '❌', reply_markup = None )


                    msg = bot.send_message(user.id, text, reply_markup = markup)
                    bot.register_next_step_handler(msg, dino_key, msg)

                else:
                    if bd_user['language_code'] == 'ru':
                        text = f'❌ | Нет динозавра который бы мог это использовать!'
                    else:
                        text = f"❌ | Item not found in inventory!"

                    bot.send_message(user.id, text, reply_markup = Functions.inline_markup(bot, f'delete_message', user.id) )

            elif data_item['type'] in ["backpack", "ammunition"]:

                item_use_dungeon()

            else:

                if bd_user['language_code'] == 'ru':
                    text = f'❌ | Этот предмет не может быть использован в подземелье!'
                else:
                    text = f"❌ | This item cannot be used in the dungeon!"

                bot.send_message(user.id, text, reply_markup = Functions.inline_markup(bot, f'delete_message', user.id))


    def dungeon_kick_member(bot, bd_user, call, user):

        dungeonid = int(call.data.split()[1])
        dung = dungeons.find_one({"dungeonid": dungeonid})
        us_dct = {}

        for m_key in dung['users'].keys():
            if int(m_key) != user.id:

                m_chat = bot.get_chat(int(m_key))
                us_dct[ m_chat.first_name ] = f'dungeon_kick {dungeonid} {m_key}'

        markup_inline = types.InlineKeyboardMarkup(row_width = 2)
        markup_inline.add( *[ types.InlineKeyboardButton(
                              text = inl,
                              callback_data = us_dct[inl] ) for inl in us_dct.keys()
                         ])

        markup_inline.add( types.InlineKeyboardButton( text = '❌', callback_data = f'dungeon.to_lobby {dungeonid}' ) )

        if bd_user['language_code'] == 'ru':
            markup_inline.add( types.InlineKeyboardButton( text = '➖ Выйти', callback_data = f'dungeon.leave_in_game_answer {dungeonid}' ) )

        else:
            markup_inline.add( types.InlineKeyboardButton( text = '➖ Leave', callback_data = f'dungeon.leave_in_game_answer {dungeonid}' ) )


        if bd_user['language_code'] == 'ru':
            text = "❌ | Исключение пользователей > "
        else:
            text = "❌ | Exclusion of users > "

        bot.edit_message_caption(text, call.message.chat.id, call.message.message_id, parse_mode = 'Markdown', reply_markup = markup_inline)
        dng, inf = Dungeon.base_upd(userid = user.id, messageid = 'kick_room', dungeonid = dungeonid, type = 'edit_last_page')

    def dungeon_kick(bot, bd_user, call, user):

        dungeonid = int(call.data.split()[1])
        k_user_id = str(call.data.split()[2])
        dung = dungeons.find_one({"dungeonid": dungeonid})

        if k_user_id in dung['users'].keys():
            user_message = dung['users'][k_user_id]['messageid']
            dng, inf = Dungeon.base_upd(userid = int(k_user_id), dungeonid = dungeonid, type = 'leave_user')

            if inf == 'leave_user':

                if bd_user['language_code'] == 'ru':
                    text = "❌ | Вы были исключены из подземелья."
                else:
                    text = "❌ | You have been excluded from the dungeon."

                bot.delete_message(int(k_user_id), user_message)
                bot.send_message(int(k_user_id), text, reply_markup = Functions.markup(bot, 'dungeon_menu', user))

                CallData.dungeon_kick_member(bot, bd_user, call, user)
                inf = Dungeon.message_upd(bot, userid = user.id, dungeonid = dungeonid, upd_type = 'all', ignore_list = [user.id])

    def dungeon_leave_in_game_answer(bot, bd_user, call, user):

        dungeonid = int(call.data.split()[1])
        k_user_id = str(user.id)
        dung = dungeons.find_one({"dungeonid": dungeonid})
        markup_inline = types.InlineKeyboardMarkup(row_width = 2)

        if bd_user['language_code'] == 'ru':

            inl_l = {'✅ Да': 'dungeon.leave_in_game',
                     '❌ Нет':  'message_delete',
                    }

            text = "🗻 | Вы уверены что хотите выйти из подземелья?"

            markup_inline.add( *[ types.InlineKeyboardButton( text = inl, callback_data = f"{inl_l[inl]} {dungeonid}") for inl in inl_l.keys() ])

        else:

            inl_l = {'✅ Yes': 'dungeon.leave_in_game',
                     '❌ No':  'message_delete',
                    }

            text = "🗻 | Are you sure you want to get out of the dungeon?"

            markup_inline.add( *[ types.InlineKeyboardButton( text = inl, callback_data = f"{inl_l[inl]} {dungeonid}") for inl in inl_l.keys() ])

        bot.send_message(user.id, text = text, parse_mode = 'Markdown', reply_markup = markup_inline)

    def dungeon_leave_in_game(bot, bd_user, call, user):

        dungeonid = int(call.data.split()[1])
        k_user_id = str(user.id)
        dung = dungeons.find_one({"dungeonid": dungeonid})

        try:
            bot.delete_message(user.id, call.message.message_id)
        except:
            pass

        if k_user_id in dung['users'].keys():
            if user.id == dungeonid:

                inf = Dungeon.message_upd(bot, dungeonid = user.id, type = 'delete_dungeon')
                kwargs = { 'save_inv': False }
                dng, inf = Dungeon.base_upd(dungeonid = user.id, type = 'delete_dungeon', kwargs = kwargs)

            else:
                dng, inf = Dungeon.base_upd(userid = int(k_user_id), dungeonid = dungeonid, type = 'leave_user')
                user_message = dung['users'][k_user_id]['messageid']

                if inf == 'leave_user':

                    if bd_user['language_code'] == 'ru':
                        text = "🗻 | Вы вышли из подземелья!"
                    else:
                        text = "🗻 | You are out of the dungeon!"

                    bot.delete_message(int(k_user_id), user_message)
                    bot.send_message(int(k_user_id), text, reply_markup = Functions.markup(bot, 'dungeon_menu', user))

                    inf = Dungeon.message_upd(bot, userid = user.id, dungeonid = dungeonid, upd_type = 'all')

    def dungeon_fork_answer(bot, bd_user, call, user):

        dungeonid = int(call.data.split()[1])
        res_n = int(call.data.split()[2]) - 1
        dung = dungeons.find_one({"dungeonid": dungeonid})
        room_n = str(dung['stage_data']['game']['room_n'])
        room = dung['floor'][room_n]

        for r_l in room['results']:
            if user.id in r_l:
                r_l.remove(user.id)

        room['results'][res_n].append(user.id)

        rs_all = 0
        for l in room['results']: rs_all += len(l)

        if rs_all >= len( dung['users'].keys() ):

            if len(room['results']) == 2:

                if len(room['results'][0]) > len(room['results'][1]):
                    new_room_type = room['poll_rooms'][0]

                elif len(room['results'][0]) == len(room['results'][1]):
                    new_room_type = room['poll_rooms'][ random.randint(0,1) ]

                else:
                    new_room_type = room['poll_rooms'][1]

            if len(room['results']) == 3:

                mx_n = max( len(room['results'][0]), len(room['results'][1]), len(room['results'][2]) )

                for i in range(0, 3):
                    if len(room['results'][i]) == mx_n:
                        new_room_type = room['poll_rooms'][i]

            dng, inf = Dungeon.base_upd(dungeonid = dungeonid, type = 'create_room', kwargs = { 'rooms_list': [room_n], 'rooms': { f'{room_n}': new_room_type } } )

            inf = Dungeon.message_upd(bot, userid = user.id, dungeonid = dungeonid, upd_type = 'all', image_update = True)

        else:

            dung['floor'][room_n]['results'] = room['results']
            dungeons.update_one( {"dungeonid": dungeonid}, {"$set": {f'floor': dung['floor'] }} )

            inf = Dungeon.message_upd(bot, userid = user.id, dungeonid = dungeonid, upd_type = 'all')

    def dungeon_safe_exit(bot, bd_user, call, user):

        dungeonid = int(call.data.split()[1])
        dung = dungeons.find_one({"dungeonid": dungeonid})
        k_user_id = str(user.id)

        if user.id == dungeonid:

            for k_user_id in dung['users'].keys():
                Dungeon.user_dungeon_stat(int(k_user_id), dungeonid)

            inf = Dungeon.message_upd(bot, dungeonid = user.id, type = 'delete_dungeon')
            ngd, inf = Dungeon.base_upd(dungeonid = user.id, type = 'delete_dungeon')

        else:

            if k_user_id in dung['users'].keys():
                user_message = dung['users'][k_user_id]['messageid']
                dng, inf = Dungeon.base_upd(userid = int(k_user_id), dungeonid = dungeonid, type = 'leave_user')

                if inf == 'leave_user':
                    dungeons.user_dungeon_stat(user.id, dungeonid)

                    if bd_user['language_code'] == 'ru':
                        text = "🗻 | Вы вышли из подземелья!"
                    else:
                        text = "🗻 | You are out of the dungeon!"

                    bot.delete_message(int(k_user_id), user_message)
                    bot.send_message(int(k_user_id), text, reply_markup = Functions.markup(bot, 'dungeon_menu', user))

                    inf = Dungeon.message_upd(bot, userid = user.id, dungeonid = dungeonid, upd_type = 'all')

    def dungeon_mine(bot, bd_user, call, user):

        dungeonid = int(call.data.split()[1])
        dung = dungeons.find_one({"dungeonid": dungeonid})
        room_n = str(dung['stage_data']['game']['room_n'])

        data_items = items_f['items']
        ob_ef = 0
        upd_items = False

        for dkey in dung['users'][str(user.id)]['dinos'].keys():
            eq_tool = bd_user['dinos'][dkey]['dungeon']['equipment']['weapon']

            if eq_tool == None:
                end_up = 0 #не убирать прочность

            else:
                data_item = data_items[ str(eq_tool['item_id']) ]
                if "effectiv" in data_item.keys():
                    ob_ef += data_item["effectiv"]
                    end_up = 1 #убирать чуть прочности

                else:
                    ob_ef += 1
                    end_up = 2 #убирать много прочности

        if str(user.id) not in dung['floor'][room_n]['users_res'].keys():
            dung['floor'][room_n]['users_res'][str(user.id)] = []

        users_res = dung['floor'][room_n]['users_res'][str(user.id)]
        mine_res = dung['floor'][room_n]['resources']
        user_dt = dung['users'][str(user.id)]
        dp_rm_res = []

        for dt_i in mine_res:

            if dt_i['min_efect'] <= ob_ef:
                dp_rm_res.append( dt_i['item'] )

        for itm in users_res:

            if itm in dp_rm_res:
                dp_rm_res.remove(itm)

        if dp_rm_res != []:

            if len(user_dt['inventory']) >= Dungeon.d_backpack(bd_user):

                if bd_user['language_code'] == 'ru':
                    show_text = '❗ | В вашем рюкзаке больше нет места! Освободите место, а после заберите награду.'

                else:
                    show_text = "❗ | There is no more space in your backpack! Make room, and then collect the reward."

            else:

                dung['floor'][room_n]['users_res'][str(user.id)].append( dp_rm_res[0] )
                dung['users'][str(user.id)]['inventory'].append( dp_rm_res[0] )

                dungeons.update_one( {"dungeonid": dungeonid}, {"$set": {f'floor.{room_n}.users_res.{user.id}': dung['floor'][room_n]['users_res'][str(user.id)] }} )

                dungeons.update_one( {"dungeonid": dungeonid}, {"$set": {f'users.{user.id}': dung['users'][str(user.id)] }} )

                data_item = data_items[ dp_rm_res[0]['item_id'] ]

                if bd_user['language_code'] == 'ru':
                    sw_text = f'⛏ | Ваши динозавры выкопали {data_item["name"]["ru"]}!'

                else:
                    sw_text = f"⛏ | Your dinosaurs dug up {data_item['name']['en']}!"

                if end_up == 1:

                    eq_tool['abilities']['endurance'] -= random.randint(1,2)
                    upd_items = True

                elif end_up == 2:

                    eq_tool['abilities']['endurance'] -= random.randint(5,15)
                    upd_items = True

                if eq_tool != None and eq_tool['abilities']['endurance'] <= 0:
                    bd_user['dinos'][dino_id]['dungeon']['equipment']['weapon'] = None
                    upd_items = True

                    if dung['settings']['lang'] == 'ru':
                        sw_text += '💢 Ваше оружие сломалось!\n'
                    else:
                        sw_text += '💢 Your weapon is broken!\n'

                if upd_items == True:
                    users.update_one( {"userid": bd_user['userid']}, {"$set": {f'dinos.{dino_id}': bd_user['dinos'][dino_id] }} )

        else:

            if bd_user['language_code'] == 'ru':
                sw_text = 'В данный момент нет материалов которые ваши динозавры способны выкопать!'

            else:
                sw_text = "At the moment there are no materials that your dinosaurs are able to dig up!"

        bot.send_message(user.id, sw_text, reply_markup = Functions.inline_markup(bot, f'delete_message', user.id) )

    def dungeon_shop_menu(bot, bd_user, call, user):

        dungeonid = int(call.data.split()[1])
        dung = dungeons.find_one({"dungeonid": dungeonid})
        room_n = str(dung['stage_data']['game']['room_n'])

        room = dung['floor'][room_n]
        products = room['products']
        data_items = items_f['items']
        inl_l = {}
        markup_inline = types.InlineKeyboardMarkup(row_width = 1)

        if dung['settings']['lang'] == 'ru':
            text = f'🛒 | Хозяин лавки приветствует тебя путник! Выбирай товар по отличной цене!\n\n💰 | Монеты: {dung["users"][str(user.id)]["coins"]}'
        else:
            text = f'🛒 | The shopkeeper greets you traveler! Choose a product at a great price!\n\n💰 | Coins: {dung["users"][str(user.id)]["coins"]}'

        for pr in products:

            data_item = data_items[ pr['item']['item_id'] ]
            if dung['settings']['lang'] == 'ru':
                inl_l[ f"{data_item['name']['ru']} — Цена: {pr['price']}" ] = f'dungeon.shop_buy {dungeonid} {Functions.qr_item_code(pr["item"])}'

            else:

                inl_l[ f"{data_item['name']['en']} — Price: {pr['price']}" ] = f'dungeon.shop_buy {dungeonid} {Functions.qr_item_code(pr["item"])}'

        inl_l['❌'] = f'dungeon.to_lobby {dungeonid}'

        markup_inline.add( *[ types.InlineKeyboardButton( text = inl, callback_data = inl_l[inl]) for inl in inl_l.keys() ] )

        bot.edit_message_caption(text, call.message.chat.id, call.message.message_id, parse_mode = 'Markdown', reply_markup = markup_inline)
        dng, inf = Dungeon.base_upd(userid = user.id, messageid = 'shop', dungeonid = dungeonid, type = 'edit_last_page')

    def dungeon_shop_buy(bot, bd_user, call, user):

        dungeonid = int(call.data.split()[1])
        dung = dungeons.find_one({"dungeonid": dungeonid})
        item_qr = call.data.split()[2]
        data = Functions.des_qr(item_qr, True )
        room_n = str(dung['stage_data']['game']['room_n'])
        user_data = dung['users'][str(user.id)]
        data_items = items_f['items']

        room = dung['floor'][room_n]
        products = room['products']
        n_pr = None

        for pr in products:

            if pr['item'] == data:
                n_pr = pr
                break

        if n_pr == None:

            if bd_user['language_code'] == 'ru':
                sw_text = 'Товар не найден, возможно его уже купил другой игрок.'

            else:
                sw_text = "The product has not been found, perhaps another player has already bought it."

            bot.send_message(user.id, sw_text, reply_markup = Functions.inline_markup(bot, f'delete_message', user.id) )

            CallData.dungeon_shop_menu(bot, bd_user, call, user)

        else:

            if n_pr['price'] > user_data['coins']:

                if bd_user['language_code'] == 'ru':
                    sw_text = 'У вас не хватает монет для покупки!'

                else:
                    sw_text = "You don't have enough coins to buy!"

                bot.send_message(user.id, sw_text, reply_markup = Functions.inline_markup(bot, f'delete_message', user.id) )

            else:

                user_data['coins'] -= n_pr['price']
                user_data['inventory'].append(n_pr['item'])
                products.remove(n_pr)

                dungeons.update_one( {"dungeonid": dungeonid}, {"$set": {f'users.{user.id}': dung['users'][str(user.id)] }} )
                dungeons.update_one( {"dungeonid": dungeonid}, {"$set": {f'floor.{room_n}': dung['floor'][room_n] }} )

                if bd_user['language_code'] == 'ru':
                    sw_text = f"🎇 | Предмет {data_items[n_pr['item']['item_id']]['name']['ru']} был приобретён!"

                else:
                    sw_text = f"🎇 | The item {data_items[n_pr['item']['item_id']]['name']['en']} has been purchased!"

                bot.send_message(user.id, sw_text, reply_markup = Functions.inline_markup(bot, f'delete_message', user.id) )

                CallData.dungeon_shop_menu(bot, bd_user, call, user)

    def rayt_lvl(bot, bd_user, call, user):

        if bd_user['language_code'] == 'ru':
            text =  f'*┌* 🎢 Рейтинг по уровню:\n'
        else:
            text =  f'*┌* 🎢 Rating by level:\n'

        rayt_list = Functions.rayt_update('check')[1]
        max_rayt_users = 10
        total = 0
        uses_list = []

        for ud in rayt_list: uses_list.append( ud['userid'] )

        if bd_user['userid'] in uses_list:
            ind = uses_list.index(bd_user['userid'])+1
        else:
            ind = '-'

        if bd_user['language_code'] == 'ru':
            text += f"*├* Ваше место в рейтинге: #{ind}\n\n"
        else:
            text += f"*├* Your place in the ranking: #{ind}\n\n"

        for ud in rayt_list:

            if total < max_rayt_users:

                try:
                    member = bot.get_chat(ud['userid'])
                    name = member.first_name
                except:
                    name = ud['userid']

                if total < max_rayt_users - 1:
                    el = '├'

                elif total == max_rayt_users - 1:
                    el = '└'

                if total == 0:
                    mm = '🥇'
                elif total == 1:
                    mm = '🥈'
                elif total == 2:
                    mm = '🥉'
                else:
                    mm = total+1

                if bd_user['language_code'] == 'ru':
                    text += f"*{el}* #{mm} *{name}*:\n      *└* Ур. {ud['lvl'][0]} Опыт {ud['lvl'][1]}\n"
                else:
                    text += f"*{el}* #{mm} *{name}*:\n      *└* Lvl {ud['lvl'][0]} Exp {ud['lvl'][1]}\n"

            else:
                break

            total += 1

        bot.send_message(call.message.chat.id, text, parse_mode = "Markdown")

    def rayt_money(bot, bd_user, call, user):

        if bd_user['language_code'] == 'ru':
            text = f'*┌* 🎢 Рейтинг по монетам:\n'
        else:
            text = f'*┌* 🎢 Coin Rating:\n'

        rayt_list = Functions.rayt_update('check')[0]
        max_rayt_users = 10
        total = 0
        uses_list = []

        for ud in rayt_list: uses_list.append( ud['userid'] )

        if bd_user['userid'] in uses_list:
            ind = uses_list.index(bd_user['userid'])+1
        else:
            ind = '-'

        if bd_user['language_code'] == 'ru':
            text += f"*├* Ваше место в рейтинге: #{ind}\n\n"
        else:
            text += f"*├* Your place in the ranking: #{ind}\n\n"

        for ud in rayt_list:

            if total < max_rayt_users:

                try:
                    member = bot.get_chat(ud['userid'])
                    name = member.first_name
                except:
                    name = ud['userid']

                if total < max_rayt_users - 1:
                    el = '├'

                elif total == max_rayt_users - 1:
                    el = '└'

                if total == 0:
                    mm = '🥇'
                elif total == 1:
                    mm = '🥈'
                elif total == 2:
                    mm = '🥉'
                else:
                    mm = total+1

                if bd_user['language_code'] == 'ru':
                    text += f"*{el}* #{mm} *{name}*:\n      *└* Монеты {ud['coins']}\n"
                else:
                    text += f"*{el}* #{mm} *{name}*:\n      *└* Coins {ud['coins']}\n"

            else:
                break

            total += 1

        bot.send_message(call.message.chat.id, text, parse_mode = "Markdown")

    def rayt_dungeon(bot, bd_user, call, user):

        rayt_list = Functions.rayt_update('check')[2]

        if bd_user['language_code'] == 'ru':
            text = f'*┌* 🗻 Рейтинг по подземельям:\n'
        else:
            text = f'*┌* 🗻 Dungeon Rating:\n'

        max_rayt_users = 10
        total = 0

        sort_l_keys = sorted([ int(i) for i in rayt_list.keys() ], reverse = True)

        for floorn in sort_l_keys:

            if total < max_rayt_users:
                lm = []

                for ud in rayt_list[str(floorn)]:

                    try:
                        member = bot.get_chat(ud)
                        name = member.first_name
                    except:
                        name = str(ud)

                    lm.append(name)

                if total < max_rayt_users - 1:
                    el = '├'

                elif total == max_rayt_users - 1:
                    el = '└'

                if total == 0:
                    mm = '🥇'
                elif total == 1:
                    mm = '🥈'
                elif total == 2:
                    mm = '🥉'
                else:
                    mm = ''

                if bd_user['language_code'] == 'ru':
                    text += f'*{el}* Этаж #{floorn}\n    *└* {mm} {", ".join(lm) }\n\n'
                else:
                    text += f'*{el}* Floor #{floorn}\n    *└* {mm} {", ".join(lm) }\n\n'


            else:
                break

            total += 1

        bot.send_message(call.message.chat.id, text, parse_mode = "Markdown")

    def complete_quest(bot, bd_user, call, user):
        q_id = int(call.data.split()[1])

        quest = None
        for qu in bd_user['user_dungeon']['quests']['activ_quests']:
            if qu['id'] == q_id:
                quest = qu
                break

        if quest == None:

            if bd_user['language_code'] == 'ru':
                text = '🎭 | Квест не найден!'
            else:
                text = '🎭 | The quest was not found!'

            bot.send_message(call.message.chat.id, text)

        else:

            if quest['time'] - time.time() > 0:

                ans, f_ans = Dungeon.check_quest(bot, bd_user, met = 'user_active', quests_type = None, kwargs = {'quest': quest} )

                if not ans:

                    if f_ans == 'n_cmp':

                        if bd_user['language_code'] == 'ru':
                            text = '🎭 | Требования квеста не были выполнены!'
                        else:
                            text = '🎭 | The quest requirements were not met!'

                    if f_ans == 'n_quests':

                        if bd_user['language_code'] == 'ru':
                            text = '🎭 | Квест не найден!'
                        else:
                            text = '🎭 | The quest was not found!'

                    bot.send_message(call.message.chat.id, text)

                else:

                    try:
                        bot.delete_message(user.id, call.message.id)
                    except Exception as e:
                        print(f"delete message-quest: {e}")

            else:

                if bd_user['language_code'] == 'ru':
                    text = '🎭 | Время для выполнения квеста закончилось, квест был передан другому пользователю!'
                else:
                    text = '🎭 | The time for completing the quest is over, the quest has been transferred to another user!'

                bot.send_message(call.message.chat.id, text)

                bd_user['user_dungeon']['quests']['activ_quests'].remove(quest)
                users.update_one( {"userid": call.message.chat.id}, {"$set": {'user_dungeon': bd_user['user_dungeon'] }} )

    def delete_quest(bot, bd_user, call, user):
        q_id = int(call.data.split()[1])

        quest = None
        for qu in bd_user['user_dungeon']['quests']['activ_quests']:
            if qu['id'] == q_id:
                quest = qu
                break

        if quest == None:

            if bd_user['language_code'] == 'ru':
                text = '🎭 | Квест не найден!'
            else:
                text = '🎭 | The quest was not found!'

            bot.send_message(call.message.chat.id, text)

        else:

            if bd_user['language_code'] == 'ru':
                text = '🎭 | Квест удалён!'
            else:
                text = '🎭 | The quest has been deleted!'

            bot.send_message(call.message.chat.id, text)

            try:
                bot.delete_message(user.id, call.message.id)
            except:
                pass

            bd_user['user_dungeon']['quests']['activ_quests'].remove(quest)
            users.update_one( {"userid": call.message.chat.id}, {"$set": {'user_dungeon': bd_user['user_dungeon'] }} )

    def dungeon_settings_start_floor(bot, bd_user, call, user):

        dungeonid = int(call.data.split()[1])
        dung = dungeons.find_one({"dungeonid": dungeonid})

        if dung != None:


            ns_res = None
            st = bd_user['user_dungeon']['statistics']

            for i in st:

                if ns_res == None:
                    ns_res = i

                else:
                    if i['end_floor'] >= ns_res['end_floor']:
                        ns_res = i

            if ns_res == None:

                if bd_user['language_code'] == 'ru':
                    show_text = '🏷 | Вы пока что не можете установить другой начальный этаж!'

                else:
                    show_text = "🏷 | You can't install another primary floor yet!"

                bot.answer_callback_query(call.id, show_text, show_alert = True)

            else:
                markup_inline = types.InlineKeyboardMarkup(row_width = 5)
                max_floor = ns_res['end_floor']
                inl_l = {}

                for i in range(1, max_floor + 1):

                    if i % 5 == 0 or i == 1:
                        inl_l[str(i)] = f'dungeon.start_floor {dungeonid} {i}'

                markup_inline.add( *[ types.InlineKeyboardButton( text = inl, callback_data = f"{inl_l[inl]} {dungeonid}") for inl in inl_l.keys() ])

                if bd_user['language_code'] == 'ru':
                    text = f'🏷 | Укажите начальный этаж:'
                    markup_inline.add( types.InlineKeyboardButton( text = '❌ Отмена', callback_data = f'dungeon.settings {dungeonid}') )

                else:
                    text = "🏷 | Specify the initial floor:"
                    markup_inline.add( types.InlineKeyboardButton( text = '❌ Cancel', callback_data = f'dungeon.settings {dungeonid}') )

                bot.edit_message_caption(text, call.message.chat.id, call.message.message_id, parse_mode = 'Markdown', reply_markup = markup_inline)

    def dungeon_start_floor(bot, bd_user, call, user):

        dungeonid = int(call.data.split()[1])
        floor = int(call.data.split()[2])
        dung = dungeons.find_one({"dungeonid": dungeonid})

        if dung != None:
            min_money = 150 + floor * 50

            for uk in dung['users']:
                us = dung['users'][uk]

                if us['coins'] < min_money:
                    us['coins'] = min_money

                    if dung['settings']['lang'] == 'ru':
                        text = f'📌 | Настройки комнаты изменены, ваш баланс монет был изменён на {min_money}'

                    else:
                        text = f'📌 | Room settings have been changed, your coin balance has been changed to {min_money}'

                    bot.send_message(int(uk), text, reply_markup = Functions.inline_markup(bot, f'delete_message', int(uk) ))

            dungeons.update_one( {"dungeonid": dungeonid}, {"$set": {f'users': dung['users'] }} )

            dungeons.update_one( {"dungeonid": dungeonid}, {"$set": {f'settings.start_floor': floor }} )
            inf = Dungeon.message_upd(bot, userid = user.id, dungeonid = dungeonid, type = 'settings')
    
    def faq(bot, bd_user, call, user):

        f_type = call.data.split()[1]

        if f_type == 'general':

            if bd_user['language_code'] == 'ru':

                text =  "*┌* 🎈 *Редкости*\n\n"
                text += "*├* События и динозавры делятся на редкости.\nЧем больше редкость, тем слаще награда.\n\n"
                text += "*┌*  1. Обычная - 50%\n*├*  2. Необычная - 25%\n*├*  3. Редкая - 15%\n*├*  4. Мистическая - 9%\n*└*  5. Легендарная - 1%\n\n"

                text += "*┌* 🕹 *Взаимодейтвия*\n\n"
                text += "*├* Для взаимодействия с динозарвом передите в `🕹 Действия`.\n\n"
                text += "*├*  1. Для того что бы покормить динозавра, вам требуется добыть пищу, нажмите на `🕹 Действия` > `🍕 Сбор пищи` и следуйте инструкциям.\n\n"
                text += "*├*  2. Для того чтобы покормить динозавра нажмите на `🕹 Действия` > `🍣 Покормить` и выберите подходящую пищу.\n\n"
                text += "*├*  3. В `🎮 Развлечения` можно выбрать игру и развлечь динозавра, чтобы поднять его настроение.\n\n"
                text += "*├*  4. В `🎑 Путешествие` можно найти разные предметы, встретить друзей и увидеть много интересного!\n\n"
                text += "*└*  5. `🌙 Уложить спать` динозавру ежедневно требуется сон, не забывайте укладывать его спать!\n\n"

                text += "*┌* 🎮 *Профиль*\n\n"
                text += "*└*  Чтобы посмотреть инвентарь или узнать свою статистику, перейдите в `👁‍🗨 Профиль`\n\n"

                text += "*┌* 🔧 *Настройки*\n\n"
                text += "*└*  В настройках вы можете переименовать динозавра, отключить уведомления или переключить язык.\n\n"

                text += "*┌* 🛒 *Рынок*\n\n"
                text += "*└*  На рынке можно продать или приобрести нужные вам вещи.\n\n"

                text += "*┌* 👥 *Друзья*\n\n"
                text += "*└*  В меню друзей вы можете управлять своими друзьями и реферальной системой. Чем больше друзей, тем болше возможностей получить какие то бонусы. Так же пригласив друга через реферальную систему, вы и ваш друг получат приятные бонусы.\n\n"

                text += "*┌* 🦕 *Количество динозавров*\n\n"
                text += "*├*  Каждый 20-ый уровень количество динозавров увеличивается на 1.\n*├*  20ый уровень - 2 динозавра.\n*└*  40ой уровень - 3 динозавра...\n\n"
            
            else:

                text =  "*┌* *Rarities*\n\n"
                text +="*├* Events and dinosaurs are divided into rarities.The greater the rarity, the sweeter the reward.\n\n"
                text+= "*┌* 1. Normal - 50%\n*├* 2. Unusual - 25%\n*├* 3. Rare - 15%\n*├* 4. Mystical - 9%\n*└* 5. Legendary - 1%\n\n"

                text += "*┌* 🕹 *Interaction*\n\n"
                text += "*├* To interact with the dinozarv, pass in `🕹 Actions`.\n\n"
                text += "*├* 1. In order to feed the dinosaur, you need to get food, click on `🕹 Actions` > `🍕 Food Collection` and follow the instructions.\n\n"
                text += "*├* 2. To feed the dinosaur, click on `🕹 Actions` > `🍣 Feed` and choose the appropriate food.\n\n"
                text += "*├* 3. In `🎮 Entertainment`, you can choose a game and entertain the dinosaur to cheer him up.\n\n"
                text += "*├* 4. In the `🎑 Journey` you can find different items, meet friends and see a lot of interesting things!\n\n"
                text += "*└* 5. `🌙 Put to bed` The dinosaur needs sleep every day, don't forget to put him to bed!\n\n"

                text += "*┌* 🎮 *Profile*\n\n"
                text+= "*└* To view inventory or find out your statistics, go to `👁🗨 Profile`\n\n"

                text += "*┌* 🔧*Settings*\n\n"
                text += "*└*  In the settings, you can rename the dinosaur, disable notifications, or switch the language.\n\n"

                text += "*┌* 🛒 *Market*\n\n"
                text += "*└* You can sell or buy the things you need on the market.\n\n"

                text += "*┌* 👥 *Friends*\n\n"
                text += "*└* In the friends menu, you can manage your friends and referral system. The more friends there are, the more opportunities there are to get some bonuses. Also, by inviting a friend through the referral system, you and your friend will receive pleasant bonuses.\n\n"

                text += "*┌* 🦕 *Number of dinosaurs*\n\n"
                text+= "*├* Every 20th level the number of dinosaurs increases by 1.\n*├* 20th level - 2 dinosaurs.\n*└* 40th level - 3 dinosaurs...\n\n"

        
        if f_type == 'eat':

            if bd_user['language_code'] == 'ru':

                text =  "*┌* 🥙 *Что кушает мой динозавр?*\n\n"
                text += "*├* Посмотрите на профиль своего динозавра, динозавры живут в своей родной среде.\n\n"
                text += "*└* Травоядные там где много трав, хищники в лесах / джунглях, а те кто любят рыбку - летают в облаках.\n\n"

                text += "*┌* 🍕 *Вкусняшки*\n\n"
                text += "*├* 🍯 Баночка мёда, 🥞 Сладкие блинчики - динозавры любят вкусняшки и независимо от их вида, они с радостью съедят их!\n\n"
                text += "*├* Так же эта еда даёт бонусы к настроению / здоровью и тд.\n\n"
                text += "*└* Всю информацию о предмете вы можете узнать в инвентаре!\n\n"
            
            else:

                text =  "*┌* 🥙 *What does my dinosaur eat?*\n\n"
                text += "*├* Look at the profile of your dinosaur, dinosaurs live in their native environment.\n\n"
                text += "*└* Herbivores where there are a lot of herbs, predators in forests / jungles, and those who love fish - fly in the clouds.\n\n"

                text += "*┌* 🍕 *Yummy*\n\n"
                text += "*├* 🍯 Jar of honey, 🥞 Sweet pancakes - dinosaurs love sweets and regardless of their kind, they will gladly eat them!\n\n"
                text += "*├* Also, this food gives bonuses to mood / health and so on.\n\n"
                text += "*└* You can find out all the information about the item in the inventory!\n\n"


        if f_type == 'accessories':

            if bd_user['language_code'] == 'ru':
        
                text =  "*┌* 🏓 *Аксессуары*\n\n"
                text += "*├*  Аксессуары открывают дополнительные возможности или ускоряют вид деятельности. \n\n"
                text += "*├*  Аксессуары можно установить пока динозавр ничего не делает в меню `👁‍🗨 Профиль`.\n\n"
                text += "*└*  Аксессуары можно найти в путешествиях или подземелье.\n\n"

                text =  "*┌* 🎲 *Вот некоторые из них...*\n\n"
                text += "*├* 🧸 Мишка - позволяет выбрать режим сна.\n\n"
                text += "*└* 🛠 Инструменты - ускоряют сбор пищи.\n\n"
            
            else:
                text =  "*┌* 🏓 *Accessories*\n\n"
                text += "*├* Accessories open up additional opportunities or accelerate the type of activity. \n\n"
                text += "*├* Accessories can be installed while the dinosaur does nothing in the menu `👁‍🗨 Profile`.\n\n"
                text += "*└* Accessories can be found in travel or dungeon.\n\n"

                text +=  "*┌* 🎲 *Here are some of them...*\n\n"
                text += "*├* 🧸 Bear - allows you to select the sleep mode.\n\n"
                text += "*└* 🛠 Tools - speed up food collection.\n\n"
        
        if f_type == 'dungeon':

            if bd_user['language_code'] == 'ru':

                text =  "*┌* 📜 *Квесты*\n\n"
                text += "*└* В таверне вы можете получить квест (просто ожидайте в ней), квесты дают интересные бонусы за самые обычные действия!\n\n"

                text += "*┌* 🗻 *Подземелья*\n\n"
                text += "*├* Отправляйтесь в захватывающее приключение вместе со своими друзьями! Приключения, боссы, уникальные предметы!\n\n"
                text += "*├* Чтобы попасть в подземелье вам нужно всего 200 монет!\n\n"
                text += "*└* Никакого начального снаряжения не нужно, а ваши динозавры в нём не могут умереть.\n\n"

                text += "*┌* 🍺 *Дино-таверна*\n\n"
                text += "*└* Загляните в `‍🍺 Дино-таверна`, там вы сможете узнать информацию от посетителей, найти других игроков. А также получить квесты!\n\n"
            
            else:

                text =  "*┌* 📜 *Quests*\n\n"
                text += "*└* In the tavern you can get a quest (just wait in it), quests give interesting bonuses for the most common actions!\n\n"

                text += "*┌* 🗻 *Dungeons*\n\n"
                text += "*├* Embark on an exciting adventure with your friends! Adventures, bosses, unique items!\n\n"
                text += "*├* To get into the dungeon you only need 200 coins!\n\n"
                text += "*└* No initial equipment is needed, and your dinosaurs can't die in it.\n\n"

                text += "*┌* 🍺 *Dino-tavern*\n\n"
                text += "*└* Take a look at the `🍺 Dino-tavern`, there you can find out information from visitors, find other players. And also get quests!\n\n"


        bot.send_message(call.message.chat.id, text, parse_mode = 'Markdown')

    def egg_use(bot, bd_user, call, user):

        if 'eggs' in bd_user.keys():

            if bd_user['egg_item'] in bd_user['inventory']:
                egg_n = bd_user['eggs'].index( call.data.split()[1] ) + 1
                data_items = items_f['items']
                data_item = data_items[ bd_user['egg_item']['item_id'] ]

                if data_item['time_tag'] == 'h':
                    inc_time = time.time() + data_item['incub_time'] * 3600

                if data_item['time_tag'] == 'm':
                    inc_time = time.time() + data_item['incub_time'] * 60

                if data_item['time_tag'] == 's':
                    inc_time = time.time() + data_item['incub_time']

                bd_user['dinos'][ Functions.user_dino_pn(bd_user) ] = {'status': 'incubation', 'incubation_time': inc_time , 'egg_id': call.data.split()[1], 'quality': data_item['inc_type']}

                bd_user['inventory'].remove( bd_user['egg_item'] )

                users.update_one( {"userid": user.id}, {"$set": {'dinos': bd_user['dinos']}} )
                users.update_one( {"userid": user.id}, {"$set": {'inventory': bd_user['inventory']}} )
                users.update_one( {"userid": user.id}, {"$unset": {'eggs': None}} )
                users.update_one( {"userid": user.id}, {"$unset": {'egg_item': None}} )

                if bd_user['language_code'] == 'ru':
                    text = f'🥚 | Выберите яйцо с динозавром!\n🦖 | Вы выбрали яйцо 🥚{egg_n}!'
                    text2 = f'🥚 | Яйцо отправлено на инкубацию!'

                else:
                    text = f'🥚 | Choose a dinosaur egg!\n🦖 | You have chosen an egg 🥚{egg_n}!'
                    text2 = f"🥚 | The egg has been sent for incubation!"

                bot.edit_message_caption(text, call.message.chat.id, call.message.message_id)
                bot.send_message(call.message.chat.id, text2, parse_mode = 'Markdown', reply_markup = Functions.markup(bot, 'profile', user))
            
            else:

                if bd_user['language_code'] == 'ru':
                    text = f'💥 | Предмет не найден в инвентаре!'

                else:
                    text = f'💥 | The item was not found in the inventory!'

                bot.send_message(call.message.chat.id, text, parse_mode = 'Markdown')
    
    def promo_activ(bot, bd_user, call, user):

        data = call.data.split()
        promo_code = data[1]
        activ = data[2]
        promo_data = management.find_one({"_id": 'promo_codes'})['codes']

        if bd_user == None:
            bd_user = { 'language_code': user.language_code }

        def message_promo_upd(promo, promo_code):
            inl_l = {}

            if promo['active']:
                inl_l['❌ Деактивировать'] = f'promo_activ {promo_code} activ'
                status = '✅'
            else:
                inl_l['✅ Активировать'] = f'promo_activ {promo_code} activ'
                status = '❌'

            inl_l['🗑 Удалить'] = f'promo_activ {promo_code} delete'
            inl_l['🎋 Использовать'] = f'promo_activ {promo_code} use'

            if promo['time_d'] != 'inf':
                if promo['time_end'] == 0:
                    txt_time = Functions.time_end( promo['time_d'], True)
                else:
                    txt_time = Functions.time_end( promo['time_end'] - int(time.time()), True)
            else:
                txt_time = promo['time_d']
            
            text = f"🔮 Промокод создан!\n\nПромокод: `{promo_code}`\nАктивность: {status}\nИспользований: {promo['col']}\nОкончание через: { txt_time }\nМонеты: {promo['money']}\n\nПредметы: {', '.join(Functions.sort_items_col(promo['items'], user.language_code) )}"

            markup_inline = types.InlineKeyboardMarkup(row_width=2)

            markup_inline.add( *[ types.InlineKeyboardButton( text = inl, callback_data = inl_l[inl]) for inl in inl_l] )

            return text, markup_inline

        if promo_code in promo_data.keys():
            promo = promo_data[promo_code]

            if activ == 'activ':

                if not promo['active']:
                    promo['active'] = True

                    if promo['time_d'] != 'inf':
                        promo['time_end'] = int(time.time()) + promo['time_d']
                 
                else:
                    promo['active'] = False
                    if promo['time_d'] != 'inf':
                        promo['time_d'] = promo['time_end'] - int(time.time())
                        promo['time_end'] = 0
                
                management.update_one( {"_id": 'promo_codes'}, {"$set": {f'codes.{promo_code}': promo }} )

                text, markup_inline = message_promo_upd(promo, promo_code)
                bot.edit_message_text(text, call.message.chat.id, call.message.message_id, reply_markup = markup_inline, parse_mode = 'markdown')
            
            if activ == 'delete':

                text = f'{promo_code} - удалено!'
                
                management.update_one( {"_id": 'promo_codes'}, {"$unset": {f'codes.{promo_code}': None}} )
                bot.edit_message_text(text, call.message.chat.id, call.message.message_id, parse_mode = 'markdown')
            
            if activ == 'use':
                
                ret_code, text = Functions.promo_use(promo_code, user)

                if ret_code in ['deactivated', 'max_col_use', 'time_end', 'alredy_use', 'no_user']:
                    bot.answer_callback_query(call.id, text, show_alert = True)
                
                else:
                    try:
                        bot.send_message(user.id, text)
                    except:
                        pass
        
        else:
            if bd_user['language_code'] == 'ru':
                text = f'🎍 | Промокод не найден, возможно он уже удалён...'
            else:
                text = f'🎍 | The promo code was not found, it may have already been deleted...'

            bot.answer_callback_query(call.id, text, show_alert = True)
