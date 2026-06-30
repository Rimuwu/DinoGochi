from bot.modules.overwriting.DataCalsses import LazyCollection
from bot.models.other import Management


from bot.dbmanager import mongo_client

management = LazyCollection(Management)


async def get_dino_uniqueness_factor(data_id: int):

    from bot.redismanager import redis_get
    unq_data = await redis_get('dino:statistic')

    if not unq_data or 'all_count' not in unq_data or 'data' not in unq_data:
        return 100.0

    all_dinos = unq_data['all_count']
    dino_count = unq_data['data'].get(str(data_id), 0)

    if dino_count <= 1:
        return 100.0

    if all_dinos == 0:
        return 100.0

    uniqueness_percent = round(100.0 - ((dino_count - 1) / all_dinos * 100.0), 2)
    return uniqueness_percent