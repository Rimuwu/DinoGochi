from typing import Union, Optional
from bson.objectid import ObjectId
from bot.modules.data_format import deepcopy, random_code
from time import time
from bot.models.enums import DinoStatus

skill_time = {
    "gym": [5400, 10800],
    "library": [1800, 7200],
    "swimming_pool": [5400, 7200],
    "park": [1200, 7200],
}

def get_skill_time(skill: str): return deepcopy(skill_time[skill])

async def check_status(dino_id: Union[ObjectId, dict]) -> DinoStatus:
    from bot.models.activity import Activity, Kindergarten
    from bot.models.items import ItemCraft
    from bot.models.dinosaur import DinoMood

    if isinstance(dino_id, ObjectId):
        d_id = dino_id
    elif isinstance(dino_id, dict):
        d_id = dino_id['_id']
    else:
        d_id = dino_id.id

    activity = await Activity.find_one(Activity.dino_id == d_id, with_children=True)
    status = DinoStatus.PASS if activity is None else DinoStatus(activity.activity_type)

    on_craft = await ItemCraft.find_one(ItemCraft.dino_id == d_id) is not None
    in_kindergarten = await Kindergarten.find_one(Kindergarten.type == "dino", Kindergarten.dinoid == d_id) is not None
    
    hysteria = await DinoMood.find_one(
        DinoMood.dino_id == d_id, 
        DinoMood.type == 'breakdown', 
        DinoMood.action == 'hysteria'
    ) is not None

    unrestrained_play = await DinoMood.find_one(
        DinoMood.dino_id == d_id, 
        DinoMood.type == 'breakdown', 
        DinoMood.action == 'unrestrained_play'
    ) is not None

    data = [
        DinoStatus.SLEEP, DinoStatus.UNRESTRAINED_PLAY, DinoStatus.GAME, DinoStatus.JOURNEY, 
        DinoStatus.COLLECTING, DinoStatus.KINDERGARTEN, DinoStatus.HYSTERIA, DinoStatus.FARM, 
        DinoStatus.MINE, DinoStatus.BANK, DinoStatus.SAWMILL, DinoStatus.GYM, 
        DinoStatus.LIBRARY, DinoStatus.PARK, DinoStatus.SWIMMING_POOL, DinoStatus.CRAFT, 
        DinoStatus.INACTIVE
    ]
    checks = [
        status == DinoStatus.SLEEP,
        unrestrained_play,
        status == DinoStatus.GAME,
        status == DinoStatus.JOURNEY,
        status == DinoStatus.COLLECTING,
        in_kindergarten,
        hysteria,
        status == DinoStatus.FARM,
        status == DinoStatus.MINE,
        status == DinoStatus.BANK,
        status == DinoStatus.SAWMILL,
        status == DinoStatus.GYM,
        status == DinoStatus.LIBRARY,
        status == DinoStatus.PARK,
        status == DinoStatus.SWIMMING_POOL,
        on_craft,
        status == DinoStatus.INACTIVE
    ]

    if True in checks: 
        status = data[checks.index(True)]
    return status

async def start_skill_activity(dino_id: ObjectId, activity: str, up: str, down: str, 
                               up_unit: list[float], down_unit: list[float],
                               sended: int):
    from bot.models.activity import TrainingActivity
    return await TrainingActivity.start(dino_id, activity, up, down, up_unit, down_unit, sended)

async def end_skill_activity(dino_id: ObjectId):
    from bot.models.activity import TrainingActivity
    return await TrainingActivity.end(dino_id)