import random
import time

from aiogram import types
from bot.minigames.minigame import MiniGame, Button, PlayerData, SMessage, Stage, Thread, Waiter, stageButton, stageThread, stageWaiter
from bot.modules.user.user import User, take_coins, user_name
from bot.modules.dinosaur.dinosaur import Dino
from typing import Optional

class PowerChecker(MiniGame):

    def get_GAME_ID(self): return 'PowerChecker'

    async def initialization(self, only_for: int = 0):
        self.DEBUG_MODE = True
        self.time_wait = 600

        self.only_for: int = only_for
        self.max_players: int = 2
        self.bet: int = 0

        self.ButtonsRegister = {
            'max_col': Button(stage='max_players', filters=['owner_filter'], active=False),
            'choose_dino': Button(stage='choose_dino', filters=['owner_filter'], active=False),
            'choose_bet': Button(stage='choose_bet', filters=['owner_filter'], active=False),
            'end_game': Button(function='EndGame_c', filters=['owner_filter'], active=True),
            'start_game': Button(function='StartGame', filters=['owner_filter'], active=False),

            # Кнопка для возвращения в меню подготовки
            'to_preparation': Button(stage='preparation', filters=['owner_filter'], active=False),

            # Кнопка для выбора количества игроков
            'col_players': Button(function='ColPlayers_set', filters=['owner_filter'], active=False),

            # Кнопка для выбора динозавра
            'dino_set': Button(function='ChooseDino_set', filters=['owner_filter'], active=False),

            # Кнопка для выбора ставки
            'choose_bet_set': Button(function='ChooseBet_set', filters=['owner_filter'], active=False),

            # Кнопка для начала игры
            'wait_users_start': Button(function='WaitUsersStart', filters=['owner_filter'], active=False),
        }

        self.ThreadsRegister['end_game_timer'] = Thread(repeat=20, col_repeat='inf', 
                                     function='end_game_timer', last_start=0, active=True)
        self.ThreadsRegister['service_deleter'] = Thread(repeat=20, col_repeat='inf',
                                     function='service_deleter', last_start=0, active=True)

        self.WaiterRegister = {
            "int": Waiter(function='IntWaiter', active=False, data={})
        }

        self.message_generators = {
            'main': 'PreparationGenerator',
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
                to_function='on_preparation',
                data={'back_key': 'to_preparation'}
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
                    stageButton(button='dino_set', data={'active': True}),
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

    def standart_player_data(self):
        return {'dino': '', 'ready': False}

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
            self.session_masseges['service'].data['last_action'] = time.time()
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

                if player.stage == 'preparation': # type: ignore
                    await self.MessageGenerator('preparation', user_id)
                await self.Update()

    async def Custom_StartGame(self, user_id, chat_id, message) -> None:

        owner_player = await self.GetPlayer(user_id)
        if owner_player is None:
            self.D_log('Owner player not found')
            return

        await self.EditPlayer(user_id, owner_player)
        await self.SetStage('preparation')

    async def Custom_EndGame(self) -> None:

        if self.STAGE == 'preparation':
            for player in self.PLAYERS.values():
                await take_coins(player.user_id, self.bet, update=True)


    async def enter_filter(self, callback: types.CallbackQuery) -> bool:
        if self.only_for != 0 and callback.from_user.id != self.only_for:
            await callback.answer('Игра доступна только для одного пользователя')
            return False

        if callback.from_user.id == self.owner_id:
            await callback.answer('Вы не можете вступить в свою же игру')
            return False

        if callback.from_user.id in self.PLAYERS:
            await callback.answer('Вы уже вступили в игру')
            return False

        else: return True

    async def WaitUsersStart(self, callback) -> None:
        self.WaiterRegister = {}

        self.ButtonsRegister = {
            'endandleave': Button(function='Endandleave', 
                               filters=['player_filter'], active=False),

            'enter': Button(function='waituser_Enter', 
                            filters=['enter_filter'], active=False),

            'cancel_choose': Button(function='waituser_CancelChoose',
                                    filters=['message_author_filter'], active=False),
            'dino_set': Button(function='waituser_ChooseDino_set', 
                                filters=['message_author_filter'], active=False),

            'next_stage': Button(function='waituser_NextStage',
                                filters=['player_filter'], active=False),
        }

        self.message_generators = {
            'main': 'WaitUsersStartGenerator',
            'choose_dino': 'enter_dino_generator',
        }

        self.Stages = {
            'wait_user': Stage(
                threads_active=[],
                buttons_active=[
                    stageButton(button='endandleave', data={'active': True}),
                    stageButton(button='cancel_choose', data={'active': True}),
                    stageButton(button='enter', data={'active': True}),
                    stageButton(button='dino_set', data={'active': True}),
                ],
                waiter_active=[],
                stage_generator='main',
                to_function='',
                data={
                    'back_key': 'cancel_choose'
                    }
            ),
        }

        await self.Update()
        await self.SetStage('wait_user')

    async def Endandleave(self, callback) -> None:
        """ Покинуть игру или завершить если создатель"""
        if callback.from_user.id == self.owner_id:
            await self.EndGame()
        else:
            await self.DeletePlayer(callback.from_user.id)
            await callback.answer('Вы покинули игру')

            await self.on_user_col_edit()
            await self.MessageGenerator('main', callback.from_user.id)

    async def waituser_inline(self, user_id):
        buttons = []

        if self.ButtonsRegister['enter'].active and len(self.PLAYERS) < self.max_players:
            buttons.append({'text': 'Вступить', 'callback_data': self.CallbackGenerator('enter')})

        if self.ButtonsRegister['next_stage'].active:

            ready = 0
            col_p = len(self.PLAYERS)

            for player in self.PLAYERS.values():
                if player.data.get('ready', False):
                    ready += 1

            buttons.append({'text': f'{ready}/{col_p} ✅', 'callback_data': self.CallbackGenerator('next_stage')})

        buttons.append({'text': '🚪', 'callback_data': self.CallbackGenerator('endandleave')})
        return self.list_to_inline(buttons, 2)

    async def WaitUsersStartGenerator(self, user_id: int) -> None:
        markup = await self.waituser_inline(user_id)
        text = 'Ожидание игроков'
        players = self.PLAYERS.values()

        table = "\n".join(
            [f"{player.user_name} - {'Готов' if player.data.get('dino') else 'Не готов'}" for player in players]
        )
        text += f"\n\nСостояние игроков:\n{table}"
        await self.MesageUpdate(text=text, reply_markup=markup)

    async def waituser_Enter(self, callback: types.CallbackQuery) -> None:
        """ Кнопка вступить в игру """
        user_id = callback.from_user.id

        user = await User().create(user_id)

        if user.coins < self.bet:
            await callback.answer('Недостаточно монет для ставки', show_alert=True)
            return

        dinos = await user.get_dinos(False)
        if not any([await dino.is_free() for dino in dinos]):
            await callback.answer('У вас нет свободных динозавров', show_alert=True)
            return

        if len(self.PLAYERS) >= self.max_players:
            await callback.answer('Максимальное количество игроков уже достигнуто', show_alert=True)
            return

        key = f'choose_dino_{user_id}'
        if key not in self.message_generators:
            await self.AddPlayer(user_id, callback.message.chat.id, 
                             await user_name(user_id),
                             self.STAGE
                             )

            self.message_generators[key] = 'enter_dino_generator'
            await self.Update()

            await self.MessageGenerator('main', user_id)
            await self.CreateMessage(user_id, callback.message.chat.id, key, 
                                    text='message')
            await self.MessageGenerator(key, user_id)

        else:
            await callback.answer('Вы уже в игре', show_alert=True)

    async def waituser_CancelChoose(self, callback) -> None:
        """ Отмена выбора динозавра и удаление сообщения с выбором """
        user_id = callback.from_user.id

        await self.DeletePlayer(user_id)
        await self.DeleteMessage(f'choose_dino_{user_id}')
        self.message_generators.pop(f'choose_dino_{user_id}')
        await self.Update()

        await self.MessageGenerator('main', user_id)

    async def waituser_ChooseDino_set(self, callback) -> None:
        """ Установка выбранного динозавра вторым/третьим игроком """

        dino_name = callback.data.split(':')[3]
        user_id = callback.from_user.id
        player = await self.GetPlayer(user_id)
        if player:
            player.data['dino'] = dino_name
            await self.EditPlayer(user_id, player)

        await self.on_user_col_edit()
        await self.DeleteMessage(f'choose_dino_{user_id}')
        await self.MessageGenerator('main', user_id)

    async def enter_dino_generator(self, user_id) -> None:
        markup = await self.dino_markup(user_id) # type: ignore
        text = f'{user_id} Выберите динозавра:'
        await self.MesageUpdate(f'choose_dino_{user_id}', 
                                text=text, reply_markup=markup)

    async def on_user_col_edit(self) -> None:
        bt = self.ButtonsRegister['next_stage']
        en = self.ButtonsRegister['enter']

        if len(self.PLAYERS) >= self.max_players:
            if not en.active:
                en.active = False
                await self.EditButton('enter', en)

            all_have_dino = all([player.data.get('dino') for player in 
                                 self.PLAYERS.values()])

            if all_have_dino:
                if not bt.active:
                    bt.active = True
                    await self.EditButton('next_stage', bt)

        elif len(self.PLAYERS) == 1:

            if bt.active:
                bt.active = False
                await self.EditButton('next_stage', bt)

            if not en.active:
                en.active = True
                await self.EditButton('enter', en)

    async def waituser_NextStage(self, callback) -> None:
        ready = 0
        for player in self.PLAYERS.values():
            if player.data.get('ready'):
                ready += 1
        
        this_player = await self.GetPlayer(callback.from_user.id)
        if this_player:
            this_player.data['ready'] = not this_player.data.get('ready', False)
            ready += 1

            await self.EditPlayer(callback.from_user.id, this_player)
            await self.MessageGenerator('main', callback.from_user.id)

        if ready == len(self.PLAYERS):
            self.D_log('StartGame -------------', True)


PowerChecker().RegistryMe() # Регистрация класса в реестре
