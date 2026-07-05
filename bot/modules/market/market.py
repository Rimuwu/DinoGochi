from time import time
from bson.objectid import ObjectId

from bot.exec import main_router, bot
from bot.modules.data_format import list_to_inline, random_code, seconds_to_str, item_list, escape_markdown
from bot.modules.items.item import counts_items, get_item_dict, AddItemToUser, CheckCountItemFromUser, RemoveItemFromUser
from bot.modules.items.item import get_data as get_item_data
from bot.modules.images import async_open
from bot.modules.localization import get_data, t, get_lang
from bot.modules.user.user import get_inventory, premium, user_name
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

async def generate_sell_pages(user_id: int, ignored_id: list | None = None):
    if ignored_id is None: ignored_id = []
    
    items, count = await get_inventory(user_id, ignored_id)
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

async def product_ui(lang: str, product_id: ObjectId, i_owner: bool = False):
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

            items_text = counts_items(items_id, lang)

            if product_type in ['items_coins', 'coins_items', 'auction']:
                coins_text = str(price)

            elif product_type in ['items_items']:
                items_price = []
                for i in price: items_price.append(i['item_id'])
                coins_text = counts_items(items_price, lang)

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
                data_buttons = [
                    {
                        f"🔎 {seller.name}": f"seller info {seller.owner_id}"
                    },
                    {
                        f"{b_data['items_info']}": f"product_info items {alt_id}"
                    }
                ]
                if product_type == 'auction':
                    data_buttons[0][b_data['auction']] = f"product_info buy {alt_id}"
                elif product_type == 'coins_items':
                    data_buttons[0][b_data['sell']] = f"product_info buy {alt_id}"
                else:
                    data_buttons[0][b_data['buy']] = f"product_info buy {alt_id}"

    buttons = list_to_inline(data_buttons)
    return text, buttons

async def send_view_product(product_id: ObjectId, owner_id: int):
    from bot.models.market import Product, Puhs
    res = await Puhs.find_one(Puhs.userid == owner_id)
    # Check if there is data
    # Wait, in old db, puhs had owner_id / userid. Let's find by userid first
    if not res:
        # Fallback to old field names if any
        res = await Puhs.find_one(Puhs.userid == owner_id)

    product = await Product.get(product_id)

    if res and product:
        channel = res.data.get('channel_id') if hasattr(res, 'data') and res.data else None
        if not channel:
            # Fallback
            channel = getattr(res, 'channel_id', None)
        lang = getattr(res, 'lang', 'en')

        text, markup = await product_ui(lang, product_id, False)

        buttons = [
            {
                t('product_ui.buttons.view', lang): f"product_info info {product.alt_id}"
            }
        ]

        markup = list_to_inline(buttons)
        if channel:
            await bot.send_message(channel, text, reply_markup=markup, parse_mode='Markdown')

async def create_push(owner_id: int, channel_id: int, lang: str):
    from bot.models.market import Puhs
    data = Puhs(
        userid=owner_id,
        data={
            'channel_id': channel_id,
            'lang': lang
        }
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

def preview_product(items: list, price, ptype: str, lang: str):
    text = ''

    id_list = []
    for i in items: 
        if 'count' in i:
            id_list += [i['item_id']] * i['count']
        else: 
            id_list.append(i['item_id'])

    items_text = counts_items(id_list, lang)

    if type(price) == int: price_text = f'{price} 🪙'
    else: 
        id_list = []
        for i in price: id_list.append(i['item_id'])
        price_text = counts_items(id_list, lang)

    if ptype != 'coins_items':
        text = f'{items_text} = {price_text}'
    else: text = f'{price_text} = {items_text}'
    if ptype == 'auction': text += ' (⌛)'

    return text

async def buy_product(pro_id: ObjectId, col: int, userid: int, name: str, lang: str=''):
    from bot.models.market import Product
    return await Product.buy_product(pro_id, col, userid, name, lang)

async def create_preferential(product_id: ObjectId, seconds: int, owner_id: int):
    from bot.models.market import Preferential
    data = Preferential(
        product_id=str(product_id),
        end=seconds + int(time()),
        userid=owner_id
    )
    await data.insert()

async def check_preferential(owner_id: int, product_id: ObjectId):
    from bot.models.market import Preferential
    col = await Preferential.find(Preferential.userid == owner_id).count()
    perf = await Preferential.find(Preferential.product_id == str(product_id)).count()
    premium_st = await premium(owner_id)

    from bot.const import GAME_SETTINGS
    pref_cfg = GAME_SETTINGS.get('market_preferential_limit', {"premium": 10, "standard": 5})
    if premium_st: un = pref_cfg.get('premium', 10)
    else: un = pref_cfg.get('standard', 5)

    if col >= un: return False, 1
    if perf > 0: return False, 2
    return True, 0

async def is_promotion(product_id: ObjectId):
    from bot.models.market import Preferential
    col = await Preferential.find(Preferential.product_id == str(product_id)).count()
    return col