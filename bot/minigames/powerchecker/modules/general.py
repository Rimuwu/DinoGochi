

from bot.minigames.powerchecker.minigame_powerchecker import PowerChecker
from bot.modules.decorators import register_method
from bot.modules.user.user import User


@register_method(PowerChecker)
async def dino_markup(self, user_id):
    """ Возвращает разметку для выбора динозавра с ключом dino_set \n
        Ключ кнопки возвращения берётся из stage[STAGE].data['back_key']
    """

    user = await User().create(user_id)
    dinos = await user.get_dinos()

    buttons = [
        {'text': '🦕 ' + dino.name, 
         'callback_data': self.CallbackGenerator('dino_set', f'{dino.alt_id}:{user_id}')
         } for dino in dinos
    ]
    buttons.append({'text': 'back', 'ignore_row': 'True', 
                    'callback_data': self.CallbackGenerator(
                        self.Stages[self.STAGE].data['back_key'])})

    return self.list_to_inline(buttons, 2)