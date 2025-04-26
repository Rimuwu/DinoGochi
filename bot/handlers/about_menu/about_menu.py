from bot.const import GAME_SETTINGS
from bot.exec import main_router, bot
from bot.modules.data_format import seconds_to_str
from bot.modules.decorators import HDCallback, HDMessage
from bot.modules.donation import send_inv
from bot.modules.images import async_open
from bot.modules.images_save import edit_SmartPhoto, send_SmartPhoto
from bot.modules.items.item import counts_items
from bot.modules.localization import get_data, get_lang, t
from bot.modules.logs import log
from bot.modules.markup import cancel_markup
from bot.modules.markup import markups_menu as m
from bot.modules.states_tools import ChooseIntState
from aiogram.types import (CallbackQuery, InlineKeyboardButton,
                           InlineKeyboardMarkup, InputMedia, Message, inline_keyboard_markup)
from aiogram.utils.keyboard import ReplyKeyboardBuilder, InlineKeyboardBuilder

from bot.filters.translated_text import StartWith, Text
from bot.filters.states import NothingState
from bot.filters.status import DinoPassStatus
from bot.filters.private import IsPrivateChat
from bot.filters.authorized import IsAuthorizedUser
from bot.filters.kd import KDCheck
from aiogram.filters import Command
from aiogram import F

@HDMessage
@main_router.message(IsPrivateChat(), Text('commands_name.about.team'), 
                     IsAuthorizedUser())
async def team(message: Message):
    lang = await get_lang(message.from_user.id)
    chatid = message.chat.id

    lang_text = t('language_name', lang)
    author_loc = t('localization_author', lang)

    await bot.send_message(chatid, t('about_menu.team', lang, 
                                     lang_name=lang_text,
                                     author=author_loc
                                    ), parse_mode='html')

@HDMessage
@main_router.message(IsPrivateChat(), Text('commands_name.about.links'), 
                     IsAuthorizedUser())
async def links(message: Message):
    lang = await get_lang(message.from_user.id)
    chatid = message.chat.id

    await bot.send_message(chatid, t('about_menu.links', lang), parse_mode='Markdown')

async def faq_func(lang, chatid):
    faq_data = get_data('faq', lang)
    buttons = faq_data['inline_buttons']

    markup_inline = InlineKeyboardBuilder()
    row = []
    for key, name in buttons.items():
        if key.startswith('null'):
            markup_inline.row(*row, width=3)
            row = []
            row.append(
                InlineKeyboardButton(
                    text=' ', 
                    callback_data='faq ' + key
                )
            )
            markup_inline.row(*row, width=3)
            row = []
        else:
            if len(name) > 10 and len(row) == 2:
                markup_inline.row(*row, width=3)
                row = []
            row.append(
                InlineKeyboardButton(
                    text=name, 
                    callback_data='faq ' + key
                )
            )
    markup_inline.row(*row, width=3)

    await bot.send_message(chatid, faq_data['text'], parse_mode='Markdown', reply_markup=markup_inline.as_markup(resize_keyboard=True))


@HDMessage
@main_router.message(IsPrivateChat(), Text('commands_name.about.faq'), 
                     IsAuthorizedUser())
async def faq(message: Message):
    await faq_func(await get_lang(message.from_user.id), message.chat.id)

@HDCallback
@main_router.callback_query(IsPrivateChat(), F.data.startswith('open_faq'))
async def open_faq(call: CallbackQuery):
    await faq_func(await get_lang(call.from_user.id), call.message.chat.id)

@HDCallback
@main_router.callback_query(IsPrivateChat(), F.data.startswith('faq'))
async def faq_buttons(call: CallbackQuery):
    data = call.data.split()[1]
    chatid = call.message.chat.id
    lang = await get_lang(call.from_user.id)

    if data and not data.startswith('null'):
        text = t(f'faq.{data}', lang)
        await bot.send_message(chatid, text, parse_mode='Markdown')
    else:
        await call.answer()