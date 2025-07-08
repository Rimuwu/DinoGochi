
from time import time

from bot.dbmanager import mongo_client
from bot.exec import main_router, bot
from bot.modules.dinosaur.dino_status import end_skill_activity, get_skill_time, start_skill_activity
from bot.modules.dinosaur.dinosaur import Dino
from bot.modules.dinosaur.kd_activity import check_activity, save_kd
from bot.modules.dinosaur.profile import skills_inline
from bot.modules.dinosaur.skills import add_skill_point
from bot.modules.decorators import HDCallback, HDMessage
from bot.modules.localization import get_lang, t
from bot.modules.markup import markups_menu as m
from bot.modules.dinosaur.mood import repeat_activity
from bot.modules.notifications import dino_notification
from bot.modules.overwriting.DataCalsses import DBconstructor
from bot.modules.user.advert import auto_ads
from bot.modules.user.user import User
from aiogram.types import Message, CallbackQuery
from bot.modules.data_format import list_to_inline, seconds_to_str

from bot.filters.translated_text import StartWith
from bot.filters.status import DinoPassStatus
from bot.filters.private import IsPrivateChat
from bot.filters.kd import KDCheck
from aiogram import F

dinosaurs = DBconstructor(mongo_client.dinosaur.dinosaurs)
long_activity = DBconstructor(mongo_client.dino_activity.long_activity)
dino_mood = DBconstructor(mongo_client.dinosaur.dino_mood)

async def use_energy(chatid, lang, alt_code, messageid = 0):
    res = await long_activity.find_one(
        {'alt_code': alt_code})
    if res:
        text = t(f'all_skills.use_energy.text', lang)
        mrk = list_to_inline(
            [{
                t(f'all_skills.use_energy.buttons.{int(res["use_energy"])}', lang): f'use_energy {alt_code}'
            }]
        )
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
    await save_kd(last_dino._id, skill, skills_data[skill]['kd'])
    percent, _ = await last_dino.memory_percent('action', skill, True)
    await repeat_activity(last_dino._id, percent)

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

@HDCallback
@main_router.callback_query(IsPrivateChat(), 
                            F.data.startswith('skills_start')
                            )
async def skills_start(callback: CallbackQuery):
    userid = callback.from_user.id
    user = await User().create(userid)
    lang = await user.lang

    chatid = callback.message.chat.id
    skill = callback.data.split(' ')[1]
    alt_id = callback.data.split(' ')[2]

    dino = await Dino().create(alt_id)
    if not dino:
        await bot.send_message(chatid, t('css.no_dino', lang), reply_markup=await m(userid, 'last_menu', lang))
        return

    if not await dino.is_free():
        text = t('alredy_busy', lang)
        await bot.send_message(chatid, text, parse_mode='Markdown')
        return 

    sec_col = await check_activity(dino._id, skill)
    if sec_col:
        text = t('kd_coldown', lang, ss=seconds_to_str(sec_col, lang))
        await bot.send_message(chatid, text, parse_mode='Markdown')
        return 

    await start_skill(dino, userid, chatid, lang, skill)

    edited_message = callback.message
    mrk = await skills_inline(dino, lang)
    await edited_message.edit_reply_markup(
        reply_markup=mrk)

@HDMessage
@main_router.callback_query(IsPrivateChat(), 
                     F.data.startswith('stop_skill_prepare'))
async def stop_skill_prepare(callback: CallbackQuery):
    userid = callback.from_user.id
    user = await User().create(userid)
    lang = await user.lang
    alt_id = callback.data.split(' ')[1]
    chatid = callback.message.chat.id

    dino = await Dino().create(alt_id)
    if not dino:
        await bot.send_message(chatid, t('css.no_dino', lang))
        return

    if await dino.status in ['gym', 'library', 'park', 'swimming_pool']:

        mrk = list_to_inline([
            {t('all_skills.stoping.button', lang): f'stop_skill {dino.alt_id} {callback.message.message_id}'}
        ])
        await bot.send_message(chatid, 
            t('all_skills.stoping.text', lang), 
            reply_markup = mrk,
            parse_mode = 'Markdown'
        )

    else:
        await bot.send_message(chatid, '❌', parse_mode='Markdown', reply_markup=await m(userid, 'last_menu', lang))


@HDCallback
@main_router.callback_query(IsPrivateChat(), F.data.startswith('stop_skill'))
async def stop_skill_calb(call: CallbackQuery):
    userid = call.from_user.id
    chatid = call.message.chat.id
    user = await User().create(userid)
    messageid = call.message.message_id

    alt_id = call.data.split(' ')[1]
    mess_edit_id = call.data.split(' ')[2]
    lang = await user.lang

    dino = await Dino().create(alt_id)
    if not dino:
        await bot.send_message(chatid, t('css.no_dino', lang), reply_markup=await m(userid, 'last_menu', lang))
        return

    res = await long_activity.find_one(
        {'dino_id': dino._id, 
         'activity_type': {'$in': ['gym', 'library', 'swimming_pool', 'park']}
         })

    if res and messageid: 
        traning_time = int(time()) - res['start_time']
        way = ''

        unit_percent = res['up']
        if traning_time < res['min_time']:
            unit_percent = res['up'] / 2
            await add_skill_point(dino._id, res['up_skill'], -unit_percent)
            way = '_negative'

        await dino_notification(dino._id, res['activity_type'] + '_end' + way, 
                                add_unit=round(unit_percent, 4))
        await end_skill_activity(dino._id)
        await bot.delete_message(chatid, messageid)
        
        new_profile_mrk = await skills_inline(dino, lang)
        await bot.edit_message_reply_markup(
            reply_markup=new_profile_mrk,
            chat_id=chatid,
            message_id=int(mess_edit_id)
        )

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
    
    else: await call.message.delete()