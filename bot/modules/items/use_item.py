


from random import choice, randint
import time
from typing import Optional, Union

from bson import ObjectId

from bot.modules.data_format import list_to_inline, list_to_keyboard, random_dict, seconds_to_str
from bot.modules.dinosaur.dino_status import check_status
from bot.modules.dinosaur.mood import add_mood
from bot.modules.dinosaur.rpg_states import add_state
from bot.modules.images import create_eggs_image
from bot.modules.images_save import send_SmartPhoto
from bot.modules.items.custom_book import book_page, edit_custom_book
from bot.modules.items.item import AddItemToUser, Eat, EditItemFromUser, ItemData
from bot.modules.dinosaur.dinosaur import Dino, create_dino_connection, edited_stats, insert_dino
from bot.modules.items.item import ItemInBase
from bot.modules.items.items_groups import get_group
from bot.modules.items.json_item import Armor, Backpack, Case, Collecting, Game, Journey, NullItem, Recipe, Sleep, Special, Weapon
from bot.modules.items.json_item import Egg as EggItem
from bot.modules.localization import t
from bot.modules.logs import log
from bot.modules.markup import cancel_markup, confirm_markup, count_markup, feed_count_markup, markups_menu
from bot.modules.quests import quest_process
from bot.modules.items.craft_recipe import craft_recipe
from bot.modules.states_fabric.state_handlers import ChooseStepHandler, MongoValueType
from bot.modules.states_fabric.steps_datatype import ConfirmStepData, DataType, DinoStepData, IntStepData, OptionStepData, StepMessage, StringStepData
from bot.modules.user.user import User, award_premium, get_dead_dinos
from bot.exec import bot
from bot.modules.egg import Egg

from bot.dbmanager import mongo_client
from bot.modules.overwriting.DataCalsses import DBconstructor

incubation = DBconstructor(mongo_client.items.incubation)
long_activity = DBconstructor(mongo_client.dinosaur.long_activity)
dead_dinos = DBconstructor(mongo_client.dinosaur.dead_dinos)
dinosaurs = DBconstructor(mongo_client.dinosaur.dinosaurs)
users = DBconstructor(mongo_client.user.users)
dino_owners = DBconstructor(mongo_client.dinosaur.dino_owners)
subscriptions = DBconstructor(mongo_client.user.subscriptions)

async def use_item(
        chatid: int, 
        lang: str, item: ItemInBase | ObjectId, 
        count: int = 1, 
        dino: Optional[Union[ObjectId, Dino]] = None, 
        **kwargs
    ):
    """ Использование предмета

        delete - Принудительно не удалять предмет послле использования
    """

    return_text = ''
    use_status, send_status, use_baff_status = True, True, True

    if isinstance(item, ObjectId):
        item_base_id = item

        item = ItemInBase()
        await item.link_for_id(item_base_id)

    if isinstance(dino, ObjectId):
        dino = await Dino().create(dino)

    data_item = item.items_data.data
    userid = item.owner_id

    if isinstance(data_item, Eat) and dino:

        return_text, use_status, use_baff_status, send_status = await EatItem(
            item, userid, data_item, dino, lang, count)

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

    elif isinstance(data_item, Recipe):
        use_status, send_status, use_baff_status = False, False, False
        # Проверка может завершится позднее завершения функции, отправим текст самостоятельно, так же юзер может и отказаться, удалим предмет сами

        await craft_recipe(userid, chatid, lang, item, count)

    elif isinstance(data_item, Case):
        use_status, send_status, use_baff_status = True, False, True

        # Использование кейса
        await CaseItem(userid, chatid, data_item, lang, count)

    elif isinstance(data_item, EggItem):

        return_text, use_status, send_status = await EggItem_use(
            userid, lang, data_item, item)

    elif isinstance(data_item, Special):
        reborn_id = kwargs.get('reborn_id', None)

        return_text, use_status, send_status = await SpecialItem(
            userid, dino, item, data_item, lang, count, reborn_id
        )

    if data_item.buffs and use_status and use_baff_status and dino:
        # Применяем бонусы от предметов
        return_text += '\n\n'

        for bonus in data_item.buffs:
            if data_item.buffs[bonus] > 0:
                bonus_name = '+' + bonus
            else: bonus_name = '-' + bonus

            dino.stats[bonus] = edited_stats(dino.stats[bonus], 
                         data_item.buffs[bonus] * count)

            return_text += t(f'item_use.buff.{bonus_name}', lang, 
                            unit=data_item.buffs[bonus] * count)

    # if dino_update_list and dino:
    #     # Обновляем данные, не связанные с харрактеристиками, например активные предметы
    #     for i in dino_update_list: await dino.update(i)

    if data_item.states and use_status and use_baff_status and dino:
        # Применяем временные состояния

        for state in data_item.states:
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

    if use_status: await item.UsesRemove(count)
    return send_status, return_text

# UseItem Eat
async def EatItem(item: ItemInBase, userid: int,
                  data_item: Eat, dino: Dino, lang: str, count: int
                  ):
    use_status, send_status = True, True
    return_text = ''

    item_name = item.items_data.name(lang=lang)
    item_id = item.item_id

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

    return return_text, use_status, use_baff_status, send_status

async def CaseItem(userid: int, chatid: int,
                  data_item: Case, lang: str, count: int):

    drop: list = data_item.drop_items

    drop = drop[::-1]
    drop_items = {}

    col_repit = random_dict(data_item.col_repit)
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
        drop_item = ItemData(item_id=item_id, abilities=data['abilities'])
        await AddItemToUser(userid, drop_item, data['col'])

        item_name = drop_item.name(lang=lang)
        image = f"images/items/{drop_item.data.image}.png"

        await send_SmartPhoto(chatid, image, 
            t('item_use.case.drop_item', lang, 
                item_name=item_name, col=data['col']), 
            'Markdown', await markups_menu(userid, 'last_menu', lang))


async def EggItem_use(userid: int, lang: str, data_item: EggItem,
                      item: ItemInBase
                      ):
    use_status, send_status = True, True

    return_text = ''
    user = await User().create(userid)
    dino_limit_col = await user.max_dino_col()

    dino_limit = dino_limit_col['standart']  

    if dino_limit['now'] < dino_limit['limit']:
        send_status = False
        buttons = {}

        res_egg_choose = await incubation.find_one({'owner_id': userid, 
                                        'stage': 'choosing',
                                        'quality': data_item.inc_type })

        if not res_egg_choose:
            egg_data = Egg()
            egg_data.stage = 'choosing'
            egg_data.owner_id = userid
            egg_data.quality = data_item.inc_type
            egg_data.choose_eggs()

        else:
            egg_data = Egg()
            egg_data.__dict__.update(res_egg_choose)

            if egg_data.id_message:
                try:
                    await bot.delete_message(userid, egg_data.id_message)
                except Exception as e: pass

        image = await create_eggs_image(egg_data.eggs)
        code = item.code()

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
        use_status = False
        return_text = t('item_use.egg.egg_limit', lang, 
                        limit=dino_limit['limit'])

    return return_text, use_status, send_status

async def SpecialItem(userid: int,
                      dino: Optional[Dino],
                      item: ItemInBase,
                      data_item: Special, lang: str, count: int,
                      reborn_id: Optional[ObjectId] = None):
    """ Использование специальных предметов """
    use_status, send_status = True, True
    return_text = ''

    user = await User().create(userid)

    if data_item.item_class == 'defrosting' and dino:
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

    elif data_item.item_class == 'freezing' and dino:
        status = await check_status(dino._id)
        if status == 'pass':

            if data_item.time == 'forever':
                end = 0
            elif isinstance(data_item.time, int):
                end = data_item.time + int(time.time())

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

    elif data_item.item_class == 'premium':
        await award_premium(userid, data_item.premium_time * count)

        return_text = t('item_use.special.premium', lang, 
                        premium_time=seconds_to_str(data_item.premium_time * count, lang))

    elif data_item.item_class == 'reborn':

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

    elif data_item.item_class == 'background':

        if user:
            dat_id = item.items_data.abilities['data_id']
            if dat_id in user.saved['backgrounds']:
                use_status = False
                return_text = t('backgrounds.in_st', lang)

            else:
                await users.update_one({'userid': userid}, {'$push': {
                    'saved.backgrounds': dat_id
                }}, comment='use_item_background_1')

            return_text = t('backgrounds.add_to_storage', lang)

    elif data_item.item_class == 'dino_slot':
        use_status = False
        return_text = t('item_use.special.error_slot', lang)

        col_add = item.items_data.abilities.get('count', 1) * count
        type_add = item.items_data.abilities.get('slot_type', 'dino')
        if user:
            if type_add == 'dino':
                await user.update({'$inc': {'add_slots': col_add}})

                use_status = True
                return_text = t('item_use.special.add_slot', lang)

    elif data_item.item_class == 'transport':

        if item.items_data.abilities.get('data_id', 0) == 0:
            use_status = False

            if isinstance(dino, Dino):
                new_data = item.items_data.copy()
                new_data.abilities['data_id'] = dino.alt_id

                await EditItemFromUser(userid, 'home', None,
                                       item.items_data, new_data
                                       )

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
                alt_id = item.items_data.abilities['data_id']
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

    return return_text, use_status, send_status

# Подготовка данных для использования предмета
async def adapter(return_data: dict, transmitted_data: dict):

    if 'confirm' in return_data: del return_data['confirm']
    userid = transmitted_data['userid']
    chatid = transmitted_data['chatid']
    lang = transmitted_data['lang']

    send_status, return_text = await use_item(chatid, lang, 
                                              transmitted_data['item_id'], **return_data)

    if send_status:
        await bot.send_message(chatid, return_text, parse_mode='Markdown', reply_markup=await markups_menu(userid, 'last_menu', lang))

async def pre_adapter(return_data: dict, transmitted_data: dict):
    return_data['dino'] = transmitted_data['dino']
    await adapter(return_data, transmitted_data)

# Подготовка для кормёжки
async def eat_adapter(return_data: dict, transmitted_data: dict):
    dino_id = return_data['dino']
    transmitted_data['dino'] = dino_id

    lang = transmitted_data['lang']
    userid = transmitted_data['userid']
    chatid = transmitted_data['chatid']
    max_count = transmitted_data['max_count']

    item_base_id = transmitted_data['item_id']
    item = await ItemInBase().link_for_id(item_base_id)
    if not isinstance(item.items_data.data, Eat): return

    dino = await Dino().create(dino_id)
    if not dino:
        await bot.send_message(chatid, t('css.no_dino', lang), reply_markup=await markups_menu(userid, 'last_menu', lang))
        return

    percent = 1
    age = await dino.age()
    if age.days >= 10:
        percent, repeat = await dino.memory_percent('games', item.item_id, False)

    steps: list[DataType] = [
        IntStepData('count', StepMessage(
            text='css.wait_count',
            translate_message=True,
            markup=feed_count_markup(
                dino.stats['eat'], int(item.items_data.data.act * percent),
                    max_count, item.items_data.name(lang), lang)),
            max_int=max_count
        )
    ]

    await ChooseStepHandler(pre_adapter, userid, chatid, lang, steps,
                            transmitted_data=transmitted_data).start()


async def data_for_use_item(
    item_id: ObjectId,
    userid: int, chatid: int, lang: str
    ):

    item = await ItemInBase().link_for_id(item_id)

    limiter = 1000 # Ограничение по количеству использований за раз
    adapter_function = adapter
    type_item = item.items_data.data

    transmitted_data: dict[str, MongoValueType] = {'item_id': item_id}
    item_name = item.items_data.name(lang=lang)
    steps: list[DataType] = []
    ok = True

    if not item.link_with_real_item:
        await bot.send_message(chatid, t('item_use.no_item', lang))

    else:
        if item.items_data.abilities.get('uses', 1) > 1:
            max_count = item.count * item.items_data.abilities['uses']
        else: max_count = item.count

        if max_count > limiter: max_count = limiter

        if isinstance(type_item, Eat):
            adapter_function = eat_adapter
            transmitted_data['max_count'] = max_count

            steps += [
                DinoStepData('dino', None,
                    add_egg=False, all_dinos=True
                )
            ]
        elif isinstance(type_item, (Game, Journey, Collecting, Sleep, Weapon, Armor, Backpack)):
            steps += [
                DinoStepData('dino', None,
                    add_egg=False, all_dinos=True
                )
            ]
        elif isinstance(type_item, Recipe):
            steps = [
                IntStepData('count', StepMessage(
                    text='css.wait_count',
                    translate_message=True,
                    markup=count_markup(max_count, lang)),
                    max_int=max_count
                )
            ]
        elif isinstance(type_item, Weapon):
            steps += [
                DinoStepData('dino', None,
                    add_egg=False, all_dinos=True
                )
            ]
        elif isinstance(type_item, Case):
            steps = [
                IntStepData('count', StepMessage(
                    text='css.wait_count',
                    translate_message=True,
                    markup=count_markup(max_count, lang)),
                    max_int=max_count
                )
            ]
        elif isinstance(type_item, Egg):
            steps = []

        elif isinstance(type_item, Special):

            if type_item.item_class == 'transport':

                if item.items_data.abilities['data_id'] == 0:
                    steps += [
                        DinoStepData('dino', None,
                            add_egg=False, all_dinos=False
                        )
                    ]

            elif type_item.item_class == 'defrosting':
                steps += [
                    DinoStepData('dino', None,
                                 message_key='css.inactive_dino',
                            add_egg=False, all_dinos=False
                        )
                ]

            elif type_item.item_class == 'freezing':
                steps += [
                    DinoStepData('dino', None,
                            add_egg=False, all_dinos=False
                        )
                    ]

            elif type_item.item_class == 'premium':
                res = await subscriptions.find_one({'userid': userid}, comment='premium_res')

                if res: 
                    if res['sub_end'] == 'inf':
                        await bot.send_message(chatid, t('item_use.special.infinity_premium', lang), 
                                               reply_markup=await markups_menu(userid, 'last_menu', lang))
                        return

                steps = [
                    IntStepData('count', StepMessage(
                        text='css.wait_count',
                        translate_message=True,
                        markup=count_markup(max_count, lang)),
                        max_int=max_count
                    )
                ]

            elif type_item.item_class == 'dino_slot':
                user = await User().create(userid)
                if user and user.add_slots >= 20 or user.add_slots + max_count > 20:
                    await bot.send_message(chatid, t('item_use.special.max_slots', lang), 
                                               reply_markup=await markups_menu(userid, 'last_menu', lang))
                    return

                steps = []

            elif type_item.item_class == 'reborn':
                dead = await get_dead_dinos(userid)
                options, markup = {}, []

                if dead:
                    a = 0
                    for i in dead:
                        a += 1
                        name = f'{a}🦕 {i["name"]}'
                        markup.append(name)
                        options[name] = i['_id']

                    markup.append([t('buttons_name.cancel', lang)])

                    steps = [
                        OptionStepData('reborn_data', StepMessage(
                            text=t('css.dino', lang),
                            markup=list_to_keyboard(markup, 2)),
                            options=options
                        )
                    ]

                else:
                    await bot.send_message(chatid, 
                                           t('item_use.special.reborn.no_dinos', lang), 
                                           reply_markup=await markups_menu(userid, 'last_menu', lang))
                    return

            elif type_item.item_class == 'custom_book':
                adapter_function = edit_custom_book
                steps = [
                    StringStepData('content', StepMessage(
                        text=t('css.content_str', lang, max_len=900),
                        translate_message=False,
                        markup=cancel_markup(lang)),
                        max_len=900
                    )
                ]

        elif type_item == 'book':
            text, markup = book_page(item.item_id, 0, lang)

            await bot.send_message(chatid, text, reply_markup=markup, parse_mode='Markdown')
            return
        else:
            ok = False
            await bot.send_message(chatid, t('item_use.cannot_be_used', lang))

        if ok:
            steps.insert(0, 
                ConfirmStepData('confirm', StepMessage(
                    text=t('css.confirm', lang, name=item_name),
                    translate_message=False,
                    markup=confirm_markup(lang))
                )
            )

            await ChooseStepHandler(adapter_function, userid, chatid, 
                                    lang, steps, 
                                    transmitted_data=transmitted_data).start()