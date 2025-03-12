


from aiogram import types
from bot.minigames.powerchecker.minigame_powerchecker import PowerChecker
from bot.modules.decorators import register_method
from bot.modules.user.user import take_coins

@register_method(PowerChecker)
async def friend_enter(self, callback: types.CallbackQuery):

    if self.stage == 'friend_wait':
        if self.user_id == callback.from_user.id: return
        else:
            if not await take_coins(self.user_id, self.bet, False):
                await callback.answer('Недостаточно монет', True)
                await self.back_to()
                return

            self.activ_user = callback.from_user.id
            self.opponent = callback.from_user.id
            await self.Update()

            await take_coins(self.user_id, self.bet, True)

            self.ButtonsRegister = {
                "bw": {'function': 'back_to_wait', 
                    'filters': ['check_user']},
                "cdc": {'function': 'check_dino_choose', 
                        'filters': ['check_user']}
            }

            await self.DinoChooseGenerator(self.activ_user)