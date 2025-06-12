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
from time import sleep
from asyncio import sleep as asleep

import aiogram
from aiogram.types import (InlineKeyboardButton, InlineKeyboardMarkup,
                           InlineQueryResultContact, Message, LabeledPrice)

from bot.modules.dino_uniqueness import get_dino_uniqueness_factor
from bot.modules.dinosaur import dinosaur
from bot.modules.get_state import get_state
from bot.modules.images_creators.more_dinos import MiniGame_image
from bot.modules.images_save import send_SmartPhoto

from bot.modules.inline import inline_menu
from bot.modules.items.accessory import downgrade_type_accessory
from bot.modules.items.item_tools import rare_random
from bot.modules.items.items_groups import get_group
from bot.modules.logs import log

from bot.config import conf
from bot.dbmanager import mongo_client
from bot.const import GAME_SETTINGS
from bot.exec import main_router, bot
from bot.modules.companies import nextinqueue, save_message
from bot.modules.data_format import list_to_inline, seconds_to_str, str_to_seconds, item_list
from bot.modules.dinosaur.dinosaur import check_status
from bot.modules.dinosaur.kd_activity import save_kd
from bot.modules.donation import get_history, give_reward, save_donation, send_inv
from bot.modules.images import create_egg_image, create_skill_image, dino_collecting, dino_game
from bot.modules.inventory_tools import inventory_pages
from bot.modules.items.item import (AddItemToUser, DowngradeItem, get_data,
                              get_item_dict, get_name, RemoveItemFromUser)
from bot.modules.localization import get_data, get_lang, t
from bot.modules.markup import answer_markup, cancel_markup, count_markup, down_menu, list_to_keyboard, confirm_markup
from bot.modules.notifications import user_notification, notification_manager
from bot.modules.states_fabric.state_handlers import *
from bot.modules.states_fabric.steps_datatype import IntStepData, StepMessage
# from bot.modules.states_tools import ChoosePagesState, ChooseStepState, prepare_steps
from bot.modules.user.advert import auto_ads
from bot.modules.user.user import User, max_dino_col, award_premium, count_inventory_items, experience_enhancement, take_coins
from bot.modules.managment.statistic import get_now_statistic, get_simple_graf
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
from bot.modules.items.item import get_data as get_item_data

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

            await bot.send_message(message.from_user.id, str(res))
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
from datetime import datetime, timedelta

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
    
    await state.set_data({'name': message.from_user.id, 'mef': message.chat.id})
    await message.answer(f"{await state.get_data()}")

    await state.clear()
    await state.set_state(Form.age)
    await message.answer(f"{await state.get_data()}")

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

# @main_router.message(Command(commands=['size']), IsAdminUser())
# @HDMessage
# async def size(message: Message):
    
#     await ChooseImageState(f, message.from_user.id, message.chat.id, 'ru')
#     await bot.send_message(message.from_user.id, 'send photo')


async def f(fileID, transmitted_data: dict):

    file = await bot.get_file(fileID)
    await bot.send_photo(transmitted_data['chatid'], file.file_id, 
                        caption=f'size {file.file_size}'
                        )


@main_router.message(Command(commands=['dice']), IsAdminUser())
@HDMessage
async def save_users_handler(message: Message):
    r1 = await bot.send_dice(message.from_user.id, emoji='🎲')
    r2 = await bot.send_dice(message.from_user.id, emoji='🎲')
    await bot.send_message(
        chat_id=message.from_user.id,
        text=f"🎲🎲 Results: Dice 1: {r1.dice.value}, Dice 2: {r2.dice.value}"
    )
    
rarity_to_int = {
    "common": 0, "uncommon": 1, 
    "rare": 2, "mystical": 3,
    "legendary": 4, "mythical": 5
}

def sort_f(item_id: str):
    """ Функция сортирует список с id предметов по их редкости
    """
    dt = get_item_data(item_id)
    return rarity_to_int[dt['rank']]

def rare_sort(items: list[str]):
    """ Функция сортирует список с id предметов по их редкости. От обычного к легендарному
    """

    new_list = items.copy()
    new_list.sort(key=lambda x: sort_f(x))

    return new_list

def add_to_rare_sort(items: list[str], item_id: str):
    new_list = items.copy()
    
    dt = get_item_data(item_id)
    if not dt: return items

    rarity = rarity_to_int[dt['rank']]
    for i, item in enumerate(new_list):
        if rarity_to_int[get_item_data(item)['rank']] >= rarity:
            new_list.insert(i, item_id)
            break

    return new_list

# def rare_random(items: list[str], count: int = 1):
#     """Функция выбирает случайные предметы из списка на основе их редкости."""
#     rarity_chances = {
#         "common": 50,
#         "uncommon": 25,
#         "rare": 15,
#         "mystical": 9,
#         "legendary": 1
#     }

#     # Получаем данные о редкости предметов
#     item_chances = [rarity_chances[get_item_data(item)['rank']] for item in items]

#     # Нормализуем шансы
#     total_chance = sum(item_chances)
#     weights = [chance / total_chance for chance in item_chances]

#     # Выбираем случайные предметы
#     selected_items = choices(items, weights=weights, k=count)
#     return selected_items

@main_router.message(Command(commands=['sort_rar']), IsAdminUser())
@HDMessage
async def sort_rar(message: Message):
    
    group = get_group('egg')
    sort_g = rare_sort(group)

    # Проверка на шанс функции rare_random
    item_counts = {item: 0 for item in sort_g}
    iterations = 100_000

    for _ in range(iterations):
        selected_items = rare_random(sort_g, count=5)
        for item in selected_items:
            item_counts[item] += 1

    chances = {item: (count / (iterations * 5)) * 100 for item, count in item_counts.items()}
    result = "\n".join([f"{item}: {chance:.2f}%" for item, chance in chances.items()])
    await message.answer(f"Item chances after {iterations} iterations:\n{result}")

@main_router.message(Command(commands=['donations']), IsAdminUser())
@HDMessage
async def donations(message: Message):

    # Получаем историю донатов за последние 3 дня
    recent_donations = await get_history(timeline=3)

    if not recent_donations:
        await message.answer("За последние 3 дня донатов не было.")
        return

    # Форматируем данные для вывода
    response = "Донаты за последние 3 дня:\n"
    for donation in recent_donations:
        user_id = donation.get("userid", "Неизвестно")
        name = donation.get("username", "Неизвестно")
        amount = donation.get("amount", 0)
        date = datetime.utcfromtimestamp(donation.get("time", 0)).strftime('%Y-%m-%d %H:%M:%S')
        response += f"Пользователь: {user_id} ({name}), Сумма: {amount}⭐, Дата: {date}\n"

    await message.answer(response)

@main_router.message(Command(commands=['incubation']), IsAdminUser())
@HDMessage
async def incubation_d(message: Message):
    
    await inc.update_many({}, {'$set': {'incubation_time': 0}}, comment='incubation_update')
    await incubation()
    

@main_router.message(Command(commands=['downgrade_200']), IsAdminUser())
@HDMessage
async def downgrade(message: Message):
    
    user = await User().create(message.from_user.id)
    dinos = await user.get_dinos()
    if dinos:
        dino = dinos[0]
        await message.answer(f"Первый динозавр: {dino}")
    else:
        await message.answer("У пользователя нет динозавров.")
        return

    await downgrade_type_accessory(dino, 'weapon', 200)


@main_router.message(Command(commands=['downgrade_50']), IsAdminUser())
@HDMessage
async def downgrade(message: Message):
    
    user = await User().create(message.from_user.id)
    dinos = await user.get_dinos()
    if dinos:
        dino = dinos[0]
        await message.answer(f"Первый динозавр: {dino}")
    else:
        await message.answer("У пользователя нет динозавров.")
        return

    await downgrade_type_accessory(dino, 'weapon', 50)

@main_router.message(Command(commands=['downgrade_49']), IsAdminUser())
@HDMessage
async def downgrade(message: Message):
    
    user = await User().create(message.from_user.id)
    dinos = await user.get_dinos()
    if dinos:
        dino = dinos[0]
        await message.answer(f"Первый динозавр: {dino}")
    else:
        await message.answer("У пользователя нет динозавров.")
        return

    await downgrade_type_accessory(dino, 'weapon', 49)

from aiogram.types import StarTransaction

@main_router.message(Command(commands=['story_stars']), IsAdminUser())
@HDMessage
async def story_stars(message: Message):

    res = await bot.get_star_transactions()

    print(res)


@main_router.message(Command(commands=['tets']), IsAdminUser())
@HDMessage
async def test4(message: Message):
    
    fil = await get_simple_graf(days=30, data_type='dinosaurs', filter_mode=None, lang='ru')
    await bot.send_photo(message.from_user.id, fil, caption='test')

@main_router.message(Command(commands=['sdr34']), IsAdminUser())
@HDMessage
async def sdr34(message: Message):
    
    arg = message.text.split()
    if len(arg) < 2:
        await message.answer("Пожалуйста, укажите название группы предметов.")
        return
    else:
        group_name = arg[1]
    
    count = 100000
    if len(arg) > 2:
        try:
            count = int(arg[2])
        except ValueError:
            await message.answer("Некорректное значение для count, используется 100000.")
        
    
    advanced_rank_for_items = {
        # "mystical": ["ink", "skin", "fish_oil", "twigs_tree", "feather", "wool"],
    }

    group = get_group(group_name)
    r = rare_random(group, count=count, advanced_rank_for_items=advanced_rank_for_items)
    
    rare_dct = {}
    for item_id in group:
        item = get_item_data(item_id)
        if item['rank'] not in rare_dct:
            rare_dct[item['rank']] = []
        rare_dct[item['rank']].append(item_id)

    # Подсчёт количества выпадений по редкости
    rarity_counts = {rank: 0 for rank in rare_dct}
    for item_id in r:
        item = get_item_data(item_id)
        rarity_counts[item['rank']] += 1

    # Подсчёт процентов по редкости
    rarity_percents = {rank: (count / len(r)) * 100 for rank, count in rarity_counts.items()}

    # Подсчёт выпадений и процентов по каждому предмету
    item_counts = {item_id: 0 for item_id in group}
    for item_id in r:
        item_counts[item_id] += 1
    item_percents = {item_id: (count / len(r)) * 100 for item_id, count in item_counts.items()}

    # Формируем строку для вывода по редкости
    result = "\n".join([
        f"{rank}: {count} ({rarity_percents[rank]:.2f}%)"
        for rank, count in rarity_counts.items()
    ])

    # Формируем строку для вывода по каждому предмету
    items_result = "\n".join([
        f"{get_item_data(item_id)['rank']} {item_id}: {item_counts[item_id]} ({item_percents[item_id]:.2f}%)"
        for item_id in group
    ])

    items_result = items_result.replace('uncommon', '💚') \
        .replace('common', '🤍') \
        .replace('rare', '💙') \
        .replace('mystical', '💜') \
        .replace('legendary', '🧡') \
        .replace('mythical', '❤️')

    pprint(rarity_counts)
    await message.answer(
        f"Выпадения по редкости из {count}:\n{result}\n\n"
        f"Выпадения по каждому предмету:\n{items_result}"
    )

from bot.modules.items.items import AddItemToUser

@main_router.message(Command(commands=['test_add']), IsAdminUser())
@HDMessage
async def test_add(message: Message):
    user_id = message.from_user.id

    item = await AddItemToUser(user_id, item_id='cookie', count=1)
    await message.answer(f"Добавлен предмет: {item}")