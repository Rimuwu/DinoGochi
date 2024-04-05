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
from bot.modules.data_format import seconds_to_str, str_to_seconds, item_list
from bot.modules.dinosaur import check_status
from bot.modules.donation import check_donations, get_donations
from bot.modules.images import create_egg_image, dino_collecting, dino_game
from bot.modules.inventory_tools import inventory_pages
from bot.modules.item import (AddItemToUser, DowngradeItem, get_data,
                              get_item_dict, get_name, RemoveItemFromUser)
from bot.modules.localization import get_data, t
from bot.modules.markup import count_markup, down_menu, list_to_keyboard, confirm_markup
from bot.modules.notifications import user_notification, notification_manager
from bot.modules.states_tools import ChoosePagesState, ChooseStepState, prepare_steps
from bot.modules.user import User, max_dino_col, award_premium, count_inventory_items, experience_enhancement
from bot.modules.statistic import get_now_statistic
from bot.modules.quests import create_quest, quest_ui, save_quest
from bot.modules.journey import create_event, random_event, activate_event

from bot.modules.market import (add_product, create_seller,
                                generate_sell_pages, product_ui, seller_ui)
from bson.objectid import ObjectId
from bot.modules.images import create_dino_image, create_dino_image_pst

from bot.modules.events import create_event, add_event, get_event

from typing import Optional
from bot.modules.advert import show_advert

dinosaurs = mongo_client.dinosaur.dinosaurs
products = mongo_client.market.products
sellers = mongo_client.market.sellers
puhs = mongo_client.market.puhs
items = mongo_client.items.items
users = mongo_client.user.users
friends = mongo_client.user.friends
ads = mongo_client.user.ads

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

@bot.message_handler(pass_bot=True, commands=['fix_sleep'], is_admin=True)
async def fix_sleep(message):
    
    await dinosaurs.update_many(
        {'stats.sleep': {'$ne': None}}, {"$unset": {'stats.sleep': 1}})


@bot.message_handler(pass_bot=True, commands=['new_year'], is_admin=True)
async def new_year(message):
    
    ev = await create_event("new_year")
    await add_event(ev)
    await bot.send_message(conf.bot_group_id, t("events.new_year"))

from bot.modules.dungeon import Lobby, DungPlayer

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

@bot.message_handler(pass_bot=True, commands=['gramads'], is_admin=True)
async def gramads(message):
    await show_advert(message.from_user.id)

@bot.message_handler(pass_bot=True, commands=['teste'], is_admin=True)
async def teste(message):
    
    lst = [{"1": 1}, {"1": 1}, {"1": 1}, {"1": 1}, {"1": 1}, {"1": 1}, {"1": 1}, {"1": 1}, {"1": 1}, {"1": 1}, {"1": 1}]
    item_list(lst)

@bot.message_handler(pass_bot=True, commands=['status'], is_admin=True)
async def status(message):
    
    
    user = await User().create(message.from_user.id)
    dinos = await user.get_dinos()
    
    dino = dinos[0]
    print(await check_status(dino._id))

@bot.message_handler(pass_bot=True, commands=['ddt'], is_admin=True)
async def ddt(message):
    await ads.update_many(
        {'limit': {'$lte': 1800}}, {'$set': {'limit': 1800}}
    )

@bot.message_handler(pass_bot=True, commands=['fix'], is_admin=True)
async def fix(message):
    
    find_res = await items.find(
        {'items_data.abilities': {"$ne": None}, "count": {"$ne": 1}}
                                ).to_list(None)

    for i in find_res:
        preabil = {}

        if 'abilities' in i['items_data']:
            preabil = i['items_data']['abilities']
        ok = await RemoveItemFromUser(i['owner_id'], i['items_data']['item_id'], i['count'], preabil)

        if ok:
            await AddItemToUser(i['owner_id'], i['items_data']['item_id'], i['count'], preabil)
    
    print("Nice!")