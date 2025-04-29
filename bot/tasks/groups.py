
from bot.dbmanager import mongo_client
from bot.modules.groups import delete_messages

from bot.modules.overwriting.DataCalsses import DBconstructor

from bot.config import conf
from bot.dbmanager import mongo_client
from bot.taskmanager import add_task

groups = DBconstructor(mongo_client.group.groups)
messages = DBconstructor(mongo_client.group.messages)

async def delete_messages_task():
    all_groups = await groups.find({}, 
                                   comment='delete_messages')
    for group in all_groups:
        group_id = group['group_id']
        delete_time = group['delete_message']

        if delete_time == 0: continue
        else:
            await delete_messages(group_id, delete_time)

if __name__ != '__main__':
    if conf.active_tasks:
        add_task(delete_messages_task, 300.0, 30.0)