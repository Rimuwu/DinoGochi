from aiogram import types
from aiogram import F
from bot.exec import main_router
from bot.filters.authorized import IsAuthorizedUser
from bot.modules.decorators import HDCallback, HDMessage

from bot.minigames.test_minigame import TestMiniGame
from bot.minigames.minigame import database, get_session
from aiogram import types
from bot.dbmanager import mongo_client
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
            await game.ContinueGame(code)
            func = game.GetButton(callback.data.split(':')[2])
            if func is not None:
                await func( callback )

    else:
        return await callback.answer("Игра не найдена")

@HDMessage
@main_router.message(Command(commands=['minigame']))
async def MiniGame_start(message: types.Message):
    game = TestMiniGame()

    await game.StartGame(message.chat.id, message.from_user.id)
    return await message.answer("Игра начата")

@HDMessage
@main_router.message(Command(commands=['database']))
async def database_f(message: types.Message):
    
    await message.answer(str(database))
