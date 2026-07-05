from bot.modules.overwriting.DataCalsses import LazyCollection
from bot.models.tavern import Quest
from bot.models.user import User
from asyncio import sleep
from time import time

from bot.dbmanager import mongo_client
from bot.exec import main_router, bot
from bot.modules.data_format import list_to_inline
from bot.modules.decorators import HDCallback, HDMessage
from bot.modules.items.item import AddItemToUser
from bot.modules.localization import get_data, get_lang, t
from bot.modules.quests import check_quest, quest_resampling, quest_ui
from aiogram.types import (CallbackQuery,
                           InlineKeyboardMarkup, Message)

from bot.filters.translated_text import StartWith, Text
from bot.filters.states import NothingState
from bot.filters.status import DinoPassStatus
from bot.filters.private import IsPrivateChat
from bot.filters.authorized import IsAuthorizedUser
from bot.filters.kd import KDCheck
from bot.filters.admin import IsAdminUser
from aiogram import F
from aiogram.filters import Command, StateFilter

from aiogram.fsm.context import FSMContext

quests_data = LazyCollection(Quest)

@HDMessage
@main_router.message(IsPrivateChat(), Text('commands_name.dino_tavern.quests'), IsAuthorizedUser())
async def check_quests(message: Message):
    userid = message.from_user.id
    lang = await get_lang(message.from_user.id)
    chatid = message.chat.id

    user = await User.find_one(User.userid == userid)
    if user:
        quests = await quests_data.find({'owner_id': userid}, comment='check_quests_quests')

        text = t('quest.quest_menu', lang, 
                end=user.dungeon.get('quest_ended', 0), act=len(quests))
        await bot.send_message(chatid, text)

        for quest in quests:
            text, mark = quest_ui(quest, lang, quest['alt_id'])
            await bot.send_message(
                            chatid, text, reply_markup=mark, parse_mode='Markdown')
            await sleep(0.3)

@HDCallback
@main_router.callback_query(IsPrivateChat(), F.data.startswith('quest'))
async def quest(call: CallbackQuery):
    chatid = call.message.chat.id
    userid = call.from_user.id
    lang = await get_lang(call.from_user.id)
    message = call.message

    data = call.data.split()
    alt_id = data[2]

    quest = await quests_data.find_one({'alt_id': alt_id, 'owner_id': userid}, comment='quest_quest')
    if quest:
        if int(time()) > quest['time_end']:
            await quest_resampling(quest['_id'])

            text = t('quest.time_end_h', lang)
            await bot.send_message(chatid, text)
            await bot.edit_message_reply_markup(None, chatid, message.message_id, 
                                   reply_markup=InlineKeyboardMarkup(inline_keyboard=[]))
        else:
            if data[1] == 'delete':
                await quest_resampling(quest['_id'])

                text = t('quest.delete_button', lang)
                mark = list_to_inline([{text: ' '}])
                await bot.edit_message_reply_markup(None, chatid, message.message_id, 
                                    reply_markup=mark)
            elif data[1] == 'end':
                result = await check_quest(quest)

                if result:
                    text = t('quest.end_quest', lang, author_name=quest['author'], name=quest['name'])

                    b_name = t('quest.end_quest_button', lang)
                    mark = list_to_inline([{b_name: ' '}])

                    await bot.edit_message_reply_markup(None, chatid, message.message_id, reply_markup=mark)

                    from bot.modules.overwriting.DataCalsses import Transaction
                    async with Transaction():
                        user = await User.find_one(User.userid == userid)
                        if user:
                            await user.add_coins(quest['reward']['coins'])
                            await user.inc_quests_ended()
                            for i in quest['reward']['items']: 
                                await user.add_item(i)

                        await quests_data.delete_one({'_id': quest['_id']}, comment='quest_2')

                else: text = t('quest.conditions', lang)

                await bot.send_message(chatid, text, parse_mode='Markdown')
    else:
        text = t('quest.not_found', lang)
        await bot.send_message(chatid, text)
        await bot.edit_message_reply_markup(None, chatid, message.message_id, 
                                   reply_markup=InlineKeyboardMarkup(inline_keyboard=[]))