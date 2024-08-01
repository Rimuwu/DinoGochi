from random import choice, randint, uniform

from bot.config import mongo_client
from bot.exec import bot
from bot.modules.dinosaur.kd_activity import save_kd
from bot.modules.dinosaur.skills import add_skill_point
from bot.modules.decorators import HDMessage
from bot.modules.localization import get_data, t
from bot.modules.markup import markups_menu as m
from bot.modules.dinosaur.mood import add_mood, repeat_activity
from bot.modules.overwriting.DataCalsses import DBconstructor
from bot.modules.user.user import User
from telebot.types import Message

dinosaurs = DBconstructor(mongo_client.dinosaur.dinosaurs)
long_activity = DBconstructor(mongo_client.dino_activity.long_activity)
dino_mood = DBconstructor(mongo_client.dinosaur.dino_mood)

@bot.message_handler(textstart='commands_name.skills_actions.gym', dino_pass=True, nothing_state=True, kd_check='gym')
@HDMessage
async def gym(message: Message):
    userid = message.from_user.id
    user = await User().create(userid)
    lang = await user.lang
    last_dino = await user.get_last_dino()
    chatid = message.chat.id
    
    