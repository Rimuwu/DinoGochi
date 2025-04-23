from random import randint, random
from time import time

from bot.config import conf
from bot.dbmanager import mongo_client
from bot.modules.data_format import transform
from bot.modules.dinosaur.dinosaur  import Dino, end_game, mutate_dino_stat, get_owner
from bot.modules.dinosaur.mood import add_mood, check_breakdown, check_inspiration
from bot.modules.dinosaur.rpg_states import add_state
from bot.modules.items.accessory import check_accessory
from bot.modules.user.user import experience_enhancement
from bot.taskmanager import add_task
from bot.modules.quests import quest_process

from bot.modules.overwriting.DataCalsses import DBconstructor
long_activity = DBconstructor(mongo_client.dino_activity.long_activity)
dinosaurs = DBconstructor(mongo_client.dinosaur.dinosaurs)
dino_owners = DBconstructor(mongo_client.dinosaur.dino_owners)

REPEAT_MINUTES = 3
ENERGY_DOWN = 0.03 * REPEAT_MINUTES
ENERGY_DOWN2 = 0.5 * REPEAT_MINUTES
LVL_CHANCE = 0.125 * REPEAT_MINUTES
GAME_CHANCE = 0.17 * REPEAT_MINUTES

async def game_end():
    data = await long_activity.find({'game_end': 
        {'$lte': int(time())},'activity_type': 'game'}, comment='game_end_data')

    for i in data:
        await end_game(i['dino_id'])
        game_time = i['game_end'] - i['game_start']
        owner = await get_owner(i['dino_id'])
        if owner:
            await quest_process(owner['owner_id'], 'game', (game_time) // 60)

        await add_mood(i['dino_id'], 'end_game', 1, 
                 int((game_time // 2) * i['game_percent']))

async def game_process():
    data = await long_activity.find(
        {'game_end': {'$gte': int(time())},
            'activity_type': 'game'}, comment='game_process_data')

    for game_data in data:
        percent = game_data['game_percent']
        dino = await dinosaurs.find_one({'_id': game_data['dino_id']}, comment='game_process_dino') # type: dict | None

        if dino:
            charisma = dino['stats']['charisma']

            if random() <= ENERGY_DOWN:
                if random() <= ENERGY_DOWN2: 
                    await mutate_dino_stat(dino, 'energy', -1)

            if dino['stats']['game'] < 100:
                if random() <= LVL_CHANCE: 
                    if not await check_breakdown(dino['_id'], 'unrestrained_play'):
                        dino_con = await dino_owners.find_one({'dino_id': dino['_id']}, 
                            comment='game_process_dino_con')
                        if dino_con:
                            userid = dino_con['owner_id']
                            if await check_inspiration(dino['_id'], 'exp_boost'):
                                await experience_enhancement(userid, randint(1, 10))
                            else:
                                await experience_enhancement(userid, randint(1, 20))

                            if randint(1, 100) + transform(charisma, 20, 30) >= 80:
                                await experience_enhancement(userid, randint(1, 5))

                if dino['stats']['game'] < 100:
                    if random() <= GAME_CHANCE:
                        add_unit = 0

                        if randint(1, 100) + transform(charisma, 20, 5) >= 80:
                            add_unit = randint(1, 5)

                        if randint(1, 4) == 4:
                            dino_class = await Dino().create(dino['_id'])
                            if dino_class:
                                if await check_accessory(
                                    dino_class, 'controller', True
                                    ):
                                        add_unit = randint(1, 5)

                        await mutate_dino_stat(dino, 'game', int(add_unit + randint(2, 10) * percent))

if __name__ != '__main__':
    if conf.active_tasks:
        add_task(game_end, 15, 3.0)
        add_task(game_process, REPEAT_MINUTES * 60.0, 3.0)