from typing import Dict, Any, Optional, List, Union
from bson.objectid import ObjectId
import time
import json
from random import choice, choices, randint
from pydantic import Field
from bot.models.activity.base import Activity
from bot.modules.overwriting.DataCalsses import Transaction

# Load journey configs
try:
    with open('bot/json/journey.json', encoding='utf-8') as f: 
        JOURNEY_DATA = json.load(f)
except Exception:
    JOURNEY_DATA = {}

try:
    with open('bot/json/journey_config.json', encoding='utf-8') as f:
        JOURNEY_CONFIG = json.load(f)
except Exception:
    JOURNEY_CONFIG = {}

events = JOURNEY_CONFIG.get('events', {})
locations = JOURNEY_CONFIG.get('locations', {})
chance = JOURNEY_CONFIG.get('chance', {})
rarity_lvl = JOURNEY_CONFIG.get('rarity_lvl', [])

class JourneyActivity(Activity):
    sended: int
    location: str = "forest"
    journey_log: List[Dict[str, Any]] = Field(default_factory=list)
    items: List[str] = Field(default_factory=list)
    coins: int = 0
    journey_start: int = Field(default_factory=lambda: int(time.time()))
    journey_end: int = Field(default=0)

    @classmethod
    async def start(cls, dino_id: ObjectId, owner_id: int, duration: int = 1800, location: str = 'forest') -> bool:
        existing = await cls.find_one(cls.dino_id == ObjectId(dino_id))
        if not existing:
            act = cls(
                dino_id=str(dino_id),
                activity_type="journey",
                journey_start=int(time.time()),
                journey_end=int(time.time()) + duration,
                sended=owner_id,
                location=location,
                journey_log=[],
                items=[],
                coins=0
            )
            await act.insert()
            return True
        return False

    @classmethod
    async def end(cls, dino_id: ObjectId):
        from bot.models.user import User
        from bot.modules.items.item import AddItemToUser
        from bot.modules.logs import log
        
        act = await cls.find_one(cls.dino_id == ObjectId(dino_id))
        if act:
            async with Transaction():
                for item in act.items:
                    await AddItemToUser(act.sended, item)
                user_doc = await User.find_one(User.userid == act.sended)
                if user_doc:
                    user_doc.coins += act.coins
                    await user_doc.save()
                log(f"Edit coins: user: {act.sended} col: {act.coins}", 0, "take_coins")
                await act.delete()

    @classmethod
    def create_event_dict(cls, location: str, worldview: str = '', rarity: int = 0, event: str = ''):
        from bot.modules.data_format import random_dict
        if not worldview:
            worldview = 'negative' if randint(1, 3) == 2 else 'positive'
        if not rarity:
            rarity_chr = choices(list(chance.keys()), list(chance.values()))[0]
            rarity = rarity_lvl.index(rarity_chr)
        else:
            rarity_chr = rarity_lvl[rarity]

        loc_data = locations[location]
        if not event: 
            event = choice(loc_data[worldview][rarity_chr]) 

        event_data = events[event]
        danger = loc_data['danger']
        data = {'type': event, 'worldview': worldview, 'dino_edit': {}, 'location': location}

        if 'buffs' in event_data:
            for key in event_data['buffs']:
                data['dino_edit'][key] = random_dict(event_data['buffs'][key][worldview])
                data['dino_edit'][key] = data['dino_edit'][key] + int((data['dino_edit'][key] / 2) * (danger - 1.0))

        for key in ['conditions', 'actions']:
            if key in event_data: 
                data[key] = event_data[key]

        if 'mood_keys' in event_data:
            data['mood_keys'] = event_data['mood_keys'][worldview]

        if 'items' in event_data:
            items_col = event_data['items'][worldview]['col'][str(rarity)]
            if worldview == 'positive':
                data['items'] = []
                for _ in range(items_col):
                    item_rar = choices(list(chance.keys()), list(event_data['items'][worldview]['weight']))[0] if 'weight' in event_data['items'][worldview] else choices(list(chance.keys()), list(chance.values()))[0]
                    data['items'].append(choice(loc_data['items'][item_rar]))
            else: 
                data['remove_item'] = items_col

        if 'mobs' in event_data:
            col = event_data['mobs']['col'][str(rarity)]
            data['mobs'] = []
            for _ in range(col):
                mob = choice(loc_data['mobs']['mobs'])
                hp = random_dict(loc_data['mobs']['mobs_hp'])
                damage = random_dict(loc_data['mobs']['mobs_damage'])
                loot = JOURNEY_DATA['mobs'][mob]['loot'] if mob in JOURNEY_DATA.get('mobs', {}) else []
                data['mobs'].append({'key': mob, 'hp': hp, 'damage': damage, 'loot': loot})

        if 'coins' in event_data:
            data['coins'] = random_dict(event_data['coins'][worldview][str(rarity)])
            data['coins'] = data['coins'] + int((data['coins'] / 2) * (danger - 1.0))

        if 'location_events' in event_data:
            data['location_events'] = []
            col = random_dict(event_data['location_events'])
            for _ in range(col):
                ev = choice(loc_data['location_events'][worldview])
                data['location_events'].append(ev)

        return data

    @classmethod
    async def random_event(cls, dinoid: str, location: str, ignored_events: list = [], friend_dino = None) -> bool:
        event, res = {}, None
        stop = False
        for _ in range(15):
            if not stop:
                for _ in range(10):
                    event = cls.create_event_dict(location)
                    if event['type'] not in ignored_events: 
                        stop = True
                        break
                if event:
                    res = await cls.activate_event(dinoid, event, friend_dino)
                    if res: 
                        if event['type'] == 'exit': 
                            await cls.find(cls.dino_id == ObjectId(dinoid)).update({'$set': {'journey_end': int(time.time())}})
                        return True
            else: 
                break
        return bool(res)

    @classmethod
    async def activate_event(cls, dinoid: str, event: dict, friend_dino = None) -> bool:
        from bot.models.dinosaur import Dino, DinoMood
        from bot.models.items import Item
        from bot.models.dinosaur import Dino
        from bot.modules.user.user import get_frineds
        
        journey_base = await cls.find_one(cls.dino_id == ObjectId(dinoid))
        dino = await Dino().create(dinoid)
        if not dino or not journey_base: 
            return False

        active_consequences = True
        event_data = events[event['type']]
        data = {'type': event['type'], 'location': event['location'], 'worldview': event['worldview']}
        end_time = journey_base.journey_end - int(time.time())

        if 'friend' in event: 
            data['friend'] = event['friend']
        if 'location_events' in event: 
            data['location_events'] = event['location_events']

        if 'conditions' in event_data:
            conditions = event_data['conditions']
            if 'have_item' in conditions and len(journey_base.items) == 0: 
                return False
            elif 'have_coins' in conditions and journey_base.coins <= 0: 
                return False
            elif 'have_friend' in conditions and 'friend' not in journey_base.model_extra: 
                return False

        if 'actions' in event_data:
            actions = event_data['actions']
            if 'joint_event' in actions and 'friend' in journey_base.model_extra:
                if not friend_dino:
                    friend_dino = journey_base.model_extra['friend']

            if 'location_friend' in actions:
                res = await get_frineds(journey_base.sended)
                friends = res['friends']
                in_loc = []
                for friend_id in friends:
                    res_j = await cls.find(cls.sended == friend_id, cls.location == journey_base.location).to_list()
                    for i in res_j: 
                        in_loc.append(i.dino_id)

                if not in_loc: 
                    return True
                else: 
                    if not friend_dino:
                        friend_dino = choice(in_loc)

            for act_dct in actions:
                if isinstance(act_dct, dict):
                    if act_dct['type'] == 'random_action':
                        rand_list = choice(act_dct['data'])
                        for i in rand_list: 
                            actions.append(i)
                    if act_dct['type'] == 'random_event':
                        rand_list = choice(act_dct['data'])
                        new_event = cls.create_event_dict(data['location'], data['worldview'], event=rand_list)
                        await cls.activate_event(dinoid, new_event, friend_dino)
                        return True

            if 'delete_items' in actions and 'items' in event: 
                del event['items']
            if 'delete_coins' in actions and 'coins' in event: 
                del event['coins']
            if 'edit_location' in actions:
                ran_locs = list(locations.keys())
                ran_locs.remove(data['location'])
                new_loc = choice(ran_locs)
                journey_base.location = new_loc
                await journey_base.save()
                data['old_location'] = new_loc

            if 'random_event' in actions:
                await cls.random_event(dinoid, journey_base.location, ['joint_event', 'joint_activity', 'meeting_friend'], friend_dino)
                return True

        if friend_dino: 
            data['friend'] = friend_dino

        if 'location_events' in event and event['worldview'] == 'negative':
            eve_list = event['location_events']
            if 'rain' in eve_list and await Item.check_accessory(dino, 'cloak', True):
                event['location_events'].remove('rain')
                event['location_events'].append('anti_rain')
            if 'cold_wind' in eve_list and await Item.check_accessory(dino, 'leather_clothing', True):
                event['location_events'].remove('cold_wind')
                event['location_events'].append('anti_cold_wind')

        if active_consequences:
            async with Transaction():
                if 'mobs' in event:
                    dino_hp, loot, status = 0, [], True
                    data['mobs'] = []

                    from bot.models.dinosaur import Dino
                    power = await Dino.check_skill(dino.id, 'power')

                    from bot.modules.items.item import get_data
                    damage = await Item.weapon_damage(dino) + int((power / 2) * (1.0))
                    have_acs = await Item.check_accessory(dino, 'skinning_knife', True)
                    protection = await Item.armor_protection(dino, False)

                    for mob in event['mobs']:
                        dam_col = mob['hp'] // damage
                        data['mobs'].append(mob['key'])
                        if (dam_col * mob['damage']) > 0:
                            await Item.downgrade_type_accessory(dino, 'armor')
                            dino_hp -= (dam_col * mob['damage']) - protection

                        if dino.stats['heal'] - dino_hp > 10:
                            chance_kn = (1, 3) if have_acs else (1, 2)
                            for it in mob['loot']:
                                if randint(*chance_kn) == 2:
                                    loot.append(it)
                        else:
                            status = False
                            break

                    if status:
                        event['worldview'] = 'positive'
                        if 'items' in event:
                            event['items'].extend(loot)
                        else: 
                            event['items'] = loot
                        event['dino_edit']['heal'] = dino_hp
                    else:
                        event['worldview'] = 'negative'
                        event['dino_edit']['heal'] = dino.stats['heal'] - 10

                if 'coins' in event:
                    journey_base.coins += event['coins']
                    data['coins'] = event['coins']
                    if journey_base.coins < 0: 
                        journey_base.coins = 0
                    await journey_base.save()

                if 'dino_edit' in event:
                    data['dino_edit'] = event['dino_edit']
                    for key, value in event['dino_edit'].items():
                        edit = True
                        if key == 'game' and await Item.check_accessory(dino, 'rubik_cube', True) and event['worldview'] == 'negative': 
                            edit = False
                        if key == 'eat' and await Item.check_accessory(dino, 'bag_goodies', True) and event['worldview'] == 'negative': 
                            edit = False
                        if dino and edit: 
                            await Dino.mutate_stat(dino, key, value)

                if 'items' in event:
                    data['items'] = event['items'] 
                    for i in data['items']:
                        journey_base.items.append(i)
                    await journey_base.save()

                if 'mood_keys' in event:
                    unit = 1 if data['worldview'] == 'positive' else -1
                    if 'location_events' in event:
                        for i in event['location_events']:
                            mood_res = await DinoMood.add(ObjectId(dinoid), i, unit, end_time)
                            if not mood_res:
                                await DinoMood.add(ObjectId(dinoid), 'journey_event', unit, end_time)
                    else:
                        for i in event['mood_keys']: 
                            await DinoMood.add(ObjectId(dinoid), i, unit, end_time)

                if 'remove_item' in event:
                    col = event['remove_item']
                    items = journey_base.items
                    data['remove_items'] = []
                    no_items = False
                    for _ in range(col):
                        if items: 
                            it = choice(items)
                            items.remove(it)
                            data['remove_items'].append(it)
                        else: 
                            no_items = True
                            break
                    if not no_items and not await Item.check_accessory(dino, 'lock_bag', True):
                        journey_base.items = items
                        await journey_base.save()
                    else:
                        return True

            journey_base.journey_log.append(data)
            await journey_base.save()
            if friend_dino:
                event['friend'] = dinoid
                await cls.activate_event(friend_dino, event)
            return True
        return False

    @classmethod
    async def generate_event_message(cls, event: dict, lang: str, journey_id: ObjectId, encode: bool = False) -> str:
        from bot.modules.data_format import encoder_text, count_elements
        from bot.modules.items.item import counts_items
        from bot.modules.localization import get_data, t
        from bot.models.dinosaur import Dino

        location = event['location']
        event_type = event['type']
        worldview = event['worldview']

        signs = get_data('journey.signs', lang)
        journey_text = get_data('journey', lang)

        if event_type in journey_text:
            text_list = get_data(f'journey.{event_type}', lang)
        else:
            if location in journey_text:
                if worldview in journey_text[location]:
                    if event_type in journey_text[location][worldview]:
                        text_list = get_data(f'journey.{location}.{worldview}.{event_type}', lang)
                    else:
                        text_list = get_data(f'journey.{location}.{event_type}', lang)
                else:
                    text_list = get_data(f'journey.{location}.{event_type}', lang)
            else:
                text_list = get_data(f'journey.{worldview}.{event_type}', lang)

        if 'replic' not in event:
            text = choice(text_list)
            repl_id = text_list.index(text)
            journey_data = await cls.find_one(cls.id == journey_id)
            if journey_data and journey_data.journey_log:
                log_index = journey_data.journey_log.index(event)
                await journey_data.update({'$set': {f'journey_log.{log_index}.replic': repl_id}})
        else:
            text = text_list[event['replic']]

        if encode:
            text = encoder_text(text, 3)
        add_list = []

        if 'coins' in event:
            if event['coins'] != 0:
                add_list.append(f'{event["coins"]}{signs["coins"]}')

        if 'dino_edit' in event:
            for i in ['heal', 'game', 'energy', 'eat']:
                add = ''
                if i in event['dino_edit']:
                    if event["dino_edit"][i] != 0:
                        if event["dino_edit"][i] > 0:
                            add = '+'
                        add_list.append(f'{add}{event["dino_edit"][i]}{signs[i]}')

        if 'location_events' in event:
            for i in event['location_events']:
                add_list.append(f'{signs[i]}')

        if 'items' in event:
            if event['items']:
                add_list.append('+' + counts_items(event['items'], lang))
        if 'remove_items' in event:
            if event['remove_items']:
                add_list.append('-' + counts_items(event['remove_items'], lang))

        if 'old_location' in event:
            loc = event['old_location']
            old_loc = get_data(f'journey_start.locations.{location}', lang)['name']
            loc_now = get_data(f'journey_start.locations.{loc}', lang)['name']
            add_list.append(f'{old_loc} -> {loc_now}')

        if 'friend' in event:
            from bot.models.dinosaur import Dino
            friend_dino = await Dino.find_one(Dino.id == ObjectId(event['friend']))
            if friend_dino:
                add_list.append(f'🦕 {friend_dino.name}')
                text = text.replace("{friend}", friend_dino.name)

        if 'mobs' in event:
            md = get_data('mobs', lang)
            mobs_names = []
            for i in event['mobs']:
                mobs_names.append(f'{md[i]["emoji"]} {md[i]["name"]}')
            add_list.append(f'👿 ({count_elements(mobs_names)})')

        if 'cancel' in event:
            add_list.append(t('journey.cancel', lang))

        if add_list:
            add_text = ', '.join(add_list)
            text += f'\n<code>{add_text}</code>'
        return text

    @classmethod
    async def all_log(cls, logs: list, lang: str, journey_id: ObjectId) -> List[str]:
        from bot.modules.logs import log
        text, n, n_message = '', 0, 0
        messages = ['']

        for event in logs:
            n += 1
            try:
                m = await cls.generate_event_message(event, lang, journey_id)
                text = f'{n}. {m}\n\n'
            except Exception as E:
                text = f'error generation - {event}\n{E}'
                log(text, 2, 'log generation')

            if len(messages[n_message]) >= 1700:
                messages.append('')
                n_message += 1
            messages[n_message] += text

        return messages
