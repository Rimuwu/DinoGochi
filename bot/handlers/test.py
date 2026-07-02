from aiogram.types import CallbackQuery
from bot.modules.overwriting.DataCalsses import LazyCollection
from bot.models.dinosaur import DeadDino, Dino, DinoOwners, Egg
from bot.models.items import Item
from bot.models.other import Management
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
from bot.models import dinosaur
from bot.modules.get_state import get_state
from bot.modules.images_creators.more_dinos import MiniGame_image
from bot.modules.images_save import send_SmartPhoto

from bot.modules.inline import inline_menu
from bot.models.items import Item
from bot.modules.items.item_tools import rare_random
from bot.modules.items.items_groups import get_group
from bot.modules.logs import log

from bot.config import conf
from bot.dbmanager import mongo_client
from bot.const import GAME_SETTINGS
from bot.exec import main_router, bot
from bot.modules.companies import nextinqueue, save_message
from bot.modules.data_format import list_to_inline, seconds_to_str, str_to_seconds, item_list
from bot.models.dinosaur import Dino
from bot.models.activity import KDActivity
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
from bot.modules.user.user import User, max_dino_col, award_premium, count_inventory_items, experience_enhancement
from bot.modules.managment.statistic import get_now_statistic, get_simple_graf
from bot.modules.quests import create_quest, quest_ui, save_quest

from bot.modules.market.market import (ITEMS, add_product, create_seller,
                                generate_sell_pages, product_ui, seller_ui)
from bson.objectid import ObjectId
from bot.modules.images import create_dino_image, create_dino_image_pst, async_open

from bot.models.other import Event

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

from bot.modules.decorators import HDMessage

from bson.objectid import ObjectId
from bson.son import SON
from bot.modules.items.item import get_data as get_item_data

# from bot.modules.states_tools import ChooseImageState
from bot.tasks.incubation import incubation
from bot.modules.user.dinocollection import add_to_collection_dino

users = mongo_client.user.users
dinosaurs = LazyCollection(Dino)
dino_owners = LazyCollection(DinoOwners)
items = LazyCollection(Item)
management = LazyCollection(Management)
dead_dinos = LazyCollection(DeadDino)
inc = LazyCollection(Egg)

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
    
    # await KDActivity.save_kd(ld._id, 'pet', 180)
    # await KDActivity.save_kd(ld._id, 'talk', 3600*2)
    # await KDActivity.save_kd(ld._id, 'fighting', 3600)


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

    await Item.downgrade_type_accessory(dino, 'weapon', 200)


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

    await Item.downgrade_type_accessory(dino, 'weapon', 50)

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

    await Item.downgrade_type_accessory(dino, 'weapon', 49)

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

@main_router.message(Command(commands=['reload_localization', 'reload_loc']), IsAdminUser())
async def reload_localization_cmd(message: Message):
    user = message.from_user
    if user.id in conf.bot_devs:
        from bot.modules.localization import reload as reload_l
        try:
            reload_l()
            await message.answer("✅ Локализация успешно перезагружена с диска!")
        except Exception as e:
            await message.answer(f"❌ Ошибка при перезагрузке локализации: {e}")
    else:
        await message.answer("❌ Нет прав разработчика.")

@main_router.message(Command(commands=['reload_config', 'reload_configs']), IsAdminUser())
async def reload_config_cmd(message: Message):
    user = message.from_user
    if user.id in conf.bot_devs:
        from bot.const import reload_const
        from bot.modules.items.collect_items import reload_items
        try:
            reload_const()
            reload_items()
            await message.answer("✅ Конфиги предметов и константы успешно перезагружены с диска!")
        except Exception as e:
            await message.answer(f"❌ Ошибка при перезагрузке конфигов: {e}")
    else:
        await message.answer("❌ Нет прав разработчика.")

def md_to_html(text: str) -> str:
    import re
    # Escape HTML special characters
    text = text.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")
    # Convert markdown bold to HTML bold
    pattern_bold = re.compile(r'\*(.*?)\*')
    text = pattern_bold.sub(r'<b>\1</b>', text)
    # Convert markdown code to HTML code
    pattern_code = re.compile(r'`(.*?)`')
    text = pattern_code.sub(r'<code>\1</code>', text)
    return text

def format_team_members(members, lang):
    from bot.modules.items.item import get_name
    from bot.modules.localization import t
    lines = []
    for p in members:
        eq = []
        if p.get("weapon"):
            eq.append(get_name(p['weapon'], lang))
        if p.get("shield"):
            eq.append(get_name(p['shield'], lang))
        eq_str = f" ({', '.join(eq)})" if eq else ""
        
        name = p['name']
        if p.get("type") == "mob" and p.get("mob_id"):
            translated = t(f"mobs.{p['mob_id']}.name", lang)
            if "mobs." not in translated:
                name = translated
            else:
                name = p['mob_id'].capitalize()
            mob_emoji = t(f"mobs.{p['mob_id']}.emoji", lang)
            if "mobs." in mob_emoji or not mob_emoji:
                mob_emoji = "👾"
            name = f"{mob_emoji} {name}"
        else:
            for suffix in [" (X)", " (Y)"]:
                if name.endswith(suffix):
                    name = name[:-len(suffix)]
                
        cleaned_name = name.replace('_', ' ')
        lines.append(f"• *{cleaned_name}* (HP: {int(p['hp'])}/{int(p['max_hp'])}){eq_str}")
    return "\n".join(lines)

@main_router.message(Command(commands=['test_combat']))
async def test_combat_cmd(message: Message):
    import uuid
    from bot.modules.combat.auto_combat import AutoCombat, generate_opponents, CombatParticipant
    from bot.redismanager import redis_set
    from bot.models.user import User
    from bot.models.items import Item
    from bson import ObjectId

    userid = message.from_user.id
    lang = 'ru'
    db_user = await User.find_one(User.userid == userid)
    if db_user:
        lang = db_user.settings.get('lang', 'ru')

    # Parse arguments
    args = message.text.split()[1:]
    count = 1
    preferred_types = []
    
    if args:
        try:
            count = int(args[0])
            preferred_types = args[1:]
        except ValueError:
            preferred_types = args
            count = len(preferred_types)

    # Get user's active dinosaur
    dino_obj = None
    if db_user:
        dino_obj = await db_user.get_last_dino()

    # Create participant list
    team_x = []
    if dino_obj:
        # Fetch user's inventory items to pass to dinosaur (for healing)
        db_items = await Item.find(Item.owner_id == userid).to_list()
        inventory_ids = [item.id for item in db_items]
        dino_part = await CombatParticipant.from_dino(dino_obj, inventory_ids)
        team_x.append(dino_part)
    else:
        # Fallback Mock Dinosaur
        mock_dino = CombatParticipant(
            unique_id=f"mock_dino_{userid}",
            name="TestDinoCarry",
            participant_type="dino",
            max_hp=100.0,
            hp=100.0,
            max_energy=100.0,
            energy=100.0,
            stats={"power": 12.0, "dexterity": 10.0, "intelligence": 12.0, "charisma": 10.0},
            role="carry",
            weapon={
                "item_id": "bone_sword",
                "abilities": {"lvl": 0, "endurance": 50}
            },
            shield={
                "item_id": "wood_shield",
                "abilities": {"lvl": 0, "endurance": 120}
            },
            inventory=[
                {
                    "item_id": "therapeutic_mixture",
                    "count": 3
                }
            ]
        )
        team_x.append(mock_dino)

    # Generate Y team
    try:
        team_y = generate_opponents(count, preferred_types, total_danger=1.0)
    except Exception as e:
        await message.answer(f"❌ Ошибка генерации противников: {e}")
        return

    if not team_y:
        await message.answer("❌ Не удалось сгенерировать противников.")
        return

    # Suffix team names to make turn order logs clear
    for p in team_x:
        p.name = f"{p.name} (X)"
    for p in team_y:
        p.name = f"{p.name} (Y)"

    # Run combat
    try:
        combat = AutoCombat(team_x, team_y)
        result = combat.run()
        
        # Save to Redis (1 day TTL)
        combat_log_id = f"combat_log:{uuid.uuid4().hex}"
        await redis_set(combat_log_id, result, ex=86400)
        
        # Sync to DB
        await combat.sync_to_database()
    except Exception as e:
        await message.answer(f"❌ Ошибка в ходе автобоя: {e}")
        return

    # Format summary
    winner_val = "A" if result["winner"] == "X" else "B" if result["winner"] == "Y" else result["winner"]
    try:
        winner_msg = t("combat_log.battle_end", lang, winner_team=winner_val)
        reason_msg = t(result["reason_key"], lang)
    except Exception:
        winner_msg = f"\n🏆 *Бой завершен! Победила команда {winner_val}!*"
        reason_msg = f"\n💀 Все противники выбыли."

    team_x_str = format_team_members(result["starting_data"]["X"], lang)
    team_y_str = format_team_members(result["starting_data"]["Y"], lang)
    try:
        teams_info = t("combat_log.team_info_header", lang, team_x=team_x_str, team_y=team_y_str)
    except Exception:
        teams_info = f"👥 *Составы команд:*\n🟢 Команда X:\n{team_x_str}\n🔴 Команда Y:\n{team_y_str}"

    summary_text = f"🎮 *Автобой завершен!*\n" \
                   f"📝 *Причина окончания:* {reason_msg}\n" \
                   f"{winner_msg}\n\n" \
                   f"{teams_info}"
    
    if result["loot"]:
        from bot.modules.items.item import get_name
        from collections import Counter
        counts = Counter(result["loot"])
        translated_loot = []
        for item_id, count in counts.items():
            translated_name = get_name(item_id, lang)
            if count > 1:
                translated_loot.append(f"{translated_name} x{count}")
            else:
                translated_loot.append(translated_name)
        try:
            loot_msg = t("combat_log.loot_dropped", lang, loot_list=", ".join(translated_loot))
        except Exception:
            loot_msg = f"\n🎁 *Получен лут:* {', '.join(translated_loot)}"
        summary_text += f"\n{loot_msg}"
        
    summary_text += f"\n\n🔑 *Redis ID:* `{combat_log_id}` (24h TTL)"

    # Inline button
    from aiogram.utils.keyboard import InlineKeyboardBuilder
    from aiogram.types import InlineKeyboardButton

    builder = InlineKeyboardBuilder()
    builder.add(InlineKeyboardButton(
        text=t("combat_log.buttons.view_log", lang, default="📝 Лог боя"),
        callback_data=f"combat_log_view {combat_log_id} 0"
    ))

    html_summary = md_to_html(summary_text)
    await message.answer(html_summary, reply_markup=builder.as_markup(), parse_mode="HTML")


@main_router.message(Command(commands=['test_mob_combat', 'mob_combat']))
async def test_mob_combat_cmd(message: Message):
    import uuid
    from bot.modules.combat.auto_combat import AutoCombat, generate_opponents
    from bot.redismanager import redis_set
    from bot.models.user import User

    userid = message.from_user.id
    lang = 'ru'
    db_user = await User.find_one(User.userid == userid)
    if db_user:
        lang = db_user.settings.get('lang', 'ru')

    # Parse arguments
    args = message.text.split()[1:]
    count_x = 3
    count_y = 3
    
    if args:
        try:
            count_x = int(args[0])
            if len(args) > 1:
                count_y = int(args[1])
            else:
                count_y = count_x
        except ValueError:
            pass

    # Generate teams
    try:
        team_x = generate_opponents(count_x, total_danger=1.0)
        team_y = generate_opponents(count_y, total_danger=1.0)
    except Exception as e:
        await message.answer(f"❌ Ошибка генерации мобов: {e}")
        return

    if not team_x or not team_y:
        await message.answer("❌ Не удалось сгенерировать команды мобов.")
        return

    # Suffix team names
    for p in team_x:
        p.name = f"{p.name} (X)"
    for p in team_y:
        p.name = f"{p.name} (Y)"

    # Run combat (NO DB sync since they are just random mobs)
    try:
        combat = AutoCombat(team_x, team_y)
        result = combat.run()
        
        # Save to Redis (1 day TTL)
        combat_log_id = f"combat_log:{uuid.uuid4().hex}"
        await redis_set(combat_log_id, result, ex=86400)
    except Exception as e:
        await message.answer(f"❌ Ошибка в ходе автобоя мобов: {e}")
        return

    # Format summary
    winner_val = "A" if result["winner"] == "X" else "B" if result["winner"] == "Y" else result["winner"]
    try:
        winner_msg = t("combat_log.battle_end", lang, winner_team=winner_val)
        reason_msg = t(result["reason_key"], lang)
    except Exception:
        winner_msg = f"\n🏆 *Бой завершен! Победила команда {winner_val}!*"
        reason_msg = f"\n💀 Все противники выбыли."

    team_x_str = format_team_members(result["starting_data"]["X"], lang)
    team_y_str = format_team_members(result["starting_data"]["Y"], lang)
    try:
        teams_info = t("combat_log.team_info_header", lang, team_x=team_x_str, team_y=team_y_str)
    except Exception:
        teams_info = f"👥 *Составы команд:*\n🟢 Команда X:\n{team_x_str}\n🔴 Команда Y:\n{team_y_str}"

    summary_text = f"🤖 *PvP Бой Моб vs Моб завершен!*\n" \
                   f"📝 *Причина окончания:* {reason_msg}\n" \
                   f"{winner_msg}\n\n" \
                   f"{teams_info}" \
                   f"\n\n🔑 *Redis ID:* `{combat_log_id}` (24h TTL)"

    # Inline button
    from aiogram.utils.keyboard import InlineKeyboardBuilder
    from aiogram.types import InlineKeyboardButton

    builder = InlineKeyboardBuilder()
    builder.add(InlineKeyboardButton(
        text=t("combat_log.buttons.view_log", lang, default="📝 Лог боя"),
        callback_data=f"combat_log_view {combat_log_id} 0"
    ))

    html_summary = md_to_html(summary_text)
    await message.answer(html_summary, reply_markup=builder.as_markup(), parse_mode="HTML")


@main_router.callback_query(F.data.startswith('combat_log_view'))
async def combat_log_view_call(callback: CallbackQuery):
    from aiogram.types import CallbackQuery
    from aiogram.utils.keyboard import InlineKeyboardBuilder
    from aiogram.types import InlineKeyboardButton
    from bot.redismanager import redis_get
    from bot.models.user import User
    from bot.modules.combat.auto_combat import AutoCombat

    chatid = callback.message.chat.id
    lang = 'ru'
    db_user = await User.find_one(User.userid == callback.from_user.id)
    if db_user:
        lang = db_user.settings.get('lang', 'ru')
        
    data = callback.data.split()
    log_id = data[1]
    page_idx = int(data[2]) if len(data) > 2 else 0

    result = await redis_get(log_id)
    if not result:
        await callback.answer("❌ Лог боя не найден или его срок действия (24 часа) истек.", show_alert=True)
        return

    # Convert and group logs into text rounds using AutoCombat static helper
    round_logs = AutoCombat.group_and_format_log(result, lang)

    rounds_list = sorted(round_logs.keys())
    if not rounds_list:
        rounds_list = [1]
        round_logs = {1: []}

    page_idx = max(0, min(page_idx, len(rounds_list) - 1))
    target_round = rounds_list[page_idx]
    round_entries = round_logs.get(target_round, [])

    # Format page content
    log_lines = []
    
    # Translate header
    header = t("combat_log.header", lang, page=page_idx + 1, pages=len(rounds_list))
    log_lines.append(header)

    # Prepend starting team info on page 0
    if page_idx == 0:
        team_x_str = format_team_members(result["starting_data"]["X"], lang)
        team_y_str = format_team_members(result["starting_data"]["Y"], lang)
        try:
            teams_info = t("combat_log.team_info_header", lang, team_x=team_x_str, team_y=team_y_str)
        except Exception:
            teams_info = f"👥 *Составы команд:*\n🟢 Команда X:\n{team_x_str}\n🔴 Команда Y:\n{team_y_str}"
        log_lines.append(teams_info + "\n")

    log_lines.extend(round_entries)

    # If it is the last page, append final battle_end and loot if not present
    if page_idx == len(rounds_list) - 1:
        end_key = "combat_log.battle_end"
        if not any("winner_team" in line or "Победила" in line or "victorious" in line for line in round_entries):
            winner_val = "A" if result["winner"] == "X" else "B" if result["winner"] == "Y" else result["winner"]
            try:
                log_lines.append(t(end_key, lang, winner_team=winner_val))
            except Exception:
                log_lines.append(f"\n🏆 *Бой завершен! Победила команда {winner_val}!*")
            if result["loot"]:
                from bot.modules.items.item import get_name
                from collections import Counter
                counts = Counter(result["loot"])
                translated_loot = []
                for item_id, count in counts.items():
                    translated_name = get_name(item_id, lang)
                    if count > 1:
                        translated_loot.append(f"{translated_name} x{count}")
                    else:
                        translated_loot.append(translated_name)
                try:
                    log_lines.append(t("combat_log.loot_dropped", lang, loot_list=", ".join(translated_loot)))
                except Exception:
                    log_lines.append(f"\n🎁 *Получен лут:* {', '.join(translated_loot)}")

    full_text = "\n".join(log_lines)

    # Build navigation keyboard
    kb_builder = InlineKeyboardBuilder()
    buttons_row = []
    
    if page_idx > 0:
        buttons_row.append(InlineKeyboardButton(
            text=t("combat_log.buttons.back", lang, default="◀️ Назад"),
            callback_data=f"combat_log_view {log_id} {page_idx - 1}"
        ))
        
    buttons_row.append(InlineKeyboardButton(
        text=t("combat_log.buttons.page", lang, page=page_idx + 1, pages=len(rounds_list), default=f"Раунд {page_idx + 1}/{len(rounds_list)}"),
        callback_data=" "
    ))

    if page_idx < len(rounds_list) - 1:
        buttons_row.append(InlineKeyboardButton(
            text=t("combat_log.buttons.next", lang, default="Вперед ▶️"),
            callback_data=f"combat_log_view {log_id} {page_idx + 1}"
        ))

    kb_builder.row(*buttons_row)
    kb_builder.row(InlineKeyboardButton(
        text=t("combat_log.buttons.close", lang, default="❌ Закрыть"),
        callback_data="combat_log_close"
    ))

    try:
        html_text = md_to_html(full_text)
        await callback.message.edit_text(
            html_text,
            reply_markup=kb_builder.as_markup(),
            parse_mode="HTML"
        )
    except Exception as e:
        import traceback
        traceback.print_exc()
        await callback.answer(f"❌ Ошибка отображения лога: {e}", show_alert=True)

@main_router.callback_query(F.data == 'combat_log_close')
async def combat_log_close_call(callback: CallbackQuery):
    try:
        await callback.message.delete()
    except Exception:
        await callback.answer()