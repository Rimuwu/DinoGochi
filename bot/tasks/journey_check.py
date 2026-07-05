from time import time
from bot.config import conf
from bot.models.activity import JourneyActivity
from bot.taskmanager import add_task
from bot.modules.quests import quest_process

REPEAT_MINUTS = 2

async def end_journey_time():
    current_time = int(time())
    active_ended = await JourneyActivity.find(JourneyActivity.end_time <= current_time).to_list()
    for journey in active_ended:
        duration_minutes = (current_time - journey.start_time) // 60
        await JourneyActivity.end(journey.dino_ids[0])
        await quest_process(journey.sended, 'journey', duration_minutes)

async def events():
    current_time = int(time())
    await JourneyActivity.process_ticks(current_time)

if __name__ != '__main__':
    if conf.active_tasks: 
        add_task(end_journey_time, 30.0, 5.0)
        add_task(events, REPEAT_MINUTS * 60.0, 20.0)