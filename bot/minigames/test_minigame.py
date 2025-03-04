from bot.exec import main_router, bot
import random
from bot.modules.inline import list_to_inline
from aiogram import types
from bot.modules.logs import log

BASE_PATH = ''
DATA_PREFIX = ''

database = {}

async def SessionGenerator():
    code = ''.join([random.choice('0123456789qwertyuiopasdfghjklzxcvbnm') for _ in range(4)])
    if code in database: # временная реализация базы
        return await SessionGenerator()
    return code

class MiniGame:
    INLINE_PREFIX = 'minigame'

    # ======== CREATE ======== #
    """ Когда обхект класса создан """
    
    def __init__(self):
        
        # ======== SESSION ======== #
        self._id = 0
        self.session_key = '0000'
        self.message_id = 0
        self.chat_id = 0
        self.user_id = 0

        # ======== DATA ======== #
        self.score = 0
        self.max_score = 3

        # ======== BUTTONS ======== #
        self.ButtonsRegister = {
            "bt": self.button
        }

    # ======== START ======== #
    """ Когда объект создан первый раз """

    async def StartGame(self, chat_id: int, user_id: int) -> None:
        """ Когда игра запускается впервые"""
        self.chat_id = chat_id
        self.user_id = user_id

        self.session_key = await SessionGenerator()
        await self.__Update()

        await self.MessageGenerator()

    async def ContinueGame(self, code: str) -> None:
        """ Когда игра продолжается после неожиданного завершения"""
        self.session_key = code
        await self.__LoadData()

        await self.MessageGenerator()

    # ======== END ======== #
    """ Когда игра завершена """

    async def EndGame(self): 
        global database
        """ Заканчивает игру """
        # await self.DeleteMessage()
        del database[self.session_key] # временная реализация базы

    # ======== MARKUP ======== #
    """ Код для работы с меню """
    
    async def MarkupGenerator(self):
        """ Генерация меню """

        return list_to_inline(
            [
                {'button': f'minigame:{self.session_key}:bt'}
            ]
        )

    # ======== MESSAGE ======== #
    """ Код для генерации собщения и меню """

    async def DeleteMessage(self) -> None:
        """ Удаляет сообщение """
        if self.message_id:
            try:
                await bot.delete_message(
                    chat_id=self.chat_id,
                    message_id=self.message_id
                )
            except: pass
            self.message_id = 0

    async def MesageUpdate(self, text, reply_markup) -> None:
        """ Обновляет сообщение """

        if self.message_id:
            try:
                await bot.edit_message_text(
                    text=text,
                    chat_id=self.chat_id,
                    message_id=self.message_id,
                    reply_markup=reply_markup
                )
            except: pass
        else:
            msg = await bot.send_message(
                text=text,
                chat_id=self.chat_id,
                reply_markup=reply_markup
            )
            self.message_id = msg.message_id
            await self.__Update()

    async def MessageGenerator(self, end=False) -> None:
        """ Генерирует сообщение """
        if not end:
            text = f'Score {self.score} - max {self.max_score}'
            markup = await self.MarkupGenerator()
        else:
            text = 'Game WIN!'
            markup = None
        
        await self.MesageUpdate(text, markup)

    # ======== LOGIC ======== #
    """ Логика миниигры """
    
    async def __LoadData(self) -> None:
        global database
        """ Загрузка данных из базы"""
        self.__dict__ = database[self.session_key].copy() # временная реализация базы

    async def __Update(self):
        global database
        """ Обновление данных в базе """
        database[self.session_key] = self.__dict__ # временная реализация базы

    def ButtonsRegistr(self, key: str):
        """ Возвращение функции отвечающей за кнопку """
        if key not in self.ButtonsRegister:
            return None
        return self.ButtonsRegister[key]

    async def __on_score_change(self) -> None:
        await self.__Update()
        
        if self.score >= self.max_score:
            await self.EndGame()
            await self.MessageGenerator(True)
        else:
            await self.MessageGenerator()

    # ======== BUTTONS ======== #
    """ Функции кнопок """

    async def button(self, callback: types.CallbackQuery):
        """ Обработка кнопки """ 
        self.score += 1
        log(f"Score: {self.score}")
        await self.__on_score_change()