import asyncio

from bson import ObjectId
from bot.exec import bot
import random
from bot.minigames.minigame_registartor import Registry
from bot.modules.inline import list_to_inline
from aiogram import types
from bot.modules.logs import log
from bot.dbmanager import mongo_client
from bot.modules.overwriting.DataCalsses import DBconstructor
import time

database = DBconstructor(mongo_client.minigames.online)

class MiniGame:

    # ======== CREATE ======== #
    """ Когда обхект класса создан """

    def __init__(self):
        self.GAME_ID: str = 'BASEMINIGAME' # Этот пункт обязательно должен быть изменён
        self.active_threads: bool = True # Служит для паузы тасков
        self.__threads_work: bool = True # Служит для отключения цикла
        self.thread_tick: int = 5

        # ======== SESSION ======== #
        self._id: ObjectId = ObjectId()
        self.session_key: str = '0000'
        self.chat_id: int = 0
        self.user_id: int = 0

        # Дополнительные сообщения в формате {'function_key': message_id}
        # function_key - просто ключ для чего юзается
        self.session_masseges: dict = {
            'main': 0
        }

        # ======== BUTTONS ======== #
        self.ButtonsRegister: dict = {
            "bn1": "button"
        }

        # ======== THREADS ======== #
        # Желательно, чтобы repeat было кратно 5

        self.ThreadsRegister: dict = {
            "timer": {"repeat": 5, "col_repeat": 1, "function": 'timer',
                      "last_start": 0
                      }  # col_repeat - кол-во повторений (или 'inf')
        }

        self.initialization()

    def initialization(self):
        """ Вызывается при инициализации, создан для того, чтобы не переписывать init """
        # ======== DATA ======== #
        pass

    def __str__(self):
        return f'{self.GAME_ID}'

    # ======== THREADS ======== #

    async def run_threads(self):
        """ Запуск вечного цикла для проверки и выполнения потоков """
        while self.__threads_work:
            await asyncio.sleep(self.thread_tick)

            if self.active_threads:
                for key, thread in self.ThreadsRegister.items():
                    now = time.time()

                    if (thread['last_start'] + thread['repeat'] < now) and (thread['col_repeat'] == 'inf' or thread['col_repeat'] > 0):
                        function = getattr(self, thread['function'], None)
                        if function:
                            try:
                                await function()
                            except Exception as e:
                                log(f'MiniGame {self.__qualname__} ERROR in thread: {e}', 3)

                            thread['last_start'] = now

                            if thread['col_repeat'] != 'inf':
                                thread['col_repeat'] -= 1

                                if thread['col_repeat'] <= 0:
                                    del self.ThreadsRegister[key]

                            await self.Update()

    # ======== THREADS ======== #
    async def timer(self):
        """ Поток работы таймера """
        pass

    # ======== START ======== #
    """ Когда объект создан первый раз """

    async def StartGame(self, chat_id: int, user_id: int) -> None:
        """ Когда игра запускается впервые"""
        self.chat_id = chat_id
        self.user_id = user_id

        # Сохраняем данные в базе
        self.session_key = await SessionGenerator()
        Registry.save_class_object(self.GAME_ID, self.session_key, self)
        await insert_session(self.__dict__)

        # Отправляем сообщение
        await self.MessageGenerator()

        # Запускаем доп процессы (Последняя строчка в функции)
        await self.run_threads()

    async def ContinueGame(self, code: str) -> None:
        """ Когда игра продолжается после неожиданного завершения"""
        self.session_key = code
        await self.__LoadData()

        await self.MessageGenerator()

        # Запускаем доп процессы (Последняя строчка в функции)
        await self.run_threads()

    # ======== END ======== #
    """ Когда игра завершена """

    async def EndGame(self): 
        """ Заканчивает игру """
        self.__threads_work = False
        self.active_threads = False

        await delete_session(self._id)
        Registry.delete_class_object(self.GAME_ID, self.session_key)

    # ======== MARKUP ======== #
    """ Код для работы с меню """
    
    def CallbackGenerator(self, function_name: str, data: str = '') -> str:
        text = f'minigame:{self.session_key}:{function_name}'
        if data: text += f':{data}'
        return text

    async def MarkupGenerator(self):
        """ Генерация меню """

        return list_to_inline(
            [
                {'button': self.CallbackGenerator('bn1')}
            ]
        )

    # ======== MESSAGE ======== #
    """ Код для генерации собщения и меню """

    async def DeleteMessage(self, func_key: str = 'main') -> None:
        """ Удаляет сообщение """
        message_id = self.session_masseges.get(func_key, 0)

        if message_id:
            try:
                await bot.delete_message(
                    chat_id=self.chat_id,
                    message_id=message_id
                )
            except: pass
            del self.session_masseges[func_key]

    async def MesageUpdate(self, func_key: str = 'main', text: str = '', reply_markup = None) -> None:
        """ Обновляет сообщение """
        message_id = self.session_masseges.get(func_key, 0)

        if message_id:
            try:
                await bot.edit_message_text(
                    text=text,
                    chat_id=self.chat_id,
                    message_id=message_id,
                    reply_markup=reply_markup
                )
            except: pass
        else:
            msg = await bot.send_message(
                text=text,
                chat_id=self.chat_id,
                reply_markup=reply_markup
            )
            self.session_masseges[func_key] = msg.message_id
            await self.Update()

    async def MessageGenerator(self) -> None:
        """ Генерирует сообщение """
        text = f'MesageGenerator {self.session_key}'
        markup = await self.MarkupGenerator()

        await self.MesageUpdate(text=text, reply_markup=markup)

    # ======== LOGIC ======== #
    """ Логика миниигры """

    async def __LoadData(self) -> None:
        """ Загрузка данных из базы"""
        self.__dict__ = await get_session(self.session_key)

    async def Update(self):
        """ Обновление данных в базе """
        await update_session(self._id, self.__dict__)

    def GetButton(self, key: str):
        """ Возвращение функции отвечающей за кнопку """
        if key not in self.ButtonsRegister:
            return None
        return getattr(self, self.ButtonsRegister[key], None)

    def RegistryMe(self):
        """ Регистрирует класс в локальной базе данных """
        Registry.register_game(self)

    # ======== BUTTONS ======== #
    """ Функции кнопок """

    async def button(self, callback: types.CallbackQuery):
        """ Обработка кнопки """
        ...


async def check_session(session_key: str) -> bool:
    res = await database.find_one({'session_key': session_key},
                                  comment='check_session_minigame')
    return bool(res)

async def update_session(_id: ObjectId, data: dict) -> None:
    await database.update_one({'_id': _id}, 
                              {'$set': data},
                              comment='update_session_minigame')
    # if upd.modified_count == 0:
    #     del data['_id']
    #     await database.insert_one(data,
    #                               comment='update_session_minigame')
    
async def insert_session(data: dict) -> ObjectId:
    del data['_id']
    result = await database.insert_one(data, comment='insert_session_minigame')
    return result.inserted_id

async def delete_session(_id: ObjectId) -> None:
    await database.delete_one({'_id': _id}, comment='delete_session_minigame')

async def get_session(session_key: str) -> dict:
    data = await database.find_one({'session_key': session_key},
                                   comment='get_session_minigame')
    if data: return data
    return {}

async def SessionGenerator(length: int = 4) -> str:
    code = ''.join([random.choice('0123456789qwertyuiopasdfghjklzxcvbnm') for _ in range(length)])
    if await check_session(code):
        return await SessionGenerator(length)
    return code