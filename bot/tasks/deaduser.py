from asyncio import sleep
from time import time

from bot.config import conf, mongo_client
from bot.exec import bot
from bot.modules.data_format import random_code, seconds_to_str, list_to_inline
from bot.modules.localization import t, get_lang
from bot.modules.user.user import col_dinos
from bot.taskmanager import add_task
from bot.modules.user.user import User
from bot.modules.logs import log
 

from bot.modules.overwriting.DataCalsses import DBconstructor
users = DBconstructor(mongo_client.user.users)
dead_users = DBconstructor(mongo_client.other.dead_users)

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
        col_d = await col_dinos(us['userid'])
        if col_d == 0:
            delta_days = (int(time()) - us['last_message_time']) // 86400

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
                        if ex.error_code in [400, 403]:
                            # - Если нельзя отправить спустя месяц - удалить акк
                            user = await User().create(userid)
                            await user.full_delete()
                            del_u += 1

        await sleep(1.5)
    log(f'Завершил работу. Проверено {len(users_ids)}, удалено: {del_u}', 0, 'DeadUsers')


async def clear_data():
    users_ids = await dead_users.find({},
                                      {'_id': 1, 'userid': 1}, comment='clear_data')

    for user in users_ids:
        res = await users.find_one({
            'userid': user['userid']
        }, {'last_message_time': 1}, comment='clear_data_res')
        
        if res:
            if (int(time()) - res['last_message_time']) // 86400 < 7:
                await dead_users.delete_one({
                    '_id': user['_id']
                }, comment='clear_data_1')


if __name__ != '__main__':
    if conf.active_tasks: 
        add_task(clear_data, 36000.0, 500.0)
        add_task(DeadUser_return, 36000.0, 100.0)