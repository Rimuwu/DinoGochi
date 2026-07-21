from bot.models.dinosaur import Dino, DinoMood
from time import time

from bson import ObjectId

from bot.exec import main_router, bot
from bot.models.dinosaur import Dino
from bot.models.activity import WorkActivity, Activity
from bot.modules.items.item import get_items_names
from bot.modules.localization import get_data, get_lang, t
from bot.modules.markup import markups_menu as m
from bot.modules.notifications import dino_notification
from bot.modules.states_fabric.state_handlers import ChooseOptionHandler
from bot.modules.user.advert import auto_ads
from bot.modules.user.user import User
from aiogram.types import Message, CallbackQuery
from bot.modules.data_format import list_to_inline, list_to_keyboard, progress_bar

from bot.filters.translated_text import StartWith, Text
from bot.filters.status import DinoPassStatus
from bot.filters.private import IsPrivateChat
from aiogram import F

@main_router.message(
    IsPrivateChat(), Text('commands_name.extraction_actions.progress'))
async def progress(message: Message):
    if not message or not message.from_user:
        return

    userid = message.from_user.id

    user = await User().create(userid)
    lang = await user.lang
    dino = await user.get_last_dino()
    chatid = message.chat.id

    if not dino:
        await bot.send_message(chatid, t('css.no_dino', lang), reply_markup=await m(userid, 'last_menu', lang))
        return

    status = await dino.status
    status = status.value

    if status in ['bank', 'mine', 'sawmill']:
        activ = await Activity.find_one(
            Activity.activity_type == status,
            Activity.dino.id == dino.id
        )
        if activ:
            activ_dict = activ.dict()
            rmk = None
            time_ost = int(time()) - activ_dict['start_time']
            time_end = activ_dict['end_time'] - activ_dict['start_time']
            time_bar = progress_bar(time_ost, time_end, 5, '⌛', '⚪', 
                                    '[', ']')

            storage_max = 1
            storage_now = 0
            if activ_dict.get('coins') is not None:
                storage_max = activ_dict.get('max_coins') or 1
                storage_now = activ_dict.get('coins') or 0
            elif activ_dict.get('items') is not None:
                storage_max = activ_dict.get('max_items') or 1
                storage_now = 0
                for key, item in activ_dict['items'].items(): storage_now += item['count']

            emoji_data = get_data(f'works.progress.{status}-emoji', lang)
            if not isinstance(emoji_data, list) or len(emoji_data) < 2:
                emoji_data = ['🍕', '⚪']
            storage_bar = progress_bar(storage_now, storage_max, 5, 
                                       emoji_data[0], emoji_data[1],
                                       start_text='[', end_text=']'
                                       )

            check_max = 3
            check_now = activ_dict['checks']
            check_bar = progress_bar(check_now, check_max, 3, '👁', '⚪', 
                                    '[', ']')

            text = t(f'works.progress.{status}', lang, time_bar=time_bar, storage_bar=storage_bar, check_bar=check_bar)
            if check_now != 0:
                rmk = list_to_inline([
                    {t('works.buttons.check', lang): f'progress_work check {dino.alt_id}'}
                ])

            await bot.send_message(chatid, text, reply_markup=rmk)

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

    from beanie.operators import In
    res = await Activity.find_one(
        In(Activity.activity_type, ['bank', 'mine', 'sawmill']),
        Activity.dino.id == dino.id
    )

    if res:
        res_dict = res.dict()
        if action == 'check':
            if res_dict['checks'] != 0:
                await res.update({'$inc': {'checks': -1}})

                if res_dict.get('coins') is not None:
                    text = t('works.storage.coins', lang, 
                          coins=res_dict['coins'],
                          max_coins=res_dict['max_coins'])

                elif res_dict.get('items') is not None:
                    count = 0
                    for key, item in res_dict['items'].items(): count += item['count']

                    text = t('works.storage.items', lang, 
                          items=get_items_names(list(res_dict['items'].values()), lang),
                          count=count,
                          max_count=res_dict['max_items'])

                await bot.send_message(chatid, text, 
                           reply_markup = await m(userid, 'last_menu', lang))

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

    from beanie.operators import In
    res = await Activity.find_one(
        In(Activity.activity_type, ['bank', 'mine', 'sawmill']),
        Activity.dino.id == last_dino.id
    )

    if res:
        res_dict = res.dict()
        if res_dict.get('coins') is not None:
            text = t('works.stop.coins', lang, coins=res_dict['coins'])

        elif res_dict.get('items') is not None:
            text = t('works.stop.items', lang, items=get_items_names(list(res_dict['items'].values()), lang))

        await WorkActivity.end_work(last_dino.id)
        await dino_notification(last_dino.id, 
                                f'{res.activity_type}_end', 
                                results=text
                                )
        await bot.send_message(chatid, t('back_text.extraction_actions_menu', lang), reply_markup=await m(userid, 'extraction_actions_menu', lang))
    else:
        await bot.send_message(chatid, "❌", reply_markup = await m(userid, 'last_menu', lang))


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
    await DinoMood.repeat_activity(last_dino._id, percent)

    await WorkActivity.start_mine(last_dino._id, userid, data)
    text = t('works.start.mine', lang)
    mes = await bot.send_message(chatid, text,
                           reply_markup = await m(userid, 'last_menu', lang))

    await auto_ads(mes)

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
    await DinoMood.repeat_activity(last_dino._id, percent)

    await WorkActivity.start_bank(last_dino._id, userid, data)
    text = t('works.start.bank', lang)
    mes = await bot.send_message(chatid, text,
                           reply_markup = await m(userid, 'last_menu', lang))

    await auto_ads(mes)

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
    await DinoMood.repeat_activity(last_dino._id, percent)

    await WorkActivity.start_sawmill(last_dino._id, userid, data)
    text = t('works.start.sawmill', lang)
    mes = await bot.send_message(chatid, text,
                           reply_markup = await m(userid, 'last_menu', lang))

    await auto_ads(mes)