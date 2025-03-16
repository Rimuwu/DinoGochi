import random
import time

from bot.modules.inline import list_to_inline
from aiogram import types
from bot.minigames.minigame import MiniGame, Button, PlayerData, SMessage, Stage, Thread, Waiter, stageButton, stageThread, stageWaiter
from bot.modules.user.user import User, take_coins, user_name
from bot.modules.dinosaur.dinosaur import Dino
from typing import Optional

class PowerChecker(MiniGame):

    def get_GAME_ID(self):
        return 'PowerChecker'

    def edit_settings(self):
        pass

    async def initialization(self, only_for: int = 0):
        self.DEBUG_MODE = True
        self.time_wait = 600

        self.only_for: int = only_for
        self.bet: int = 0

        self.ButtonsRegister = {
        }

        self.ThreadsRegister = {
            "timer": Thread(repeat=20, col_repeat='inf', function='timer', last_start=0, active=True)
        }

        self.WaiterRegister = {
            "str": Waiter(function='StrWaiter', active=False, data={}),
            "int": Waiter(function='IntWaiter', active=False, data={})
        }

        self.message_generators = {
            'main': 'MainGenerator',
        }

        await self.Update()

    async def Custom_StartGame(self) -> None:
        pass

    async def Custom_EndGame(self) -> None:
        pass

    async def MarkupGenerator(self):
        data = []
        return list_to_inline(data, 3)

    async def MainGenerator(self) -> None:
        markup = await self.MarkupGenerator()
        text = ''
        await self.MesageUpdate(text=text, reply_markup=markup)

    async def ServiceGenerator(self, mtype: str) -> None:
        if mtype == 'no_coins':
            text = 'Недостаточно монет.'
        elif mtype == 'zero':
            text = 'Ставка не может быть нулевой или меньше нуля.'
        await self.DeleteMessage('service')
        msg = await self.MesageUpdate('service', text=text)
        if isinstance(msg, types.Message):
            self.session_masseges['service'] = SMessage(message_id=msg.message_id, chat_id=msg.chat.id, data={})

    async def service_deleter(self):
        if 'service' not in self.session_masseges: return
        if 'last_action' not in self.session_masseges['service']: return
        if time.time() - self.session_masseges['service']['last_action'] >= 60:
            await self.DeleteMessage('service')

    async def timer(self):
        if time.time() - self.LAST_ACTION >= self.time_wait:
            await self.EndGame()
        else:
            await self.Update()

    async def StrWaiter(self, message: types.Message, command: bool = False):
        pass

    async def IntWaiter(self, message: types.Message, command: bool = False):
        pass

    async def check_user(self, callback: types.CallbackQuery) -> bool:
        status = self.activ_user == 0 or callback.from_user.id == self.activ_user
        if not status:
            await callback.answer('У вас нет прав на нажатие', True)
        return status

PowerChecker().RegistryMe() # Регистрация класса в реестре
