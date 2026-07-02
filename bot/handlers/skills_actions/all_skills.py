from bot.modules.overwriting.DataCalsses import LazyCollection
from bot.models.dinosaur import State, Dino, DinoMood
from bot.models.activity import Activity

from time import time

from bot.dbmanager import mongo_client
from bot.exec import main_router, bot
from bot.modules.dinosaur.dino_status import end_skill_activity, get_skill_time, start_skill_activity
from bot.models.dinosaur import Dino
from bot.models.activity import KDActivity
from bot.models.dinosaur import Dino
from bot.modules.decorators import HDCallback, HDMessage
from bot.modules.localization import get_lang, t
from bot.modules.markup import markups_menu as m
from bot.modules.notifications import dino_notification
from bot.modules.user.advert import auto_ads
from bot.modules.user.user import User
from aiogram.types import Message, CallbackQuery
from bot.modules.data_format import list_to_inline, seconds_to_str

from bot.filters.translated_text import Text, StartWith
from bot.filters.states import NothingState
from bot.filters.status import DinoPassStatus
from bot.filters.private import IsPrivateChat
from bot.filters.authorized import IsAuthorizedUser
from bot.filters.kd import KDCheck
from aiogram import F

dinosaurs = LazyCollection(Dino)
long_activity = LazyCollection(Activity)
dino_mood = LazyCollection(DinoMood)

async def use_energy(chatid, lang, alt_code, messageid = 0):
    res = await long_activity.find_one(
        {'alt_code': alt_code})
    if res:
        text = t(f'all_skills.use_energy.text', lang)
        buttons = [
            {
                t(f'all_skills.use_energy.buttons.{int(res["use_energy"])}', lang): f'use_energy {alt_code}'
            },
            {
                t('all_skills.use_boost_button', lang, default='⚡ Бустер тренировки'): f'use_training_boost {alt_code}'
            }
        ]
        mrk = list_to_inline(buttons)
        text = t(f'all_skills.use_energy.text', lang)
        if not messageid:
            await bot.send_message(chatid, text, parse_mode='Markdown',
            reply_markup=mrk)
        else:
            await bot.edit_message_text(
                text, None, chatid, messageid, reply_markup=mrk,
                parse_mode='Markdown'
            )
            
skills_data = {
    'gym': {
        'kd': 3600 * 8,
        'skills': ['power', 'dexterity'],
        'units': [[0.01, 0.015], [0.005, 0.007]]
    },
    'library': {
        'kd': 3600 * 12,
        'skills': ['intelligence', 'power'],
        'units': [[0.01, 0.015], [0.005, 0.007]]
    },
    'park': {
        'kd': 3600 * 4,
        'skills': ['charisma', 'intelligence'],
        'units': [[0.01, 0.015], [0.005, 0.007]]
    },
    'swimming_pool': {
        'kd': 3600 * 16,
        'skills': ['dexterity', 'charisma'],
        'units': [[0.01, 0.015], [0.005, 0.007]]
    }
}

async def start_skill(last_dino: Dino, userid, chatid, lang, skill):
    await KDActivity.save_kd(last_dino._id, skill, skills_data[skill]['kd'])
    percent, _ = await last_dino.memory_percent('action', skill, True)
    await DinoMood.repeat_activity(last_dino._id, percent)

    res = await start_skill_activity(
        last_dino._id, skill, 
        *skills_data[skill]['skills'],
        *skills_data[skill]['units'], sended=userid
    )

    tran_time = get_skill_time(skill)[0]
    text = t(f'all_skills.{skill}', lang, 
             min_time=seconds_to_str(tran_time, lang))
    mes = await bot.send_message(chatid, text, parse_mode='Markdown',
        reply_markup=await m(userid, 'last_menu', lang))

    alt_code = res['alt_code']
    await use_energy(chatid, lang, alt_code)
    await auto_ads(mes)

@HDMessage
@main_router.message(IsPrivateChat(), StartWith('commands_name.skills_actions.gym'), DinoPassStatus(), KDCheck('gym'))
async def gym(message: Message):
    userid = message.from_user.id
    user = await User().create(userid)
    lang = await user.lang
    last_dino = await user.get_last_dino()
    chatid = message.chat.id
    
    if not last_dino:
        await bot.send_message(chatid, t('css.no_dino', lang), reply_markup=await m(userid, 'last_menu', lang))
        return

    await start_skill(last_dino, userid, chatid, lang, 'gym')

@HDMessage
@main_router.message(IsPrivateChat(), StartWith('commands_name.skills_actions.library'), DinoPassStatus(), KDCheck('library'))
async def library(message: Message):
    userid = message.from_user.id
    user = await User().create(userid)
    lang = await user.lang
    last_dino = await user.get_last_dino()
    chatid = message.chat.id

    if not last_dino:
        await bot.send_message(chatid, t('css.no_dino', lang), reply_markup=await m(userid, 'last_menu', lang))
        return

    await start_skill(last_dino, userid, chatid, lang, 'library')

@HDMessage
@main_router.message(IsPrivateChat(), StartWith('commands_name.skills_actions.park'), DinoPassStatus(), KDCheck('park'))
async def park(message: Message):
    userid = message.from_user.id
    user = await User().create(userid)
    lang = await user.lang
    last_dino = await user.get_last_dino()
    chatid = message.chat.id
    
    if not last_dino:
        await bot.send_message(chatid, t('css.no_dino', lang), reply_markup=await m(userid, 'last_menu', lang))
        return

    await start_skill(last_dino, userid, chatid, lang, 'park')

@HDMessage
@main_router.message(IsPrivateChat(), StartWith('commands_name.skills_actions.swimming_pool'), DinoPassStatus(), KDCheck('swimming_pool'))
async def swimming_pool(message: Message):
    userid = message.from_user.id
    user = await User().create(userid)
    lang = await user.lang
    last_dino = await user.get_last_dino()
    chatid = message.chat.id
    
    if not last_dino:
        await bot.send_message(chatid, t('css.no_dino', lang), reply_markup=await m(userid, 'last_menu', lang))
        return

    await start_skill(last_dino, userid, chatid, lang, 'swimming_pool')

@HDMessage
@main_router.message(IsPrivateChat(), StartWith('commands_name.skills_actions.stop_work'))
async def stop_work(message: Message):
    userid = message.from_user.id
    user = await User().create(userid)
    lang = await user.lang
    last_dino = await user.get_last_dino()
    chatid = message.chat.id
    
    if not last_dino:
        await bot.send_message(chatid, t('css.no_dino', lang), reply_markup=await m(userid, 'last_menu', lang))
        return

    if await last_dino.status in ['gym', 'library', 'park', 'swimming_pool']:

        mrk = list_to_inline([
            {t('all_skills.stoping.button', lang): 'stop_work'}
        ])
        await bot.send_message(chatid, 
            t('all_skills.stoping.text', lang), 
            reply_markup = mrk,
            parse_mode = 'Markdown'
        )

    else:
        await bot.send_message(chatid, '❌', parse_mode='Markdown', reply_markup=await m(userid, 'last_menu', lang))


@HDCallback
@main_router.callback_query(IsPrivateChat(), F.data.startswith('stop_work'))
async def stop_work_calb(call: CallbackQuery):
    userid = call.from_user.id
    chatid = call.message.chat.id
    lang = await get_lang(userid)
    user = await User().create(userid)
    last_dino = await user.get_last_dino()
    messageid = call.message.message_id
    dino_id = last_dino._id
    
    if not last_dino:
        await bot.send_message(chatid, t('css.no_dino', lang), reply_markup=await m(userid, 'last_menu', lang))
        return

    res = await long_activity.find_one(
        {'dino_id': dino_id, 
         'activity_type': {'$in': ['gym', 'library', 'swimming_pool', 'park']}
         })

    if res and messageid: 
        traning_time = int(time()) - res['start_time']
        way = ''

        unit_percent = res['up']
        if traning_time < res['min_time']:
            unit_percent = res['up'] / 2
            await Dino.add_skill_point(dino_id, res['up_skill'], -unit_percent)
            way = '_negative'

        await dino_notification(dino_id, res['activity_type'] + '_end' + way, 
                                add_unit=round(unit_percent, 4))
        await end_skill_activity(dino_id)
        await bot.delete_message(chatid, messageid)
        await bot.send_message(chatid, t('back_text.skills_actions_menu', lang), reply_markup=await m(userid, 'skills_actions_menu', lang))

@HDCallback
@main_router.callback_query(IsPrivateChat(), F.data.startswith('use_energy'))
async def use_energy_calb(call: CallbackQuery):

    alt_code = call.data.split()[1]
    chatid = call.message.chat.id
    userid = call.from_user.id
    messageid = call.message.message_id
    lang = await get_lang(userid)

    res = await long_activity.find_one(
        {'alt_code': alt_code})
    if res and messageid:
        if res['use_energy']:
            await long_activity.update_one(
                {'alt_code': alt_code},
                {'$set': {'use_energy': False}}
            )
        else:
            await long_activity.update_one(
                {'alt_code': alt_code},
                {'$set': {'use_energy': True}}
            )

        await use_energy(chatid, lang, alt_code, messageid)


@HDCallback
@main_router.callback_query(IsPrivateChat(), F.data.startswith('use_training_boost'))
async def use_training_boost_calb(call: CallbackQuery):
    """Открывает инвентарь с фильтром по нужному типу бустера тренировки."""
    from bot.modules.items.item_tools import open_training_boost_inventory

    alt_code = call.data.split()[1]
    chatid = call.message.chat.id
    userid = call.from_user.id
    lang = await get_lang(userid)

    res = await long_activity.find_one({'alt_code': alt_code})
    if not res:
        await call.answer(t('css.error', lang, default='❌ Тренировка не найдена'), show_alert=True)
        return

    activity_type = res['activity_type']
    await call.answer()
    await open_training_boost_inventory(userid, chatid, lang, activity_type)