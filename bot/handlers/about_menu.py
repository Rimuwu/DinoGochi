from telebot.types import (CallbackQuery, InlineKeyboardButton,
                           InlineKeyboardMarkup, Message, InputMedia)

from bot.config import mongo_client
from bot.const import GAME_SETTINGS
from bot.exec import bot
from bot.modules.donation import send_inv
from bot.modules.images import async_open
from bot.modules.localization import get_data, t, get_lang
from bot.modules.item import counts_items
from bot.modules.data_format import seconds_to_str
from bot.modules.states_tools import ChooseIntState
from bot.modules.markup import cancel_markup
from bot.modules.markup import markups_menu as m

@bot.message_handler(pass_bot=True, text='commands_name.about.team', 
                     is_authorized=True, private=True)
async def team(message: Message):
    lang = await get_lang(message.from_user.id)
    chatid = message.chat.id

    lang_text = t('language_name', lang)
    author_loc = t('localization_author', lang)

    await bot.send_message(chatid, t('about_menu.team', lang, 
                                     lang_name=lang_text,
                                     author=author_loc
                                    ), parse_mode='html')

@bot.message_handler(pass_bot=True, text='commands_name.about.links', 
                     is_authorized=True, private=True)
async def links(message: Message):
    lang = await get_lang(message.from_user.id)
    chatid = message.chat.id

    await bot.send_message(chatid, t('about_menu.links', lang), parse_mode='Markdown')

async def main_support_menu(lang: str):
    image = await async_open('images/remain/support/placeholder.png', True)
    text_data = get_data('support_command', lang)
    text = text_data['info']
    prd_text = text_data['products_bio']
    buttons = {}

    a = 0
    for key, bio in prd_text.items():
        a += 1
        text += f'{a}. *{bio["name"]}* — {bio["short"]}\n\n'
        buttons[bio["name"]] = f'support info {key}'

    markup_inline = InlineKeyboardMarkup(row_width=1)
    markup_inline.add(*[
        InlineKeyboardButton(
            text=key, 
            callback_data=name
        ) for key, name in buttons.items()])

    return image, text, markup_inline

@bot.message_handler(pass_bot=True, text='commands_name.about.support', 
                     is_authorized=True, private=True)
async def support(message: Message):
    lang = await get_lang(message.from_user.id)
    chatid = message.chat.id

    image, text, markup_inline = await main_support_menu(lang)
    
    await bot.send_photo(chatid, image, text, reply_markup=markup_inline, parse_mode='Markdown')

@bot.message_handler(pass_bot=True, commands=['premium'], 
                     is_authorized=True, private=True)
async def support_com(message: Message):
    lang = await get_lang(message.from_user.id)
    chatid = message.chat.id

    image, text, markup_inline = await main_support_menu(lang)
    
    await bot.send_photo(chatid, image, text, reply_markup=markup_inline, parse_mode='Markdown')

@bot.message_handler(pass_bot=True, text='commands_name.about.faq', 
                     is_authorized=True, private=True)
async def faq(message: Message):
    lang = await get_lang(message.from_user.id)
    chatid = message.chat.id

    faq_data = get_data('faq', lang)
    buttons = faq_data['inline_buttons']

    markup_inline = InlineKeyboardMarkup(row_width=2)
    markup_inline.add(*[
        InlineKeyboardButton(
            text=name, 
            callback_data=key
        ) for key, name in buttons.items()])

    await bot.send_message(chatid, faq_data['text'], parse_mode='Markdown', reply_markup=markup_inline)

@bot.callback_query_handler(pass_bot=True, func=lambda call: 
    call.data.startswith('faq'))
async def faq_buttons(call: CallbackQuery):
    data = call.data.split()[1]
    chatid = call.message.chat.id
    lang = await get_lang(call.from_user.id)

    text = t(f'faq.{data}', lang)
    await bot.send_message(chatid, text, parse_mode='Markdown')

@bot.callback_query_handler(pass_bot=True, func=lambda call: 
    call.data.startswith('support'))
async def support_buttons(call: CallbackQuery):
    action = call.data.split()[1]
    product_key = call.data.split()[2]
    products = GAME_SETTINGS['products']
    product = {}

    chatid = call.message.chat.id
    user_id = call.from_user.id
    lang = await get_lang(call.from_user.id)
    messageid = call.message.id

    if action == "main":
        image, text, markup_inline = await main_support_menu(lang)

        await bot.edit_message_media(
                chat_id=chatid,
                message_id=messageid,
                reply_markup=markup_inline,
                media=InputMedia(type='photo', media=image, caption=text, parse_mode='Markdown'))
    else:
        if product_key != 'non_repayable': product = products[product_key]
        markup_inline = InlineKeyboardMarkup(row_width=2)

        text_data = get_data('support_command', lang)
        product_bio = text_data['products_bio'][product_key]

        image = await async_open(product_bio['image'], True)
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

                markup_inline.add(*[
                    InlineKeyboardButton(
                        text=key, 
                        callback_data=item) for key, item in buttons.items()]
                                    )

            else:
                await ChooseIntState(tips, user_id, chatid, lang, 1, 100_000)
                await bot.send_message(chatid, text_data['free_enter'], reply_markup=cancel_markup(lang))

            markup_inline.add(
            InlineKeyboardButton(
                text=t('buttons_name.back', lang), 
                callback_data='support main 0'
            ))

        elif action == "buy":
            currency = 'XTR'
            count = call.data.split()[3]

            image = await async_open('images/remain/support/placeholder.png', True)

            text = text_data['buy']

            markup_inline.add(
            InlineKeyboardButton(
                text=t('buttons_name.back', lang), 
                callback_data=f'support info {product_key}'
            ))

            await send_inv(user_id, product_key, count, lang)

        if call.message.content_type == 'text':
            await bot.send_photo(
                        chat_id=chatid,
                        photo=image,
                        caption=text,
                        reply_markup=markup_inline,
                        parse_mode='Markdown')
        else:
            try:
                await bot.edit_message_media(
                        chat_id=chatid,
                        message_id=messageid,
                        reply_markup=markup_inline,
                        media=InputMedia(type='photo', media=image, caption=text, parse_mode='Markdown'))
            except: pass


async def tips(col, transmitted_data):
    userid = transmitted_data['userid']
    chatid = transmitted_data['chatid']
    lang = transmitted_data['lang']

    await send_inv(userid, 'non_repayable', 1, lang, col)
    await bot.send_message(chatid, t('support_command.create_invoice', lang), reply_markup=await m(userid, 'last_menu', lang))