from bson import ObjectId
from bot.exec import main_router, bot
from bot.filters.authorized import IsAuthorizedUser
from bot.filters.private import IsPrivateChat
from bot.modules.decorators import HDCallback, HDMessage
from bot.modules.get_state import get_state
from bot.modules.inventory.inline_inventory import InlineInventory, inline_count_page, inline_item_page, swipe_inl_page
from aiogram.filters import StateFilter
from aiogram.types import CallbackQuery, Message
from aiogram import F

from bot.modules.items.item import ItemData, ItemInBase, decode_item, item_info


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
        location_type = data['location']['type']
        location_link = data['location']['link']
        lang = data['lang']
        messages_list = data['messages_list']
        inventory_return = data['inventory_return']

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
        text_id = messages_list[1]

        if isinstance(item_data, dict):
            # {'item_id': str, 'abilities': dict}
            item = ItemInBase(
                owner_id=userid,
                item_id=item_data['item_id'],
                abilities=item_data['abilities'],
                location_type=location_type,
                location_link=location_link
            )

            if data['real_items']:
                await item.link_yourself()
            else:
                item.count = data['max_data_count']

        elif isinstance(item_data, ObjectId):
            item = await ItemInBase().link_for_id(item_data)

        if work_model == 'item-info':
            text, image = await item_info(item, lang)

            await bot.edit_message_text(
                parse_mode='Markdown',
                text=text, 
                chat_id=chatid, 
                message_id=text_id,
                reply_markup=await inline_item_page(item, lang, custom_code)
            )

        elif work_model == 'item-count':
            text, image = await item_info(item, lang)
            item_code = item.code()

            count_now = 0
            for dct in inventory_return:
                if dct.keys() == {item_code}:
                    count_now = dct[item_code]
                    break

            await state.update_data(
                activ_item=item_code,
            )
 
            inl = await inline_count_page(
                custom_code, count_now, item.count)

            await bot.edit_message_text(
                parse_mode='Markdown',
                text=text, 
                chat_id=chatid, 
                message_id=text_id,
                reply_markup=inl
            )

        elif work_model == 'item':
            ...

        elif work_model == 'item-count':
            ...

    elif call_data[2] in ['count', 'col-count']:
        item_code = data['activ_item']

        item_d = await decode_item(item_code)
        if isinstance(item_d, ItemData):

            item = ItemInBase(
                owner_id=userid,
                item_id=item_d.item_id,
                abilities=item_d.abilities,
                location_type=location_type,
                location_link=location_link
            )

            if data['real_items']:
                await item.link_yourself()
            else:
                item.count = data['max_data_count']

        else:
            item = item_d

        count_now = 0
        ind = -1
        for i, dct in enumerate(inventory_return):
            if dct.keys() == {item_code}:
                count_now = dct[item_code]
                ind = i
                break

        new_count = int(call_data[3])
        if new_count < 0: new_count = 0
        elif new_count > item.count:
            new_count = item.count
        
        if call_data[2] == 'col-count':
            if count_now == item.count:
                new_count = 0
            elif count_now == 0:
                new_count = item.count
            else:
                new_count = 0

        if ind == -1:
            inventory_return.append(
                {item_code: new_count}
            )
        else:
            inventory_return[ind][item_code] = new_count
        
        if new_count == 0: inventory_return.pop(ind)

        await state.update_data(
            inventory_return=inventory_return,
        )

        if new_count == count_now:
            await call.answer('Count is already set to this value.')
            return

        inl = await inline_count_page(
                custom_code, new_count, item.count)

        await call.message.edit_reply_markup(reply_markup=inl)