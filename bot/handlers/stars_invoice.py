
from time import time

from bot.const import GAME_SETTINGS
from bot.exec import main_router, bot
from bot.modules.donation import give_reward, save_donation
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
    
    log(f'Начата обработка {message.successful_payment}', 4)

    if message.successful_payment:
        payload = message.successful_payment.invoice_payload # Делаем строчку с кодом товара и количеством "dino_ultima#2"
        total_price = message.successful_payment.total_amount
        user = message.from_user
        if not user:
            log('No user in successful_payment message', 3)
            return

        message_split = payload.split('#')
        product_key = message_split[0]
        if message_split[1] != 'inf':
            col = int(message_split[1])
        else:
            col = 'inf'

        if product_key in products:
            code = await save_donation(
                user.id, 
                user.first_name, 
                total_price, 
                product_key, int(time()),
                col,
                message.successful_payment.telegram_payment_charge_id
            )

            log(f'Обработан {payload} -> {code}', 4)

            await give_reward(user.id, product_key, col, code)

        else:
            log(f'Неизвестный продукт {payload} -> {product_key}', 4)
