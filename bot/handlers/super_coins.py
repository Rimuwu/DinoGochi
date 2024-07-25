from bot.config import mongo_client
from bot.const import GAME_SETTINGS
from bot.exec import bot
from bot.modules.user.advert import create_ads_data
from bot.modules.data_format import list_to_inline, seconds_to_str
from bot.modules.decorators import HDCallback, HDMessage
from bot.modules.items.item import AddItemToUser, counts_items
from bot.modules.localization import get_data, get_lang, t
from bot.modules.overwriting.DataCalsses import DBconstructor
from bot.modules.user.user import premium
from telebot.types import CallbackQuery, InlineKeyboardMarkup, Message

users = DBconstructor(mongo_client.user.users)
ads = DBconstructor(mongo_client.user.ads)

async def main_message(user_id):
    text = ''
    markup = InlineKeyboardMarkup()

    lang = await get_lang(user_id)
    user = await users.find_one({"userid": user_id}, comment='main_message_super_c_user')
    ads_cabinet = await create_ads_data(user_id)
    if user and ads_cabinet:
        coins = user['super_coins']
        dollars = round(coins*0.0015, 4)

        text = t("super_coins.info", lang, coins=coins, dollars=dollars, 
                 limit = seconds_to_str(ads_cabinet['limit'], lang))
        buttons = get_data("super_coins.buttons", lang)

        inl_buttons = dict(zip(buttons.values(), buttons.keys()))
        markup = list_to_inline([inl_buttons], 1)

    return text, markup

@bot.message_handler(pass_bot=True, commands=['super'], private=True)
@HDMessage
async def super_c(message: Message):
    chatid = message.chat.id
    userid = message.from_user.id

    await create_ads_data(userid)
    text, markup = await main_message(userid)
    await bot.send_message(chatid, text, reply_markup=markup, parse_mode="Markdown")

@bot.callback_query_handler(pass_bot=True, func=lambda call: 
    call.data.startswith('super_coins'), private=True)
@HDCallback
async def super_coins(call: CallbackQuery):
    chatid = call.message.chat.id
    user_id = call.from_user.id
    lang = await get_lang(call.from_user.id)

    code = call.data.split()[1]

    if code == "view":
        text = t("super_coins.view.info", lang)
        buttons = get_data("super_coins.view.buttons", lang)

        inl_buttons = dict(zip(
            map(lambda a: a['text'], buttons.values()), 
            map(lambda b: f"ads_limit {b}", buttons.keys())
                               ))
        markup = list_to_inline([inl_buttons], 2)

        await bot.edit_message_text(text, chatid, call.message.id,
                                    reply_markup=markup)

    elif code == "products":

        shop_items = GAME_SETTINGS['super_shop']
        text = t("super_coins.shop", lang) + '\n\n'
        mrk_list = []

        a = 0
        for key, value in shop_items.items():
            a += 1
            key_text = f'{value["price"]} ➞ {counts_items(value["items"], lang)}\n'
            text += f'*{a}.* ' + key_text

            mrk_list.append({f'{a}. ' + key_text: f"super_shop buy {key}"})

        mrk_list.append(
            {t('buttons_name.back',lang): 'super_shop back'})

        markup = list_to_inline(mrk_list, 2)
        await bot.edit_message_text(text, chatid, call.message.id,
                                    reply_markup=markup, parse_mode='Markdown')

@bot.callback_query_handler(pass_bot=True, func=lambda call: 
    call.data.startswith('ads_limit'), private=True)
@HDCallback
async def ads_limit(call: CallbackQuery):
    chatid = call.message.chat.id
    user_id = call.from_user.id
    lang = await get_lang(call.from_user.id)

    code = call.data.split()[1]
    buttons = get_data("super_coins.view.buttons", lang)

    if code == 'no_ads':
        if not await premium(user_id):
            text = t("no_premium", lang)
            await bot.send_message(chatid, text)
        else:
            await ads.update_one({'userid': user_id}, 
                                 {"$set": {'limit': 'inf'}}, comment='ads_limit')
    else:
        limit = buttons[code]['data']
        await ads.update_one({'userid': user_id}, {"$set": {'limit': limit}}, comment='ads_limit_limit')

    text, markup = await main_message(user_id)
    await bot.edit_message_text(text, chatid, call.message.id,
                                    reply_markup=markup, parse_mode="Markdown")

@bot.callback_query_handler(pass_bot=True, func=lambda call: 
    call.data.startswith('super_shop'), private=True)
@HDCallback
async def super_shop(call: CallbackQuery):
    chatid = call.message.chat.id
    user_id = call.from_user.id
    lang = await get_lang(call.from_user.id)

    code = call.data.split()[1]

    if code == 'back':
        text, markup = await main_message(user_id)
        await bot.edit_message_text(text, chatid, call.message.id,
                                    reply_markup=markup, parse_mode="Markdown")

    elif code == 'buy':
        product_code = call.data.split()[2]
        products = GAME_SETTINGS['super_shop']
        user = await users.find_one({'userid': user_id}, comment='super_shop_user')

        product = products[product_code]
        price = product['price']
        items = product['items']

        if user and user['super_coins'] >= price:
            await users.update_one({'_id': user['_id']}, 
                                   {'$inc': {'super_coins': -price}}, comment='super_shop_price')
            for i in items: await AddItemToUser(user_id, i)

            await bot.send_message(chatid, t('super_coins.buy', lang))

            text, markup = await main_message(user_id)
            await bot.edit_message_text(text, chatid, call.message.id,
                                    reply_markup=markup, parse_mode="Markdown")