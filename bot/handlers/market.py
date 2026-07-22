
from bot.models.user import User
from bot.models.market import Product, Puhs, Seller


from bot.dbmanager import mongo_client
from bot.exec import main_router, bot
from bot.modules.add_product.add_product import prepare_data_option
from bot.modules.data_format import (escape_markdown, list_to_inline,
                                     list_to_keyboard)
from bot.modules.images_save import send_SmartPhoto
from bot.modules.items.item import item_info
from bot.modules.localization import get_lang, t
from bot.modules.logs import log
from bot.modules.market.market import (create_push, create_seller, delete_product,
                                preview_product, product_ui, seller_ui)
from bot.modules.market.market_chose import (buy_item, find_prepare,
                                      pr_edit_description, pr_edit_image,
                                      pr_edit_name, prepare_add,
                                      prepare_delete_all, prepare_edit_price,
                                      promotion_prepare, send_info_pr)
from bot.modules.markup import cancel_markup
from bot.modules.markup import markups_menu as m
from bot.modules.states_fabric.state_handlers import ChoosePagesStateHandler, ChooseOptionHandler, ChooseStepHandler, ChooseStringHandler
from bot.modules.states_fabric.steps_datatype import CustomStepData, StepMessage, StringStepData

from aiogram.types import CallbackQuery, InlineKeyboardMarkup, Message

from bot.filters.translated_text import StartWith, Text
from bot.filters.states import NothingState
from bot.filters.status import DinoPassStatus
from bot.filters.private import IsPrivateChat
from bot.filters.authorized import IsAuthorizedUser
from bot.filters.kd import KDCheck
from bot.filters.admin import IsAdminUser
from aiogram import F
from aiogram.filters import Command, StateFilter
from fuzzywuzzy import fuzz

from aiogram.fsm.context import FSMContext
import random




async def create_adapter(return_data, transmitted_data):
    chatid = transmitted_data['chatid']
    userid = transmitted_data['userid']
    lang = transmitted_data['lang']

    name = return_data['name']
    description = return_data['description']
    description = escape_markdown(description)
    await create_seller(userid, name, description)

    await bot.send_message(chatid, t('market_create.create', lang), 
                           reply_markup= await m(userid, 'seller_menu', lang))

async def custom_name(message: Message, transmitted_data):
    userid = message.from_user.id
    lang = await get_lang(message.from_user.id)

    max_len = 50
    min_len = 3

    content = str(message.text)
    content_len = len(content)
    name = escape_markdown(content)

    if content_len > max_len:
        await bot.send_message(message.chat.id, 
                t('states.ChooseString.error_max_len', lang,
                number = content_len, max = max_len))
    elif content_len < min_len:
        await bot.send_message(message.chat.id, 
                t('states.ChooseString.error_min_len', lang,
                number = content_len, min = min_len))
    elif await Seller.find_one(Seller.name == name):
        await bot.send_message(message.chat.id, 
                t('market_create.name_error', lang))
    else: 
        return True, name
    return False, None

@main_router.message(IsPrivateChat(), Text('commands_name.seller_profile.create_market'), IsAuthorizedUser())
async def create_market(message: Message):
    userid = message.from_user.id
    lang = await get_lang(message.from_user.id)
    chatid = message.chat.id

    user = await User.find_one(User.userid == userid)
    res = await Seller.find_one(Seller.owner_id == userid)

    if res or not user:
        await bot.send_message(message.chat.id, t('menu_text.seller', lang), 
                            reply_markup= await m(userid, 'market_menu', lang))
    elif user.lvl < 2:
        await bot.send_message(message.chat.id, t('market_create.lvl', lang))
    else:

        steps = [
            CustomStepData('name', StepMessage(
                'market_create.name',
                markup=cancel_markup(lang), 
                translate_message=True),
                custom_handler=custom_name, 
            ),
            StringStepData('description', StepMessage(
                'market_create.description',
                markup=cancel_markup(lang), 
                translate_message=True),
                max_len=500, 
            )
        ]
        
        await ChooseStepHandler(
            create_adapter, userid, chatid, lang, steps
        ).start()

@main_router.message(IsPrivateChat(), Text('commands_name.seller_profile.my_market'), IsAuthorizedUser())
async def my_market(message: Message):
    userid = message.from_user.id
    lang = await get_lang(message.from_user.id)
    chatid = message.chat.id

    res = await Seller.find_one(Seller.owner_id == userid)
    if res:
        text, markup, image = await seller_ui(userid, lang, True)
        try:
            await bot.send_photo(chatid, image, caption=text, reply_markup=markup)
        except:
            await bot.send_photo(chatid, image, caption=text, reply_markup=markup)

@main_router.message(IsPrivateChat(), Text('commands_name.seller_profile.add_product'), IsAuthorizedUser())
async def add_product_com(message: Message):
    userid = message.from_user.id
    lang = await get_lang(message.from_user.id)
    chatid = message.chat.id

    options = {
        "🍕 ➞ 🪙": 'items_coins',
        "🪙 ➞ 🍕": 'coins_items',
        "🍕 ➞ 🍕": 'items_items',
        "🍕 ➞ ⏳": 'auction'
    }

    b_list = list(options.keys())
    markup = list_to_keyboard(
        [b_list, t('buttons_name.cancel', lang)], 2
    )

    await bot.send_message(chatid, t('add_product.options_info', lang), reply_markup=markup)
    # await ChooseOptionState(prepare_data_option, userid, chatid, lang, options)
    await ChooseOptionHandler(
        prepare_data_option, userid, chatid, lang, options).start()

@main_router.message(IsPrivateChat(), Text('commands_name.seller_profile.my_products'), IsAuthorizedUser())
async def my_products(message: Message):
    userid = message.from_user.id
    lang = await get_lang(message.from_user.id)
    chatid = message.chat.id

    user_prd = await Product.find(Product.owner_id == userid).to_list()
    rand_p = {}

    if user_prd:
        for product in user_prd:
            p_dict = product.dict()
            rand_p[
                preview_product(p_dict['items'], p_dict['price'], 
                                p_dict['type'], lang)
            ] = str(product.id)

        await bot.send_message(chatid, t('products.search', lang))

        await ChoosePagesStateHandler(
            send_info_pr, userid, chatid, lang, rand_p, 1, 3, None, False, False).start()
    else:
        text = t('no_products', lang)
        await bot.send_message(chatid, text)

@main_router.callback_query(F.data.startswith('product_info'))
async def product_info(call: CallbackQuery):
    call_data = call.data.split()
    chatid = call.message.chat.id
    userid = call.from_user.id
    lang = await get_lang(call.from_user.id)

    call_type = call_data[1]
    alt_id = call_data[3] if call_type in ['item_detail', 'itd'] else call_data[2]
    product = await Product.find_one(Product.alt_id == alt_id)
    if product:
        prd_dict = product.dict()
        if call_type == 'delete':
            if product.owner_id == userid:

                await bot.edit_message_reply_markup(None, chatid, call.message.message_id, reply_markup=list_to_inline([]))

                status = await delete_product(None, alt_id)

                if status: text = t('product_info.delete', lang)
                else: text = t('product_info.error', lang)

                markup = list_to_inline([])
                if getattr(call.message, 'photo', None):
                    await bot.edit_message_caption(caption=text, chat_id=chatid, message_id=call.message.message_id, reply_markup=markup)
                else:
                    await bot.edit_message_text(text, chat_id=chatid, message_id=call.message.message_id, reply_markup=markup)
        else:
            if call_type == 'edit_price' and product.owner_id == userid:
                await prepare_edit_price(userid, chatid, lang, alt_id)

            elif call_type == 'add' and product.owner_id == userid:
                await prepare_add(userid, chatid, lang, alt_id)

            elif call_type in ['item_detail', 'itd']:
                code = call_data[2]
                from bot.modules.items.item import decode_item, item_info
                from bot.config import conf

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

                back_btn_text = t("buttons_name.back", lang)
                back_callback = f"product_info info {alt_id}"
                markup = list_to_inline([{back_btn_text: back_callback}], 1)

                if getattr(call.message, 'photo', None):
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

            elif call_type == 'buy' and product.owner_id != userid:
                if product.owner_id != userid:
                    await buy_item(userid, chatid, lang, prd_dict, 
                                   await User.get_user_name(userid), call.message.message_id)

            elif call_type == 'info':
                text, markup = await product_ui(lang, product.id, 
                                          product.owner_id == userid, html=True)

                import re
                text = re.sub(r'!\[(.*?)\]\(tg://emoji\?id=(\d+)\)', r'<tg-emoji emoji-id="\2">\1</tg-emoji>', text)
                text = re.sub(r'\*([^*\n]+)\*', r'<b>\1</b>', text)
                text = re.sub(r'_([_\n]+)_', r'<i>\1</i>', text)

                if userid == call.message.chat.id:
                    if getattr(call.message, 'photo', None):
                        from bot.modules.images import get_items_photo_media
                        from bot.redismanager import redis_set
                        from aiogram.types import InputMediaPhoto
                        
                        media_file, redis_key = await get_items_photo_media(product.items)
                        media = InputMediaPhoto(media=media_file, caption=text)
                        try:
                            mes = await bot.edit_message_media(
                                chat_id=chatid,
                                message_id=call.message.message_id,
                                media=media,
                                reply_markup=markup
                            )
                            if redis_key and mes and mes.photo:
                                await redis_set(redis_key, mes.photo[-1].file_id)
                        except Exception:
                            await bot.edit_message_caption(
                                chat_id=chatid,
                                message_id=call.message.message_id,
                                caption=text,
                                reply_markup=markup
                            )
                    else:
                        from bot.modules.images import send_items_photo
                        try:
                            await bot.delete_message(chatid, call.message.message_id)
                        except Exception:
                            pass
                        await send_items_photo(chatid, product.items, text, reply_markup=markup)
                else:
                    from bot.modules.images import send_items_photo
                    await send_items_photo(userid, product.items, text, reply_markup=markup)
                
                if userid != call.message.chat.id:

                    await call.answer(
                        t('product_info.call_channel', lang),
                        show_alert=True
                    )

            elif call_type == 'promotion' and product.owner_id == userid:
                await promotion_prepare(userid, chatid, lang, product.id, 
                                        call.message.message_id)

@main_router.callback_query(IsPrivateChat(), F.data.startswith('seller'))
async def seller(call: CallbackQuery):
    call_data = call.data.split()
    chatid = call.message.chat.id
    userid = call.from_user.id
    lang = await get_lang(call.from_user.id)

    call_type = call_data[1]
    owner_id = int(call_data[2])

    # Кнопки вызываемые владельцем
    if call_type == 'cancel_all':
        await prepare_delete_all(userid, chatid, lang, call.message.message_id)
    elif call_type == 'edit_text':
        await pr_edit_description(userid, chatid, lang, call.message.message_id)
    elif call_type == 'edit_name':
        await pr_edit_name(userid, chatid, lang, call.message.message_id)
    elif call_type == 'edit_image':
        user = await User.find_one(User.userid == userid)
        is_premium = await user.premium if user else False
        if is_premium:
            await pr_edit_image(userid, chatid, lang, call.message.message_id)
        else:
            await bot.send_message(chatid, t('no_premium', lang))
            
    elif call_type == 'push_channel':
        push_obj = await Puhs.find_one(Puhs.owner_id == userid)
        seller_obj = await Seller.find_one(Seller.owner_id == userid)
        behavior = getattr(seller_obj, 'stock_out_behavior', 'zero') if seller_obj else 'zero'
        
        info_text = t('push.push_info', lang)
        bot_user = await bot.get_me()
        bot_username = bot_user.username
        
        if push_obj:
            channel_info = t('push.connected_channel_info', lang, channel_id=push_obj.channel_id)
            behavior_text = t(f'push.behavior.{behavior}', lang)
            text = f"{channel_info}\n⚙ <b>{t('push.behavior_label', lang)}</b> {behavior_text}\n\n{info_text}"
            
            buttons = [
                [
                    {
                        t('buttons_name.toggle_behavior', lang): f"seller toggle_behavior {owner_id}"
                    }
                ],
                [
                    {
                        t('buttons_name.delete_push', lang): f"seller delete_push {owner_id}"
                    }
                ],
                [
                    {
                        t('buttons_name.back', lang): f"seller info {owner_id}"
                    }
                ]
            ]
        else:
            text = f"{info_text}\n\n_❌ {t('push.no_channel', lang)}_"
            buttons = [
                [
                    {
                        "text": t('buttons_name.add_to_channel', lang),
                        "url": f"https://t.me/{bot_username}?startchannel=true"
                    }
                ],
                [
                    {
                        t('buttons_name.back', lang): f"seller info {owner_id}"
                    }
                ]
            ]
            
        markup = list_to_inline(buttons)
        try:
            await bot.edit_message_caption(chat_id=chatid, message_id=call.message.message_id, caption=text, reply_markup=markup)
        except Exception:
            await bot.edit_message_text(chat_id=chatid, message_id=call.message.message_id, text=text, reply_markup=markup)
            
    elif call_type == 'toggle_behavior':
        seller_obj = await Seller.find_one(Seller.owner_id == userid)
        if seller_obj:
            current = getattr(seller_obj, 'stock_out_behavior', 'zero')
            new_behavior = 'delete' if current == 'zero' else 'zero'
            seller_obj.stock_out_behavior = new_behavior
            await seller_obj.save()
            
        if hasattr(call, 'model_copy'):
            call = call.model_copy(update={'data': f"seller push_channel {owner_id}"})
        elif hasattr(call, 'copy'):
            call = call.copy(update={'data': f"seller push_channel {owner_id}"})
        else:
            call.data = f"seller push_channel {owner_id}"
        await globals()['seller'](call)
        
    elif call_type == 'delete_push':
        push_obj = await Puhs.find_one(Puhs.owner_id == userid)
        if push_obj:
            await push_obj.delete()
            
        if hasattr(call, 'model_copy'):
            call = call.model_copy(update={'data': f"seller push_channel {owner_id}"})
        elif hasattr(call, 'copy'):
            call = call.copy(update={'data': f"seller push_channel {owner_id}"})
        else:
            call.data = f"seller push_channel {owner_id}"
        await globals()['seller'](call)

    # Кнопки вызываемые не владельцем
    elif call_type == 'info':
        my_status = owner_id == userid
        seller = await Seller.find_one(Seller.owner_id == owner_id)

        if seller:
            text, markup, image = await seller_ui(owner_id, lang, my_status)

            # If alt_id is provided, add a back button to return to the product!
            if len(call_data) > 3:
                alt_id = call_data[3]
                back_btn_text = t("buttons_name.back", lang)
                back_callback = f"product_info info {alt_id}"
                
                from aiogram.utils.keyboard import InlineKeyboardBuilder
                from aiogram.types import InlineKeyboardButton
                builder = InlineKeyboardBuilder.from_markup(markup)
                builder.row(InlineKeyboardButton(text=back_btn_text, callback_data=back_callback))
                markup = builder.as_markup()

            from aiogram.types import InputMediaPhoto
            try:
                # Try to edit both media and caption
                media = InputMediaPhoto(media=image, caption=text)
                await bot.edit_message_media(chat_id=chatid, message_id=call.message.message_id, media=media, reply_markup=markup)
            except Exception:
                try:
                    await bot.edit_message_caption(chat_id=chatid, message_id=call.message.message_id, caption=text, reply_markup=markup)
                except Exception:
                    try:
                        await bot.send_photo(chatid, image, caption=text, reply_markup=markup)
                    except:
                        await bot.send_photo(chatid, image, caption=text, reply_markup=markup)

    elif call_type == 'all':
        user_prd = await Product.find(Product.owner_id == owner_id).to_list()

        rand_p = {}
        for product in user_prd:
            p_dict = product.dict()
            rand_p[
                preview_product(p_dict['items'], p_dict['price'], 
                                p_dict['type'], lang)
            ] = str(product.id)

        await bot.send_message(chatid, t('products.search', lang))
        # await ChoosePagesState(send_info_pr, userid, chatid, lang, rand_p, 1, 3, 
        #                        None, False, False)
        await ChoosePagesStateHandler(
            send_info_pr, userid, chatid, lang, rand_p, 1, 3, None, False, False).start()

@main_router.message(IsPrivateChat(), Text('commands_name.market.random'), IsAuthorizedUser())
async def random_products(message: Message):
    userid = message.from_user.id
    lang = await get_lang(message.from_user.id)
    chatid = message.chat.id

    # Count all products except user's own
    total = await Product.find(Product.owner_id != userid).count()

    if not total:
        await bot.send_message(chatid, t('products.null', lang))
        return

    # Each "window" = 18 items (6 rows × 3 cols in ChoosePagesStateHandler 2×3)
    # We want to pre-load 3 windows (prev + current + next) = 54 items for seamless scrolling
    WINDOW = 18
    LOAD = WINDOW * 3  # 54 items total

    # Pick a random starting position (skip)
    skip = random.randint(0, max(0, total - 1))

    # Load LOAD items starting at skip, wrapping around the collection
    products_head = await (
        Product.find(Product.owner_id != userid)
        .skip(skip)
        .limit(LOAD)
        .to_list()
    )

    # If we got fewer than LOAD items (hit the end), wrap around from the beginning
    if len(products_head) < LOAD:
        remaining = LOAD - len(products_head)
        products_tail = await (
            Product.find(Product.owner_id != userid)
            .limit(remaining)
            .to_list()
        )
        # Avoid duplicates if total < LOAD
        tail_ids = {p.id for p in products_head}
        products_tail = [p for p in products_tail if p.id not in tail_ids]
        all_products = products_head + products_tail
    else:
        all_products = products_head

    rand_p = {}
    for prd in all_products:
        prd_dict = prd.dict()
        key = preview_product(prd_dict['items'], prd_dict['price'], prd_dict['type'], lang)
        # Ensure unique keys (preview_product may produce identical strings for different products)
        while key in rand_p:
            key += '\u200b'  # append zero-width space
        rand_p[key] = str(prd.id)

    await bot.send_message(chatid, t('products.search', lang))

    # Jump to the middle window (page 3) only if we filled all 3 windows (54 items).
    # Otherwise start from page 0 so the first page is always fully populated.
    if len(all_products) >= LOAD:
        items_per_page = 2 * 3   # horizontal × vertical
        start_page = WINDOW // items_per_page  # = 3
    else:
        start_page = 0

    await ChoosePagesStateHandler(
        send_info_pr, userid, chatid, lang, rand_p, 2, 3, None, False, False,
        page=start_page
    ).start()


@main_router.message(IsPrivateChat(), Text('commands_name.market.find'), IsAuthorizedUser())
async def find_products(message: Message):
    userid = message.from_user.id
    lang = await get_lang(message.from_user.id)
    chatid = message.chat.id

    await find_prepare(userid, chatid, lang)

@main_router.callback_query(IsPrivateChat(), F.data.startswith('create_push'))
async def push(call: CallbackQuery):
    call_data = call.data.split()
    chatid = call.message.chat.id
    userid = call.from_user.id
    lang = await get_lang(call.from_user.id)

    channel_id = int(call_data[1])

    res = await Puhs.find_one(Puhs.owner_id == userid)
    if res:
        res.channel_id = channel_id
        res.lang = lang
        await res.save()
        text = t('push.update', lang)
    else: 
        await create_push(userid, channel_id, lang)
        text = t('push.new', lang)

    await bot.send_message(userid, text)
    await bot.edit_message_reply_markup(None, chatid, call.message.message_id, 
                                        reply_markup=InlineKeyboardMarkup(inline_keyboard=[]))

@main_router.message(IsPrivateChat(), Text('commands_name.market.search_markets'), IsAuthorizedUser())
async def search_markets(message: Message):
    userid = message.from_user.id
    lang = await get_lang(message.from_user.id)
    chatid = message.chat.id

    mrk = list_to_inline([
        {
            t('search_markets.random', lang): 'random_markets',
            t('search_markets.find', lang): 'find_markets'
        }
    ])

    await bot.send_message(chatid, t('search_markets.text', lang),
                          reply_markup=mrk)

@main_router.callback_query(IsPrivateChat(), F.data.startswith('random_markets'))
async def random_markets(call: CallbackQuery):
    call_data = call.data.split()
    chatid = call.message.chat.id
    userid = call.from_user.id

    lang = await get_lang(userid)

    # Получаем случайные магазины
    all_markets = await Seller.find(Seller.owner_id != userid).to_list()
    markets = random.sample(all_markets, min(15, len(all_markets))) if all_markets else []

    if not markets:
        await bot.edit_message_text(
            t('search_markets.no_markets', lang),
            chat_id=chatid,
            message_id=call.message.message_id
        )
        return

    # Формируем список магазинов для отображения
    market_list = {}
    for market in markets: 
        if market.owner_id:
            market_list[market.name] = market.owner_id

    await ChoosePagesStateHandler(
            send_seller_info, userid, chatid, lang, market_list, 1, 3, None, False, False).start()

async def send_seller_info(option, transmitted_data: dict):
    chatid = transmitted_data['chatid']
    lang = transmitted_data['lang']
    userid = transmitted_data['userid']

    text, markup, image = await seller_ui(option, lang, False)
    try:
        await bot.send_photo(chatid, image, caption=text, reply_markup=markup)
    except:
        await bot.send_photo(chatid, image, caption=text, reply_markup=markup)

@main_router.callback_query(IsPrivateChat(), F.data.startswith('find_markets'))
async def find_markets(call: CallbackQuery):
    call_data = call.data.split()
    chatid = call.message.chat.id
    userid = call.from_user.id

    lang = await get_lang(userid)
    
    await bot.send_message(
        chatid,
        t('search_markets.find_market', lang),
        reply_markup=cancel_markup(lang)
    )

    await ChooseStringHandler(
        find_prepare_mk, userid, chatid, lang, 3, 50).start()

async def find_prepare_mk(return_data, transmitted_data):
    chatid = transmitted_data['chatid']
    lang = transmitted_data['lang']
    userid = transmitted_data['userid']
    name = return_data.lower()

    # Получаем все магазины кроме своего
    markets = await Seller.find(Seller.owner_id != userid).to_list()

    if not markets:
        await bot.send_message(chatid, t('search_markets.no_markets', lang))
        return

    # Ищем совпадения имен
    market_list = {}
    for market in markets:
        market_name = market.name.lower()

        # Считаем процент совпадения через fuzzywuzzy
        similarity = fuzz.ratio(name, market_name)

        # Если совпадение больше 60%
        if similarity >= 60:
            if market.owner_id:
                market_list[market.name] = market.owner_id

    if market_list:
        await ChoosePagesStateHandler(
            send_seller_info, userid, chatid, lang, market_list, 1, 3, None, False, False).start()
    else:
        await bot.send_message(chatid, t('search_markets.no_markets', lang),
                               reply_markup=await m(userid, 'last_menu', lang))
