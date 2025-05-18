from bot.config import conf

from aiogram import Bot, Dispatcher
from bot.const import GAME_SETTINGS
from bot.dbmanager import mongo_client
from bot.exec import main_router, bot
from bot.modules.data_format import list_to_inline
from bot.modules.groups import add_group_user, delete_group, delete_group_user, insert_group
from bot.modules.localization import get_lang, t
from bot.modules.logs import log
from bot.modules.managment.boost_spy import create_boost, delete_boost
from bot.modules.overwriting.DataCalsses import DBconstructor
from bot.modules.user.user import user_in_chat
from aiogram.types import ChatMemberUpdated, Message, ChatBoostUpdated, ChatBoostRemoved, ChatBoostSourcePremium
from aiogram.filters.chat_member_updated import \
    ChatMemberUpdatedFilter, MEMBER, KICKED, LEFT, ADMINISTRATOR, CREATOR, IS_NOT_MEMBER, IS_MEMBER

from bot.tasks.bot_report import create_report
from aiogram import F

puhs = DBconstructor(mongo_client.market.puhs)

@main_router.my_chat_member()
async def my_update(data: ChatMemberUpdated):
    lang = await get_lang(data.from_user.id)
    userid = data.from_user.id

    if data.chat.type in ['group', 'supergroup']:
        # Настройка группы для игр
        if data.new_chat_member.status in ['left', 'kicked'] and \
            data.old_chat_member.status in ['member', 'administrator']:

            await delete_group(data.chat.id)

        else:
           await insert_group(data.chat.id)

    elif data.chat.type == 'channel': 
        # Настройки уведомления о товарах
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

@main_router.chat_member(ChatMemberUpdatedFilter(IS_MEMBER >> IS_NOT_MEMBER))
async def on_user_leave(event: ChatMemberUpdated): 

    if event.chat.type in ['group', 'supergroup']:
        if event.new_chat_member.user.is_bot or \
            event.new_chat_member.user.id == bot.id:
                return

        await delete_group_user(event.chat.id, event.new_chat_member.user.id)

@main_router.chat_member(ChatMemberUpdatedFilter(IS_NOT_MEMBER >> IS_MEMBER))
async def on_user_join(event: ChatMemberUpdated): 

    if event.chat.type in ['group', 'supergroup']:
        if event.new_chat_member.user.is_bot or \
            event.new_chat_member.user.id == bot.id:
                return

        await add_group_user(event.chat.id, event.new_chat_member.user.id)

@main_router.shutdown()
async def bot_stop(bot: Bot, dispatcher: Dispatcher, bots: tuple[Bot], router):
    report_id = conf.bot_report_id
    channel_id, topic_id = report_id.split('_', 1)

    text = f'🔴 Бот остановлен...'
    await bot.send_message(channel_id, text,
                     message_thread_id=int(topic_id)
    )
    await create_report()

@main_router.chat_boost(
    F.chat.id == GAME_SETTINGS['channel_id'])
async def on_chat_boost(event: ChatBoostUpdated, bot: Bot):
    expiration_timestamp = int(event.boost.expiration_date.timestamp())

    if isinstance(event.boost.source, ChatBoostSourcePremium):
        user = event.boost.source.user
        if user:
            await create_boost(user.id, expiration_timestamp)

@main_router.removed_chat_boost(
    F.chat.id == GAME_SETTINGS['channel_id'])
async def on_removed_chat_boost(event: ChatBoostRemoved, bot: Bot):
    user = event.source.user
    if user:
        await delete_boost(user.id)
