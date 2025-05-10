

from bot.dbmanager import mongo_client
from bot.modules.overwriting.DataCalsses import DBconstructor

management = DBconstructor(mongo_client.other.management)


async def get_dino_uniqueness_factor(data_id: int):

    unq_data: dict = await management.find_one(
    {'_id': 'dino_statistic'},
    comment='get_dino_uniqueness_factor'
    ) # type: ignore #type: dict

    all_dinos = unq_data['all_count']
    dino_count = unq_data['data'].get(str(data_id), 0)

    if dino_count <= 1:
        return 100.0

    if all_dinos == 0:
        return 100.0

    uniqueness_percent = round(100.0 - ((dino_count - 1) / all_dinos * 100.0), 2)
    return uniqueness_percent