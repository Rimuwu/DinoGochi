from telebot.types import Message, CallbackQuery

from bot.exec import bot
from bot.config import mongo_client
from bot.modules.data_format import seconds_to_str, user_name, str_to_seconds, list_to_inline
from bot.modules.inline import inline_menu
from bot.modules.localization import  get_lang, t, get_data
from bot.modules.over_functions import send_message
from bot.modules.advert import show_advert

users = mongo_client.user.users

@bot.message_handler(pass_bot=True, commands=['super'])
async def super_c(message: Message):
    chatid = message.chat.id
    userid = message.from_user.id

    lang = await get_lang(message.from_user.id)
    user = await users.find_one({"userid": userid})
    if user:
        coins = user['super_coins']
        dollars = round(coins*0.0015, 4)

        text = t("super_coins.info", lang, coins=coins, dollars=dollars)
        buttons = get_data("super_coins.buttons", lang)

        inl_buttons = dict(zip(buttons.values(), buttons.keys()))
        markup = list_to_inline([inl_buttons], 1)

        await send_message(chatid, text, reply_markup=markup)

@bot.callback_query_handler(pass_bot=True, func=lambda call: 
    call.data.startswith('super_coins'), private=True)
async def add_friend_callback(call: CallbackQuery):
    chatid = call.message.chat.id
    user_id = call.from_user.id
    lang = await get_lang(call.from_user.id)

    code = call.data.split()[1]

    if code == "view":
        result = await show_advert(user_id)
        if result != 1:
            if result == 7:
                text = t("super_coins.limit", lang)
            else:
                text = t("super_coins.noads", lang)
            await send_message(chatid, text)

    elif code == "products":
        text = "It will be soon, you still don't have that many coins yet..."
        await send_message(chatid, text)