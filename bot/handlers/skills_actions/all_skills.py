
from time import time

from bot.dbmanager import mongo_client
from bot.exec import bot
from bot.modules.dinosaur.dino_status import end_skill_activity, get_skill_time, start_skill_activity
from bot.modules.dinosaur.dinosaur import Dino
from bot.modules.dinosaur.kd_activity import save_kd
from bot.modules.dinosaur.skills import add_skill_point
from bot.modules.decorators import HDCallback, HDMessage
from bot.modules.localization import get_lang, t
from bot.modules.markup import markups_menu as m
from bot.modules.dinosaur.mood import repeat_activity
from bot.modules.notifications import dino_notification
from bot.modules.overwriting.DataCalsses import DBconstructor
from bot.modules.user.advert import auto_ads
from bot.modules.user.user import User
from telebot.types import Message, CallbackQuery
from bot.modules.data_format import list_to_inline, seconds_to_str

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
                text, chatid, messageid, reply_markup=mrk,
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

@bot.message_handler(textstart='commands_name.skills_actions.gym', dino_pass=True, nothing_state=True, kd_check='gym')
@HDMessage
async def gym(message: Message):
    userid = message.from_user.id
    user = await User().create(userid)
    lang = await user.lang
    last_dino = await user.get_last_dino()
    chatid = message.chat.id

    await start_skill(last_dino, userid, chatid, lang, 'gym')

@bot.message_handler(textstart='commands_name.skills_actions.library', dino_pass=True, nothing_state=True, kd_check='library')
@HDMessage
async def library(message: Message):
    userid = message.from_user.id
    user = await User().create(userid)
    lang = await user.lang
    last_dino = await user.get_last_dino()
    chatid = message.chat.id

    await start_skill(last_dino, userid, chatid, lang, 'library')

@bot.message_handler(textstart='commands_name.skills_actions.park', dino_pass=True, nothing_state=True, kd_check='park')
@HDMessage
async def park(message: Message):
    userid = message.from_user.id
    user = await User().create(userid)
    lang = await user.lang
    last_dino = await user.get_last_dino()
    chatid = message.chat.id

    await start_skill(last_dino, userid, chatid, lang, 'park')

@bot.message_handler(textstart='commands_name.skills_actions.swimming_pool', dino_pass=True, nothing_state=True, kd_check='swimming_pool')
@HDMessage
async def swimming_pool(message: Message):
    userid = message.from_user.id
    user = await User().create(userid)
    lang = await user.lang
    last_dino = await user.get_last_dino()
    chatid = message.chat.id

    await start_skill(last_dino, userid, chatid, lang, 'swimming_pool')

@bot.message_handler(textstart='commands_name.skills_actions.stop_work', nothing_state=True)
@HDMessage
async def stop_work(message: Message):
    userid = message.from_user.id
    user = await User().create(userid)
    lang = await user.lang
    last_dino = await user.get_last_dino()
    chatid = message.chat.id

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


@bot.callback_query_handler(pass_bot=True, func=lambda call: 
    call.data.startswith('stop_work'))
@HDCallback
async def stop_work_calb(call: CallbackQuery):
    userid = call.from_user.id
    chatid = call.message.chat.id
    user = await User().create(userid)
    last_dino = await user.get_last_dino()
    messageid = call.message.id
    dino_id = last_dino._id

    res = await long_activity.find_one(
        {'dino_id': dino_id, 
         'activity_type': {'$in': ['gym', 'library', 'swimming_pool', 'park']}
         })

    if res and messageid: 
        traning_time = int(time()) - res['start_time']
        way = ''

        if traning_time < res['min_time']:
            unit_percent = res['up'] / 2
            await add_skill_point(dino_id, res['up_skill'], -unit_percent)
            way = '_negative'

        await dino_notification(dino_id, res['activity_type'] + '_end' + way)
        await end_skill_activity(dino_id)
        await bot.delete_message(chatid, messageid)

@bot.callback_query_handler(pass_bot=True, func=lambda call: 
    call.data.startswith('use_energy'))
@HDCallback
async def use_energy_calb(call: CallbackQuery):

    alt_code = call.data.split()[1]
    chatid = call.message.chat.id
    userid = call.from_user.id
    messageid = call.message.id
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