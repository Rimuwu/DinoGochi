


from random import randint
from typing import Optional, Union

from bson import ObjectId

from bot.modules.dinosaur.mood import add_mood
from bot.modules.items.items import Eat
from bot.modules.dinosaur.dinosaur import Dino, edited_stats
from bot.modules.items.items import ItemInBase
from bot.modules.items.json_item import Armor, Backpack, Collecting, Game, Journey, NullItem, Sleep, Weapon
from bot.modules.localization import t
from bot.modules.quests import quest_process
from bot.modules.items.craft_recipe import craft_recipe


async def use_item(
        userid: int, chatid: int, 
        lang: str, item: ItemInBase | ObjectId, count: int=1, 
        dino: Optional[Union[ObjectId, Dino]] = None, 
        delete: bool = True, **kwargs
    ):
    """ Использование предмета

        delete - Принудительно не удалять предмет послле использования
    """

    return_text = ''
    dino_update_list = []
    use_status, send_status, use_baff_status = True, True, True

    if isinstance(item, ObjectId):
        item_base_id = item

        item = ItemInBase()
        await item.link_for_id(item_base_id)

    if isinstance(dino, ObjectId):
        dino_id = dino
        dino = await Dino().create(dino)

    item_id: str = item.item_id
    data_item = item.items_data.data
    abilities: dict = item.items_data.abilities
    item_name: str = item.items_data.name(lang=lang)
    type_item: str = item.items_data.data.type

    if isinstance(data_item, Eat) and dino:

        if await dino.status == 'sleep':
            # Если динозавр спит, отменяем использование и говорим что он спит.
            return_text = t('item_use.eat.sleep', lang)
            use_status = False

        else:
            # Если динозавр не спит, то действует в соответсвии с класом предмета.
            if data_item.item_class == 'ALL' or (
                data_item.item_class == dino.data['class']):
                # Получаем конечную характеристику
                percent = 1

                age = await dino.age()
                if age.days >= 10:
                    percent, repeat = await dino.memory_percent('eat', item_id)
                    return_text = t(f'item_use.eat.repeat.m{repeat}', lang, percent=int(percent*100)) + '\n'

                    if repeat >= 3: await add_mood(dino._id, 'repeat_eat', -1, 900)

                dino.stats['eat'] = edited_stats(dino.stats['eat'], 
                                    int((data_item.act * count)*percent))

                # Определяем текст Выпил / Съел
                activ_text = t(f'item_use.eat.eat', lang)
                if data_item.drink:
                    activ_text = t(f'item_use.eat.drink', lang)

                return_text += t('item_use.eat.great', lang,
                         item_name=item_name, eat_stat=dino.stats['eat'],
                         dino_name=dino.name, activ=activ_text
                         )
                await add_mood(dino._id, 'good_eat', 1, 900)

            else:
                # Если еда не соответствует классу, то убираем дполнительные бафы.
                use_baff_status = False
                loses_eat = randint(0, (data_item.act * count) // 2) * -1

                # Получаем конечную характеристики
                dino.stats['eat'] = edited_stats(dino.stats['eat'], loses_eat)

                return_text = t('item_use.eat.bad', lang, 
                                item_name=item_name, loses_eat=loses_eat,
                                dino_name=dino.name
                                )

                await add_mood(dino._id, 'bad_eat', -1, 1200)
            await quest_process(userid, 'feed', items=[item_id] * count)

    elif isinstance(data_item, (Game, Journey, Collecting, Sleep, Weapon, Armor, Backpack)) and dino:
        
        pass

        # if await dino.status == type_item:
        #     # Запрещает менять активный предмет во время совпадающий с его типом активности
        #     return_text = t('item_use.accessory.no_change', lang)
        #     use_status = False
        # else:

        #     if len(dino.activ_items) >= 5:
        #         # Превышено максимальное количество аксессуаров
        #         return_text = t('item_use.accessory.max_items', lang)
        #         use_status = False

        #     elif any(i['item_id'] == item.item_id for i in dino.activ_items):
        #         # Если предмет с таким item_id уже есть в activ_items
        #         return_text = t('item_use.accessory.already_have', lang)
        #         use_status = False

        #     elif item:
        #         # Защита от вечных аксессуаров
        #         dino_update_list.append({
        #             '$push': {f'activ_items': get_item_dict(item['item_id'])}})

        #         return_text = t('item_use.accessory.change', lang)
        #     else:
        #         dino_update_list.append({
        #             '$push': {f'activ_items': item}})
                
        #         return_text = t('item_use.accessory.change', lang)

    elif type_item == 'recipe':
        send_status, use_status = False, False 
        # Проверка может завершится позднее завершения функции, отправим текст самостоятельно, так же юзер может и отказаться, удалим предмет сами

        await craft_recipe(userid, chatid, lang, item, count)

    elif data_item['type'] == 'case':
        send_status = False
        drop: list = data_item['drop_items']

        drop = drop[::-1]
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
            if 'image' in drop_item_data:
                image = f"images/items/{drop_item_data['image']}.png"
            else:
                print(drop_item_data)
                image = f"images/items/null.png"

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

            res_egg_choose = await incubation.find_one({'owner_id': userid, 
                                           'stage': 'choosing',
                                           'quality': data_item['inc_type'] })

            if not res_egg_choose:
                egg_data = Egg()
                egg_data.stage = 'choosing'
                egg_data.owner_id = userid
                egg_data.quality = data_item['inc_type']
                egg_data.choose_eggs()

            else:
                egg_data = Egg()
                egg_data.__dict__.update(res_egg_choose)

                if egg_data.id_message:
                    try:
                        await bot.delete_message(userid, egg_data.id_message)
                    except Exception as e: pass

            image = await create_eggs_image(egg_data.eggs)
            code = await item_code(item_dict=item, userid=userid)

            btn = {
                t('item_use.egg.edit_buttons', lang):  f'item egg_edit {code}'
            }

            for i in range(3): 
                buttons[f'🥚 {i+1}'] = f'item egg {code} {egg_data.eggs[i]}'
            buttons = list_to_inline([btn, buttons])

            mes = await bot.send_photo(userid, image, 
                                 caption=t('item_use.egg.egg_answer', lang), 
                                 parse_mode='Markdown', reply_markup=buttons)

            egg_data.id_message = mes.message_id
            egg_data.start_choosing = int(time.time())

            if not res_egg_choose: await egg_data.insert()

            await bot.send_message(userid, 
                                   t('item_use.egg.plug', lang),     
                                   reply_markup=await markups_menu(userid, 'last_menu', lang))
        else:
            return_text = t('item_use.egg.egg_limit', lang, 
                            limit=dino_limit['limit'])

    elif data_item['type'] == 'special':
        user = await User().create(userid)

        if data_item['item_class'] == 'defrosting' and dino:
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

        elif data_item['item_class'] == 'freezing' and dino:
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

        elif data_item['item_class'] == 'premium':
            await award_premium(userid, data_item['premium_time'] * count)
            return_text = t('item_use.special.premium', lang, 
                            premium_time=seconds_to_str(data_item['premium_time'] * count, lang))

        elif data_item['item_class'] == 'reborn':
            reborn_id = kwargs.get('reborn_data', None)
            dct_dino = await dead_dinos.find_one({'_id': reborn_id}, comment='use_item_reborn')
            if dct_dino:

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
            else: use_status = False

        elif data_item['item_class'] == 'background':
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

        elif data_item['item_class'] == 'dino_slot':
            use_status = False
            return_text = t('item_use.special.error_slot', lang)
            user = await User().create(userid)

            col_add = abilities.get('count', 1) * count
            type_add = abilities.get('slot_type', 'dino')
            if user:
                if type_add == 'dino':
                    await user.update({'$inc': {'add_slots': col_add}})

                    use_status = True
                    return_text = t('item_use.special.add_slot', lang)

        elif data_item['item_class'] == 'transport':

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

                    if user.settings['last_dino'] == dino._id:
                        await users.update_one({'userid': userid}, {
                            '$set': {'settings.last_dino': None}}, comment='use_item_transport_1')

                    await dino_owners.delete_many({'dino_id': dino._id})

                    return_text = t('transport.add_dino', lang)

                else:
                    log(f'transport egg error {userid} {item} {dino}', lvl=3)
                    return_text = t('transport.error', lang)

            else:
                user = await User().create(userid)
                max_dc = await user.max_dino_col()

                cuds = max_dc['standart']['now']
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