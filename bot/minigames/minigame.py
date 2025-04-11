import asyncio
from math import e

from bson import ObjectId
from bot.dataclasess.minigame import Button, PlayerData, SMessage, Stage, Thread, Waiter, stageButton, stageThread, stageWaiter
from bot.exec import bot
import random
from bot.minigames.minigame_registartor import Registry
from aiogram import types
from bot.modules.data_format import escape_markdown
from bot.modules.localization import get_lang
from bot.modules.logs import log
from bot.dbmanager import mongo_client
from bot.modules.overwriting.DataCalsses import DBconstructor
import time
from typing import Optional
from aiogram.types import Message

from bot.modules.user import user
from bot.modules.user.user import user_name

database = DBconstructor(mongo_client.minigames.online)

class MiniGame:

    # ======== CREATE ======== #
    """ Когда объект класса создан """

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

        self.PLAYERS: dict[str, PlayerData] = {} # Словарь игроков

        # ======== MESSAGES ======== #

        # function_key - просто ключ для чего юзается
        self.session_masseges: dict[str, SMessage] = {}

        # Функции отвечающие за генерацию текста для каждого типа сообщения
        self.message_generators: dict[str, str] = {
            'main': 'MainGenerator' # Код генератора: имя функции
        }

        # ======== BUTTONS ======== #
        self.ButtonsRegister: dict[str, Button] = {
            # Код для сокращения : {'function': имя функции, 'filters': [функции, которые вместе должны выдать True]}
            "bn1": Button(function='button', 
                          filters=['simple_filter'], 
                          active=True)
        }

        # ======== ContentWaiter ======== #
        # str, int, image, sticker

        # Отслеживание идёт только для main сообщения!
        # или по команде /context session_key ...
        self.WaiterRegister: dict[str, Waiter] = {
            "str": Waiter(function='WaiterStr', active=True, data={})
        }

        # ======== THREADS ======== #
        # Желательно, чтобы repeat было кратно THREAD_TICK

        self.ThreadsRegister: dict[str, Thread] = {
            "check_session": Thread(30, 'inf', 'check_session', 0, True)
        }

        # ======== STAGES ======== #

        self.Stages: dict[str, Stage] = {
            'preparation': Stage(
                [ stageThread(thread='check_session', data={'active': True}) ], # Какие треды активировать
                [ stageButton(button='bn1', data={'active': True}) ], # Какие кнопки активировать 
                [ stageWaiter(waiter='str', data={'active': True}) ], # Какие вейтеры активиров
                'main', # Ключ сообщения для
                '', # Какую функцию запускает при переходе
                {}
            )
        }

        # ======== SETTINGS ======== #
        self.DEACTIVATE_NOT_ACTIVE_BUTTONS: bool = True # Деактивация кнопок, которые не указаны как активные
        self.DEBUG_MODE: bool = True # Включение логирования
        self.THREAD_TICK: int = 5
        self.LANGUAGE: str = 'en'
        self.STAGE = ''

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
        self.Stages[key] = stage
        await self.Update()
        self.D_log(f'AddStage {key}')

    async def DeleteStage(self, key: str):
        """ Удаляет этап из игры по ключу"""
        if key in self.Stages:
            del self.Stages[key]
            await self.Update()
            self.D_log(f'DeleteStage {key}')
        else:
            self.D_log(f'DeleteStage {key} not found')

    async def UserStage(self, user_id: int):
        """ Возвращает текущий этап пользователя """
        player = self.PLAYERS.get(str(user_id))
        if player:
            return player.stage
        return None

    async def SetStage(self, stage: str, user_id: Optional[int] = None):
        """ Переходит к этапу для всех пользователей или для одного """ 

        await self.HandleStageChange(stage)

        if user_id is None:
            self.STAGE = stage

            for player in self.PLAYERS.values():
                player.stage = stage
                current_stage = self.Stages.get(stage)
                if current_stage:
                    # Отправка сообщения
                    await self.MessageGenerator(current_stage.stage_generator, player.user_id)

        else:
            player = self.PLAYERS.get(str(user_id))
            current_stage = self.Stages.get(stage)
            if player and current_stage: 
                player.stage = stage
                # Отправка сообщения
                await self.MessageGenerator(current_stage.stage_generator, player.user_id)

        await self.Update()
        self.D_log(f'SetStage {stage} for user {user_id}')

    async def EditStage(self, key: str, stage: Stage):
        """ Изменяет этап по ключу """
        if key in self.Stages:
            self.Stages[key] = stage
            await self.Update()
            self.D_log(f'EditStage {key}')
        else:
            self.D_log(f'EditStage {key} not found')

    async def ClearStage(self):
        """ Очищает этапы """
        self.Stages = {}
        await self.Update()
        self.D_log('ClearStage')
    
    async def HandleStageChange(self, stage: str):
        """ Обрабатывает изменения этапа """
        current_stage = self.Stages.get(stage)
        if not current_stage:
            self.D_log(f'Stage {stage} not found')
            return

        # Управление потоками
        await self.ManageThreads(current_stage.threads_active)
        
        # Управление ожиданиями
        await self.ManageWaiters(current_stage.waiter_active)

        # Управление кнопками
        await self.ManageButtons(current_stage.buttons_active)

        if self.DEACTIVATE_NOT_ACTIVE_BUTTONS:
            # Деактивация кнопок, которые не указаны как активные
            active_button_keys = {button.button for button in current_stage.buttons_active}
            for key, button in self.ButtonsRegister.items():
                if key not in active_button_keys:
                    button.active = False

        await self.Update()

        # Выполнение функций
        function = getattr(self, current_stage.to_function, None)
        if function: await function()

    async def ManageThreads(self, threads: list[stageThread]):
        """ Управляет потоками в зависимости от этапа """
        for thread in threads:
            key = thread.thread
            data = thread.data

            for attr, value in data.items():
                if key in self.ThreadsRegister:
                    setattr(self.ThreadsRegister[key], attr, value)
                else:
                    self.D_log(f'ManageThreads {key} not found')

    async def ManageButtons(self, buttons: list[stageButton]):
        """ Управляет кнопками в зависимости от этапа """
        for button in buttons:
            key = button.button
            data = button.data

            for attr, value in data.items():
                if key in self.ButtonsRegister:
                    setattr(self.ButtonsRegister[key], attr, value)
                else:
                    self.D_log(f'ManageButtons {key} not found')

    async def ManageWaiters(self, waiters: list[stageWaiter]):
        """ Управляет ожиданиями в зависимости от этапа """
        for waiter in waiters:
            key = waiter.waiter
            data = waiter.data

            for attr, value in data.items():
                if key in self.WaiterRegister:
                    setattr(self.WaiterRegister[key], attr, value)
                else:
                    self.D_log(f'ManageWaiters {key} not found')

    # ======== THREADS ======== #

    async def AddThread(self, key: str, thread: Thread):
        """ Добавляет новый поток в игру """
        self.ThreadsRegister[key] = thread
        await self.Update()
        self.D_log(f'AddThread {key}')

    async def DeleteThread(self, key: str):
        """ Удаляет поток из игры по ключу"""
        if key in self.ThreadsRegister:
            del self.ThreadsRegister[key]
            await self.Update()
            self.D_log(f'DeleteThread {key}')
        else:
            self.D_log(f'DeleteThread {key} not found')

    async def EditThread(self, key: str, thread: Thread):
        """ Изменяет поток по ключу """
        if key in self.ThreadsRegister:
            self.ThreadsRegister[key] = thread
            await self.Update()
            self.D_log(f'EditThread {key}')
        else:
            self.D_log(f'EditThread {key} not found')

    async def GetThread(self, key: str) -> Optional[Thread]:
        """ Возвращает поток по ключу """
        return self.ThreadsRegister.get(key)

    async def ClearThreads(self):
        """ Очищает потоки """
        self.ThreadsRegister = {}
        await self.Update()
        self.D_log('ClearThreads')

    async def __run_threads(self):
        """ Запуск вечного цикла для проверки и выполнения потоков """
        while self.__threads_work:
            # self.D_log(f'run_threads {list(self.ThreadsRegister.keys())}')

            await asyncio.sleep(self.THREAD_TICK)

            if self.active_threads:
                for key, thread in self.ThreadsRegister.items():
                    now = time.time()

                    if (thread.last_start + thread.repeat < now) and (thread.col_repeat == 'inf' or (isinstance(thread.col_repeat, int) and thread.col_repeat > 0)) and thread.active:
                        function = getattr(self, thread.function, None)
                        if function:

                            # self.D_log(f'start_thread {thread.function} | repeat {thread.repeat} | col_repeat {thread.col_repeat}')

                            try:
                                await function()
                            except Exception as e:
                                self.D_log(f'thread_error {thread.function} {e}')

                            thread.last_start = now

                            if isinstance(thread.col_repeat, int):
                                thread.col_repeat -= 1

                                if thread.col_repeat <= 0:
                                    del self.ThreadsRegister[key]

                            await self.Update()

    # ======== THREADS ======== #

    async def check_session(self):
        """ Поток для отключения игры если в базе нет сессии """
        if not await check_session(self.session_key):
            await self.EndGame()

    # ======== START ======== #
    """ Когда объект создан первый раз """

    async def StartGame(self, chat_id: int, user_id: int, 
                        message: Message, **kwargs) -> None:
        """ Когда игра запускается впервые """
        await self.AddPlayer(user_id, chat_id, await user_name(user_id))
        self.LANGUAGE = await get_lang(user_id)

        # Сохраняем данные в базе
        self.session_key = await SessionGenerator()
        Registry.save_class_object(self.GAME_ID, self.session_key, self)
        await insert_session(self.__dict__)

        # Отправляем сообщение
        await self.CreateMessage(user_id, chat_id, 'main', 
                                 'preparation message for start game...')

        await self.Custom_StartGame(user_id, chat_id, message, **kwargs)

        asyncio.create_task(self.__run_threads())

    async def Custom_StartGame(self, user_id: int, chat_id: int, message: Message, **kwargs) -> None:
        """ Когда игра запускается впервые (Создан, чтобы не переписывать StartGame) """
        pass 

    async def ContinueGame(self, code: str) -> None:
        """ Когда игра продолжается после неожиданного завершения """
        self.session_key = code
        self.LAST_ACTION = time.time()
        await self.__LoadData()

        await self.Custom_ContinueGame()

        asyncio.create_task(self.__run_threads())
    
    async def Custom_ContinueGame(self) -> None:
        """ Когда игра продолжается после неожиданного завершения (Создан, чтобы не переписывать ContinueGame) """
        pass

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
        
        # Вызов функции EndGameGenerator
        await self.EndGameGenerator()
        
        # Удаление всех сообщений, кроме 'main'
        keys_to_delete = [key for key in self.session_masseges if key != 'main']
        for key in keys_to_delete:
            await self.DeleteMessage(func_key=key)

        await delete_session(self._id)
        Registry.delete_class_object(self.GAME_ID, self.session_key)

    async def Custom_EndGame(self):
        """ Заканчивает игру (Создан, чтобы не переписывать EndGame) """
        pass

    # ======== MARKUP ======== #
    """ Код для работы с меню """

    def CallbackGenerator(self, button_key: str, data: str = '') -> str:
        """Генерирует callback для кнопки"""

        if button_key not in self.ButtonsRegister:
            raise ValueError(f'CallbackGenerator {button_key} not found')

        text = f'minigame:{self.session_key}:{button_key}'
        if data: text += f':{data}' # 3-... аргумент
        return text

    async def MarkupGenerator(self):
        """ Генерация меню """
        buttons = [
            {'text': 'Button 1', 'callback_data': self.CallbackGenerator('bn1')},
            # Добавьте другие кнопки здесь
        ]
        return self.list_to_inline(buttons)

    # ======== MESSAGE ======== #
    """ Код для генерации собщения и меню """

    async def EndGameGenerator(self):
        text = f'Игра {self.session_key} завершена'
        await self.MesageUpdate('main', text=text)

    async def GetMessageGenerator(self, func_key: str = 'main'):
        generator = self.message_generators.get(func_key, 'error_find_generator')
        # self.D_log(f'GetMessageGenerator {func_key} -> {generator}')
        return generator

    async def DeleteMessage(self, func_key: str = 'main') -> None:
        """ Удаляет сообщение """
        data = self.session_masseges.get(func_key, 
                                         SMessage(message_id=0, chat_id=0, 
                                                  data={}, parse_mode=None
                                                  ))
        self.D_log(f'DeleteMessage {func_key}')

        message_id = data.message_id
        chat_id = data.chat_id

        if message_id and message_id != 0:
            try:
                await bot.delete_message(
                    chat_id=chat_id,
                    message_id=message_id
                )
            except: pass
            del self.session_masseges[func_key]
            await self.Update()

    async def CreateMessage(self, user_id: int, chat_id: int, func_key: str = 'main', text = 'create message...', parse_mode: Optional[str] = 'Markdown') -> types.Message:
        """ Создает сообщение """
        self.D_log(f'CreateMessage {func_key}')

        msg = await bot.send_message(
            text=text,
            chat_id=chat_id,
            reply_markup=self.list_to_inline([]), # Пустая клавиатура
            parse_mode=parse_mode
        )
        self.session_masseges[func_key] = SMessage(message_id=msg.message_id,
                                                   chat_id=msg.chat.id, data={'author': user_id}, parse_mode=parse_mode)
        await self.Update()

        return msg

    async def MesageUpdate(self, func_key: str = 'main', text: str = '', reply_markup = None):
        """ Обновляет сообщение """
        if not text: return
        # self.D_log(f'MesageUpdate {func_key}')

        data = self.session_masseges.get(func_key, SMessage(message_id=0, chat_id=0, data={}, parse_mode=None))
        # self.D_log(f'MesageUpdate {func_key} data {data}')

        message_id = data.message_id
        chat_id = data.chat_id
        parse_mode = data.parse_mode

        if not chat_id:
            self.D_log(f'MesageUpdate {func_key} failed: chat_id is {chat_id} message_id is {message_id}')
            return None

        if message_id:
            try:
                msg = await bot.edit_message_text(
                    text=text,
                    chat_id=chat_id,
                    message_id=message_id,
                    reply_markup=reply_markup,
                    parse_mode=parse_mode
                )
            except Exception as e:
                if 'message is not modified' in str(e):
                    return None
                else:
                    self.D_log(f'MesageUpdate1 {func_key} failed: {e}')
                    # await self.DeleteMessage(func_key)
                    return None
        else:
            await self.CreateMessage(404, chat_id, func_key)

        return msg

    async def MainGenerator(self, user_id: int) -> None:
        """ Генерирует сообщение """
        text = f'MesageGenerator {self.session_key}'
        markup = await self.MarkupGenerator()

        await self.MesageUpdate(text=text, reply_markup=markup)

    async def MessageGenerator(self, func_key: str = 'main',
                               user_id: int = 0,
                               *args, **kwargs):
        """ Функция определяет какая функция отвечает за генерацию текста """
        func_name = await self.GetMessageGenerator(func_key)
        Generator_func = getattr(self, func_name, None)

        if Generator_func:
            await Generator_func( user_id, *args, **kwargs )
        else:
            self.D_log(f'Error: Message generator function {func_name} not found, {self.message_generators}')

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

        # Получаем данные сессии из базы данных
        data = await get_session(self.session_key)

        # Десериализация данных
        self.PLAYERS = {k: PlayerData(**v) for k, v in data.get('PLAYERS', {}).items()}
        self.session_masseges = {k: SMessage(**v) for k, v in data.get('session_masseges', {}).items()}
        self.ButtonsRegister = {k: Button(**v) for k, v in data.get('ButtonsRegister', {}).items()}
        self.WaiterRegister = {k: Waiter(**v) for k, v in data.get('WaiterRegister', {}).items()}
        self.ThreadsRegister = {k: Thread(**v) for k, v in data.get('ThreadsRegister', {}).items()}
        self.Stages = {
            k: Stage(
                threads_active=[stageThread(**t) for t in v['threads_active']],
                buttons_active=[stageButton(**b) for b in v['buttons_active']],
                waiter_active=[stageWaiter(**w) for w in v['waiter_active']],
                stage_generator=v['stage_generator'],
                to_function=v['to_function'],
                data=v['data']
            ) for k, v in data.get('Stages', {}).items()
        }

        # Обновление остальных атрибутов
        for key, value in data.items():
            if key not in ['PLAYERS', 'session_masseges', 'ButtonsRegister', 'WaiterRegister', 'ThreadsRegister', 'Stages']: 
                setattr(self, key, value)

    async def Update(self):
        """ Обновление данных в базе """

        # Сериализация данных
        serialized_data = {key: serialize(value) for key, value in self.__dict__.items() if not callable(value)}

        # Красивый вывод логов
        if self.DEBUG_MODE:
            old_data = await get_session(self.session_key)
            if old_data:
                changed_keys = compare_dicts(old_data, serialized_data)

                if changed_keys:
                    txt = '\n'.join([f'{key} | {old_value} -> {new_value}' for key, old_value, new_value in changed_keys])

                    self.D_log(txt)

        # Обновление в базе
        await update_session(self._id, serialized_data)

    def RegistryMe(self):
        """ Регистрирует класс в локальной базе данных """
        self.D_log(f'Registry game {self.GAME_ID} start', ignore=True)
        Registry.register_game(self)


    # ======== FILTERS ======== #
    """ Фильтры для кнопок, функции получают callback и должны вернуть bool"""

    async def simple_filter(self, callback: types.CallbackQuery) -> bool:
        self.D_log(f'simple_filter {callback.data} -> True')
        return True

    async def owner_filter(self, callback: types.CallbackQuery) -> bool:
        status = callback.from_user.id == self.owner_id
        if not status:
            await callback.answer('Only for owner!')
        return status

    async def player_filter(self, callback: types.CallbackQuery) -> bool:
        status = str(callback.from_user.id) in self.PLAYERS
        if not status:
            await callback.answer('Only for players!')
        return status

    async def message_author_filter(self, callback) -> bool:
        if 'author' in self.session_masseges['main'].data:

            for key, message_data in self.session_masseges.items():
                if message_data.message_id == callback.message.message_id:
                    if message_data.data['author'] == callback.from_user.id:
                        return True

        await callback.answer('Only for message author!')
        return False

    # ======== BUTTONS ======== #
    """ Функции кнопок """

    async def AddButton(self, key: str, button: Button):
        """ Добавление кнопки """
        self.ButtonsRegister[key] = button
        await self.Update()
        self.D_log(f'AddButton {key}')

    async def DeleteButton(self, key: str):
        """ Удаление кнопки """
        if key in self.ButtonsRegister:
            del self.ButtonsRegister[key]
            await self.Update()
            self.D_log(f'DeleteButton {key}')
        else:
            self.D_log(f'DeleteButton {key} not found')

    async def EditButton(self, key: str, button: Button):
        """ Редактирование кнопки """
        if key in self.ButtonsRegister:
            self.ButtonsRegister[key] = button
            await self.Update()

            self.D_log(f'EditButton {key}')
        else:
            self.D_log(f'EditButton {key} not found')

    async def ClearButtons(self):
        """ Очистка кнопок """
        self.ButtonsRegister = {}
        await self.Update()
        self.D_log('ClearButtons')

    async def ActiveButton(self, key: str, callback: types.CallbackQuery):
        """ Запускает функции отвечающей за кнопку """
        self.LAST_ACTION = time.time()
        await self.Update()

        self.D_log(f'ActiveButton {key} {callback.data}')

        if key not in self.ButtonsRegister: 
            self.D_log(f'ActiveButton {key} not found')
            return False

        button = self.ButtonsRegister[key]

        # Проверка на фильтры
        filters = button.filters
        filter_results = [await getattr(self, filter_func)(callback) for filter_func in filters]

        if all(filter_results) and button.active:
            button_function = getattr(self, button.function, None)

            if button_function:
                self.D_log(f'button_function {key} {button_function.__name__} {callback.data}')
                await button_function(callback)
                return True

            if button.stage and button.stage in self.Stages:
                self.D_log(f'button_stage {key} {callback.data}')
                await self.SetStage(button.stage, callback.from_user.id)
                return True

            if not button.stage and button.stage not in self.Stages:
                self.D_log(f'button_function {key} stage not found')
        else:
            self.D_log(f'button_function {key} not active[{button.active}] or filters{filter_results} not passed')
        return False

    async def DEV_BUTTON(self, callback: types.CallbackQuery):
        pass

    async def button(self, callback: types.CallbackQuery):
        """ Обработка кнопки """
        ...
    
    # ======== PLAYER ======== #
    """ Функции для работы с игроками """

    @property
    def owner(self):
        return self.PLAYERS.get(
            list(self.PLAYERS.keys())[0]
        )

    @property
    def owner_id(self):
        if self.PLAYERS:
            return self.PLAYERS.get(
                list(self.PLAYERS.keys())[0]
            ).user_id # type: ignore
        return 0


    def standart_player_data(self):
        """ Стандартные данные для игрока НАДО ПЕРЕПИСЫВАТЬ!"""

        return {}

    async def AddPlayer(self, user_id: int, chat_id: int, user_name: str, stage: str = '', data: Optional[dict] = None):
        """ Добавление игрока + данные из standart_player_data"""
        self.PLAYERS[str(user_id)] = PlayerData(
            user_id=user_id, chat_id=chat_id, 
            user_name=escape_markdown(user_name), stage=stage, data=data or self.standart_player_data())

        await self.Update()
        self.D_log(f'AddPlayer {user_id}')

    async def DeletePlayer(self, user_id: int):
        """ Удаление игрока """
        if str(user_id) in self.PLAYERS:
            del self.PLAYERS[str(user_id)]
            await self.Update()
            self.D_log(f'DeletePlayer {user_id}')
        else:
            self.D_log(f'DeletePlayer {user_id} not found')
    
    async def EditPlayer(self, user_id: int, player: PlayerData):
        """ Редактирование игрока """
        if str(user_id) in self.PLAYERS:
            self.PLAYERS[str(user_id)] = player
            await self.Update()
            self.D_log(f'EditPlayer {user_id}')
        else:
            self.D_log(f'EditPlayer {user_id} not found')

    async def ClearPlayers(self):
        """ Очистка игроков """
        self.PLAYERS = {}
        await self.Update()
        self.D_log('ClearPlayers')
    
    async def GetPlayer(self, user_id: int) -> Optional[PlayerData]:
        return self.PLAYERS.get(str(user_id), None)

    # ======== ContenWaiter ======== #

    async def AddWaiter(self, key: str, waiter: Waiter):
        """ Добавление ожидания """
        self.WaiterRegister[key] = waiter
        await self.Update()
        self.D_log(f'AddWaiter {key}')

    async def DeleteWaiter(self, key: str):
        """ Удаление ожидания """
        if key in self.WaiterRegister:
            del self.WaiterRegister[key]
            await self.Update()
            self.D_log(f'DeleteWaiter {key}')
        else:
            self.D_log(f'DeleteWaiter {key} not found')

    async def EditWaiter(self, key: str, waiter: Waiter):
        """ Редактирование ожидания """
        if key in self.WaiterRegister:
            self.WaiterRegister[key] = waiter
            await self.Update()
            self.D_log(f'EditWaiter {key}')
        else:
            self.D_log(f'EditWaiter {key} not found')

    async def ClearWaiters(self):
        """ Очистка ожиданий """
        self.WaiterRegister = {}
        await self.Update()
        self.D_log('ClearWaiters')

    async def ActiveWaiter(self, key: str, message: types.Message, 
                           command: bool = False):
        """ Запускает функции отвечающей за ожидающие определённый контент """
        self.LAST_ACTION = time.time()
        await self.Update()
        self.D_log(f'ActiveWaiter {key}')

        if key not in self.WaiterRegister: 
            return False

        waiter = self.WaiterRegister[key]
        waiter_function = getattr(self, waiter.function, None)

        if waiter_function and waiter.active: 
            self.D_log(f'waiter_function {key} {message.text}')
            await waiter_function(message, command)
            return True
        return False

    async def StrWaiter(self, message: types.Message, command: bool = False):
        await message.answer(f'Standart message waiter -> {message.text}')
    
    
    # ======== SERVICE ======== #
    """ Служебные функции """

    def list_to_inline(self, buttons, row_width=3):
        """ Преобразует список кнопок в inline-клавиатуру """
        inline_keyboard = []
        row = []
        for button in buttons:
            if 'ignore_row' in button and button['ignore_row'].lower() == 'true':
                inline_keyboard.append(row)
                row = []
                inline_keyboard.append([types.InlineKeyboardButton(**button)])
                continue
            row.append(types.InlineKeyboardButton(**button))
            if len(row) == row_width:
                inline_keyboard.append(row)
                row = []
        if row:
            inline_keyboard.append(row)
        return types.InlineKeyboardMarkup(inline_keyboard=inline_keyboard)


async def check_session(session_key: str) -> bool:
    res = await database.find_one({'session_key': session_key},
                                  comment='check_session_minigame')
    return bool(res)

async def update_session(_id: ObjectId, data: dict) -> None:

    await database.update_one({'_id': _id}, 
                              {'$set': data},
                comment='update_session_minigame')

async def insert_session(data: dict) -> ObjectId:
    data['_id'] = ObjectId()
    serialized_data = {key: serialize(value) for key, value in data.items() if not callable(value)}

    result = await database.insert_one(serialized_data, comment='insert_session_minigame')
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

def serialize(value):
    if isinstance(value, dict):
        return {k: serialize(v) for k, v in value.items()}
    elif isinstance(value, list):
        return [serialize(v) for v in value]
    elif hasattr(value, '__dict__'):
        return serialize(value.__dict__)
    elif callable(value):
        return None
    else:
        return value