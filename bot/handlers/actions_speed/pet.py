from bot.modules.overwriting.DataCalsses import LazyCollection
from bot.models.dinosaur import Dino, DinoMood
from random import choice, randint, uniform

from bot.dbmanager import mongo_client
from bot.exec import main_router, bot
from bot.filters.private import IsPrivateChat
from bot.models.activity import KDActivity
from bot.models.dinosaur import Dino
from bot.modules.decorators import HDMessage
from bot.models.dinosaur import Dino
from bot.modules.localization import get_data, t
from bot.modules.markup import markups_menu as m
from bot.modules.user.advert import auto_ads
from bot.modules.user.user import User, user_name
from aiogram.types import Message

from bot.filters.translated_text import Text
from bot.filters.status import DinoPassStatus
from bot.filters.kd import KDCheck
from aiogram import F

dinosaurs = LazyCollection(Dino)
dino_mood = LazyCollection(DinoMood)

@HDMessage
@main_router.message(IsPrivateChat(), Text('commands_name.speed_actions.pet'), DinoPassStatus(), KDCheck('pet'))
async def pet(message: Message):
    userid = message.from_user.id
    user = await User().create(userid)
    lang = await user.lang
    last_dino = await user.get_last_dino()
    chatid = message.chat.id
    cancel_break = False
    
    if not last_dino:
        await bot.send_message(chatid, t('css.no_dino', lang), reply_markup=await m(userid, 'last_menu', lang))
        return

    await DinoMood.add(last_dino._id, 'pet', 1, 600)
    await KDActivity.save_kd(last_dino._id, 'pet', 900)

    percent, _ = await last_dino.memory_percent('action', 'pet', True)
    await DinoMood.repeat_activity(last_dino._id, percent)

    lst_skills = [
        'power', 'dexterity', 'intelligence', 'charisma'
    ]
    r_skill = choice(lst_skills)

    await Dino.add_skill_point(last_dino._id, r_skill, -uniform(0.0001, 0.001))

    if randint(1, 4) == 2:
        res = await dino_mood.find_one({'dino_id': last_dino._id, 'type': 'breakdown'}, comment='pet_res')

        if res:
            await dino_mood.delete_one(
                {'_id': res['_id']})

            if res['action'] == 'hysteria':
                await set_status(last_dino._id, 'pass')

            cancel_break = True

    owner = await user_name(userid)
    rand_d_act = choice(get_data('pet.lst', lang))
    mes = rand_d_act['message'].format(
        owner=f'`{owner}`')

    text = f"🦕 | __{rand_d_act['reaction']}__\n🪈 | {mes}"
    try:
        mes = await bot.send_message(chatid, text, parse_mode='Markdown',
            reply_markup=await m(userid, 'speed_actions_menu', lang, True))
    except Exception as e:
        mes = await bot.send_message(chatid, text, 
            reply_markup=await m(userid, 'speed_actions_menu', lang, True))

    if cancel_break:
        await bot.send_message(chatid, t('pet.cancel_breakdown', lang), parse_mode='Markdown')
    await auto_ads(mes)