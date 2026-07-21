
from bot.models.user import Ad
from bot.models.user import User
from bot.const import GAME_SETTINGS
from bot.exec import main_router, bot
from bot.modules.user.advert import create_ads_data
from bot.modules.data_format import list_to_inline, seconds_to_str
from bot.modules.items.item import AddItemToUser, counts_items, get_item_dict, get_name, item_code
from bot.modules.localization import get_data, get_lang, t
from bot.modules.user.user import premium
from aiogram.types import CallbackQuery, InlineKeyboardMarkup, Message

from bot.filters.private import IsPrivateChat
from aiogram import F
from aiogram.filters import Command

from aiogram.fsm.context import FSMContext



async def main_message(user_id):
    text = ''
    markup = InlineKeyboardMarkup(inline_keyboard=[])

    lang = await get_lang(user_id)
    user = await User.find_one(User.userid == user_id)
    ads_cabinet = await create_ads_data(user_id)
    if user and ads_cabinet:
        coins = user.super_coins
        dollars = round(coins*0.0015, 4)

        text = t("super_coins.info", lang, coins=coins, dollars=dollars, 
                 limit = seconds_to_str(ads_cabinet.limit, lang))
        buttons = get_data("super_coins.buttons", lang)

        inl_buttons = dict(zip(buttons.values(), buttons.keys()))
        markup = list_to_inline([inl_buttons], 1)

    return text, markup

@main_router.message(Command(commands=['super']), IsPrivateChat())
async def super_c(message: Message):
    chatid = message.chat.id
    userid = message.from_user.id

    await create_ads_data(userid)
    text, markup = await main_message(userid)
    await bot.send_message(chatid, text, reply_markup=markup)

@main_router.callback_query(F.data.startswith('super_coins'), IsPrivateChat())
async def super_coins(call: CallbackQuery, state: FSMContext):
    chatid = call.message.chat.id
    user_id = call.from_user.id
    lang = await get_lang(call.from_user.id)

    data = call.data.split()
    code = data[1]

    if code == "view":
        text = t("super_coins.view.info", lang)
        buttons = get_data("super_coins.view.buttons", lang)

        inl_buttons = dict(zip(
            map(lambda a: a['text'], buttons.values()), 
            map(lambda b: f"ads_limit {b}", buttons.keys())
        ))
        markup = list_to_inline([inl_buttons], 2)

        await bot.edit_message_text(text, None, chatid, call.message.message_id,
                                   reply_markup=markup)

    elif code == "products":
        # Pagination logic
        shop_items = list(GAME_SETTINGS['super_shop'].items())
        items_per_page = 8

        # Get page number from callback data, default to 1
        page = 1
        if len(data) > 2 and data[2].isdigit():
            page = int(data[2])
        total_pages = (len(shop_items) + items_per_page - 1) // items_per_page

        start = (page - 1) * items_per_page
        end = start + items_per_page
        current_items = shop_items[start:end]

        text = t("super_coins.shop", lang) + '\n\n'

        mrk_list = []

        for idx, (key, value) in enumerate(current_items, start=start + 1):
            item_desc_with_emoji = counts_items(value["items"], lang, custom_emoji=True)
            key_text = f'{value["price"]} {{custom_emoji:super_coin}} ➞ {item_desc_with_emoji}\n'
            text += f'*{idx}.* ' + key_text
            
            item_desc_no_emoji = counts_items(value["items"], lang, custom_emoji=False)
            button_text = f'{idx}. {value["price"]} ➞ {item_desc_no_emoji}'
            
            first_item_id = value["items"][0]
            from bot.const import ITEMS_CUSTOM_EMOJIS
            emoji_data = ITEMS_CUSTOM_EMOJIS.get(first_item_id, {})
            custom_emoji_id = emoji_data.get('id')
            
            btn_dict = {
                "text": button_text,
                "callback_data": f"super_coins info {key} {page}"
            }
            if custom_emoji_id:
                btn_dict["custom_emoji_id"] = custom_emoji_id
            mrk_list.append(btn_dict)

        text +=  f'\n{page}/{total_pages}'

        # Pagination buttons
        nav_buttons = {}
        if page > 1:
            nav_buttons[GAME_SETTINGS['back_button']] = f"super_coins products {page-1}"
        nav_buttons[t('buttons_name.back', lang)] = 'super_shop back'
        if page < total_pages:
            nav_buttons[GAME_SETTINGS['forward_button']] = f"super_coins products {page+1}"

        mrk_list.append(nav_buttons)
        markup = list_to_inline(mrk_list, 3)
        from bot.modules.localization import resolve_custom_emojis
        text = resolve_custom_emojis(text)
        await bot.edit_message_text(text, None, chatid, call.message.message_id,
                                   reply_markup=markup)

    elif code == "info":
        # data: super_coins info <product_key> <page>
        if len(data) < 3: return

        product_key = data[2]
        page = int(data[3]) if len(data) > 3 and data[3].isdigit() else 1
        products = GAME_SETTINGS['super_shop']
        product = products.get(product_key)
        if not product: return

        item_desc = counts_items(product['items'], lang)
        price = product['price']
        text = t("super_coins.product_info", lang, price=price, items=item_desc)

        # Кнопки: Купить и Назад
        buttons = []

        for iem_id in set(product['items']):
            item_dct = get_item_dict(iem_id)
            abil = item_dct.get('abilities', {})

            code = await item_code(item_dct)
            
            from bot.const import ITEMS_CUSTOM_EMOJIS
            emoji_data = ITEMS_CUSTOM_EMOJIS.get(iem_id, {})
            custom_emoji_id = emoji_data.get('id')
            
            btn_text = get_name(iem_id, lang, abil, with_emoji=False, custom_emoji=False)
            btn_dict = {
                "text": btn_text,
                "callback_data": f"super_shop_item {code} {product_key} {page}"
            }
            if custom_emoji_id:
                btn_dict["custom_emoji_id"] = custom_emoji_id
            buttons.append(btn_dict)

        back_text = t("buttons_name.back", lang)
        buy_text = t("super_coins.buy_button", lang)
        
        from bot.const import CUSTOM_EMOJIS
        super_coin_id = CUSTOM_EMOJIS.get('super_coin', {}).get('id')
        
        buy_btn = {
            "text": buy_text,
            "callback_data": f"super_shop buy {product_key}"
        }
        if super_coin_id:
            buy_btn["custom_emoji_id"] = super_coin_id
            
        buttons.append([
            {
                "text": back_text,
                "callback_data": f"super_coins products {page}"
            },
            buy_btn
        ])
        markup = list_to_inline(buttons, 2)
        await bot.edit_message_text(text, None, chatid, call.message.message_id,
                                   reply_markup=markup)

@main_router.callback_query(F.data.startswith('ads_limit'), IsPrivateChat())
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
            ad_obj = await Ad.find_one(Ad.userid == user_id)
            if ad_obj:
                await ad_obj.update({"$set": {'limit': 'inf'}})
    else:
        limit = buttons[code]['data']
        ad_obj = await Ad.find_one(Ad.userid == user_id)
        if ad_obj:
            await ad_obj.update({"$set": {'limit': limit}})

    text, markup = await main_message(user_id)
    await bot.edit_message_text(text, None, chatid, call.message.message_id,
                                    reply_markup=markup)

@main_router.callback_query(F.data.startswith('super_shop '), IsPrivateChat())
async def super_shop(call: CallbackQuery):
    chatid = call.message.chat.id
    user_id = call.from_user.id
    lang = await get_lang(call.from_user.id)

    code = call.data.split()[1]

    if code == 'back':
        text, markup = await main_message(user_id)
        await bot.edit_message_text(text, None, chatid, call.message.message_id,
                                    reply_markup=markup)

    elif code == 'buy':
        product_code = call.data.split()[2]
        products = GAME_SETTINGS['super_shop']
        user = await User.find_one(User.userid == user_id)

        product = products[product_code]
        price = product['price']
        items = product['items']

        if user and user.super_coins >= price:
            await user.update({'$inc': {'super_coins': -price}})
            from bot.modules.logs import log
            log(f"Edit super_coins: user: {user_id} col: {-price}", 1, "super_shop")
            for i in items: await AddItemToUser(user_id, i)

            await bot.send_message(chatid, t('super_coins.buy', lang,
                                            items=counts_items(items, lang),
                                             ),
                                   message_effect_id='5046509860389126442')

            text, markup = await main_message(user_id)
            await bot.edit_message_text(text, None, chatid, call.message.message_id,
                                    reply_markup=markup)
        else:
            await call.answer(t('super_coins.no_coins', lang), show_alert=True)


@main_router.callback_query(F.data.startswith('super_shop_item'), IsPrivateChat())
async def super_shop_item_info(call: CallbackQuery):
    chatid = call.message.chat.id
    userid = call.from_user.id
    lang = await get_lang(userid)

    parts = call.data.split()
    # parts: super_shop_item <code> <product_key> <page>
    code = parts[1]
    product_key = parts[2]
    page = int(parts[3])

    from bot.modules.items.item import decode_item, item_info
    from bot.config import conf
    from bot.modules.data_format import md_to_html

    item_base = await decode_item(code)
    if 'items_data' not in item_base:
        item = item_base
    else:
        item = item_base['items_data']

    if not item:
        await call.answer(t('super_coins.expired', lang), show_alert=True)
        return

    dev = userid in conf.bot_devs
    text, image = await item_info(item_base, lang, dev, html=True)

    # Only a back button to the product info screen
    back_btn_text = t("buttons_name.back", lang)
    back_callback = f"super_coins info {product_key} {page}"
    markup = list_to_inline([{back_btn_text: back_callback}], 1)

    if call.message.photo:
        await bot.edit_message_caption(
            chat_id=chatid,
            message_id=call.message.message_id,
            caption=text,
            reply_markup=markup
        )
    else:
        await bot.edit_message_text(
            text=text,
            chat_id=chatid,
            message_id=call.message.message_id,
            reply_markup=markup
        )
