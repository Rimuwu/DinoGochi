from random import choice, choices, randint, random, shuffle
import time

from bot.dbmanager import mongo_client
from bot.const import GAME_SETTINGS
from bot.exec import main_router, bot
from bot.modules.data_format import (list_to_inline, list_to_keyboard,
                                     random_dict, seconds_to_str)
from bot.modules.dinosaur.dino_status import check_status
from bot.modules.dinosaur.dinosaur  import Dino, create_dino_connection, edited_stats, insert_dino, set_status
from bot.modules.dinosaur.rpg_states import add_state
from bot.modules.images import async_open, create_eggs_image
from bot.modules.images_save import send_SmartPhoto
from bot.modules.items.craft_recipe import craft_recipe
from bot.modules.items.item import (AddItemToUser, CalculateDowngradeitem,
                              CheckItemFromUser, EditItemFromUser,
                              RemoveItemFromUser, UseAutoRemove, counts_items,
                              get_data, get_item_dict, get_name, is_standart,
                              item_code)
from bot.modules.items.items_groups import get_group
from bot.modules.localization import get_data as get_loca_data
from bot.modules.localization import t
from bot.modules.logs import log
from bot.modules.markup import (cancel_markup, confirm_markup, count_markup,
                                feed_count_markup, markups_menu)
from bot.modules.dinosaur.mood import add_mood
from bot.modules.quests import quest_process
from bot.modules.states_tools import ChooseConfirmState, ChooseStepState
from bot.modules.get_state import get_state
from bot.modules.user.user import User, col_dinos, get_dead_dinos, max_dino_col, max_eat, count_inventory_items, award_premium
from typing import Optional, Union

from bson import ObjectId


from bot.modules.overwriting.DataCalsses import DBconstructor
dinosaurs = DBconstructor(mongo_client.dinosaur.dinosaurs)
dino_owners = DBconstructor(mongo_client.dinosaur.dino_owners)
items = DBconstructor(mongo_client.items.items)
dead_dinos = DBconstructor(mongo_client.dinosaur.dead_dinos)
users = DBconstructor(mongo_client.user.users)
long_activity = DBconstructor(mongo_client.dino_activity.long_activity)

async def exchange(return_data: dict, transmitted_data: dict):
    item = transmitted_data['item']
    friend = return_data['friend']
    count = return_data['count']
    userid = transmitted_data['userid']
    chatid = transmitted_data['chatid']
    lang = transmitted_data['lang']
    username = transmitted_data['username']

    item_type = get_data(item['item_id'])
    eat_count = await count_inventory_items(userid, ['eat'])

    if item_type == 'eat' and eat_count >= await max_eat(userid):
        await bot.send_message(chatid, t('max_friend_count', lang),
                            reply_markup=await markups_menu(userid, 'last_menu', lang))
    else:
        preabil = {}
        if 'abilities' in item: preabil = item['abilities']

        status = await RemoveItemFromUser(userid, item['item_id'], count, preabil)
        if status:
            await AddItemToUser(friend['userid'], item['item_id'], count, preabil)

            await bot.send_message(friend['userid'], t('exchange', lang, 
                                items=counts_items([item['item_id']]*count, lang),username=username))

            await bot.send_message(chatid, t('exchange_me', lang),
                                reply_markup=await markups_menu(userid, 'last_menu', lang))


async def exchange_item(userid: int, chatid: int, item: dict,
                        lang: str, username: str):
    items_data = await items.find({'items_data': item, 
                                   "owner_id": userid}, comment='exchange_item_items_data')
    max_count = 0

    for i in items_data: max_count += i['count']

    if items_data:
        item_name = get_name(item['item_id'], lang, item.get("abilities", {}))

        steps = [
            {"type": 'bool', "name": 'confirm', "data": {'cancel': True}, 
             'message': {'text': t('confirm_exchange', lang, name=item_name), 
                         'reply_markup': confirm_markup(lang)}},

            {"type": 'int', "name": 'count', "data": {
                "max_int": max_count, 'autoanswer': False}, 
            'message': {'text': t('css.wait_count', lang), 
                        'reply_markup': count_markup(max_count, lang)}},

            {"type": 'friend', 'name': 'friend', 'data': {'one_element': True},
             "message": None
             }
        ]

        transmitted_data = {'item': item, 'username': username}
        await ChooseStepState(exchange, userid, 
                                      chatid, lang, steps, transmitted_data)

async def use_item(userid: int, chatid: int, lang: str, item: dict, count: int=1, 
                   dino: Union[Dino, None]=None, delete: bool = True):
    """ Использование предмета

        delete - Принудительно не удалять предмет послле использования
    """
    return_text = ''
    dino_update_list = []
    use_status, send_status, use_baff_status = True, True, True

    item_id: str = item['item_id']
    data_item: dict = get_data(item_id)
    abilities = item.get("abilities", {})
    item_name: str = get_name(item_id, lang, abilities)
    type_item: str = data_item['type']

    if type_item == 'eat' and dino:

        if await dino.status == 'sleep':
            # Если динозавр спит, отменяем использование и говорим что он спит.
            return_text = t('item_use.eat.sleep', lang)
            use_status = False

        else:
            # Если динозавр не спит, то действует в соответсвии с класом предмета.
            if data_item['class'] == 'ALL' or (
                data_item['class'] == dino.data['class']):
                # Получаем конечную характеристику
                percent = 1
                age = await dino.age()
                if age.days >= 10:
                    percent, repeat = await dino.memory_percent('eat', item_id)
                    return_text = t(f'item_use.eat.repeat.m{repeat}', lang, percent=int(percent*100)) + '\n'

                    if repeat >= 3: await add_mood(dino._id, 'repeat_eat', -1, 900)

                dino.stats['eat'] = edited_stats(dino.stats['eat'], 
                                    int((data_item['act'] * count)*percent))

                # Определяем текст Выпил / Съел
                activ_text = t(f'item_use.eat.eat', lang)
                if 'drink' in data_item and data_item['drink']:
                    activ_text = t(f'item_use.eat.drink', lang)

                return_text += t('item_use.eat.great', lang,
                         item_name=item_name, eat_stat=dino.stats['eat'],
                         dino_name=dino.name, activ=activ_text
                         )
                await add_mood(dino._id, 'good_eat', 1, 900)

            else:
                # Если еда не соответствует классу, то убираем дполнительные бафы.
                use_baff_status = False
                loses_eat = randint(0, (data_item['act'] * count) // 2) * -1

                # Получаем конечную характеристики
                dino.stats['eat'] = edited_stats(dino.stats['eat'], loses_eat)

                return_text = t('item_use.eat.bad', lang, 
                                item_name=item_name, loses_eat=loses_eat,
                                dino_name=dino.name
                                )

                await add_mood(dino._id, 'bad_eat', -1, 1200)
            await quest_process(userid, 'feed', items=[item_id] * count)

    elif type_item in ['game', "journey", "collecting", "sleep", 'weapon', 'armor', 'backpack'] and dino:

        if await dino.status == type_item:
            # Запрещает менять активный предмет во время совпадающий с его типом активности
            return_text = t('item_use.accessory.no_change', lang)
            use_status = False
        else:

            if len(dino.activ_items) >= 5:
                # Превышено максимальное количество аксессуаров
                return_text = t('item_use.accessory.max_items', lang)
                use_status = False

            elif any(i['item_id'] == item['item_id'] for i in dino.activ_items):
                # Если предмет с таким item_id уже есть в activ_items
                return_text = t('item_use.accessory.already_have', lang)
                use_status = False

            elif is_standart(item):
                # Защита от вечных аксессуаров
                dino_update_list.append({
                    '$push': {f'activ_items': get_item_dict(item['item_id'])}})

                return_text = t('item_use.accessory.change', lang)
            else:
                dino_update_list.append({
                    '$push': {f'activ_items': item}})
                
                return_text = t('item_use.accessory.change', lang)

    elif type_item == 'recipe':
        send_status, use_status = False, False 
        # Проверка может завершится позднее завершения функции, отправим текст самостоятельно, так же юзер может и отказаться, удалим предмет сами

        await craft_recipe(userid, chatid, lang, item, count)

    elif data_item['type'] == 'case':
        send_status = False
        drop = data_item['drop_items']
        shuffle(drop)
        drop_items = {}

        col_repit = random_dict(data_item['col_repit'])
        for _ in range(count):
            for _ in range(col_repit):
                drop_item = None
                while drop_item == None:
                    for iterable_data in drop:
                        if iterable_data['chance'][1] == iterable_data['chance'][0] or randint(1, iterable_data['chance'][1]) <= iterable_data['chance'][0]:
                            drop_item = iterable_data.copy()

                            if isinstance(drop_item['id'], dict):
                                # В материалах указана группа
                                drop_item['id'] = choice(get_group(drop_item['id']['group']))

                            elif isinstance(drop_item['id'], list):
                                # В материалах указан список предметов которых можно использовать
                                drop_item['id'] = choice(drop_item['id'])

                            break

            drop_col = random_dict(drop_item['col'])
            if drop_item['id'] in drop_items:
                drop_items[drop_item['id']]['col'] += drop_col
            else: drop_items[drop_item['id']] = {
                "col": drop_col, "abilities": drop_item['abilities']}

        for item_id, data in drop_items.items():
            await AddItemToUser(userid, item_id, data['col'], data['abilities'])

            drop_item_data = get_data(item_id)
            item_name = get_name(item_id, lang, abilities)
            image = f"images/items/{drop_item_data['image']}.png"

            await send_SmartPhoto(userid, image, 
                t('item_use.case.drop_item', lang, 
                  item_name=item_name, col=data['col']), 
                'Markdown', await markups_menu(userid, 'last_menu', lang))

    elif data_item['type'] == 'egg':
        user = await User().create(userid)
        dino_limit_col = await user.max_dino_col()
        dino_limit = dino_limit_col['standart']  
        use_status = False

        if dino_limit['now'] < dino_limit['limit']:
            send_status = False
            buttons = {}
            image, eggs = await create_eggs_image()
            code = await item_code(item_dict=item, userid=userid)

            for i in range(3): buttons[f'🥚 {i+1}'] = f'item egg {code} {eggs[i]}'
            buttons = list_to_inline([buttons])

            await bot.send_photo(userid, image, 
                                 caption=t('item_use.egg.egg_answer', lang), 
                                 parse_mode='Markdown', reply_markup=buttons)
            await bot.send_message(userid, 
                                   t('item_use.egg.plug', lang),     
                                   reply_markup=await markups_menu(userid, 'last_menu', lang))
        else:
            return_text = t('item_use.egg.egg_limit', lang, 
                            limit=dino_limit['limit'])

    elif data_item['type'] == 'special':
        user = await User().create(userid)

        if data_item['class'] == 'defrosting' and dino:
            status = await check_status(dino._id)

            if status != 'inactive':
                use_status = False
                return_text = t('item_use.special.defrost.notinc', lang)

            else:
                return_text = t('item_use.special.defrost.ok', lang)
                await long_activity.delete_one(
                    {'dino_id': dino._id, 
                    'activity_type': 'inactive'}
                )

        elif data_item['class'] == 'freezing' and dino:
            status = await check_status(dino._id)
            if status == 'pass':

                if data_item['time'] == 'forever':
                    end = 0
                else:
                    end = data_item['time'] + int(time.time())

                data = {
                    'activity_type': 'inactive',
                    'dino_id': dino._id,
                    'time_end': end
                }

                await long_activity.insert_one(data)
                return_text = t('item_use.special.freez', lang)
            else:
                return_text = t('alredy_busy', lang)
                use_status = False

        elif data_item['class'] == 'premium':
            await award_premium(userid, data_item['premium_time'] * count)
            return_text = t('item_use.special.premium', lang, 
                            premium_time=seconds_to_str(data_item['premium_time'] * count, lang))

        elif data_item['class'] == 'reborn':
            dct_dino: dict = dino #type: ignore
            dino_limit_col = await user.max_dino_col()
            dino_limit = dino_limit_col['standart']  

            if dino_limit['now'] < dino_limit['limit']:
                res, alt_id = await insert_dino(userid, dct_dino['data_id'], 
                                          dct_dino['quality'])
                if res:
                    await dinosaurs.update_one({'_id': res.inserted_id}, 
                                               {'$set': {'name': dct_dino['name']}}, 
                                               comment='use_item_reborn')

                    if 'stats' in dct_dino:
                        for i in dct_dino['stats']:
                            await dinosaurs.update_one({'_id': res.inserted_id}, 
                                {'$set': {f'stats.{i}': 
                                    dct_dino['stats'][i]}}, 
                            comment='use_item_reborn_1')

                    await dead_dinos.delete_one({'_id': dct_dino['_id']}, comment='use_item_reborn') 
                    return_text = t('item_use.special.reborn.ok', lang, 
                            limit=dino_limit['limit'])
                else: use_status = False
            else:
                return_text = t('item_use.special.reborn.limit', lang, 
                            limit=dino_limit['limit'])
                use_status = False

        elif data_item['class'] == 'background':
            user = await users.find_one({"userid": userid}, comment='use_item_background')
            if user:
                if item['abilities']['data_id'] in user['saved']['backgrounds']:
                    use_status = False
                    return_text = t('backgrounds.in_st', lang)
                else:
                    await users.update_one({'userid': userid}, {'$push': {
                        'saved.backgrounds': item['abilities']['data_id']
                    }}, comment='use_item_background_1')

                return_text = t('backgrounds.add_to_storage', lang)

        elif data_item['class'] == 'transport':

            if abilities.get('data_id', 0) == 0:
                use_status = False

                if isinstance(dino, Dino):
                    await EditItemFromUser(userid, item, {
                        'item_id': item['item_id'],
                        'abilities': {
                            'data_id': dino.alt_id
                    }})

                    data = {
                        'activity_type': 'inactive',
                        'dino_id': dino._id,
                        'time_end': 0
                    }
                    await long_activity.delete_many({'dino_id': dino._id})
                    await long_activity.insert_one(data)
                    await dino_owners.delete_many({'dino_id': dino._id})

                    return_text = t('transport.add_dino', lang)

                else:
                    log(f'transport egg error {userid} {item} {dino}', lvl=3)
                    return_text = t('transport.error', lang)

            else:
                user = await User().create(userid)
                cuds = await user.get_col_dinos
                max_dc = await user.max_dino_col()
                max_dc_st = max_dc['standart']['limit']

                if cuds + 1 > max_dc_st:
                    use_status = False
                    return_text = t('transport.max_dino', lang)

                else:
                    alt_id = item['abilities']['data_id']
                    dino_dtc = await dinosaurs.find_one({'alt_id': alt_id}, comment='use_item_transport')
                    if dino_dtc:
                        dino_id = dino_dtc['_id']
                        use_status = True

                        await create_dino_connection(dino_id, userid)
                        await long_activity.delete_many(
                            {'dino_id': dino_id}
                        )
                        return_text = t('transport.delete_dino', lang)
                    else: 
                        use_status = False
                        return_text = t('transport.error', lang)

    if data_item.get('buffs', {}) and use_status and use_baff_status and dino:
        # Применяем бонусы от предметов
        return_text += '\n\n'

        for bonus in data_item['buffs']:
            if data_item['buffs'][bonus] > 0:
                bonus_name = '+' + bonus
            else: bonus_name = '-' + bonus

            dino.stats[bonus] = edited_stats(dino.stats[bonus], 
                         data_item['buffs'][bonus] * count)

            return_text += t(f'item_use.buff.{bonus_name}', lang, 
                            unit=data_item['buffs'][bonus] * count)

    if dino_update_list and dino:
        # Обновляем данные, не связанные с харрактеристиками, например активные предметы
        for i in dino_update_list: await dino.update(i)

    if data_item.get('sates', []) and use_status and use_baff_status and dino:
        # Применяем временные состояния

        for state in data_item['sates']:
            await add_state(dino._id, state['char'], state['unit'] * count, 
                            state['time'] * count)

    if dino and type(dino) == Dino:
        # Обновляем данные харрактеристик
        upd_values = {}
        dino_now = await Dino().create(dino._id)
        if dino_now:
            if dino_now.stats != dino.stats:
                for i in dino_now.stats:
                    if dino_now.stats[i] != dino.stats[i]:
                        upd_values['stats.'+i] = dino.stats[i] - dino_now.stats[i]

            if upd_values: await dino_now.update({'$inc': upd_values})

    if use_status and delete: await UseAutoRemove(userid, item, count)
    return send_status, return_text

async def adapter(return_data: dict, transmitted_data: dict):

    if 'confirm' in return_data: del return_data['confirm']
    userid = transmitted_data['userid']
    chatid = transmitted_data['chatid']
    lang = transmitted_data['lang']

    send_status, return_text = await use_item(userid, chatid, lang, transmitted_data['items_data'], **return_data)

    if send_status:
        await bot.send_message(chatid, return_text, parse_mode='Markdown', reply_markup=await markups_menu(userid, 'last_menu', lang))

async def pre_adapter(return_data: dict, transmitted_data: dict):
    return_data['dino'] = transmitted_data['dino']

    await adapter(return_data, transmitted_data)

async def eat_adapter(return_data: dict, transmitted_data: dict):
    dino: Dino = return_data['dino']
    transmitted_data['dino'] = dino
    lang = transmitted_data['lang']
    userid = transmitted_data['userid']
    chatid = transmitted_data['chatid']
    max_count = transmitted_data['max_count']

    item = transmitted_data['items_data']
    item_data = get_data(item['item_id'])
    item_name = get_name(item['item_id'], lang, item.get("abilities", {}))

    percent = 1
    age = await dino.age()
    if age.days >= 10:
        percent, repeat = await dino.memory_percent('games', item['item_id'], False)

    steps = [
        {"type": 'int', "name": 'count', "data": {"max_int": max_count}, 
         "translate_message": True,
            'message': {'text': 'css.wait_count', 
                        'reply_markup': feed_count_markup(
                            dino.stats['eat'], int(item_data['act'] * percent), max_count, item_name, lang)}}
            ]
    await ChooseStepState(pre_adapter, userid, chatid, lang, steps, 
                                transmitted_data=transmitted_data)

def book_page(book_id: str, page: int, lang: str):
    pages = get_loca_data(f'books.{book_id}', lang)
    name = get_name(book_id, lang)
    if page >= len(pages): page = 0
    elif page < 0: page = len(pages) - 1

    text = pages[page]
    text += f'\n\n{page+1} | {len(pages)}\n_{name}_'
    
    markup = list_to_inline(
        [{'◀': f'book {book_id} {page-1}', '▶': f'book {book_id} {page+1}'}, 
         {'🗑': 'delete_message'}]
    )
    return text, markup

async def data_for_use_item(item: dict, userid: int, chatid: int, lang: str, confirm: bool = True):
    item_id = item['item_id']
    data_item = get_data(item_id)
    type_item = data_item['type']
    limiter = 100 # Ограничение по количеству использований за раз
    adapter_function = adapter

    bases_item = await items.find({'owner_id': userid, 'items_data': item}, 
                                  comment='data_for_use_item_bases_item')
    transmitted_data = {'items_data': item}
    item_name = get_name(item_id, lang, item.get("abilities", {}))
    steps = []
    ok = True

    if not bases_item:
        await bot.send_message(chatid, t('item_use.no_item', lang))
    elif type(bases_item) is list:
        max_count = 0
        for base_item in bases_item:

            if 'abilities' in item.keys() and 'uses' in item['abilities']:
                max_count += base_item['count'] * base_item['items_data']['abilities']['uses']
            else: max_count += base_item['count']

        if max_count > limiter: max_count = limiter

        if type_item == 'eat':
            adapter_function = eat_adapter
            transmitted_data['max_count'] = max_count  # type: ignore

            steps = [
                {"type": 'dino', "name": 'dino', "data": {"add_egg": False}, 
                    'message': None}
            ]
        elif type_item in ['game', 'sleep', 
                           'journey', 'collecting', 
                           'weapon', 'backpack', 'armor']:
            steps = [
                {"type": 'dino', "name": 'dino', "data": {"add_egg": False}, 
                    'message': None}
            ]
        elif type_item == 'recipe':
            steps = [
                {"type": 'int', "name": 'count', "data": {"max_int": max_count}, 
                    'message': {'text': t('css.wait_count', lang), 
                                'reply_markup': count_markup(max_count, lang)}}
            ]
        elif type_item == 'weapon':
            steps = [
                {"type": 'dino', "name": 'dino', "data": {"add_egg": False}, 
                    'message': None}
            ]
        elif type_item == 'case':
            steps = [
                {"type": 'int', "name": 'count', "data": {"max_int": max_count}, 
                    'message': {'text': t('css.wait_count', lang), 
                                'reply_markup': count_markup(max_count, lang)}}
            ]
        elif type_item == 'egg':
            steps = []

        elif type_item == 'special':

            if data_item['class'] in ['transport']:

                if item['abilities']['data_id'] == 0:
                    steps = [{"type": 'dino', 
                            "name": 'dino', 
                            "data": {"add_egg": False, "all_dinos": False}, 
                            'message': t('css.inactive_dino', lang)
                    }]

            elif data_item['class'] in ['defrosting']:
                steps = [{"type": 'dino', 
                         "name": 'dino', 
                         "data": {"add_egg": False, "all_dinos": False}, 
                         'message': t('css.inactive_dino', lang)}]

            elif data_item['class'] in ['freezing']:
                steps = [{"type": 'dino', 
                         "name": 'dino', 
                         "data": {"add_egg": False, "all_dinos": False}, 
                         'message': None}]

            elif data_item['class'] in ['premium']:
                steps = [
                    {"type": 'int', "name": 'count', "data":
                        {"max_int": max_count}, 
                        'message': {
                            'text': t('css.wait_count', lang), 
                            'reply_markup': count_markup(max_count, lang)}}
                ]

            elif data_item['class'] in ['reborn']:
                dead = await get_dead_dinos(userid)
                options, markup = {}, []

                if dead:
                    a = 0
                    for i in dead:
                        a += 1
                        name = f'{a}🦕 {i["name"]}'
                        markup.append(name)
                        options[name] = i

                    markup.append([t('buttons_name.cancel', lang)])

                    steps = [
                        {"type": 'option', "name": 'dino', "data": 
                            {"options": options}, 
                            'message': {'text': t('css.dino', lang), 
                                        'reply_markup': list_to_keyboard(markup, 2)}}
                    ]

                else:
                    await bot.send_message(chatid, 
                                           t('item_use.special.reborn.no_dinos', lang))
                    return

            elif data_item['class'] in ['custom_book']:
                adapter_function = edit_custom_book
                steps = [
                    {"type": 'str', "name": 'content', "data":
                        {"max_len": 900}, 
                        'message': {
                            'text': t('css.content_str', lang, max_len=900), 
                            'reply_markup': cancel_markup(lang)}}
                ]
                transmitted_data['item_base_id'] = base_item['_id']

        elif type_item == 'book':
            text, markup = book_page(item_id, 0, lang)

            await bot.send_message(chatid, text, reply_markup=markup, parse_mode='Markdown')
            return
        else:
            ok = False
            await bot.send_message(chatid, t('item_use.cannot_be_used', lang))

        if ok:
            if confirm:
                steps.insert(0, {
                    "type": 'bool', "name": 'confirm', 
                    "data": {'cancel': True}, 
                    'message': {
                        'text': t('css.confirm', lang, name=item_name), 'reply_markup': confirm_markup(lang)
                        }
                    })

            await ChooseStepState(adapter_function, userid, chatid, 
                                  lang, steps, 
                                transmitted_data=transmitted_data)

async def delete_action(return_data: dict, transmitted_data: dict):
    userid = transmitted_data['userid']
    chatid = transmitted_data['chatid']
    lang = transmitted_data['lang']
    item = transmitted_data['items_data']
    count = return_data['count']
    item_name = transmitted_data['item_name']
    preabil = {}
    
    if 'abilities' in item: preabil = item['abilities']
    res = await RemoveItemFromUser(userid, item['item_id'], count, preabil)

    if res:
        await bot.send_message(chatid, t('delete_action.delete', lang,  
                                         name=item_name, count=count), 
                               reply_markup=
                               await markups_menu(userid, 'last_menu', lang))
    else:
        await bot.send_message(chatid, t('delete_action.error', lang), 
                               reply_markup=
                               await markups_menu(userid, 'last_menu', lang))
        

async def delete_item_action(userid: int, chatid:int, item: dict, lang: str):
    steps = []
    find_items = await items.find({'owner_id': userid, 
                             'items_data': item}, comment='delete_item_action')
    transmitted_data = {'items_data': item, 'item_name': ''}
    max_count = 0
    item_id = item['item_id']

    for base_item in find_items: max_count += base_item['count']

    if max_count:
        item_name = get_name(item_id, lang, item.get("abilities", {}))
        transmitted_data['item_name'] = item_name

        steps.append({"type": 'int', "name": 'count', 
                        "data": {"max_int": max_count}, 
                        'message': {'text': t('css.wait_count', lang), 
                                    'reply_markup': count_markup(max_count, lang)}}
        )
        steps.insert(0, {
                "type": 'bool', "name": 'confirm', 
                "data": {'cancel': True}, 
                'message': {
                    'text': t('css.delete', lang, name=item_name), 'reply_markup': confirm_markup(lang)
                    }
                })

        await ChooseStepState(delete_action, userid, chatid, lang, steps, 
                            transmitted_data=transmitted_data)
    else:
        await bot.send_message(chatid, t('delete_action.error', lang), 
                               reply_markup=
                               await markups_menu(userid, 'last_menu', lang))

rarity_chances = {
    "common": 50,
    "uncommon": 25,
    "rare": 15,
    "mystical": 9,
    "legendary": 1,
    "mythical": 0.1
}

def rare_random(items: list[str], count: int = 1, 
                chances_add: Optional[dict[str, int]] = None,
                special_chances: Optional[dict[str, int]] = None
                ) -> list[str]:
    """Функция выбирает случайные предметы из списка на основе их редкости.
       chances_add - словарь с шансами, которые нужно добавить к основным шансам
       special_chances - словарь с шансами, которые нужно использовать вместо основных для определённых предметов
    """

    if chances_add:
        # Добавляем шансы из переданного словаря
        # Если ключ уже существует, то изменяем его значение
        for key, value in chances_add.items():
            if key in rarity_chances:
                rarity_chances[key] += value
            else:
                rarity_chances[key] = value

    # Получаем данные о редкости предметов
    item_chances = []
    for item in items:
        rank = get_data(item)['rank']
        if special_chances and item in special_chances:
            # Используем специальные шансы, если они указаны для предмета
            item_chances.append(special_chances[item])
        else:
            # Используем стандартные шансы
            item_chances.append(rarity_chances[rank])

    # Нормализуем шансы
    total_chance = sum(item_chances)
    weights = [chance / total_chance for chance in item_chances]

    # Выбираем случайные предметы
    shuffle(items)
    selected_items = choices(items, weights=weights, k=count)
    return selected_items

rarity_to_int = {
    "common": 0, "uncommon": 1, 
    "rare": 2, "mystical": 3,
    "legendary": 4, "mythical": 5
}

def sort_f(item_id: str):
    """ Функция сортирует список с id предметов по их редкости
    """
    dt = get_data(item_id)
    return rarity_to_int[dt['rank']]

def rare_sort(items: list[str]):
    """ Функция сортирует список с id предметов по их редкости. От обычного к легендарному
    """

    new_list = items.copy()
    new_list.sort(key=lambda x: sort_f(x))

    return new_list

def add_to_rare_sort(items: list[str], item_id: str):
    new_list = items.copy()
    
    dt = get_data(item_id)
    if not dt: return items

    rarity = rarity_to_int[dt['rank']]
    for i, item in enumerate(new_list):
        if rarity_to_int[get_data(item)['rank']] >= rarity:
            new_list.insert(i, item_id)
            break

    return new_list


async def edit_custom_book(return_data: dict, transmitted_data: dict):
    """ Функция редактирует кастомную книгу
    """
    userid = transmitted_data['userid']
    chatid = transmitted_data['chatid']
    lang = transmitted_data['lang']

    item = transmitted_data['items_data']

    transmitted_data['content'] = return_data['content']

    await ChooseConfirmState(
        edit_custom_book_confirm, userid, chatid, lang, True, transmitted_data=transmitted_data,
    )
    await bot.send_message(chatid, t('custom_book.confirm_edit', lang),
                           reply_markup=confirm_markup(lang))

async def edit_custom_book_confirm(_: bool, transmitted_data: dict):
    """ Функция редактирует кастомную книгу
    """
    userid = transmitted_data['userid']
    chatid = transmitted_data['chatid']
    lang = transmitted_data['lang']

    item_base_id = transmitted_data['item_base_id']
    content = transmitted_data['content']

    await items.update_one({'_id': item_base_id}, {'$set': {
        'items_data.abilities.content': content,
        'items_data.abilities.author': userid,
    }}, comment='edit_custom_book_confirm')

    await bot.send_message(chatid, '✅', 
            reply_markup=await markups_menu(userid, 'last_menu', lang))