from bot.modules.inline import list_to_inline
from aiogram import types
from bot.modules.logs import log
from bot.minigames.minigame import MiniGame
from typing import Any


def search_in_radius(matrix: list, r: int, c: int, search: Any, R: int):
    """
    Ищет заданное значение в матрице в пределах заданного радиуса.
    Аргументы:
    matrix (list of list of int): Матрица, в которой производится поиск.
    r (int): Индекс строки, откуда начинается поиск.
    c (int): Индекс столбца, откуда начинается поиск.
    search (int): Значение, которое нужно найти.
    R (int): Радиус поиска. (>1)
    Возвращает:
    list of tuple: Список координат (строка, столбец), где найдено значение.
    """
    rows = len(matrix)
    cols = len(matrix[0]) 
    result = []

    for i in range(max(0, r - R), min(rows, r + R + 1)):
        for j in range(max(0, c - R), min(cols, c + R + 1)):
            if matrix[i][j] == search:
                result.append((i, j))

    return result

class FishingGame(MiniGame):

    # ======== CREATE ======== #
    """ Когда обхект класса создан """

    def initialization(self):
        self.GAME_ID = 'FishingGame'

        self.score = 0
        self.stage = 'choose_area'
        self.area = [
            [0, 0, 0, 0, 0, 0],
            [0, 0, 0, 0, 0, 0],
            [0, 0, 0, 0, 0, 0],
            [0, 0, 0, 0, 0, 0],
            [0, 0, 0, 0, 0, 0],
            [0, 0, 0, 0, 0, 0]
        ]
        
        self.fishing_emoji = '🐟' # data - 1
        self.predator_emoji = '🦈' # data - 2
        self.rock_emoji = '🪨' # data - 3
        self.grass_emoji = '🌿' # data - 4
        
        

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