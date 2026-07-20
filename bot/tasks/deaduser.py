from bot.modules.overwriting.DataCalsses import LazyCollection
from bot.models.user import User
from bot.models.other import DeadUser
from asyncio import sleep
from time import time

from bot.config import conf
from bot.dbmanager import mongo_client
from bot.exec import main_router, bot
from bot.modules.data_format import random_code, seconds_to_str, list_to_inline
from bot.modules.localization import t, get_lang

from bot.taskmanager import add_task
from bot.modules.user.user import User
from bot.modules.logs import log
 

users = LazyCollection(User)
dead_users = LazyCollection(DeadUser)

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

    res = await dead_users.find_one({'userid': userid}, comment='save_d_res')
    if res:
        await dead_users.update_one({'userid': userid}, {'$set':
            data}, comment='save_d_check')
    else:
        await dead_users.insert_one(data, comment='save_d_1')

async def DeadUser_return():
    users_ids = list(await users.find({"last_message_time": 
        {'$lte': int(time()) - 86400 * 7}}, {'_id': 1, 'last_message_time': 1, 'userid': 1}
                                 ))

    log(f'Начата проверка {len(users_ids)}', 0)

    del_u = 0
    for us in users_ids:
        user = await User.find_one(User.userid == us['userid'])
        col_d = await user.get_col_dinos if user else 0
        if col_d == 0:
            last_msg_t = us.get('last_message_time', 0)
            if not last_msg_t or last_msg_t <= 0:
                continue

            delta_days = (int(time()) - last_msg_t) // 86400
            if delta_days > 730:
                continue

            res = await dead_users.find_one({'userid': us['userid']}, {'_id': 0}, 
                                            comment='DeadUser_return_res')
            if res:
                userid, type_send, promo, last_m = list(res.values())
            else:
                userid, type_send, promo, last_m = us['userid'], '0', '', int(time())

            lat_days = (int(time()) - last_m) // 86400

            if delta_days >= 7 and delta_days < 30 and type_send != 'situation1':
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

            elif delta_days >= 31 and type_send != 'situation2' \
                or type_send == 'situation2' and lat_days >= 31:
                    code = random_code()

                    await save_d(userid, 'situation2', int(time()), code)
                    lang = await get_lang(userid)

                    st_time = seconds_to_str(
                        int(time()) - us['last_message_time'], lang, max_lvl='day'
                    )

                    text = t('dead_user.situation2', lang, st_time = st_time)
                    button = t('dead_user.buttons.promo', lang)

                    markup = list_to_inline(
                        [{button: f'start_cmd {code}'}]
                    )
                    try:
                        await bot.send_message(userid, text, reply_markup=markup)
                    except Exception as ex:
                        error_code = ex.args[0] if ex.args else None
                        if error_code in [400, 403]:
                            # - Если нельзя отправить спустя месяц - удалить акк
                            user = await User().create(userid)
                            if user:
                                await user.full_delete()
                                del_u += 1

        await sleep(1.5)
    log(f'Завершил работу. Проверено {len(users_ids)}, удалено: {del_u}', 0, 'DeadUsers')


async def clear_data():
    dead_users_list = await dead_users.find({}, {'userid': 1}, comment='clear_data_list')
    if not dead_users_list:
        return

    dead_userids = [u['userid'] for u in dead_users_list if 'userid' in u]
    if not dead_userids:
        return

    min_active_time = int(time()) - 7 * 86400
    batch_size = 1000

    for i in range(0, len(dead_userids), batch_size):
        chunk = dead_userids[i:i + batch_size]
        active_users = await users.find({
            'userid': {'$in': chunk},
            'last_message_time': {'$gt': min_active_time}
        }, {'userid': 1}, comment='clear_data_active_users')

        active_userids = [u['userid'] for u in active_users if 'userid' in u]
        if active_userids:
            await dead_users.delete_many({
                'userid': {'$in': active_userids}
            }, comment='clear_data_delete_active')


if __name__ != '__main__':
    if conf.active_tasks: 
        add_task(clear_data, 36000.0, 500.0)
        add_task(DeadUser_return, 36000.0, 100.0)