from time import time
from bson import ObjectId
from bot.config import conf
from bot.models.activity import JourneyActivity
from bot.modules.quests import quest_process
from bot.modules.task_queue import task_handler

@task_handler("end_journey_time")
async def end_journey_time_task(data: dict):
    journey_id = data.get("journey_id")
    if journey_id:
        journey = await JourneyActivity.find_one(
            JourneyActivity.id == ObjectId(journey_id))
        if journey:
            current_time = int(time())
            duration_minutes = (current_time - journey.start_time) // 60
            await JourneyActivity.end(journey.id)
            await quest_process(journey.sended, 'journey', duration_minutes)

@task_handler("journey_event")
async def journey_event_task(data: dict):
    journey_id = data.get("journey_id")
    if journey_id:
        journey = await JourneyActivity.find_one(JourneyActivity.id == ObjectId(journey_id))
        if journey:
            current_time = int(time())
            await JourneyActivity.process_journey_ticks(journey, current_time)