from bot.modules.overwriting.DataCalsses import LazyCollection, RawLazyCollection
from bot.models.dinosaur import Dino
from bot.models.user import User
from bot.models.items import Item
from bot.models.group import Group
from bot.models.other import Statistic
from bot.models.activity import Kindergarten
# Чеки, обновляющие информацию о рейтинге или количестве объектов в базе
# Дабы не собирать информацию каждый раз при запросе пользователя
from bot.config import conf
from bot.dbmanager import mongo_client
from bot.modules.donation import get_history
from bot.taskmanager import add_task
from datetime import datetime
from bot.modules.user.user import max_lvl_xp
from time import time
from bot.modules.notifications import user_notification
from bot.models.dinosaur import Dino
from bot.redismanager import redis_set


from collections import defaultdict
dinosaurs = LazyCollection(Dino)
users = LazyCollection(User)
items = LazyCollection(Item)
groups = LazyCollection(Group)
statistic = LazyCollection(Statistic)
kindergarten = LazyCollection(Kindergarten)

# Чек статистики, запускать раз в час
async def statistic_check():
    items_len = await items.count_documents({}, comment='statistic_check_items_len')
    users_len = await users.count_documents({}, comment='statistic_check_users_len')
    dinosaurs_len = await dinosaurs.count_documents({}, comment='statistic_check_dinosaurs_len')
    groups_len = await groups.count_documents({}, comment='statistic_check_groups_len')

    data = {
        'date': str(datetime.now().date()),
        'dinosaurs': dinosaurs_len,
        'users': users_len,
        'items': items_len,
        'groups': groups_len
    }
    if res := await statistic.find_one({'date': data['date']}, comment='statistic_check_res'):
        await statistic.delete_one({'_id': res['_id']}, comment='statistic_check_2')

    await statistic.insert_one(data, comment='statistic_check_1')

def calculate_donations(history):
    user_amounts = defaultdict(int)
    for entry in history:
        user_amounts[entry['userid']] += entry['amount']
    return sorted(
        [{'userid': uid, 'amount': amount} for uid, amount in user_amounts.items()],
        key=lambda x: x['amount'],
        reverse=True
    )

async def rayting_check():
    collection = User.get_settings().pymongo_collection

    # 1. Рейтинг по монетам (топ-1000)
    coins_cursor = collection.find(
        {}, 
        {'userid': 1, 'coins': 1}, 
        comment='rayting_check_coins_opt'
    ).sort([('coins', -1)]).limit(1000)
    coins_list = await coins_cursor.to_list(length=1000)
    coins_ids = [user['userid'] for user in coins_list]

    # 2. Рейтинг по уровням (топ-1000)
    lvl_cursor = collection.find(
        {}, 
        {'userid': 1, 'lvl': 1, 'xp': 1}, 
        comment='rayting_check_lvl_opt'
    ).sort([('lvl', -1), ('xp', -1)]).limit(1000)
    lvl_list = await lvl_cursor.to_list(length=1000)
    lvl_ids = [user['userid'] for user in lvl_list]

    # 3. Рейтинг по супер-монетам (топ-1000)
    super_cursor = collection.find(
        {}, 
        {'userid': 1, 'super_coins': 1}, 
        comment='rayting_check_super_opt'
    ).sort([('super_coins', -1)]).limit(1000)
    super_list = await super_cursor.to_list(length=1000)
    super_ids = [user['userid'] for user in super_list]
    
    await redis_set('rayting:coins', {'data': coins_list, 'ids': coins_ids})
    await redis_set('rayting:lvl', {'data': lvl_list, 'ids': lvl_ids})
    await redis_set('rayting:super', {'data': super_list, 'ids': super_ids})

    # Обновление рейтинга донатов 
    history_all = await get_history()
    history_30 = await get_history(30)

    donat_all_list = calculate_donations(history_all)[:1000]
    donat_30_list = calculate_donations(history_30)[:1000]

    donat_all_ids = [i['userid'] for i in donat_all_list]
    donat_30_ids = [i['userid'] for i in donat_30_list]

    await redis_set('rayting:dontaion_all', {'data': donat_all_list, 'ids': donat_all_ids})
    await redis_set('rayting:dontaion_30d', {'data': donat_30_list, 'ids': donat_30_ids})
    
    await redis_set('rayting:update_time', {'time': int(time())})


async def kindergarten_update():
    data = list(await kindergarten.find({'type': 'save',
                                   'end': {'$lte': int(time())}}, comment='kindergarten_update')
                ).copy()

    for i in data: await kindergarten.delete_one({'_id': i['_id']}, comment='kindergarten_update_1')

async def dino_kindergarten():
    data = list(await kindergarten.find({'type': 'dino',
                                   'end': {'$lte': int(time())}}, comment='dino_kindergarten_data')
                ).copy()

    for i in data: 
        from bot.models.enums import DinoStatus
        await Dino.set_status(i['dinoid'], DinoStatus.PASS)
        await kindergarten.delete_one({'_id': i['_id']}, comment='dino_kindergarten_1')

        dino = await dinosaurs.find_one({'_id': i['dinoid']}, 
                                        comment='dino_kindergarten_dino')
        if dino:
            owner = await Dino.get_owner_by_id(i['dinoid'])
            if owner:
                lang = await Dino.get_language(i['dinoid'])
                await user_notification(owner.owner_id, 'kindergarten', lang, 
                                dino_name=dino['name'], 
                                dino_alt_id_markup=dino['alt_id'])

async def dino_statistic():
    upd_data = {}
    dinos = list(await dinosaurs.find({}, 
                    {'data_id': 1}, 
                    comment='dino_statistic_dinosaurs'
                    ))

    for i in dinos:
        data_id = i['data_id']
        upd_data[str(data_id)] = upd_data.get(str(data_id), 0) + 1

    await redis_set('dino:statistic', {'data': upd_data, 'all_count': len(dinos)})


if __name__ != '__main__':
    if conf.active_tasks:
        add_task(rayting_check, 3600, 15.0)
        add_task(statistic_check, 3600, 30.0)
        add_task(dino_kindergarten, 1800, 15.0)
        add_task(kindergarten_update, 43200, 30.0)
        add_task(dino_statistic, 7200, 60.0)