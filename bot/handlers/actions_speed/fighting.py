from bot.models.dinosaur import Dino, DinoMood
from random import randint, uniform

from bot.exec import main_router, bot
from bot.models.activity import KDActivity
from bot.modules.localization import  t
from bot.modules.markup import markups_menu as m
from bot.modules.user.advert import auto_ads
from bot.modules.user.user import User
from aiogram.types import Message

from bot.filters.translated_text import Text
from bot.filters.status import DinoPassStatus
from bot.filters.private import IsPrivateChat
from bot.filters.kd import KDCheck
from aiogram import F

from bot.filters.multi_dino import MultiDinoFilter
from bot.modules.data_format import seconds_to_str

@main_router.message(
    IsPrivateChat(),
    Text('commands_name.speed_actions.fighting'),
    MultiDinoFilter(True)
)
async def multi_fighting(message: Message):
    userid = message.from_user.id
    user = await User().create(userid)
    lang = await user.lang
    last_dinos = await user.get_last_dinos()
    chatid = message.chat.id

    if not last_dinos:
        await bot.send_message(chatid, t('css.no_dino', lang), 
            reply_markup=await m(userid, 'last_menu', lang))
        return

    reports = []
    for dino in last_dinos:
        sec_col = await KDActivity.check_activity(dino._id, 'fighting')
        if sec_col:
            reports.append(f"🦕 <b>{dino.name}</b>:\n<blockquote>{t('kd_coldown', lang, ss=seconds_to_str(sec_col, lang))}</blockquote>")
            continue

        st = await dino.status
        st_val = st.value if hasattr(st, 'value') else str(st)
        if st_val != 'pass':
            reports.append(f"🦕 <b>{dino.name}</b>:\n<blockquote>{t('alredy_busy', lang)}</blockquote>")
            continue

        dex_status, block_status = False, False
        percent, _ = await dino.memory_percent('action', 'fighting', True)
        await DinoMood.repeat_activity(dino._id, percent)
        await KDActivity.save_kd(dino._id, 'fighting', 2400)

        if uniform(1, 10) < 4 + 0.4 * dino.stats['dexterity']:
            dex_status = True
        elif uniform(1, 10) < 4 + 0.4 * dino.stats['power']:
            block_status = True
        else:
            heal = randint(1, 5)
            await DinoMood.add(dino._id, 'break', -1, 1200)
            await Dino.add_skill_point(dino._id, 'power', uniform(0.001, 0.01))
            await Dino.mutate_stat(dino, 'heal', -heal)
            hit_text = t('fighting.hit', lang, heal=heal)
            reports.append(f"🦕 <b>{dino.name}</b>:\n<blockquote>{hit_text}</blockquote>")
            continue

        if dex_status and block_status:
            code_s = randint(1, 2)
        elif dex_status:
            code_s = 1
        else:
            code_s = 2

        if code_s == 1:
            await Dino.add_skill_point(dino._id, 'dexterity', uniform(0.001, 0.01))
            avoid_text = t('fighting.avoid', lang)
            reports.append(f"🦕 <b>{dino.name}</b>:\n<blockquote>{avoid_text}</blockquote>")
        elif code_s == 2:
            await Dino.add_skill_point(dino._id, 'power', uniform(0.001, 0.01))
            block_text = t('fighting.block', lang)
            reports.append(f"🦕 <b>{dino.name}</b>:\n<blockquote>{block_text}</blockquote>")

    full_text = "\n\n".join(reports)
    mes = await bot.send_message(chatid, full_text, reply_markup=await m(userid, 'speed_actions_menu', lang, True))
    await auto_ads(mes)


@main_router.message(
    IsPrivateChat(), 
    Text('commands_name.speed_actions.fighting'), DinoPassStatus(), 
    KDCheck('fighting')
)
async def fighting(message: Message):
    userid = message.from_user.id
    user = await User().create(userid)
    lang = await user.lang
    last_dino = await user.get_last_dino()
    chatid = message.chat.id
    
    if not last_dino:
        await bot.send_message(chatid, t('css.no_dino', lang), 
        reply_markup = await m(userid, 'last_menu', lang))
        return

    dex_status, block_status = False, False

    percent, _ = await last_dino.memory_percent('action', 'fighting', True)
    await DinoMood.repeat_activity(last_dino._id, percent)
    await KDActivity.save_kd(last_dino._id, 'fighting', 2400)

    if uniform(1, 10) < 4 + 0.4 * last_dino.stats['dexterity']:
        dex_status = True

    elif uniform(1, 10) < 4 + 0.4 * last_dino.stats['power']:
        block_status = True

    else:
        heal = randint(1, 5)
        await DinoMood.add(last_dino._id, 'break', -1, 1200)
        await Dino.add_skill_point(last_dino._id, 'power', uniform(0.001, 0.01))
        await Dino.mutate_stat(last_dino, 'heal', -heal)

        text = t(f'fighting.hit', lang, heal=heal)
        await bot.send_message(chatid, text,
            reply_markup = await m(userid, 'speed_actions_menu', lang, True))
        return

    if all([dex_status, block_status]): code_s = randint(1, 2)
    elif dex_status: code_s = 1
    elif block_status: code_s = 2

    if code_s == 1: # Уклонился
        await Dino.add_skill_point(
            last_dino._id, 'dexterity', uniform(0.001, 0.01))

        text = t(f'fighting.avoid', lang)
        mes = await bot.send_message(chatid, text,
            reply_markup = await m(userid, 'speed_actions_menu', lang, True))

    elif code_s == 2: # Заблокировал удар
        await Dino.add_skill_point(last_dino._id, 'power', uniform(0.001, 0.01))

        text = t(f'fighting.block', lang)
        mes = await bot.send_message(chatid, text,
            reply_markup = await m(userid, 'speed_actions_menu', lang, True))
    await auto_ads(mes)