

from asyncio import sleep
import time
from typing import Optional
from bot.exec import bot
from bot.dbmanager import mongo_client
from bot.modules.localization import t
from bot.modules.overwriting.DataCalsses import DBconstructor
from bot.modules.data_format import list_to_inline, seconds_to_str

groups = DBconstructor(mongo_client.group.groups)
messages = DBconstructor(mongo_client.group.messages)
users = DBconstructor(mongo_client.group.users)
bot_users = DBconstructor(mongo_client.user.users)

async def get_group(group_id: int) -> Optional[dict]:
    res = await groups.find_one({"group_id": group_id}, comment='get_group')
    if res: return res
    else: return None

async def get_group_by_chat(chat_id: int) -> Optional[dict]:
    res = await groups.find_one({"group_id": chat_id}, comment='get_group_by_chat')
    if res: return res
    else: return None

async def insert_group(group_id: int):

    data = {
        "group_id": group_id,
        "topic_link": 0, # 0 = не привязан к топику, 0000101010101 = привязан к топику с этим id
        "topic_incorrect_message": True, # True = сообщение о неправильном топике
        "delete_message": 0, # 0 = не удалять сообщения, 20-120 = через сколько удалять сообщение
    }

    res = await groups.find_one({"group_id": group_id})
    if not res:
        await groups.insert_one(data, comment='insert_group')
        return True
    else:
        return False

async def delete_group(group_id: int):

    await groups.delete_one({"group_id": group_id}, comment='delete_group')
    await messages.delete_many({"group_id": group_id}, comment='delete_group')
    await users.delete_many({"group_id": group_id}, comment='delete_group')

async def add_message(group_id: int, message_id: int):

    group = await get_group(group_id)
    if group:
        if group['delete_message'] == 0: return True
        else:
            data = {
                "group_id": group_id,
                "message_id": message_id,
                "time_sended": int(time.time()), # Время отправки сообщения
            }

            res = await messages.find_one({"group_id": group_id, "message_id": message_id})
            if not res:
                await messages.insert_one(data, comment='add_message')
                return True

    return False

async def delete_message(group_id: int, message_id: int):
    try:
        await bot.delete_message(group_id, message_id)
    except Exception as e: pass
    await messages.delete_one({"group_id": group_id, 
            "message_id": message_id}, comment='delete_message')

async def delete_messages(group_id: int, ignore_time: bool):
    group = await get_group(group_id)
    if group:
        me = await bot.me()
        try:
            me_in_chat = await bot.get_chat_member(group_id, me.id)
        except Exception as e:
            me_in_chat = None
        if not me_in_chat: return

        if not me_in_chat.can_delete_messages:
            await groups.update_one({"group_id": group_id},
                {"$set": {"delete_message": 0}}, 
                comment='delete_messages')
            return 

        if me_in_chat.can_delete_messages:
            cursor = await messages.find({"group_id": group_id}, 
                                        comment='delete_messages')
            for message in cursor:
                if ignore_time or (message['time_sended'] + group['delete_message'] * 60 < int(time.time())):
                    await sleep(0.5)
                    await delete_message(group_id, message['message_id'])

async def group_user(group_id: int, user_id: int):
    user = await bot_users.find_one({"userid": user_id}, comment='group_user')
    if not user: return None

    res = await users.find_one({"group_id": group_id, 
                                "user_id": user_id}, comment='group_user')
    if res: return res
    else: return None

async def add_group_user(group_id: int, user_id: int):

    data = {
        "group_id": group_id,
        "user_id": user_id,
        "games_count": 0, # Количество сыгранных игр
    }

    res = await users.find_one({"group_id": group_id, "user_id": user_id})
    if not res:
        await users.insert_one(data, comment='add_group_user')
        return True
    else:
        return False

async def delete_group_user(group_id: int, user_id: int):
    await users.delete_one({"group_id": group_id, 
            "user_id": user_id}, comment='delete_group_user')

async def group_info(group_id: int, lang: str):
    res = await groups.find_one({"group_id": group_id}, comment='group_info')

    if res:
        if res['topic_link'] == 0:
            topic_link = '`' + t('groups_setting.all_topics', lang) + '`'
        else:
            topic_link = f"[{t('groups_setting.one_topic', lang)} (id{res['topic_link']})](https://t.me/c/{str(group_id)[4:]}/{res['topic_link']})"

        if res['topic_incorrect_message']:
            topic_incorrect_message = '✅'
        else:
            topic_incorrect_message = '❌'

        if res['delete_message'] == 0:
            delete_message = t('groups_setting.none_delete', lang)
        else:
            delete_message = t('groups_setting.true_delete', lang, 
                               time=seconds_to_str(res['delete_message']*60, lang, False, 'minute'))

        count = await users.count_documents({"group_id": group_id}, comment='group_info_count')

        text = t('groups_setting.main_message', lang,
                 topic_status=topic_link,
                 mess_status=topic_incorrect_message,
                 delete_status=delete_message,
                 count=count,
                 com1='/setdeletetime',
                )
        
        buttons = []
        if res['topic_link'] == 0:
            buttons.append(
                {
                    t('groups_setting.buttons.topic', lang): f'groups_setting set_topic'
                }
            )
        else:
            buttons.append(
                {
                    t('groups_setting.buttons.delete_topic', lang): f'groups_setting null_topic_main'
                }
            )

        if res['topic_incorrect_message']:
            buttons.append(
                {
                    t('groups_setting.buttons.mess', lang): f'groups_setting no_message'
                }
            )
        else:
            buttons.append(
                {
                    t('groups_setting.buttons.no_mess', lang): f'groups_setting message'
                }
            )

        if res['delete_message'] != 0:
            buttons.append(
                {
                    t('groups_setting.buttons.delete', lang): f'groups_setting no_delete'
                }
            )

        return text, list_to_inline(buttons)
    return None, None
