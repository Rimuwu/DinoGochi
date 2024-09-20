from random import choice, randint, uniform

from bot.dbmanager import mongo_client
from bot.exec import bot
from bot.modules.dinosaur.kd_activity import save_kd
from bot.modules.dinosaur.skills import add_skill_point
from bot.modules.decorators import HDMessage
from bot.modules.localization import get_data, t
from bot.modules.markup import markups_menu as m
from bot.modules.dinosaur.mood import add_mood, repeat_activity
from bot.modules.overwriting.DataCalsses import DBconstructor
from bot.modules.user.advert import auto_ads
from bot.modules.user.user import User
from telebot.types import Message

dinosaurs = DBconstructor(mongo_client.dinosaur.dinosaurs)
long_activity = DBconstructor(mongo_client.dino_activity.long_activity)
dino_mood = DBconstructor(mongo_client.dinosaur.dino_mood)

@bot.message_handler(textstart='commands_name.speed_actions.talk', dino_pass=True, nothing_state=True, kd_check='talk')
@HDMessage
async def talk(message: Message):
    userid = message.from_user.id
    user = await User().create(userid)
    lang = await user.lang
    last_dino = await user.get_last_dino()
    chatid = message.chat.id

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