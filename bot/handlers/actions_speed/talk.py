from bot.models.dinosaur import Dino, DinoMood
from random import choice, uniform

from bot.exec import main_router, bot
from bot.models.activity import KDActivity
from bot.modules.localization import get_data, t
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
    Text('commands_name.speed_actions.talk'),
    MultiDinoFilter(True)
)
async def multi_talk(message: Message):
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
        sec_col = await KDActivity.check_activity(dino._id, 'talk')
        if sec_col:
            reports.append(f"🦕 <b>{dino.name}</b>:\n<blockquote>{t('kd_coldown', lang, ss=seconds_to_str(sec_col, lang))}</blockquote>")
            continue

        st = await dino.status
        st_val = st.value if hasattr(st, 'value') else str(st)
        if st_val != 'pass':
            reports.append(f"🦕 <b>{dino.name}</b>:\n<blockquote>{t('alredy_busy', lang)}</blockquote>")
            continue

        percent, _ = await dino.memory_percent('action', 'talk', True)
        await DinoMood.repeat_activity(dino._id, percent)

        if uniform(1, 10) > 5 + 0.4 * dino.stats['charisma']: 
            status = 'negative'
            unit = -1
        else:
            status = 'positive'
            unit = 1

        await DinoMood.add(dino._id, f'{status}_talk', unit, 600)
        await KDActivity.save_kd(dino._id, 'talk', 900)
        await Dino.add_skill_point(dino._id, 'charisma', uniform(0.001, 0.01))

        text_l: list = get_data(f'talk.themes.{status}', lang)
        theme = choice(text_l)
        talk_text = t(f'talk.{status}', lang, theme=theme)
        dino_res = f"🦕 <b>{dino.name}</b>:\n<blockquote>{talk_text}</blockquote>"
        reports.append(dino_res)

    full_text = "\n\n".join(reports)
    mes = await bot.send_message(chatid, full_text, reply_markup=await m(userid, 'speed_actions_menu', lang, True))
    await auto_ads(mes)


@main_router.message(
    IsPrivateChat(), 
    Text('commands_name.speed_actions.talk'), 
    DinoPassStatus(), KDCheck('talk')
)
async def talk(message: Message):
    userid = message.from_user.id
    user = await User().create(userid)
    lang = await user.lang
    last_dino = await user.get_last_dino()
    chatid = message.chat.id
    
    if not last_dino:
        await bot.send_message(chatid, t('css.no_dino', lang), 
        reply_markup = await m(userid, 'last_menu', lang))
        return

    percent, _ = await last_dino.memory_percent('action', 'talk', True)
    await DinoMood.repeat_activity(last_dino._id, percent)

    if uniform(1, 10) > 5 + 0.4 * last_dino.stats['charisma']: 
        status = 'negative' # negative 50%
        unit = -1
    else:
        status = 'positive' # positive 50%
        unit = 1

    await DinoMood.add(last_dino._id, f'{status}_talk', unit, 600)
    await KDActivity.save_kd(last_dino._id, 'talk', 900)
    await Dino.add_skill_point(last_dino._id, 'charisma', uniform(0.001, 0.01))

    text_l: list = get_data(f'talk.themes.{status}', lang)
    theme = choice(text_l)

    text = t(f'talk.{status}', lang, theme=theme)
    mes = await bot.send_message(chatid, text,
        reply_markup = await m(userid, 'speed_actions_menu', lang, True))

    await auto_ads(mes)