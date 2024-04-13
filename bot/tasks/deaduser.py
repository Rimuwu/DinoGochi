from datetime import datetime, timezone, timedelta
from random import choice, randint, choices
from time import time

from bot.config import conf, mongo_client
from bot.exec import bot
from bot.modules.data_format import seconds_to_str, list_to_inline
from bot.modules.localization import get_data, t, get_lang
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
# - Если можно отправить спустя месяц - сообщение с ромокодом


async def save_d(userid: int, type_send: str, last_m: int, promo: str = ''):
    data = {
        'userid': userid,
        'type_send': type_send,
        'promo': promo,
        'last_m': last_m
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
                userid, type_send, promo, last_m = list(res.values())
            else:
                userid, type_send, promo, last_m = us['userid'], '0', '', int(time())

            lat_days = last_m // 86400

            if delta.days >= 7 and delta.days < 30 and type_send != 'situation1':
                # - Если можно отправить спустя неделю - просто сообщение с напоминанием

                lang = await get_lang(userid)
                text = t('dead_user.situation1', lang)
                button = t('dead_user.buttons.game', lang)

                markup = list_to_inline(
                    [{button: f'start_cmd {promo}'}]
                )
                try:
                    await bot.send_message(userid, text, reply_markup=markup)
                except: 
                    # - Если нельзя отправить спустя неделю - ничего
                    pass

                await save_d(userid, 'situation1', int(time()))

            elif delta.days >= 30 and type_send != 'situation2' \
                or type_send == 'situation2' and lat_days >= 30:
                    
                    


    # Юзеры у которых последнее сообщение больше чем неделю назад 
    





if __name__ != '__main__':
    if conf.active_tasks:
        add_task(DeadUser_return, 36000.0, 100.0)