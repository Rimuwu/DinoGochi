from typing import Dict, Any, Optional, List, Union
from beanie import Document, PydanticObjectId, Link as BeanieLink
from bson.objectid import ObjectId
from pydantic import Field
from pymongo import IndexModel, ASCENDING, TEXT
from bot.models.base_private import PrivateModelMixin
from bot.models.user import User

class Link(PrivateModelMixin, Document):
    code: str = ""
    who_create: str = "system"
    start: int = 0
    concern: Optional[PydanticObjectId] = None

    class Settings:
        name = "links"
        indexes = [
            IndexModel([("code", TEXT)], name="code"),
            IndexModel([("concern", ASCENDING)], name="concern")
        ]

    @classmethod
    async def create_track(cls, code: str, who_create: str = "system"):
        import time
        from bson import ObjectId

        concern = None
        if "__" in code:
            base_code, concern_code = code.split("__", 1)
            concern_track = await cls.find_one(cls.code == concern_code)
            if concern_track:
                concern = concern_track.id

        res = await cls.find_one(cls.code == code)
        if res: 
            return None

        data = cls(
            code=code,
            start=int(time.time()),
            who_create=who_create,
            concern=concern
        )
        await data.insert()
        return data

    @classmethod
    async def get_track_data(cls, code: str):
        res = await cls.find_one(cls.code == code)
        if res:
            members_track = await TrackingMember.find(TrackingMember.track_id == str(res.id)).to_list()
            concern_links = await cls.find(cls.concern == res.id).to_list()

            return {
                'code': res.code,
                'start': res.start,
                'who_create': res.who_create,
                'concern': res.concern,
                'members': [m.model_dump() for m in members_track],
                'concern_links': [c.model_dump() for c in concern_links],
                '_id': res.id
            }
        return {}

    @classmethod
    async def delete_track(cls, code: str) -> bool:
        res = await cls.find_one(cls.code == code)
        if res:
            await res.delete()
            await TrackingMember.find(TrackingMember.track_id == str(res.id)).delete()
            return True
        return False


class TrackingMember(PrivateModelMixin, Document):
    track_id: str = ""
    user: Optional[BeanieLink[User]] = None
    enter: int = 0
    status: str = ""
    first_status: str = ""
    already_in_bot: bool = False

    class Settings:
        name = "tracking_members"
        indexes = [
            IndexModel([("track_id", ASCENDING)], name="track_id"),
            IndexModel([("user", ASCENDING)], name="user")
        ]

    async def set_status(self, status: str) -> None:
        self.status = status
        await self.save()

    @classmethod
    async def add_track_user(cls, code: str, userid: int):
        import time
        from bot.models.tracking import Link as TrackLink
        from bot.models.user import User

        res = await TrackLink.find_one(TrackLink.code == code)
        if res:
            track_id = res.id
            user_obj = await User.find_one(User.userid == userid)
            already_in_bot = user_obj is not None
            first_status = await cls.user_first_status(user_obj)

            if not user_obj:
                user_obj = await User(userid=userid).insert()

            res2 = await cls.find_one(cls.user.id == user_obj.id, cls.track_id == str(track_id))

            if not res2:
                data = cls(
                    track_id=str(track_id),
                    user=user_obj,
                    enter=int(time.time()),
                    status=first_status,
                    first_status=first_status,
                    already_in_bot=already_in_bot
                )
                await data.insert()
                return data
        return None

    @classmethod
    async def user_first_status(cls, user_obj: Optional[User]) -> str:
        from bot.models.dinosaur import DinoOwners, Egg

        if not user_obj:
            return 'click_start'
        else:
            dinos = await DinoOwners.find_one(DinoOwners.owner.id == user_obj.id)
            eggs = await Egg.find_one(Egg.owner.id == user_obj.id)

            if dinos: 
                return 'gaming'
            elif eggs: 
                return 'incubate'

        return 'create_account'

    @classmethod
    async def edit_track_user(cls, code: str, userid: int, status: str) -> bool:
        from bot.models.tracking import Link as TrackLink
        from bot.models.user import User
        res = await TrackLink.find_one(TrackLink.code == code)
        if res:
            user_obj = await User.find_one(User.userid == userid)
            if user_obj:
                res2 = await cls.find_one(cls.user.id == user_obj.id, cls.track_id == str(res.id))
                if res2:
                    await res2.set_status(status)
                    return True
        return False

    @classmethod
    async def update_all_user_track(cls, userid: int, status: str):
        from bot.models.user import User
        user_obj = await User.find_one(User.userid == userid)
        if user_obj:
            members = await cls.find(cls.user.id == user_obj.id, cls.status != status).to_list()
            for member in members:
                await member.set_status(status)
