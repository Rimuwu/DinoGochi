import telebot
from telebot import types
import config
import random
import json
import pymongo

bot = telebot.TeleBot(config.TOKEN)

client = pymongo.MongoClient(config.CLUSTER_TOKEN)
users = client.bot.users

with open('../images/dino_data.json') as f:
    json_f = json.load(f)

def markup(element = 1, message = None):
    markup = types.ReplyKeyboardMarkup(resize_keyboard = True)
    user = message.from_user

    if element == 1 and users.find_one({"userid": user.id}) != None:

        if user.language_code == 'ru':
            nl = ['🦖 Динозавр', '🎢 Рейтинг']
        else:
            nl = ['🦖 Dinosaur', '🎢 Rating']

        item1 = types.KeyboardButton(nl[0])
        item2 = types.KeyboardButton(nl[1])

        markup.add(item1, item2)

    elif element == 1:

        if user.language_code == 'ru':
            nl = ['🍡 Начать играть']
        else:
            nl = ['🍡 Start playing']

        item1 = types.KeyboardButton(nl[0])

        markup.add(item1)

    return markup


@bot.message_handler(commands=['start', 'help'])
def on_start(message):
    user = message.from_user
    if user.language_code == 'ru':
        text = f"🎋 | Хей <b>{user.first_name}</b>, рад приветствовать тебя!\n"
        f"<b>•</b> Я маленький игровой бот по типу тамагочи, только с динозаврами!🦖\n\n"
        f"<b>🕹 | Что такое тамагочи?</b>\n"
        f'<b>•</b> Тамагочи - игра с виртуальным питомцем, которого надо кормить, ухаживать за ним, играть и тд.🥚\n'
        f"<b>•</b> Соревнуйтесь в рейтинге и станьте лучшим!\n\n"
        f"<b>🎮 | Как начать играть?</b>\n"
        f'<b>•</b> Нажмите кномку <b>🍡 Начать играть</b>!\n\n'
        f'<b>❤ | Ждём в игре!</b>\n'
    else:
        text = f"🎋 | Hey <b>{user.first_name}</b>, I am glad to welcome you!\n"
        f"<b>•</b> I'm a small tamagotchi-type game bot, only with dinosaurs!🦖\n\n"
        f"<b>🕹 | What is tamagotchi?</b>\n"
        f'<b>•</b> Tamagotchi is a game with a virtual pet that needs to be fed, cared for, played, and so on.🥚\n'
        f"<b>•</b> Compete in the ranking and become the best!\n\n"
        f"<b>🎮 | How to start playing?</b>\n"
        f'<b>•</b> Press the button <b>🍡Start playing</b>!\n\n'
        f'<b>❤ | Waiting in the game!</b>\n'
        f'<b>❗ | In some places, the bot may not be translated!</b>\n'

    bot.reply_to(message, text, reply_markup = markup(message = message), parse_mode = 'html')


@bot.message_handler(content_types = ['text'])
def on_message(message):
    user = message.from_user

    if message.chat.type == 'private':

        if message.text in ['🍡 Начать играть', '🍡 Start playing']:
            if users.find_one({"userid": user.id}) == None:
                users.insert_one({'userid': user.id, 'dinos': {}})
                bot.reply_to(message, 'start!',reply_markup = markup(message = message))

# @bot.message_handler(commands=['random'])
# def random_command(message):
#     rid = str(random.choice(list(json_f['data']['egg'])))
#     image_d = str(json_f['elements'][rid]['image'])
#     photo = open(f"../images/{image_d}", 'rb')
#     bot.send_photo(message.chat.id, photo)
#

print(f'Бот {bot.get_me().first_name} запущен!')
bot.infinity_polling(none_stop = True)
