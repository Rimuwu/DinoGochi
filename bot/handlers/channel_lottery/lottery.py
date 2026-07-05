from bot.modules.overwriting.DataCalsses import LazyCollection
from bot.models.other import Lottery, LotteryMember
from random import choice, randint, uniform
from time import time
from asyncio import sleep

from bot.dbmanager import mongo_client
from bot.exec import main_router, bot

from bot.handlers.companies import end
from bot.modules.localization import get_lang, t
from aiogram.filters import Command
from aiogram.types import Message
from aiogram.types import CallbackQuery
from aiogram import F
from bot.filters.authorized import IsAuthorizedUser
from bot.modules.logs import log

from bot.filters.admin import IsAdminUser

from bot.models.other import Lottery, LotteryMember

lottery = LazyCollection(Lottery)
lottery_members = LazyCollection(LotteryMember)


@main_router.message(Command(commands=['lottery_create']), IsAdminUser())
async def lottery_create(message: Message):
    args = message.text.split(' ')[1:]
    channel_id = message.chat.id
    if args:
        try:
            channel_id = int(args[0])
        except ValueError:
            pass
    
    await Lottery.create_lottery(channel_id, 0, 120, 
        {
            '1': {
                'items': [
                    {'items_data': {
                        'item_id': 'premium_activator',
                        'abilities': {'interact': False}
                    }, 
                    'count': 3}
                ],
                'coins': 50000,
                'count': 1
            },
            '2': {
                'items': [
                    {'items_data': {
                        'item_id': 'dino_slot',
                        'abilities': {'interact': False}
                    }, 
                    'count': 1}
                ],
                'coins': 15000,
                'count': 3
            },
            '3': {
                'items': [
                    {'items_data': {
                        'item_id': 'all_or_nothing_case_eggs',
                    }, 
                    'count': 1}
                ],
                'coins': 10000,
                'count': 5
            },
            '4': {
                'items': [
                    {'items_data': {
                        'item_id': 'rune_lvl1',
                    }, 
                    'count': 1}
                ],
                'coins': 5000,
                'count': 10
            },
            '5': {
                'items': [
                    {'items_data': {
                        'item_id': 'incubation_boost_1d',
                    }, 
                    'count': 1}
                ],
                'coins': 1000,
                'count': 10
            },
            '6': {
                'items': [
                    {'items_data': {
                        'item_id': 'training_boost_gym_4h',
                    }, 
                    'count': 1}
                ],
                'coins': 1000,
                'count': 10
            },
            '7': {
                'items': [
                    {'items_data': {
                        'item_id': 'training_boost_library_4h',
                    }, 
                    'count': 1}
                ],
                'coins': 1000,
                'count': 10
            },
            '8': {
                'items': [
                    {'items_data': {
                        'item_id': 'training_boost_park_4h',
                    }, 
                    'count': 1}
                ],
                'coins': 1000,
                'count': 10
            },
            '9': {
                'items': [
                    {'items_data': {
                        'item_id': 'weapon_case',
                    }, 
                    'count': 1}
                ],
                'coins': 1000,
                'count': 10
            },
            '10': {
                'items': [
                    {'items_data': {
                        'item_id': 'weapon_case',
                    }, 
                    'count': 1}
                ],
                'coins': 1000,
                'count': 10
            },
        }, 'en', 0)


@main_router.message(Command(commands=['update_lottery']), IsAdminUser())
async def update_lottery(message: Message):
    
    args = message.text.split(' ')[1:]
    alt_id = args[0]
    
    lotter = await lottery.find_one({'alt_id': alt_id}, comment='update_lottery')
    
    if lotter:
        await Lottery.create_message(lotter['alt_id'])

@main_router.message(Command(commands=['Lottery.end_lottery']), IsAdminUser())
async def end_lottery_com(message: Message):
    
    args = message.text.split(' ')[1:]
    alt_id = args[0]

    lotter = await lottery.find_one({'alt_id': alt_id}, comment='update_lottery')

    if lotter:
        await Lottery.end_lottery(lotter['_id'])

@main_router.callback_query(F.data.startswith('lottery_enter'), IsAuthorizedUser())
async def lottery_enter(callback: CallbackQuery):

    chatid = callback.message.chat.id
    userid = callback.from_user.id

    lang = await get_lang(callback.from_user.id)
    data = callback.data.split(':')[1:]

    alt_id = data[0]

    success, message = await LotteryMember.create_member(userid, alt_id)
    await callback.answer(t(f'lottery.{message}', lang), show_alert=True)

    if success: 
        find_lot = await Lottery.find_one(Lottery.alt_id == alt_id)
        if find_lot:
            count = await LotteryMember.find(LotteryMember.lot_id == str(find_lot.id)).count()
            if count % 5 == 0:
                try:
                    await Lottery.create_message(alt_id)
                except Exception as e:
                    await sleep(5)
                    try:
                        await Lottery.create_message(alt_id)
                    except Exception as e:
                        log(f'except in Lottery.create_message lottery {e}', 3)

