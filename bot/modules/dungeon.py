import random
from bot.config import mongo_client
from bson.objectid import ObjectId
from typing import Union, Any
from motor import Neve

lobbys = mongo_client.dungeon.lobby

class Lobby:

    def __init__(self) -> None:
        self._id: ObjectId = ObjectId()

        self.dungeonid: int = 0 # id создателя
        self.users: dict[str, DungPlayer] = {} # Данные юзеров

        self.floor: dict[str, Any] = {} # Данные этажа
        self.rooms: dict[str, Room] = {} # Комнаты

        self.dungeon_stage: str = 'preparation' # Этап
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
        await lobbys.update_one({"dungeonid": self.dungeonid}, {"$set": {item:value}})

    def __str__(self) -> str:
        return str(self.__dict__)

    async def create(self, lobbyid:Union[int, ObjectId]):
        """ Создание класса лобби на основе данных из базы
        """
        find_result = await lobbys.find_one({"_id": lobbyid})
        if not find_result:
            find_result = await lobbys.find_one({"dungeonid": lobbyid})
        if find_result: 
            self.__dict__ = find_result

            users = {}
            for userkey, uservalue in find_result['users'].items(): # type: ignore
                user = DungPlayer().FromDict(uservalue, int(userkey), self.dungeonid)
                users[userkey] = user

        return self


class DungPlayer:

    def __init__(self) -> None:
        self._id: ObjectId = ObjectId() # Id данных юзера

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
                                {"$set": {f"users.{self.userid}": self.__dict__}})

class Room:

    def __init__(self) -> None:

        self.type: str = ""
        self.next_room: bool = True
        self.ready: list = []
        self.image: str = ''

class Mob:

    def __init__(self) -> None:
        self._id: ObjectId = ObjectId()
        pass

