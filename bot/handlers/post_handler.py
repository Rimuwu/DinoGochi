"""Файл должен загружаться последним, чтобы сюда попадали только необработанные хендлеры
"""
from aiogram import types
from bot.exec import main_router, bot
from bot.modules.logs import log
from bot.modules.localization import t, get_lang

from bot.filters.translated_text import StartWith, Text
from bot.filters.states import NothingState
from bot.filters.status import DinoPassStatus
from bot.filters.private import IsPrivateChat
from bot.filters.authorized import IsAuthorizedUser
from bot.filters.kd import KDCheck
from bot.filters.admin import IsAdminUser
from aiogram import F
from aiogram.filters import Command, StateFilter

from aiogram.fsm.context import FSMContext

@main_router.callback_query(F.data.startswith('delete_message'))
async def delete_message(call: types.CallbackQuery):
    chatid = call.message.chat.id
    await bot.delete_message(chatid, call.message.message_id)
    await bot.answer_callback_query(call.id, "🗑")

@main_router.callback_query(F.data == ' ')
async def pass_h(call: types.CallbackQuery): pass

@main_router.callback_query()
async def not_found(call: types.CallbackQuery):
    userid = call.from_user.id
    log(f'Ключ {call.data} не был обработан! Пользователь: {userid}', 0, "CallbackQuery")

@main_router.message(IsAuthorizedUser(False), IsPrivateChat())
async def not_authorized(message: types.Message):
    lang = await get_lang(message.from_user.id)
    chatid = message.chat.id

    if not message.from_user.bot:
        text = t('not_authorized', lang)
        await bot.send_message(chatid, text)