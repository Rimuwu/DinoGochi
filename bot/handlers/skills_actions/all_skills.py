from bot.models.dinosaur import Dino, DinoMood
from bot.models.activity import Activity

from time import time

from bot.exec import main_router, bot
from bot.models.activity.training import TrainingActivity
from bot.models.dinosaur import Dino
from bot.models.activity import KDActivity
from bot.models.dinosaur import Dino
from bot.modules.localization import get_data, get_lang, t
from bot.modules.markup import markups_menu as m
from bot.modules.notifications import dino_notification
from bot.modules.user.advert import auto_ads
from bot.modules.user.user import User
from aiogram.types import Message, CallbackQuery
from bot.modules.data_format import list_to_inline, seconds_to_str

from bot.filters.translated_text import StartWith, Text
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
            await bot.send_message(chatid, text,
            reply_markup=mrk)
        else:
            await bot.edit_message_text(
                text, None, chatid, messageid, reply_markup=mrk
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
    mes = await bot.send_message(chatid, text,
        reply_markup=await m(userid, 'last_menu', lang))

    alt_code = res['alt_code']
    await use_energy(chatid, lang, alt_code)
    await auto_ads(mes)

async def build_skills_send_keyboard(user: User, lang: str):
    last_dinos = await user.get_last_dinos()
    draft = user.settings.get('skills_draft', {})
    
    skills_map = {
        'gym': '🥏',
        'library': '📚',
        'park': '🌳',
        'swimming_pool': '💧'
    }

    buttons = []
    active_count = 0

    for dino in last_dinos:
        selected_skill = draft.get(dino.alt_id, 'none')
        kd = await KDActivity.check_all_activity(dino._id)

        if selected_skill in skills_map:
            active_count += 1

        dino_btn = {
            "text": f"🦕 {dino.name}",
            "callback_data": f"skill_select {dino.alt_id} none"
        }
        if selected_skill == 'none':
            dino_btn["style"] = "primary"
        
        row = [dino_btn]
        for sk_key, sk_emoji in skills_map.items():
            cd_sec = kd.get(sk_key, 0)
            btn_text = sk_emoji
            if cd_sec > 0:
                btn_text += f" ({seconds_to_str(cd_sec, lang, True, 'hour')})"

            btn = {
                "text": btn_text,
                "callback_data": f"skill_select {dino.alt_id} {sk_key}"
            }
            if selected_skill == sk_key:
                btn["style"] = "primary"
            row.append(btn)

        buttons.append(row)

    buttons.append([{
        "text": t('all_skills.send_button', lang, count=active_count),
        "callback_data": "skill_batch_send"
    }])

    return list_to_inline(buttons)


@main_router.message(
    IsPrivateChat(),
    StartWith('commands_name.skills_actions.send')
)
async def skills_send(message: Message):
    userid = message.from_user.id
    user = await User().create(userid)
    lang = await user.lang
    last_dinos = await user.get_last_dinos()
    chatid = message.chat.id

    if not last_dinos:
        await bot.send_message(chatid, t('css.no_dino', lang), reply_markup=await m(userid, 'last_menu', lang))
        return

    # Reset draft selections when opening menu
    user.settings['skills_draft'] = {}
    await user.save()

    inline = await build_skills_send_keyboard(user, lang)
    await bot.send_message(chatid, t('all_skills.send_title', lang), reply_markup=inline)


@main_router.callback_query(IsPrivateChat(), F.data.startswith('skill_select'))
async def skill_select_calb(call: CallbackQuery):
    userid = call.from_user.id
    lang = await get_lang(userid)
    user = await User().create(userid)
    data = call.data.split()

    dino_alt_id = data[1]
    choice_key = data[2]

    if 'skills_draft' not in user.settings:
        user.settings['skills_draft'] = {}

    user.settings['skills_draft'][dino_alt_id] = choice_key
    await user.save()

    inline = await build_skills_send_keyboard(user, lang)
    try:
        await call.message.edit_reply_markup(reply_markup=inline)
    except Exception: pass
    await call.answer()


@main_router.callback_query(IsPrivateChat(), F.data == 'skill_batch_send')
async def skill_batch_send_calb(call: CallbackQuery):
    userid = call.from_user.id
    lang = await get_lang(userid)
    user = await User().create(userid)
    chatid = call.message.chat.id
    last_dinos = await user.get_last_dinos()
    draft = user.settings.get('skills_draft', {})

    skills_map = ['gym', 'library', 'park', 'swimming_pool']
    to_send = []
    for dino in last_dinos:
        sk = draft.get(dino.alt_id) or draft.get(str(dino.id))
        if sk in skills_map:
            to_send.append((dino, sk))

    if not to_send:
        await call.answer(t('all_skills.none_selected', lang), show_alert=True)
        return

    reports = []
    for dino, skill in to_send:
        sec_col = await KDActivity.check_activity(dino._id, skill)
        if sec_col:
            reports.append(f"🦕 <b>{dino.name}</b>: {t('kd_coldown', lang, ss=seconds_to_str(sec_col, lang))}")
            continue

        st = await dino.status
        st_val = st.value if hasattr(st, 'value') else str(st)
        if st_val != 'pass':
            reports.append(f"🦕 <b>{dino.name}</b>: {t('alredy_busy', lang)}")
            continue

        await start_skill(dino, userid, chatid, lang, skill)

    user.settings['skills_draft'] = {}
    await user.save()

    try:
        await bot.delete_message(userid, call.message.message_id)
    except Exception: pass

    await bot.send_message(chatid, t('all_skills.training_started', lang), reply_markup=await m(userid, 'skills_actions_menu', lang, True))
    await call.answer()


async def get_training_progress_data(userid: int, lang: str):
    user = await User().create(userid)
    dinos = await user.get_dinos()
    from beanie.operators import In

    skill_emojis = {
        'gym': '🥏',
        'library': '📚',
        'park': '🌳',
        'swimming_pool': '💧'
    }

    buttons = []
    text_blocks = []

    for dino in dinos:
        res = await Activity.find_one(
            Activity.dino.id == dino.id,
            In(Activity.activity_type, ['gym', 'library', 'swimming_pool', 'park'])
        )
        if res:
            res_dict = res.dict()
            act_type = res_dict['activity_type']
            emoji = skill_emojis.get(act_type, '🦕')
            act_title = t(f'commands_name.skills_actions.{act_type}', lang)
            elapsed_minutes = max(0, (int(time()) - res_dict['start_time']) // 60)

            buttons.append([
                {"text": f"{emoji} {dino.name}", "callback_data": "None"},
                {"text": t('all_skills.return_button', lang), "callback_data": f"stop_work_inline {dino.alt_id}"}
            ])

            info_str = t('all_skills.progress_info', lang, activity=act_title, minutes=elapsed_minutes)
            text_blocks.append(f"🦕 <b>{dino.name}</b>:\n<blockquote>{info_str}</blockquote>")

    if not buttons:
        return None, None

    header = t('all_skills.progress_title', lang)
    full_text = header + "\n\n" + "\n\n".join(text_blocks)
    return full_text, list_to_inline(buttons)


@main_router.message(
    IsPrivateChat(),
    Text('commands_name.skills_actions.progress')
)
async def skills_progress(message: Message):
    userid = message.from_user.id
    user = await User().create(userid)
    lang = await user.lang
    chatid = message.chat.id

    full_text, inline = await get_training_progress_data(userid, lang)
    if not inline:
        await bot.send_message(chatid, t('all_skills.no_training', lang), reply_markup=await m(userid, 'skills_actions_menu', lang))
    else:
        await bot.send_message(chatid, full_text, reply_markup=inline)


@main_router.callback_query(IsPrivateChat(), F.data.startswith('stop_work_inline'))
async def stop_work_inline_calb(call: CallbackQuery):
    userid = call.from_user.id
    chatid = call.message.chat.id
    lang = await get_lang(userid)
    data = call.data.split()
    dino_alt_id = data[1]

    dino = await Dino.find_one(Dino.alt_id == dino_alt_id)
    if not dino:
        await call.answer(t('css.no_dino', lang), show_alert=True)
        return

    from beanie.operators import In
    res = await Activity.find_one(
        Activity.dino.id == dino.id, 
        In(Activity.activity_type, ['gym', 'library', 'swimming_pool', 'park'])
    )

    if res:
        res_dict = res.dict()
        traning_time = int(time()) - res_dict['start_time']
        way = ''

        unit_percent = res_dict['up']
        if traning_time < res_dict['min_time']:
            unit_percent = res_dict['up'] / 2
            await Dino.add_skill_point(dino.id, res_dict['up_skill'], -unit_percent)
            way = '_negative'

        notif_key = res_dict['activity_type'] + '_end' + way
        await dino_notification(dino.id, notif_key, add_unit=round(unit_percent, 4))
        await TrainingActivity.end(dino.id)
        await call.answer()

        notif_data = get_data(f'notifications.{notif_key}', lang)
        if isinstance(notif_data, dict):
            text_msg = notif_data['text'].format(dino_name=dino.name, add_unit=round(unit_percent, 4))
        else:
            text_msg = notif_data.format(dino_name=dino.name, add_unit=round(unit_percent, 4))
        await bot.send_message(chatid, text_msg)

        full_text, new_inline = await get_training_progress_data(userid, lang)
        if new_inline:
            try:
                await call.message.edit_text(full_text, reply_markup=new_inline)
            except Exception: pass
        else:
            try:
                await call.message.edit_text(t('all_skills.no_training', lang))
            except Exception: pass
    else:
        await call.answer("❌", show_alert=False)


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
            reply_markup = mrk
        )

    else:
        await bot.send_message(chatid, '❌', reply_markup=await m(userid, 'last_menu', lang))


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

        notif_key = res_dict['activity_type'] + '_end' + way
        await dino_notification(dino_id, notif_key, 
                                add_unit=round(unit_percent, 4))

        await TrainingActivity.end(dino_id)
        await bot.delete_message(chatid, messageid)

        notif_data = get_data(f'notifications.{notif_key}', lang)
        if isinstance(notif_data, dict):
            text_msg = notif_data['text'].format(dino_name=last_dino.name, add_unit=round(unit_percent, 4))
        else:
            text_msg = notif_data.format(dino_name=last_dino.name, add_unit=round(unit_percent, 4))

        await bot.send_message(chatid, text_msg, reply_markup=await m(userid, 'skills_actions_menu', lang))

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
