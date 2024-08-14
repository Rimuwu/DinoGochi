from random import choice, randint, uniform

from bot.config import mongo_client
from bot.exec import bot
from bot.modules.dinosaur.dino_status import start_skill_activity
from bot.modules.dinosaur.kd_activity import save_kd
from bot.modules.dinosaur.skills import add_skill_point
from bot.modules.decorators import HDMessage
from bot.modules.localization import get_data, t
from bot.modules.markup import markups_menu as m
from bot.modules.dinosaur.mood import add_mood, repeat_activity
from bot.modules.overwriting.DataCalsses import DBconstructor
from bot.modules.states_tools import ChooseOptionState
from bot.modules.user.user import User
from telebot.types import Message
from bot.modules.data_format import seconds_to_str, list_to_keyboard
from bot.modules.dinosaur.dinosaur import Dino

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

    options = {
        "⏳ " + seconds_to_str(5400, lang): 5400,
        "⏳ " + seconds_to_str(7200, lang): 7200,
        "⏳ " + seconds_to_str(10800, lang): 10800,
    }
    mrk = list_to_keyboard([list(options.keys())])
    await bot.send_message(chatid, 
        t('all_skills.choose_time', lang), 
        reply_markup = mrk,
        parse_mode ='Markdown'
    )
    await ChooseOptionState(
        start_gym, userid, chatid, 
        lang, options,
        {'last_dino': last_dino}
    )


async def start_gym(time_sec: int, transmitted_data: dict):
    last_dino = transmitted_data['last_dino']

    await save_kd(last_dino._id, 'gym', 3600 * 12)
    percent, _ = await last_dino.memory_percent('action', 'gym', True)
    await repeat_activity(last_dino._id, percent)

    
    print(time_sec)
    return
    await start_skill_activity(
        last_dino._id, 'gym', 
        'power', 'dexterity',
        0.0123, 0.006, 100
    )