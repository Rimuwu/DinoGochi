import random
from bot.dbmanager import mongo_client
from bson.objectid import ObjectId
from typing import Union, Any
from bot.modules.data_format import user_name
from bot.exec import bot
from bot.modules.user.user import take_coins
from bot.modules.items.item import AddListItems

from bot.modules.overwriting.DataCalsses import DBconstructor
lobbys = DBconstructor(mongo_client.dungeon.lobby)
users = DBconstructor(mongo_client.user.users)

class DungPlayer:

    def __init__(self) -> None:
        self._id: ObjectId = ObjectId() # Id данных юзера
        self.name: str = '' # Имя пользователя

        self.message: int = 0 # Активное сообщени
        self.page: str = "main" # Страница в сообщении

        self.coins: int = 0 # Количество монет, взятое в подземелье
        self.dinos: list[ObjectId] = [] # Id данных динозавров юзера
        self.inventory: list[dict] = [] # Список с предметами

    def __getitem__(self, item):
        return self.__dict__[item]

    async def __setitem__(self, item, value) -> None:
        self.__dict__[item] = value
        await self.save()

    def __str__(self) -> str:
        return str(self.__dict__)

    async def create(self, user_id:int, message:int, 
                     coins:int = 0, dinos:list[ObjectId] = [], 
                     inventory:list[dict] = []):
        user = await users.find_one({"userid": user_id}, comment='DungPlayer_create')
        if user:
            teleuser = await botworker.get_chat_member(user_id, user_id)

            self._id = user['_id']
            self.name = user_name(teleuser.user)
            self.message = message
            self.coins = coins
            self.dinos = dinos
            self.inventory = inventory

        return self

    def FromDict(self, data:dict, userid:int, dungeonid:int):
        self.__dict__ = data
        self.dungeonid = dungeonid
        self.userid = userid
        return self

    async def save(self):
        data = self.__dict__.copy()
        dungeonid = data['dungeonid']
        del data['dungeonid']

        await lobbys.update_one({"dungeonid": dungeonid}, 
                                {"$set": {f"users.{self.userid}": self.__dict__}}, comment='DungPlayer_save')

    @property
    async def user_id(self):
        user = await users.find_one({"_id": self._id}, {"userid": 1}, comment='DungPlayer_user_id')
        if user: return user['userid']

class Lobby:

    def __init__(self) -> None:
        self._id: ObjectId = ObjectId()

        self.dungeonid: int = 0 # id создателя
        self.users: dict[str, DungPlayer] = {} # Данные юзеров

        self.floor: dict[str, Any] = {} # Данные этажа
        self.rooms: dict[str, Room] = {} # Комнаты

        self.stage: str = 'preparation' # Этап
        self.stage_data: dict[str, Any] = {} # Данные этапа
        self.settings: dict[str, Any] = {} # Настройки

    def __getitem__(self, item):
        return self.__dict__[item]

    async def __setitem__(self, item, value) -> None:
        """ Не вызывается при обновлении вложенных данных
            lobby["dungeonid"] = 1 - Сработает
            lobby["settings"]["lang"] = "en" - НЕ СРАБОТАЕТ!
        """
        self.__dict__[item] = value
        await lobbys.update_one({"dungeonid": self.dungeonid}, {"$set": {item:value}}, 
                                comment='Lobby__setitem__')

    def __str__(self) -> str:
        return str(self.__dict__)

    async def create(self, user_id:int, message:int):
        find_result = await lobbys.find_one({"dungeonid": user_id}, comment='Lobby_create_find_result')
        if not find_result:
            self.dungeonid = user_id
            owner = await DungPlayer().create(user_id, message)
            await self.add_player(owner, user_id)

            await lobbys.insert_one(self.ToBaseFormat, comment='Lobby_create')
            return self

        else: return await self.FromBase(find_result['_id'])

    async def FromBase(self, lobbyid:Union[int, ObjectId]):
        """ Создание класса лобби на основе данных из базы
        """
        find_result = await lobbys.find_one({"_id": lobbyid}, comment='Lobby_FromBase')
        if not find_result:
            find_result = await lobbys.find_one({"dungeonid": lobbyid}, comment='Lobby_FromBase_1')
        if find_result: 
            self.__dict__ = find_result

            users = {}
            for userkey, uservalue in find_result['users'].items(): # type: ignore
                user = DungPlayer().FromDict(uservalue, int(userkey), self.dungeonid)
                users[userkey] = user

        return self

    @property
    def ToBaseFormat(self) -> dict:
        data = self.__dict__.copy()

        for var in ('users', 'floor', 'rooms'):
            for key, value in self[var].items(): 
                data['users'][key] = value.__dict__

        return data

    @property
    async def delete(self):
        for userkey in self.users.keys(): await self.delete_player(int(userkey))
        await lobbys.delete_one({"_id": self._id}, comment='Lobby_delete')

    async def add_player(self, user:DungPlayer, user_id:int):
        self['users'][str(user_id)] = user
        await lobbys.update_one({"_id": self._id}, 
                                {"$set": {f"users.{user_id}": user.__dict__}}, comment='Lobby_add_player')

    async def delete_player(self, user_id:int):
        player:DungPlayer = self['users'][str(user_id)].copy()

        if self.stage == 'preparation':
            await take_coins(user_id, player.coins, True)
            await AddListItems(user_id, player.inventory)

        del self['users'][str(user_id)]
        await lobbys.update_one({"_id": self._id}, 
                                {"$unset": {f"users.{user_id}": 0}}, comment='delete_player')

class Room:

    def __init__(self) -> None:

        self.type: str = ""
        self.next_room: bool = True
        self.image: str = ''

class Mob:

    def __init__(self) -> None:
        self._id: ObjectId = ObjectId()
        pass

