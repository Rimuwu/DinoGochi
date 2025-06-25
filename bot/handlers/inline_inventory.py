from bot.exec import main_router, bot
from bot.filters.authorized import IsAuthorizedUser
from bot.filters.private import IsPrivateChat
from bot.modules.decorators import HDCallback, HDMessage
from bot.modules.get_state import get_state
from bot.modules.inventory.inline_inventory import InlineInventory, swipe_inl_page
from aiogram.filters import StateFilter
from aiogram.types import CallbackQuery, Message
from aiogram import F


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

    if call_data[1] != custom_code:
        await call.answer('This page is outdated, please try again.', show_alert=True)
        return

    if call_data[2] == 'swipe':
        page = int(call_data[3])
        await state.update_data(
            page=page
            )

        await swipe_inl_page(chatid, userid)