from datetime import datetime, timezone
from random import choice, randint, choices, random
from time import time

from bot.config import conf
from bot.dbmanager import mongo_client
from bot.exec import main_router, bot
from bot.modules.localization import get_data, t
from bot.modules.logs import log
from bot.modules.quests import create_quest, quest_resampling, save_quest
from bot.taskmanager import add_task
 

from bot.modules.overwriting.DataCalsses import DBconstructor
users = DBconstructor(mongo_client.user.users)
tavern = DBconstructor(mongo_client.tavern.tavern)
quests_data = DBconstructor(mongo_client.tavern.quests)
daily_data = DBconstructor(mongo_client.tavern.daily_award)

async def tavern_quest(user):
    free_quests = await quests_data.find(
        {'owner_id': 0}, {'_id': 1}, comment='tavern_quest_free_quests')
    lang = user['lang']

    if await quests_data.count_documents({'owner_id': user['userid']}, comment='tavern_quest_12') < 5:
        if free_quests and random() <= 0.3:
            ran_quest = choice(free_quests)
            free_quests.remove(ran_quest)

            quest_id = ran_quest['_id']

            # Попытка исправиль оишбку ERROR tavern_life task_error: 'time_end'
            if 'time_end' in ran_quest:
                new_time = ran_quest['time_end'] - ran_quest['time_start']
                await quests_data.update_one({'_id': quest_id}, {"$set": {
                    'owner_id': user['userid'], 
                    'time_start': int(time()), 
                    'end_time': int(time()) + new_time}}, comment='tavern_quest_1')

                text = t('quest.resаmpling', lang)

        else:
            compl = choices([2, 1], [0.25, 0.5])[0]

            quest = create_quest(compl, lang=lang)
            await save_quest(quest, user['userid'])
            text = t('quest.new', lang)

        try: await bot.send_message(user['userid'], text)
        except: pass

async def tavern_replic(user):
    names = get_data('quests.authors', user['lang'])

    if names:
        random_name = choice(names)
        if type(random_name) == dict:
            random_name = random_name['name']
        random_replic = choice(get_data('tavern_dialogs', user['lang']))

        text = f'👤 {random_name}: {random_replic}'
        try:
            await bot.send_message(user['userid'], text)
        except Exception: pass

async def tavern_life():
    in_tavern = await tavern.find({}, comment='tavern_life_in_tavern')

    for user in in_tavern:
        if user['time_in'] + 3600 <= int(time()):
            await tavern.delete_one({'_id': user['_id']}, comment='tavern_life_1')
            try:
                await bot.send_message(user['userid'], 
                        t('tavern_sleep', user['lang']))
            except: pass

        elif random() <= 0.1: await tavern_replic(user)
        elif random() <= 0.1: await tavern_quest(user)

async def quest_managment():
    quests = await quests_data.find({}, comment='quest_managment')

    for quest in quests:
        time_end = quest['time_end']
        delta = datetime.fromtimestamp(int(time()), tz=timezone.utc) - datetime.fromtimestamp(time_end, tz=timezone.utc)

        if delta.days >= 14 and quest['owner_id'] == 0:
            await quests_data.delete_one({'_id': quest['_id']}, comment='quest_managment_1')

        elif int(time()) >= quest['time_end']:
            await quest_resampling(quest['_id'])

async def daily_award_old():
    data = await daily_data.find(
        {'time_end': {'$lte': int(time())}}, comment='daily_award_old_data')
    for i in list(data): await daily_data.delete_one({'_id': i['_id']}, comment='daily_award_old_1')

# async def daily_award_notif():
#     users_ids = await users.find({"last_message_time": {'$gte': int(time()) - 86400 * 7}}, 
#                         {'userid': 1, 'settings': 1})

#     for uid in users_ids:
#         if not await daily_data.find_one({'owner_id': uid['userid']}):
#             if uid['settings']['notifications']:
#                 await user_notification(uid['userid'], 'daily_award')
#                 await sleep(0.5)

if __name__ != '__main__':
    if conf.active_tasks:
        # add_task(daily_award_notif, 36000.0, 10800.0)
        add_task(daily_award_old, 7200.0, 1.0)
        add_task(tavern_life, 180.0, 10.0)
        add_task(quest_managment, 240.0, 10.0)