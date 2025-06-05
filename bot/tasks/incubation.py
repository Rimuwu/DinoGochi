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
from bot.exec import bot

from bot.modules.overwriting.DataCalsses import DBconstructor
incubations = DBconstructor(mongo_client.dinosaur.incubation)
users = DBconstructor(mongo_client.user.users)

async def incubation():
    """Проверка инкубируемых яиц
    """

    data = await incubations.find(
        {
            'incubation_time': {'$lte': int(time())},
            '$or': [
                {'stage': None},
                {'stage': 'incubation'}
            ]
        },
        comment='incubation_data'
    )

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

async def delete_choosing():
    """Проверка инкубируемых яиц
    """

    data = await incubations.find(
        {
            'start_choosing': {'$lte': int(time()) - 12 * 60 * 60},
            'stage': 'choosing',
            'id_message': {'$ne': 0}
        },
        comment='incubation_data'
    )

    for message_egg in data:
        #удаляем динозавра из инкубаций
        await incubations.delete_one({'_id': message_egg['_id']}, comment='incubation_2')

        if message_egg['id_message']:
            try:
                await bot.delete_message(message_egg['owner_id'], 
                                         message_egg['id_message'])
            except Exception as e: pass

if __name__ != '__main__':
    if conf.active_tasks:
        add_task(incubation, 20.0, 1.0)
        add_task(delete_choosing, 3600.0, 15.0)