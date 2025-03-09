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
@main_router.message(Text('commands_name.about.team'), 
                     IsAuthorizedUser(), IsPrivateChat())
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
@main_router.message(Text('commands_name.about.links'), 
                     IsAuthorizedUser(), IsPrivateChat())
async def links(message: Message):
    lang = await get_lang(message.from_user.id)
    chatid = message.chat.id

    await bot.send_message(chatid, t('about_menu.links', lang), parse_mode='Markdown')

@HDMessage
@main_router.message(Text('commands_name.about.faq'), 
                     IsAuthorizedUser(), IsPrivateChat())
async def faq(message: Message):
    lang = await get_lang(message.from_user.id)
    chatid = message.chat.id

    faq_data = get_data('faq', lang)
    buttons = faq_data['inline_buttons']

    markup_inline = InlineKeyboardBuilder()
    markup_inline.row(*[
        InlineKeyboardButton(
            text=name, 
            callback_data=key
        ) for key, name in buttons.items()], width=2)

    await bot.send_message(chatid, faq_data['text'], parse_mode='Markdown', reply_markup=markup_inline.as_markup(resize_keyboard=True))

@HDCallback
@main_router.callback_query(F.data.startswith('faq'))
async def faq_buttons(call: CallbackQuery):
    data = call.data.split()[1]
    chatid = call.message.chat.id
    lang = await get_lang(call.from_user.id)

    text = t(f'faq.{data}', lang)
    await bot.send_message(chatid, text, parse_mode='Markdown')