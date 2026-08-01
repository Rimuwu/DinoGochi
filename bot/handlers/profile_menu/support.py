from bot.const import GAME_SETTINGS
from bot.exec import main_router, bot
from bot.config import conf
from bot.modules.data_format import seconds_to_str
from bot.modules.donation import send_inv, get_product_price_and_discount
from bot.models.other import Event
from bot.modules.cryptobot import create_cryptobot_payment, check_cryptobot_payment

from bot.modules.images_save import edit_SmartPhoto, send_SmartPhoto
from bot.modules.items.item import counts_items
from bot.modules.localization import get_data, get_lang, t
from bot.modules.logs import log
from bot.modules.markup import cancel_markup
from bot.modules.markup import markups_menu as m
from bot.modules.states_fabric.state_handlers import ChooseIntHandler
from aiogram.types import (CallbackQuery, InlineKeyboardButton,
                        Message)
from aiogram.utils.keyboard import  InlineKeyboardBuilder

from bot.filters.translated_text import Text
from bot.filters.private import IsPrivateChat
from bot.filters.authorized import IsAuthorizedUser
from aiogram.filters import Command
from aiogram import F

SUPPORT_ITEMS_PER_PAGE = 5

SUPPORT_PAGES = {
    "premium": ["dino_ultima"],
    "kits": ["rescue_kit", "reborn", "pause"],
    "currency": ["super_coins", "non_repayable"],
    "runes": [
        "rune_lvl1", "rune_lvl2", "rune_lvl3", "rune_lvl4", "rune_lvl5",
        "rune_lvl6", "rune_lvl7", "rune_lvl8", "rune_lvl9", "rune_lvl10",
        "rune_x2_lvl1", "rune_x2_lvl2", "rune_x2_lvl3", "rune_x2_lvl4",
        "rune_x2_lvl5", "rune_x2_lvl6", "rune_x2_lvl7", "rune_x2_lvl8",
        "rune_x2_lvl9", "rune_x2_lvl10",
        "rune_x3_lvl1", "rune_x3_lvl2", "rune_x3_lvl3",
        "rune_x5_lvl1", "rune_x5_lvl2", "rune_x5_lvl3",
    ],
    "boosters": [
        "incubation_boost_1h", "incubation_boost_12h", "incubation_boost_1d",
        "incubation_boost_3d", "incubation_boost_7d",
    ],
    "slots": ["dino_slot"],
}

def find_support_page(product_key: str) -> str | None:
    for page_key, products in SUPPORT_PAGES.items():
        if product_key in products:
            return page_key
    return None

def get_page_number(data: list[str], position: int = 3) -> int:
    if len(data) > position and data[position].isdigit():
        return max(1, int(data[position]))
    return 1

async def support_choice_menu(lang: str):
    image = 'images/remain/support/placeholder.png'
    text_data = get_data('support_command', lang)
    choice_data = text_data['choose']

    markup_inline = InlineKeyboardBuilder()
    markup_inline.row(
        InlineKeyboardButton(
            text=choice_data['super_shop'],
            callback_data='support super 0'
        ),
        InlineKeyboardButton(
            text=choice_data['donate'],
            callback_data='support main 0'
        ),
        width=2
    )

    return image, choice_data['info'], markup_inline.as_markup(resize_keyboard=True)

def make_custom_button(name: str, callback_data: str) -> InlineKeyboardButton:
    from bot.modules.data_format import parse_custom_emoji_markdown, resolve_button_data, remove_alt_emoji_from_text
    from bot.modules.localization import resolve_custom_emojis
    clean_text, emoji_id, alt_emoji = parse_custom_emoji_markdown(name)
    if emoji_id:
        btn_text, icon_emoji = resolve_button_data(remove_alt_emoji_from_text(clean_text, alt_emoji), emoji_id)
    else:
        btn_text = resolve_custom_emojis(name, html=False)
        icon_emoji = None

    kwargs = {"text": btn_text, "callback_data": callback_data}
    if icon_emoji:
        kwargs["icon_custom_emoji_id"] = icon_emoji
    return InlineKeyboardButton(**kwargs)

async def main_support_menu(lang: str):
    image = 'images/remain/support/placeholder.png'
    text_data = get_data('support_command', lang)
    text = text_data['info']
    pages = text_data.get('pages', {})
    btn_objects = []

    a = 0
    for key in SUPPORT_PAGES:
        bio = pages.get(key)
        if not bio:
            continue
        a += 1
        text += f'{a}. <b>{bio["name"]}</b> — {bio["short"]}\n\n'
        cb = 'support info dino_ultima' if key == "premium" else f'support page {key}'
        btn_objects.append(make_custom_button(bio["name"], cb))

    product_bio = text_data['products_bio'].get('non_repayable')
    if product_bio:
        btn_objects.append(make_custom_button(product_bio["name"], 'support info non_repayable'))

    markup_inline = InlineKeyboardBuilder()
    markup_inline.row(*btn_objects, width=2)

    return image, text, markup_inline.as_markup(resize_keyboard=True)

@main_router.message(IsPrivateChat(), Text('commands_name.profile.support'), 
                     IsAuthorizedUser())
async def support(message: Message):
    lang = await get_lang(message.from_user.id)
    chatid = message.chat.id

    image, text, markup_inline = await support_choice_menu(lang)
    
    await send_SmartPhoto(chatid, image, text, 'HTML', markup_inline)

@main_router.message(IsPrivateChat(), Command(commands=['premium']),
                     IsAuthorizedUser())
async def support_com(message: Message):
    lang = await get_lang(message.from_user.id)
    chatid = message.chat.id

    image, text, markup_inline = await main_support_menu(lang)

    await send_SmartPhoto(chatid, image, text, 'HTML', markup_inline)


@main_router.callback_query(IsPrivateChat(), F.data.startswith('support'))
async def support_buttons(call: CallbackQuery):
    data = call.data.split()
    action = data[1]

    # Handle actions that don't need product_key early
    if action == "advantage_info":
        lang = await get_lang(call.from_user.id)
        await call.answer(t('support_command.advantage_info_popup', lang), show_alert=True)
        return

    product_key = data[2]
    products = GAME_SETTINGS['products']
    product = {}

    chatid = call.message.chat.id
    user_id = call.from_user.id
    lang = await get_lang(call.from_user.id)
    messageid = call.message.message_id

    if action == "verify_pay":
        code = product_key
        success = await check_cryptobot_payment(code)
        if success:
            await call.answer(t('support_command.payment_check_success', lang), show_alert=True)
            image_way = 'images/remain/support/placeholder.png'
            text = t('support_command.payment_check_success', lang)
            markup_inline = InlineKeyboardBuilder()
            markup_inline.row(
                InlineKeyboardButton(
                    text=t('buttons_name.back', lang),
                    callback_data='support main 0'
                ),
                width=1
            )
        else:
            await call.answer(t('support_command.payment_check_fail', lang), show_alert=True)
            return

        if isinstance(call.message, Message) and call.message.content_type == 'text':
            await send_SmartPhoto(chatid, image_way, text, 'HTML', markup_inline.as_markup(resize_keyboard=True))
        else:
            try:
                await edit_SmartPhoto(chatid, messageid, image_way, text, 'HTML', markup_inline.as_markup(resize_keyboard=True))
            except Exception as e:
                log(f'edit_SmartPhoto error: {e}', 2)
        return

    if action == "choose":
        image, text, markup_inline = await support_choice_menu(lang)
        await edit_SmartPhoto(chatid, messageid, image, text, 'HTML', markup_inline)

    elif action == "super":
        from bot.handlers.super_coins import main_message

        text, markup_inline = await main_message(user_id)
        await bot.send_message(chatid, text, reply_markup=markup_inline)
        await call.answer()

    elif action == "main":
        image, text, markup_inline = await main_support_menu(lang)
        await edit_SmartPhoto(chatid, messageid, image, text, 'HTML', markup_inline)

    elif action == "page":
        text_data = get_data('support_command', lang)
        page_bio = text_data.get('pages', {}).get(product_key, {})
        image_way = page_bio.get('image', 'images/remain/support/placeholder.png')
        page = get_page_number(data)

        markup_inline = InlineKeyboardBuilder()
        page_products = [
            key for key in SUPPORT_PAGES.get(product_key, [])
            if key == 'non_repayable' or key in products
        ]

        total_pages = max(1, (len(page_products) + SUPPORT_ITEMS_PER_PAGE - 1) // SUPPORT_ITEMS_PER_PAGE)
        page = min(page, total_pages)
        start = (page - 1) * SUPPORT_ITEMS_PER_PAGE
        end = start + SUPPORT_ITEMS_PER_PAGE
        current_products = page_products[start:end]
        text = f'{page_bio.get("name", product_key)} — {page_bio.get("short", "")}\n\n{page_bio.get("description", "")}'
        if total_pages > 1:
            text += f'\n\n{page}/{total_pages}'

        product_buttons = []
        for key in current_products:
            bio = text_data['products_bio'].get(key)
            if not bio:
                continue
            product_buttons.append(make_custom_button(bio["name"], f'support info {key} {page}'))

        if product_buttons:
            markup_inline.row(*product_buttons, width=1)
        nav_buttons = []
        if page > 1:
            nav_buttons.append(InlineKeyboardButton(
                text=GAME_SETTINGS['back_button'],
                callback_data=f'support page {product_key} {page - 1}'
            ))
        if page < total_pages:
            nav_buttons.append(InlineKeyboardButton(
                text=GAME_SETTINGS['forward_button'],
                callback_data=f'support page {product_key} {page + 1}'
            ))
        if nav_buttons:
            markup_inline.row(*nav_buttons, width=2)
        markup_inline.row(
            InlineKeyboardButton(
                text=t('buttons_name.back', lang),
                callback_data='support main 0'
            ), width=2)

        if isinstance(call.message, Message) and call.message.content_type == 'text':
            await send_SmartPhoto(chatid, image_way, text, 'HTML', markup_inline.as_markup(resize_keyboard=True))
        else:
            try:
                await edit_SmartPhoto(chatid, messageid, image_way, text, 'HTML', markup_inline.as_markup(resize_keyboard=True))
            except Exception as e:
                log(f'edit_SmartPhoto error: {e}', 2)
    else:
        if product_key != 'non_repayable': product = products[product_key]
        markup_inline = InlineKeyboardBuilder()

        text_data = get_data('support_command', lang)
        product_bio = text_data['products_bio'][product_key]

        image_way = product_bio['image']

        from bot.modules.localization import resolve_custom_emojis
        text = resolve_custom_emojis(f'{product_bio["name"]} — {product_bio["short"]}\n\n{product_bio["description"]}', html=True)

        if product_key == 'dino_ultima':
            from bot.models.user import Subscription
            import time
            now = int(time.time())
            active_sub_count = await Subscription.find({
                "$or": [
                    {"sub_end": "inf"},
                    {"sub_end": {"$gt": now}}
                ]
            }).count()
            text += t("support_command.active_premiums", lang, count=active_sub_count)

        if product_key != 'non_repayable' and product['items']:
            text += f'\n\n{text_data["items"].format(items=counts_items(product["items"], lang))}'

        if action == "info":
            if product_key != 'non_repayable':
                currency = 'XTR'
                buttons = {}

                text += f'\n{text_data["col_answer"]}'

                # Calculate base price for discount calculation
                cost_dict = product['cost']
                keys_list = list(cost_dict.keys())
                base_key = None
                for k in keys_list:
                    if k.isdigit():
                        base_key = k
                        break

                if base_key is not None:
                    base_price = cost_dict[base_key][currency] / int(base_key)
                else:
                    base_price = None

                global_discount = await Event.get_donate_discount()
                if global_discount > 0:
                    text += f'\n<b>{t("support_command.global_discount_active", lang, discount=global_discount)}</b>\n'

                if product['type'] == 'subscription':
                    for key, item in cost_dict.items():
                        discounted_price, total_discount = get_product_price_and_discount(product, key, currency, global_discount)
                        price_text = f"{discounted_price}🌟"

                        if key.isdigit():
                            name = f'{seconds_to_str(product["time"]*int(key), lang)} = {price_text}'
                            if total_discount > 0:
                                name += f' (-{total_discount}%)'
                        elif key == 'inf':
                            name = f'♾ = {price_text}'
                            if total_discount > 0:
                                name += f' (-{total_discount}%)'
                        buttons[name] = f'support buy {product_key} {key}'

                elif product['type'] in ['kit', 'super_coins']:
                    for key, item in cost_dict.items():
                        discounted_price, total_discount = get_product_price_and_discount(product, key, currency, global_discount)
                        price_text = f"{discounted_price}🌟"

                        name = f'x{key} = {price_text}'
                        if total_discount > 0:
                            name += f' (-{total_discount}%)'
                        buttons[name] = f'support buy {product_key} {key}'

                markup_inline.row(*[
                    InlineKeyboardButton(
                        text=key, 
                        callback_data=item) for key, item in buttons.items()],
                        width=2)

            else:
                await ChooseIntHandler(tips, user_id, chatid, lang, 1, 500_000
                                        ).start()
                await bot.send_message(chatid, text_data['free_enter'], reply_markup=cancel_markup(lang))

            markup_inline.row(
                InlineKeyboardButton(
                    text=t('buttons_name.back', lang), 
                    callback_data=f'support page {find_support_page(product_key)} {get_page_number(data, 3)}'
                    if find_support_page(product_key) else 'support main 0'
                ), width=2)

        elif action == "buy":
            count = call.data.split()[3]

            global_discount = await Event.get_donate_discount()
            discounted_xtr, _ = get_product_price_and_discount(product, count, 'XTR', global_discount)
            discounted_usdt, _ = get_product_price_and_discount(product, count, 'USDT', global_discount)

            # Calculate savings vs Stars
            star_usd_rate = GAME_SETTINGS.get('star_usd_rate', 0.015)
            stars_usd_total = discounted_xtr * star_usd_rate
            if stars_usd_total > 0 and discounted_usdt > 0:
                crypto_saving_pct = round((1 - discounted_usdt / stars_usd_total) * 100)
            else:
                crypto_saving_pct = 0

            image_way = 'images/remain/support/placeholder.png'
            text = t('support_command.select_payment_method', lang, product_name=product_bio['name'], count=count)

            # Row 1: TON + USDT side by side
            markup_inline.row(
                InlineKeyboardButton(
                    text=t('support_command.payment_ton', lang, amount=discounted_usdt),
                    callback_data=f'support cryptobot_pay {product_key} {count} TON',
                    style='success'
                ),
                InlineKeyboardButton(
                    text=t('support_command.payment_usdt', lang, amount=discounted_usdt),
                    callback_data=f'support cryptobot_pay {product_key} {count} USDT',
                    style='success'
                ),
                width=2
            )

            # Row 2: advantage badge (clickable info popup)
            if crypto_saving_pct > 0:
                markup_inline.row(
                    InlineKeyboardButton(
                        text=t('support_command.payment_advantage', lang, pct=crypto_saving_pct),
                        callback_data='support advantage_info'
                    ),
                    width=1
                )
                markup_inline.row(
                    InlineKeyboardButton(
                        text=t('support_command.buy_crypto_p2p', lang),
                        url=conf.crypto_pay_referral
                    ),
                    width=1
                )

            # Row 3: Stars
            markup_inline.row(
                InlineKeyboardButton(
                    text=t('support_command.payment_stars', lang, amount=discounted_xtr),
                    callback_data=f'support stars_pay {product_key} {count}',
                    style='primary'
                ),
                width=1
            )

            markup_inline.row(
                InlineKeyboardButton(
                    text=t('buttons_name.back', lang),
                    callback_data=f'support info {product_key}'
                ), width=1
            )

        elif action == "stars_pay":
            count = call.data.split()[3]
            await send_inv(user_id, product_key, count, lang)
            await call.answer()
            return

        elif action == "cryptobot_pay":
            parts = call.data.split()
            count = parts[3]
            asset = parts[4] if len(parts) > 4 else 'USDT'
            product_cost = product.get('cost', {}).get(str(count), {})
            if 'USDT' not in product_cost:
                await call.answer(t('support_command.payment_method_unavailable', lang), show_alert=True)
                return

            global_discount = await Event.get_donate_discount()
            discounted_usdt, _ = get_product_price_and_discount(product, count, 'USDT', global_discount)

            payment_data = await create_cryptobot_payment(
                user_id=user_id,
                user_first_name=call.from_user.first_name,
                product_key=product_key,
                col=count,
                usdt_amount=discounted_usdt,
                asset=asset,
                lang=lang
            )
            if not payment_data:
                await call.answer(t('support_command.payment_creation_error', lang), show_alert=True)
                return

            payment_url, code = payment_data

            image_way = 'images/remain/support/placeholder.png'
            text = t('support_command.buy_cryptobot', lang, amount=discounted_usdt)

            markup_inline.row(
                InlineKeyboardButton(
                    text=t('support_command.pay_button', lang),
                    url=payment_url
                ),
                width=1
            )
            markup_inline.row(
                InlineKeyboardButton(
                    text=t('support_command.verify_payment_button', lang),
                    callback_data=f'support verify_pay {code}'
                ),
                width=1
            )
            markup_inline.row(
                InlineKeyboardButton(
                    text=t('buttons_name.back', lang),
                    callback_data=f'support info {product_key}'
                ),
                width=1
            )

        if isinstance(call.message, Message) and call.message.content_type == 'text':
            await send_SmartPhoto(chatid, image_way, text, 'HTML', markup_inline.as_markup(resize_keyboard=True))
        else:
            try:
                await edit_SmartPhoto(chatid, messageid, image_way, text, 'HTML', markup_inline.as_markup(resize_keyboard=True))
            except Exception as e:
                log(f'edit_SmartPhoto error: {e}', 2) 



async def tips(col, transmitted_data):
    userid = transmitted_data['userid']
    chatid = transmitted_data['chatid']
    lang = transmitted_data['lang']

    await send_inv(userid, 'non_repayable', '1', lang, col)
    await bot.send_message(chatid, t('support_command.create_invoice', lang), reply_markup=await m(userid, 'last_menu', lang))
