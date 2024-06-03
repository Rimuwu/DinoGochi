from telebot.types import (CallbackQuery, InlineKeyboardButton,
                           InlineKeyboardMarkup, Message, InputMedia)

from bot.config import mongo_client
from bot.exec import bot
from bot.modules.images import async_open
from bot.modules.localization import get_data, t, get_lang
from bot.modules.currency import get_all_currency, get_products
from bot.modules.item import counts_items
from bot.modules.data_format import seconds_to_str
 

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
    products = get_products()
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
                text += f'\n\n{text_data["currency_answer"]}'
                markup_inline.add(*[
                InlineKeyboardButton(
                    text=currency, 
                    callback_data=f'support currency {product_key} {currency}') for currency in get_all_currency()])
            else:
                markup_inline.add(InlineKeyboardButton(
                    text=text_data['buy_button'], 
                    url='https://telegra.ph/Donation-DinoGochi-11-05'))

            markup_inline.add(
            InlineKeyboardButton(
                text=t('buttons_name.back', lang), 
                callback_data='support main 0'
            ))

        elif action == "currency":
            currency = call.data.split()[3]
            buttons = {}

            text += f'\n\n{text_data["currency"].format(currency=currency)}'
            text += f'\n{text_data["col_answer"]}'

            if product['type'] == 'subscription':
                for key, item in product['cost'].items():
                    name = f'{seconds_to_str(product["time"]*int(key), lang)} = {item[currency]}{currency}'

                    buttons[name] = f'support buy {product_key} {currency} {key}'
            elif product['type'] == 'kit':
                for key, item in product['cost'].items():
                    name = f'x{key} = {item[currency]}{currency}'
                    buttons[name] = f'support buy {product_key} {currency} {key}'

            markup_inline.add(*[
            InlineKeyboardButton(
                text=key, 
                callback_data=item) for key, item in buttons.items()]
                            )

            markup_inline.add(
            InlineKeyboardButton(
                text=t('buttons_name.back', lang), 
                callback_data=f'support info {product_key}'
            ))

        elif action == "buy":
            currency = call.data.split()[3]
            count = call.data.split()[4]
            amount = product['cost'][count][currency]

            image = await async_open('images/remain/support/placeholder.png', True)

            text = text_data['buy'].format(
                count=count, user_id=user_id, product_key=product_key,
                currency=currency, amount=amount)

            markup_inline.add(InlineKeyboardButton(
                text=text_data['buy_button'], 
                url='https://telegra.ph/Donation-DinoGochi-11-05'))
            
            markup_inline.add(
            InlineKeyboardButton(
                text=t('buttons_name.back', lang), 
                callback_data=f'support currency {product_key} {currency}'
            ))

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
