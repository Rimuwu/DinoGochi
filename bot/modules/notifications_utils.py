# Вспомогательные функции для уведомлений, чтобы избежать циклических импортов
from bot.dbmanager import mongo_client
from bot.modules.overwriting.DataCalsses import DBconstructor
from bot.modules.localization import get_lang
from bot.modules.logs import log
from bot.modules.user.dinocollection import add_to_collection_dino
from bot.modules.data_format import *
from bot.modules.items.item import AddItemToUser
from bot.const import *
from bot.modules.notifications import *
from random import choice
from bson.objectid import ObjectId
from aiogram.utils.keyboard import InlineKeyboardBuilder

# Вынесем только dino_notification, остальное не трогаем

async def dino_notification(*args, **kwargs):
    from bot.modules.notifications import dino_notification as orig_dino_notification
    return await orig_dino_notification(*args, **kwargs)
