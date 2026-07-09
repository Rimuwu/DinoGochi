from bot.models.dinosaur import Dino, DinoMood
from bot.models.activity import Activity

from time import time

from bot.exec import main_router, bot
from bot.models.activity.training import TrainingActivity
from bot.models.dinosaur import Dino
from bot.models.activity import KDActivity
from bot.models.dinosaur import Dino
from bot.modules.localization import get_lang, t
from bot.modules.markup import markups_menu as m
from bot.modules.notifications import dino_notification
from bot.modules.user.advert import auto_ads
from bot.modules.user.user import User
from aiogram.types import Message, CallbackQuery
from bot.modules.data_format import list_to_inline, seconds_to_str

from bot.filters.translated_text import StartWith
from bot.filters.status import DinoPassStatus
from bot.filters.private import IsPrivateChat
from bot.filters.kd import KDCheck
from aiogram import F

async def use_energy(chatid, lang, alt_code, messageid = 0):
    res = await Activity.find_one(Activity.alt_code == alt_code)
    if res:
        res_dict = res.dict()
        text = t(f'all_skills.use_energy.text', lang)
        buttons = [
            {
                t(f'all_skills.use_energy.buttons.{int(res_dict["use_energy"])}', lang): f'use_energy {alt_code}'
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

from bot.const import GAME_SETTINGS
skills_data = GAME_SETTINGS['skills_data']

async def start_skill(last_dino: Dino, userid, chatid, lang, skill):
    await KDActivity.save_kd(last_dino._id, skill, skills_data[skill]['kd'])
    percent, _ = await last_dino.memory_percent('action', skill, True)
    await DinoMood.repeat_activity(last_dino._id, percent)

    res = await TrainingActivity.start(
        last_dino._id, skill, 
        *skills_data[skill]['skills'],
        *skills_data[skill]['units'], sended=userid
    )
    if not res:
        await bot.send_message(chatid, t('alredy_busy', lang), reply_markup=await m(userid, 'last_menu', lang))
        return

    tran_time = Dino.get_skill_time(skill)[0]
    text = t(f'all_skills.{skill}', lang, 
             min_time=seconds_to_str(tran_time, lang))
    mes = await bot.send_message(chatid, text, parse_mode='Markdown',
        reply_markup=await m(userid, 'last_menu', lang))

    alt_code = res['alt_code']
    await use_energy(chatid, lang, alt_code)
    await auto_ads(mes)

@main_router.message(
    IsPrivateChat(), 
    StartWith('commands_name.skills_actions.gym'), 
    DinoPassStatus(), 
    KDCheck('gym')
    )
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

@main_router.message(
    IsPrivateChat(), 
    StartWith('commands_name.skills_actions.library'), 
    DinoPassStatus(), 
    KDCheck('library')
    )
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

@main_router.message(
    IsPrivateChat(),
    StartWith('commands_name.skills_actions.park'),
    DinoPassStatus(),
    KDCheck('park')
    )
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

@main_router.message(
    IsPrivateChat(),
    StartWith('commands_name.skills_actions.swimming_pool'),
    DinoPassStatus(),
    KDCheck('swimming_pool')
    )
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

@main_router.message(
    IsPrivateChat(), StartWith('commands_name.skills_actions.stop_work'))
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


@main_router.callback_query(IsPrivateChat(), F.data.startswith('stop_work'))
async def stop_work_calb(call: CallbackQuery):
    userid = call.from_user.id
    chatid = call.message.chat.id
    lang = await get_lang(userid)
    user = await User().create(userid)
    last_dino = await user.get_last_dino()
    messageid = call.message.message_id
    dino_id = last_dino.id

    if not last_dino:
        await bot.send_message(chatid, t('css.no_dino', lang), reply_markup=await m(userid, 'last_menu', lang))
        return

    from beanie.operators import In
    res = await Activity.find_one(
        Activity.dino.id == dino_id, 
        In(Activity.activity_type, ['gym', 'library', 'swimming_pool', 'park'])
    )

    if res and messageid: 
        res_dict = res.dict()
        traning_time = int(time()) - res_dict['start_time']
        way = ''

        unit_percent = res_dict['up']
        if traning_time < res_dict['min_time']:
            unit_percent = res_dict['up'] / 2
            await Dino.add_skill_point(
                dino_id, res_dict['up_skill'], -unit_percent)
            way = '_negative'

        await dino_notification(dino_id, res_dict['activity_type'] + '_end' + way, 
                                add_unit=round(unit_percent, 4))

        await TrainingActivity.end(dino_id)
        await bot.delete_message(chatid, messageid)
        await bot.send_message(chatid, t('back_text.skills_actions_menu', lang), reply_markup=await m(userid, 'skills_actions_menu', lang))

@main_router.callback_query(IsPrivateChat(), F.data.startswith('use_energy'))
async def use_energy_calb(call: CallbackQuery):

    alt_code = call.data.split()[1]
    chatid = call.message.chat.id
    userid = call.from_user.id
    messageid = call.message.message_id
    lang = await get_lang(userid)

    res = await Activity.find_one(Activity.alt_code == alt_code)
    if res and messageid:
        res_dict = res.dict()
        if res_dict['use_energy']:
            await res.update({'$set': {'use_energy': False}})
        else:
            await res.update({'$set': {'use_energy': True}})

        await use_energy(chatid, lang, alt_code, messageid)


@main_router.callback_query(IsPrivateChat(), F.data.startswith('use_training_boost'))
async def use_training_boost_calb(call: CallbackQuery):
    """Открывает инвентарь с фильтром по нужному типу бустера тренировки."""
    from bot.modules.items.item_tools import open_training_boost_inventory

    alt_code = call.data.split()[1]
    chatid = call.message.chat.id
    userid = call.from_user.id
    lang = await get_lang(userid)

    res = await Activity.find_one(Activity.alt_code == alt_code)
    if not res:
        await call.answer(t('css.error', lang, default='❌ Тренировка не найдена'), show_alert=True)
        return

    activity_type = res.activity_type
    await call.answer()
    await open_training_boost_inventory(userid, chatid, lang, activity_type)
