from dbm.ndbm import library
from time import time
from typing import Optional

from bot.dbmanager import mongo_client
from bot.const import GAME_SETTINGS
from bot.exec import bot
from bot.modules.dino_uniqueness import get_dino_uniqueness_factor
from bot.modules.dinosaur.kd_activity import check_all_activity
from bot.modules.images import create_skill_image
from bot.modules.images_save import edit_SmartPhoto, send_SmartPhoto
from bot.modules.data_format import (list_to_inline, near_key_number, seconds_to_str)
from bot.modules.dinosaur.dinosaur import Dino, check_for_activity
from bot.modules.localization import get_data, t
from bot.modules.managment.events import check_event, get_event
from bot.modules.markup import markups_menu as m
from bot.modules.overwriting.DataCalsses import DBconstructor
from bot.modules.user.user import User
from aiogram import types
from aiogram.types import Message, InlineKeyboardMarkup

dino_mood = DBconstructor(mongo_client.dinosaur.dino_mood)
dinosaurs = DBconstructor(mongo_client.dinosaur.dinosaurs)
dino_owners = DBconstructor(mongo_client.dinosaur.dino_owners)

long_activity = DBconstructor(mongo_client.dino_activity.long_activity)
users = DBconstructor(mongo_client.user.users)
kindergarten_bd = DBconstructor(mongo_client.dino_activity.kindergarten)

async def add_activity_info(dino, lang, text, tem):
    status = await dino.status

    # Journey activity
    if status == 'journey':
        text += '\n\n'
        journey_data = await long_activity.find_one({'dino_id': dino._id, 
                                    'activity_type': 'journey'}, comment='dino_profile_journey')

        if journey_data:
            st = journey_data['journey_start']
            journey_time = seconds_to_str(int(time()) - st, lang)
            loc = journey_data['location']
            loc_name = get_data(f'journey_start.locations.{loc}', lang)['name']
            col = len(journey_data['journey_log'])

            text += t('p_profile.journey.text', lang, 
                      em_journey_act = tem['em_journey_act']) + '\n'
            text += t('p_profile.journey.info', lang, journey_time=journey_time, location=loc_name, col=col)

    # Game activity
    elif status == 'game':
        data = await long_activity.find_one({'dino_id': dino._id, 'activity_type': 'game'}, comment='dino_profile_game')
        text += t(
                f'p_profile.game.text', lang, em_game_act=tem['em_game_act'])
        if data:
            # if await check_accessory(dino, 'timer', True):
            #     end = seconds_to_str(data['game_end'] - int(time()), lang)
            #     text += t(f'p_profile.game.game_end', lang, end=end)

            duration = seconds_to_str(int(time()) - data['game_start'], lang)
            text += t(
                f'p_profile.game.game_duration', lang, duration=duration)

    # Collecting activity
    elif status == 'collecting':
        data = await long_activity.find_one({'dino_id': dino._id, 'activity_type': 'collecting'}, comment='dino_profile_collecting')
        if data:
            text += t(
                f'p_profile.collecting.text', lang, em_coll_act=tem['em_coll_act'])
            text += t(
                f'p_profile.collecting.progress.{data["collecting_type"]}', lang,
                now = data['now_count'], max_count=data['max_count'])

    # Sleep activity
    elif status == 'sleep':
        data = await long_activity.find_one({'dino_id': dino._id,
                                'activity_type': 'sleep'}, comment='dino_profile_sleep')
        if data:
            text += t(
                f'p_profile.sleep.{data["sleep_type"]}', lang, em_sleep_act=tem['em_sleep_act'])
            text += t(
                f'p_profile.sleep.sleep_duration', lang,
                duration=seconds_to_str(int(time()) - data['sleep_start'], lang))

    # Work activity
    elif status in ['bank', 'sawmill', 'mine']:
        data = await long_activity.find_one({'dino_id': dino._id, 
                            'activity_type': status}, comment='dino_profile_work')
        text += t(
                f'p_profile.work.text', lang, em_work_act=tem[f'em_{status}_act'],
                work_type=t(f'p_profile.work.work_type.{status}', lang))
        if data:
            duration = seconds_to_str(int(time()) - data['start_time'], lang)
            text += t(
                f'p_profile.work.work_duration', lang, duration=duration)

    # Training activity
    elif status in ['swimming_pool', 'gym', 'library', 'park']:
        data = await long_activity.find_one({'dino_id': dino._id, 
                            'activity_type': status}, comment='dino_profile_training')
        text += t(
                f'p_profile.training.text', lang, em_training_act=tem[f'em_{status}_act'],
                training_type=t(f'p_profile.training.training_type.{status}', lang))
        if data:
            duration = seconds_to_str(int(time()) - data['start_time'], lang)
            text += t(
                f'p_profile.training.training_duration', lang, duration=duration)

    return text

async def dino_profile(userid: int, 
                       chatid: int, dino: Dino, lang: str, 
                       custom_url, 
                       message_to_edit: Optional[Message] = None):
    text = ''

    text_rare = get_data('rare', lang)
    replics = get_data('p_profile.replics', lang)
    status_rep = t(f'p_profile.stats.{await dino.status}', lang)
    joint_dino, my_joint = False, False

    user = await User().create(userid)
    owners = await dino_owners.find({'dino_id': dino._id}, comment='dino_profile_owners')

    for owner in owners:
        if owner['owner_id'] == userid and owner['type'] == 'add_owner':
            joint_dino = True
        if owner['owner_id'] == userid and owner['type'] == 'owner' \
                and len(owners) >= 2: 
            my_joint = True

    season = await get_event('time_year')
    if 'data' in season:
        season = season['data']['season']
    else: season = 'standart'
    tem = GAME_SETTINGS['events']['time_year'][season]

    stats_text = ''
    # Генерация блока со статистикой
    for i in ['heal', 'eat', 'game', 'mood', 'energy']:
        repl = near_key_number(dino.stats[i], replics[i])
        stats_text += f'{tem[i]} {repl} \[ *{dino.stats[i]}%* ]\n'

    age = await dino.get_age()
    if age.days == 0:
        age = seconds_to_str(age.seconds, lang)
    else: age = seconds_to_str(age.days * 86400, lang)

    dino_name = dino.name
    if joint_dino: dino_name += t('p_profile.joint', lang)

    unique = await get_dino_uniqueness_factor(dino.data_id)

    kwargs = {
        'em_name': tem['name'], 'dino_name': dino_name,
        'em_status': tem['status'], 'status': status_rep,
        'em_rare': tem['rare'], 'qual': text_rare[dino.quality][1],
        'em_age': tem['age'], 'age': age,
        'em_uniqueness': tem['uniqueness'], 'uniqueness': unique,
    }

    # Первое апреля
    if await check_event('april_1'):
        for k, v in kwargs.items(): 
            if k.startswith('em_'):
                kwargs[k] = '🤡'

    text = t('p_profile.profile_text', lang, formating=False).format(**kwargs)

    text = await add_activity_info(dino, lang, text, tem)
    text += '\n\n' + stats_text + '\n'

    # # Генерация блока с аксессуарами
    # acsess = {
    #     'game': tem['ac_game'], 'collecting': tem['ac_collecting'], 'journey': tem['ac_journey'], 'sleep': tem['ac_sleep'], 'weapon': tem['ac_weapon'], "armor": tem['ac_armor'], 'backpack': tem['ac_backpack']
    # }

    menu = dino_profile_markup(False, 
                               lang, dino.alt_id)

    # затычка на случай если не сгенерируется изображение
    generate_image = 'images/remain/no_generate.png'
    if message_to_edit is None:
        msg = await send_SmartPhoto(chatid, generate_image, 
                                    text, 'Markdown', reply_markup=menu)
    else:
        msg = await edit_SmartPhoto(chatid, 
                    message_to_edit.message_id, generate_image, text, 'Markdown', reply_markup=menu)

    if message_to_edit is None:
        await bot.send_message(chatid, t('p_profile.return', lang), reply_markup= await m(userid, 'last_menu', lang))

    # изменение сообщения с уже нужным изображением
    image = await dino.image(user.settings['profile_view'], custom_url)
    await bot.edit_message_media(
        chat_id=chatid,
        message_id=msg.message_id,
        media=types.InputMediaPhoto(
            media=image, 
            parse_mode='Markdown', caption=text),
        reply_markup=menu
        )

# Страница профиля навыков динозавра
async def skills_profile(dino: Dino, lang, message: Message):

    age = await dino.get_age()
    image = await create_skill_image(dino.data_id, 
                                     age.days, lang, dino.stats)
    data_skills = {}

    for i in ['power', 'dexterity', 'intelligence', 'charisma']:
        data_skills[i] = near_key_number(
            dino.stats[i], get_data(f'skills_profile.{i}', lang)
        )
        data_skills[i+'_u'] = round(dino.stats[i], 4)

    text = t('skills_profile.info', lang, **data_skills)

    markup = await skills_inline(dino, lang)

    await message.edit_media(
        types.InputMediaPhoto(
            media=image, parse_mode='Markdown', caption=text),
        reply_markup=markup
    )


async def skills_inline(dino: Dino, lang: str):
    # Инлайн меню с быстрыми действиями. Например как снять аксессуар
    
    kwargs = {}
    for activity in ['gym', 'library', 'park', 'swimming_pool']:
        if await check_for_activity(activity, dino):
            kwargs[activity + '_act'] = True

    buttons = [
        {
            t('skills_profile.button_name', lang): 
                f'dino_menu main_message {dino.alt_id}'
        },
        {},
    ]
    
    kd = await check_all_activity(dino._id)

    if await dino.status in ['gym', 'library', 'park', 'swimming_pool']:

        buttons[0][
            t('skills_profile.inline_buttons.stop', lang)] = f'stop_skill_prepare {dino.alt_id}'

    else:

        if kwargs['gym_act']:
            dp = f'({seconds_to_str(kd["gym"], lang, True, "hour")})' if 'gym' in kd else ''

            buttons[1][
                t('skills_profile.inline_buttons.gym', lang) + f' {dp}'] = f'skills_start gym {dino.alt_id}'

        if kwargs['library_act']:
            dp = f'({seconds_to_str(kd["library"], lang, True, "hour")})' if 'library' in kd else ''

            buttons[1][
                t('skills_profile.inline_buttons.library', lang) + f' {dp}'] = f'skills_start library {dino.alt_id}'

        if kwargs['park_act']:
            dp = f'({seconds_to_str(kd["park"], lang, True, "hour")})' if 'park' in kd else ''

            buttons[1][
                t('skills_profile.inline_buttons.park', lang) + f' {dp}'] = f'skills_start park {dino.alt_id}'

        if kwargs['swimming_pool_act']:
            dp = f'({seconds_to_str(kd["swimming_pool"], lang, True, "hour")})' if 'swimming_pool' in kd else ''

            buttons[1][
                t('skills_profile.inline_buttons.swimming_pool', lang) + f' {dp}'] = f'skills_start swimming_pool {dino.alt_id}'

    return list_to_inline(buttons, 2)


def dino_profile_markup(add_acs_button: bool, lang: str, 
                        alt_id: str
                        ):
    # Инлайн меню с быстрыми действиями. Например как снять аксессуар

    buttons = {}
    rai = get_data('p_profile.inline_menu', lang)

    if add_acs_button:
        buttons[rai['reset_activ_item']['text']] = \
        rai['reset_activ_item']['data']

    buttons[rai['mood_log']['text']] = rai['mood_log']['data']

    buttons[rai['kindergarten']['text']] = rai['kindergarten']['data']

    # Страницы
    buttons[rai['skills']['text']] = rai['skills']['data']
    buttons[rai['accessories']['text']] = rai['accessories']['data']

    # Настройки
    buttons[rai['manage']['text']] = rai['manage']['data']
    # if joint_dino: 
    #     buttons[rai['joint_dino']['text']] = rai['joint_dino']['data']
    # if my_joint: 
    #     buttons[rai['my_joint']['text']] = rai['my_joint']['data']
    
    # buttons[rai['backgrounds']['text']] = rai['backgrounds']['data']

    for but in buttons: buttons[but] = buttons[but].format(dino=alt_id)
    return list_to_inline([buttons], 2)

def manage_markup(lang, dino: Dino):
    # Инлайн меню с быстрыми действиями. Например как снять аксессуар

    rai = get_data('p_profile.inline_menu', lang)
    buttons = {}

    joint_dino, my_joint = False, False

    if joint_dino: 
        buttons[rai['joint_dino']['text']] = rai['joint_dino']['data']
    if my_joint: 
        buttons[rai['my_joint']['text']] = rai['my_joint']['data']
    
    buttons[rai['backgrounds']['text']] = rai['backgrounds']['data']