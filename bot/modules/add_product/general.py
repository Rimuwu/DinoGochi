from bot.modules.data_format import item_list
from bot.modules.items.item import CheckCountItemFromUser, RemoveItemFromUser
from bot.modules.localization import t
from bot.exec import bot
from bot.modules.market.market import add_product, product_ui
 
from bot.modules.states_tools import ChooseStepState
from bot.modules.user.user import take_coins
from bot.modules.markup import cancel_markup, markups_menu as m

MAX_PRICE = 10_000_000

async def coins_stock(return_data, transmitted_data):
    """ Функция для запроса цены и запаса 
    """
    chatid = transmitted_data['chatid']
    userid = transmitted_data['userid']
    lang = transmitted_data['lang']
    option = transmitted_data['option']

    if type(return_data['items']) != list:
        return_data['items'] = [return_data['items']]
        return_data['col'] = [return_data['col']]

    steps = [
        {
            "type": 'int', "name": 'price', "data": {"max_int": MAX_PRICE},
            "translate_message": True,
            'message': {'text': f'add_product.coins.{option}', 
                        'reply_markup': cancel_markup(lang)}
        },
        {
            "type": 'int', "name": 'in_stock', "data": {"max_int": 100},
            "translate_message": True,
            'message': {'text': f'add_product.stock.{option}', 
                        'reply_markup': cancel_markup(lang)}
        }
    ]

    transmitted_data = {
        'items': return_data['items'],
        'col': return_data['col'],
        'option': transmitted_data['option']
    }

    await ChooseStepState(end, userid, chatid, 
                          lang, steps, 
                          transmitted_data=transmitted_data)

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

    if option == 'coins_items':  
        # Проверить количество монет 
        res = await take_coins(userid, -price*in_stock, True)
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

                await RemoveItemFromUser(userid, item_id, count * in_stock, abil)

    if option == 'auction':
        add_arg['min_add'] = return_data['min_add']
        add_arg['end'] = return_data['time_end']

    elif option == 'items_items':
        price = item_list(price)

    if product_status:
        pr_id = await add_product(userid, option, items, 
                                  price, in_stock, add_arg)
        m_text, markup = await product_ui(lang, pr_id, True)

        try:
            await bot.send_message(chatid, m_text, reply_markup=markup,
                                   parse_mode='Markdown')
        except Exception as e:
            print(e)
            await bot.send_message(chatid, m_text, reply_markup=markup)

    await bot.send_message(chatid, text, reply_markup= await m(userid, 'last_menu', lang), parse_mode='Markdown')