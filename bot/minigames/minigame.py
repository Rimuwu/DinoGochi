from bot.exec import bot
import random
from bot.minigames.minigame_registartor import Registry
from bot.modules.inline import list_to_inline
from aiogram import types
from bot.modules.logs import log
from bot.dbmanager import mongo_client
from bot.modules.overwriting.DataCalsses import DBconstructor

database = DBconstructor(mongo_client.minigames.online)

class MiniGame:

    # ======== CREATE ======== #
    """ Когда обхект класса создан """

    def __init__(self):
        self.GAME_ID = 'BASEMINIGAME' # Этот пункт обязательно должен быть изменён

        # ======== SESSION ======== #
        self._id = 0
        self.session_key = '0000'
        self.message_id = 0
        self.chat_id = 0
        self.user_id = 0

        # ======== BUTTONS ======== #
        self.ButtonsRegister = {
            "bn1": "button"
        }

        self.initialization()

    def initialization(self):
        """Вызывается при инициализации, создан для того, чтобы не переписывать init"""
        # ======== DATA ======== #
        pass

    def __str__(self):
        return f'{self.GAME_ID}'

    # ======== START ======== #
    """ Когда объект создан первый раз """

    async def StartGame(self, chat_id: int, user_id: int) -> None:
        """ Когда игра запускается впервые"""
        self.chat_id = chat_id
        self.user_id = user_id

        self.session_key = await SessionGenerator()
        Registry.save_class_object(self.GAME_ID, self.session_key, self)
        await self.Update()

        await self.MessageGenerator()

    async def ContinueGame(self, code: str) -> None:
        """ Когда игра продолжается после неожиданного завершения"""
        self.session_key = code
        await self.__LoadData()

        await self.MessageGenerator()

    # ======== END ======== #
    """ Когда игра завершена """

    async def EndGame(self): 
        """ Заканчивает игру """
        await delete_session(self.session_key)

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
            await self.Update()

    async def MessageGenerator(self) -> None:
        """ Генерирует сообщение """
        text = f'MesageGenerator {self.session_key}'
        markup = await self.MarkupGenerator()

        await self.MesageUpdate(text, markup)

    # ======== LOGIC ======== #
    """ Логика миниигры """

    async def __LoadData(self) -> None:
        """ Загрузка данных из базы"""
        self.__dict__ = await get_session(self.session_key)

    async def Update(self):
        """ Обновление данных в базе """
        await update_session(self.session_key, self.__dict__)

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

async def update_session(session_key: str, data: dict) -> None:
    upd = await database.update_one({'session_key': session_key}, 
                              {'$set': data},
                              comment='update_session_minigame')
    if upd.modified_count == 0:
        del data['_id']
        await database.insert_one(data,
                                  comment='update_session_minigame')

async def delete_session(session_key: str) -> None:
    await database.delete_one({'session_key': session_key},
                              comment='delete_session_minigame')

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