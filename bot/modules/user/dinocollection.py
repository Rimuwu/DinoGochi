

from bot.dbmanager import mongo_client
 
from bot.modules.overwriting.DataCalsses import DBconstructor
import time
from bot.const import DINOS

dino_collection = DBconstructor(mongo_client.user.dino_collection)

def get_dino_data(data_id: int):
    data = DINOS['elements'][str(data_id)]
    return data

async def add_to_collection_dino(user_id: int, data_id: int):
    # Проверяем, существует ли уже такая запись
    existing = await dino_collection.find_one(
        {"user_id": user_id, "data_id": int(data_id)})
    if existing: return None  

    dino_data = get_dino_data(int(data_id))

    entry = {
        "user_id": user_id,
        "data_id": int(data_id),
        "familie": dino_data['name'],
        "date": int(time.time())
    }
    await dino_collection.insert_one(entry)
    return entry

async def get_dino_collection_by_user(user_id: int):
    return await dino_collection.find({"user_id": user_id})

async def get_count_families_by_user(user_id: int):
    collection = await get_dino_collection_by_user(user_id)
    families = set()
    for entry in collection:
        families.add(entry['familie'])
    return len(families)