from random import randint, shuffle

from bot.config import mongo_client
from bot.const import GAME_SETTINGS
from bot.exec import bot
from bot.modules.data_format import (list_to_inline, list_to_keyboard,
                                     random_dict, seconds_to_str)
from bot.modules.dinosaur.dinosaur  import Dino, edited_stats, insert_dino
from bot.modules.images import async_open, create_eggs_image
from bot.modules.items.craft_recipe import craft_recipe
from bot.modules.items.item import (AddItemToUser, CalculateDowngradeitem,
                              CheckItemFromUser, EditItemFromUser,
                              RemoveItemFromUser, UseAutoRemove, counts_items,
                              get_data, get_item_dict, get_name, is_standart,
                              item_code)
from bot.modules.localization import get_data as get_loca_data
from bot.modules.localization import t
from bot.modules.markup import (confirm_markup, count_markup,
                                feed_count_markup, markups_menu)
from bot.modules.dinosaur.mood import add_mood
from bot.modules.quests import quest_process
from bot.modules.states_tools import ChooseStepState
from bot.modules.user.user import User, get_dead_dinos, max_eat, count_inventory_items, award_premium
from typing import Union


from bot.modules.overwriting.DataCalsses import DBconstructor
dinosaurs = DBconstructor(mongo_client.dinosaur.dinosaurs)
items = DBconstructor(mongo_client.items.items)
dead_dinos = DBconstructor(mongo_client.dinosaur.dead_dinos)
users = DBconstructor(mongo_client.user.users)


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
            await AddItemToUser(friend.id, item['item_id'], count, preabil)

            await bot.send_message(friend.id, t('exchange', lang, 
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

# async def end_craft(transmitted_data: dict):
#     """ Завершает крафт удаляя и создавая предметы
#     """
#     materials = transmitted_data['materials']
#     userid = transmitted_data['userid']
#     chatid = transmitted_data['chatid']
#     data_item = transmitted_data['data_item']
#     delete_item = transmitted_data['delete_item']
#     count = transmitted_data['count']
#     lang = transmitted_data['lang']

#     # Удаление рецепта
#     await UseAutoRemove(userid, delete_item, count)

#     # Удаление материалов
#     inv = []
#     for iteriable_item in materials['delete']:
#         if iteriable_item not in inv:
#             item_id = iteriable_item['item_id']

#             col = materials['delete'].count(iteriable_item)
#             inv.append(iteriable_item)

#             await RemoveItemFromUser(userid, item_id, col)

#     # Добавление предметов
#     for create_data in data_item['create']:
#         if create_data['type'] == 'create':
#             preabil = create_data.get('abilities', {}) # Берёт характеристики если они есть
#             await AddItemToUser(userid, create_data['item'], count, preabil)

#     # Вычисление опыта за крафт
#     if 'rank' in data_item.keys():
#         xp = GAME_SETTINGS['xp_craft'][data_item['rank']] * count
#     else:
#         xp = GAME_SETTINGS['xp_craft']['common'] * count

#     # Начисление опыта за крафт
#     await experience_enhancement(userid, xp)

#     # Создание сообщения
#     created_items = []
#     for i in data_item['create']:
#         created_items.append(i['item'])

#     await bot.send_message(chatid, t('item_use.recipe.create', lang, 
#                                      items=counts_items(created_items*count, lang)), 
#                            parse_mode='Markdown', reply_markup=await markups_menu(userid, 'last_menu', lang))

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
            if dino.activ_items[type_item]:
                await AddItemToUser(userid, 
                              dino.activ_items[type_item]['item_id'], 1,  #type: ignore
                              dino.activ_items[type_item]['abilities'])  #type: ignore
            if is_standart(item):
                # Защита от вечных аксессуаров
                dino_update_list.append({
                    '$set': {f'activ_items.{type_item}': get_item_dict(item['item_id'])}})
            else:
                dino_update_list.append({
                    '$set': {f'activ_items.{type_item}': item}})
            
            return_text = t('item_use.accessory.change', lang)

    elif type_item == 'recipe':
        send_status, use_status = False, False 
        # Проверка может завершится позднее завершения функции, отправим текст самостоятельно, так же юзер может и отказаться, удалим предмет сами

        await craft_recipe(userid, chatid, lang, item, count)

        # for iterable_item in data_item['materials']:
        #     iterable_id: str = iterable_item['item']

        #     if iterable_item['type'] == 'delete':
        #         materials['delete'].append(get_item_dict(
        #             iterable_id))

        #     elif iterable_item['type'] == 'endurance':
        #         if 'endurance' not in materials['edit']:
        #             materials['edit']['endurance'] = {}
        #         materials['edit']['endurance'][iterable_id] = iterable_item['act'] * count

        # materials['delete'] = materials['delete'] * count
        # deleted_items, not_enough_items = {}, []

        # for iterable_item in materials['delete']:
        #     iter_id = iterable_item['item_id']
        #     if iter_id not in deleted_items and iter_id not in not_enough_items:
        #         ret_data_f = await CheckItemFromUser(userid, iterable_item, 
        #                             materials['delete'].count(iterable_item))
        #         if ret_data_f['status']:
        #             deleted_items[iter_id] = materials['delete'].count(iterable_item)
        #         else:
        #             not_enough_items += [iter_id] * ret_data_f["difference"]

        # if not not_enough_items:
        #     if materials['edit']:
        #         steps = []
        #         transmitted_data = {
        #                 'count': count, 
        #                 'materials': materials,
        #                 'data_item': data_item,
        #                 'delete_item': item
        #             }

        #         for iterable_key in materials['edit']:
        #             for iterable_id in materials['edit'][iterable_key]:
        #                 steps.append(
        #                     {
        #                         "type": 'inv', "name": iterable_id, "data":
        #                         {
        #                             'item_filter': [iterable_id], 
        #                             'changing_filters': False,
        #                         },
        #                         "translate_message": True,
        #                         'message': 'item_use.recipe.consumable_item',
        #                     }
        #                 )
        #         await ChooseStepState(edit_craft, userid, 
        #                               chatid, lang, steps, transmitted_data)
        #     else:
        #         transmitted_data = {
        #             'userid': userid,
        #             'chatid': chatid,
        #             'lang': lang,
        #             'materials': materials,
        #             'count': count,
        #             'data_item': data_item,
        #             'delete_item': item
        #         }
        #         await end_craft(transmitted_data)
        # else:
        #     use_status, send_status = False, True
        #     return_text = t('item_use.recipe.not_enough_m', lang, materials=counts_items(not_enough_items, lang))

    elif data_item['type'] == 'case':
        send_status = False
        drop = data_item['drop_items']
        shuffle(drop)
        drop_items = {}

        col_repit = random_dict(data_item['col_repit'])
        for _ in range(col_repit):
            drop_item = None
            while drop_item == None:
                for iterable_data in drop:
                    if randint(1, iterable_data['chance'][1]) <= iterable_data['chance'][0]:
                        drop_item = iterable_data
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
            image = await async_open(f"images/items/{drop_item_data['image']}.png", True)

            await bot.send_photo(userid, image, 
                                    t('item_use.case.drop_item', lang, item_name=item_name, col=data['col']), 
                                    parse_mode='Markdown', reply_markup=
                                    await markups_menu(userid, 'last_menu', lang))

    elif data_item['type'] == 'egg':
        user = await User().create(userid)
        dino_limit_col = await user.max_dino_col()
        dino_limit = dino_limit_col['standart']  
        use_status = False

        if dino_limit['now'] < dino_limit['limit']:
            send_status = False
            buttons = {}
            image, eggs = await create_eggs_image()
            code = item_code(item)

            for i in range(3): buttons[f'🥚 {i+1}'] = f'item egg {code} {eggs[i]}'
            buttons = list_to_inline([buttons])

            await bot.send_photo(userid, image, 
                                 t('item_use.egg.egg_answer', lang), 
                                 parse_mode='Markdown', reply_markup=buttons)
            await bot.send_message(userid, 
                                   t('item_use.egg.plug', lang),     
                                   reply_markup=await markups_menu(userid, 'last_menu', lang))
        else:
            return_text = t('item_use.egg.egg_limit', lang, 
                            limit=dino_limit['limit'])

    elif data_item['type'] == 'special':
        user = await User().create(userid)
        dct_dino: dict = dino #type: ignore

        if data_item['class'] == 'premium':
            await award_premium(userid, data_item['premium_time'] * count)
            return_text = t('item_use.special.premium', lang, 
                            premium_time=seconds_to_str(data_item['premium_time'] * count, lang))

        elif data_item['class'] == 'reborn':
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
                        await dinosaurs.update_one({'_id': res.inserted_id}, 
                                               {'$set': {'stats': dct_dino}}, 
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

    if data_item.get('buffs', []) and use_status and use_baff_status and dino:
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

    if dino and type(dino) == Dino:
        # Обновляем данные харрактеристик
        upd_values = {}
        dino_now: Dino = await Dino().create(dino._id)
        if dino_now.stats != dino.stats:
            for i in dino_now.stats:
                if dino_now.stats[i] != dino.stats[i]:
                    upd_values['stats.'+i] = dino.stats[i] - dino_now.stats[i]

        if upd_values: await dino_now.update({'$inc': upd_values})

    if use_status and delete: await UseAutoRemove(userid, item, count)
    return send_status, return_text

# async def edit_craft(return_data: dict, transmitted_data: dict):
#     materials = transmitted_data['materials']
#     userid = transmitted_data['userid']
#     chatid = transmitted_data['chatid']
#     lang = transmitted_data['lang']
#     items_data = []
#     ok = True

#     for iterable_key in materials['edit']:
#         for item_key, unit in materials['edit'][iterable_key].items():
#             item = return_data[item_key]
#             find_items = await items.find({'owner_id': userid, 
#                                    'items_data': item}, comment='edit_craft_find_items')
#             for find_item in find_items:
#                 if unit > 0:
#                     ret_data = CalculateDowngradeitem(find_item['items_data'], 
#                                                       iterable_key, unit)
#                     items_data.append({"data": ret_data, 'old_item': item})
#                     unit = ret_data['ost']
#                 else: break
#             if unit > 0: 
#                 ok = False
#                 break
#         if not ok: break

#     if not ok:
#         iterable_data = items_data[0]
#         item_name = get_name(iterable_data['old_item']['item_id'], lang)

#         await bot.send_message(chatid, 
#             t('item_use.recipe.enough_characteristics', lang, item_name=item_name), 
#             parse_mode='Markdown', 
#             reply_markup=await markups_menu(userid, 'last_menu', lang))

#     if ok:
#         for iterable_data in items_data.copy(): 
#             iterable_item = iterable_data['old_item']

#             if iterable_data['data']['status'] == 'remove':
#                 await RemoveItemFromUser(userid, iterable_item['item_id'], 1,
#                                    iterable_item['abilities'])
#             elif iterable_data['data']['status'] == 'edit':
#                 await EditItemFromUser(userid, iterable_item, iterable_data['data']['item'])

#         await end_craft(transmitted_data)



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

            if data_item['class'] in ['freezing', 'defrosting']:
                ...
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