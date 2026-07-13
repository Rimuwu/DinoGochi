from bot.modules.data_format import item_list
from bot.modules.items.item import CheckCountItemFromUser, RemoveItemFromUser
from bot.modules.localization import t
from bot.exec import bot, log
from bot.modules.market.market import add_product, product_ui

from bot.modules.states_fabric.state_handlers import ChooseStepHandler
from bot.modules.states_fabric.steps_datatype import BaseUpdateType, ConfirmStepData, IntStepData, InventoryStepData, StepMessage, TimeStepData
 
from bot.models.user import User
from bot.modules.markup import cancel_markup, markups_menu as m

from bot.const import GAME_SETTINGS
MAX_PRICE = GAME_SETTINGS.get('market_max_price', 10_000_000)

async def coins_stock(return_data, transmitted_data):
    """ Функция для запроса цены и запаса 
    """
    chatid = transmitted_data['chatid']
    userid = transmitted_data['userid']
    lang = transmitted_data['lang']
    option = transmitted_data['option']
    

    if 'col' not in return_data:
        items_list = return_data['items']
        return_data['items'] = [{'item_id': i['item_id'], 'abilities': i.get('abilities', {})} for i in items_list]
        return_data['col'] = [i['count'] for i in items_list]
    elif type(return_data['items']) != list:
        return_data['items'] = [return_data['items']]
        return_data['col'] = [return_data['col']]

    steps = [
        IntStepData('price', StepMessage(
            text=f'add_product.coins.{option}',
            translate_message=True,
            markup=cancel_markup(lang)),
            max_int=MAX_PRICE
        ),
        IntStepData('in_stock', StepMessage(
            text=f'add_product.stock.{option}',
            translate_message=True,
            markup=cancel_markup(lang)),
            max_int=100
        ),
    ]

    transmitted_data = {
        'items': return_data['items'],
        'col': return_data['col'],
        'option': transmitted_data['option']
    }

    await ChooseStepHandler(end, userid, chatid,
                          lang, steps,
                          transmitted_data=transmitted_data).start()

async def end(return_data, transmitted_data):
    """ Последняя функция, создаёт продукт и проверяте монеты / предметы
    """
    chatid = transmitted_data['chatid']
    userid = transmitted_data['userid']
    lang = transmitted_data['lang']

    option = transmitted_data['option']
    price = return_data['price']
    items = transmitted_data['items']
    col = transmitted_data['col']

    product_status, add_arg = True, {}
    text = t('add_product.all_good', lang)

    if 'in_stock' in return_data:
        in_stock = return_data['in_stock']
    else: in_stock = transmitted_data['in_stock']

    a = 0
    for item in items: 
        item['count'] = col[a]
        a += 1

    from bot.modules.overwriting.DataCalsses import Transaction
    async with Transaction():
        user = await User.find_one(User.userid == userid)
        if not user:
            return

        if option == 'coins_items':  
            # Проверить количество монет 
            res = await user.remove_coins(price * in_stock)
            if not res:
                product_status = False
                text = t('add_product.few_coins', lang, coins=price*in_stock)

        elif option in ['items_coins', 'items_items', 'auction']:  
            # Проверить предметы
            items_status = []
            for item in items:
                item_id = item['item_id']
                count = item['count']

                if 'abilities' in item: abil = item['abilities']
                else: abil = {}

                status = await CheckCountItemFromUser(userid, 
                                count * in_stock, item_id, abil)
                items_status.append(status)

            if not all(items_status):
                product_status = False
                text = t('add_product.no_items', lang)
            else:
                for item in items:
                    item_id = item['item_id']
                    count = item['count']

                    if 'abilities' in item: abil = item['abilities']
                    else: abil = {}

                    await user.remove_item(item_id, count * in_stock, abil)

        if option == 'auction':
            add_arg['min_add'] = return_data['min_add']
            add_arg['end'] = return_data['time_end']

        elif option == 'items_items':
            price = item_list(price)

        if product_status:
            pr_id = await add_product(userid, option, items, 
                                      price, in_stock, add_arg)
            m_text, markup = await product_ui(lang, pr_id, True)

            from bot.models.market import Product
            product = await Product.get(pr_id)
            if product:
                from bot.modules.images import send_items_photo
                try:
                    await send_items_photo(chatid, product.items, m_text, reply_markup=markup, parse_mode='Markdown')
                except Exception as e:
                    log(str(e), 3)
                    await bot.send_message(chatid, m_text, reply_markup=markup)
            else:
                try:
                    await bot.send_message(chatid, m_text, reply_markup=markup,
                                           parse_mode='Markdown')
                except Exception as e:
                    log(str(e), 3)
                    await bot.send_message(chatid, m_text, reply_markup=markup)

    await bot.send_message(chatid, text, reply_markup= await m(userid, 'last_menu', lang), parse_mode='Markdown')