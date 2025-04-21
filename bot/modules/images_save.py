# Функции для отправки по file_id вместо файла
# {
#    "directorie_way": file_id
#}
#

import json
from math import fabs
import os
from typing import Union, List
from bot.exec import main_router, bot
from bot.modules.images import async_open
import aiogram
from aiogram.types import InputFile, MessageEntity, InlineKeyboardMarkup, ReplyKeyboardMarkup, ReplyKeyboardRemove, ForceReply, ReplyParameters


storage = {}
DIRECTORY = 'bot/data/file_base.json'

def get_storage():
    # Проверка наличия файла с данными в bot/data/file_base.json

    try:
        with open(DIRECTORY, encoding='utf-8') as f: 
            storage = json.load(f)
    except Exception as error:
        storage = {}
        if not os.path.exists(DIRECTORY):
            with open(DIRECTORY, 'w', encoding='utf-8') as f:
                f.write('{}')
            return {}
    return storage

def save(new_file: dict):
    with open(DIRECTORY, 'w', encoding='utf-8') as f:
        json.dump(new_file, f, sort_keys=True, indent=4, ensure_ascii=False)


async def send_SmartPhoto(chat_id: int | str,
    photo_way: str,
    caption: str | None = None,
    parse_mode: str | None = None,
    reply_markup: InlineKeyboardMarkup | ReplyKeyboardMarkup | ReplyKeyboardRemove | ForceReply | None = None,
    show_caption_above_media: bool | None = None,
    has_spoiler: bool | None = None,
    disable_notification: bool | None = None,
    protect_content: bool | None = None,
    message_effect_id: str | None = None,
    reply_parameters: ReplyParameters | None = None,
    allow_sending_without_reply: bool | None = None,
    reply_to_message_id: int | None = None,
    request_timeout: int | None = None):
    global storage

    if photo_way in storage:
        file_id = storage[photo_way]
        try:
            # Пытаемся проверить доступность file_id
            await bot.get_file(file_id, request_timeout=20)
            # Отпрляем файл по file_id
            mes = await bot.send_photo(chat_id, file_id, caption=caption, 
                            parse_mode=parse_mode, reply_markup=reply_markup,
                            show_caption_above_media=show_caption_above_media,
                            has_spoiler=has_spoiler,
                            disable_notification=disable_notification,
                            protect_content=protect_content,
                            message_effect_id=message_effect_id,
                            reply_parameters=reply_parameters,
                            allow_sending_without_reply=allow_sending_without_reply,
                            reply_to_message_id=reply_to_message_id,
                            request_timeout=request_timeout)
            return mes
        except Exception:
            # Если возникла любая ошибка при проверке file_id, значит он недействителен или устарел
            # Удаляем некорректный file_id из хранилища
            storage.pop(photo_way, None)

    # Либо файла нет, либо file_id устарело
    # Отправяем файл с пк + сохраняем file_id
    if isinstance(photo_way, str):
        file_photo = await async_open(photo_way, True)
    else:
        file_photo = photo_way

    mes = await bot.send_photo(chat_id, file_photo, caption=caption, 
                    parse_mode=parse_mode, reply_markup=reply_markup,
                    show_caption_above_media=show_caption_above_media,
                    has_spoiler=has_spoiler,
                    disable_notification=disable_notification,
                    protect_content=protect_content,
                    message_effect_id=message_effect_id,
                    reply_parameters=reply_parameters,
                    allow_sending_without_reply=allow_sending_without_reply,
                    reply_to_message_id=reply_to_message_id,
                    request_timeout=request_timeout)

    # Сохраняем file_id
    if mes and mes.photo and type(photo_way) == str:
        file_id = mes.photo[-1].file_id
        storage[photo_way] = file_id
        save(storage)

    return mes

async def edit_SmartPhoto(chatid: int, message_id: int, 
                          photo_way, caption: Union[str, None], parse_mode: Union[str, None], reply_markup: Union[aiogram.types.InlineKeyboardMarkup, None]):
    global storage

    if photo_way in storage:
        file_id = storage[photo_way]
        try:
            # Пытаемся проверить доступность file_id
            await bot.get_file(file_id, request_timeout=20)
            # Отправляем файл по file_id
            mes = await bot.edit_message_media(
                media=aiogram.types.InputMediaPhoto(media=file_id, caption=caption, parse_mode=parse_mode), 
                chat_id=chatid, message_id=message_id, reply_markup=reply_markup)
            return mes
        except Exception:
            # Если возникла любая ошибка при проверке file_id, значит он недействителен или устарел
            # Удаляем некорректный file_id из хранилища
            storage.pop(photo_way, None)

    # Либо файла нет, либо file_id устарело
    # Отправляем файл с пк + сохраняем file_id
    if isinstance(photo_way, str):
        file_photo = await async_open(photo_way, True)
    else:
        file_photo = photo_way

    mes = await bot.edit_message_media(
                aiogram.types.InputMediaPhoto(media=file_photo, caption=caption, parse_mode=parse_mode), 
                chat_id=chatid, message_id=message_id, reply_markup=reply_markup)

    # Сохраняем file_id
    if mes and mes.photo and type(photo_way) == str:
        file_id = mes.photo[-1].file_id
        storage[photo_way] = file_id
        save(storage)

    return mes

if __name__ != '__main__':
    storage = get_storage()