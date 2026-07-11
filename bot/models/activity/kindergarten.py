from beanie import Document, Link
from bson.objectid import ObjectId
from typing import Dict, Any, Optional, Union
import time

from pymongo import IndexModel, ASCENDING
from bot.models.base_private import PrivateModelMixin
from bot.models.dinosaur import Dino

class Kindergarten(PrivateModelMixin, Document):
    userid: int = 0
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
                [("userid", ASCENDING)],
                unique=True,
                partialFilterExpression={"userid": {"$exists": True}},
                name="userid"
            )
        ]

    @classmethod
    async def add_moth_data(cls, userid: int):
        data = cls(
            userid=userid,
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
    async def remove_dino(cls, dinoid: Union[ObjectId, str]):
        if isinstance(dinoid, str):
            dinoid = ObjectId(dinoid)
        await cls.find(cls.dino.id == dinoid, cls.type == "dino").delete()
        try:
            from bot.modules.dino_status_cache import invalidate_status_cache
            await invalidate_status_cache(dinoid)
        except Exception:
            pass

    @classmethod
    async def dino_kind(cls, dinoid: Union[ObjectId, str], hours: int = 1):
        if isinstance(dinoid, str):
            dinoid = ObjectId(dinoid)
        dino_obj = await Dino.find_one(Dino.id == dinoid)
        if dino_obj:
            data = cls(
                dino=dino_obj,
                type="dino",
                start=int(time.time()),
                end=int(time.time()) + hours * 3600
            )
            await data.insert()
            try:
                from bot.modules.dino_status_cache import invalidate_status_cache
                await invalidate_status_cache(dinoid)
            except Exception:
                pass

    @classmethod
    async def check_hours(cls, userid: int):
        st = await cls.find_one(cls.userid == userid)
        if st:
            return st.total, st.end
        else:
            await cls.add_moth_data(userid)
            return 240, int(time.time()) + 2_592_000

    @classmethod
    async def minus_hours(cls, userid: int, hours: int = 1) -> bool:
        st = await cls.find_one(cls.userid == userid)
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
        st = await cls.find_one(cls.userid == userid)
        if st and st.now:
            if st.now.get('data') == time.strftime('%j'):
                return st.now.get('hours', 0)
            else:
                st.now['data'] = time.strftime('%j')
                st.now['hours'] = 0
                await st.save()
                return 0
        return 0
