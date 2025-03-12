


from aiogram import types
from bot.minigames.powerchecker.minigame_powerchecker import PowerChecker
from bot.modules.decorators import register_method
from bot.modules.dinosaur.dinosaur import Dino

@register_method(PowerChecker)
async def back_to(self, callback: types.CallbackQuery | None = None):
    if self.stage == 'preparation':
        self.ButtonsRegister = {
            "cd": {'function': 'choose_dino', 'filters': ['check_user']},
            "cb": {'function': 'choose_bet', 'filters': ['check_user']},
            "ns": {'function': 'next_stage', 'filters': ['check_user']},
            "eg": {'function': 'end_game', 'filters': ['check_user']},
        }
        self.WaiterRegister['int']['active'] = False
    elif self.stage == 'friend_wait':
        self.ButtonsRegister = {
            "fe": {'function': 'friend_enter', 'filters': ['check_user']},
            "eg": {'function': 'end_game', 'filters': ['check_user']},
        }
    await self.Update()
    await self.MainGenerator()

@register_method(PowerChecker)
async def choose_dino(self, callback: types.CallbackQuery):
    """ Обработка кнопки """

    self.ButtonsRegister = {
        "bp": {'function': 'back_to', 
                'filters': ['check_user']},
        "cdc": {'function': 'check_dino_choose', 
                'filters': ['check_user']}
    }
    await self.Update()
    await self.DinoChooseGenerator(self.user_id)

@register_method(PowerChecker)
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
            await self.back_to()
        else:
            await callback.answer('Динозавр занят', True)

@register_method(PowerChecker)
async def choose_bet(self, callback: types.CallbackQuery):
    """ Обработка кнопки """
    self.ButtonsRegister = {
        "bp": {'function': 'back_to', 
                'filters': ['check_user']},
    }

    self.WaiterRegister['int']['active'] = True
    await self.Update()

    await self.BetGenerator()

@register_method(PowerChecker)
async def next_stage(self, callback: types.CallbackQuery):

    if self.stage == 'preparation' and self.users['main']['dinosaur'] and self.bet:
        if self.only_for != 0:
            self.activ_user = self.only_for
            await self.Update()
        await self.stage_edit('friend_wait')

@register_method(PowerChecker)
async def end_game(self, callback: types.CallbackQuery):

    if self.user_id != callback.from_user.id: return

    if self.stage == 'preparation':
        self.D_log('end_game', True)
        await self.EndGame()