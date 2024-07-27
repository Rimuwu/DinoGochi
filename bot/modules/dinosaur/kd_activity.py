from bson.objectid import ObjectId
from bot.config import mongo_client
from bot.modules.overwriting.DataCalsses import DBconstructor
from time import time as time_now

dinosaurs = DBconstructor(mongo_client.dinosaur.dinosaurs)
kd_activity = DBconstructor(mongo_client.dino_activity.kd_activity)

async def save_kd(dino_id: ObjectId, activity_type: str, kd_time: int) -> dict:
    """ kd_time - просто количество секунд ожидания, код сам добавить настоящее время
    """

    if not await kd_activity.find_one({'dino_id': dino_id, 'activity_type': activity_type}, comment='save_kd_1'):
        kd = {
            'dino_id': dino_id,
            'activity_type': activity_type,
            'kd_time': kd_time + int(time_now())
        }

        await kd_activity.insert_one(kd, comment='save_kd')
        return kd
    return {}

async def check_activity(dino_id: ObjectId, activity_type: str) -> int:
    """ Отвечает на вопрос - есть ли кд на эту активность
        Возвращает 0 - если активность можно использовать
        Возвращает количесвтов секунд (int) сколько активность ещё нельзя использовать
    """

    fr = await kd_activity.find_one({'dino_id': dino_id, 'activity_type': activity_type}, comment='check_activity_fr')
    if not fr: return 0
    else:
        time_ost = fr['kd_time'] - int(time_now())
        if time_ost < 0:
            await kd_activity.delete_one({'_id': fr['_id']}, comment='check_activity')
            return 0
        else: return time_ost

async def check_all_activity(dino_id: ObjectId):
    """ Проверяет все кд активности у динозавра и возвращает словарь
        Формат: активность: оставшееся время
    """
    fr_l = await kd_activity.find({'dino_id': dino_id}, comment='check_all_activity_fr_l')
    result_dict = {}

    for i in fr_l:
        time_ost = i['kd_time'] - int(time_now())
        if time_ost < 0:
            await kd_activity.delete_one({'_id': i['_id']}, comment='check_all_activity_1')
        else:
            result_dict[i['activity_type']] = i['kd_time'] - int(time_now())

    return result_dict