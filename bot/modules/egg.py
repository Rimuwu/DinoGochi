

from random import choice, sample
from time import time

from bot.const import DINOS
from bot.const import GAME_SETTINGS as GS

from bot.modules.logs import log

from bson.objectid import ObjectId
from bot.dbmanager import mongo_client
from bot.modules.overwriting.DataCalsses import DBconstructor
from bot.modules.images import create_egg_image

incubations = DBconstructor(mongo_client.dinosaur.incubation)


class Egg:

    def __init__(self):
        """Создание объекта яйца.

            Логика:
            - Сначалао создаётся сообщение с выбором яйца и заносятся данные для взаимодействия с ним
            (Если предмет использован повторно, то прошлое сообщение удаляется и создаётся новое)
            - Если сообщение висит больше 12 часов, то сообщение удаляется и данные очищаются
            - Если пользователь выбрал яйцо, то начинается инкубация (удаляются данные после # ---)

        """

        self._id = ObjectId()
        self.incubation_time = 0

        self.owner_id = 0

        self.egg_id = 0
        self.quality = 'random'
        self.dino_id = 0

        self.stage: str = 'incubation'  # incubation / choosing

        # --- Данные удаляемые после выбора яйца ---
        self.id_message: int = 0  # Сообщение с выбором яйца
        self.eggs = [0, 0, 0] # Список яиц, которые были выбраны
        self.dinos = [0, 0, 0] # Список динозавров, которые были выбраны

        self.start_choosing: int = 0  # Время начала выбора яйца

    def choose_eggs(self):
        """Выбор трёх яиц для инкубации.
        """

        if self.quality == 'random':
            dinos_qual = DINOS['data']['dino']
        else:
            dinos_qual = DINOS[self.quality]

        self.dinos = sample(dinos_qual, 3)
        self.eggs = []

        for dino_id in self.dinos:
            dino_data = get_dino_data(dino_id)
            egg_id = dino_data.get('egg', 0)
            self.eggs.append(egg_id)

    async def create(self, baseid: ObjectId):
        res = await incubations.find_one({"_id": baseid}, comment='Egg_create')
        if res:
            self.UpdateData(res)
            return self
        return None

    def UpdateData(self, data):
        if data: self.__dict__ = data

    def __str__(self) -> str:
        return f'{self._id} {self.quality}'

    async def update(self, update_data: dict):
        """
        {"$set": {'stats.eat': 12}} - установить
        {"$inc": {'stats.eat': 12}} - добавить
        """
        data = await incubations.update_one({"_id": self._id}, update_data, comment='Egg_update')
        # self.UpdateData(data) #Не получается конвертировать в словарь возвращаемый объект
        return data

    async def insert(self):
        """Вставка яйца в базу данных.
        """
        log(prefix='InsertEgg',
            message=f'owner_id: {self.owner_id} data: {self.__dict__}',
            lvl=0)

        return await incubations.insert_one(self.__dict__, comment='Egg_insert')

    async def delete(self):
        await incubations.delete_one({'_id': self._id}, comment='Egg_delete')

    async def image(self, lang: str='en'):
        """Сгенерировать изображение объекта.
        """
        t_inc = self.remaining_incubation_time()
        return await create_egg_image(egg_id=self.egg_id, rare=self.quality, seconds=t_inc, lang=lang)

    def remaining_incubation_time(self):
        return max(0, self.incubation_time - int(time()))

def get_dino_data(data_id: int):
    data = {}
    try:
        data = DINOS['elements'][str(data_id)]
    except Exception as e:
        log(f'Ошибка в получении данных динозавра -> {e}', 3)
    return data

def random_dino(quality: str='com') -> int:
    """Рандомизация динозавра по редкости
    """
    return choice(DINOS[quality])

async def incubation_egg(egg_id: int, owner_id: int, 
                         inc_time: int=0, quality: str='random', 
                         dino_id: int=0):
    """Создание инкубируемого динозавра
    """
    
    res = await incubations.find_one(
        {'owner_id': owner_id, 
         'stage': 'choosing',
         'quality': quality
        }, comment='incubation_egg_find')

    egg = Egg()
    if res:
        egg.__dict__ = res
    else:
        log(prefix='InsertEgg ERROR', message=f'owner_id: {owner_id} data: {res}', lvl=0)
        return None

    egg.incubation_time = inc_time + int(time())
    egg.egg_id = egg_id
    egg.owner_id = owner_id
    egg.quality = quality

    if not dino_id:
        egg.dino_id = egg.dinos[egg.eggs.index(egg_id)]
    else:
        egg.dino_id = dino_id

    if inc_time == 0: #Стандартное время инкцбации
        egg.incubation_time = int(time()) + GS['first_dino_time_incub']

    egg.stage = 'incubation'  # Устанавливаем стадию инкубации
    del egg.id_message, egg.eggs, egg.dinos, egg.start_choosing

    log(prefix='InsertEgg', 
        message=f'owner_id: {owner_id} data: {egg.__dict__}', lvl=0)
    
    return await incubations.update_one(
        {'_id': egg._id}, {'$set': egg.__dict__,
                           '$unset': {
                               'id_message': 1,
                               'eggs': 1,
                               'dinos': 1,
                               'start_choosing': 1,
                           }
                        }
        )