from bot.modules.overwriting.DataCalsses import LazyCollection
from bot.models.activity import Activity
from bot.models.dinosaur import DinoMood, Dino, DinoOwners
from bot.models.user import User
from random import randint, random
from time import time
from bson import ObjectId
from bot.modules.task_queue import task_handler

from bot.config import conf
from bot.modules.data_format import transform
from bot.models.dinosaur import Dino
from bot.models.activity import GameActivity
from bot.models.items import Item

from bot.taskmanager import add_task
from bot.modules.quests import quest_process

long_activity = LazyCollection(Activity)
dinosaurs = LazyCollection(Dino)
dino_owners = LazyCollection(DinoOwners)

REPEAT_MINUTES = 3
ENERGY_DOWN = 0.03 * REPEAT_MINUTES
ENERGY_DOWN2 = 0.5 * REPEAT_MINUTES
LVL_CHANCE = 0.125 * REPEAT_MINUTES
GAME_CHANCE = 0.17 * REPEAT_MINUTES

@task_handler("game_end")
async def game_end_task(data: dict):
    dino_id = data.get("dino_id")
    if dino_id:
        dino_oid = ObjectId(dino_id)
        i = await long_activity.find_one({'dino_id': dino_oid, 'activity_type': 'game'})
        if i:
            await GameActivity.end(dino_oid)
            game_time = i['end_time'] - i['start_time']
            owner = await Dino.get_owner_by_id(dino_oid)
            if owner:
                await quest_process(owner.owner_id, 'game', (game_time) // 60)

            await DinoMood.add(dino_oid, 'end_game', 1, 
                     int((game_time // 2) * i['game_percent']))

async def game_process():
    data = await long_activity.find(
        {'end_time': {'$gte': int(time())},
            'activity_type': 'game'}, comment='game_process_data')

    for game_data in data:
        percent = game_data['game_percent']
        dino = await dinosaurs.find_one({'_id': game_data['dino_id']}, comment='game_process_dino') # type: dict | None

        if dino:
            charisma = dino['stats']['charisma']

            if random() <= ENERGY_DOWN:
                if random() <= ENERGY_DOWN2: 
                    await Dino.mutate_stat(dino, 'energy', -1)

            if dino['stats']['game'] < 100:
                if random() <= LVL_CHANCE: 
                    if not await DinoMood.check_breakdown(dino['_id'], 'unrestrained_play'):
                        dino_con = await Dino.get_owner_by_id(dino['_id'])
                        if dino_con and dino_con.owner_id:
                            user_obj = await User.find_one(User.userid == dino_con.owner_id)
                            if user_obj:
                                if await DinoMood.check_inspiration(dino['_id'], 'exp_boost'):
                                    await user_obj.add_xp_lvl(randint(1, 10))
                                else:
                                    await user_obj.add_xp_lvl(randint(1, 20))

                                if randint(1, 100) + transform(charisma, 20, 30) >= 80:
                                    await user_obj.add_xp_lvl(randint(1, 5))

                if dino['stats']['game'] < 100:
                    if random() <= GAME_CHANCE:
                        add_unit = 0

                        if randint(1, 100) + transform(charisma, 20, 5) >= 80:
                            add_unit = randint(1, 5)

                        if randint(1, 4) == 4:
                            dino_class = await Dino().create(dino['_id'])
                            if dino_class:
                                controller = await Item.check_accessory(
                                    dino_class.id, 'controller', True
                                    )

                                if controller:
                                    add_unit = randint(1, 5) + controller.get_level()

                        await Dino.mutate_stat(
                            dino, 'game', int(add_unit + randint(2, 10) * percent))

if __name__ != '__main__':
    if conf.active_tasks:
        add_task(game_process, REPEAT_MINUTES * 60.0, 3.0)