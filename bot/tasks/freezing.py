
from time import time

from bot.config import conf
from bot.dbmanager import mongo_client
from bot.taskmanager import add_task


from bot.modules.overwriting.DataCalsses import DBconstructor
long_activity = DBconstructor(mongo_client.dino_activity.long_activity)


async def inactive_dinos():
    data = await long_activity.find(
        {'time_end': {'$ne': 0, '$gte': int(time())},
            'activity_type': 'inactive'}, comment='inactive_dinos')
    
    for i in data:
        await long_activity.delete_one({'_id': i['_id']})

if __name__ != '__main__':
    if conf.active_tasks:
        add_task(inactive_dinos, 3600, 1.0)