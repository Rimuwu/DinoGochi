from bson import ObjectId
from bot.exec import main_router, bot
from bot.filters.authorized import IsAuthorizedUser
from bot.filters.private import IsPrivateChat
from bot.modules.decorators import HDCallback, HDMessage
from bot.modules.get_state import get_state
from bot.modules.inventory.inline_inventory import InlineInventory, inline_item_page, swipe_inl_page
from aiogram.filters import StateFilter
from aiogram.types import CallbackQuery, Message
from aiogram import F

from bot.modules.items.item import ItemInBase, item_info


@HDCallback
@main_router.callback_query(
    IsPrivateChat(), 
    StateFilter(InlineInventory.Inventory), 
    F.data.startswith('inline_inventory'))
async def inv_callback(call: CallbackQuery):
    call_data = call.data.split()
    chatid = call.message.chat.id
    userid = call.from_user.id

    state = await get_state(userid, chatid)
    if data := await state.get_data():
        items_data = data['items_data']
        work_model = data['work_model']
        page = data['page']
        custom_code = data['custom_code']
        view = data['view']
        userid = data['userid']
        location_type = data['location_type']
        location_link = data['location_link']
        lang = data['lang']
        messages_list = data['messages_list']

    if call_data[1] != custom_code:
        await call.answer('This page is outdated, please try again.', show_alert=True)
        return

    if call_data[2] == 'swipe':
        page = int(call_data[3])
        await state.update_data(
            page=page
            )

        await swipe_inl_page(chatid, userid)

    elif call_data[2] == 'inv_page':
        await swipe_inl_page(chatid, userid, True)

    elif call_data[2] == 'item':
        item_page_n = int(call_data[3])
        items_per_page = view['horizontal'] * view['vertical']
        item_data = items_data[list(items_data.keys())[
            page * items_per_page + item_page_n
            ]
        ]

        if isinstance(item_data, dict):
            # {'item_id': str, 'abilities': dict}
            item = await ItemInBase().link(
                owner_id=userid,
                item_id=item_data['item_id'],
                abilities=item_data['abilities'],
                location_type=location_type,
                location_link=location_link
            )

        elif isinstance(item_data, ObjectId):
            item = await ItemInBase().link_for_id(item_data)

        if work_model == 'item-info':
            text, image = await item_info(item, lang)
            text_id = messages_list[1]
            await bot.edit_message_text(
                parse_mode='Markdown',
                text=text, 
                chat_id=chatid, 
                message_id=text_id,
                reply_markup=await inline_item_page(item, lang, custom_code)
            )

        elif work_model == 'item-count':
            ...

        elif work_model == 'items':
            ...
        
        elif work_model == 'items-count':
            ...

        elif work_model == 'items-count':
            ...

