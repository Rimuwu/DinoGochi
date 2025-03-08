from bot.modules.inline import list_to_inline
from aiogram import types
from bot.modules.logs import log
from bot.minigames.minigame import MiniGame

class TestMiniGame(MiniGame):

    # ======== CREATE ======== #
    """ Когда обхект класса создан """

    def get_GAME_ID(self): return 'TESTMINIGAME'

    async def initialization(self):
        self.DEBUG_MODE = True

        self.score = 0
        self.max_score = 3
        self.time_i = 0
        self.max_time = 3

        self.ButtonsRegister = {
            "button1": 'button'
        }

        self.ThreadsRegister['timer'] = {
            "repeat": 5, 
            "col_repeat": 'inf', "function": 'timer',
            "last_start": 0
        }

    # ======== THREADS ======== #
    async def timer(self):
        """ Поток работы таймера """
        if self.time_i < self.max_time - 1:
            self.time_i += 1
            await self.Update()
            await self.MainGenerator()
        else:
            await self.MainGenerator(True)
            await self.EndGame()

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

    async def MainGenerator(self, end=False) -> None:
        """ Генерирует сообщение """
        if not end:
            text = f'Score {self.score} - max {self.max_score}\nGame time: {self.time_i * 5}s. / {self.max_time * 5}s.'
            markup = await self.MarkupGenerator()
        else:
            if self.score == self.max_score:
                text = 'Game WIN!'
            else:
                text = 'You LOSE!'
            markup = None

        await self.MesageUpdate(text=text, reply_markup=markup)

    # ======== LOGIC ======== #
    """ Логика миниигры """

    async def __on_score_change(self) -> None:
        await self.Update()

        if self.score >= self.max_score:
            await self.EndGame()
            await self.MainGenerator(True)
        else:
            await self.MainGenerator()

    # ======== BUTTONS ======== #
    """ Функции кнопок """

    async def button(self, callback: types.CallbackQuery):
        """ Обработка кнопки """

        self.score += 1
        log(f"Score: {self.score}")
        await self.__on_score_change()



TestMiniGame().RegistryMe() # Регистрация класса в реестре