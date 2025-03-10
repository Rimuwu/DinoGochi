

import random
import time

from bot.modules.inline import list_to_inline
from aiogram import types
from aiogram.utils.keyboard import InlineKeyboardBuilder
from aiogram.types import InlineKeyboardButton

from bot.minigames.minigame import MiniGame
from typing import Any
from bot.modules.user import user
from bot.exec import bot

from bot.modules.user.user import User, take_coins, user_name
from bot.modules.dinosaur.dinosaur import Dino

class PowerChecker(MiniGame):

    # ======== CREATE ======== #
    """ Когда обхект класса создан """

    def get_GAME_ID(self): return 'PowerChecker'

    async def initialization(self, only_for: int = 0):
        self.DEBUG_MODE = True
        self.time_wait = 600

        self.only_for: int = only_for # Если отправлено ответом на сообщение, то только для этого пользователя

        self.opponent: int = 0
        self.activ_user: int = self.user_id

        self.bet: int = 0 # ставка (если не доиграли - возвращаем деньги обоим игрокам)

        """ preparation - выбор динозавра автора и ставки
            friend_wait - ожидание подключения другого игрока
            game - игра 
            end_game - конец игры
            
        """
        self.stage: str = '' 

        self.users = {
            'main': {
                'dinosaur': None,
                'tree_trunk': None,
                'name': ''
            },
            'opponent': {
                'dinosaur': None,
                'tree_trunk': None,
                'name': ''
            }
        }

        self.ButtonsRegister = {
            "cd": {'function': 'choose_dino', 'filters': []},
            "cb": {'function': 'choose_bet', 'filters': []},
            "ns": {'function': 'next_stage', 'filters': []},
            "eg": {'function': 'end_game', 'filters': []},
        }

        self.ThreadsRegister['timer'] = {
            "repeat": 20, 
            "col_repeat": 'inf', "function": 'timer',
            "last_start": 0
        }

        self.WaiterRegister: dict = {
            "str": {'function': 'StrWaiter', 'active': False, 'data': {}},
            "int": {'function': 'IntWaiter', 'active': False, 'data': {}}
        }

        self.message_generators: dict = {
            'main': 'MainGenerator',
            'dino_choose': 'DinoChooseGenerator',
            'service': 'ServiceGenerator'
        }

        await self.Update()


    async def Custom_StartGame(self) -> None:
        self.users['main']['name'] = await user_name(self.user_id)
        await self.Update()

        await self.stage_edit('preparation')
    
    async def Custom_EndGame(self) -> None:
        await take_coins(self.user_id, self.bet, True)

        if self.opponent:
            await take_coins(self.opponent, self.bet, True)

    # ======== MARKUP ======== #
    """ Код для работы с меню """

    async def MarkupGenerator(self):
        """ Генерация меню """
        data = []

        if self.stage == 'preparation':
            data = [{'Choose Dino': self.CallbackGenerator('choose_dino'),
                     'Choose Bet': self.CallbackGenerator('choose_bet'),
                     'End Game': self.CallbackGenerator('end_game')
                    }]

            if self.users['main']['dinosaur'] and self.bet:
                data.append({'Start Game': self.CallbackGenerator('next_stage')})

        return list_to_inline(data, 3)

    # ======== MESSAGE ======== #
    """ Код для генерации собщения и меню """

    async def MainGenerator(self) -> None:
        """ Генерирует сообщение """
        markup = await self.MarkupGenerator()
        text = ''

        if self.stage == 'preparation':
            dino_text = 'не выбран'
            if self.users['main']['dinosaur']:
                dino = await Dino().create(self.users['main']['dinosaur'])
                dino_text = dino.name

            bet_text = 'не выбрана'
            if self.bet: bet_text = self.bet

            text = f'Тут идёт описание игры\n\n🦕 Динозавр: {dino_text}\n💸 Ставка: {bet_text}'


        await self.MesageUpdate(text=text, reply_markup=markup)
    
    async def DinoChooseGenerator(self, user_id: int) -> None:
        """ Генерирует сообщение """
        user = await User().create(user_id)
        dinos = await user.get_dinos()
        dino_list = []
        for dino in dinos:
            dino_list.append({
                f'{dino.name}': 
                    self.CallbackGenerator('check_dino_choose', dino.alt_id)
                })
        dino_list.append({'Back': self.CallbackGenerator('back_to_preparation')})
        markup = list_to_inline(dino_list, 2)

        text = 'Выберите динозавра (список свободных дино): \n\n'

        await self.MesageUpdate('main', text=text, reply_markup=markup)
    
    async def BetGenerator(self) -> None:
        """ Генерирует сообщение """
        text = f'С помощью ответа на это сообщение введите сумму ставки в монетах, либо по команде /context {self.session_key} <значение>\n\nСумма будет снята с вашего баланса.'
        
        markup = list_to_inline([{
            'Back': self.CallbackGenerator('back_to_preparation')}
                                 ], 2)
        await self.MesageUpdate('main', text=text, reply_markup=markup)
    
    async def ServiceGenerator(self, mtype: str) -> None:
        """ Генерирует сообщение """

        if mtype == 'no_coins':
            text = 'Недостаточно монет.'
        elif mtype == 'zero':
            text = 'Ставка не может быть нулевой или меньше нуля.'

        await self.DeleteMessage('service')
        
        await self.MesageUpdate('service', text=text)
        self.session_masseges['service'] = {'message_id': 0, 
                                            'last_action': time.time()}

    # ======== LOGIC ======== #
    """ Логика миниигры """
    
    async def service_deleter(self):
        if 'service' not in self.session_masseges: return
        if 'last_action' not in self.session_masseges['service']: return

        if time.time() - self.session_masseges['service']['last_action'] >= 60:
            await self.DeleteMessage('service')

    async def timer(self):
        """ Поток работы таймера """
        if time.time() - self.LAST_ACTION >= self.time_wait:
            # await self.MessageGenerator('main')
            await self.EndGame()
        else:
            await self.Update()
            # await self.MessageGenerator('main')

    async def stage_edit(self, new_stage: str) -> None:
        self.D_log(f'stage_edit {self.stage} -> {new_stage}')

        if self.stage == new_stage: return

        if new_stage == 'preparation':
            self.stage = 'preparation'
            
            self.ThreadsRegister['service_deleter'] = {
                "repeat": 20, 
                "col_repeat": 'inf', "function": 'service_deleter',
                "last_start": 0
            }

        await self.Update()
        await self.MainGenerator()

    async def end_game_timer(self):
        if time.time() - self.LAST_ACTION >= self.time_wait: 
            await self.EndGame()
        await self.MainGenerator()

    # ======== BUTTONS ======== #
    """ Функции кнопок """
    
    async def back_to_preparation(self, callback: types.CallbackQuery):
        self.ButtonsRegister = {
            "cd": {'function': 'choose_dino', 'filters': ['check_user']},
            "cb": {'function': 'choose_bet', 'filters': ['check_user']},
            "ns": {'function': 'next_stage', 'filters': ['check_user']},
            "eg": {'function': 'end_game', 'filters': ['check_user']},
        }
        self.WaiterRegister['int']['active'] = False
        await self.Update()
        await self.MainGenerator()

    async def choose_dino(self, callback: types.CallbackQuery):
        """ Обработка кнопки """

        self.ButtonsRegister = {
            "bp": {'function': 'back_to_preparation', 
                   'filters': ['check_user']},
            "cdc": {'function': 'check_dino_choose', 
                    'filters': ['check_user']}
        }
        await self.Update()
        await self.DinoChooseGenerator(self.user_id)

    async def check_dino_choose(self, callback: types.CallbackQuery):
        args = callback.data.split(':')
        if len(args) < 3: return
        dino_alt_id = args[3]
        
        data_path = 'main'
        if callback.from_user.id != self.user_id:
            data_path = 'opponent'

        dino = await Dino().create(dino_alt_id)
        if dino: 

            if await dino.status == 'pass':
                self.users[data_path]['dinosaur'] = dino_alt_id
                await self.Update()
                await self.back_to_preparation(callback)
            else:
                await callback.answer('Динозавр занят', True)

    async def choose_bet(self, callback: types.CallbackQuery):
        """ Обработка кнопки """
        self.WaiterRegister['int']['active'] = True
        await self.Update()
        
        await self.BetGenerator()

    async def next_stage(self, callback: types.CallbackQuery):
        pass

    async def end_game(self, callback: types.CallbackQuery):
        pass

    # ======== ContenWaiter ======== #
    async def StrWaiter(self, message: types.Message, command: bool = False):
        pass

    async def IntWaiter(self, message: types.Message, command: bool = False):
        
        if message.from_user.id != self.activ_user: return
        if self.stage != 'preparation': return

        coins = int(message.text)
        if coins <= 0: 
            await self.ServiceGenerator('zero')
            await message.delete()
            return

        elif not await take_coins(-coins, False): 
            await self.ServiceGenerator('no_coins')
            await message.delete()
            return 
        
        else:
            await take_coins(-(coins-self.bet), True)
            self.bet = coins
            await self.Update()

        await self.back_to_preparation(message)

    # ======== FILTERS ======== #

    async def check_user(self, callback: types.CallbackQuery) -> bool:
        status = callback.from_user.id == self.activ_user
        if not status:
            await callback.answer('У вас нет прав на нажатие', True)
        return status


PowerChecker().RegistryMe() # Регистрация класса в реестре