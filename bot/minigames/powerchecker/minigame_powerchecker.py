import random
import time

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
        self.col_players: int = 2
        self.bet: int = 0

        self.ButtonsRegister = {
            'max_col': Button(function='MaxCol', filters=['owner_filter'], active=False),
            'choose_dino': Button(function='ChooseDino', filters=['owner_filter'], active=False),
            'choose_bet': Button(function='ChooseBet', filters=['owner_filter'], active=False),
            'end_game': Button(function='EndGame_c', filters=['owner_filter'], active=False),
            'start_game': Button(function='StartGame', filters=['owner_filter'], active=False),

            # Кнопка для возвращения в меню подготовки
            'to_preparation': Button(function='ToPreparation', filters=['owner_filter'], active=False),

            # Кнопка для выбора количества игроков
            'col_players': Button(function='ColPlayers_set', filters=['owner_filter'], active=False),

            # Кнопка для выбора динозавра
            'choose_dino_set': Button(function='ChooseDino_set', filters=['owner_filter'], active=False),

            # Кнопка для выбора ставки
            'choose_bet_set': Button(function='ChooseBet_set', filters=['owner_filter'], active=False),
        }

        self.ThreadsRegister['end_game_timer'] = Thread(repeat=20, col_repeat='inf', 
                                     function='end_game_timer', last_start=0, active=True)
        self.ThreadsRegister['service_deleter'] = Thread(repeat=20, col_repeat='inf',
                                     function='service_deleter', last_start=0, active=True)

        self.WaiterRegister = {
            "int": Waiter(function='IntWaiter', active=False, data={})
        }

        self.message_generators = {
            'main': 'MainGenerator',
            'preparation': 'PreparationGenerator',
            'max_players': 'MaxPlayersGenerator',
            'choose_dino': 'ChooseDinoGenerator',
            'choose_bet': 'ChooseBetGenerator',
            'service': 'ServiceGenerator',
        }

        self.Stages = {
            'preparation': Stage(
                threads_active=[],
                buttons_active=[
                    stageButton(button='max_col', data={'active': True}),
                    stageButton(button='choose_dino', data={'active': True}),
                    stageButton(button='choose_bet', data={'active': True}),
                    stageButton(button='end_game', data={'active': True}),
                ],
                waiter_active=[],
                stage_generator='preparation',
                to_function='',
                data={}
            ),
            'max_players': Stage(
                threads_active=[],
                buttons_active=[
                    stageButton(button='col_players', data={'active': True}),
                    stageButton(button='to_preparation', data={'active': True}),
                ],
                waiter_active=[],
                stage_generator='max_players',
                to_function='',
                data={}
            ),
            'choose_dino': Stage(
                threads_active=[],
                buttons_active=[
                    stageButton(button='choose_dino_set', data={'active': True}),
                    stageButton(button='to_preparation', data={'active': True}),
                ],
                waiter_active=[],
                stage_generator='choose_dino',
                to_function='',
                data={}
            ),
            'choose_bet': Stage(
                threads_active=[],
                buttons_active=[
                    stageButton(button='to_preparation', data={'active': True}),
                ],
                waiter_active=[
                    stageWaiter(waiter='int', data={'active': True}),
                ],
                stage_generator='choose_bet',
                to_function='',
                data={}
            ),
        }

        await self.Update()

    async def ServiceGenerator(self, user_id: int, mtype: str) -> None:
        text = '-34'
        if mtype == 'no_coins':
            text = 'Недостаточно монет.'
        elif mtype == 'zero':
            text = 'Ставка не может быть нулевой или меньше нуля.'

        await self.DeleteMessage('service')
        chat_id = self.session_masseges['main'].chat_id
        msg = await self.CreateMessage(user_id, chat_id, 'service', text=text)

        if isinstance(msg, types.Message):
            self.session_masseges['service'] = SMessage(message_id=msg.message_id, chat_id=msg.chat.id, data={'last_action': time.time()})
            await self.Update()

    async def service_deleter(self):
        if 'service' not in self.session_masseges: return

        service_message = self.session_masseges['service']
        if 'last_action' not in service_message.data: return

        if time.time() - service_message.data['last_action'] >= 60:
            await self.DeleteMessage('service')

    async def end_game_timer(self):
        if time.time() - self.LAST_ACTION >= self.time_wait and self.LAST_ACTION != 0:
            await self.EndGame()
        else:
            if 'main' in self.session_masseges and 'author' in self.session_masseges['main'].data:

                user_id = self.session_masseges['main'].data['author']
                player = await self.GetPlayer(user_id)

                if player.stage == 'preparation':
                    await self.MessageGenerator('preparation', user_id)
                await self.Update()

    async def Custom_StartGame(self, user_id, chat_id, message) -> None:
        owner_player = await self.GetPlayer(user_id)
        if owner_player is None:
            self.D_log('Owner player not found')
            return
 
        owner_player.data = {'dino': ''}

        await self.EditPlayer(user_id, owner_player)
        await self.SetStage('preparation')

    async def Custom_EndGame(self) -> None:

        if self.STAGE == 'preparation':
            for player in self.PLAYERS.values():
                await take_coins(player.user_id, self.bet, update=True)

    async def EndGame_c(self, callback) -> None:
        await self.EndGame()
    
    async def PreparationMarkup(self):
        buttons = [
            {'text': 'max players', 'callback_data': self.CallbackGenerator('max_col')},
            {'text': '🦕', 'callback_data': self.CallbackGenerator('choose_dino')},
            {'text': '💰', 'callback_data': self.CallbackGenerator('choose_bet')},
            {'text': '🚪', 'callback_data': self.CallbackGenerator('end_game')},
        ]
        return self.list_to_inline(buttons)

    async def MainGenerator(self, user_id) -> None:
        text = 'main'
        await self.MesageUpdate(text=text)

    async def PreparationGenerator(self, user_id) -> None:
        self.D_log(f'PreparationGenerator {user_id}')
        owner_player = await self.GetPlayer(user_id)
        if owner_player is None:
            self.D_log('Owner player not found')

        dino_name = "Не выбран"
        bet_text = "Не выбрана"

        if 'dino' in owner_player.data and owner_player.data['dino']:
            dino = await Dino().create(owner_player.data['dino'])
            dino_name = dino.name if dino else dino_name

        if self.bet > 0:
            bet_text = str(self.bet)

        time_left = self.time_wait - (time.time() - self.LAST_ACTION)
        time_left_text = f'Время до удаления игры: {int(time_left)} секунд'

        text = f'Динозавр: {dino_name}\nСтавка: {bet_text}\nМакс. игроков: {self.col_players}\n{time_left_text}'
        markup = await self.PreparationMarkup()
        await self.MesageUpdate('main', text=text, reply_markup=markup)

    async def MaxCol(self, callback) -> None:
        await self.SetStage('max_players')

    async def ToPreparation(self, callback) -> None:
        await self.SetStage('preparation')

    async def max_playersMarkup(self):
        buttons = [
            {'text': '2 players', 'callback_data': self.CallbackGenerator('col_players', '2')},
            {'text': '3 players', 'callback_data': self.CallbackGenerator('col_players', '3')},
            {'text': '4 players', 'callback_data': self.CallbackGenerator('col_players', '4')},
            {'text': 'back', 'callback_data': self.CallbackGenerator('to_preparation')},
        ]
        return self.list_to_inline(buttons, 3)

    async def ColPlayers_set(self, callback) -> None:
        col_players = callback.data.split(':')[3]
        self.col_players = col_players
        await self.Update()
        await self.SetStage('preparation')

    async def MaxPlayersGenerator(self, user_id) -> None:
        markup = await self.max_playersMarkup()
        text = 'Выберите максимальное количество игроков:'
        await self.MesageUpdate('main', text=text, reply_markup=markup)
    
    async def ChooseDino(self, callback) -> None:
        await self.SetStage('choose_dino')

    async def choose_dinoMarkup(self, user_id):
        
        user = await User().create(user_id)
        dinos = await user.get_dinos()
        
        buttons = [{'text': dino.name, 'callback_data': self.CallbackGenerator('choose_dino_set', dino.alt_id)} for dino in dinos]
        buttons.append({'text': 'back', 'ignore_row': 'True', 'callback_data': self.CallbackGenerator('to_preparation')})
        return self.list_to_inline(buttons, 2)

    async def ChooseDino_set(self, callback) -> None:
        dino_name = callback.data.split(':')[3]
        user_id = callback.from_user.id
        player = await self.GetPlayer(user_id)
        if player:
            player.data['dino'] = dino_name
            await self.EditPlayer(user_id, player)
        await self.Update()
        await self.SetStage('preparation')

    async def ChooseDinoGenerator(self, user_id) -> None:
        markup = await self.choose_dinoMarkup(user_id)
        text = 'Выберите динозавра:'
        await self.MesageUpdate('main', text=text, reply_markup=markup)

    async def ChooseBet(self, callback) -> None:
        await self.SetStage('choose_bet')

    async def choose_betMarkup(self):
        buttons = [
            {'text': 'back', 'callback_data': self.CallbackGenerator('to_preparation')},
        ]
        return self.list_to_inline(buttons, 1)

    async def ChooseBetGenerator(self, user_id) -> None:
        markup = await self.choose_betMarkup()
        text = 'Выберите ставку:'
        await self.MesageUpdate('main', text=text, reply_markup=markup)

    async def IntWaiter(self, message: types.Message, command: bool = False):
        if command: 
            coins = int(message.text.split(' ')[3])
        else:
            coins = int(message.text)
            
        try:
            await message.delete()
        except: pass

        user_id = message.from_user.id
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


PowerChecker().RegistryMe() # Регистрация класса в реестре
