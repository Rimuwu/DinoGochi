from typing import Optional
from bot.models.group import Group, GroupMessage, GroupUser

async def get_group(group_id: int) -> Optional[dict]:
    return await Group.get_group(group_id)

async def get_group_by_chat(chat_id: int) -> Optional[dict]:
    return await Group.get_group_by_chat(chat_id)

async def insert_group(group_id: int) -> bool:
    return await Group.insert_group(group_id)

async def delete_group(group_id: int):
    await Group.delete_group(group_id)

async def add_message(group_id: int, message_id: int) -> bool:
    return await GroupMessage.add_message(group_id, message_id)

async def delete_message(group_id: int, message_id: int):
    await GroupMessage.delete_message(group_id, message_id)

async def delete_messages(group_id: int, ignore_time: bool):
    await Group.delete_messages(group_id, ignore_time)

async def group_user(group_id: int, user_id: int) -> Optional[dict]:
    return await GroupUser.group_user(group_id, user_id)

async def add_group_user(group_id: int, user_id: int) -> bool:
    return await GroupUser.add_group_user(group_id, user_id)

async def delete_group_user(group_id: int, user_id: int):
    await GroupUser.delete_group_user(group_id, user_id)

async def group_info(group_id: int, lang: str):
    return await Group.group_info(group_id, lang)
