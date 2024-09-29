from asyncio import sleep
from time import time

from bot.dbmanager import mongo_client
from bot.exec import bot
from bot.modules.data_format import list_to_inline
from bot.modules.decorators import HDCallback, HDMessage
from bot.modules.items.item import AddItemToUser
from bot.modules.localization import get_data, get_lang, t
from bot.modules.overwriting.DataCalsses import DBconstructor
from bot.modules.quests import check_quest, quest_resampling, quest_ui
from bot.modules.user.user import take_coins
from aiogram.types import (CallbackQuery,
                           InlineKeyboardMarkup, Message)

quests_data = DBconstructor(mongo_client.tavern.quests)
users = DBconstructor(mongo_client.user.users)

@bot.message(text='commands_name.dino_tavern.quests', is_authorized=True, private=True)
@HDMessage
async def check_quests(message: Message):
    userid = message.from_user.id
    lang = await get_lang(message.from_user.id)
    chatid = message.chat.id

    user = await users.find_one({'userid': userid}, comment='check_quests_user')
    if user:
        quests = await quests_data.find({'owner_id': userid}, comment='check_quests_quests')

        text = t('quest.quest_menu', lang, 
                end=user['dungeon']['quest_ended'], act=len(quests))
        await bot.send_message(chatid, text)

        for quest in quests:
            text, mark = quest_ui(quest, lang, quest['alt_id'])
            await bot.send_message(
                            chatid, text, reply_markup=mark, parse_mode='Markdown')
            await sleep(0.3)

@bot.callback_query_handler(func=lambda call: 
    call.data.startswith('quest'), private=True)
@HDCallback
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
            await bot.edit_message_reply_markup(chatid, message.id, 
                                   reply_markup=InlineKeyboardMarkup())
        else:
            if data[1] == 'delete':
                await quest_resampling(quest['_id'])

                text = t('quest.delete_button', lang)
                mark = list_to_inline([{text: ' '}])
                await bot.edit_message_reply_markup(chatid, message.id, 
                                    reply_markup=mark)
            elif data[1] == 'end':
                result = await check_quest(quest)

                if result:
                    text = t('quest.end_quest', lang, author_name=quest['author'], name=quest['name'])

                    b_name = t('quest.end_quest_button', lang)
                    mark = list_to_inline([{b_name: ' '}])

                    await bot.edit_message_reply_markup(chatid, message.id, reply_markup=mark)

                    await take_coins(userid, quest['reward']['coins'], True)
                    for i in quest['reward']['items']: 
                        await AddItemToUser(userid, i)

                    await quests_data.delete_one({'_id': quest['_id']}, comment='quest_2')
                    await users.update_one({'userid': userid}, {'$inc': {'dungeon.quest_ended': 1}}, comment='quest_end')

                else: text = t('quest.conditions', lang)

                await bot.send_message(chatid, text, parse_mode='Markdown')
    else:
        text = t('quest.not_found', lang)
        await bot.send_message(chatid, text)
        await bot.edit_message_reply_markup(chatid, message.id, 
                                   reply_markup=InlineKeyboardMarkup())