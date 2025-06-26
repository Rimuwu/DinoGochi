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
from random import choice, choices
from asyncio import sleep as asleep

import aiogram
from aiogram.types import (InlineKeyboardButton, InlineKeyboardMarkup,
                           InlineQueryResultContact, Message, LabeledPrice)

from bot.modules.backup.tg_base import send_backup, split_gz_archive
from bot.modules.dino_uniqueness import get_dino_uniqueness_factor
from bot.modules.dinosaur import dinosaur
from bot.modules.egg import Egg
from bot.modules.get_state import get_state
from bot.modules.images_creators.more_dinos import MiniGame_image
from bot.modules.images_save import send_SmartPhoto

from bot.modules.inline import inline_menu
# from bot.modules.items.accessory import downgrade_type_accessory
from bot.modules.items.collect_items import get_all_items
from bot.modules.items.items_groups import get_group
from bot.modules.items.json_item import INC_TYPES, ITEMS
from bot.modules.logs import log

from bot.config import conf
from bot.dbmanager import mongo_client
from bot.const import DINOS, GAME_SETTINGS
from bot.exec import main_router, bot
from bot.modules.companies import nextinqueue, save_message
from bot.modules.data_format import list_to_inline, seconds_to_str, str_to_seconds, item_list
from bot.modules.dinosaur.dinosaur import check_status
from bot.modules.dinosaur.kd_activity import save_kd
from bot.modules.donation import get_history, give_reward, save_donation, send_inv
from bot.modules.images import create_egg_image, create_skill_image, dino_collecting, dino_game
from bot.modules.inventory.inventory_tools import inventory_pages
from bot.modules.items.item import (AddItemToUser, ItemData, get_name, RemoveItemFromUser)
from bot.modules.localization import get_data, get_lang, t
from bot.modules.markup import answer_markup, cancel_markup, count_markup, down_menu, list_to_keyboard, confirm_markup
from bot.modules.notifications import user_notification, notification_manager
from bot.modules.states_fabric.state_handlers import *
from bot.modules.states_fabric.steps_datatype import IntStepData, StepMessage
# from bot.modules.states_tools import ChoosePagesState, ChooseStepState, prepare_steps
from bot.modules.user.advert import auto_ads, show_advert_richads
from bot.modules.user.user import User, max_dino_col, award_premium, count_inventory_items, experience_enhancement, take_coins
from bot.modules.managment.statistic import get_now_statistic, get_simple_graf
from bot.modules.quests import create_quest, quest_ui, save_quest
# from bot.modules.dinosaur.journey import create_event, random_event, activate_event

# from bot.modules.market.market import (ITEMS, add_product, create_seller,
#                                 generate_sell_pages, product_ui, seller_ui)
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
# from bot.modules.items.item import get_data as get_item_data

# from bot.modules.states_tools import ChooseImageState
from bot.tasks.incubation import incubation
from bot.modules.user.dinocollection import add_to_collection_dino

users = mongo_client.user.users
dinosaurs = DBconstructor(mongo_client.dinosaur.dinosaurs)
dino_owners = DBconstructor(mongo_client.dinosaur.dino_owners)
items = DBconstructor(mongo_client.items.items)
management = DBconstructor(mongo_client.other.management)
dead_dinos = DBconstructor(mongo_client.dinosaur.dead_dinos)
inc = DBconstructor(mongo_client.dinosaur.incubation)

@main_router.message(Command(commands=['t1']), 
                     IsAdminUser())
async def t1(message):
    user = message.from_user
    
    code = '1223'
    await ChooseInlineHandler(
        func, user.id, message.chat.id, 'ru', code,
        one_element=False
    ).start()

    mark_list = {
        'b1': f'chooseinline {code} b1',
        'b2': f'chooseinline {code} b2',
        'b3': f'chooseinline {code} b3',
    }
    mark = list_to_inline([mark_list], 2)
    await message.answer(
        'Выберите кнопку', reply_markup=mark
    )

async def func(*args, **kwargs):
    print(args)
    print(kwargs)

@main_router.message(Command(commands=['zd']), 
                     IsAdminUser())
async def zd(message):
    user = message.from_user
    
    for i in ITEMS:
        
        item = ItemData(i)
        await AddItemToUser(user.id, item, 100)

from bot.modules.backup.bd_backup import create_mongo_dump, restore_mongo_dump
from aiogram.types import InputFile, FSInputFile 

@main_router.message(Command(commands=['create_backup']), 
                     IsAdminUser())
async def create_backup(message):
    user = message.from_user
    
    create_mongo_dump()

@main_router.message(Command(commands=['send_last_backup']), 
                     IsAdminUser())
async def send_last_backup(message):
    user = message.from_user

    r = split_gz_archive('/backups/last_mongo_backup.gz')

    await send_backup(
        chat_id=conf.backup_group_id,
        parts=r
    )

async def tt(*args, **kwargs):
    print(args)
    print(kwargs)

@main_router.message(Command(commands=['inl_inv']), 
                     IsAdminUser())
async def inl_inv(message):
    user = message.from_user
    print('start')
    
    st = await ChooseInlineInventory(tt, user.id, message.chat.id, 'ru', 
                                'inv',
                                one_element=True
                                
                                
                                ).start()
    print(st)

@main_router.message(Command(commands=['ra']), 
                     IsAdminUser())
async def ra(message):
    user = message.from_user
    
    await show_advert_richads(user_id=user.id, lang='id')