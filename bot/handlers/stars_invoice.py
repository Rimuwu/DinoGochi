
from time import time

from bot.const import GAME_SETTINGS
from bot.exec import main_router, bot
from bot.modules.data_format import random_code
from bot.modules.donation import (OpenDonatData, give_reward, save,
                                  save_donation)
from bot.modules.localization import get_lang, t
from bot.modules.logs import log
from aiogram.types import Message, PreCheckoutQuery
from aiogram import F

products = GAME_SETTINGS['products']

@main_router.pre_checkout_query()
async def checkout(pre_checkout_query: PreCheckoutQuery):
    lang = await get_lang(pre_checkout_query.from_user.id)

    res = await bot.answer_pre_checkout_query(pre_checkout_query.id, ok=True,
                                  error_message=t('notifications.donation.pre_check_error', lang, formating=False))

    log(f'Был выдан ответ на pre_checkout_query_handler -> {res}, user: {pre_checkout_query.from_user.id}', 4)

@main_router.message(F.successful_payment)
async def got_payment(message: Message):
    """ Выдача товара за покупку """
    if message.successful_payment:
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