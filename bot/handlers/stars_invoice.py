from itertools import product
from telebot.types import CallbackQuery, Message, PreCheckoutQuery

from bot.const import GAME_SETTINGS
from bot.config import mongo_client
from bot.const import GAME_SETTINGS as GS
from bot.exec import bot
from bot.modules.data_format import escape_markdown, list_to_inline, random_code
from bot.modules.donation import OpenDonatData, give_reward, save, save_donation
from bot.modules.item import AddItemToUser, counts_items
from bot.modules.localization import get_data, t, get_lang
from bot.modules.markup import cancel_markup
from bot.modules.markup import markups_menu as m
from bot.modules.logs import log
from time import time

products = GAME_SETTINGS['products']

@bot.pre_checkout_query_handler(func=lambda query: True)
async def checkout(pre_checkout_query: PreCheckoutQuery):
    lang = get_lang(pre_checkout_query.from_user.language_code)

    res = await bot.answer_pre_checkout_query(pre_checkout_query.id, ok=True,
                                  error_message=t('notifications.donation.pre_check_error', lang, formating=False))

    log(f'Был выдан ответ на pre_checkout_query_handler -> {res}, user: {pre_checkout_query.from_user.id}', 4)


@bot.message_handler(content_types=['successful_payment'])
async def got_payment(message: Message):
    """ Выдача товара за покупку """
    payload = message.successful_payment.invoice_payload # Делаем строчку с кодом товара и количеством "dino_ultima#2"
    total_price = message.successful_payment.total_amount
    user_id = message.chat.id
    chat_user = await bot.get_chat_member(user_id, user_id)
    processed_donations = OpenDonatData()

    message_split = payload.split('#')
    product_key = message_split[0]
    col = int(message_split[1])

    if product_key in products:
        donation_data = save_donation(
            chat_user.user.first_name, 
            total_price, 'done', 
            product_key, True, int(time()),
            col
        )

        processed_donations[f"{random_code(5)}_{user_id}"] = donation_data
        save(processed_donations)

        await give_reward(user_id, product_key, col)