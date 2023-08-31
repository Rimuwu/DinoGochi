from telebot.types import (CallbackQuery, InlineKeyboardButton,
                           InlineKeyboardMarkup, Message, InputMedia, ChatMemberUpdated)

from bot.config import mongo_client
from bot.exec import bot
from bot.modules.localization import get_data, t, get_lang
from bot.modules.currency import get_all_currency, get_products
from bot.modules.item import counts_items
from bot.modules.data_format import seconds_to_str, list_to_inline
from bot.modules.user import user_in_chat

users = mongo_client.user.users
puhs = mongo_client.market.puhs

@bot.my_chat_member_handler()
async def my_update(data: ChatMemberUpdated):
    lang = get_lang(data.from_user.id)
    userid = data.from_user.id

    if data.new_chat_member.status == 'administrator':
        status = await user_in_chat(userid, data.chat.id)
        can_manage_chat = data.new_chat_member.can_manage_chat
        res = puhs.find_one({'owner_id': userid})
        if not res:
            if status not in ['creator', 'administrator']:
                text = t('push.not_admin', lang)
                await bot.send_message(userid, text)
                return

            elif not can_manage_chat:
                text = t('push.not_management', lang)
                await bot.send_message(userid, text)
                return

            else:
                text = t('push.ok', lang)
                buttons = [{t('buttons_name.confirm', lang): f'create_push {data.chat.id}'}]
                markup = list_to_inline(buttons)

                await bot.send_message(userid, text, reply_markup=markup)

    elif data.new_chat_member.status == 'left':
        res = puhs.find_one({'owner_id': userid})
        if res: puhs.delete_one({'owner_id': userid})
