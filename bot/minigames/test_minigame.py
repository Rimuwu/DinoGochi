from bot.modules.inline import list_to_inline
from aiogram import types
from bot.modules.logs import log
from bot.minigames.minigame import MiniGame

from bot.minigames.minigame_registartor import Registry

class TestMiniGame(MiniGame):

    # ======== CREATE ======== #
    """ Когда обхект класса создан """

    def initialization(self):
        self.GAME_ID = 'TESTMINIGAME'
        
        self.score = 0
        self.max_score = 3

        self.ButtonsRegister = {
            "button1": 'button'
        }

    # ======== MARKUP ======== #
    """ Код для работы с меню """

    async def MarkupGenerator(self):
        """ Генерация меню """

        return list_to_inline(
            [
                {'button': self.CallbackGenerator('button1')}
            ]
        )

    # ======== MESSAGE ======== #
    """ Код для генерации собщения и меню """

    async def MessageGenerator(self, end=False) -> None:
        """ Генерирует сообщение """
        if not end:
            text = f'Score {self.score} - max {self.max_score}'
            markup = await self.MarkupGenerator()
        else:
            text = 'Game WIN!'
            markup = None

        await self.MesageUpdate(text=text, reply_markup=markup)

    # ======== LOGIC ======== #
    """ Логика миниигры """

    async def __on_score_change(self) -> None:
        await self.Update()

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



TestMiniGame().RegistryMe() # Регистрация класса в реестре