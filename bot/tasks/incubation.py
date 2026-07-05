from bot.modules.overwriting.DataCalsses import LazyCollection
from bot.models.dinosaur import Egg
from bot.models.user import User
from math import e
from time import time

from bot.config import conf
from bot.dbmanager import mongo_client
from bot.models.dinosaur import Dino
from bot.modules.managment.tracking import update_all_user_track
from bot.modules.notifications import user_notification
from bot.modules.user.user import User
from bot.taskmanager import add_task
from bot.modules.localization import get_lang
from bot.exec import bot

incubations = LazyCollection(Egg)
users = LazyCollection(User)

async def incubation():
    """Проверка инкубируемых яиц
    """
    from beanie.odm.operators.find.comparison import In

    data = await Egg.find(
        Egg.incubation_time <= int(time()),
        In(Egg.stage, [None, 'incubation'])
    ).to_list()

    for egg in data:
        # atomically delete/claim the egg first to prevent double hatching
        delete_result = await egg.delete()
        if delete_result and delete_result.deleted_count:
            #создаём динозавра
            res, alt_id = await Dino.insert_dino(egg.owner_id, egg.dino_id, egg.quality)

            #отправляем уведомление
            user = await User().create(egg.owner_id)
            lang = await get_lang(user.userid)
            await user_notification(egg.owner_id, 
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