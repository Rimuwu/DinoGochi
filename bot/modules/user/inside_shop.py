
from random import choice
from time import time

from bson import ObjectId
from telebot.types import User as teleUser

from bot.config import mongo_client
from bot.const import GAME_SETTINGS as GS
from bot.exec import bot
from bot.modules.data_format import escape_markdown, item_list, seconds_to_str, user_name
from bot.modules.dinosaur.dinosaur import Dino, Egg
from bot.modules.items.items_groups import get_group
from bot.modules.user.advert import create_ads_data
from bot.modules.user.friends import get_frineds
from bot.modules.items.item import AddItemToUser, get_item_dict
from bot.modules.items.item import get_data as get_item_data
from bot.modules.items.item import get_name
from bot.modules.localization import get_data, t, get_lang, available_locales
from bot.modules.logs import log
from bot.modules.notifications import user_notification
from bot.modules.managment.referals import get_code_owner, get_user_sub
from datetime import datetime, timedelta


from bot.modules.overwriting.DataCalsses import DBconstructor
inside_shop = DBconstructor(mongo_client.market.inside_shop)

async def create_shop(onwer_id):

    data = {
        "owner_id": onwer_id,
        "day_number": 0,
        "items": {}
    }

    res = await inside_shop.insert_one(data)
    await update_shop(res.inserted_id)


async def update_shop(ins_id: ObjectId):

    shop = await inside_shop.find_one({'_id': ins_id})
    if shop:
        day_n = int(time.strftime("%j"))
        if day_n != shop['day_number']:

            items_group = get_group('recipe')
            for i in range(5):
                