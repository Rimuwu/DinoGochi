from typing import Optional, Union, Any
from beanie import Document, Link
from bot.models.base_private import PrivateModelMixin
from bot.models.user import User

class Group(PrivateModelMixin, Document):
    group_id: Optional[int] = None
    topic_link: int = 0
    topic_incorrect_message: bool = True
    delete_message: int = 0

    class Settings:
        name = "groups"

    async def set_delete_message(self, seconds: int) -> None:
        self.delete_message = seconds
        await self.save()

    async def set_topic_link(self, topic_id: int) -> None:
        self.topic_link = topic_id
        await self.save()

    async def set_topic_incorrect_message(self, status: bool) -> None:
        self.topic_incorrect_message = status
        await self.save()

    @classmethod
    async def get_group(cls, group_id: int) -> Optional[dict]:
        res = await cls.find_one(cls.group_id == group_id)
        if res: return res.dict()
        else: return None

    @classmethod
    async def get_group_by_chat(cls, chat_id: int) -> Optional[dict]:
        res = await cls.find_one(cls.group_id == chat_id)
        if res: return res.dict()
        else: return None

    @classmethod
    async def insert_group(cls, group_id: int) -> bool:
        data = {
            "group_id": group_id,
            "topic_link": 0,
            "topic_incorrect_message": True,
            "delete_message": 0,
        }
        res = await cls.find_one(cls.group_id == group_id)
        if not res:
            await cls(**data).insert()
            return True
        else:
            return False

    @classmethod
    async def delete_group(cls, group_id: int):
        group_obj = await cls.find_one(cls.group_id == group_id)
        if group_obj: await group_obj.delete()
        await GroupMessage.find(GroupMessage.group_id == group_id).delete()
        await GroupUser.find(GroupUser.group_id == group_id).delete()

    @classmethod
    async def delete_messages(cls, group_id: int, ignore_time: bool):
        from bot.exec import bot
        import time
        from asyncio import sleep
        group = await cls.get_group(group_id)
        if group:
            me = await bot.me()
            try:
                me_in_chat = await bot.get_chat_member(group_id, me.id)
            except Exception:
                me_in_chat = None
            if not me_in_chat: return

            if not me_in_chat.can_delete_messages:
                group_obj = await cls.find_one(cls.group_id == group_id)
                if group_obj:
                    group_obj.delete_message = 0
                    await group_obj.save()
                return 

            if me_in_chat.can_delete_messages:
                cursor = await GroupMessage.find(GroupMessage.group_id == group_id).to_list()
                for message_obj in cursor:
                    message = message_obj.dict()
                    if ignore_time or ( (message['time_sended'] + group['delete_message'] * 60) <= int(time.time()) ):
                        await sleep(0.5)
                        await GroupMessage.delete_message(group_id, message['message_id'])

    @classmethod
    async def group_info(cls, group_id: int, lang: str):
        from bot.modules.localization import t
        from bot.modules.data_format import list_to_inline, seconds_to_str
        res_model = await cls.find_one(cls.group_id == group_id)
        res = res_model.dict() if res_model else None

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

            count = await GroupUser.find(GroupUser.group_id == group_id).count()

            text = t('groups_setting.main_message', lang,
                     topic_status=topic_link,
                     mess_status=topic_incorrect_message,
                     delete_status=delete_message,
                     count=count,
                     com1='/setdeletetime',
                     com2='/deleteallmessages'
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


class GroupMessage(PrivateModelMixin, Document):
    group_id: Optional[int] = None
    message_id: Optional[int] = None
    user: Optional[Link[User]] = None
    timestamp: int = 0
    time_sended: int = 0

    class Settings:
        name = "messages"

    async def set_time_sended(self, timestamp: int) -> None:
        self.time_sended = timestamp
        await self.save()

    @classmethod
    async def add_message(cls, group_id: int, message_id: int) -> bool:
        import time
        group = await Group.get_group(group_id)
        if group:
            if group['delete_message'] == 0: return True
            else:
                data = {
                    "group_id": group_id,
                    "message_id": message_id,
                    "time_sended": int(time.time()),
                }

                res = await cls.find_one(cls.group_id == group_id, cls.message_id == message_id)
                if not res:
                    await cls(**data).insert()
                    return True

        return False

    @classmethod
    async def delete_message(cls, group_id: int, message_id: int):
        from bot.exec import bot
        try:
            await bot.delete_message(group_id, message_id)
        except Exception: pass
        msg_obj = await cls.find_one(cls.group_id == group_id, cls.message_id == message_id)
        if msg_obj: await msg_obj.delete()


class GroupUser(PrivateModelMixin, Document):
    userid: int = 0
    group_id: Optional[int] = None
    games_count: int = 0

    class Settings:
        name = "group_users"

    async def increment_games(self, count: int = 1) -> None:
        self.games_count += count
        await self.save()

    @classmethod
    async def group_user(cls, group_id: int, user_id: int):
        res = await cls.find_one(cls.group_id == group_id, cls.userid == user_id)
        if res: return res.dict()
        else: return None

    @classmethod
    async def add_group_user(cls, group_id: int, user_id: int) -> bool:
        res = await cls.find_one(cls.group_id == group_id, cls.userid == user_id)
        if not res:
            data = {
                "group_id": group_id,
                "userid": user_id,
                "games_count": 0,
            }
            await cls(**data).insert()
            return True
        else:
            return False

    @classmethod
    async def delete_group_user(cls, group_id: int, user_id: int):
        guser = await cls.find_one(cls.group_id == group_id, cls.userid == user_id)
        if guser: await guser.delete()
