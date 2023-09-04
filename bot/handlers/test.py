# Тестовые команды

import statistics
from asyncio import sleep
from pprint import pprint
from time import time
import json
from random import choice

from telebot.types import (InlineKeyboardButton, InlineKeyboardMarkup,
                           InlineQueryResultContact, Message)

from bot.config import conf, mongo_client
from bot.const import GAME_SETTINGS, ITEMS
from bot.exec import bot
from bot.handlers.dino_profile import transition
from bot.modules.currency import convert
from bot.modules.data_format import seconds_to_str, str_to_seconds
from bot.modules.donation import check_donations, get_donations
from bot.modules.images import create_egg_image, dino_collecting, dino_game
from bot.modules.inventory_tools import inventory_pages
from bot.modules.item import (AddItemToUser, DowngradeItem, get_data,
                              get_item_dict, get_name)
from bot.modules.localization import get_data, t
from bot.modules.markup import count_markup, down_menu, list_to_keyboard, confirm_markup
from bot.modules.notifications import user_notification, notification_manager
from bot.modules.states_tools import ChoosePagesState, ChooseStepState, prepare_steps
from bot.modules.user import User, max_dino_col, award_premium, count_inventory_items
from bot.modules.statistic import get_now_statistic
from bot.modules.quests import create_quest, quest_ui, save_quest
from bot.modules.journey import create_event, random_event, activate_event

from bot.modules.market import (add_product, create_seller,
                                generate_sell_pages, product_ui, seller_ui)
from bson.objectid import ObjectId

dinosaurs = mongo_client.dinosaur.dinosaurs
products = mongo_client.market.products
sellers = mongo_client.market.sellers
puhs = mongo_client.market.puhs
items = mongo_client.items.items


with open('bot/json/old_ids.json', encoding='utf-8') as f: 
    ids = json.load(f)

@bot.message_handler(pass_bot=True, commands=['add_item', 'item_add'], is_admin=True)
async def command(message):
    user = message.from_user
    if user.id in conf.bot_devs:
        msg_args = message.text.split()

        if len(msg_args) < 4:
            print('-347')

        else:
            ad_user = int(msg_args[1])
            item_id = msg_args[2]
            col = int(msg_args[3])
            
            print('user', ad_user, 'id:', item_id, 'col:', col)
            res = AddItemToUser(ad_user, item_id, col)
            print(res)
    else:
        print(user.id, 'not in devs')

