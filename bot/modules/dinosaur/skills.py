
from bson.objectid import ObjectId
from bot.config import mongo_client

from bot.modules.overwriting.DataCalsses import DBconstructor

users = DBconstructor(mongo_client.user.users)
dinosaurs = DBconstructor(mongo_client.dinosaur.dinosaurs)


"""
90 дней на прокачку силы до максимума - 0.11 за 1.5 часа (рандом 0.05-0.15)
- 0.0123 за 10 минут

Погладить - (рандом -(0.001, 0.01) случайный скилл )
Поговорить - (рандом (0.001, 0.01) харизма )
Борьба - (рандом (0.001, 0.01) сила )

"""


async def add_skill_point(dino_id: ObjectId, skill: str, point: float):

    """ -1  -  максимальный / минимальный уровень навыка
         1  -  добавлен

        point - отрицательное / положительное число 
    """

    assert skill in ['charisma', 'intelligence', 'dexterity', 'power'], f'Skill {skill} не в списке'

    dino = await dinosaurs.find_one({"_id": dino_id}, comment='add_skill_point')
    if dino:
        skill_stat = dino['stats'][skill]

        if skill_stat + point >= 10.0: return -1
        elif skill_stat + point <= 0.0: return -1
        else:
            await dinosaurs.update_one({'_id': dino['_id']}, 
                                        {'$set': {f'stats.{skill}': 
                                            round(point + dino['stats'][skill], 4)}})
            return 1