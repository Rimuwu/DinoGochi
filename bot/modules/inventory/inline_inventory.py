
from aiogram.fsm.state import StatesGroup, State
from bson import ObjectId

from bot.dbmanager import mongo_client, conf
from bot.const import GAME_SETTINGS as gs
from bot.exec import bot
from bot.modules.data_format import list_to_inline
from bot.modules.get_state import get_state
from bot.modules.inline import item_info_markup
from bot.modules.items.item import ItemData, ItemInBase
from aiogram.types import InlineKeyboardButton
from aiogram.utils.keyboard import InlineKeyboardBuilder

back_button, forward_button = gs['back_button'], gs['forward_button']


class InlineInventory(StatesGroup):
    Inventory = State() # Состояние открытого инвентаря
    InventoryItem = State()  # Состояние просмотра предмета в инвентаре
    InventoryCount = State()  # Состояние выбора количества предмета в инвентаре


async def inline_page_items(items_data: dict, page: int = 0, 
                            horizontal: int = 2, vertical: int = 3,
                            prefix_key: str = ''
                            ):
    """
    
        Создание страницы с предметами инвентаря.
    
    """

    page_items = list(items_data.keys())[
        page * horizontal * vertical: (page + 1) * horizontal * vertical
        ]

    max_page = len(items_data) // (horizontal * vertical)

    minus_page = page - 1 if page > 0 else max_page
    plus_page = page + 1 if page + 1 < max_page else 0

    page_data = [{} for _ in range(vertical)]

    for n, item_name in enumerate(page_items):
        page_data[n // horizontal][item_name] = f'inline_inventory {prefix_key} item {n}'

    page_data.append(
        {
            back_button: f'inline_inventory {prefix_key} swipe {minus_page}',
            forward_button: f'inline_inventory {prefix_key} swipe {plus_page}'
        }
    )

    return list_to_inline(page_data, max(3, horizontal))

async def inline_item_page(item: ItemInBase, lang: str, 
                           prefix_key: str = ''):
    """
        Создание страницы с информацией о предмете.
    """
    standart_mrk: InlineKeyboardBuilder = await item_info_markup(item, 
                                            lang, as_markup=False)

    standart_mrk.row(
        InlineKeyboardButton(
            text='Back to Inventory', 
            callback_data=f'inline_inventory {prefix_key} inv_page'
        )
    )

    return standart_mrk.as_markup()

async def inline_count_page(prefix_key: str, count_now: int, max_count: int):

    dcc_buttons = {
        '➖': f'inline_inventory {prefix_key} count {count_now - 1}',
        f'{count_now}/{max_count}': f'inline_inventory {prefix_key} col-count {count_now}',
        '➕': f'inline_inventory {prefix_key} count {count_now + 1}'
    }

    back = {
        'Back to Inventory': f'inline_inventory {prefix_key} inv_page'
    }

    return list_to_inline([dcc_buttons, back], 3)


async def inline_inventory_handler(element, transmitted_data: dict):
    """
    """

    print(element)
    

async def swipe_inl_page(chatid: int, userid: int, update_text: bool = False):
    state = await get_state(userid, chatid)

    if data := await state.get_data():
        messages_list = data['messages_list']
        items_data = data['items_data']
        custom_code  = data['custom_code']
        page = data['page']
        view = data['view']
        settings_menu = data['settings_menu']
        work_model = data['work_model']

    if settings_menu:
        text = 'standart_text for settings'
        if messages_list[0]:
            pass
            # await bot.edit_message_text(chatid, messages_list[0], text,
            #                     reply_markup=None
            #                     )
        else:
            m1 = await bot.send_message(chatid, text,
                                reply_markup=None
                                )
            messages_list[0] = m1.message_id

    # if work_model != 'item-info':

    page_inl = await inline_page_items(items_data, page, 
                                       **view,
                            prefix_key=custom_code)

    text2 = f'standart_text for info {page} / {len(items_data)//(view["vertical"] * view["horizontal"])}'
    if messages_list[1]:
        if update_text:
            await bot.edit_message_text(text2, None, chatid, 
                                        messages_list[1], text2,
                                reply_markup=page_inl
                                )
        else:
            await bot.edit_message_reply_markup(None, chatid, 
                                                messages_list[1],
                                                reply_markup=page_inl
                                                )
    else:
        m2 = await bot.send_message(chatid, text2,
                                reply_markup=page_inl
                                )
        messages_list[1] = m2.message_id

    await state.update_data(
        messages_list=messages_list
    )