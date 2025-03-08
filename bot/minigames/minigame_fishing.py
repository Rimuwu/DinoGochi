
from random import randint
import random
import time


from bot.modules.inline import list_to_inline
from aiogram import types
from aiogram.utils.keyboard import InlineKeyboardBuilder
from aiogram.types import InlineKeyboardButton

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

fishing_emoji = '🐟' # data - 1
predator_emoji = '🦈' # data - 2
rock_emoji = '🪨' # data - 3
grass_emoji = '🌿' # data - 4

def get_emoji(data: int) -> str:
    if data == 1:
        return fishing_emoji
    elif data == 2:
        return predator_emoji
    elif data == 3:
        return rock_emoji
    elif data == 4:
        return grass_emoji
    else:
        return '▫'

class FishingGame(MiniGame):

    # ======== CREATE ======== #
    """ Когда обхект класса создан """

    def get_GAME_ID(self): return 'FishingGame'

    async def initialization(self):
        self.DEBUG_MODE = True
        self.time_wait = 600

        self.score = 0
        self.stage: str = ''

        self.area = [
            [0, 0, 0, 0, 0, 0],
            [0, 0, 0, 0, 0, 0],
            [0, 0, 0, 0, 0, 0],
            [0, 0, 0, 0, 0, 0],
            [0, 0, 0, 0, 0, 0],
            [0, 0, 0, 0, 0, 0]
        ]

        self.choosed_positions = []
        self.max_choosed_positions = 3

        self.ButtonsRegister = {
            "button1": 'button',
            "sbt": 'stop_game_bt',
            "ср": 'choose_positions',
            "sr": 'square'
        }

    async def Custom_StartGame(self) -> None:
        await self.stage_edit('preparation')

    # ======== MARKUP ======== #
    """ Код для работы с меню """

    async def MarkupGenerator(self):
        """ Генерация меню """
        data = []
        
        if self.stage == 'preparation':
            data = [{'Start Game': self.CallbackGenerator('button1')}]
        elif self.stage == 'game':
            data = [{'Stop Game': self.CallbackGenerator('sbt'), 
                     'Choose Position': self.CallbackGenerator('choose_positions')}
                    ]
        elif self.stage == 'choose_positions':
            inline = InlineKeyboardBuilder()

            row_i = -1
            conlumn_i = -1
            for row in self.area:
                row_i += 1
                conlumn_i = -1
                for column in row:
                    conlumn_i += 1
                    data.append(
                        {get_emoji(column):
                            self.CallbackGenerator('square', data=f'{row_i}:{conlumn_i}')}
                    )

            inline.row(*[
                InlineKeyboardButton(text=list(i.keys())[0], 
                                     callback_data=list(i.values())[0]) for i in data], 
                       width=len(self.area[0]))

            return inline.as_markup(row_width=len(self.area[0]))

        return list_to_inline(data, 6)

    # ======== MESSAGE ======== #
    """ Код для генерации собщения и меню """

    async def AreaToMessage(self) -> str:
        message = ''

        for row in self.area:
            for column in row:
                message += ' ' + get_emoji(column) + ' '
            message += '\n'
        return message


    async def MainGenerator(self) -> None:
        """ Генерирует сообщение """
        markup = await self.MarkupGenerator()
        text = ''
        end_time = self.time_wait - int(time.time() - self.LAST_ACTION)

        if self.stage == 'preparation':
            text = f'Нажмите на кнопку, чтобы начать игру.\nВремя ожидания: {end_time}s'

        if self.stage == 'game':
            text = f'Ваш счёт: {self.score}\nВремя ожидания: {end_time}s\n\n'

        if self.stage == 'choose_positions':
            text = f'Выберите позиции для удара\nВыбраны: {self.choosed_positions}\nВремя ожидания: {end_time}s\n\n'

            text += await self.AreaToMessage()


        await self.MesageUpdate(text=text, reply_markup=markup)

    # ======== LOGIC ======== #
    """ Логика миниигры """

    async def AreaGenerator(self) -> None:
        count = {1: 3, 
             2: 1, 
             3: randint(1, 5), 
             4: randint(1, 4)}

        while any(val > 0 for val in count.values()):
            i = random.randint(0, len(self.area) - 1)
            j = random.randint(0, len(self.area[i]) - 1)
            if self.area[i][j] == 0:
                n = random.choice([key for key in count.keys() if count[key] > 0])
                self.area[i][j] = n
                count[n] -= 1

    async def stage_edit(self, new_stage: str) -> None:
        self.D_log(f'stage_edit {self.stage} -> {new_stage}')

        if self.stage == new_stage: return

        if self.stage == 'preparation':
            # del self.ThreadsRegister['timer']
            pass

        if new_stage == 'preparation':
            self.stage = 'preparation'

            self.ThreadsRegister['timer'] = {
                'repeat': 15,
                'col_repeat': 'inf',
                'function': 'end_game_timer',
                'last_start': 0
            }

        elif new_stage == 'game':
            self.stage = 'game'
            await self.AreaGenerator()

        elif new_stage == 'choose_positions':
            self.stage = 'choose_positions'

        await self.MainGenerator()
        await self.Update()

    async def end_game_timer(self):
        if time.time() - self.LAST_ACTION > self.time_wait: 
            await self.EndGame()
        await self.MainGenerator()

    # ======== BUTTONS ======== #
    """ Функции кнопок """

    async def button(self, callback: types.CallbackQuery):
        """ Обработка кнопки """

        await self.stage_edit('game')

    async def stop_game_bt(self, callback: types.CallbackQuery):
        await self.EndGame()
    
    async def choose_positions(self, callback: types.CallbackQuery):
        await self.stage_edit('choose_positions')

    async def square(self, callback: types.CallbackQuery):
        self.D_log(f'square {callback.data}')
        spl_data = callback.data.split(':')
        row = spl_data[3]
        column = spl_data[4]
        
        if [row, column] in self.choosed_positions:
            self.choosed_positions.remove([row, column])
        else:
            if len(self.choosed_positions) < self.max_choosed_positions:
                self.choosed_positions.append([row, column])

        await self.Update()
        await self.MainGenerator()


FishingGame().RegistryMe() # Регистрация класса в реестре