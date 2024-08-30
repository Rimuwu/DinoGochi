from random import choice, randint
from time import time

from bson.objectid import ObjectId

from bot.config import mongo_client
from bot.const import  QUESTS
from bot.modules.data_format import (list_to_inline, random_code, random_dict,
seconds_to_str)
from bot.modules.items.item import counts_items, get_name, RemoveItemFromUser
from bot.modules.localization import get_data, t
from bot.modules.items.collect_items import get_all_items

from bot.modules.overwriting.DataCalsses import DBconstructor
quests_data = DBconstructor(mongo_client.tavern.quests)
items = DBconstructor(mongo_client.items.items)

ITEMS = get_all_items()

complex_time = {
    1: {"min": 36000, "max": 57600, "type": "random"},
    2: {"min": 86400, "max": 172800, "type": "random"},
    3: {"min": 259200, "max": 432000, "type": "random"},
    4: {"min": 604800, "max": 864000, "type": "random"},
    5: {"min": 864000, "max": 1209600, "type": "random"},
}

EAT_DATA = {}

def save_eat_items():
    eat_data = {}

    for key, item in ITEMS.items():
        if item['type'] == 'eat':
            if item['rank'] in eat_data:
                eat_data[item['rank']].append(key)
            else:
                eat_data[item['rank']] = [key]
    return eat_data

def create_quest(complexity: int, qtype: str='', lang: str = 'en'):
    """ Создание данных для квеста
        complexity - [1, 5]
    """
    quests = []
    assert 1 <= complexity <= 5, f"1 <= {complexity} <= 5"

    if not qtype:
        types = ['feed', 'collecting', 'fishing', 'journey', 'game', 'get', 'hunt']
        # 'kill', 
        qtype = choice(types)

    for quest in QUESTS:
        if quest['type'] == qtype and quest['complexity'] == complexity:
            quests.append(quest)

    if quests:
        quest_data, count = choice(quests), 0
        coins_one = random_dict(quest_data['reward']['coins'])

        quest = {
            'reward': {'coins': 0, 'items': []},
            'complexity': complexity,
            'type': qtype,
            'data': {}
        }

        if qtype == 'get':
            quest['data']['items'] = []
            col_items = random_dict(quest_data['data']['count'])
            for _ in range(col_items):
                quest['data']['items'].append(choice(quest_data['data']['items']))

        elif qtype in ['journey', 'game']:
            quest['data']['minutes'] = [random_dict(quest_data['data']['minutes']), 0]

        elif qtype in ['fishing', 'collecting', 'hunt']:
            count = random_dict(quest_data['data']['count'])
            quest['data']['count'] = [count, 0]

        elif qtype == 'feed':
            count = random_dict(quest_data['data']['count'])
            eat_rank = random_dict(quest_data['data']['eat_rare'])
            data_items = {}

            temp_count = count
            while temp_count > 0:
                if temp_count != 1:
                    n = randint(1, temp_count)
                else: n = 1
                temp_count -= n
                random_item = choice(EAT_DATA[eat_rank])

                data_items[random_item] = [n, 0]

            quest['data']['items'] = data_items

        if count:
            coins = coins_one * count
        else: coins = coins_one

        quest['reward']['coins'] = coins

        authors = get_data('quests.authors', lang)
        quest['author'] = choice(authors)

        names = get_data(f'quests.{qtype}', lang)
        quest['name'] = choice(names)

        quest['time_end'] = int(time()) + random_dict(complex_time[complexity])
        quest['time_start'] = int(time())

        return quest
    else: return {}

def quest_ui(quest: dict, lang: str, quest_id: str=''):
    """ Генерация текста и клавиатуры о квесте
    """
    text = ''

    name = quest["name"]
    author = quest["author"]
    text += t('quest.had', lang, 
              name=name, author=author) + '\n\n'
    complexity = t('quest.comp_element', lang) * quest['complexity']
    text += t('quest.complexity', lang, complexity=complexity) + '\n'

    qtype = t(f'quest.types.{quest["type"]}', lang)
    text += t('quest.type', lang, qtype=qtype) + '\n\n'

    if quest['type'] == 'get':
        items_list = counts_items(quest['data']['items'], lang)
        text += t('quest.get', lang, items_list=items_list)

    elif quest['type'] == 'game':
        minutes, now = quest['data']['minutes']
        text += t('quest.game', lang, min=minutes, now=now)

    elif quest['type'] == 'journey':
        minutes, now = quest['data']['minutes']
        text += t('quest.journey', lang, min=minutes, now=now)

    elif quest['type'] == 'feed':
        eat_list = ''
        for ikey, ivalue in quest['data']['items'].items():
            eat_list += f'{get_name(ikey, lang, ivalue.get("abilities", {}))}: {ivalue[1]} / {ivalue[0]}\n'
        text += t('quest.feed', lang, eat_list=eat_list)[:-1]

    elif quest['type'] == 'collecting':
        cmax, now = quest['data']['count']
        text += t('quest.collecting', lang, max=cmax, now=now)

    elif quest['type'] == 'fishing':
        cmax, now = quest['data']['count']
        text += t('quest.fishing', lang, max=cmax, now=now)

    elif quest['type'] == 'hunt':
        cmax, now = quest['data']['count']
        text += t('quest.hunt', lang, max=cmax, now=now)

    text += '\n\n' + t('quest.reward.had', lang) + '\n'
    if quest['reward']['coins']:
        text += t('quest.reward.coins', lang, coins=quest['reward']['coins'])
    if quest['reward']['items']:
        text = counts_items(quest['reward']['items'], lang)

    time_end = quest['time_end'] - int(time())
    text += '\n\n' + t('quest.time_end', lang, time_end=seconds_to_str(time_end, lang))

    buttons = {}
    if quest_id:
        tb: dict = get_data('quest.buttons', lang)
        for key, value in tb.items():
            buttons[value] = key + ' ' + quest_id

    markup = list_to_inline([buttons], 2)
    return text, markup

async def save_quest(quest: dict, owner_id: int): 
    """ Сохраняет квест в базе
    """
    async def generation_code():
        code = random_code(10)
        if await quests_data.find_one({'alt_id': code}, comment='save_quest'):
            code = generation_code()
        return code

    quest['alt_id'] = await generation_code()
    quest['owner_id'] = owner_id

    await quests_data.insert_one(quest, comment='save_quest')
    return quest['alt_id']

async def quest_resampling(questid: ObjectId):
    """ Убирает владельца квеста, тем самым предоставляя квест для распределния на новых участников
    """
    await quests_data.update_one({'_id': questid}, {'$set': {'owner_id': 0}}, comment='quest_resampling')

async def quest_process(userid: int, quest_type: str, unit: int = 0, items: list = []):
    """ Заносит данные в квест
    """
    quests = await quests_data.find({"owner_id": userid, 
                                     'type': quest_type}, comment='quest_process_quests')

    for quest in quests:
        if quest_type in ['journey', 'game']:
            minuts = quest['data']['minutes']
            if unit + minuts[1] > minuts[0]:
                plus = minuts[0] - minuts[1]
            else: plus = unit

            if plus:
                await quests_data.update_one({'_id': quest['_id']}, 
                                             {"$inc": {'data.minutes.1': plus}}, comment='quest_process_1')

        elif quest_type in ['fishing', 'collecting', 'hunt']:
            count = quest['data']['count']
            if unit + count[1] > count[0]:
                plus = count[0] - count[1]
            else: plus = unit
            if plus:
                await quests_data.update_one({'_id': quest['_id']}, 
                                       {"$inc": {'data.count.1': plus+1}}, comment='quest_process_2')

        elif quest_type == 'feed':
            for i in items:
                if i in quest['data']['items']:
                    if quest['data']['items'][i][1] < quest['data']['items'][i][0]:
                        await quests_data.update_one({'_id': quest['_id']}, 
                                               {"$inc": {f'data.items.{i}.1': 1}}, comment='quest_process_3')

async def check_quest(quest: dict):
    """ Проверяет квест на выполнение, если тип квеста "get" то в случае выполнения удалит предметы
    """
    if quest['type'] == 'get': 
        count_items = {}

        # Сортируем для запроса
        for i in quest['data']['items']:
            if i in count_items:
                count_items[i] += 1
            else: count_items[i] = 1

        # Проверяем на наличие
        for key, value in count_items.items():
            result = await items.find(
                {"items_data.item_id": key, "owner_id": quest['owner_id']}, comment='check_quest_result')

            if not result: return False
            else:
                max_count = 0
                for i in result: max_count += i['count']
                if value > max_count: return False

        # Удаляем предметы
        for key, value in count_items.items():
            await RemoveItemFromUser(quest['owner_id'], key, value)
        return True
    
    elif quest['type'] in ['journey', 'game']:
        minuts = quest['data']['minutes']
        if minuts[1] >= minuts[0]: return True
        return False

    elif quest['type'] == 'feed':
        for key, value in quest['data']['items'].items():
            if value[0] > value[1]: return False
        return True

    elif quest['type'] in ['fishing', 'collecting', 'hunt']:
        count = quest['data']['count']
        if count[1] >= count[0]: return True
        return False

EAT_DATA = save_eat_items()