"""Файл должен загружаться последним, чтобы сюда попадали только необработанные хендлеры
"""
from aiogram import types
from bot.exec import bot
from bot.modules.logs import log
from bot.modules.localization import t, get_lang
from bot.modules.decorators import HDCallback, HDMessage
 

@bot.callback_query(F.data.startswith('delete_message'))
@HDCallback
async def delete_message(call: types.CallbackQuery):
    chatid = call.message.chat.id
    await bot.delete_message(chatid, call.message.id)
    await bot.answer_callback_query(call.id, "🗑")

@bot.callback_query(func=lambda call: call.data == ' ')
@HDCallback
async def pass_h(call: types.CallbackQuery): pass

@bot.callback_query(func=lambda call: True)
@HDCallback
async def not_found(call: types.CallbackQuery):
    userid = call.from_user.id
    log(f'Ключ {call.data} не был обработан! Пользователь: {userid}', 0, "CallbackQuery")

@bot.message(is_authorized=False, private=True)
@HDMessage
async def not_authorized(message: types.Message):
    lang = await get_lang(message.from_user.id)
    chatid = message.chat.id

    text = t('not_authorized', lang)
    await bot.send_message(chatid, text)

# @bot.message()
# async def not_found_text(message: types.Message):
#     lang = await get_lang(message.from_user.id)
#     chatid = message.chat.id

#     text = t('not_found_key', lang)
#     await bot.send_message(chatid, text)