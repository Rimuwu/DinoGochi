
from aiogram import F, types
from bot.exec import main_router, bot

from bot.filters.private import IsPrivateChat
from bot.modules.data_format import list_to_keyboard
from bot.modules.decorators import HDCallback
from bot.modules.dinosaur.dino_status import check_status
from bot.modules.dinosaur.dinosaur import Dino
from bot.modules.localization import get_lang, t
from bot.modules.states_fabric.state_handlers import ChooseOptionHandler
from bot.modules.markup import markups_menu as m

from bot.dbmanager import mongo_client
from bot.modules.overwriting.DataCalsses import DBconstructor
kindergarten_bd = DBconstructor(mongo_client.dino_activity.kindergarten)
dinosaurs = DBconstructor(mongo_client.dinosaur.dinosaurs)

@HDCallback
@main_router.callback_query(IsPrivateChat(), F.data.startswith('-0'))
async def acs_manage(call: types.CallbackQuery):
    split_d = call.data.split()
    # action = split_d[1]
    # alt_key = split_d[2]

    userid = call.from_user.id
    chatid = call.message.chat.id
    lang = await get_lang(call.from_user.id)

    dino = await dinosaurs.find_one({'alt_id': alt_key}, comment='kindergarten_dino')
    if dino:
        ...