from beanie import Document
from bson.objectid import ObjectId
from typing import Dict, Any, Optional
import time

class Kindergarten(Document):
    userid: Optional[int] = None
    total: Optional[int] = None
    type: str  # "save" or "dino"
    start: int
    end: int
    now: Optional[Dict[str, Any]] = None
    dinoid: Optional[ObjectId] = None

    class Settings:
        name = "kindergarten"

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
    async def Kindergarten.dino_kind(cls, dinoid: ObjectId, hours: int = 1):
        data = cls(
            dinoid=dinoid,
            type="dino",
            start=int(time.time()),
            end=int(time.time()) + hours * 3600
        )
        await data.insert()

    @classmethod
    async def Kindergarten.check_hours(cls, userid: int):
        st = await cls.find_one(cls.userid == userid)
        if st:
            return st.total, st.end
        else:
            await cls.add_moth_data(userid)
            return 240, int(time.time()) + 2_592_000

    @classmethod
    async def Kindergarten.minus_hours(cls, userid: int, hours: int = 1) -> bool:
        st = await cls.find_one(cls.userid == userid)
        if st:
            if (st.total - hours) < 0:
                return False
            else:
                await st.update({
                    '$inc': {'total': -hours, 'now.hours': hours},
                    '$set': {'now.data': time.strftime('%j')}
                })
                return True
        return False

    @classmethod
    async def Kindergarten.hours_now(cls, userid: int) -> int:
        st = await cls.find_one(cls.userid == userid)
        if st and st.now:
            if st.now.get('data') == time.strftime('%j'):
                return st.now.get('hours', 0)
            else:
                await st.update({
                    '$set': {
                        'now.data': time.strftime('%j'),
                        'now.hours': 0
                    }
                })
                return 0
        return 0
