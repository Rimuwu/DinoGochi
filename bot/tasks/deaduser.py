from datetime import datetime, timezone, timedelta
from random import choice, randint, choices
from time import time

from bot.config import conf, mongo_client
from bot.exec import bot
from bot.modules.data_format import seconds_to_str
from bot.modules.localization import get_data, t
from bot.modules.notifications import user_notification
from bot.modules.quests import create_quest, quest_resampling, save_quest
from bot.modules.user import col_dinos
from bot.taskmanager import add_task
 

users = mongo_client.user.users
tavern = mongo_client.tavern.tavern
quests_data = mongo_client.tavern.quests
daily_data = mongo_client.tavern.daily_award
dead_users = mongo_client.other.dead_users

# - Если нельзя отправить спустя неделю - ничего
# - Если нельзя отправить спустя месяц - удаление аккаунта
# - Если можно отправить спустя неделю - просто сообщение с напоминанием
# - Если можно отправить спустя месяц - создание промокода 


async def save_d(userid: int, type_send: str, promo: str = ''):
    data = {
        'userid': userid,
        'type_send': type_send,
        'promo': promo
    }

    await dead_users.insert_one(data)

async def DeadUser_return():
    users_ids = await users.find({"last_message_time": 
        {'$lte': int(time()) - 86400 * 7}}, {'_id': 1, 'last_message_time': 1, 'userid': 1}
                                 ).to_list(None) 

    for us in users_ids:
        if await col_dinos(us['userid']):
            create = us['_id'].generation_time
            now = datetime.now(timezone.utc)
            delta: timedelta = now - create

            res = await dead_users.find_one({'userid': us['userid']}) # type: dict
            if res:
                userid, type_send, promo = list(res.values())
            else:
                userid, type_send, promo = us['userid'], '0', ''

            if delta.days >= 7 and delta.days <= 30 and type_send != 'situation1':
                # - Если можно отправить спустя неделю - просто сообщение с напоминанием
                


    # Юзеры у которых последнее сообщение больше чем неделю назад 
    





if __name__ != '__main__':
    if conf.active_tasks:
        add_task(DeadUser_return, 36000.0, 100.0)