from bot.models.tavern import Quest
from bot.models.user import User
from asyncio import sleep
from time import time

from bot.exec import main_router, bot
from bot.modules.data_format import list_to_inline
from bot.modules.localization import get_lang, t
from bot.modules.quests import check_quest, quest_resampling, quest_ui
from aiogram.types import (CallbackQuery,
                           InlineKeyboardMarkup, Message)

from bot.filters.translated_text import Text
from bot.filters.private import IsPrivateChat
from bot.filters.authorized import IsAuthorizedUser
from aiogram import F

@main_router.message(IsPrivateChat(), Text('commands_name.dino_tavern.quests'), IsAuthorizedUser())
async def check_quests(message: Message):
    userid = message.from_user.id
    lang = await get_lang(message.from_user.id)
    chatid = message.chat.id

    user = await User.find_one(User.userid == userid)
    if user:
        quests = await Quest.find(Quest.owner_id == userid).to_list()

        text = t('quest.quest_menu', lang, 
                end=user.dungeon.get('quest_ended', 0), act=len(quests))
        await bot.send_message(chatid, text)

        for quest in quests:
            q_dict = quest.dict()
            text, mark = quest_ui(q_dict, lang, q_dict['alt_id'])
            await bot.send_message(
                            chatid, text, reply_markup=mark, parse_mode='Markdown')
            await sleep(0.3)

@main_router.callback_query(IsPrivateChat(), F.data.startswith('quest'))
async def quest(call: CallbackQuery):
    chatid = call.message.chat.id
    userid = call.from_user.id
    lang = await get_lang(call.from_user.id)
    message = call.message

    data = call.data.split()
    alt_id = data[2]

    quest = await Quest.find_one(Quest.owner_id == userid, Quest.alt_id == alt_id)

    if not quest:
        text = t('quest.not_found', lang)
        await bot.send_message(chatid, text)
        await bot.edit_message_reply_markup(None, chatid, message.message_id, 
                                   reply_markup=InlineKeyboardMarkup(inline_keyboard=[]))
        return 

    q_dict = quest.dict()
    if int(time()) > q_dict['time_end']:
        await quest_resampling(quest.id)

        text = t('quest.time_end_h', lang)
        await bot.send_message(chatid, text)
        await bot.edit_message_reply_markup(None, chatid, message.message_id, 
                                reply_markup=InlineKeyboardMarkup(inline_keyboard=[]))
    else:
        if data[1] == 'delete':
            await quest_resampling(quest.id)

            text = t('quest.delete_button', lang)
            mark = list_to_inline([{text: ' '}])
            await bot.edit_message_reply_markup(None, chatid, message.message_id, 
                                reply_markup=mark)
        elif data[1] == 'end':
            result = await check_quest(q_dict)

            if result:
                text = t('quest.end_quest', lang, author_name=q_dict['author'], name=q_dict['name'])

                b_name = t('quest.end_quest_button', lang)
                mark = list_to_inline([{b_name: ' '}])

                await bot.edit_message_reply_markup(None, chatid, message.message_id, reply_markup=mark)

                from bot.modules.overwriting.DataCalsses import Transaction
                async with Transaction():
                    user = await User.find_one(User.userid == userid)
                    if user:
                        await user.add_coins(q_dict['reward']['coins'])
                        await user.inc_quests_ended()
                        for i in q_dict['reward']['items']: 
                            await user.add_item(i)

                    await quest.delete()

            else: text = t('quest.conditions', lang)

            await bot.send_message(chatid, text, parse_mode='Markdown')
