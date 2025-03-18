# Тестовые команды

import asyncio
from functools import wraps
from hmac import new
import stat
import statistics
from asyncio import sleep
from pprint import pprint
from time import time
import json
from random import choice
from time import sleep
from asyncio import sleep as asleep

from aiogram.types import (InlineKeyboardButton, InlineKeyboardMarkup,
                           InlineQueryResultContact, Message, LabeledPrice)
from bot.modules.dinosaur import dinosaur
from bot.modules.get_state import get_state
from bot.modules.images_save import send_SmartPhoto

from bot.modules.inline import inline_menu
from bot.modules.logs import log

from bot.config import conf
from bot.dbmanager import mongo_client
from bot.const import GAME_SETTINGS
from bot.exec import main_router, bot
from bot.modules.companies import nextinqueue, save_message
from bot.modules.data_format import list_to_inline, seconds_to_str, str_to_seconds, item_list
from bot.modules.dinosaur.dinosaur import check_status
from bot.modules.dinosaur.kd_activity import save_kd
from bot.modules.donation import send_inv
from bot.modules.images import create_egg_image, create_skill_image, dino_collecting, dino_game
from bot.modules.inventory_tools import inventory_pages
from bot.modules.items.item import (AddItemToUser, DowngradeItem, get_data,
                              get_item_dict, get_name, RemoveItemFromUser)
from bot.modules.localization import get_data, get_lang, t
from bot.modules.markup import answer_markup, cancel_markup, count_markup, down_menu, list_to_keyboard, confirm_markup
from bot.modules.notifications import user_notification, notification_manager
from bot.modules.states_tools import ChoosePagesState, ChooseStepState, prepare_steps
from bot.modules.user.advert import auto_ads
from bot.modules.user.user import User, max_dino_col, award_premium, count_inventory_items, experience_enhancement, take_coins
from bot.modules.managment.statistic import get_now_statistic
from bot.modules.quests import create_quest, quest_ui, save_quest
from bot.modules.dinosaur.journey import create_event, random_event, activate_event

from bot.modules.market.market import (ITEMS, add_product, create_seller,
                                generate_sell_pages, product_ui, seller_ui)
from bson.objectid import ObjectId
from bot.modules.images import create_dino_image, create_dino_image_pst, async_open

from bot.modules.managment.events import create_event, add_event, get_event

from bot.modules.user.user import get_inventory

from typing import Optional
from PIL import Image

from bot.filters.translated_text import StartWith, Text
from bot.filters.states import NothingState
from bot.filters.status import DinoPassStatus
from bot.filters.private import IsPrivateChat
from bot.filters.authorized import IsAuthorizedUser
from bot.filters.kd import KDCheck
from bot.filters.admin import IsAdminUser
from aiogram import F, Router
from aiogram.filters import Command, StateFilter

from bot.modules.overwriting.DataCalsses import DBconstructor
from bot.modules.decorators import HDMessage

from bson.objectid import ObjectId
from bson.son import SON

from bot.modules.states_tools import ChooseImageState

users = mongo_client.user.users
dinosaurs = mongo_client.dinosaur.dinosaurs
dino_owners = DBconstructor(mongo_client.dinosaur.dino_owners)
items = DBconstructor(mongo_client.items.items)

@main_router.message(Command(commands=['add_item', 'item_add']), IsAdminUser())
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

@main_router.message(Command(commands=['1xp']), IsAdminUser())
async def command2(message):
    user = message.from_user
    if user.id in conf.bot_devs:
        await experience_enhancement(user.id, 1)
    else:
        print(user.id, 'not in devs')


@main_router.message(Command(commands=['test_img']), IsAdminUser())
async def test_img(message):
    user = message.from_user

    uu = await User().create(user.id)
    dinos = await uu.get_dinos()
    
    dino = dinos[0]
    
    t1_list = []

    for i in range(1000):
        st_t = time()
        res = await create_dino_image_pst(dino.data_id, 
                        {'heal': 0, 'eat': 0, 'energy': 0, 'game': 0, 'mood': 0}, "leg", 1, 30)

        tt = time() - st_t
        # await bot.send_photo(user.id, res, f"test {i} {tt}")
        t1_list.append(tt)
    
    t2_list = []

    for i in range(1000):
        st_t = time()
        res = await create_dino_image(dino.data_id, 
                        {'heal': 0, 'eat': 0, 'energy': 0, 'game': 0, 'mood': 0}, "leg", 1, 30)

        tt = time() - st_t
        # await bot.send_photo(user.id, res, f"test {i} {tt}")
        t2_list.append(tt)
 
    
    t1 = sum(t1_list) / len(t1_list)
    t2 = sum(t2_list) / len(t2_list)
    
    await message.answer(f"t1: {t1:.3f}, t2: {t2:.3f}, diff: {t1-t2:.3f}")

from bot.modules.dungeon.dungeon import Lobby, DungPlayer

@main_router.message(Command(commands=['dung']), IsAdminUser())
async def dung(message):

    m = await bot.send_message(message.from_user.id, "test")
    lobby = await Lobby().create(message.from_user.id, m.message_id)

    pprint(lobby.__dict__)

@main_router.message(Command(commands=['delete']), IsAdminUser())
async def delete(message):

    lobby = await Lobby().FromBase(message.from_user.id)
    await lobby.delete

@main_router.message(Command(commands=['add_to']), IsAdminUser())
async def add_to(message):

    lobby = await Lobby().FromBase(1191252229)

    m = await bot.send_message(message.from_user.id, "test")
    player = await DungPlayer().create(message.from_user.id, m.message_id)
    await lobby.add_player(player, message.from_user.id)

# @main_router.message(Command(commands=['test'])
# @HDMessage
# async def test(message: Message):
    
    # uu = await User().create(message.from_user.id)
    # ld = await uu.get_last_dino()
    
    # await save_kd(ld._id, 'pet', 180)
    # await save_kd(ld._id, 'talk', 3600*2)
    # await save_kd(ld._id, 'fighting', 3600)


    # async for index in users.list_indexes():
    #     index: SON
    #     print(index)
    #     print(dict(index['key']))

    # await users.create_index(())
    
    # resp = users.create_index([ ("field_to_index", -1) ], unique = True)
    
    


@main_router.message(Command(commands=['test']))
@HDMessage
async def test(message: Message):
    
    lang = 'ru'
    userid = message.from_user.id
    chatid = message.chat.id
    
    r = await nextinqueue(userid)
    print(r)


@main_router.message(Command(commands=['test2']))
@HDMessage
async def test2(message: Message):
    st = time()
    print(82323)
    
    await send_SmartPhoto(message.chat.id, 'images/remain/taverna/dino_reward.png', None, 'Markdown', None)
    log(f'test2 {time() - st} MEOW')

@main_router.message(Command(commands=['errr']))
@HDMessage
async def super_test(message: Message):
    
    2 / 0


from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import default_state, StatesGroup, State

class Form(StatesGroup):
    name = State()
    age = State()

@HDMessage
@main_router.message(Command(commands=['check_state']))
async def check(message: Message):
    
    
    state = await get_state(message.from_user.id, message.chat.id)
    await message.answer('ok')
    
    r = await state.get_state()
    d = await state.get_data()
    await message.answer(f"{r} {d}")


@main_router.message(Command(commands=['set_state']))
async def check(message: Message):
    
    await message.answer('ok')
    
    state = await get_state(message.from_user.id, message.chat.id)
    r = await state.set_state(Form.name)
    await state.set_data({'name': message.from_user.id, 'mef': message.chat.id})
    await message.answer(f"{await state.get_state()}")

@main_router.message(Command(commands=['set_state1']))
async def check(message: Message):
    
    await message.answer('ok')
    
    state = await get_state(message.from_user.id, message.chat.id)
    r = await state.set_state(Form.name)

@HDMessage
@main_router.message(Command(commands=['res_state']), StateFilter(Form.name))
async def check(message: Message):
    
    state = await get_state(message.from_user.id, message.chat.id)
    await message.answer('ok')
    await state.clear()

@HDMessage
@main_router.message(Command(commands=['upd_state']), StateFilter(Form.name))
async def check(message: Message):
    state = await get_state(message.from_user.id, message.chat.id)
    await state.update_data(name='new_test')
    
    r = await state.get_state()
    d = await state.get_data()
    await message.answer(f"{r} {d}")

@HDMessage
@main_router.message(Command(commands=['test_limits']), IsAdminUser())
async def check(message: Message):
    
    msg = await message.answer('0')

    for i in range(1, 3001):

        if i % 10 == 0: 
            try:
                itt = await items.find({})
                await msg.edit_text(str(i))
            except Exception as e:
                log(f"ERRRRRRRRRRRRRRRRRRRRRRRRRRRRRRR {e}")


@main_router.message(Command(commands=['save_users']), IsAdminUser())
@HDMessage
async def save_users_handler(message: Message):
    cursor = users.find({}, {"userid": 1})
    with open("bot/data/users.txt", "w", encoding="utf-8") as f:
        async for doc in cursor:
            f.write(str(doc["userid"]) + "\n")
    await message.answer("User IDs saved.")
    


@main_router.message(Command(commands=['size']), IsAdminUser())
@HDMessage
async def size(message: Message):
    
    await ChooseImageState(f, message.from_user.id, message.chat.id, 'ru')
    await bot.send_message(message.from_user.id, 'send photo')


async def f(fileID, transmitted_data: dict):

    file = await bot.get_file(fileID)
    await bot.send_photo(transmitted_data['chatid'], file.file_id, 
                        caption=f'size {file.file_size}'
                        )
