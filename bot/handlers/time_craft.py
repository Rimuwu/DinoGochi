from time import time
from aiogram.types import CallbackQuery
from bson import ObjectId
from bot.exec import main_router, bot
from bot.modules.data_format import list_to_inline, seconds_to_str
from bot.modules.decorators import HDCallback, HDMessage
from bot.modules.dinosaur.dinosaur import Dino
from bot.modules.items.item import get_items_names
from bot.modules.items.time_craft import dino_craft, stop_craft
from bot.modules.localization import get_lang
from bot.modules.localization import t
# from bot.modules.states_tools import ChooseDinoState, ChoosePagesState
from bot.modules.markup import markups_menu as m

from bot.config import conf
from bot.dbmanager import mongo_client

from bot.filters.translated_text import StartWith, Text
from bot.filters.states import NothingState
from bot.filters.status import DinoPassStatus
from bot.filters.private import IsPrivateChat
from bot.filters.authorized import IsAuthorizedUser
from bot.filters.kd import KDCheck
from bot.filters.admin import IsAdminUser
from aiogram import F
from aiogram.filters import Command, StateFilter

from aiogram.fsm.context import FSMContext

from bot.modules.overwriting.DataCalsses import DBconstructor
from bot.modules.states_fabric.state_handlers import ChooseDinoHandler, ChoosePagesStateHandler
users = DBconstructor(mongo_client.user.users)
item_craft = DBconstructor(mongo_client.items.item_craft)

@HDMessage
@main_router.message(Command(commands=['craftlist']), IsPrivateChat())
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
        # await ChoosePagesState(info_craft, userid, chatid, lang, options, one_element=False, autoanswer=False)
        await ChoosePagesStateHandler(info_craft, userid, chatid, lang, options, one_element=False, autoanswer=False).start()
    else:
        await bot.send_message(chatid, '❌')

async def info_craft(data, transmitted_data: dict):
    chatid = transmitted_data['chatid']
    lang = transmitted_data['lang']

    portable = False
    if 'portable' in transmitted_data:
        portable = transmitted_data['portable']

    if not portable:
        craft = await item_craft.find_one({'_id': data})
    else:
        craft = await item_craft.find_one({'alt_code': data})

    if craft:
        alt_code = craft['alt_code']
        b_l = []
        b_l.append({
                t('time_craft.cancel', lang): f'time_craft {alt_code} cancel_craft'
            })

        if craft['dino_id']:
            dino_acc = await Dino().create(craft['dino_id'])
            if dino_acc:
                name = dino_acc.name
            else:
                craft['dino_id'] = None

        if not craft['dino_id']:
            name = '-'
            b_l.append({
                t('time_craft.button', lang): f'time_craft {alt_code} send_dino'
            })

        mrk = list_to_inline(b_l)
        info = t('time_craft.craft_info', lang,
                 items=get_items_names(craft['items'], lang),
                 craft_time=seconds_to_str(craft['time_end'] - int(time()), lang, False, 'minute'),
                 dino=name
                 )

        if not portable:
            await bot.send_message(chatid, info, parse_mode='Markdown',
                               reply_markup=mrk)
        else:
            return info, mrk

@HDCallback
@main_router.callback_query(F.data.startswith('time_craft'), IsAuthorizedUser())
async def time_craft(callback: CallbackQuery):
    chatid = callback.message.chat.id
    userid = callback.from_user.id
    lang = await get_lang(callback.from_user.id)
    data = callback.data.split()

    alt_code = data[1]
    action = data[2]

    if action == 'send_dino':
        transmitted_data = {'ms_id': callback.message.message_id, 'alt_code': alt_code}
        # await ChooseDinoState(send_dino_to_craft, userid, chatid, 
        #                       lang, False, False, transmitted_data)
        await ChooseDinoHandler(send_dino_to_craft, userid, chatid,
                               lang, False, False, 
                               transmitted_data,
                               status_filter='pass').start()

    elif action == 'cancel_craft':
        await stop_craft(alt_code)
        await bot.delete_message(chatid, callback.message.message_id)

async def send_dino_to_craft(dino_id: ObjectId, transmitted_data: dict):
    chatid = transmitted_data['chatid']
    userid = transmitted_data['userid']
    lang = transmitted_data['lang']
    ms_id = transmitted_data['ms_id']
    alt_code = transmitted_data['alt_code']

    dino = await Dino().create(dino_id)
    if not dino:
        await bot.send_message(chatid, t('dino_not_found', lang), parse_mode='Markdown',
                            reply_markup= await m(userid, 'last_menu', lang))
        return

    if await dino.status == 'pass':
        st, pers = await dino_craft(dino._id, alt_code)
        if st:
            text = t('time_craft.send_dino', lang, percent=pers)

            transmitted_data = {
                'portable': True,
                'chatid': chatid,
                'lang': lang
            }
            info, mrk = await info_craft(alt_code, transmitted_data) # type: ignore
            try:
                await bot.edit_message_text(info, None, chatid, ms_id, reply_markup=mrk, parse_mode='Markdown')
            except: pass

            await bot.send_message(chatid, text, parse_mode='Markdown',
                                reply_markup=await m(userid, 'last_menu', lang))

        else:
            await bot.send_message(chatid, "❌", parse_mode='Markdown', 
                            reply_markup= await m(userid, 'last_menu', lang))
    else:
        await bot.send_message(chatid,t('alredy_busy', lang), parse_mode='Markdown', 
                            reply_markup= await m(userid, 'last_menu', lang))