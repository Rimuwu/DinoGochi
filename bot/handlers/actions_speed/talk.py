from random import choice, randint, uniform

from bot.dbmanager import mongo_client
from bot.exec import main_router, bot
from bot.modules.dinosaur.kd_activity import save_kd
from bot.modules.dinosaur.skills import add_skill_point
from bot.modules.decorators import HDMessage
from bot.modules.localization import get_data, t
from bot.modules.markup import markups_menu as m
from bot.modules.dinosaur.mood import add_mood, repeat_activity
from bot.modules.overwriting.DataCalsses import DBconstructor
from bot.modules.user.advert import auto_ads
from bot.modules.user.user import User
from aiogram.types import Message

from bot.filters.translated_text import Text
from bot.filters.states import NothingState
from bot.filters.status import DinoPassStatus
from bot.filters.private import IsPrivateChat
from bot.filters.authorized import IsAuthorizedUser
from bot.filters.kd import KDCheck
from aiogram import F

dinosaurs = DBconstructor(mongo_client.dinosaur.dinosaurs)
long_activity = DBconstructor(mongo_client.dino_activity.long_activity)
dino_mood = DBconstructor(mongo_client.dinosaur.dino_mood)

@HDMessage
@main_router.message(Text('commands_name.speed_actions.talk'), DinoPassStatus(), KDCheck('talk'))
async def talk(message: Message):
    userid = message.from_user.id
    user = await User().create(userid)
    lang = await user.lang
    last_dino = await user.get_last_dino()
    chatid = message.chat.id
    
    if not last_dino:
        await bot.send_message(chatid, t('css.no_dino', lang), reply_markup=await m(userid, 'last_menu', lang))
        return

    percent, _ = await last_dino.memory_percent('action', 'talk', True)
    await repeat_activity(last_dino._id, percent)

    if uniform(1, 10) > 5 + 0.4 * last_dino.stats['charisma']: 
        status = 'negative' # negative 50%
        unit = -1
    else:
        status = 'positive' # positive 50%
        unit = 1

    await add_mood(last_dino._id, f'{status}_talk', unit, 600)
    await save_kd(last_dino._id, 'talk', 900)
    await add_skill_point(last_dino._id, 'charisma', uniform(0.001, 0.01))

    text_l: list = get_data(f'talk.themes.{status}', lang)
    theme = choice(text_l)

    text = t(f'talk.{status}', lang, theme=theme)
    mes = await bot.send_message(chatid, text,  parse_mode='Markdown',
        reply_markup=await m(userid, 'speed_actions_menu', lang, True))
    await auto_ads(mes)