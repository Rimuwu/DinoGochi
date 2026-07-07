
from bot.models.user import Subscription
from bot.models.dinosaur import State, DinoMood, DeadDino, Dino, DinoOwners, Egg
from bot.models.items import Item
from bot.models.user import User
from bot.models.activity import Activity
from random import choices, shuffle

from bot.exec import bot
from bot.modules.data_format import (list_to_inline, list_to_keyboard,
                                     random_dict, seconds_to_str)

from bot.models.dinosaur import Dino, DinoOwners, Egg
from bot.modules.images import create_eggs_image
from bot.modules.images_save import send_SmartPhoto
from bot.modules.items.craft_recipe import craft_recipe
from bot.modules.items.item import (AddItemToUser, EditItemFromUser,
                              RemoveItemFromUser, UseAutoRemove, counts_items,
                              get_data, get_item_dict, get_name, is_standart,
                              item_code)
from bot.modules.items.items_groups import get_group
from bot.modules.localization import get_data as get_loca_data
from bot.modules.localization import t
from bot.modules.logs import log
from bot.modules.markup import (cancel_markup, confirm_markup, count_markup,
                                feed_count_markup, markups_menu)
from bot.modules.quests import quest_process
from bot.modules.states_fabric.state_handlers import ChooseConfirmHandler, ChooseStepHandler
from bot.modules.states_fabric.steps_datatype import ConfirmStepData, DataType, DinoStepData, FriendStepData, IntStepData, OptionStepData, StepMessage, StringStepData, MultiInventoryStepData
from bot.modules.user.user import max_eat, count_inventory_items
from typing import Optional, Union

from bson import ObjectId


async def confirm_exchange_callback(st: str, transmitted_data: dict):
    from bot.modules.get_state import get_state
    chatid = transmitted_data['chatid']
    userid = transmitted_data['userid']
    lang = transmitted_data['lang']
    chosen_items = transmitted_data['chosen_items']
    friend = transmitted_data['friend']
    username = transmitted_data['username']

    message_data = transmitted_data['temp']['message_data']

    state = await get_state(userid, chatid)
    await state.clear()

    try:
        await bot.delete_message(chatid, message_data.message_id)
    except:
        pass

    if st == 'yes':
        from bot.modules.items.item import transfer_item
        success_items = []
        for chosen_item in chosen_items:
            preabil = chosen_item.get('abilities', {})
            status = await transfer_item(userid, friend['userid'], chosen_item['item_id'], chosen_item['count'], preabil)
            if status:
                success_items.append(chosen_item)

        if success_items:
            names = [get_name(i['item_id'], lang, i.get('abilities', {})) + f" x{i['count']}" for i in success_items]
            items_text = ", ".join(names)
            
            try:
                await bot.send_message(friend['userid'], t('exchange', lang, 
                                    items=items_text, username=username))
            except:
                pass

            if chatid == userid:
                await bot.send_message(chatid, t('exchange_me', lang),
                                    reply_markup=await markups_menu(userid, 'last_menu', lang))
            else:
                # В группе отправляем обычное сообщение
                await bot.send_message(chatid, t('group_transfer.items_answer_yes', lang, user_name=friend['name']).format(user_name=friend['name']))
    else:
        if chatid == userid:
            await bot.send_message(chatid, t('group_transfer.items_answer_no', lang, default='❌ Передача предметов отменена.'),
                                   reply_markup=await markups_menu(userid, 'last_menu', lang))
        else:
            await bot.send_message(chatid, t('group_transfer.items_answer_no', lang, default='❌ Передача предметов отменена.'))


async def exchange(return_data: dict, transmitted_data: dict):
    from bot.modules.states_fabric.state_handlers import ChooseInlineHandler
    from bot.modules.data_format import random_code
    from aiogram.utils.keyboard import InlineKeyboardBuilder
    from aiogram.types import InlineKeyboardButton

    chosen_items = return_data['items']
    friend = return_data['friend']
    userid = transmitted_data['userid']
    chatid = transmitted_data['chatid']
    lang = transmitted_data['lang']
    username = transmitted_data['username']

    # Сначала проверяем, выбрано ли хоть что-то
    if not chosen_items:
        await bot.send_message(chatid, t('inventory.no_select', lang))
        return

    # Формируем список предметов для сообщения подтверждения
    names = [get_name(i['item_id'], lang, i.get('abilities', {})) + f" x{i['count']}" for i in chosen_items]
    items_text = "\n".join([f"• {n}" for n in names])

    confirm_text = t('confirm_exchange_question', lang, name=friend['name']).format(name=friend['name']) + f"\n\n{items_text}"

    custom_code = random_code()

    builder = InlineKeyboardBuilder()
    builder.button(text=t('buttons_name.yes', lang, default='✅ Да'), callback_data=f"chooseinline {custom_code} yes", style="danger")
    builder.button(text=t('buttons_name.no', lang, default='❌ Нет'), callback_data=f"chooseinline {custom_code} no")
    builder.adjust(2)

    await ChooseInlineHandler(
        confirm_exchange_callback,
        userid, chatid,
        lang, custom_code,
        {
            "chosen_items": chosen_items,
            "friend": friend,
            "username": username,
            "userid": userid,
            "chatid": chatid,
            "lang": lang
        }
    ).start()

    await bot.send_message(chatid, confirm_text, parse_mode='Markdown', reply_markup=builder.as_markup())


async def exchange_item(userid: int, chatid: int, item: dict,
                        lang: str, username: str):
    # Retrieve all user items to populate the inventory selection
    inventory, _ = await User.get_inventory(userid, [])
    
    steps = [
        MultiInventoryStepData('items', StepMessage(
            text=t('confirm_exchange', lang, name=""),
            translate_message=False,
        ), inventory=inventory),
        FriendStepData('friend', None,
            one_element=True
        )
    ]

    transmitted_data = {'username': username}
    await ChooseStepHandler(exchange, userid, 
                            chatid, lang, steps,
                            transmitted_data).start()

async def use_item(userid: int, chatid: int, lang: str, item: dict, count: int=1, 
                   dino: Optional[Union[ObjectId, Dino]] = None, delete: bool = True,
                   **kwargs):
    """ Использование предмета

        delete - Принудительно не удалять предмет после использования
    """
    from bot.models.items import Item
    from bot.models.dinosaur import Dino

    # Check if item is stored in the database or transient
    abilities = item.get('abilities', {})
    from bot.modules.items.item import get_item_dict
    item_dict = get_item_dict(item['item_id'], abilities)
    if not abilities:
        item_doc = await Item.find_one({
            'owner_id': userid,
            'items_data.item_id': item['item_id'],
            '$or': [
                {'items_data.abilities': {'$exists': False}},
                {'items_data.abilities': {}}
            ]
        })
    else:
        item_doc = await Item.find_one(Item.owner_id == userid, Item.items_data == item_dict)
    if not item_doc:
        # Transient item
        item_doc = Item(owner_id=str(userid), items_data=item, count=count)

    if isinstance(dino, str) and ObjectId.is_valid(dino):
        dino = ObjectId(dino)

    if isinstance(dino, ObjectId):
        dino = await Dino.find_one(Dino.id == dino)

    return_text, use_status = await item_doc.use_item(userid, chatid, lang, count, dino, **kwargs)

    if use_status and delete:
        await UseAutoRemove(userid, item, count)

    send_status = bool(return_text)
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
    dino_id = return_data['dino']
    transmitted_data['dino'] = dino_id

    lang = transmitted_data['lang']
    userid = transmitted_data['userid']
    chatid = transmitted_data['chatid']
    max_count = transmitted_data['max_count']

    item = transmitted_data['items_data']
    item_data = get_data(item['item_id'])
    item_name = get_name(item['item_id'], lang, item.get("abilities", {}))
    
    dino = await Dino().create(dino_id)
    if not dino:
        await bot.send_message(chatid, t('css.no_dino', lang), reply_markup=await markups_menu(userid, 'last_menu', lang))
        return

    percent = 1
    age = await dino.age()
    if age.days >= 10:
        percent, repeat = await dino.memory_percent('eat', item['item_id'], False)

    steps = [
        IntStepData('count', StepMessage(
            text='css.wait_count',
            translate_message=True,
            markup=feed_count_markup(
                dino.stats['eat'], int(item_data['act'] * percent), max_count, item_name, lang)),
            max_int=max_count
        )
    ]

    await ChooseStepHandler(pre_adapter, userid, chatid, lang, steps,
                            transmitted_data=transmitted_data).start()

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


async def training_boost_use_adapter(return_data: dict, transmitted_data: dict):
    """Применяет бустер тренировки к активной тренировке последнего динозавра пользователя."""
    from bot.models.activity import Activity
    from time import time as _time

    lang = transmitted_data['lang']
    userid = transmitted_data['userid']
    chatid = transmitted_data['chatid']
    item = transmitted_data['items_data']

    user_dino_ids = await _get_user_dino_ids(userid)
    if not user_dino_ids:
        await bot.send_message(chatid, t('css.no_dino', lang),
                               reply_markup=await markups_menu(userid, 'last_menu', lang))
        return

    activity_type = item.get('activity_type', '')
    activity = await Activity.find_one(
        Activity.dino.id.is_in(user_dino_ids),
        Activity.activity_type == activity_type
    )

    if not activity:
        await bot.send_message(chatid,
            t('all_skills.training_boost.not_training', lang,
              default=f'❌ Динозавр не находится в тренировке ({activity_type})!'),
            reply_markup=await markups_menu(userid, 'last_menu', lang))
        return

    preabil = item.get('abilities', {})
    removed = await RemoveItemFromUser(userid, item['item_id'], 1, preabil)
    if not removed:
        await bot.send_message(chatid, t('p_profile.boost_error', lang, default='❌ Ошибка применения!'),
                               reply_markup=await markups_menu(userid, 'last_menu', lang))
        return

    bonus_percent = item.get('bonus_percent', 0.5)
    duration = item.get('duration', 3600)
    expires_at = int(_time()) + duration

    activity.training_boost = {'bonus_percent': bonus_percent, 'expires_at': expires_at}
    await activity.save()

    from bot.modules.data_format import seconds_to_str
    dur_str = seconds_to_str(duration, lang)
    await bot.send_message(chatid,
        t('all_skills.training_boost.applied', lang,
          bonus=int(bonus_percent * 100), duration=dur_str,
          default='⚡ Бустер активирован!'),
        reply_markup=await markups_menu(userid, 'last_menu', lang))


async def _get_user_dino_ids(userid: int) -> list:
    """Returns list of ObjectId dino ids for a user using Beanie."""
    from bot.models.dinosaur import Dino as DinoModel
    dinos = await DinoModel.find({'owner_id': userid}).to_list()
    return [d.id for d in dinos]


async def open_training_boost_inventory(userid: int, chatid: int, lang: str, activity_type: str):
    """Opens standard item cards for training boosters."""
    filter_items = [{'item_id': f'training_boost_{activity_type}_1h'},
                    {'item_id': f'training_boost_{activity_type}_4h'}]
    items = await User.get_inventory_from_i(userid, filter_items, 20)

    if not items:
        await bot.send_message(chatid,
            t('all_skills.training_boost.no_items', lang,
              default='🧵 Нет бустеров для этой тренировки.'))
        return

    for inv_item in items:
        item_dict = inv_item['item']
        await data_for_use_item(item_dict, userid, chatid, lang)


async def boost_use_adapter(return_data: dict, transmitted_data: dict):

    egg_id = return_data['egg']
    transmitted_data['egg_id'] = egg_id

    lang = transmitted_data['lang']
    userid = transmitted_data['userid']
    chatid = transmitted_data['chatid']
    item = transmitted_data['items_data']

    from bot.models.dinosaur import Egg
    egg = await Egg.find_one(Egg.id == egg_id)
    if not egg:
        await bot.send_message(chatid, t('p_profile.boost_error', lang, default='❌ Ошибка: Ускорение недоступно!'), reply_markup=await markups_menu(userid, 'last_menu', lang))
        return

    preabil = item.get('abilities', {})
    removed = await RemoveItemFromUser(userid, item['item_id'], 1, preabil)
    if not removed:
        await bot.send_message(chatid, t('p_profile.boost_error', lang, default='❌ Ошибка: Ускорение недоступно!'), reply_markup=await markups_menu(userid, 'last_menu', lang))
        return

    time_boost = item.get('time_boost', 0)
    if not time_boost:
        item_data = get_data(item['item_id'])
        time_boost = item_data.get('time_boost', 0)

    new_incubation_time = egg.incubation_time - time_boost
    
    import time as time_mod
    if new_incubation_time <= int(time_mod.time()):
        from bot.models.dinosaur import Dino
        from bot.modules.managment.tracking import update_all_user_track
        from bot.modules.notifications import user_notification
        from bot.models.user import User

        # atomically delete/claim the egg first to prevent double hatching
        delete_result = await egg.delete()
        if delete_result and delete_result.deleted_count:
            res, alt_id = await Dino.insert_dino(egg.owner_id, egg.dino_id, egg.quality) 
            user = await User().create(egg.owner_id)
            await user_notification(egg.owner_id, 
                        'incubation_ready', lang, 
                        user_name=user.name, dino_alt_id_markup=alt_id)
            await update_all_user_track(user.userid, 'gaming')
        await bot.send_message(chatid, t('p_profile.boost_success', lang, default='⚡ Вылупление успешно ускорено!'), reply_markup=await markups_menu(userid, 'last_menu', lang))
    else:
        egg_obj = await Egg.find_one(Egg.id == egg.id)
        if egg_obj:
            egg_obj.incubation_time = new_incubation_time
            await egg_obj.save()
            
        boost_time_str = seconds_to_str(time_boost, lang)
        remained_time_str = seconds_to_str(max(0, new_incubation_time - int(time_mod.time())), lang)
        text = t('p_profile.boost_progress', lang, boost_time=boost_time_str, remained_time=remained_time_str, default=f"⚡ Инкубация ускорена на {boost_time_str}!\n⌛ Осталось времени: {remained_time_str}")
        await bot.send_message(chatid, text, reply_markup=await markups_menu(userid, 'last_menu', lang))


async def data_for_use_item(item: dict, userid: int, chatid: int, lang: str, confirm: bool = True):
    item_id = item['item_id']
    data_item = get_data(item_id)
    type_item = data_item['type']
    limiter = 1000 # Ограничение по количеству использований за раз
    adapter_function = adapter

    abilities = item.get('abilities', {})
    from bot.modules.items.item import get_item_dict
    item_dict = get_item_dict(item_id, abilities)
    if not abilities:
        bases_item_models = await Item.find(
            Item.owner_id == userid,
            Item.items_data.item_id == item_id,
            (Item.items_data.abilities == None) | (Item.items_data.abilities == {})
        ).to_list()
    else:
        bases_item_models = await Item.find(
            Item.owner_id == userid,
            Item.items_data == item_dict
        ).to_list()
    bases_item = [b.dict() for b in bases_item_models]
    transmitted_data = {'items_data': item}
    item_name = get_name(item_id, lang, item.get("abilities", {}))
    steps: list[DataType] = []
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

            steps += [
                DinoStepData('dino', None,
                    add_egg=False, all_dinos=True
                )
            ]
        elif type_item in ['game', 'sleep', 
                           'journey', 'collecting', 
                           'weapon', 'backpack', 'armor']:
            steps += [
                DinoStepData('dino', None,
                    add_egg=False, all_dinos=True
                )
            ]
        elif type_item == 'recipe':
            steps = [
                IntStepData('count', StepMessage(
                    text='css.wait_count',
                    translate_message=True,
                    markup=count_markup(max_count, lang)),
                    max_int=max_count
                )
            ]
        elif type_item == 'weapon':
            steps += [
                DinoStepData('dino', None,
                    add_egg=False, all_dinos=True
                )
            ]
        elif type_item == 'case':
            steps = [
                IntStepData('count', StepMessage(
                    text='css.wait_count',
                    translate_message=True,
                    markup=count_markup(max_count, lang)),
                    max_int=max_count
                )
            ]
        elif type_item == 'egg':
            steps = []

        elif type_item == 'incubation_boost':
            adapter_function = boost_use_adapter
            steps += [
                DinoStepData('egg', None,
                             add_egg=True, all_dinos=False, only_egg=True)
            ]

        elif type_item == 'training_boost':
            # Применяется напрямую к активной тренировке — без выбора дино
            adapter_function = training_boost_use_adapter

        elif type_item == 'special':

            if data_item['class'] in ['transport']:

                if item['abilities']['data_id'] == 0:
                    steps += [
                        DinoStepData('dino', None,
                            add_egg=False, all_dinos=False
                        )
                    ]

            elif data_item['class'] in ['defrosting']:
                steps += [
                    DinoStepData('dino', None,
                                 message_key='css.inactive_dino',
                            add_egg=False, all_dinos=False
                        )
                ]

            elif data_item['class'] in ['freezing']:
                steps += [
                    DinoStepData('dino', None,
                            add_egg=False, all_dinos=False
                        )
                    ]

            elif data_item['class'] in ['premium']:
                res = await Subscription.find_one(Subscription.userid == userid)
                if res: 
                    if res.sub_end == 'inf':
                        await bot.send_message(chatid, t('item_use.special.infinity_premium', lang), reply_markup=await markups_menu(userid, 'last_menu', lang))
                        return

                steps = [
                    IntStepData('count', StepMessage(
                        text='css.wait_count',
                        translate_message=True,
                        markup=count_markup(max_count, lang)),
                        max_int=max_count
                    )
                ]

            elif data_item['class'] in ['dino_slot']:
                steps = []

            elif data_item['class'] in ['reborn']:
                user = await User.find_one(User.userid == userid)
                dead = await user.get_dead_dinos() if user else []
                options, markup = {}, []

                if dead:
                    a = 0
                    for i in dead:
                        i: DeadDino
                        a += 1
                        name = f'{a}🦕 {i.name}'
                        markup.append(name)
                        options[name] = i.id

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
                                           t('item_use.special.reborn.no_dinos', lang))
                    return

            elif data_item['class'] in ['custom_book']:
                adapter_function = edit_custom_book
                steps = [
                    StringStepData('content', StepMessage(
                        text=t('css.content_str', lang, max_len=900),
                        translate_message=False,
                        markup=cancel_markup(lang)),
                        max_len=900
                    )
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
    item_id = item['item_id']
    abilities = item.get('abilities', {})
    from bot.modules.items.item import get_item_dict
    item_dict = get_item_dict(item_id, abilities)
    if not abilities:
        find_items = await items.find({
            'owner_id': userid,
            'items_data.item_id': item_id,
            '$or': [
                {'items_data.abilities': {'$exists': False}},
                {'items_data.abilities': {}}
            ]
        }, comment='delete_item_action')
    else:
        find_items = await items.find({'owner_id': userid, 
                                 'items_data': item_dict}, comment='delete_item_action')
    transmitted_data = {'items_data': item, 'item_name': ''}
    max_count = 0

    for base_item in find_items: max_count += base_item['count']

    if max_count:
        item_name = get_name(item_id, lang, item.get("abilities", {}))
        transmitted_data['item_name'] = item_name

        steps = [
            ConfirmStepData('confirm', StepMessage(
                text=t('css.delete', lang, name=item_name),
                translate_message=False,
                markup=confirm_markup(lang)),
                cancel=True
            ),
            IntStepData('count', StepMessage(
                text='css.wait_count',
                translate_message=True,
                markup=count_markup(max_count, lang)),
                max_int=max_count
            )
        ]

        await ChooseStepHandler(delete_action, userid, chatid, lang, steps,
                                transmitted_data=transmitted_data).start()

    else:
        await bot.send_message(chatid, t('delete_action.error', lang), 
                               reply_markup=
                               await markups_menu(userid, 'last_menu', lang))

standart_rarity_chances = {
    "common": 50,
    "uncommon": 25,
    "rare": 15,
    "mystical": 9,
    "legendary": 1,
    "mythical": 0.1
}

def rare_random(items: list[str], count: int = 1, 
                chances_add: Optional[dict[str, int]] = None,
                special_chances: Optional[dict[str, int]] = None,
                rarity_chances: Optional[dict[str, int]] = None,
                advanced_rank_for_items: Optional[dict[str, list[str]]] = None
                ) -> list[str]:
    """Функция выбирает случайные предметы из списка на основе их редкости.
       chances_add - словарь с шансами, которые нужно добавить к основным шансам
       special_chances - словарь с шансами, которые нужно использовать вместо основных для определённых предметов (0-100)
    """
    shuffle(items)

    if not rarity_chances:
        # Если не переданы шансы редкости, используем стандартные
        rarity_chances = standart_rarity_chances.copy()
    
    if not advanced_rank_for_items:
        # Если не переданы продвинутые редкости, используем пустой словарь
        advanced_rank_for_items = {}

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
        # Проверяем, есть ли предмет в каком-либо списке значений advanced_rank_for_items
        rank = None
        if advanced_rank_for_items:
            for adv_rank, adv_items in advanced_rank_for_items.items():
                if item in adv_items:
                    rank = adv_rank
                    break
        if not rank:
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

    # item = transmitted_data['items_data']

    transmitted_data['content'] = return_data['content']

    await ChooseConfirmHandler(
        edit_custom_book_confirm, userid, chatid, lang, True, 
        transmitted_data=transmitted_data).start()
    
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

    item = await Item.find_one(Item.id == item_base_id)
    if item:
        if 'abilities' not in item.items_data:
            item.items_data['abilities'] = {}
        item.items_data['abilities']['content'] = content
        item.items_data['abilities']['author'] = userid
        await item.save()

    await bot.send_message(chatid, '✅', 
            reply_markup=await markups_menu(userid, 'last_menu', lang))
