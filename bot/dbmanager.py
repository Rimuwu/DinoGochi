import asyncio
import os
import pprint
from typing import Dict

import motor.motor_asyncio
from bot.config import conf
from motor.core import AgnosticClient

from bot.const import GAME_SETTINGS


from pymongo import monitoring
import time
from bot.modules.logs import log

_start_times = {}

class CommandLogger(monitoring.CommandListener):
    def started(self, event):
        _start_times[event.request_id] = time.time()

    def succeeded(self, event):
        start_time = _start_times.pop(event.request_id, None)
        if start_time:
            duration = time.time() - start_time
            if event.command_name not in ['ping', 'ismaster', 'hello']:
                log(lvl=-1, prefix="db_query", 
                    message=f'{event.command_name} took {round(duration, 4)}s (req: {event.request_id})')

    def failed(self, event):
        _start_times.pop(event.request_id, None)
        log(lvl=-1, prefix="db_query_failed", 
            message=f'{event.command_name} failed: {event.failure} (req: {event.request_id})')

monitoring.register(CommandLogger())

class UnifiedDatabaseWrapper:
    def __init__(self, dinogochi_db, db_name):
        self._dinogochi_db = dinogochi_db
        self._db_name = db_name

    def __getattr__(self, col_name):
        mapped_name = self._map_col(col_name)
        return self._dinogochi_db[mapped_name]

    def __getitem__(self, col_name):
        return self.__getattr__(col_name)

    def _map_col(self, col_name):
        if self._db_name == "group" and col_name == "users":
            return "group_users"
        if self._db_name == "lottery" and col_name == "members":
            return "lottery_members"
        if self._db_name == "tracking" and col_name == "members":
            return "tracking_members"
        if self._db_name == "dungeon":
            return f"deleted_dungeon_{col_name}"
        return col_name

    async def list_collection_names(self, *args, **kwargs):
        return await self._dinogochi_db.list_collection_names(*args, **kwargs)

    async def create_collection(self, name, *args, **kwargs):
        mapped_name = self._map_col(name)
        return await self._dinogochi_db.create_collection(mapped_name, *args, **kwargs)

# Monkeypatch AsyncIOMotorClient to support append_metadata for Beanie
if not hasattr(motor.motor_asyncio.AsyncIOMotorClient, "append_metadata"):
    def _append_metadata(self, *args, **kwargs):
        if hasattr(self.delegate, "append_metadata"):
            return self.delegate.append_metadata(*args, **kwargs)
    motor.motor_asyncio.AsyncIOMotorClient.append_metadata = _append_metadata

class UnifiedMongoClientWrapper:
    def __init__(self, real_client):
        self._real_client = real_client
        self.dinogochi = real_client["dinogochi"]
        self.HOST = real_client.HOST
        self.PORT = real_client.PORT

    def __getattr__(self, name):
        if name == "dinogochi":
            return self.dinogochi
        if name in ["server_info", "list_database_names", "drop_database", "close", "get_io_loop", "append_metadata", "start_session"]:
            return getattr(self._real_client, name)
        return UnifiedDatabaseWrapper(self.dinogochi, name)

    def __getitem__(self, name):
        return self.__getattr__(name)

real_mongo_client = motor.motor_asyncio.AsyncIOMotorClient(conf.mongo_url)
mongo_client = UnifiedMongoClientWrapper(real_mongo_client)

async def init_beanie_odm(client: motor.motor_asyncio.AsyncIOMotorClient):
    from beanie import init_beanie
    from bot.models.user import User, Lang, Referral, Friend, Subscription, Ad, DinoCollection, Achievement
    from bot.models.dinosaur import Dino, Egg, DeadDino, DinoOwners, DinoMood, State
    from bot.models.items import Item, EatItem, AccessoryItem, RecipeItem, CaseItem, EggItem, SpecialItem, ItemCraft, Farm
    from bot.models.market import Product, Seller, Preferential, Puhs
    from bot.models.activity import KDActivity, Activity, GameActivity, SleepActivity, JourneyActivity, CollectingActivity, TrainingActivity, WorkActivity, CraftActivity, Kindergarten
    from bot.models.tavern import Quest, Tavern, DailyAward, InsideShop
    from bot.models.tracking import Link, TrackingMember
    from bot.models.group import Group, GroupMessage, GroupUser
    from bot.models.other import (Lottery, LotteryMember, Online, Management, 
                                  Statistic, Event, Promo, DeadUser, 
                                  Company, MessageLog, States, Booster, OnetimeReward, DungLobby, Donation)

    target_db = client["dinogochi"]
    await init_beanie(
        database=target_db,
        document_models=[
            User, Lang, Referral, Friend, Subscription, Ad, DinoCollection, Achievement,
            Dino, Egg, DeadDino, DinoOwners, DinoMood, State,
            Item, EatItem, AccessoryItem, RecipeItem, CaseItem, EggItem, SpecialItem, ItemCraft, Farm,
            Product, Seller, Preferential, Puhs,
            KDActivity, Activity, GameActivity, SleepActivity, JourneyActivity, CollectingActivity, TrainingActivity, WorkActivity, CraftActivity, Kindergarten,
            Quest, Tavern, DailyAward, InsideShop,
            Link, TrackingMember,
            Group, GroupMessage, GroupUser,
            Lottery, LotteryMember, Online, Management, 
            Statistic, Event, Promo, DeadUser, 
            Company, MessageLog, States, Booster, OnetimeReward, DungLobby, Donation
        ]
    )


async def check_db(client: UnifiedMongoClientWrapper):
    if not await client._real_client.server_info():
        raise ConnectionError("Failed to connect to MongoDB server")

    print(f"{client.HOST}, mongo connected")

    print('Initializing Beanie ODM...')
    await init_beanie_odm(client._real_client)
    print('Beanie ODM initialized.')

    from bot.redismanager import init_redis
    await init_redis()

    print('Creating necessary documents...')
    await create_necessary_documents(client)
    print('Necessary documents created.')
    print('The databases are checked and prepared for use.')

async def create_necessary_documents(client: UnifiedMongoClientWrapper):
    for base, collections in GAME_SETTINGS.get('please_create_this', {}).items():
        database = client[base]
        for col, documents in collections.items():
            collection = database[col]
            for doc in documents:
                await create_document_if_not_exists(collection, doc)

async def create_document_if_not_exists(collection, doc: Dict):
    if not await collection.find_one({"_id": doc['_id']}, {'_id': 1}):
        await collection.insert_one(doc)

def check():
    for way in [conf.logs_dir]:
        if not os.path.exists(way):
            os.mkdir(way)
            print(f"I didn't find the {way} directory, so I created it.")

    if conf.check_translate:
        from tools.translate.translate import main as check_locs
        print("Запуск автоматической проверки файлов локализации.")
        res = check_locs()
        print("Обновлённые данные:")
        pprint.pprint(res)
        print()
