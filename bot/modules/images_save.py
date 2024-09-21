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

from bot.modules.logs import log

storage = {}
DIRECTORY = 'bot/json/file_base.json'

def get_storage():
    # Проверка наличия файла с данными в temp/file_id_directorie.json
    global storage

    with open(DIRECTORY, encoding='utf-8') as f: 
        storage = json.load(f)

def save(new_file: dict):
    """
    Saves the given new_file dictionary to the file at DIRECTORY.
    If the file is not found, a FileNotFoundError is raised.
    If the file is not a dictionary, a TypeError is raised.
    """
    if not isinstance(new_file, dict):
        raise TypeError("new_file should be a dictionary")
    try:
        with open(DIRECTORY, 'w', encoding='utf-8') as f:
            json.dump(new_file, f, sort_keys=True, indent=4, ensure_ascii=False)
    except FileNotFoundError as e:
        raise FileNotFoundError(f"File {DIRECTORY} not found") from e
    except TypeError as e:
        raise TypeError(f"new_file should be a dictionary, not {type(new_file)}") from e

async def send_SmartPhoto(chatid: int, photo_way: str, caption: Union[str, None], parse_mode: Union[str, None], reply_markup: Union[telebot.types.InlineKeyboardMarkup, None]):
    global storage
    
    log(f'{storage}')

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


    if mes and mes.photo:
        file_id = mes.photo[-1].file_id
        storage[photo_way] = file_id
        save(storage)

if __name__ != '__main__':
    get_storage()