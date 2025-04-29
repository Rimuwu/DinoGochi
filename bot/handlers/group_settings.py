
from curses.ascii import isdigit
from bot.dbmanager import mongo_client
from bot.exec import main_router, bot
from bot.modules.decorators import HDCallback, HDMessage
from bot.modules.groups import add_message, delete_messages, get_group, get_group_by_chat, group_info, insert_group
from bot.modules.localization import get_lang, t
from bot.modules.overwriting.DataCalsses import DBconstructor
from aiogram.types import CallbackQuery, Message

from aiogram import F
from aiogram.filters import Command

from bot.filters.group_filter import GroupRules
from bot.filters.group_admin import IsGroupAdmin
from bot.filters.private import IsPrivateChat

users = DBconstructor(mongo_client.user.users)
groups = DBconstructor(mongo_client.group.groups)
messages = DBconstructor(mongo_client.group.messages)

@main_router.callback_query(IsPrivateChat(False), IsGroupAdmin(True), 
                            F.data.startswith('groups_setting'))
@HDCallback
async def groups_setting_calb(call: CallbackQuery):
    call_data = call.data.split()
    chatid = call.message.chat.id
    userid = call.from_user.id
    lang = await get_lang(userid)

    group = await get_group_by_chat(chatid)
    if group:

        if call_data[1] in ['null_topic', 'null_topic_main']:

            if group['topic_link'] != 0:
                await groups.update_one({"group_id": chatid}, 
                                        {"$set": {"topic_link": 0}}, 
                                        comment='groups_setting null_topic')
                await call.answer(t('groups_setting.null_topic', 
                                    await get_lang(userid)), show_alert=True)

            if call_data[1] == 'null_topic_main':

                text, reply = await group_info(chatid, lang)
                await call.message.edit_text(text, 
                            parse_mode='Markdown', reply_markup=reply)

        elif call_data[1] == 'set_topic':
            if group['topic_link'] == 0 and call.message.message_thread_id:
                await groups.update_one({"group_id": chatid}, 
                                        {"$set": 
                                            {"topic_link": 
                                                call.message.message_thread_id}}, 
                                        comment='groups_setting set_topic')
                await call.answer(t('groups_setting.set_topic', 
                                    await get_lang(userid)), show_alert=True)

            text, reply = await group_info(chatid, lang)
            await call.message.edit_text(text, 
                            parse_mode='Markdown', reply_markup=reply)
        
        elif call_data[1] == 'no_message':
            if group['topic_incorrect_message']:
                await groups.update_one({"group_id": chatid}, 
                                        {"$set": 
                                            {"topic_incorrect_message": 
                                                False}}, 
                                        comment='groups_setting no_message')
                await call.answer(t('groups_setting.no_message', 
                                    await get_lang(userid)), show_alert=True)

            text, reply = await group_info(chatid, lang)
            await call.message.edit_text(text, 
                            parse_mode='Markdown', reply_markup=reply)

        elif call_data[1] == 'message':
            if not group['topic_incorrect_message']:
                await groups.update_one({"group_id": chatid}, 
                                        {"$set": 
                                            {"topic_incorrect_message": 
                                                True}}, 
                                        comment='groups_setting message')
                await call.answer(t('groups_setting.message', 
                                    await get_lang(userid)), show_alert=True)

            text, reply = await group_info(chatid, lang)
            await call.message.edit_text(text, 
                            parse_mode='Markdown', reply_markup=reply)

        elif call_data[1] == 'no_delete':
            if group['delete_message'] != 0:
                await groups.update_one({"group_id": chatid}, 
                                        {"$set": 
                                            {"delete_message": 0}}, 
                                        comment='groups_setting no_delete')
                await call.answer(t('groups_setting.no_delete', 
                                    await get_lang(userid)), show_alert=True)
                await messages.delete_many({"group_id": chatid},
                                           comment='delete_message no_delete')

            text, reply = await group_info(chatid, lang)
            await call.message.edit_text(text, 
                            parse_mode='Markdown', reply_markup=reply)


@main_router.message(Command('group_settings'),
                     GroupRules(True))
async def group_settings_commands(message: Message):
    chatid = message.chat.id
    userid = message.from_user.id
    lang = await get_lang(userid)

    text, reply = await group_info(chatid, lang)
    mes = await message.answer(text, parse_mode='Markdown', reply_markup=reply)
    await add_message(chatid, mes.message_id)

@main_router.message(Command(commands=['setdeletetime']),
                     GroupRules(True), IsGroupAdmin(True))
async def set_delete_time(message: Message):
    chatid = message.chat.id
    userid = message.from_user.id
    data = str(message.text).split()
    no_arg = len(data) == 1

    lang = await get_lang(userid)
    group = await get_group(chatid)
    if group:
        me = await bot.me()
        try:
            me_in_chat = await bot.get_chat_member(chatid, 
                                                   me.id)
        except Exception as e:
            me_in_chat = None
        if not me_in_chat: return

        if not me_in_chat.can_delete_messages:
            mes = await message.answer(t('no_delete_rights', lang), parse_mode='Markdown')
            await add_message(chatid, mes.message_id)

        elif no_arg:
            await groups.update_one({"group_id": chatid},
                                    {"$set": {"delete_message": 0}}, 
                                    comment='set_delete_time')
        else:
            num = data[1]
            if num.isdigit():

                if int(num) >= 0 and int(num) < 240:
                    await groups.update_one({"group_id": chatid},
                                        {"$set": {"delete_message": int(num)}}, 
                                        comment='set_delete_time')
                    mes = await message.answer(
                        t('groups_setting.delete_time_set', lang, time=num))
                else:
                    mes = await message.answer(t('groups_setting.invalid_time', lang))
            else:
                mes = await message.answer(t('groups_setting.invalid_time', lang))
            await add_message(chatid, mes.message_id)

    await add_message(chatid, message.message_id)
