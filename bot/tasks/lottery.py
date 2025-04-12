from bson import ObjectId
from bot.dbmanager import mongo_client
from bot.modules.lottery.lottery import end_lottery
from bot.modules.overwriting.DataCalsses import DBconstructor
from time import time

from bot.config import conf
from bot.dbmanager import mongo_client
from bot.taskmanager import add_task
from bot.modules.quests import quest_process
from bot.modules.logs import log

lottery = DBconstructor(mongo_client.lottery.lottery)
lottery_members = DBconstructor(mongo_client.lottery.members)


async def lottery_process():
    
    now = int(time())
    # фильтр - розыгрыши, которые закончились
    lotteries = await lottery.find({'time_end': {'$lt': now}}, comment='lottery_process')

    for lot in lotteries: 
        try:
            await end_lottery(lot['_id'])
        except Exception as e:
            log(f'except in lottery_process {e}', 3)


if __name__ != '__main__':
    if conf.active_tasks:
        # add_task(lottery_process, 60.0, 10.0)