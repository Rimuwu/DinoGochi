from aiogram import types
from aiogram import F
from bot.exec import main_router, bot
from bot.filters.authorized import IsAuthorizedUser
from bot.filters.reply_message import IsReply
from bot.handlers.test import command
from bot.minigames.minigame_fishing import FishingGame
from bot.minigames.minigame_powerchecker import PowerChecker
from bot.modules.decorators import HDCallback, HDMessage

from bot.minigames.test_minigame import TestMiniGame
from bot.minigames.minigame import database, get_session
from aiogram import types
from bot.dbmanager import mongo_client
from bot.modules.localization import get_lang, t
from bot.modules.logs import log
from bot.modules.overwriting.DataCalsses import DBconstructor
from bot.minigames.minigame_registartor import Registry
from aiogram.filters import Command

database = DBconstructor(mongo_client.minigames.online)

@HDCallback
@main_router.callback_query(IsAuthorizedUser(), 
                            F.data.startswith('minigame'))
async def MiniGame_button(callback: types.CallbackQuery):
    if not callback.data: return await callback.answer("Ошибка")

    code = callback.data.split(':')[1]
    session = await get_session(code)
    if session:
        game_id = session['GAME_ID']
        game = Registry.get_class_object(game_id, code)

        if game:
            await game.ActiveButton(callback.data.split(':')[2], callback)

    else:
        return await callback.answer("Игра не найдена")

@main_router.message(IsAuthorizedUser(), Command(commands=['context']))
async def WaiterHandler_command(message: types.Message):
    if message.text is None: return

    # args - это список из всех аргументов команды, 
    # начиная со второго (первый - это сама команда)
    args = message.text.split(' ')[1:]
    session_key = args[0]

    game_data = await database.find_one(
        {'session_key': session_key}, 
        comment='get_session_minigame'
    )

    if not game_data: return
    game_id = game_data['GAME_ID']
    game = Registry.get_class_object(game_id, session_key)
    if game: 
        text_type = 'str'
        if message.text.isdigit(): text_type = 'int'

        await game.ActiveWaiter(text_type, message)

@main_router.message(IsAuthorizedUser(), IsReply())
async def WaiterHandler(message: types.Message):
    if message.text is None: return
    game_data = None

    message_id = message.reply_to_message.message_id # type: ignore
    game_data = await database.find_one(
        {'session_masseges.main': message_id}, 
        comment='get_session_minigame')

    if game_data:
        code = game_data['session_key']
        game_id = game_data['GAME_ID']

        game = Registry.get_class_object(game_id, code)

        text_type = 'str'
        if message.text.isdigit(): text_type = 'int'

        if game:
            await game.ActiveWaiter(text_type, message)

@HDMessage
@main_router.message(Command(commands=['minigame']))
async def MiniGame_start(message: types.Message):
    game = TestMiniGame()

    await game.StartGame(message.chat.id, message.from_user.id)
    return await message.answer("Игра начата")

@HDMessage
@main_router.message(Command(commands=['power']))
async def fishing_start(message: types.Message):
    
    game = PowerChecker()
    await game.StartGame(message.chat.id, message.from_user.id)