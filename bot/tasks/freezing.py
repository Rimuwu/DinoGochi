from bot.modules.overwriting.DataCalsses import LazyCollection
from bot.models.activity import Activity

from time import time

from bot.config import conf
from bot.dbmanager import mongo_client
from bot.taskmanager import add_task


long_activity = LazyCollection(Activity)


async def inactive_dinos():
    now = int(time())
    data = await long_activity.find(
        {
            'activity_type': 'inactive',
            '$or': [
                {'end_time': {'$ne': 0, '$lte': now}},
                {'time_end': {'$ne': 0, '$lte': now}}
            ]
        },
        comment='inactive_dinos'
    )

    for i in data:
        await long_activity.delete_one({'_id': i['_id']})
        dino_id = i.get('dino_id')
        if dino_id:
            try:
                from bot.modules.dino_status_cache import invalidate_status_cache
                await invalidate_status_cache(dino_id)
            except Exception:
                pass

if __name__ != '__main__':
    if conf.active_tasks:
        add_task(inactive_dinos, 3600, 1.0)