
from time import time

from bot.const import GAME_SETTINGS
from bot.exec import bot
from bot.modules.data_format import random_code
from bot.modules.decorators import HDMessage
from bot.modules.donation import (OpenDonatData, give_reward, save,
                                  save_donation)
from bot.modules.localization import get_lang, t
from bot.modules.logs import log
from aiogram.types import Message, PreCheckoutQuery

products = GAME_SETTINGS['products']

@bot.pre_checkout_query_handler(func=lambda query: True)
async def checkout(pre_checkout_query: PreCheckoutQuery):
    lang = await get_lang(pre_checkout_query.from_user.id)

    res = await bot.answer_pre_checkout_query(int(pre_checkout_query.id), ok=True,
                                  error_message=t('notifications.donation.pre_check_error', lang, formating=False))

    log(f'Был выдан ответ на pre_checkout_query_handler -> {res}, user: {pre_checkout_query.from_user.id}', 4)


@bot.message(content_types=['successful_payment'])
@HDMessage
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