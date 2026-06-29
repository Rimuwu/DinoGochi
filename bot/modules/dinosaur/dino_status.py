from typing import Union, Optional
from bson.objectid import ObjectId
from bot.modules.data_format import deepcopy, random_code
from time import time

skill_time = {
    "gym": [5400, 10800],
    "library": [1800, 7200],
    "swimming_pool": [5400, 7200],
    "park": [1200, 7200],
}

def get_skill_time(skill: str): return deepcopy(skill_time[skill])

async def check_status(dino_id: Union[ObjectId, dict]) -> str:
    from bot.models.activity import Activity, Kindergarten
    from bot.models.items import ItemCraft
    from bot.models.dinosaur import DinoMood
    
    if isinstance(dino_id, ObjectId):
        d_id = dino_id
    elif isinstance(dino_id, dict):
        d_id = dino_id['_id']
    else:
        d_id = dino_id.id

    activity = await Activity.find_one(Activity.dino_id == str(d_id))
    status = 'pass' if activity is None else activity.activity_type

    on_craft = await ItemCraft.find_one(ItemCraft.dino_id == str(d_id)) is not None
    in_kindergarten = await Kindergarten.find_one(Kindergarten.dinos.contains(str(d_id))) is not None
    
    hysteria = await DinoMood.find_one(
        DinoMood.dino_id == str(d_id), 
        DinoMood.type == 'breakdown', 
        DinoMood.action == 'hysteria'
    ) is not None

    unrestrained_play = await DinoMood.find_one(
        DinoMood.dino_id == str(d_id), 
        DinoMood.type == 'breakdown', 
        DinoMood.action == 'unrestrained_play'
    ) is not None

    data = ['sleep', 'unrestrained_play', 'game', 'journey', 'collecting', 'kindergarten', 'hysteria', 'farm', 'mine', 'bank', 'sawmill', 'gym', 'library', 'park', 'swimming_pool', 'craft', 'inactive']
    checks = [
        status == 'sleep',
        unrestrained_play,
        status == 'game',
        status == 'journey',
        status == 'collecting',
        in_kindergarten,
        hysteria,
        status == 'farm',
        status == 'mine',
        status == 'bank',
        status == 'sawmill',
        status == 'gym',
        status == 'library',
        status == 'park',
        status == 'swimming_pool',
        on_craft,
        status == 'inactive'
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