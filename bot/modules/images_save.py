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
from bot.config import conf
import aiogram
from aiogram.types import InlineKeyboardMarkup, ReplyKeyboardMarkup, ReplyKeyboardRemove, ForceReply, ReplyParameters, BufferedInputFile
from bot.modules.logs import log

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

async def in_storage(file_name: str) -> bool:
    """
    Проверяет, есть ли файл с именем file_name в хранилище и file_id актуален.
    :param file_name: Имя файла для проверки
    :return: True, если файл есть в хранилище и file_id действителен, иначе False
    """
    if file_name in storage:
        file_id = storage[file_name]
        try:
            await bot.get_file(file_id, request_timeout=20)
            return True
        except Exception:
            # file_id невалиден, удаляем из хранилища
            storage.pop(file_name, None)
            save(storage)
    return False

async def send_SmartPhoto(chat_id: int | str,
    photo_way: str | BufferedInputFile,
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

    photo_name = photo_way if isinstance(photo_way, str) else photo_way.filename

    if photo_name in storage:
        file_id = storage[photo_name]
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
        file_photo = await async_open(photo_way, True) # type: BufferedInputFile 
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
    if mes and mes.photo:
        file_id = mes.photo[-1].file_id
        storage[photo_name] = file_id
        save(storage)

    return mes

async def edit_SmartPhoto(chatid: int, message_id: int, 
                          photo_way: Union[str, BufferedInputFile], caption: Union[str, None], parse_mode: Union[str, None], reply_markup: Union[aiogram.types.InlineKeyboardMarkup, None]):
    global storage
    photo_name = photo_way if isinstance(photo_way, str) else photo_way.filename

    if photo_name in storage:
        file_id = storage[photo_name]
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
    if mes and mes.photo:
        file_id = mes.photo[-1].file_id
        storage[photo_name] = file_id
        save(storage)

    return mes

storage = get_storage()
log('Загружен модуль для сохранения изображений', 1)
log(f'В базе изображений - {len(storage)} картинок', 1)

if conf.reset_images_base:
    log('Сброс базы изображений из за настройки в конфиге', 1)
    storage = {}
    save(storage)
    log('База изображений очищена', 1)