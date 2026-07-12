
from bot.models.dinosaur import DeadDino, Dino, DinoOwners, Egg
from bot.models.items import Item
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
from bot.modules.user.user import User, count_inventory_items
from bot.modules.managment.statistic import get_now_statistic, get_simple_graf
from bot.modules.quests import create_quest, quest_ui, save_quest

from bot.modules.market.market import (ITEMS, add_product, create_seller,
                                generate_sell_pages, product_ui, seller_ui)
from bson.objectid import ObjectId
from bot.modules.images import create_dino_image, create_dino_image_pst, async_open

from bot.models.other import Event



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


from bson.objectid import ObjectId
from bson.son import SON
from bot.modules.items.item import get_data as get_item_data

from bot.tasks.incubation import incubation

users = mongo_client.user.users


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
        uu = await User.find_one(User.userid == user.id)
        if uu:
            await uu.add_xp_lvl(1)
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


# @main_router.message(Command(commands=['test'])
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
async def test(message: Message):
    
    lang = 'ru'
    userid = message.from_user.id
    chatid = message.chat.id
    
    r = await nextinqueue(userid)
    print(r)


@main_router.message(Command(commands=['test2']))
async def test2(message: Message):
    st = time()
    print(82323)
    
    await send_SmartPhoto(message.chat.id, 'images/remain/taverna/dino_reward.png', None, 'Markdown', None)
    log(f'test2 {time() - st} MEOW')

@main_router.message(Command(commands=['errr']))
async def super_test(message: Message):
    
    2 / 0


from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import default_state, StatesGroup, State
from datetime import datetime, timedelta

class Form(StatesGroup):
    name = State()
    age = State()

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

@main_router.message(Command(commands=['res_state']), StateFilter(Form.name))
async def check(message: Message):
    
    state = await get_state(message.from_user.id, message.chat.id)
    await message.answer('ok')
    await state.clear()

@main_router.message(Command(commands=['upd_state']), StateFilter(Form.name))
async def check(message: Message):
    state = await get_state(message.from_user.id, message.chat.id)
    await state.update_data(name='new_test')
    
    r = await state.get_state()
    d = await state.get_data()
    await message.answer(f"{r} {d}")

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
# async def size(message: Message):
    
#     await ChooseImageState(f, message.from_user.id, message.chat.id, 'ru')
#     await bot.send_message(message.from_user.id, 'send photo')


async def f(fileID, transmitted_data: dict):

    file = await bot.get_file(fileID)
    await bot.send_photo(transmitted_data['chatid'], file.file_id, 
                        caption=f'size {file.file_size}'
                        )


@main_router.message(Command(commands=['dice']), IsAdminUser())
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
async def incubation_d(message: Message):
    
    await inc.update_many({}, {'$set': {'incubation_time': 0}}, comment='incubation_update')
    await incubation()
    

@main_router.message(Command(commands=['downgrade_200']), IsAdminUser())
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
async def story_stars(message: Message):

    res = await bot.get_star_transactions()

    print(res)


@main_router.message(Command(commands=['tets']), IsAdminUser())
async def test4(message: Message):
    
    fil = await get_simple_graf(days=30, data_type='dinosaurs', filter_mode=None, lang='ru')
    await bot.send_photo(message.from_user.id, fil, caption='test')

@main_router.message(Command(commands=['sdr34']), IsAdminUser())
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

from aiogram.filters import CommandObject

@main_router.message(Command(commands=['force_event']), IsAdminUser())
async def force_event_cmd(message: Message, command: CommandObject):
    user = message.from_user
    if user.id not in conf.bot_devs:
        await message.answer("❌ Нет прав разработчика.")
        return

    args = command.args
    if not args:
        await message.answer("❌ Формат: /force_event <journey_id> <event_name>")
        return

    parts = args.strip().split()
    if len(parts) < 2:
        await message.answer("❌ Формат: /force_event <journey_id> <event_name>")
        return

    try:
        from bson import ObjectId
        journey_id = ObjectId(parts[0])
    except Exception:
        await message.answer("❌ Неверный формат ObjectID.")
        return

    event_name = parts[1]

    from bot.models.activity import JourneyActivity
    from bot.models.activity.journey import events
    
    if event_name not in events:
        await message.answer(f"❌ Событие '{event_name}' не найдено в конфигурации.")
        return

    journey = await JourneyActivity.find_one(JourneyActivity.id == journey_id)
    if not journey:
        await message.answer("❌ Активность путешествия не найдена.")
        return

    # Generate event structure
    from random import choice, choices, randint
    import time
    from bot.models.activity.journey import choice_events_pool
    
    ev_cfg = events[event_name]
    is_choice = ev_cfg.get("is_choice", False)
    is_battle = event_name in ["battle", "cave_bat", "oasis_camel", "shark_attack"]
    ev_type = "choice" if is_choice else ("battle" if is_battle else "standard")

    from bot.models.dinosaur import Dino
    dinos = [await Dino().create(d_id) for d_id in journey.dino_ids]
    dinos = [d for d in dinos if d]
    affected_dino = choice(dinos) if dinos else None

    if ev_type == "choice":
        choice_cfg = None
        for c in choice_events_pool:
            if c["key"] == event_name:
                choice_cfg = c
                break
        if not choice_cfg:
            choice_cfg = {
                "key": event_name,
                "options_count": ev_cfg.get("options_count", 2),
                "outcomes": ev_cfg.get("outcomes", [])
            }
        event_dict = choice_cfg
    elif ev_type == "battle":
        if event_name == "cave_bat":
            mobs_list = ["bat"]
        elif event_name == "oasis_camel":
            mobs_list = ["camel"]
        elif event_name == "shark_attack":
            mobs_list = ["shark"]
        else:
            from bot.models.activity.journey import locations
            mobs_cfg = locations.get(journey.location, {}).get("mobs", {})
            mob_names = mobs_cfg.get("mobs", ["crocodile"])
            mobs_list = [choice(mob_names) for _ in range(randint(1, 2))]
        event_dict = {
            "type": event_name,
            "location": journey.location,
            "sub_location": None,
            "depth": 0,
            "mobs": mobs_list
        }
    else:
        outcomes = ev_cfg.get("outcomes", [])
        selected_outcome = None
        fallback_outcomes = [out for out in outcomes if "requirements" not in out]
        if fallback_outcomes:
            out_weights = [out.get("weight", 100) for out in fallback_outcomes]
            selected_outcome = choices(fallback_outcomes, weights=out_weights)[0]
        elif outcomes:
            selected_outcome = outcomes[0].get("success", outcomes[0])
        else:
            selected_outcome = {"story_key": "success"}

        items_add = JourneyActivity.roll_items_to_add(selected_outcome.get("items_add", []))
        event_dict = {
            "type": event_name,
            "location": journey.location,
            "sub_location": None,
            "depth": 0,
            "story_key": selected_outcome.get("story_key", "success"),
            "affected_dino_id": str(affected_dino.id) if affected_dino else None,
            "dino_edit": selected_outcome.get("dino_edit", {}),
            "coins": selected_outcome.get("coins", 0),
            "items_add": items_add,
            "items_remove": selected_outcome.get("items_remove", [])
        }
        if "change_location" in selected_outcome:
            event_dict["change_location"] = selected_outcome["change_location"]

    ev = {
        "tick_index": len(journey.pregenerated_events) + 1,
        "trigger_time": int(time.time()),
        "status": "pending",
        "type": ev_type,
        "event_data": event_dict
    }

    # Append to journey and save
    journey.pregenerated_events.append(ev)
    journey.pregenerated_events = [e.copy() for e in journey.pregenerated_events]
    await journey.save()

    # Trigger immediately
    try:
        if ev_type == "standard":
            await JourneyActivity.trigger_standard_event(journey, ev)
        elif ev_type == "battle":
            await JourneyActivity.trigger_battle_event(journey, ev)
        elif ev_type == "choice":
            await JourneyActivity.trigger_choice_event(journey, ev)

        from bot.modules.localization import get_lang
        lang = await get_lang(message.from_user.id)

        entry = ev.get("event_data", {}).copy()
        entry["type"] = entry.get("type", ev.get("type"))
        if ev_type == "choice":
            entry["type"] = "choice"
        elif ev_type == "battle":
            entry["type"] = "battle"
        entry["tick_index"] = ev.get("tick_index")
        entry["trigger_time"] = ev.get("trigger_time")

        event_text = await JourneyActivity.generate_event_message(entry, lang, journey.id)
        await message.answer(f"✅ Успешно сгенерировано и активировано событие <b>{event_name}</b> ({ev_type}):\n\n{event_text}", parse_mode="HTML")
    except Exception as e:
        await message.answer(f"❌ Ошибка при активации события: {e}")

@main_router.message(Command(commands=['next_event']), IsAdminUser())
async def force_next_event_cmd(message: Message, command: CommandObject):
    user = message.from_user
    if user.id not in conf.bot_devs:
        await message.answer("❌ Нет прав разработчика.")
        return

    args = command.args
    if not args:
        await message.answer("❌ Формат: /next_event <journey_id> [count]")
        return

    parts = args.strip().split()
    try:
        from bson import ObjectId
        journey_id = ObjectId(parts[0])
    except Exception:
        await message.answer("❌ Неверный формат ObjectID.")
        return

    count = 1
    if len(parts) > 1:
        try:
            count = max(1, int(parts[1]))
        except Exception:
            await message.answer("❌ Второй аргумент (количество) должен быть числом.")
            return

    from bot.models.activity import JourneyActivity
    journey = await JourneyActivity.find_one(JourneyActivity.id == journey_id)
    if not journey:
        await message.answer("❌ Активность путешествия не найдена.")
        return

    results = []
    for _ in range(count):
        # Reload journey each iteration to get updated state
        journey = await JourneyActivity.find_one(JourneyActivity.id == journey_id)
        if not journey:
            break

        # Find first pending event
        ev = None
        for item in journey.pregenerated_events:
            if item.get("status") == "pending":
                ev = item
                break

        if not ev:
            results.append("❌ Нет событий в статусе 'pending'.")
            break

        try:
            if ev.get("type") == "standard":
                await JourneyActivity.trigger_standard_event(journey, ev)
            elif ev.get("type") == "battle":
                await JourneyActivity.trigger_battle_event(journey, ev)
            elif ev.get("type") == "choice":
                await JourneyActivity.trigger_choice_event(journey, ev)

            from bot.modules.localization import get_lang
            lang = await get_lang(message.from_user.id)

            entry = ev.get("event_data", {}).copy()
            entry["type"] = entry.get("type", ev.get("type"))
            if ev.get("type") == "choice":
                entry["type"] = "choice"
            elif ev.get("type") == "autofeed":
                entry["type"] = "autofeed"
            elif ev.get("type") == "battle":
                entry["type"] = "battle"
            entry["tick_index"] = ev.get("tick_index")
            entry["trigger_time"] = ev.get("trigger_time")

            event_text = await JourneyActivity.generate_event_message(entry, lang, journey.id)
            results.append(f"✅ <b>{ev.get('type')}</b>\n{event_text}")
        except Exception as e:
            results.append(f"❌ Ошибка: {e}")
            break

    summary = f"<b>Запущено {len(results)} событий:</b>\n\n" + "\n\n---\n\n".join(results)
    await message.answer(summary, parse_mode="HTML")


@main_router.message(Command(commands=['zero_journey_time']), IsAdminUser())
async def zero_journey_time_cmd(message: Message, command: CommandObject):
    user = message.from_user
    if user.id not in conf.bot_devs:
        await message.answer("❌ Нет прав разработчика.")
        return

    args = command.args
    if not args:
        await message.answer("❌ Формат: /zero_journey_time <journey_id>")
        return

    from bson import ObjectId
    try:
        journey_id = ObjectId(args.strip())
    except Exception:
        await message.answer("❌ Неверный формат ObjectID.")
        return

    from bot.models.activity import JourneyActivity
    journey = await JourneyActivity.find_one(JourneyActivity.id == journey_id)
    if not journey:
        await message.answer("❌ Активность путешествия не найдена.")
        return

    # Find the next pending event
    next_ev = None
    for ev in journey.pregenerated_events:
        if ev.get("status") == "pending":
            next_ev = ev
            break

    if not next_ev:
        await message.answer("❌ В путешествии больше нет pending событий.")
        return

    # 1. Use redis_get to retrieve task_id cleanly without JSON quotes
    from bot.redismanager import get_redis, redis_get, redis_set
    resource_id = f"journey_event:{journey.id}"
    task_id = await redis_get(f"task:resource:{resource_id}")

    if not task_id:
        await message.answer("❌ Задача в редисе для этого путешествия не найдена.")
        return

    task_id = str(task_id)
    redis_client = get_redis()

    # 2. Update task score (run_at) in the sorted set queue to 0
    await redis_client.zadd("task:queue", {task_id: 0})

    # 3. Update the run_at field inside the payload to 0
    payload = await redis_get(f"task:data:{task_id}")
    if isinstance(payload, dict):
        payload["run_at"] = 0
        await redis_set(f"task:data:{task_id}", payload, ex=86400 * 2)

    await message.answer(
        f"✅ Скор задачи в Redis изменен на 0 для события {next_ev.get('type')} (ID: {task_id}). Она будет обработана очередью мгновенно.",
        parse_mode="HTML"
    )


@main_router.message(Command(commands=['overload_training']), IsAdminUser())
async def overload_training_cmd(message: Message, command: CommandObject):
    import time
    user = message.from_user
    if user.id not in conf.bot_devs:
        await message.answer("❌ Нет прав разработчика.")
        return

    percent = 25
    args = command.args
    if args:
        try:
            percent = int(args.strip())
        except ValueError:
            await message.answer("❌ Неверный формат процентов. Пример: /overload_training 25")
            return

    from bot.models.activity.training import TrainingActivity
    training = await TrainingActivity.find_one(TrainingActivity.userid == user.id)
    if not training:
        await message.answer("❌ У вас нет активных тренировок.")
        return

    max_time = training.max_time
    training_time = max_time + percent * (max_time // 100)
    start_time = int(time.time()) - training_time
    last_check = int(time.time()) - 601

    training.start_time = start_time
    training.last_check = last_check
    await training.save()

    from bot.tasks.skills import skills_work
    await skills_work()

    await message.answer(
        f"✅ Время старта тренировки изменено для перегрузки на {percent}%.\n"
        f"Задача <code>skills_work</code> успешно вызвана.",
        parse_mode="HTML"
    )


@main_router.message(Command(commands=['pack_emoji_ids', 'pack_emojis']), IsAdminUser())
async def get_pack_emoji_ids_cmd(message: Message):
    user = message.from_user
    if user.id not in conf.bot_devs:
        await message.answer("❌ Нет прав разработчика.")
        return

    entities = message.entities or []
    custom_emojis = [e for e in entities if e.type == "custom_emoji"]
    if not custom_emojis:
        await message.answer("❌ Отправьте команду и хотя бы один кастомный эмодзи из пака в качестве аргумента.")
        return

    first_emoji = custom_emojis[0]
    emoji_id = first_emoji.custom_emoji_id

    try:
        stickers = await bot.get_custom_emoji_stickers([emoji_id])
        if not stickers:
            await message.answer("❌ Не удалось получить информацию об эмодзи от Telegram.")
            return
        
        sticker = stickers[0]
        set_name = getattr(sticker, 'set_name', None)
        if not set_name:
            await message.answer("❌ Этот кастомный эмодзи не принадлежит к известному паку (sticker set).")
            return

        sticker_set = await bot.get_sticker_set(name=set_name)
        
        results = [f"📦 <b>Пак:</b> {sticker_set.title} (<code>{set_name}</code>)\n"]
        for st in sticker_set.stickers:
            st_emoji = getattr(st, 'emoji', '')
            st_custom_id = getattr(st, 'custom_emoji_id', None)
            if st_custom_id:
                results.append(f"<tg-emoji emoji-id=\"{st_custom_id}\">{st_emoji}</tg-emoji> | <code>{st_custom_id}</code>")
            else:
                results.append(f"{st_emoji} | (нет custom_emoji_id)")

        output = "\n".join(results)
        if len(output) > 4000:
            for i in range(0, len(output), 4000):
                await message.answer(output[i:i+4000], parse_mode="HTML")
        else:
            await message.answer(output, parse_mode="HTML")

    except Exception as e:
        await message.answer(f"❌ Ошибка при получении пака: {e}")


@main_router.message(Command(commands=['show_emoji', 'emoji_show']), IsAdminUser())
async def show_emoji_cmd(message: Message):
    user = message.from_user
    if user.id not in conf.bot_devs:
        await message.answer("❌ Нет прав разработчика.")
        return

    msg_args = message.text.split()
    if len(msg_args) < 2:
        await message.answer("❌ Формат: /show_emoji <emoji_id>")
        return

    emoji_id = msg_args[1].strip()
    if not emoji_id.isdigit():
        await message.answer("❌ ID эмодзи должен быть числом.")
        return

    try:
        stickers = await bot.get_custom_emoji_stickers([emoji_id])
        emoji_char = stickers[0].emoji if stickers else "⭐"
        
        text = (
            f"Rendered: <tg-emoji emoji-id=\"{emoji_id}\">{emoji_char}</tg-emoji>\n"
            f"HTML: <code>&lt;tg-emoji emoji-id=\"{emoji_id}\"&gt;{emoji_char}&lt;/tg-emoji&gt;</code>\n"
            f"MarkdownV2: <code>![{emoji_char}](tg://emoji?id={emoji_id})</code>"
        )
        await message.answer(text, parse_mode="HTML")
    except Exception as e:
        await message.answer(f"❌ Ошибка при отображении эмодзи: {e}")


@main_router.message(Command(commands=['emoji_id', 'get_emoji_id']), IsAdminUser())
async def get_emoji_id_cmd(message: Message):
    user = message.from_user
    if user.id not in conf.bot_devs:
        await message.answer("❌ Нет прав разработчика.")
        return

    entities = message.entities or []
    custom_emojis = [e for e in entities if e.type == "custom_emoji"]
    if not custom_emojis:
        await message.answer("❌ В сообщении не найдено кастомных эмодзи. Отправьте команду вместе с кастомными эмодзи.")
        return

    text = message.text
    results = []
    for entity in custom_emojis:
        offset = entity.offset
        length = entity.length
        emoji_char = text[offset:offset+length]
        emoji_id = entity.custom_emoji_id
        results.append(f"{emoji_char} | ID: <code>{emoji_id}</code>")

    await message.answer("\n".join(results), parse_mode="HTML")


@main_router.message(Command(commands=['sync_emoji_packs']), IsAdminUser())
async def sync_emoji_packs_cmd(message: Message):
    """Создаёт/обновляет стикерпаки по конфигу manage в custom_emojis.json, сохраняет ID."""
    user = message.from_user
    if user.id not in conf.bot_devs:
        await message.answer("❌ Нет прав разработчика.")
        return

    await message.answer("⏳ Синхронизация пакетов эмодзи...")

    from bot.modules.emoji_packs import sync_emoji_packs
    owner_id = conf.bot_devs[0]

    try:
        report_lines = await sync_emoji_packs(owner_id, 'bot/json/custom_emojis.json')
        await message.answer("⏳ Синхронизация пакетов эмодзи предметов...")
        report_lines_items = await sync_emoji_packs(owner_id, 'bot/json/items_custom_emojis.json')
        report_lines.extend(report_lines_items)
    except Exception as e:
        await message.answer(f"❌ Критическая ошибка: {e}")
        return

    chunks = []
    current_chunk = []
    current_len = 0
    for line in report_lines:
        if current_len + len(line) + 1 > 4000:
            if current_chunk:
                chunks.append("\n".join(current_chunk))
            current_chunk = [line]
            current_len = len(line)
        else:
            current_chunk.append(line)
            current_len += len(line) + 1
    if current_chunk:
        chunks.append("\n".join(current_chunk))

    for chunk in chunks:
        if chunk.strip():
            await message.answer(chunk, parse_mode="HTML")


@main_router.message(Command(commands=['list_custom_emojis']), IsAdminUser())
async def list_custom_emojis_cmd(message: Message):
    """Выводит все кастомные эмодзи с названиями, ID и альтернативами."""
    user = message.from_user
    if user.id not in conf.bot_devs:
        await message.answer("❌ Нет прав разработчика.")
        return

    from bot.const import CUSTOM_EMOJIS

    if not CUSTOM_EMOJIS:
        await message.answer("ℹ️ CUSTOM_EMOJIS пуст.")
        return

    lines = ["<b>🎨 Кастомные эмодзи:</b>\n"]
    for name, data in CUSTOM_EMOJIS.items():
        emoji_id = data.get('id')
        alternatives = data.get('alternatives', [])
        manage = data.get('manage')

        alt_str = " | ".join(alternatives) if alternatives else "—"

        if emoji_id and str(emoji_id) != 'null':
            alt_display = alternatives[0] if alternatives else "⭐"
            rendered = f"<tg-emoji emoji-id=\"{emoji_id}\">{alt_display}</tg-emoji>"
            id_str = f"<code>{emoji_id}</code>"
        else:
            rendered = "❓ (нет ID)"
            id_str = "<i>null</i>"

        pack_info = ""
        if manage:
            pack_name = manage.get('pack_name', '?')
            repainting = "🖌️" if manage.get('needs_repainting') else ""
            pack_info = f"\n    📦 <code>{pack_name}</code> {repainting}"

        lines.append(
            f"• <b>{name}</b> {rendered}\n"
            f"  ID: {id_str}\n"
            f"  Альт: {alt_str}"
            f"{pack_info}"
        )

    output = "\n\n".join(lines)
    if len(output) > 3900:
        chunks = []
        current = lines[0]
        for line in lines[1:]:
            candidate = current + "\n\n" + line
            if len(candidate) > 3900:
                chunks.append(current)
                current = line
            else:
                current = candidate
        chunks.append(current)
        for chunk in chunks:
            await message.answer(chunk, parse_mode="HTML")
    else:
        await message.answer(output, parse_mode="HTML")


@main_router.message(Command(commands=['clear_custom_emoji_ids']), IsAdminUser())
async def clear_custom_emoji_ids_cmd(message: Message):
    """Удаляет все созданные стикерпаки и сбрасывает ID в custom_emojis.json и items_custom_emojis.json"""
    user = message.from_user
    if user.id not in conf.bot_devs:
        await message.answer("❌ Нет прав разработчика.")
        return

    await message.answer("⏳ Удаление стикерпаков и очистка ID кастомных эмодзи...")

    try:
        from bot.modules.emoji_packs import _load_raw, _save_raw, delete_all_emoji_packs

        # 0. Delete all sticker packs
        owner_id = conf.bot_devs[0]
        pack_report = await delete_all_emoji_packs(owner_id)
        pack_text = "\n".join(pack_report)
        chunk_limit = 4000
        lines = pack_text.splitlines(keepends=True)
        chunks, current = [], ""
        for line in lines:
            if len(current) + len(line) > chunk_limit:
                if current:
                    await message.answer(current, parse_mode="HTML")
                current = line
            else:
                current += line
        if current:
            await message.answer(current, parse_mode="HTML")

        # 1. Clear custom_emojis.json
        data = _load_raw('bot/json/custom_emojis.json')
        if data:
            for key in data:
                if 'id' in data[key]:
                    data[key]['id'] = ""
            _save_raw(data, 'bot/json/custom_emojis.json')

        # 2. Clear items_custom_emojis.json
        items_data = _load_raw('bot/json/items_custom_emojis.json')
        if items_data:
            for key in items_data:
                if 'id' in items_data[key]:
                    items_data[key]['id'] = ""
                if 'rare_id' in items_data[key]:
                    items_data[key]['rare_id'] = ""
            _save_raw(items_data, 'bot/json/items_custom_emojis.json')

        # 3. Reload constants
        from bot.const import reload_const
        reload_const()
    except Exception as e:
        await message.answer(f"❌ Ошибка во время очистки: {e}")
        return

    await message.answer("✅ Все паки удалены, ID кастомных эмодзи сброшены.")


