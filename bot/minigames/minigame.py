import asyncio

from bson import ObjectId
from bot.dataclasess.minigame import Button, PlayerData, SMessage, Stage, Thread, Waiter
from bot.exec import bot
import random
from bot.minigames.minigame_registartor import Registry
from bot.modules.inline import list_to_inline
from aiogram import types
from bot.modules.logs import log
from bot.dbmanager import mongo_client
from bot.modules.overwriting.DataCalsses import DBconstructor
import time


# Написать функции для управления юзерами, кнопками, вейтарами, тредами.


database = DBconstructor(mongo_client.minigames.online)

class MiniGame:

    # ======== CREATE ======== #
    """ Когда обхект класса создан """

    def __init__(self):
        # ======== GAME ======== #
        self.GAME_ID: str = self.get_GAME_ID() # Этот пункт обязательно должен быть изменён через перезаписанную функцию GET_GAME_ID

        self.active_threads: bool = True # Служит для паузы тасков
        self.__threads_work: bool = True # Служит для отключения цикла

        # ======== SESSION ======== #
        self._id: ObjectId = ObjectId()
        self.session_key: str = '0000'

        self.TIME_START: float = time.time() # Время начала игры
        self.LAST_ACTION: float = self.TIME_START

        self.PLAYERS: dict[str, PlayerData] = {
            str(0): PlayerData(user_id=0, chat_id=0,
                               user_name='', data={})
            } # Словарь игроков

        # ======== MESSAGES ======== #

        # Дополнительные сообщения в формате {'function_key': message_id}
        # function_key - просто ключ для чего юзается
        self.session_masseges: dict[str, SMessage] = {
            'main': SMessage(message_id=0, chat_id=0, data={})
        }

        # Функции отвечающие за генерацию текста для каждого типа сообщения
        self.message_generators: dict[str, str] = {
            'main': 'MainGenerator' # Код генератора: имя функции
        }

        # ======== BUTTONS ======== #
        self.ButtonsRegister: dict[str, Button] = {
            # Код для сокращения : {'function': имя функции, 'filters': [функции, которые вместе должны выдать True]}
            "bn1": Button(function='button', 
                    filters=['simple_filter'], active=True)
        }

        # ======== ContentWaiter ======== #
        # str, int, image, sticker

        # Отслеживание идёт только для main сообщения!
        # или по команде /context session_key ...
        self.WaiterRegister: dict[str, Waiter] = {
            # Тип данных: {'function': имя функции, 
            #              'active': True/False, 'data': ''}
            "str": Waiter(function='WaiterStr', 
                          active=True, data={})
        }

        # ======== THREADS ======== #
        # Желательно, чтобы repeat было кратно THREAD_TICK

        self.ThreadsRegister: dict[str, Thread] = {
            "check_session": Thread(30, 'inf', 'check_session', 0, True)
        }

        # ======== STAGES ======== #

        self.stages: dict[str, Stage] = {
            'preparation': Stage(
                [ {'thread': 'check_session', 'active': True} ], # Какие треды активировать
                [ {'button': 'bn1', 'active': True} ], # Какие кнопки активировать 
                [ {'waiter': 'str', 'active': True} ], # Какие вейтеры активиров
                'MainGenerator', # Основной обработчик состояния
                '', # Какую функцию запускае 
                {}
            )
        }

        # ======== SETTINGS ======== #
        self.DEBUG_MODE: bool = True # Включение логирования
        self.THREAD_TICK: int = 5

        self.edit_settings() # Функция только для изменения настроек

        asyncio.get_event_loop().create_task(self.initialization())
        self.D_log(f'Create MiniGame {self.__str__()}')

    def get_GAME_ID(self): 
        """ ВОзвращает идентификатор игры """
        return 'BASEMINIGAME'

    def edit_settings(self): 
        """ Только для изменения переменных и настроек до запуска инициализации"""
        pass

    async def initialization(self):
        """ Вызывается при инициализации, создан для того, чтобы не переписывать init """
        # ======== DATA ======== #
        pass

    def __str__(self):
        return f'{self.GAME_ID} {self.session_key}'
    
    # ======== STAGES ======== #
    
    async def AddStage(self, key: str, stage: Stage):
        """Добавляет новый этап в игру """
        pass
    
    async def DeleteStage(self, key: str):
        """ Удаляет этап из игры по ключу"""
        pass

    async def UserStage(self, user_id: int):
        """ Возвращает текущий этап пользователя """
        pass

    async def SetStage(self, stage: str, user_id: int | None = None):
        """ Переходит к этапу для всех пользователей или для одного """ 
        pass

    async def EditStage(self, key: str, stage: Stage):
        """ Изменяет этап по ключу """
        pass

    # ======== THREADS ======== #

    async def AddThread(self, key: str, thread: dict):
        """Добавляет новый поток в игру """
        pass
    
    async def DeleteThread(self, key: str):
        """ Удаляет поток из игры по ключу"""
        pass

    async def EditThread(self, key: str, thread: dict):
        """ Изменяет поток по ключу """
        pass

    async def GetThread(self, key: str):
        """ Возвращает поток по ключу """
        pass

    async def __run_threads(self):
        """ Запуск вечного цикла для проверки и выполнения потоков """
        while self.__threads_work:
            self.D_log(f'run_threads {list(self.ThreadsRegister.keys())}')

            await asyncio.sleep(self.THREAD_TICK)

            if self.active_threads:
                for key, thread in self.ThreadsRegister.items():
                    now = time.time()

                    if (thread['last_start'] + thread['repeat'] < now) and (thread['col_repeat'] == 'inf' or thread['col_repeat'] > 0) and ('active' not in thread or thread['active']):
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

        asyncio.create_task(self.__run_threads())

    async def Custom_StartGame(self) -> None:
        """ Когда игра запускается впервые (Создан, чтобы не переписывать StartGame) """
        pass 

    async def ContinueGame(self, code: str) -> None:
        """ Когда игра продолжается после неожиданного завершения"""
        self.session_key = code
        self.LAST_ACTION = time.time()
        await self.__LoadData()

        # await self.MessageGenerator()

        asyncio.create_task(self.__run_threads())

    # ======== END ======== #
    """ Когда игра завершена """

    async def EndGame(self): 
        """ Заканчивает игру """
        self.__threads_work = False
        self.active_threads = False

        try:
            await self.Custom_EndGame()
        except Exception as e:
            self.D_log(f'CustomEndGame error {e}')

        await delete_session(self._id)
        Registry.delete_class_object(self.GAME_ID, self.session_key)
    async def Custom_EndGame(self):
        """ Заканчивает игру (Создан, чтобы не переписывать EndGame) """
        pass

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
        data = self.session_masseges.get(func_key, {})

        if data.get('message_id'): message_id = data['message_id']
        else: message_id = 0

        if message_id and message_id != 0:
            try:
                await bot.delete_message(
                    chat_id=self.chat_id,
                    message_id=message_id
                )
            except: pass
            del self.session_masseges[func_key]

    async def MesageUpdate(self, func_key: str = 'main', text: str = '', reply_markup = None):
        """ Обновляет сообщение """
        if not text: return
        self.D_log(f'MesageUpdate {func_key}')

        data = self.session_masseges.get(func_key, {})
        if data.get('message_id'): message_id = data['message_id']
        else: 
            message_id = 0
            self.session_masseges[func_key] = {'message_id': 0}

        if message_id:
            try:
                msg = await bot.edit_message_text(
                    text=text,
                    chat_id=self.chat_id,
                    message_id=message_id,
                    reply_markup=reply_markup
                )
            except:
                await self.DeleteMessage(func_key)
                return None
        else:
            msg = await bot.send_message(
                text=text,
                chat_id=self.chat_id,
                reply_markup=reply_markup
            )
            self.session_masseges[func_key]['message_id'] = msg.message_id
            await self.Update()

        return msg

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
        lvl = 1
        if 'error' in text.lower(): lvl = 2

        if self.DEBUG_MODE or ignore:
            log(
                message=str(text), lvl=lvl, 
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
        self.D_log(f'Registry game {self.GAME_ID} start', ignore=True)
        Registry.register_game(self)


    # ======== FILTERS ======== #
    """ Фильтры для кнопок, функции получают callback и должны вернуть bool"""
    
    async def simple_filter(self, callback: types.CallbackQuery) -> bool:
        self.D_log(f'simple_filter {callback.data} -> True')
        return True

    # ======== BUTTONS ======== #
    """ Функции кнопок """
    
    async def AddButton(self, key: str, Button: Button):
        """ Добавление кнопки """
        pass
    
    async def DeleteButton(self, key: str):
        """ Удаление кнопки """
        pass

    async def EditButton(self, key: str, Button: Button):
        """ Редактирование кнопки """
        pass

    

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

        if button_function:
            # Проверка на фильтры
            filters = self.ButtonsRegister[key].get('filters', [])
            filter_results = [await getattr(self, filter_func)(callback) for filter_func in filters]
            self.D_log(f'filter_results {filter_results}')

            if all(filter_results) and ('active' not in self.ButtonsRegister[key] or self.ButtonsRegister[key]['active']):
                self.D_log(f'button_function {key} {callback.data}')
                await button_function(callback)
                return True
            else:
                self.D_log(f'button_function {key} not active or filters not passed')
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
        self.D_log(f'ActiveWaiter {key}')

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

    data = {key: value for key, value in data.items() if not callable(value)}

    await database.update_one({'_id': _id}, 
                              {'$set': data},
                              comment='update_session_minigame')
    # if upd.modified_count == 0:
    #     del data['_id']
    #     await database.insert_one(data,
    #                               comment='update_session_minigame')
    
async def insert_session(data: dict) -> ObjectId:
    data['_id'] = ObjectId()
    data = {key: value for key, value in data.items() if not callable(value)}

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