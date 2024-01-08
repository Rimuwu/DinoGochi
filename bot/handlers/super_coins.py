from telebot.types import Message, CallbackQuery, InlineKeyboardMarkup 

from bot.exec import bot
from bot.config import mongo_client
from bot.modules.data_format import list_to_inline, seconds_to_str
from bot.modules.localization import  get_lang, t, get_data
from bot.modules.over_functions import send_message
from bot.modules.user import premium

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
        text = "It will be soon, you still don't have that many coins yet..."
        await send_message(chatid, text)

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