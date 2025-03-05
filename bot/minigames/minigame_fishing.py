from bot.modules.inline import list_to_inline
from aiogram import types
from bot.modules.logs import log
from bot.minigames.minigame import MiniGame

class FishingGame(MiniGame):

    # ======== CREATE ======== #
    """ Когда обхект класса создан """

    def initialization(self):
        self.GAME_ID = 'FishingGame'

        self.score = 0
        self.stage = ''
        self.area = [
            [0, 0, 0, 0, 0, 0],
            [0, 0, 0, 0, 0, 0],
            [0, 0, 0, 0, 0, 0],
            [0, 0, 0, 0, 0, 0],
            [0, 0, 0, 0, 0, 0],
            [0, 0, 0, 0, 0, 0]
        ]
        
        

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
    
    

    # ======== BUTTONS ======== #
    """ Функции кнопок """

    async def button(self, callback: types.CallbackQuery):
        """ Обработка кнопки """



FishingGame().RegistryMe() # Регистрация класса в реестре