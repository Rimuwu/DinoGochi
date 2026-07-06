from beanie import Document, Link
from bson.objectid import ObjectId
from typing import Dict, Any, Optional
import time

from pymongo import IndexModel, ASCENDING
from bot.models.base_private import PrivateModelMixin
from bot.models.user import User
from bot.models.dinosaur import Dino

class Kindergarten(PrivateModelMixin, Document):
    user: Optional[Link[User]] = None
    total: Optional[int] = None
    type: str = ""  # "save" or "dino"
    start: int = 0
    end: int = 0
    now: Optional[Dict[str, Any]] = None
    dino: Optional[Link[Dino]] = None

    class Settings:
        name = "kindergarten"
        indexes = [
            IndexModel(
                [("user", ASCENDING)],
                unique=True,
                partialFilterExpression={"user": {"$exists": True}},
                name="user"
            )
        ]

    @classmethod
    async def add_moth_data(cls, userid: int):
        user_obj = await User.find_one(User.userid == userid)
        if not user_obj:
            user_obj = await User(userid=userid).insert()

        data = cls(
            user=user_obj,
            total=240,
            type="save",
            start=int(time.time()),
            end=int(time.time()) + 2_592_000,
            now={
                "data": time.strftime('%j'),
                "hours": 0
            }
        )
        await data.insert()

    @classmethod
    async def remove_dino(cls, dinoid: ObjectId):
        await cls.find(cls.dino.id == dinoid, cls.type == "dino").delete()

    @classmethod
    async def dino_kind(cls, dinoid: ObjectId, hours: int = 1):
        dino_obj = await Dino.find_one(Dino.id == dinoid)
        if dino_obj:
            data = cls(
                dino=dino_obj,
                type="dino",
                start=int(time.time()),
                end=int(time.time()) + hours * 3600
            )
            await data.insert()

    @classmethod
    async def check_hours(cls, userid: int):
        user_obj = await User.find_one(User.userid == userid)
        if not user_obj:
            user_obj = await User(userid=userid).insert()

        st = await cls.find_one(cls.user.id == user_obj.id)
        if st:
            return st.total, st.end
        else:
            await cls.add_moth_data(userid)
            return 240, int(time.time()) + 2_592_000

    @classmethod
    async def minus_hours(cls, userid: int, hours: int = 1) -> bool:
        user_obj = await User.find_one(User.userid == userid)
        if not user_obj:
            return False

        st = await cls.find_one(cls.user.id == user_obj.id)
        if st:
            if (st.total - hours) < 0:
                return False
            else:
                st.total -= hours
                if st.now:
                    st.now['hours'] = st.now.get('hours', 0) + hours
                    st.now['data'] = time.strftime('%j')
                await st.save()
                return True
        return False

    @classmethod
    async def hours_now(cls, userid: int) -> int:
        user_obj = await User.find_one(User.userid == userid)
        if not user_obj:
            return 0

        st = await cls.find_one(cls.user.id == user_obj.id)
        if st and st.now:
            if st.now.get('data') == time.strftime('%j'):
                return st.now.get('hours', 0)
            else:
                st.now['data'] = time.strftime('%j')
                st.now['hours'] = 0
                await st.save()
                return 0
        return 0
