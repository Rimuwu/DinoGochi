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
        self.GAME_ID: str = self.get_GAME_ID() # Этот пункт обязательно должен быть изменён через перезаписанную функцию GET_GAME_ID

        self.active_threads: bool = True # Служит для паузы тасков
        self.__threads_work: bool = True # Служит для отключения цикла
        self.THREAD_TICK: int = 5

        # ======== SESSION ======== #
        self._id: ObjectId = ObjectId()
        self.session_key: str = '0000'
        self.chat_id: int = 0
        self.user_id: int = 0

        self.PLAYERS: list = [] # Используется для проверки запуска игры

        # ======== MESSAGES ======== #

        # Дополнительные сообщения в формате {'function_key': message_id}
        # function_key - просто ключ для чего юзается
        self.session_masseges: dict = {
            'main': 0
        }

        # Функции отвечающие за генерацию текста для каждого типа сообщения
        self.message_generators: dict = {
            'main': 'MainGenerator' # Код генератора: имя функции
        }

        # ======== BUTTONS ======== #
        self.ButtonsRegister: dict = {
            # Код для сокращения : {'function': имя функции, 'filters': [функции, которые вместе должны выдать True]}
            "bn1": {'function': 'button', 'filters': ['simple_filter']} 
        }

        # ======== ContenWaiter ======== #
        # str, int, image, sticker

        # Отслеживание идёт только для main сообщения!
        # или по команде /context session_key ...
        self.WaiterRegister: dict = {
            # Тип данных: {'function': имя функции, 
            #              'active': True/False, 'data': ''}
            "str": {'function': 'WaiterStr', 'active': True, 'data': {}} 
        }

        # ======== THREADS ======== #
        # Желательно, чтобы repeat было кратно 5

        self.ThreadsRegister: dict = {
            "check_session": {"repeat": 30, "col_repeat": 'inf', 
                              "function": 'check_session',
                              "last_start": 0}
        }

        self.TIME_START: float = time.time() # Время начала игры
        self.LAST_ACTION: float = self.TIME_START

        self.DEBUG_MODE: bool = False # Включение логирования

        asyncio.get_event_loop().create_task(self.initialization())

    def get_GAME_ID(self): return 'BASEMINIGAME'

    async def initialization(self):
        """ Вызывается при инициализации, создан для того, чтобы не переписывать init """
        # ======== DATA ======== #
        pass

    def __str__(self):
        return f'{self.GAME_ID} {self.session_key}'

    # ======== THREADS ======== #

    async def run_threads(self):
        """ Запуск вечного цикла для проверки и выполнения потоков """
        while self.__threads_work:
            self.D_log(f'run_threads {list(self.ThreadsRegister.keys())}')

            await asyncio.sleep(self.THREAD_TICK)

            if self.active_threads:
                for key, thread in self.ThreadsRegister.items():
                    now = time.time()

                    if (thread['last_start'] + thread['repeat'] < now) and (thread['col_repeat'] == 'inf' or thread['col_repeat'] > 0):
                        function = getattr(self, thread['function'], None)
                        if function:

                            self.D_log(f'start_thread {thread["function"]} | repeat {thread["repeat"]} | col_repeat {thread["col_repeat"]}')
                            
                            try:
                                await function()
                            except Exception as e:
                                self.D_log(f'thread_error {thread["function"]} {e}')

                            thread['last_start'] = now

                            if thread['col_repeat'] != 'inf':
                                thread['col_repeat'] -= 1

                                if thread['col_repeat'] <= 0:
                                    del self.ThreadsRegister[key]

                            await self.Update()

    # ======== THREADS ======== #
    async def check_session(self):
        """ Поток для отключения игры если в базе нет сессии"""
        if not await check_session(self.session_key):
            await self.EndGame()

    # ======== START ======== #
    """ Когда объект создан первый раз """

    async def StartGame(self, chat_id: int, user_id: int) -> None:
        """ Когда игра запускается впервые"""
        self.chat_id = chat_id
        self.user_id = user_id

        self.PLAYERS.append(user_id)

        # Сохраняем данные в базе
        self.session_key = await SessionGenerator()
        Registry.save_class_object(self.GAME_ID, self.session_key, self)
        await insert_session(self.__dict__)

        # Отправляем сообщение
        await self.MessageGenerator()

        await self.Custom_StartGame()

        asyncio.create_task(self.run_threads())

    async def Custom_StartGame(self) -> None:
        """ Когда игра запускается впервые (Создан, чтобы не переписывать StartGame) """
        pass 

    async def ContinueGame(self, code: str) -> None:
        """ Когда игра продолжается после неожиданного завершения"""
        self.session_key = code
        self.LAST_ACTION = time.time()
        await self.__LoadData()

        # await self.MessageGenerator()

        asyncio.create_task(self.run_threads())

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
        button_key = next((key for key, value in self.ButtonsRegister.items() if value['function'] == function_name), function_name)

        text = f'minigame:{self.session_key}:{button_key}'
        if data: text += f':{data}' # 3-... аргумент
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

    async def GetMessageGenerator(self, func_key: str = 'main'):
        return self.message_generators.get(func_key, 
                            list(self.message_generators.keys())[0]) 

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
        if not text: return
        self.D_log(f'MesageUpdate {func_key}')

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

    async def MainGenerator(self) -> None:
        """ Генерирует сообщение """
        text = f'MesageGenerator {self.session_key}'
        markup = await self.MarkupGenerator()

        await self.MesageUpdate(text=text, reply_markup=markup)

    async def MessageGenerator(self, func_key: str = 'main', 
                               *args, **kwargs):
        """ Функция определяет какая функция отвечает за генерацию текста """
        func_name = await self.GetMessageGenerator(func_key)
        Generator_func = getattr(self, func_name)

        await Generator_func( *args, **kwargs )

    # ======== LOGIC ======== #
    """ Логика миниигры """

    def D_log(self, text: str, ignore: bool = False) -> None:
        """ Логирование в дебаг моде """
        if self.DEBUG_MODE or ignore:
            log(
                message=str(text), lvl=2, 
                prefix=f'MiniGame {self.__str__()}'
            )

    async def __LoadData(self) -> None:
        """ Загрузка данных из базы"""
        self.__dict__ = await get_session(self.session_key)

    async def Update(self):
        """ Обновление данных в базе """

        if self.DEBUG_MODE:
            old_data = await get_session(self.session_key)
            if old_data:
                changed_keys = compare_dicts(old_data, self.__dict__)

                if changed_keys:
                    txt = '\n'.join([f'{key} | {old_value} -> {new_value}' for key, old_value, new_value in changed_keys])

                    self.D_log(txt)

        await update_session(self._id, self.__dict__)

    def RegistryMe(self):
        """ Регистрирует класс в локальной базе данных """
        self.D_log(f'Registry game {self.GAME_ID}', ignore=True)
        Registry.register_game(self)

    # ======== FILTERS ======== #
    """ Фильтры для кнопок, функции получают callback и должны вернуть bool"""
    
    async def simple_filter(self, callback: types.CallbackQuery) -> bool:
        self.D_log(f'simple_filter {callback.data} -> True')
        return True

    # ======== BUTTONS ======== #
    """ Функции кнопок """

    async def ActiveButton(self, key: str, callback: types.CallbackQuery):
        """ Запускает функции отвечающей за кнопку """
        self.LAST_ACTION = time.time()
        await self.Update()
        self.D_log(f'ActiveButton {key} {callback.data}')

        if key not in self.ButtonsRegister: 
            self.D_log(f'ActiveButton {key} not found')
            return False

        button_function = getattr(self, 
                                  self.ButtonsRegister[key]['function'], None)
        self.D_log(f'button_function {button_function}')

        if button_function:
            # Проверка на фильтры
            filters = self.ButtonsRegister[key].get('filters', [])
            filter_results = [await getattr(self, filter_func)(callback) for filter_func in filters]
            self.D_log(f'filter_results {filter_results}')

            if all(filter_results):
                self.D_log(f'button_function {key} {callback.data}')
                await button_function(callback)
                return True
        else:
            self.D_log(f'button_function {key} not found')
        return False

    async def DEV_BUTTON(self, callback: types.CallbackQuery):
        pass

    async def button(self, callback: types.CallbackQuery):
        """ Обработка кнопки """
        ...

    # ======== ContenWaiter ======== #

    async def ActiveWaiter(self, key: str, message: types.Message, 
                           command: bool = False):
        """ Запускает функции отвечающей за ожидающие определённый контент """
        self.LAST_ACTION = time.time()
        await self.Update()
        self.D_log(f'GetWaiter {key}')

        if key not in self.WaiterRegister: 
            return False
        waiter_function = getattr(self, 
                    self.WaiterRegister[key]['function'], None)
        if waiter_function and self.WaiterRegister[key]['active']: 
            self.D_log(f'waiter_function {key} {message.text}')
            await waiter_function(message, command)
            return True
        return False

    async def StrWaiter(self, message: types.Message, command: bool = False):
        await message.answer(f'Standart message waiter -> {message.text}')


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

def compare_dicts(d1, d2, path=''):
    changed_keys = []
    for k in d1.keys() | d2.keys():
        new_path = f'{path}.{k}' if path else k
        if k not in d1:
            changed_keys.append((new_path, None, d2[k]))
        elif k not in d2:
            changed_keys.append((new_path, d1[k], None))
        elif isinstance(d1[k], dict) and isinstance(d2[k], dict):
            compare_dicts(d1[k], d2[k], new_path)
        elif d1[k] != d2[k]:
            changed_keys.append((new_path, d1[k], d2[k]))

    return changed_keys