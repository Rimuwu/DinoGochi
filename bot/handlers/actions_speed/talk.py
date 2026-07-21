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