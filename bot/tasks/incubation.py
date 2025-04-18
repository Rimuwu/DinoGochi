from math import e
from time import time

from bot.config import conf
from bot.dbmanager import mongo_client
from bot.modules.dinosaur.dinosaur  import insert_dino
from bot.modules.managment.tracking import update_all_user_track
from bot.modules.notifications import user_notification
from bot.modules.user.user import User
from bot.taskmanager import add_task
from bot.modules.localization import get_lang

from bot.modules.overwriting.DataCalsses import DBconstructor
incubations = DBconstructor(mongo_client.dinosaur.incubation)
users = DBconstructor(mongo_client.user.users)

async def incubation():
    """Проверка инкубируемых яиц
    """

    data = await incubations.find(
        {'incubation_time': {'$lte': int(time())}}, comment='incubation_data') #$lte - incubation_time <= time()

    for egg in data:
        #создаём динозавра
        res, alt_id = await insert_dino(egg['owner_id'], egg['dino_id'], egg['quality']) 

        #удаляем динозавра из инкубаций
        await incubations.delete_one({'_id': egg['_id']}, comment='incubation_1') 

        #отправляем уведомление
        user = await User().create(egg['owner_id'])
        lang = await get_lang(user.userid)
        await user_notification(egg['owner_id'], 
                    'incubation_ready', lang, 
                    user_name=user.name, dino_alt_id_markup=alt_id)

        await update_all_user_track(user.userid, 'gaming')

if __name__ != '__main__':
    if conf.active_tasks:
        add_task(incubation, 20.0, 1.0)