from bson import ObjectId
from bot.config import conf
from bot.models.other import Lottery
from bot.modules.logs import log
from bot.modules.task_queue import task_handler

@task_handler("lottery_end")
async def lottery_end_task(data: dict):
    lot_id = data.get("lottery_id")
    if lot_id:
        lot = await Lottery.find_one(Lottery.id == ObjectId(lot_id))
        if lot:
            try:
                await Lottery.end_lottery(lot.id)
            except Exception as e:
                log(f'except in lottery_end_task {e}', 3)