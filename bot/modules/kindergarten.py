from bot.config import mongo_client
from time import time, strftime

kindergarten = mongo_client.dino_activity.kindergarten
m_hours = 120

async def add_moth_data(userid: int):
    data = {
        "userid": userid,
        "total": m_hours,
        "type": "save",
        "start": int(time()),
        "end": int(time()) + 2_592_000,
        "now": {
            "data": strftime('%j'),
            "hours": 0
        }
    }
    await kindergarten.insert_one(data)

async def dino_kind(dinoid, hours: int = 1):
    data = {
        "dinoid": dinoid,
        "type": "dino",
        "start": int(time()),
        "end": int(time()) + hours * 3600
    }

    await kindergarten.insert_one(data)

async def check_hours(userid: int):
    st = await kindergarten.find_one({'userid': userid})

    if st: return st['total'], st['end']
    else:
        await add_moth_data(userid)
        return m_hours, int(time()) + 2_592_000

async def minus_hours(userid: int, hours: int = 1):
    st = await kindergarten.find_one({'userid': userid})
    if st:
        if (st['total'] - hours) < 0: return False
        else:
            await kindergarten.update_one(
                {'userid': userid}, 
                {'$inc': {'total': -hours, 'now.hours': hours},
                 '$set': {'now.data': strftime('%j')}
                }
            )
            return True
    else: return False

async def hours_now(userid: int):
    st = await kindergarten.find_one({'userid': userid})
    if st:
        if st['now']['data'] == strftime('%j'):
            return st['now']['hours']
        else:
            await kindergarten.update_one({'userid': userid}, 
                                    {'$set': {'now.data': strftime('%j'), 
                                             'now.hours': 0}}
                                    )
            return 0
    else: return 0