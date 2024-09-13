from bot.dbmanager import mongo_client
from bot.exec import bot
from bot.modules.data_format import list_to_inline
from bot.modules.localization import get_lang, t
from bot.modules.overwriting.DataCalsses import DBconstructor
from bot.modules.user.user import user_in_chat
from telebot.types import ChatMemberUpdated

puhs = DBconstructor(mongo_client.market.puhs)

@bot.my_chat_member_handler(pass_bot=True)
async def my_update(data: ChatMemberUpdated):
    lang = await get_lang(data.from_user.id)
    userid = data.from_user.id

    if data.new_chat_member.status == 'administrator':
        status = await user_in_chat(userid, data.chat.id)
        can_manage_chat = data.new_chat_member.can_manage_chat
        res = await puhs.find_one({'owner_id': userid}, comment='my_update')
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
        res = await puhs.find_one({'owner_id': userid}, comment='my_update')
        if res: await puhs.delete_one({'owner_id': userid}, comment='my_update')
