from aiogram import types
from aiogram.filters import Command, StateFilter
from aiogram import F
from bot.exec import main_router
from bot.filters.authorized import IsAuthorizedUser
from bot.filters.translated_text import StartWith
from bot.modules.decorators import HDCallback, HDMessage

from bot.minigames.test_minigame import database, MiniGame


@HDCallback
@main_router.callback_query(IsAuthorizedUser(), 
                            F.data.startswith('minigame'))
async def MiniGame_button(callback: types.CallbackQuery):
    code = callback.data.split(':')[1]
    if code not in database:
        return await callback.answer("Игра не найдена")
    
    else:
        game = MiniGame()
        await game.ContinueGame(code)
        func = game.ButtonsRegistr(callback.data.split(':')[2])
        await func(
            callback
        )
    
@HDMessage
@main_router.message(Command(commands=['minigame']))
async def MiniGame_start(message: types.Message):
    game = MiniGame()

    await game.StartGame(message.chat.id, message.from_user.id)
    return await message.answer("Игра начата")

@HDMessage
@main_router.message(Command(commands=['database']))
async def MiniGame_start(message: types.Message):
    
    await message.answer(str(database))
