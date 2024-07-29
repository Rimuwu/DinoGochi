from random import choice, randint, uniform
from time import time

from bot.config import mongo_client
from bot.const import GAME_SETTINGS
from bot.exec import bot
from bot.modules.dinosaur.kd_activity import check_activity, save_kd
from bot.modules.dinosaur.skills import add_skill_point
from bot.modules.items.accessory import check_accessory
from bot.modules.user.advert import auto_ads
from bot.modules.data_format import list_to_inline, user_name
from bot.modules.decorators import HDCallback, HDMessage
from bot.modules.dinosaur.dinosaur  import Dino, end_game, set_status
from bot.modules.user.friends import send_action_invite
from bot.modules.images import dino_game
from bot.modules.localization import get_data, get_lang, t
from bot.modules.markup import cancel_markup
from bot.modules.markup import markups_menu as m
from bot.modules.dinosaur.mood import add_mood, check_breakdown, check_inspiration
from bot.modules.overwriting.DataCalsses import DBconstructor
from bot.modules.quests import quest_process
from bot.modules.states_tools import ChooseStepState
from bot.modules.user.user import User, premium
from telebot.types import Message
from bot.modules.data_format import seconds_to_str

dinosaurs = DBconstructor(mongo_client.dinosaur.dinosaurs)
long_activity = DBconstructor(mongo_client.dino_activity.long_activity)
dino_mood = DBconstructor(mongo_client.dinosaur.dino_mood)

@bot.message_handler(textstart='commands_name.speed_actions.pet', dino_pass=True, nothing_state=True, kd_check='pet')
@HDMessage
async def pet(message: Message):
    userid = message.from_user.id
    user = await User().create(userid)
    lang = await user.lang
    last_dino = await user.get_last_dino()
    chatid = message.chat.id
    cancel_break = False

    await add_mood(last_dino._id, 'pet', 1, 600)
    await save_kd(last_dino._id, 'pet', 900)

    lst_skills = [
        'power', 'dexterity', 'intelligence', 'charisma'
    ]
    r_skill = choice(lst_skills)

    await add_skill_point(last_dino._id, r_skill, -uniform(0.001, 0.01))

    if randint(1, 4) == 2:
        res = await dino_mood.find_one({'dino_id': last_dino._id, 'type': 'breakdown'}, comment='pet_res')

        if res:
            await dino_mood.delete_one(
                {'_id': res['_id']})

            if res['action'] == 'hysteria':
                await set_status(last_dino._id, 'pass')

            cancel_break = True

    owner = user_name(message.from_user)
    rand_d_act = choice(get_data('pet.lst', lang))
    mes = rand_d_act['message'].format(
        owner=owner)
    text = f"🦕 | __{rand_d_act['reaction']}__\n🪈 | {mes}"
    await bot.send_message(chatid, text,  parse_mode='Markdown',
        reply_markup=await m(userid, 'speed_actions_menu', lang, True))

    if cancel_break:
        await bot.send_message(chatid, t('pet.cancel_breakdown', lang), parse_mode='Markdown')