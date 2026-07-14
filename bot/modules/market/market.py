from time import time
from bson.objectid import ObjectId

from bot.exec import main_router, bot
from bot.modules.data_format import list_to_inline, random_code, seconds_to_str, item_list, escape_markdown
from bot.modules.items.item import counts_items, get_item_dict, get_name, AddItemToUser, CheckCountItemFromUser, RemoveItemFromUser
from bot.modules.items.item import get_data as get_item_data
from bot.modules.images import async_open
from bot.modules.localization import get_data, t, get_lang
from bot.models.user import User
from bot.modules.notifications import user_notification
from bot.modules.items.collect_items import get_all_items

ITEMS = get_all_items()

async def generation_code(owner_id: int):
    from bot.models.market import Product
    return await Product.generation_code(owner_id)

async def add_product(owner_id: int, product_type: str, items: list, price, in_stock: int = 1,
                add_arg: dict | None = None):
    from bot.models.market import Product
    return await Product.add(owner_id, product_type, items, price, in_stock, add_arg)

async def create_seller(owner_id: int, name: str, description: str):
    from bot.models.market import Seller
    return await Seller.create_shop(owner_id, name, description)

async def seller_ui(owner_id: int, lang: str, my_market: bool, name: str = ''):
    from bot.models.market import Seller
    seller = await Seller.find_one(Seller.owner_id == owner_id)
    if seller:
        return await seller.get_ui(my_market, lang, name)
    return '', None, None

def generate_items_pages(ignored_id: list | None = None, ignore_cant: bool = False):
    if ignored_id is None: ignored_id = []
    
    items = []
    exclude = ignored_id
    for key, item in ITEMS.items():
        data = get_item_dict(key)

        if not ignore_cant:
            if 'cant_sell' in item and item['cant_sell']:
                if key not in exclude:
                    exclude.append(key)
            elif key not in exclude:
                items.append({'item': data, 'count': 1})
        else:
            items.append({'item': data, 'count': 1})

    return items, exclude

async def get_active_market_item_ids() -> list[str]:
    """Returns item_ids that currently have at least one active product listing.
    Result is cached in Redis for 30 minutes."""
    from bot.redismanager import redis_get, redis_set
    import json

    CACHE_KEY = 'market:active_item_ids'
    cached = await redis_get(CACHE_KEY)
    if cached:
        try:
            return json.loads(cached)
        except Exception:
            pass

    from bot.models.market import Product
    active_ids: set[str] = set()
    products = await Product.find().to_list()
    for product in products:
        for item_id in (product.items_id or []):
            if item_id:
                active_ids.add(item_id)

    result = sorted(active_ids)
    await redis_set(CACHE_KEY, json.dumps(result), ex=1800)
    return result


async def generate_sell_pages(user_id: int, ignored_id: list | None = None):
    if ignored_id is None: ignored_id = []
    
    items, count = await User.get_inventory(user_id, ignored_id)
    exclude = ignored_id
    for item in list(items):
        i = item['items_data']
        data = get_item_data(i['item_id'])

        if 'abilities' in i and 'interact' in i['abilities'] and not i['abilities']['interact']:
            exclude.append(i['item_id'])
            items.remove(item)
        elif 'cant_sell' in data and data['cant_sell']:
            exclude.append(i['item_id'])
            items.remove(item)
    return items, exclude

async def product_ui(lang: str, product_id: ObjectId, i_owner: bool = False, html: bool = False):
    from bot.models.market import Product, Seller
    text, coins_text, data_buttons = '', '', []

    product = await Product.get(product_id)
    if product:
        seller = await Seller.find_one(Seller.owner_id == product.owner_id)
        if seller:
            product_type = product.type
            items = list(product.items)
            price = product.price

            items_id = []
            for i in items: 
                if 'count' in i:
                    items_id += [i['item_id']] * i['count']
                else: 
                    items_id.append(i['item_id'])

            items_text = counts_items(items_id, lang, html=html)

            if product_type in ['items_coins', 'coins_items', 'auction']:
                coins_text = str(price)

            elif product_type in ['items_items']:
                items_price = []
                for i in price: items_price.append(i['item_id'])
                coins_text = counts_items(items_price, lang, html=html)

            text += t('product_ui.cap', lang) + '\n\n'
            text += t('product_ui.type', lang, type=t(f'product_ui.types.{product_type}', lang)) + '\n'
            text += t('product_ui.in_stock', lang, now=product.bought, all=product.in_stock) + '\n\n'

            if product_type != 'auction':
                text += t(f'product_ui.text.{product_type}', lang,
                        items=items_text, price=coins_text)
            else:
                end_time = seconds_to_str(product.end - int(time()), lang, max_lvl='hour')
                min_add = product.min_add

                if product.users:
                    users = ''
                    members = list(sorted(product.users, key=lambda x: x['coins'], reverse=True))

                    max_ind = 3
                    if len(members) < max_ind: max_ind = len(members)
                    for i in range(max_ind):
                        name = members[i]['name']
                        coins = members[i]['coins']
                        users += f'{i+1}. {name} - {coins} 🪙'

                        if i != max_ind-1: users += '\n'

                else: users = t('product_ui.no_action_users', lang)

                text += t(f'product_ui.text.{product_type}', lang,
                        items=items_text, price=coins_text, end_time=end_time, min_add=min_add, users=users)

            b_data = get_data(f'product_ui.buttons', lang)
            alt_id = product.alt_id
            if i_owner:
                from bot.const import GAME_SETTINGS

                add_time = product.add_time
                duration = GAME_SETTINGS.get('market_product_duration', 86400 * 31)
                time_end = (add_time + duration) - int(time())

                if product_type in ['auction', 'items_coins']:
                    text += f'\n\n' + t(f'product_ui.owner_message', lang, 
                                        time=seconds_to_str(time_end, lang, max_lvl='day'))

                data_buttons = [
                    {},
                    {
                        b_data['delete']: f'product_info delete {alt_id}'
                    }
                ]
                if not await is_promotion(product.id):
                    data_buttons[1][b_data['promotion']] = f'product_info promotion {alt_id}'
                else:
                    data_buttons[1][b_data['alredy_promotion']] = f' '

                if product_type != 'auction':
                    data_buttons[0][b_data['add']] = f'product_info add {alt_id}'

                if product_type in ['items_coins', 'coins_items']:
                    data_buttons[0][b_data['edit_price']] = f'product_info edit_price {alt_id}'

            else:
                action_btn = {}
                if product_type == 'auction':
                    action_btn = {
                        "text": b_data['auction'],
                        "callback_data": f"product_info buy {alt_id}"
                    }
                elif product_type == 'coins_items':
                    action_btn = {
                        "text": b_data['sell'],
                        "callback_data": f"product_info buy {alt_id}"
                    }
                else:
                    action_btn = {
                        "text": b_data['buy'],
                        "callback_data": f"product_info buy {alt_id}"
                    }

                data_buttons = [
                    [
                        {
                            "text": f"🔎 {seller.name}",
                            "callback_data": f"seller info {seller.owner_id} {alt_id}"
                        },
                        action_btn
                    ]
                ]

                from bot.modules.items.item import get_name, item_code
                from bot.const import ITEMS_CUSTOM_EMOJIS

                unique_items = []
                seen_ids = set()
                for item in product.items:
                    item_id = item['item_id']
                    if item_id not in seen_ids:
                        seen_ids.add(item_id)
                        unique_items.append(item)

                item_btns = []
                for item in unique_items:
                    item_id = item['item_id']
                    code = await item_code(item)

                    emoji_data = ITEMS_CUSTOM_EMOJIS.get(item_id, {})
                    custom_emoji_id = emoji_data.get('id')

                    btn_text = get_name(item_id, lang, with_emoji=False, custom_emoji=False)

                    btn_dict = {
                        "text": btn_text,
                        "callback_data": f"product_info item_detail {code} {alt_id}"
                    }
                    if custom_emoji_id:
                        btn_dict["custom_emoji_id"] = custom_emoji_id

                    item_btns.append(btn_dict)

                # Group into rows of 2
                for i in range(0, len(item_btns), 2):
                    data_buttons.append(item_btns[i:i + 2])

    buttons = list_to_inline(data_buttons)
    return text, buttons

async def send_view_product(product_id: ObjectId, owner_id: int):
    from bot.models.market import Product, Puhs
    res = await Puhs.find_one(Puhs.owner_id == owner_id)
    product = await Product.get(product_id)

    if res and product:
        channel = res.channel_id
        lang = res.lang

        text, markup = await product_ui(lang, product_id, False, html=True)

        import re
        text = re.sub(r'!\[(.*?)\]\(tg://emoji\?id=(\d+)\)', r'<tg-emoji emoji-id="\2">\1</tg-emoji>', text)
        text = re.sub(r'\*([^*\n]+)\*', r'<b>\1</b>', text)
        text = re.sub(r'_([_\n]+)_', r'<i>\1</i>', text)

        buttons = [
            {
                t('product_ui.buttons.view', lang): f"product_info info {product.alt_id}"
            }
        ]

        markup = list_to_inline(buttons)
        if channel:
            from bot.modules.images import send_items_photo
            mes = await send_items_photo(channel, product.items, text, reply_markup=markup, parse_mode='HTML')
            if mes:
                product.message_id = mes.message_id
                await product.save()

async def create_push(owner_id: int, channel_id: int, lang: str):
    from bot.models.market import Puhs
    data = Puhs(
        owner_id=owner_id,
        channel_id=channel_id,
        lang=lang
    )
    await data.insert()

async def delete_product(baseid = None, alt_id = None):
    from bot.models.market import Product
    return await Product.delete_product(baseid, alt_id)

async def new_participant(baseid: ObjectId, userid: int, coins: int, name: str, lang: str):
    from bot.models.market import Product
    product = await Product.get(baseid)
    if product:
        return await product.new_participant(baseid, userid, coins, name, lang)
    return False

def _truncate_items_text(id_list: list, lang: str, max_names: int = 3, html: bool = False) -> str:
    """Возвращает строку имён предметов.
    Если html=True, то включает кастомные эмодзи в HTML формате."""
    from collections import Counter
    dct: dict = {}
    for i in id_list:
        if isinstance(i, str):
            dct[i] = dct.get(i, 0) + 1
        elif isinstance(i, dict):
            dct[i['item_id']] = dct.get(i['item_id'], 0) + i.get('count', 1)

    names = []
    for item, col in dct.items():
        name = get_name(item, lang, html=html, custom_emoji=html)
        if col > 1:
            name += f' x{col}'
        names.append(name)

    total = len(names)
    if total > max_names:
        shown = names[:max_names]
        extra = total - max_names
        return ', '.join(shown) + f' ...+{extra}'
    return ', '.join(names) if names else '-'


def preview_product(items: list, price, ptype: str, lang: str, html: bool = False):
    text = ''

    id_list = []
    for i in items: 
        if 'count' in i:
            id_list += [i['item_id']] * i['count']
        else: 
            id_list.append(i['item_id'])

    items_text = _truncate_items_text(id_list, lang, html=html)

    if type(price) == int:
        price_text = f'{price} 🪙'
    else: 
        id_list = []
        for i in price: id_list.append(i['item_id'])
        price_text = _truncate_items_text(id_list, lang, html=html)

    if ptype != 'coins_items':
        text = f'{items_text} = {price_text}'
    else: text = f'{price_text} = {items_text}'
    if ptype == 'auction': text += ' (⌛)'

    return text

async def buy_product(pro_id: ObjectId, col: int, userid: int, name: str, lang: str=''):
    from bot.models.market import Product
    return await Product.buy_product(pro_id, col, userid, name, lang)

async def create_preferential(product_id: ObjectId, seconds: int, owner_id: int):
    from bot.models.market import Preferential, Product
    product_obj = await Product.find_one(Product.id == product_id)
    data = Preferential(
        product=product_obj,
        end=seconds + int(time()),
        userid=owner_id
    )
    await data.insert()
    await Preferential.create_task(data.id, data.end)

async def check_preferential(owner_id: int, product_id: ObjectId):
    from bot.models.market import Preferential
    col = await Preferential.find(Preferential.userid == owner_id).count()
    perf = await Preferential.find(Preferential.product.id == product_id).count()
    user = await User.find_one(User.userid == owner_id)
    premium_st = await user.premium if user else False

    from bot.const import GAME_SETTINGS
    pref_cfg = GAME_SETTINGS.get('market_preferential_limit', {"premium": 10, "standard": 5})
    if premium_st: un = pref_cfg.get('premium', 10)
    else: un = pref_cfg.get('standard', 5)

    if col >= un: return False, 1
    if perf > 0: return False, 2
    return True, 0

async def is_promotion(product_id: ObjectId):
    from bot.models.market import Preferential
    col = await Preferential.find(Preferential.product.id == product_id).count()
    return col