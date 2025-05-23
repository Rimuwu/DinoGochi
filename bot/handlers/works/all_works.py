from time import time

from bson import ObjectId

from bot.dbmanager import mongo_client
from bot.exec import main_router, bot
from bot.modules.dinosaur.dinosaur import Dino
from bot.modules.decorators import HDCallback, HDMessage
from bot.modules.dinosaur.works import end_work, start_bank, start_mine, start_sawmill
from bot.modules.items.item import get_items_names
from bot.modules.localization import get_data, get_lang, t
from bot.modules.markup import markups_menu as m
from bot.modules.dinosaur.mood import repeat_activity
from bot.modules.notifications import dino_notification
from bot.modules.overwriting.DataCalsses import DBconstructor
# from bot.modules.states_tools import ChooseOptionState
from bot.modules.states_fabric.state_handlers import ChooseOptionHandler
from bot.modules.user.advert import auto_ads
from bot.modules.user.user import User, last_dino
from aiogram.types import Message, CallbackQuery
from bot.modules.data_format import list_to_inline, list_to_keyboard, progress_bar

from bot.filters.translated_text import StartWith, Text
from bot.filters.states import NothingState
from bot.filters.status import DinoPassStatus
from bot.filters.private import IsPrivateChat
from bot.filters.authorized import IsAuthorizedUser
from bot.filters.kd import KDCheck
from aiogram import F

from aiogram.fsm.context import FSMContext

dinosaurs = DBconstructor(mongo_client.dinosaur.dinosaurs)
long_activity = DBconstructor(mongo_client.dino_activity.long_activity)
dino_mood = DBconstructor(mongo_client.dinosaur.dino_mood)

@HDMessage
@main_router.message(IsPrivateChat(), Text('commands_name.extraction_actions.progress'))
async def progress(message: Message):
    if not message or not message.from_user:
        return
    userid = message.from_user.id

    user = await User().create(userid)
    lang = await user.lang
    dino = await user.get_last_dino()
    chatid = message.chat.id
    status = await dino.status

    if not dino:
        await bot.send_message(chatid, t('css.no_dino', lang), reply_markup=await m(userid, 'last_menu', lang))
        return

    if status in ['bank', 'mine', 'sawmill']:
        activ = await long_activity.find_one({'activity_type': status, 'dino_id': dino._id})
        if activ:
            rmk = None
            time_ost = int(time()) - activ['start_time']
            time_end = activ['end_time'] - activ['start_time']
            time_bar = progress_bar(time_ost, time_end, 5, '⌛', '⚪', 
                                    '[', ']')

            if 'coins' in activ:
                storage_max = activ['max_coins']
                storage_now = activ['coins']
            elif 'items' in activ:
                storage_max = activ['max_items']
                storage_now = 0
                for key, item in activ['items'].items(): storage_now += item['count']

            storage_bar = progress_bar(storage_now, storage_max, 5, 
                                       *get_data(f'works.progress.{status}-emoji', lang),
                                       start_text='[', end_text=']'
                                       )

            check_max = 3
            check_now = activ['checks']
            check_bar = progress_bar(check_now, check_max, 3, '👁', '⚪', 
                                    '[', ']')

            text = t(f'works.progress.{status}', lang, time_bar=time_bar, storage_bar=storage_bar, check_bar=check_bar)
            if check_now != 0:
                rmk = list_to_inline([
                    {t('works.buttons.check', lang): f'progress_work check {dino.alt_id}'}
                ])

            await bot.send_message(chatid, text, parse_mode='Markdown', reply_markup=rmk)

@HDCallback
@main_router.callback_query(IsPrivateChat(), F.data.startswith('progress_work'))
async def progress_work(call: CallbackQuery):

    if not call or not call.message or not call.from_user or not call.data:
        return

    chatid = call.message.chat.id
    userid = call.from_user.id

    try:
        action = call.data.split()[1]
        alt_code = call.data.split()[2]
    except (IndexError, AttributeError):
        return

    lang = await get_lang(userid)
    dino = await Dino().create(alt_code)
    if not dino:
        await bot.send_message(chatid, t('css.no_dino', lang), reply_markup=await m(userid, 'last_menu', lang))
        return

    res = await long_activity.find_one(
        {'activity_type': {'$in': ['bank', 'mine', 'sawmill']}, 'dino_id': dino._id}
    )

    if res:
        if action == 'check':
            if res['checks'] != 0:
                await long_activity.update_one({'_id': res['_id']}, 
                    {'$inc': {
                        'checks': -1
                    }}
                )

                if 'coins' in res:
                    text = t('works.storage.coins', lang, 
                          coins=res['coins'],
                          max_coins=res['max_coins'])

                elif 'items' in res:
                    count = 0
                    for key, item in res['items'].items(): count += item['count']

                    text = t('works.storage.items', lang, 
                          items=get_items_names(list(res['items'].values()), lang),
                          count=count,
                          max_count=res['max_items'])

                await bot.send_message(chatid, text, parse_mode='Markdown')
                await bot.send_message(chatid, '✅', 
                           reply_markup = await m(userid, 'last_menu', lang))

@HDMessage
@main_router.message(IsPrivateChat(), Text('commands_name.extraction_actions.stop_work'))
async def stop_work(message: Message):
    userid = message.from_user.id
    user = await User().create(userid)
    lang = await user.lang
    last_dino = await user.get_last_dino()
    chatid = message.chat.id
    
    if not last_dino:
        await bot.send_message(chatid, t('css.no_dino', lang), reply_markup=await m(userid, 'last_menu', lang))
        return

    res = await long_activity.find_one(
        {'activity_type': {'$in': ['bank', 'mine', 'sawmill']}, 'dino_id': last_dino._id}
    )

    if res:
        if 'coins' in res:
            text = t('works.stop.coins', lang, coins=res['coins'])

        elif 'items' in res:
            text = t('works.stop.items', lang, items=get_items_names(list(res['items'].values()), lang))

        await end_work(last_dino._id)
        await dino_notification(last_dino._id, 
                                f'{res["activity_type"]}_end', 
                                results=text
                                )
    else:
        await bot.send_message(chatid, "❌", reply_markup = await m(userid, 'last_menu', lang))


@HDMessage
@main_router.message(IsPrivateChat(), Text('commands_name.extraction_actions.mine'), 
                     DinoPassStatus())
async def mine(message: Message):
    userid = message.from_user.id
    user = await User().create(userid)
    lang = await user.lang
    last_dino = await user.get_last_dino()
    chatid = message.chat.id
    
    if not last_dino:
        await bot.send_message(chatid, t('css.no_dino', lang), reply_markup=await m(userid, 'last_menu', lang))
        return

    options = {
        t('works.buttons.coins', lang): 'coins',
        t('works.buttons.ore', lang): 'ore'
    }

    rmk = list_to_keyboard([list(options.keys()),
                            t('buttons_name.cancel', lang)
                            ]
                           )
    text = t('works.choosy_type', lang)

    transmitted_data = {
        'last_dino': last_dino._id
    }

    # await ChooseOptionState(end_mine, userid, chatid, lang, options, transmitted_data)
    await ChooseOptionHandler(end_mine, userid, chatid, lang, options,
                              transmitted_data).start()
    await bot.send_message(chatid, text, reply_markup=rmk)

async def end_mine(data, transmitted_data: dict):
    userid = transmitted_data['userid']
    chatid = transmitted_data['chatid']
    lang = transmitted_data['lang']
    last_dino_id: ObjectId = transmitted_data['last_dino']
    last_dino = await Dino().create(last_dino_id)
    if not last_dino:
        await bot.send_message(chatid, t('css.no_dino', lang), reply_markup=await m(userid, 'last_menu', lang))
        return

    percent, _ = await last_dino.memory_percent('action', 'mine', True)
    await repeat_activity(last_dino._id, percent)

    await start_mine(last_dino._id, userid, data)
    text = t('works.start.mine', lang)
    mes = await bot.send_message(chatid, text, parse_mode='Markdown',
                           reply_markup = await m(userid, 'last_menu', lang))

    await auto_ads(mes)

@HDMessage
@main_router.message(IsPrivateChat(), StartWith('commands_name.extraction_actions.bank'), 
                     DinoPassStatus())
async def bank(message: Message):
    userid = message.from_user.id
    user = await User().create(userid)
    lang = await user.lang
    last_dino = await user.get_last_dino()
    chatid = message.chat.id
    
    if not last_dino:
        await bot.send_message(chatid, t('css.no_dino', lang), reply_markup=await m(userid, 'last_menu', lang))
        return

    options = {
        t('works.buttons.coins', lang): 'coins',
        t('works.buttons.recipes', lang): 'recipes'
    }

    rmk = list_to_keyboard([list(options.keys()),
                            t('buttons_name.cancel', lang)
                            ]
                           )
    text = t('works.choosy_type', lang)

    transmitted_data = {
        'last_dino': last_dino._id
    }

    # await ChooseOptionState(end_bank, userid, chatid, lang, options, transmitted_data)
    await ChooseOptionHandler(end_bank, userid, chatid, lang, options,
                              transmitted_data).start()
    await bot.send_message(chatid, text, reply_markup=rmk)

async def end_bank(data, transmitted_data: dict):
    userid = transmitted_data['userid']
    chatid = transmitted_data['chatid']
    lang = transmitted_data['lang']
    last_dino_id: ObjectId = transmitted_data['last_dino']
    last_dino = await Dino().create(last_dino_id)
    if not last_dino:
        await bot.send_message(chatid, t('css.no_dino', lang), reply_markup=await m(userid, 'last_menu', lang))
        return

    percent, _ = await last_dino.memory_percent('action', 'bank', True)
    await repeat_activity(last_dino._id, percent)

    await start_bank(last_dino._id, userid, data)
    text = t('works.start.bank', lang)
    mes = await bot.send_message(chatid, text, parse_mode='Markdown',
                           reply_markup = await m(userid, 'last_menu', lang))

    await auto_ads(mes)

@HDMessage
@main_router.message(IsPrivateChat(), StartWith('commands_name.extraction_actions.sawmill'), 
                     DinoPassStatus())
async def sawmill(message: Message):
    userid = message.from_user.id
    user = await User().create(userid)
    lang = await user.lang
    last_dino = await user.get_last_dino()
    chatid = message.chat.id
    
    if not last_dino:
        await bot.send_message(chatid, t('css.no_dino', lang), reply_markup=await m(userid, 'last_menu', lang))
        return

    options = {
        t('works.buttons.coins', lang): 'coins',
        t('works.buttons.wood', lang): 'wood'
    }

    rmk = list_to_keyboard([list(options.keys()),
                            t('buttons_name.cancel', lang)
                            ]
                           )
    text = t('works.choosy_type', lang)

    transmitted_data = {
        'last_dino': last_dino._id
    }

    # await ChooseOptionState(end_sawmill, userid, chatid, lang, options, transmitted_data)
    await ChooseOptionHandler(end_sawmill, userid, chatid, lang, options,
                              transmitted_data).start()
    await bot.send_message(chatid, text, reply_markup=rmk)

async def end_sawmill(data, transmitted_data: dict):
    userid = transmitted_data['userid']
    chatid = transmitted_data['chatid']
    lang = transmitted_data['lang']
    last_dino_id: ObjectId = transmitted_data['last_dino']
    last_dino = await Dino().create(last_dino_id)
    if not last_dino:
        await bot.send_message(chatid, t('css.no_dino', lang), reply_markup=await m(userid, 'last_menu', lang))
        return

    percent, _ = await last_dino.memory_percent('action', 'sawmill', True)
    await repeat_activity(last_dino._id, percent)

    await start_sawmill(last_dino._id, userid, data)
    text = t('works.start.sawmill', lang)
    mes = await bot.send_message(chatid, text, parse_mode='Markdown',
                           reply_markup = await m(userid, 'last_menu', lang))

    await auto_ads(mes)