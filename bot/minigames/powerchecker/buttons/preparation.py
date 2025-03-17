


import time
from bot.minigames.powerchecker.minigame_powerchecker import PowerChecker
from bot.modules.decorators import register_method
from bot.modules.user.user import User, take_coins
from aiogram import types
from bot.modules.dinosaur.dinosaur import Dino


@register_method(PowerChecker)
async def PreparationMarkup(self):
    buttons = [
        {'text': 'max players', 'callback_data': self.CallbackGenerator('max_col')},
        {'text': '🦕', 'callback_data': self.CallbackGenerator('choose_dino')},
        {'text': '💰', 'callback_data': self.CallbackGenerator('choose_bet')},
        {'text': '🚪', 'callback_data': self.CallbackGenerator('end_game')},
    ]
    return self.list_to_inline(buttons)

@register_method(PowerChecker)
async def MainGenerator(self, user_id) -> None:
    text = 'main'
    await self.MesageUpdate(text=text)

@register_method(PowerChecker)
async def PreparationGenerator(self, user_id) -> None:
    self.D_log(f'PreparationGenerator {user_id}')
    owner_player = await self.GetPlayer(user_id)
    if owner_player is None:
        self.D_log('Owner player not found')

    dino_name = "Не выбран"
    bet_text = "Не выбрана"

    if 'dino' in owner_player.data and owner_player.data['dino']: # type: ignore
        dino = await Dino().create(owner_player.data['dino']) # type: ignore
        dino_name = dino.name if dino else dino_name

    if self.bet > 0:
        bet_text = str(self.bet)

    time_left = self.time_wait - (time.time() - self.LAST_ACTION)
    time_left_text = f'Время до удаления игры: {int(time_left)} секунд'

    text = f'Динозавр: {dino_name}\nСтавка: {bet_text}\nМакс. игроков: {self.col_players}\n{time_left_text}'
    markup = await self.PreparationMarkup()
    await self.MesageUpdate('main', text=text, reply_markup=markup)

@register_method(PowerChecker)
async def max_playersMarkup(self):
    buttons = [
        {'text': '2 players', 'callback_data': self.CallbackGenerator('col_players', '2')},
        {'text': '3 players', 'callback_data': self.CallbackGenerator('col_players', '3')},
        {'text': '4 players', 'callback_data': self.CallbackGenerator('col_players', '4')},
        {'text': 'back', 'callback_data': self.CallbackGenerator('to_preparation')},
    ]
    return self.list_to_inline(buttons, 3)

@register_method(PowerChecker)
async def ColPlayers_set(self, callback) -> None:
    col_players = callback.data.split(':')[3]
    self.col_players = col_players
    await self.Update()
    await self.SetStage('preparation')

@register_method(PowerChecker)
async def MaxPlayersGenerator(self, user_id) -> None:
    markup = await self.max_playersMarkup()
    text = 'Выберите максимальное количество игроков:'
    await self.MesageUpdate('main', text=text, reply_markup=markup)

@register_method(PowerChecker)
async def choose_dinoMarkup(self, user_id):
    
    user = await User().create(user_id)
    dinos = await user.get_dinos()
    
    buttons = [{'text': dino.name, 'callback_data': self.CallbackGenerator('choose_dino_set', dino.alt_id)} for dino in dinos]
    buttons.append({'text': 'back', 'ignore_row': 'True', 'callback_data': self.CallbackGenerator('to_preparation')})
    return self.list_to_inline(buttons, 2)

@register_method(PowerChecker)
async def ChooseDino_set(self, callback) -> None:
    dino_name = callback.data.split(':')[3]
    user_id = callback.from_user.id
    player = await self.GetPlayer(user_id)
    if player:
        player.data['dino'] = dino_name
        await self.EditPlayer(user_id, player)
    await self.Update()
    await self.SetStage('preparation')

@register_method(PowerChecker)
async def ChooseDinoGenerator(self, user_id) -> None:
    markup = await self.choose_dinoMarkup(user_id)
    text = 'Выберите динозавра:'
    await self.MesageUpdate('main', text=text, reply_markup=markup)

@register_method(PowerChecker)
async def choose_betMarkup(self):
    buttons = [
        {'text': 'back', 'callback_data': self.CallbackGenerator('to_preparation')},
    ]
    return self.list_to_inline(buttons, 1)
@register_method(PowerChecker)
async def ChooseBetGenerator(self, user_id) -> None:
    markup = await self.choose_betMarkup()
    text = 'Выберите ставку:'
    await self.MesageUpdate('main', text=text, reply_markup=markup)

@register_method(PowerChecker)
async def IntWaiter(self, message: types.Message, command: bool = False):
    if command: 
        coins = int(message.text.split(' ')[3]) # type: ignore
    else:
        coins = int(message.text) # type: ignore

    try:
        await message.delete()
    except: pass

    user_id = message.from_user.id # type: ignore
    user = await User().create(user_id)
    current_balance = user.coins

    if coins <= 0:
        await self.ServiceGenerator(user_id, 'zero')
        return

    if current_balance < coins:
        await self.ServiceGenerator(user_id, 'no_coins')
        return

    player = await self.GetPlayer(user_id)
    if player:
        previous_bet = self.bet
        self.bet = coins
        await self.Update()

        if previous_bet > 0:
            difference = coins - previous_bet
            if difference > 0:
                await take_coins(user_id, -difference, update=True)
            else:
                await take_coins(user_id, abs(difference), update=True)
        else:
            await take_coins(user_id, -coins, update=True)

        await self.SetStage('preparation')