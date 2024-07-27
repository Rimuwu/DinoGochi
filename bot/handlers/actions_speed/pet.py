from random import randint
from time import time

from bot.config import mongo_client
from bot.const import GAME_SETTINGS
from bot.exec import bot
from bot.modules.dinosaur.kd_activity import check_activity
from bot.modules.items.accessory import check_accessory
from bot.modules.user.advert import auto_ads
from bot.modules.data_format import list_to_inline
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

@bot.message_handler(pass_bot=True, text='commands_name.speed_actions.pet', dino_pass=True, nothing_state=True)
@HDMessage
async def pet(message: Message):
    userid = message.from_user.id
    user = await User().create(userid)
    lang = await user.lang
    last_dino = await user.get_last_dino()
    chatid = message.chat.id

    sec_col = await check_activity(last_dino._id, 'pet')
    if sec_col:
        text = t('kd_coldown', lang, ss=seconds_to_str(sec_col, lang))
        await bot.send_message(chatid, text)

    elif not sec_col:
        ...