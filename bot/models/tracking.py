from typing import Dict, Any, Optional, List, Union
from beanie import Document, PydanticObjectId
from bson.objectid import ObjectId
from pydantic import Field
from pymongo import IndexModel, ASCENDING, TEXT

class Link(Document):
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

class TrackingMember(Document):
    track_id: str = ""
    userid: Optional[int] = None
    enter: int = 0
    status: str = ""
    first_status: str = ""
    already_in_bot: bool = False

    class Settings:
        name = "tracking_members"
        indexes = [
            IndexModel([("track_id", ASCENDING)], name="track_id"),
            IndexModel([("userid", ASCENDING)], name="userid")
        ]

    @classmethod
    async def add_track_user(cls, code: str, userid: int):
        import time
        from bot.models.tracking import Link
        from bot.models.user import User

        res = await Link.find_one(Link.code == code)
        if res:
            track_id = res.id
            res2 = await cls.find_one(cls.userid == userid, cls.track_id == str(track_id))

            if not res2:
                already_in_bot = await User.find_one(User.userid == userid)
                first_status = await cls.user_first_status(userid)

                data = cls(
                    track_id=str(track_id),
                    userid=userid,
                    enter=int(time.time()),
                    status=first_status,
                    first_status=first_status,
                    already_in_bot=bool(already_in_bot)
                )
                await data.insert()
                return data
        return None

    @classmethod
    async def user_first_status(cls, userid: int) -> str:
        from bot.models.user import User
        from bot.models.dinosaur import DinoOwners, Egg

        user_b = await User.find_one(User.userid == userid)
        if not user_b:
            return 'click_start'
        else:
            dinos = await DinoOwners.find_one(DinoOwners.owner_id == userid)
            eggs = await Egg.find_one(Egg.owner_id == userid)

            if dinos: 
                return 'gaming'
            elif eggs: 
                return 'incubate'

        return 'create_account'

    @classmethod
    async def edit_track_user(cls, code: str, userid: int, status: str) -> bool:
        from bot.models.tracking import Link
        res = await Link.find_one(Link.code == code)
        if res:
            res2 = await cls.find_one(cls.userid == userid, cls.track_id == str(res.id))
            if res2:
                res2.status = status
                await res2.save()
                return True
        return False

    @classmethod
    async def update_all_user_track(cls, userid: int, status: str):
        await cls.find(cls.userid == userid, cls.status != status).update({'$set': {'status': status}})
