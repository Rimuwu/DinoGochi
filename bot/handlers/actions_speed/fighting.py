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
@main_router.message(Text('commands_name.speed_actions.fighting'), DinoPassStatus(), 
             KDCheck('fighting'))
async def fighting(message: Message):
    userid = message.from_user.id
    user = await User().create(userid)
    lang = await user.lang
    last_dino = await user.get_last_dino()
    chatid = message.chat.id

    dex_status, block_status = False, False

    percent, _ = await last_dino.memory_percent('action', 'fighting', True)
    await repeat_activity(last_dino._id, percent)
    await save_kd(last_dino._id, 'fighting', 2400)

    if uniform(1, 10) < 4 + 0.4 * last_dino.stats['dexterity']:
        dex_status = True

    elif uniform(1, 10) < 4 + 0.4 * last_dino.stats['power']:
        block_status = True

    else:
        heal = randint(1, 5)
        await add_mood(last_dino._id, 'break', -1, 1200)
        await add_skill_point(last_dino._id, 'power', uniform(0.001, 0.01))
        await last_dino.update(
            {'$inc': {'stats.heal': -heal}}
        )

        text = t(f'fighting.hit', lang, heal=heal)
        await bot.send_message(chatid, text,  parse_mode='Markdown',
            reply_markup=await m(userid, 'speed_actions_menu', lang, True))
        return

    if all([dex_status, block_status]): code_s = randint(1, 2)
    elif dex_status: code_s = 1
    elif block_status: code_s = 2

    if code_s == 1: # Уклонился
        await add_skill_point(last_dino._id, 'dexterity', uniform(0.001, 0.01))

        text = t(f'fighting.avoid', lang)
        mes = await bot.send_message(chatid, text,  parse_mode='Markdown',
            reply_markup=await m(userid, 'speed_actions_menu', lang, True))

    elif code_s == 2: # Заблокировал удар
        await add_skill_point(last_dino._id, 'power', uniform(0.001, 0.01))

        text = t(f'fighting.block', lang)
        mes = await bot.send_message(chatid, text,  parse_mode='Markdown',
            reply_markup=await m(userid, 'speed_actions_menu', lang, True))
    await auto_ads(mes)