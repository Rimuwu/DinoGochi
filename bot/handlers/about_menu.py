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

async def main_support_menu(lang: str):
    image = 'images/remain/support/placeholder.png'
    text_data = get_data('support_command', lang)
    text = text_data['info']
    prd_text = text_data['products_bio']
    buttons = {}

    a = 0
    for key, bio in prd_text.items():
        a += 1
        text += f'{a}. *{bio["name"]}* — {bio["short"]}\n\n'
        buttons[bio["name"]] = f'support info {key}'

    markup_inline = InlineKeyboardBuilder()
    markup_inline.row(*[
        InlineKeyboardButton(
            text=key, 
            callback_data=name
        ) for key, name in buttons.items()], width=1)

    return image, text, markup_inline.as_markup(resize_keyboard=True)

@HDMessage
@main_router.message(Text('commands_name.about.support'), 
                     IsAuthorizedUser(), IsPrivateChat())
async def support(message: Message):
    lang = await get_lang(message.from_user.id)
    chatid = message.chat.id

    image, text, markup_inline = await main_support_menu(lang)
    
    await send_SmartPhoto(chatid, image, text, 'Markdown', markup_inline)

@HDMessage
@main_router.message(Command(commands=['premium']),
                     IsAuthorizedUser(), IsPrivateChat())
async def support_com(message: Message):
    lang = await get_lang(message.from_user.id)
    chatid = message.chat.id

    image, text, markup_inline = await main_support_menu(lang)

    await send_SmartPhoto(chatid, image, text, 'Markdown', markup_inline)

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

@HDCallback
@main_router.callback_query(F.data.startswith('support'))
async def support_buttons(call: CallbackQuery, state):
    action = call.data.split()[1]
    product_key = call.data.split()[2]
    products = GAME_SETTINGS['products']
    product = {}

    chatid = call.message.chat.id
    user_id = call.from_user.id
    lang = await get_lang(call.from_user.id)
    messageid = call.message.message_id

    if action == "main":
        image, text, markup_inline = await main_support_menu(lang)
        await edit_SmartPhoto(chatid, messageid, image, text, 'Markdown', markup_inline)
    else:
        if product_key != 'non_repayable': product = products[product_key]
        markup_inline = InlineKeyboardBuilder()

        text_data = get_data('support_command', lang)
        product_bio = text_data['products_bio'][product_key]

        image_way = product_bio['image']

        text = f'{product_bio["name"]} — {product_bio["short"]}\n\n{product_bio["description"]}'

        if product_key != 'non_repayable' and product['items']:
            text += f'\n\n{text_data["items"].format(items=counts_items(product["items"], lang))}'

        if action == "info":
            if product_key != 'non_repayable':
                currency = 'XTR'
                buttons = {}

                text += f'\n{text_data["col_answer"]}'

                if product['type'] == 'subscription':
                    for key, item in product['cost'].items():
                        name = f'{seconds_to_str(product["time"]*int(key), lang)} = {item[currency]}🌟'

                        buttons[name] = f'support buy {product_key} {key}'
                elif product['type'] == 'kit':
                    for key, item in product['cost'].items():
                        name = f'x{key} = {item[currency]}🌟'
                        buttons[name] = f'support buy {product_key} {key}'

                markup_inline.row(*[
                    InlineKeyboardButton(
                        text=key, 
                        callback_data=item) for key, item in buttons.items()],
                        width=2)

            else:
                await ChooseIntState(tips, user_id, chatid, lang, 1, 500_000)
                await bot.send_message(chatid, text_data['free_enter'], reply_markup=cancel_markup(lang))

            markup_inline.row(
                InlineKeyboardButton(
                    text=t('buttons_name.back', lang), 
                    callback_data='support main 0'
                ), width=2)

        elif action == "buy":
            currency = 'XTR'
            count = call.data.split()[3]

            image_way = 'images/remain/support/placeholder.png'

            text = text_data['buy']

            markup_inline.row(
                InlineKeyboardButton(
                    text=t('buttons_name.back', lang), 
                    callback_data=f'support info {product_key}'
                ), width=2)

            await send_inv(user_id, product_key, count, lang)

        if call.message.content_type == 'text':
            await send_SmartPhoto(chatid, image_way, text, 'Markdown', markup_inline.as_markup(resize_keyboard=True))
        else:
            try:
                await edit_SmartPhoto(chatid, messageid, image_way, text, 'Markdown', markup_inline.as_markup(resize_keyboard=True))
            except Exception as e:
                log(f'edit_SmartPhoto error: {e}', 2) 


async def tips(col, transmitted_data):
    userid = transmitted_data['userid']
    chatid = transmitted_data['chatid']
    lang = transmitted_data['lang']

    await send_inv(userid, 'non_repayable', '1', lang, col)
    await bot.send_message(chatid, t('support_command.create_invoice', lang), reply_markup=await m(userid, 'last_menu', lang))