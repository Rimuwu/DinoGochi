# Функции для отправки по file_id вместо файла
# {
#    "directorie_way": file_id
#}
#

import json
import os
from typing import Union
from bot.exec import bot
from bot.modules.images import async_open
import telebot


storage = {}
DIRECTORY = 'bot/data/file_base.json'

def get_storage():
    # Проверка наличия файла с данными в bot/data/file_base.json

    try:
        with open(DIRECTORY, encoding='utf-8') as f: 
            storage = json.load(f)
    except Exception as error:
        if not os.path.exists(DIRECTORY):
            with open(DIRECTORY, 'w', encoding='utf-8') as f:
                f.write('{}')
            return {}
    return storage

def save(new_file: dict):
    with open(DIRECTORY, 'w', encoding='utf-8') as f:
        json.dump(new_file, f, sort_keys=True, indent=4, ensure_ascii=False)


async def send_SmartPhoto(chatid: int, photo_way, caption: Union[str, None], parse_mode: Union[str, None], reply_markup: Union[telebot.types.InlineKeyboardMarkup, None]):
    global storage

    if photo_way in storage:
        file_id = storage[photo_way]
        if await bot.get_file(file_id):
            # Отпрляем файл по file_id
            await bot.send_photo(chatid, file_id, caption, 
                                 parse_mode, reply_markup=reply_markup)
            return 

    # Либо файла нет, либо file_id устарело
    # Отправяем файл с пк + сохраняем file_id
    file_photo = await async_open(photo_way, True)

    mes = await bot.send_photo(chatid, file_photo, caption, 
                            parse_mode, reply_markup=reply_markup)

    # Сохраняем file_id
    if mes and mes.photo:
        file_id = mes.photo[-1].file_id
        storage[photo_way] = file_id
        save(storage)

async def edit_SmartPhoto(chatid: int, message_id: int, 
                          photo_way, caption: Union[str, None], parse_mode: Union[str, None], reply_markup: Union[telebot.types.InlineKeyboardMarkup, None]):
    global storage

    if photo_way in storage:
        file_id = storage[photo_way]
        if await bot.get_file(file_id):
            # Отпряем файл по file_id
            await bot.edit_message_media(
                telebot.types.InputMediaPhoto(file_id, caption, parse_mode), 
                chatid, message_id, reply_markup=reply_markup)
            return 

    # Либо файла нет, либо file_id устарело
    # Отправляем файл с пк + сохраняем file_id
    file_photo = await async_open(photo_way, True)

    mes = await bot.edit_message_media(
                telebot.types.InputMediaPhoto(file_photo, caption, parse_mode), 
                chatid, message_id, reply_markup=reply_markup)

    # Сохраняем file_id
    if mes and mes.photo:
        file_id = mes.photo[-1].file_id
        storage[photo_way] = file_id
        save(storage)

if __name__ != '__main__':
    storage = get_storage()