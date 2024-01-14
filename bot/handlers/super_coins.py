from telebot.types import Message, CallbackQuery, InlineKeyboardMarkup 

from bot.exec import bot
from bot.config import mongo_client
from bot.modules.data_format import list_to_inline, seconds_to_str
from bot.modules.localization import  get_lang, t, get_data
from bot.modules.over_functions import send_message
from bot.modules.user import premium
from bot.modules.item import counts_items, AddItemToUser
from bot.const import GAME_SETTINGS

users = mongo_client.user.users
ads = mongo_client.user.ads

async def main_message(user_id):
    text = ''
    markup = InlineKeyboardMarkup()

    lang = await get_lang(user_id)
    user = await users.find_one({"userid": user_id})
    ads_cabinet = await ads.find_one({'userid': user_id})
    if user and ads_cabinet:
        coins = user['super_coins']
        dollars = round(coins*0.0015, 4)

        text = t("super_coins.info", lang, coins=coins, dollars=dollars, 
                 limit = seconds_to_str(ads_cabinet['limit'], lang))
        buttons = get_data("super_coins.buttons", lang)

        inl_buttons = dict(zip(buttons.values(), buttons.keys()))
        markup = list_to_inline([inl_buttons], 1)

    return text, markup

@bot.message_handler(pass_bot=True, commands=['super'])
async def super_c(message: Message):
    chatid = message.chat.id
    userid = message.from_user.id

    text, markup = await main_message(userid)
    await send_message(chatid, text, reply_markup=markup, parse_mode="Markdown")

@bot.callback_query_handler(pass_bot=True, func=lambda call: 
    call.data.startswith('super_coins'), private=True)
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
            key_text = f'{a}. {value["price"]} ➞ {counts_items(value["items"], lang)}\n'
            text += key_text

            mrk_list.append({key_text: f"super_shop buy {key}"})

        mrk_list.append(
            {t('buttons_name.back',lang): 'super_shop back'})

        markup = list_to_inline(mrk_list, 2)
        await bot.edit_message_text(text, chatid, call.message.id,
                                    reply_markup=markup)

@bot.callback_query_handler(pass_bot=True, func=lambda call: 
    call.data.startswith('ads_limit'), private=True)
async def ads_limit(call: CallbackQuery):
    chatid = call.message.chat.id
    user_id = call.from_user.id
    lang = await get_lang(call.from_user.id)

    code = call.data.split()[1]
    buttons = get_data("super_coins.view.buttons", lang)

    if code == 'no_ads':
        if not await premium(user_id):
            text = t("no_premium", lang)
            await send_message(chatid, text)
        else:
            await ads.update_one({'userid': user_id}, 
                                 {"$set": {'limit': 'inf'}})
    else:
        limit = buttons[code]['data']
        await ads.update_one({'userid': user_id}, {"$set": {'limit': limit}})

    text, markup = await main_message(user_id)
    await bot.edit_message_text(text, chatid, call.message.id,
                                    reply_markup=markup, parse_mode="Markdown")

@bot.callback_query_handler(pass_bot=True, func=lambda call: 
    call.data.startswith('super_shop'), private=True)
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
        user = await users.find_one({'userid': user_id})

        product = products[product_code]
        price = product['price']
        items = product['items']

        if user and user['super_coins'] >= price:
            await users.update_one({'_id': user['_id']}, 
                                   {'$inc': {'super_coins': -price}})
            for i in items: await AddItemToUser(user_id, i)

            await send_message(chatid, t('super_coins.buy', lang))

            text, markup = await main_message(user_id)
            await bot.edit_message_text(text, chatid, call.message.id,
                                    reply_markup=markup, parse_mode="Markdown")