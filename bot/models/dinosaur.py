from typing import List, Dict, Any, Optional, Union
from beanie import Document, PydanticObjectId
from pydantic import Field
from bson.objectid import ObjectId
from pymongo import IndexModel, ASCENDING, TEXT
import datetime
from datetime import datetime, timezone, timedelta
import time
from random import choice, randint
from bot.models.enums import DinoStatus, MoodType, StatType

keys = [
    'good_sleep', 'end_game', 'multi_games', 'multi_heal', 
    'multi_eat', 'multi_energy', 'dream', 'good_eat', 'playing_together', 'sunshine', 'breeze', 'meeting_friend', 'magic_animal', 'magic_light', 'pet', 'talk_good', 'simple_work', 'positive_talk',
    'bad_sleep', 'stop_game', 'little_game', 'little_heal',
    'little_eat', 'little_energy', 'bad_dream', 'bad_eat', 'repeat_eat', 'rain', 'cold_wind', 'snowfall', 'drought', 'negative_talk',
    'break', 'bad_talk', 'hard_work', 'repeat_activity', 'overloading',
    'journey_event' 
]

breakdowns = {
    'seclusion': {
        'cancel_mood': 35,
        'duration_time': (1800, 7200),
    },
    'hysteria': {
        'cancel_mood': 30,
        'duration_time': (1800, 4500)
    },
    'unrestrained_play': {
        'cancel_mood': 30,
        'duration_time': (4150, 5400)
    }, 
    'downgrade': {
        'duration_time': 0
    }
}

inspiration = {
    'game': {
        'cancel_mood': 75,
        'duration_time': (3600, 9000),
        },
    'collecting': {
        'cancel_mood': 75,
        'duration_time': (3600, 9000),
        },
    'journey': {
        'cancel_mood': 75,
        'duration_time': (3600, 9000),
        },
    'sleep': {
        'cancel_mood': 75,
        'duration_time': (3600, 9000),
    },
    'craft': {
        'cancel_mood': 75,
        'duration_time': (1200, 3600),
    },
    'mine': {
        'cancel_mood': 75,
        'duration_time': (3600, 9000),
    },
    'bank': {
        'cancel_mood': 75,
        'duration_time': (3600, 9000),
    },
    'sawmill': {
        'cancel_mood': 75,
        'duration_time': (3600, 9000),
    },
    'gym': {
        'cancel_mood': 75,
        'duration_time': (3600, 7200),
    },
    'library': {
        'cancel_mood': 75,
        'duration_time': (3600, 7200),
    },
    'park': {
        'cancel_mood': 75,
        'duration_time': (1800, 7200),
    },
    'swimming_pool': {
        'cancel_mood': 75,
        'duration_time': (3600, 7200),
    },
    "exp_boost": {
        'cancel_mood': 75,
        'duration_time': (1800, 3600),
    }
}

class Dino(Document):
    data_id: int = 0
    alt_id: str = ""

    @property
    def _id(self) -> ObjectId:
        return self.id

    name: str = "name"
    quality: str = "com"
    notifications: Dict[str, Any] = Field(default_factory=dict)
    stats: Dict[str, Any] = Field(default_factory=lambda: {
        'heal': 10, 'eat': 10,
        'game': 10, 'mood': 10,
        'energy': 10,
        'power': 0.0, 'dexterity': 0.0,
        'intelligence': 0.0, 'charisma': 0.0
    })
    activ_items: List[Dict[str, Any]] = Field(default_factory=list)
    mood: Dict[str, Any] = Field(default_factory=lambda: {
        'breakdown': 0,
        'inspiration': 0
    })
    memory: Dict[str, Any] = Field(default_factory=lambda: {
        'games': [],
        'eat': [],
        'action': []
    })
    profile: Dict[str, Any] = Field(default_factory=lambda: {
        'background_type': 'standart',
        'background_id': 0
    })

    class Settings:
        name = "dinosaurs"
        indexes = [
            IndexModel([("alt_id", TEXT)], unique=True, name="alt_id")
        ]

    async def save_notification(self, not_type: str):
        self.notifications[not_type] = int(time.time())
        await self.save()

    async def delete_notification(self, not_type: str):
        if not_type in self.notifications:
            self.notifications.pop(not_type, None)
            await self.save()

    async def set_profile_background(self, background_type: str, background_id: Any):
        self.profile['background_type'] = background_type
        self.profile['background_id'] = background_id
        await self.save()

    async def set_data_id(self, data_id: str):
        self.data_id = data_id
        await self.save()

    async def set_quality(self, quality: str):
        self.quality = quality
        await self.save()

    async def set_data_id_and_quality(self, data_id: str, quality: str):
        self.data_id = data_id
        self.quality = quality
        await self.save()

    async def create(self, baseid: Union[ObjectId, str, None] = None):
        if baseid is None:
            return None

        try:
            if isinstance(baseid, str) and len(baseid) == 24:
                db_id = ObjectId(baseid)
            else:
                db_id = baseid
            find_result = await Dino.find_one(Dino.id == db_id)
        except Exception:
            find_result = None

        if not find_result:
            find_result = await Dino.find_one(Dino.alt_id == str(baseid))

        if find_result:
            for field_name in self.model_fields:
                val = getattr(find_result, field_name)
                setattr(self, field_name, val)
            self.id = find_result.id
            if hasattr(find_result, '_pre_save_values'):
                self._pre_save_values = find_result._pre_save_values
            if hasattr(find_result, '_state'):
                self._state = find_result._state
            return self
        else:
            db_id = None
            if isinstance(baseid, ObjectId):
                db_id = baseid
            elif isinstance(baseid, str) and len(baseid) == 24 and ObjectId.is_valid(baseid):
                db_id = ObjectId(baseid)
            
            if db_id:
                await DinoOwners.find({
                    "dino_id": {
                        "$in": [db_id, str(db_id)]
                    }
                }).delete()
            return None

    def __str__(self) -> str:
        return self.name

    async def update_data(self, update_data: dict):
        await Dino.find_one(Dino.id == self.id).update(update_data)
        updated = await Dino.get(self.id)

        if updated:
            self.__dict__.update(updated.__dict__)
        if self.stats['heal'] <= 0:
            await self.dead()
        return updated

    async def delete(self):
        from bot.models.activity import KDActivity, Kindergarten, Activity
        from bot.models.dinosaur import DinoOwners, DinoMood, State

        await Dino.find_one(Dino.id == self.id).delete()
        await KDActivity.find(KDActivity.dino_id == self.id).delete()
        await Activity.find(Activity.dino_id == self.id, with_children=True).delete()
        await DinoOwners.find(DinoOwners.dino_id == self.id).delete()
        await DinoMood.find(DinoMood.dino_id == self.id).delete()
        await Kindergarten.remove_dino(self.id)
        await State.find(State.dino_id == self.id).delete()

    async def dead(self):
        from bot.const import GAME_SETTINGS as GS
        from bot.models.user import User
        from bot.models.dinosaur import DeadDino
        from bot.modules.items.item import AddItemToUser
        from bot.modules.notifications import user_notification

        owner = await Dino.get_owner_by_id(self.id)
        if owner:
            user_data = await User.find_one(User.userid == owner.owner_id)
            if user_data:
                user_data.settings['last_dino'] = None
                await user_data.save()

            save_data = DeadDino(
                data_id=self.data_id,
                quality=self.quality,
                name=self.name,
                owner_id=owner.owner_id,
                stats={
                    'charisma': self.stats['charisma'],
                    'intelligence': self.stats['intelligence'],
                    'dexterity': self.stats['dexterity'],
                    'power': self.stats['power'],
                }
            )
            await save_data.insert()

            for item in self.activ_items:
                if item: 
                    await AddItemToUser(owner.owner_id, item['item_id'], 1, item.get('abilities', {}))

            if user_data:
                if await Dino.dead_check(owner.owner_id):
                    way = 'not_independent_dead'
                else: 
                    way = 'independent_dead'
                    await AddItemToUser(user_data.userid, GS['dead_dino_item'], 1, {'interact': False})

                await user_notification(owner.owner_id, way, dino_name=self.name)

        await self.delete()

    async def image(self, profile_view: int = 1, custom_url: str = ''):
        from bot.modules.images import create_dino_image
        age = await self.age()
        return await create_dino_image(self.data_id, self.stats, self.quality, profile_view, age.days, custom_url)

    async def collecting(self, owner_id: int, coll_type: str, max_count: int):
        from bot.models.activity import CollectingActivity
        return await CollectingActivity.start(self.id, owner_id, coll_type, max_count)

    async def game(self, duration: int = 1800, percent: float = 1.0):
        from bot.models.activity import GameActivity
        return await GameActivity.start(self.id, duration, percent)

    async def journey(self, owner_id: int, duration: int = 1800):
        from bot.models.activity import JourneyActivity
        return await JourneyActivity.start(self.id, owner_id, duration)

    async def sleep(self, s_type: str = 'long', duration: int = 1):
        from bot.models.activity import SleepActivity
        return await SleepActivity.start(self.id, s_type, duration)

    async def memory_percent(self, memory_type: str, obj: str, update: bool = True):
        from bot.const import GAME_SETTINGS as GS
        repeat = self.memory[memory_type].count(obj)
        percent = GS['penalties'][memory_type][str(repeat)]

        if update:
            max_repeat = {'games': 3, 'eat': 5, 'action': 8}
            if len(self.memory[memory_type]) < max_repeat[memory_type]:
                self.memory[memory_type].append(obj)
            else:
                self.memory[memory_type].pop()
                self.memory[memory_type].insert(0, obj)
            await self.update_data({'$set': {f'memory.{memory_type}': self.memory[memory_type]}})

        return percent, repeat

    @property
    def data(self):
        return Dino.get_dino_data(self.data_id)

    @property
    async def status(self) -> DinoStatus:
        from bot.modules.dinosaur.dino_status import check_status
        return await check_status(self)

    async def age(self):
        return await self.get_age(self.id)

    async def get_owner_by_id(self):
        from bot.models.dinosaur import DinoOwners
        return await DinoOwners.find_one(DinoOwners.dino_id == self.id, DinoOwners.type == 'owner')

    async def is_free(self):
        return await self.status == DinoStatus.PASS

    async def get_activity(self):
        from bot.models.activity import Activity
        return await Activity.find_one(Activity.dino_id == self.id, with_children=True)

    async def set_status(self, new_status: DinoStatus, now_status: DinoStatus | str = ''):
        await Dino.set_status(self.id, new_status, now_status)

    async def add_mood(self, key: str, unit: int, duration: int, stacked: bool = False):
        return await DinoMood.add(self.id, key, unit, duration, stacked)

    async def get_mood_status(self):
        # returns inspiration/breakdown points and checks breakdown/inspiration states
        return await DinoMood.find(DinoMood.dino_id == self.id).to_list()

    async def add_state(self, char: StatType, unit: int, time_state: int):
        return await State.add(self.id, char, unit, time_state)

    async def use_states(self):
        return await State.use_states(self.id)

    @classmethod
    def get_dino_data(cls, data_id: int) -> dict:
        from bot.const import DINOS
        from bot.modules.logs import log
        try:
            return DINOS['elements'][str(data_id)]
        except Exception as e:
            log(f'Ошибка в получении данных динозавра -> {e}', 3)
            return {}

    @classmethod
    def random_dino(cls, quality: str = 'com') -> int:
        from bot.const import DINOS
        return choice(DINOS[quality])

    @classmethod
    async def generation_code(cls, owner_id: int) -> str:
        from bot.modules.data_format import random_code
        code = f'{owner_id}_{random_code(8)}'
        if await cls.find_one(cls.alt_id == code):
            code = await cls.generation_code(owner_id)
        return code

    @classmethod
    async def insert_dino(cls, owner_id: int = 0, dino_id: int = 0, quality: str = 'random'):
        from bot.modules.data_format import random_quality
        from bot.modules.user.dinocollection import add_to_collection_dino
        from bot.modules.logs import log

        if quality in ['random', 'ran']: 
            quality = random_quality()
        if not dino_id: 
            dino_id = cls.random_dino(quality)

        dino_data = cls.get_dino_data(dino_id)
        dino = cls(
            data_id=dino_id,
            alt_id=await cls.generation_code(owner_id),
            name=dino_data['name'],
            quality=quality or dino_data['quality']
        )

        power, dexterity, intelligence, charisma = cls.set_standart_specifications(dino_data['class'], dino.quality)

        dino.stats = {
            'heal': 100, 'eat': randint(70, 100),
            'game': randint(30, 90), 'mood': randint(30, 100),
            'energy': randint(80, 100),

            'power': power, 'dexterity': dexterity,
            'intelligence': intelligence, 'charisma': charisma
        }

        log(prefix='InsertDino', 
            message=f'owner_id: {owner_id} dino_id: {dino_id} name: {dino.name} quality: {dino.quality}', 
            lvl=0)
        
        await dino.insert()
        if owner_id != 0:
            await DinoOwners.create_connection(dino.id, owner_id)
        
        await add_to_collection_dino(owner_id, dino_id)
        return dino, dino.alt_id

    @staticmethod
    def edited_stats(before: int, unit: int) -> int:
        if before + unit > 100: 
            return 100
        elif before + unit < 0: 
            return 0
        else: 
            return before + unit

    @classmethod
    async def get_age(cls, dinoid: Union[ObjectId, str]) -> timedelta:
        if isinstance(dinoid, str):
            dino = await cls.find_one(cls.alt_id == dinoid)
            if dino: 
                dinoid = dino.id

        dino_create = ObjectId(dinoid).generation_time
        now = datetime.now(timezone.utc)
        delta = now - dino_create
        return delta

    @classmethod
    async def mutate_stat(cls, dino: Union[dict, 'Dino'], key: str, value: int) -> int:
        from bot.modules.notifications import notification_manager
        
        if isinstance(dino, dict):
            dino_id = ObjectId(dino['_id'])
            st = dino['stats'][key]
        else:
            dino_id = dino.id
            st = dino.stats[key]
            
        now = st + value
        if now > 100: 
            value = 100 - st
        elif now < 0: 
            value = -st

        if key == 'heal' and now <= 0:
            dino_d = await cls.find_one(cls.id == dino_id)
            if dino_d:
                await dino_d.dead()
        else:
            r = await notification_manager(dino_id, key, now)
            await cls.find_one(cls.id == dino_id).update({'$inc': {f'stats.{key}': value}})
            return r
        return 0

    @classmethod
    async def get_owner_by_id(cls, dino_id: ObjectId):
        from bot.models.dinosaur import DinoOwners
        return await DinoOwners.find_one({
            "dino_id": {
                "$in": [ObjectId(dino_id), str(dino_id)]
            },
            "type": "owner"
        })

    @classmethod
    async def get_language(cls, dino_id: ObjectId) -> str:
        from bot.models.dinosaur import DinoOwners
        from bot.modules.localization import get_lang
        lang = 'en'
        owner = await DinoOwners.find_one({
            "dino_id": {
                "$in": [ObjectId(dino_id), str(dino_id)]
            }
        })
        if owner: 
            lang = await get_lang(owner.owner_id)
        return lang

    @classmethod
    async def dead_check(cls, userid: int) -> bool:
        from bot.models.user import User
        from bot.const import GAME_SETTINGS as GS
        user = await User.find_one(User.userid == userid)
        if user:
            col_dinos = await DinoOwners.find_one(
                            DinoOwners.owner_id == userid, DinoOwners.type == 'owner')
            col_eggs = await Egg.find_one(Egg.owner_id == userid)
            lvl = user.lvl <= GS['dead_dialog_max_lvl']

            if all([not col_dinos, not col_eggs, lvl]): 
                return True
        return False

    @classmethod
    async def set_status(cls, dino_id: ObjectId, new_status: DinoStatus | str, now_status: DinoStatus | str = ''):
        from bot.models.activity import Kindergarten, SleepActivity, GameActivity, JourneyActivity, CollectingActivity, WorkActivity, CraftActivity
        from bot.models.items import ItemCraft
        from bot.modules.dinosaur.dino_status import check_status, end_skill_activity
        from bot.modules.notifications import dino_notification

        assert new_status in [
            DinoStatus.SLEEP, DinoStatus.GAME, DinoStatus.JOURNEY, DinoStatus.COLLECTING, 
            DinoStatus.KINDERGARTEN, DinoStatus.HYSTERIA, DinoStatus.FARM, 
            DinoStatus.MINE, DinoStatus.BANK, DinoStatus.SAWMILL, DinoStatus.GYM, 
            DinoStatus.LIBRARY, DinoStatus.PARK, DinoStatus.SWIMMING_POOL, DinoStatus.CRAFT, 
            DinoStatus.UNRESTRAINED_PLAY, DinoStatus.PASS
        ], f'Состояние {new_status} не найдено!'
        
        if not now_status:
            now_status = await check_status(dino_id)

        if now_status == DinoStatus.SLEEP:
            sleeper = await SleepActivity.find_one(SleepActivity.dino_id == str(dino_id))
            if sleeper:
                sleep_time = int(time.time()) - sleeper.start_time
                await SleepActivity.end(dino_id, sleep_time)

        elif now_status == DinoStatus.GAME: 
            await GameActivity.end(dino_id)

        elif now_status == DinoStatus.JOURNEY: 
            await JourneyActivity.end(dino_id)

        elif now_status == DinoStatus.COLLECTING:
            data = await CollectingActivity.find_one(CollectingActivity.dino_id == str(dino_id))
            if data:
                await CollectingActivity.end(dino_id, data.items, data.sended, '', False)

        elif now_status == DinoStatus.KINDERGARTEN:
            await Kindergarten.remove_dino(dino_id)

        elif now_status == DinoStatus.CRAFT:
            res = await ItemCraft.find_one(ItemCraft.dino_id == str(dino_id))
            if res:
                await dino_notification(dino_id, 'craft_end')
                await res.delete()

            await CraftActivity.find(CraftActivity.dino_id == str(dino_id)).delete()

        elif now_status in [DinoStatus.GYM, DinoStatus.LIBRARY, DinoStatus.PARK, DinoStatus.SWIMMING_POOL]:
            from bot.models.activity import TrainingActivity
            res = await TrainingActivity.find_one(TrainingActivity.dino_id == str(dino_id))

            if res: 
                traning_time = int(time.time()) - res.start_time
                way = ''

                min_time = res.min_time
                unit_val = res.up_unit[0] if isinstance(res.up_unit, list) and res.up_unit else (res.up_unit or 0.0)
                if traning_time < res.min_time:
                    unit_percent = unit_val / 2

                    await cls.find_one(cls.id == dino_id).update({
                        '$inc': {f'stats.{res.up_skill}': round(-unit_percent)}
                    })
                    way = '_negative'

                await dino_notification(dino_id, res.activity_type + '_end' + way)
                await end_skill_activity(dino_id)

        elif now_status in [DinoStatus.BANK, DinoStatus.MINE, DinoStatus.SAWMILL]:
            await WorkActivity.end_work(dino_id)
            await dino_notification(dino_id, f'{now_status}_end')

    @classmethod
    def set_standart_specifications(cls, dino_type: str, dino_quality: str):
        from random import uniform
        quality_spec = {
            'com': [0, 1],
            'unc': [0, 2],
            'rar': [0, 3],
            'mys': [0, 4], 
            'leg': [0, 5]
        }
        power = round(uniform( *quality_spec[dino_quality] ), 4)
        dexterity = round(uniform( *quality_spec[dino_quality] ), 4)
        intelligence = round(uniform( *quality_spec[dino_quality] ), 4)
        charisma = round(uniform( *quality_spec[dino_quality] ), 4)

        if dino_type == 'Herbivore':
            charisma += round(uniform( *quality_spec[dino_quality] ), 4)
        elif dino_type == 'Carnivore':
            power += round(uniform( *quality_spec[dino_quality] ), 4)
        elif dino_type == 'Flying':
            dexterity += round(uniform( *quality_spec[dino_quality] ), 4)

        return round(power, 4), round(dexterity, 4), round(intelligence, 4), round(charisma, 4)

    @classmethod
    async def add_skill_point(cls, dino_id: ObjectId, skill: str, point: float) -> int:
        assert skill in ['charisma', 'intelligence', 'dexterity', 'power'], f'Skill {skill} не в списке'

        dino = await cls.find_one(cls.id == dino_id)
        if dino:
            skill_stat = dino.stats[skill]
            if skill_stat >= 20.0 or skill_stat <= 0.0: 
                return -1

            if point:
                if skill_stat + point > 20.0:
                    point = 20.0 - skill_stat

                if skill_stat + point < 0.0:
                    point = -skill_stat

                new_val = round(point + skill_stat, 4)
                await dino.update({'$set': {f'stats.{skill}': new_val}})
                dino.stats[skill] = new_val
            return 1
        return -1

    @classmethod
    async def check_skill(cls, dino_id: ObjectId, skill: str) -> float:
        assert skill in ['charisma', 'intelligence', 'dexterity', 'power'], f'Skill {skill} не в списке'
        dino = await cls.find_one(cls.id == dino_id)
        if dino: 
            return dino.stats[skill]
        return 0.0

    @classmethod
    async def max_skill(cls, owner: int, skill: str) -> float:
        from bot.modules.user.user import get_dinos
        assert skill in ['charisma', 'intelligence', 'dexterity', 'power'], f'Skill {skill} не в списке'

        dinos = await get_dinos(owner)
        max_sk = 0.0
        for dino in dinos: 
            max_sk = max(max_sk, dino.stats[skill])
        return max_sk

    async def get_combat_capabilities(self) -> dict:
        from bot.const import GAME_SETTINGS as GS
        from bot.modules.data_format import transform
        from bot.models.items import Item

        combat_config = GS.get('combat', {})
        max_char = combat_config.get('max_characteristic', 20.0)
        max_str_dmg = combat_config.get('max_strength_damage', 15)
        max_eva = combat_config.get('max_evasion_chance', 45)

        power = self.stats.get('power', 0.0)
        dexterity = self.stats.get('dexterity', 0.0)

        strength_damage_buff = transform(power, max_char, max_str_dmg)
        evasion_chance = transform(dexterity, max_char, max_eva)

        weapons = await Item.find_accessory(self.id, 'weapon')
        armors = await Item.find_accessory(self.id, 'armor')

        weapon_min = 1
        weapon_max = 1
        active_weapons = []
        for w in weapons:
            dmg_data = w.get_damage()
            if dmg_data:
                weapon_min += dmg_data.get('min', 0)
                weapon_max += dmg_data.get('max', 0)
                active_weapons.append({
                    'name': w.item_id,
                    'min': dmg_data.get('min', 0),
                    'max': dmg_data.get('max', 0),
                    'abilities': w.items_data.get('abilities', {})
                })

        total_block = 0
        active_armors = []
        for a in armors:
            refl = a.get_reflection()
            total_block += refl
            active_armors.append({
                'name': a.item_id,
                'block': refl,
                'abilities': a.items_data.get('abilities', {})
            })

        return {
            'power': power,
            'dexterity': dexterity,
            'strength_damage_buff': strength_damage_buff,
            'evasion_chance': evasion_chance,
            'weapon_min': weapon_min,
            'weapon_max': weapon_max,
            'total_min': weapon_min + strength_damage_buff,
            'total_max': weapon_max + strength_damage_buff,
            'total_block': total_block,
            'active_weapons': active_weapons,
            'active_armors': active_armors
        }

class Egg(Document):
    incubation_time: int = 0
    owner_id: Optional[int] = None
    egg_id: int = 0
    free_boost: bool = False

    @property
    def _id(self) -> ObjectId:
        return self.id
    quality: str = "random"
    dino_id: int = 0
    stage: str = "incubation"
    id_message: int = 0
    eggs: List[int] = Field(default_factory=list)
    dinos: List[int] = Field(default_factory=list)
    start_choosing: int = 0

    class Settings:
        name = "incubation"
        indexes = [
            IndexModel([("owner_id", ASCENDING)], name="owner_id"),
            IndexModel([("incubation_time", ASCENDING)], name="incubation_time")
        ]

    async def create(self, baseid: Union[ObjectId, str]):
        if isinstance(baseid, str):
            baseid = ObjectId(baseid)
        res = await Egg.find_one(Egg.id == baseid)
        if res:
            for field_name in self.model_fields:
                val = getattr(res, field_name)
                setattr(self, field_name, val)
            self.id = res.id
            if hasattr(res, '_pre_save_values'):
                self._pre_save_values = res._pre_save_values
            if hasattr(res, '_state'):
                self._state = res._state
            return self
        return None

    def choose_eggs(self):
        from bot.const import DINOS
        import random
        if self.quality == 'random':
            dinos_qual = DINOS['data']['dino']
        else:
            dinos_qual = DINOS[self.quality]

        self.dinos = random.sample(dinos_qual, 3)
        self.eggs = []
        for dino_id in self.dinos:
            dino_data = Dino.get_dino_data(dino_id)
            egg_id = dino_data.get('egg', 0)
            self.eggs.append(egg_id)

    async def image(self, lang: str = 'en'):
        from bot.modules.images import create_egg_image
        t_inc = self.remaining_incubation_time()
        return await create_egg_image(egg_id=self.egg_id, rare=self.quality, seconds=t_inc, lang=lang)

    def remaining_incubation_time(self):
        return max(0, self.incubation_time - int(time.time()))

    @classmethod
    async def incubation(cls, egg_id: int, owner_id: int, inc_time: int = 0, quality: str = 'random', dino_id: int = 0, free_boost: bool = False) -> bool:
        from bot.const import GAME_SETTINGS as GS
        from bot.modules.logs import log
        egg = await cls.find_one(
            cls.owner_id == owner_id, 
            cls.stage == 'choosing',
            cls.quality == quality
        )

        if not egg:
            log(prefix='InsertEgg ERROR', message=f'owner_id: {owner_id} data: None', lvl=0)
            return False

        egg.incubation_time = inc_time + int(time.time())
        egg.egg_id = egg_id
        egg.owner_id = owner_id
        egg.quality = quality

        if not dino_id:
            egg.dino_id = egg.dinos[egg.eggs.index(egg_id)]
        else:
            egg.dino_id = dino_id

        if inc_time == 0:
            egg.incubation_time = int(time.time()) + GS['first_dino_time_incub']

        egg.stage = 'incubation'

        log(prefix='InsertEgg', 
            message=f'owner_id: {owner_id} data: {egg.__dict__}', lvl=0)
        
        await cls.find_one(cls.id == egg.id).update({
            '$set': {
                'incubation_time': egg.incubation_time,
                'egg_id': egg.egg_id,
                'owner_id': egg.owner_id,
                'quality': egg.quality,
                'dino_id': egg.dino_id,
                'stage': egg.stage,
                'free_boost': free_boost
            },
            '$unset': {
                'id_message': 1,
                'eggs': 1,
                'dinos': 1,
                'start_choosing': 1
            }
        })
        return True

class DeadDino(Document):
    data_id: int = 0
    quality: str = ""
    name: str = ""
    owner_id: Optional[int] = None
    stats: Dict[str, float] = Field(default_factory=dict)

    class Settings:
        name = "dead_dinos"
        indexes = [
            IndexModel([("owner_id", ASCENDING)], name="owner_id")
        ]

class DinoOwners(Document):
    dino_id: Optional[PydanticObjectId] = None
    owner_id: Optional[int] = None
    type: str = ""  # 'owner' or 'add_owner'

    class Settings:
        name = "dino_owners"
        indexes = [
            IndexModel([("dino_id", ASCENDING)], name="dino_id"),
            IndexModel([("owner_id", ASCENDING)], name="owner_id")
        ]

    @classmethod
    async def create_connection(cls, dino_baseid: ObjectId, owner_id: int, con_type: str = 'owner'):
        from bot.modules.logs import log
        assert con_type in ['owner', 'add_owner'], f'Неподходящий аргумент {con_type}'

        con = cls(
            dino_id=dino_baseid,
            owner_id=owner_id,
            type=con_type
        )

        log(prefix='CreateConnection', 
            message=f'Dino - Owner Data: {con}', 
            lvl=0)
        return await con.insert()

class DinoMood(Document):
    dino_id: Optional[PydanticObjectId] = None
    action: str = ""
    unit: Optional[int] = None
    start_time: int = 0
    end_time: Optional[int] = None
    type: MoodType  # 'mood_edit' / 'mood_while' / 'breakdown' / 'inspiration'
    cancel_mood: Optional[int] = None
    while_data: Optional[Dict[str, Any]] = Field(default=None, alias="while")

    class Settings:
        name = "dino_mood"
        indexes = [
            IndexModel([("dino_id", ASCENDING)], name="dino_id"),
            IndexModel([("dino_id", ASCENDING), ("type", ASCENDING), ("action", ASCENDING)], name="dino_id_type_action")
        ]

    @classmethod
    async def add(cls, dino_id: ObjectId, key: str, unit: int, duration: int, stacked: bool = False) -> bool:
        from bot.modules.data_format import transform
        from bot.modules.logs import log

        res = await cls.find(cls.dino_id == dino_id, cls.action == key, cls.type == MoodType.MOOD_EDIT).to_list()
        if unit < 0:
            charisma = await Dino.check_skill(dino_id, 'charisma')
            if charisma > 5:
                if randint(1, transform(charisma, 20, 100)) > 70:
                    return True

        if not stacked and res:
            await res[0].update({"$set": {"end_time": int(time.time()) + duration}})
            return False
        else:
            if len(res) >= 5: # max_stack = 5
                return False


        if key in keys:
            data = cls(
                dino_id=dino_id,
                action=key,
                unit=unit,
                end_time=int(time.time()) + duration,
                start_time=int(time.time()),
                type=MoodType.MOOD_EDIT
            )
            await data.insert()
            return True
        return False

    @classmethod
    async def mood_while_if(cls, dino_id: ObjectId, key: str, characteristic: str, min_unit: int, max_unit: int, unit: int):

        res = await cls.find_one(cls.dino_id == dino_id, cls.action == key, cls.type == MoodType.MOOD_WHILE)
        if not res:
            if key in keys:
                data = cls(
                    dino_id=dino_id,
                    action=key,
                    unit=unit,
                    start_time=int(time.time()),
                    type=MoodType.MOOD_WHILE,
                    while_data={
                        'min_unit': min_unit,
                        'max_unit': max_unit,
                        'characteristic': characteristic
                    }
                )
                await data.insert()

    @classmethod
    async def dino_breakdown(cls, dino_id: ObjectId) -> str:

        from bot.models.items import Item
        from bot.models.activity import GameActivity

        action = choice(list(breakdowns.keys()))
        duration_s = breakdowns[action]['duration_time']

        if duration_s:
            duration = randint(*duration_s)
            cancel_mood = breakdowns[action]['cancel_mood']
            data = cls(
                dino_id=dino_id,
                cancel_mood=cancel_mood,
                end_time=int(time.time()) + duration,
                start_time=int(time.time()),
                type=MoodType.BREAKDOWN,
                action=action
            )
            await data.insert()

        if action == 'hysteria': 
            await Dino.set_status(dino_id, DinoStatus.PASS)
        elif action == 'unrestrained_play':
            await Dino.set_status(dino_id, DinoStatus.PASS)
            await GameActivity.start(dino_id, 10800, 0.4)
        elif action == 'downgrade':
            dino_cl = await Dino.find_one(Dino.id == dino_id)
            if dino_cl:
                allowed = await Item.find_accessory(dino_cl)
                if allowed:
                    await Item.downgrade_accessory(dino_cl, choice(allowed)[0], 30)

        return action

    @classmethod
    async def dino_inspiration(cls, dino_id: ObjectId) -> str:

        action = choice(list(inspiration.keys()))
        duration_s = inspiration[action]['duration_time']
        duration = randint(*duration_s)
        cancel_mood = inspiration[action]['cancel_mood']

        data = cls(
            dino_id=dino_id,
            cancel_mood=cancel_mood,
            end_time=int(time.time()) + duration,
            start_time=int(time.time()),
            type=MoodType.INSPIRATION,
            action=action
        )
        await data.insert()
        return action

    @classmethod
    async def calculation_points(cls, dino: dict, point_type: MoodType):
        from bot.const import GAME_SETTINGS as GS
        from bot.modules.notifications import dino_notification

        assert point_type in [MoodType.BREAKDOWN, MoodType.INSPIRATION], f'Invalid {point_type}'
        alter = MoodType.BREAKDOWN if point_type == MoodType.INSPIRATION else MoodType.INSPIRATION

        res_break = await cls.find_one(cls.dino_id == ObjectId(dino['_id']), cls.type == MoodType.BREAKDOWN)
        res_insp = await cls.find_one(cls.dino_id == ObjectId(dino['_id']), cls.type == MoodType.INSPIRATION)

        if not (res_break and res_insp):
            mood_points = dino['mood']
            if mood_points[alter.value] != 0:
                await Dino.find_one(Dino.id == ObjectId(dino['_id'])).update({'$inc': {f'mood.{alter.value}': -1}})
            else:
                if mood_points[point_type.value] + 1 >= GS['event_points']:
                    if point_type == MoodType.BREAKDOWN:
                        action = await cls.dino_breakdown(dino['_id'])
                    else:
                        action = await cls.dino_inspiration(dino['_id'])

                    await Dino.find_one(Dino.id == ObjectId(dino['_id'])).update({'$set': {f'mood.{point_type.value}': 0}})
                    add_message = f'{point_type.value}.{action}'
                    await dino_notification(dino['_id'], point_type.value, add_message=add_message, bonus=GS['inspiration_bonus'])
                else:
                    res = await cls.find_one(cls.dino_id == ObjectId(dino['_id']), cls.type == point_type)
                    if not res:
                        await Dino.find_one(Dino.id == ObjectId(dino['_id'])).update({'$inc': {f'mood.{point_type.value}': 1}})

    @classmethod
    async def check_inspiration(cls, dino_id: ObjectId, action_type: str) -> bool:

        assert action_type in list(inspiration.keys()), f'Invalid {action_type}'
        res = await cls.find_one(cls.dino_id == dino_id, cls.type == MoodType.INSPIRATION, cls.action == action_type)
        return bool(res)

    @classmethod
    async def inspiration_end(cls, dino_id: ObjectId, action_type: str) -> bool:
        res = await cls.find(cls.dino_id == dino_id, cls.type == MoodType.INSPIRATION, cls.action == action_type).delete()
        return bool(res)

    @classmethod
    async def check_breakdown(cls, dino_id: ObjectId, action_type: str = '') -> bool:

        if action_type:
            assert action_type in list(breakdowns.keys()), f'Invalid {action_type}'
            res = await cls.find_one(cls.dino_id == dino_id, cls.type == MoodType.BREAKDOWN, cls.action == action_type)
        else:
            res = await cls.find_one(cls.dino_id == dino_id, cls.type == MoodType.BREAKDOWN)
        return bool(res)

    @classmethod
    async def repeat_activity(cls, dino_id: ObjectId, percent: float):
        if percent != 0:
            if randint(0, 100) <= percent:
                await cls.add(dino_id, 'repeat_activity', -1, 3600, True)

class State(Document):
    dino_id: Optional[PydanticObjectId] = None
    char_edit: Optional[StatType] = None
    char_unit: int = 0
    time_end: int = 0
    last_check: int = 0

    class Settings:
        name = "state"
        indexes = [
            IndexModel([("dino_id", ASCENDING)], name="dino_id"),
            IndexModel([("last_check", ASCENDING)], name="last_check")
        ]

    @classmethod
    async def add(cls, dino_id: ObjectId, char: StatType, unit: int, time_state: int):
        assert char in [StatType.HEAL, StatType.EAT, StatType.GAME, StatType.MOOD, StatType.ENERGY], f'Unknown state {char}'
        data = cls(
            dino_id=dino_id,
            char_edit=char,
            char_unit=unit,
            time_end=int(time.time()) + time_state,
            last_check=int(time.time())
        )
        await data.insert()

    @classmethod
    async def use_states(cls, dino_id: ObjectId):
        res = await cls.find(cls.dino_id == dino_id).to_list()
        for state in res:
            dino = await Dino.find_one(Dino.id == dino_id)
            if dino:
                await Dino.mutate_stat(dino, state.char_edit, state.char_unit)
