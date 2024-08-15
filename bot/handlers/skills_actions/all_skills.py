from random import choice, randint, uniform

from bot.config import mongo_client
from bot.exec import bot
from bot.modules.dinosaur.dino_status import end_skill_activity, start_skill_activity
from bot.modules.dinosaur.kd_activity import save_kd
from bot.modules.dinosaur.skills import add_skill_point
from bot.modules.decorators import HDCallback, HDMessage
from bot.modules.localization import get_data, get_lang, t
from bot.modules.markup import markups_menu as m
from bot.modules.dinosaur.mood import add_mood, repeat_activity
from bot.modules.notifications import dino_notification
from bot.modules.overwriting.DataCalsses import DBconstructor
from bot.modules.states_tools import ChooseOptionState
from bot.modules.user import user
from bot.modules.user.user import User
from telebot.types import Message, CallbackQuery
from bot.modules.data_format import list_to_inline, seconds_to_str, list_to_keyboard
from bot.modules.dinosaur.dinosaur import Dino

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

@bot.message_handler(textstart='commands_name.skills_actions.gym', dino_pass=True, nothing_state=True, kd_check='gym')
@HDMessage
async def gym(message: Message):
    userid = message.from_user.id
    user = await User().create(userid)
    lang = await user.lang
    last_dino = await user.get_last_dino()
    chatid = message.chat.id

    options = {
        "⏳ " + seconds_to_str(5400, lang): 5400,
        "⏳ " + seconds_to_str(7200, lang): 7200,
        "⏳ " + seconds_to_str(10800, lang): 10800,
    }
    mrk = list_to_keyboard(
        [
            list(options.keys()),
            [t('buttons_name.cancel', lang)]
        ], 2
    )
    await bot.send_message(chatid, 
        t('all_skills.choose_time', lang), 
        reply_markup = mrk,
        parse_mode ='Markdown'
    )
    await ChooseOptionState(
        start_gym, userid, chatid, 
        lang, options,
        {'last_dino': last_dino}
    )


async def start_gym(time_sec: int, transmitted_data: dict):
    last_dino = transmitted_data['last_dino']
    userid = transmitted_data['userid']
    lang = transmitted_data['lang']
    chatid = transmitted_data['chatid']

    await save_kd(last_dino._id, 'gym', 3600 * 12)
    percent, _ = await last_dino.memory_percent('action', 'gym', True)
    await repeat_activity(last_dino._id, percent)

    res = await start_skill_activity(
        last_dino._id, 'gym', 
        'power', 'dexterity',
        0.0123, 0.006, time_sec, userid
    )

    text = t(f'all_skills.gym', lang)
    await bot.send_message(chatid, text, parse_mode='Markdown',
        reply_markup=await m(userid, 'last_menu', lang))

    alt_code = res['alt_code']
    await use_energy(chatid, lang, alt_code)


@bot.message_handler(textstart='commands_name.skills_actions.stop_work', nothing_state=True)
@HDMessage
async def gym(message: Message):
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
async def stop_work(call: CallbackQuery):
    userid = call.from_user.id
    chatid = call.message.chat.id
    user = await User().create(userid)
    last_dino = await user.get_last_dino()
    messageid = call.message.id
    dino_id = last_dino._id

    res = await long_activity.find_one(
        {'dino_id': dino_id})

    if res: 
        unit_percent = res['up_unit'] / 2
        await add_skill_point(dino_id, res['up_skill'], unit_percent)

        await end_skill_activity(dino_id)
        await dino_notification(dino_id, res['activity_type'] + '_end')

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