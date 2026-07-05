from bot.modules.overwriting.DataCalsses import LazyCollection
from bot.models.other import Lottery, LotteryMember
from bson import ObjectId
from bot.dbmanager import mongo_client
from bot.models.other import Lottery, LotteryMember
from time import time

from bot.config import conf
from bot.dbmanager import mongo_client
from bot.taskmanager import add_task
from bot.modules.quests import quest_process
from bot.modules.logs import log

lottery = LazyCollection(Lottery)
lottery_members = LazyCollection(LotteryMember)


async def lottery_process():
    
    now = int(time())
    # фильтр - розыгрыши, которые закончились
    lotteries = await lottery.find({'time_end': {'$lt': now}}, comment='lottery_process')

    for lot in lotteries: 
        try:
            await Lottery.end_lottery(lot['_id'])
        except Exception as e:
            log(f'except in lottery_process {e}', 3)


if __name__ != '__main__':
    if conf.active_tasks:
        add_task(lottery_process, 60.0, 10.0)