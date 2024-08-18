from time import time
from telebot.types import CallbackQuery
from bot.exec import bot
from bot.modules.data_format import list_to_inline, seconds_to_str
from bot.modules.decorators import HDCallback, HDMessage
from bot.modules.dinosaur.dinosaur import Dino
from bot.modules.items.item import get_items_names
from bot.modules.localization import get_lang
from bot.modules.localization import t
from bot.modules.states_tools import ChoosePagesState

from bot.config import conf, mongo_client

from bot.modules.overwriting.DataCalsses import DBconstructor
users = DBconstructor(mongo_client.user.users)
item_craft = DBconstructor(mongo_client.items.item_craft)

@bot.message_handler(pass_bot=True, commands=['craftlist'], private=True)
@HDMessage
async def craftlist(message):
    chatid = message.chat.id
    userid = message.from_user.id
    lang = await get_lang(message.from_user.id)

    options = {}
    crafts = await item_craft.find({'userid': userid})

    a = -1
    for craft in crafts:
        name = get_items_names(craft['items'], lang)
        if name in options:
            a += 1
            name += f' #{a}'
        options[name] = craft['_id']
    if options:
        await ChoosePagesState(info_craft, userid, chatid, lang, options, one_element=False, autoanswer=False)
    else:
        await bot.send_message(chatid, '❌')

async def info_craft(data, transmitted_data: dict):
    chatid = transmitted_data['chatid']
    lang = transmitted_data['lang']

    craft = await item_craft.find_one({'_id': data})
    if craft:
        alt_code = craft['alt_code']
        b_l = []
        b_l.append({
                t('time_craft.cancel', lang): f'time_craft {alt_code} send_dino'
            })

        if craft['dino_id']:
            dino_acc = await Dino().create()
            name = dino_acc.name
        else:
            name = '-'
            b_l.append({
                t('time_craft.button', lang): f'time_craft {alt_code} cancel_craft'
            })

        mrk = list_to_inline(b_l)
        info = t('time_craft.craft_info', lang,
                 items=get_items_names(craft['items'], lang),
                 craft_time=seconds_to_str(craft['time_end'] - int(time()), lang, False, 'minute'),
                 dino=name
                 )
        await bot.send_message(chatid, info, parse_mode='Markdown',
                               reply_markup=mrk)

@bot.callback_query_handler(pass_bot=True, func=lambda call: call.data.startswith('transformation'), is_authorized=True)
@HDCallback
async def transformation(callback: CallbackQuery):
    chatid = callback.message.chat.id
    userid = callback.from_user.id
    lang = await get_lang(callback.from_user.id)
    data = callback.data.split()

    alt_code = data[1]
    action = data[2]

    if action == 'send_dino':
        ...
    elif action == 'cancel_craft':
        ...