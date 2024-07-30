# Тестовые команды

from functools import wraps
import statistics
from asyncio import sleep
from pprint import pprint
from time import time
import json
from random import choice
from time import sleep
from asyncio import sleep as asleep

from telebot.types import (InlineKeyboardButton, InlineKeyboardMarkup,
                           InlineQueryResultContact, Message, LabeledPrice)

from bot.config import conf, mongo_client
from bot.const import GAME_SETTINGS, ITEMS
from bot.exec import bot
from bot.handlers.dino_profile import transition
from bot.modules.data_format import list_to_inline, seconds_to_str, str_to_seconds, item_list
from bot.modules.dinosaur.dinosaur import check_status
from bot.modules.dinosaur.kd_activity import save_kd
from bot.modules.donation import send_inv
from bot.modules.images import create_egg_image, dino_collecting, dino_game
from bot.modules.inventory_tools import inventory_pages
from bot.modules.items.item import (AddItemToUser, DowngradeItem, get_data,
                              get_item_dict, get_name, RemoveItemFromUser)
from bot.modules.localization import get_data, get_lang, t
from bot.modules.markup import count_markup, down_menu, list_to_keyboard, confirm_markup
from bot.modules.notifications import user_notification, notification_manager
from bot.modules.states_tools import ChoosePagesState, ChooseStepState, prepare_steps
from bot.modules.user.user import User, max_dino_col, award_premium, count_inventory_items, experience_enhancement, take_coins
from bot.modules.managment.statistic import get_now_statistic
from bot.modules.quests import create_quest, quest_ui, save_quest
from bot.modules.dinosaur.journey import create_event, random_event, activate_event

from bot.modules.market.market import (add_product, create_seller,
                                generate_sell_pages, product_ui, seller_ui)
from bson.objectid import ObjectId
from bot.modules.images import create_dino_image, create_dino_image_pst, async_open

from bot.modules.managment.events import create_event, add_event, get_event

from bot.modules.user.user import get_inventory

from typing import Optional
from PIL import Image

from bot.modules.user.advert import show_advert

from bot.modules.overwriting.DataCalsses import DBconstructor
from bot.modules.decorators import HDMessage

from bson.objectid import ObjectId
from bson.son import SON

users = mongo_client.user.users

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
            res = await AddItemToUser(ad_user, item_id, col)
            print(res)

            await bot.send_message(message.from_user.id, res)
    else:
        print(user.id, 'not in devs')

@bot.message_handler(pass_bot=True, commands=['1xp'], is_admin=True)
async def command2(message):
    user = message.from_user
    if user.id in conf.bot_devs:
        await experience_enhancement(user.id, 1)
    else:
        print(user.id, 'not in devs')

@bot.message_handler(pass_bot=True, commands=['1coin'], is_admin=True)
async def coin(message):
    user = message.from_user
    
    res = await users.update_one({'userid': user.id}, 
                                 {'$inc': {'coins': 999999999999999999}}, comment='9999')

    pprint(res)


@bot.message_handler(pass_bot=True, commands=['test_img'], is_admin=True)
async def test_img(message):
    user = message.from_user

    uu = await User().create(user.id)
    dinos = await uu.get_dinos()
    
    dino = dinos[0]
    
    t1_list = []

    for i in range(100):
        st_t = time()
        res = await create_dino_image_pst(dino.data_id, 
                        {'heal': 0, 'eat': 0, 'energy': 0, 'game': 0, 'mood': 0}, "leg", 1, 30)

        tt = time() - st_t
        # await bot.send_photo(user.id, res, f"test {i} {tt}")
        t1_list.append(tt)
    
    t2_list = []

    for i in range(100):
        st_t = time()
        res = await create_dino_image(dino.data_id, 
                        {'heal': 0, 'eat': 0, 'energy': 0, 'game': 0, 'mood': 0}, "leg", 1, 30)

        tt = time() - st_t
        # await bot.send_photo(user.id, res, f"test {i} {tt}")
        t2_list.append(tt)
 
    
    t1 = sum(t1_list) / len(t1_list)
    t2 = sum(t2_list) / len(t2_list)
        
    print("t1", t1, "t2", t2, t1-t2)

from bot.modules.dungeon.dungeon import Lobby, DungPlayer

@bot.message_handler(pass_bot=True, commands=['dung'], is_admin=True)
async def dung(message):

    m = await bot.send_message(message.from_user.id, "test")
    lobby = await Lobby().create(message.from_user.id, m.id)

    pprint(lobby.__dict__)

@bot.message_handler(pass_bot=True, commands=['delete'], is_admin=True)
async def delete(message):

    lobby = await Lobby().FromBase(message.from_user.id)
    await lobby.delete

@bot.message_handler(pass_bot=True, commands=['add_to'], is_admin=True)
async def add_to(message):

    lobby = await Lobby().FromBase(1191252229)

    m = await bot.send_message(message.from_user.id, "test")
    player = await DungPlayer().create(message.from_user.id, m.id)
    await lobby.add_player(player, message.from_user.id)

@bot.message_handler(pass_bot=True, commands=['test'])
@HDMessage
async def test(message: Message):
    
    # uu = await User().create(message.from_user.id)
    # ld = await uu.get_last_dino()
    
    # await save_kd(ld._id, 'pet', 180)
    # await save_kd(ld._id, 'talk', 3600*2)
    # await save_kd(ld._id, 'fighting', 3600)


    async for index in users.list_indexes():
        index: SON
        print(index)
        print(dict(index['key']))

    await users.create_index(())
    
    resp = users.create_index([ ("field_to_index", -1) ], unique = True)