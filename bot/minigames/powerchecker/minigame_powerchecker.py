from asyncio import sleep
import random
import time

from bot.exec import bot

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

            # Кнопка для удаления защищённого режима входа
            'delete_only_for': Button(function='DeleteOnlyFor', filters=['owner_filter'], active=False),

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
                    stageButton(button='delete_only_for', data={'active': True}),
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

    async def Custom_StartGame(self, user_id, chat_id, message, 
                               only_for = None) -> None:
        print(only_for)
        if only_for: self.only_for = only_for

        owner_player = await self.GetPlayer(user_id)
        if owner_player is None:
            self.D_log('Owner player not found')
            return

        await self.EditPlayer(user_id, owner_player)
        await self.SetStage('preparation')
    
    async def Custom_ContinueGame(self) -> None:
        
        if self.STAGE == 'game':
            stage = self.Stages['game']
            await self.MessageGenerator(stage.stage_generator, int(self.active_player))

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

    async def game_StartGame(self) -> None:
        self.WaiterRegister = {}

        self.ButtonsRegister = {
            "exit": Button(function='game_ExitGame', filters=['player_filter'], active=False),
            "simple_hit": Button(function='game_SimpleHit', filters=['active_player_filter'], active=False),
            "powerful_hit": Button(function='game_PowerfulHit', filters=['active_player_filter'], active=False),
            "net_dino": Button(function='game_NetDino', filters=['active_player_filter'], active=False),
            "take_axe": Button(function='game_TakeAxe', filters=['active_player_filter'], active=False),
            "pass": Button(function='game_Pass', filters=['active_player_filter'], active=False),
            "set_dino_to_attack": Button(function='game_ChooseDinoToAttack', filters=['active_player_filter'], active=False),
            "cancel": Button(function='game_CancelToMain', filters=['active_player_filter'], active=False)
        }

        self.message_generators = {
            'main': 'game_GameGenerator',
            'dice': 'game_DiceGenerator',
            'choose_dino': 'game_ChooseDinoGenerator',
        }

        self.Stages = {
            'game': Stage(
                threads_active=[],
                buttons_active=[
                    stageButton(button='exit', data={'active': True}),
                    stageButton(button='simple_hit', data={'active': True}),
                    stageButton(button='powerful_hit', data={'active': True}),
                    stageButton(button='net_dino', data={'active': True}),
                    stageButton(button='take_axe', data={'active': True}),
                    stageButton(button='pass', data={'active': True}),
                ],
                waiter_active=[],
                stage_generator='main',
                to_function='',
                data={}
            ),
            'choose_dino': Stage(
                threads_active=[],
                buttons_active=[
                    stageButton(button='set_dino_to_attack', data={'active': True}),
                    stageButton(button='cancel', data={'active': True}),
                ],
                waiter_active=[],
                stage_generator='choose_dino',
                to_function='',
                data={
                    'next_function': '',
                }
            ),
            'roll_dice': Stage(
                threads_active=[],
                buttons_active=[
                    stageButton(button='roll_dice_button', data={'active': True}),
                    stageButton(button='cancel', data={'active': True}),
                ],
                waiter_active=[],
                stage_generator='dice',
                to_function='',
                data={}
            )
        }
        
        del self.ThreadsRegister['service_deleter']
        del self.ThreadsRegister['end_game_timer']

        self.active_player: str = list(self.PLAYERS.keys())[0]
        self.power = random.randint(50, 80)
        self.log: list = []

        for player_id, player_data in self.PLAYERS.items():
            dino: Dino = await Dino().create(player_data.data['dino'])

            # Игровые данные
            player_data.data['units'] = self.power
            player_data.data['dino_power'] = dino.stats['power']
            player_data.data['dino_dexterity'] = dino.stats['dexterity']
            player_data.data['dino_overload'] = 0
            player_data.data['in_net'] = False
            player_data.data['without_tools'] = False
            player_data.data['without_limit'] = 2

            await self.EditPlayer(int(player_id), player_data)

        await self.Update()

        await self.SetStage('game')
        await self.MessageGenerator('main', self.owner_id)

    async def next_player(self):

        now = self.active_player
        keys = list(self.PLAYERS.keys())

        if now == keys[-1]:
            self.active_player = keys[0]
        else:
            self.active_player = keys[
                keys.index(now) + 1
            ]

        await self.Update()

    async def active_player_filter(self, callback: types.CallbackQuery) -> bool:
        if int(callback.from_user.id) != int(self.active_player):
            await callback.answer('Сейчас не ваш ход или вы не участник игры!')
            return False

        return True

    async def game_ExitGame(self, callback: types.CallbackQuery) -> None:
        pass

    async def game_SimpleHit(self, callback: types.CallbackQuery) -> None:
        d1, d2 = await self.game_RollDice(callback)

        if d1 and d2:
            active_player = await self.GetPlayer(int(self.active_player))

            if active_player:
                power = active_player.data['dino_power']

                active_player.data['units'] -= d1 + d2 + power // 50
                await self.EditPlayer(int(self.active_player), active_player)

                self.log.append(
                    [int(self.active_player), 
                     'simplehit', [f'🎲 {d1}', f'🎲 {d1}', f'💪 {int(power // 50)}'], 'wood']
                )
                self.log = self.log[-3:]
                await self.Update()

                await self.next_player()
                await self.MessageGenerator('main', int(self.active_player))

    async def game_PowerfulHit(self, callback: types.CallbackQuery) -> None:
        
        active_player = await self.GetPlayer(int(self.active_player))

        if active_player:
            power = active_player.data['dino_power']

            active_player.data['units'] -= power
            active_player.data['dino_overload'] += 1
            await self.EditPlayer(int(self.active_player), active_player)

            self.log.append(
                [int(self.active_player), 
                    'powerfulhit', [f'💪 {int(power)}'], 'wood']
            )
            self.log = self.log[-3:]
            await self.Update()

            await self.next_player()
            await self.MessageGenerator('main', int(self.active_player))

    async def game_NetDino(self, callback: types.CallbackQuery) -> None:
        pass

    async def game_TakeAxe(self, callback: types.CallbackQuery) -> None:
        pass

    async def game_Pass(self, callback: types.CallbackQuery) -> None:
        pass

    async def game_ChooseDinoToAttack(self, callback: types.CallbackQuery) -> None:
        pass

    async def game_CancelToMain(self, callback: types.CallbackQuery) -> None:
        pass

    async def set_dino_to_attack(self, callback: types.CallbackQuery) -> None:
        pass

    async def cancel_dino_choose(self, callback: types.CallbackQuery) -> None:
        pass

    async def game_RollDice(self, callback: types.CallbackQuery):

        res = await bot.send_dice(callback.message.chat.id, emoji='🎲', reply_markup=None, reply_to_message_id=callback.message.message_thread_id)

        res2 = await bot.send_dice(callback.message.chat.id, emoji='🎲', reply_markup=None, reply_to_message_id=callback.message.message_thread_id)

        await self.MessageGenerator('main', int(self.active_player), action_type='simplehit')
        await sleep(7)

        try:
            await res.delete()
            await res2.delete()
        except: pass

        return res.dice.value, res2.dice.value

    async def game_ChooseDinoGenerator(self, user_id: int) -> None:
        pass
    
    async def game_dice_reply_markup(self, user_id: int):
        buttons = [
            {'text': '🎲 Бросить кубик', 'callback_data': self.CallbackGenerator('roll_dice_button')},
            {'text': 'Отмена', 'callback_data': self.CallbackGenerator('cancel')},
        ]
        
        return self.list_to_inline(buttons, 2)

    async def game_DiceGenerator(self, user_id: int) -> None:
        text = '🎲 Бросок кубика 🎲\n\n' \
               'Выберите действие:\n' \
               '- Бросить кубик: Бросить кубик и узнать результат\n' \
               '- Отмена: Вернуться назад'

        await self.MesageUpdate('dice', text=text, 
                                reply_markup=await self.game_dice_reply_markup(user_id))

    async def game_main_reply_markup(self, user_id: int):
        buttons = [
            {'text': 'Удар', 'callback_data': self.CallbackGenerator('simple_hit')},
            {'text': 'Мощный удар', 'callback_data': self.CallbackGenerator('powerful_hit')},
            {'text': 'Паутина', 'callback_data': self.CallbackGenerator('net_dino')},
            {'text': 'Отобрать топор', 'callback_data': self.CallbackGenerator('take_axe')},
            {'text': 'Пропустить ход', 'callback_data': self.CallbackGenerator('pass')},
            {'text': 'Выйти', 'callback_data': self.CallbackGenerator('exit'), 'ignore_row': 'true'},
        ]
        return self.list_to_inline(buttons, 3)

    async def game_GameGenerator(self, user_id: int, action_type: str | None = None) -> None:
        data_act_player = self.PLAYERS[self.active_player]
        text = "Игроки:\n"
        for player_id, player_data in self.PLAYERS.items():
            remaining_power = player_data.data['units']
            percentage = int((remaining_power / self.power) * 100)
            if player_id == self.active_player: my_percent = percentage

            activ_emoji = '-'
            if player_id == self.active_player: activ_emoji = '>'

            text += f"{activ_emoji} {player_data.user_name}: {percentage}%\n"
        
        if self.log:
            text += '\nПоследние действия:\n'

            logs = self.log[-3:]
            for who, act_type, list_units, to_object in logs:
                who_player = await self.GetPlayer(who)
                if who_player:
                    # ['simplehit', [d1, d2, power // 50], 'wood']
                    # ['powerfulhit', [power], 'wood']
                    if act_type in ['simplehit', 'powerfulhit']:
                        text += f'{who_player.user_name} 🪓 -> {" + ".join(list_units)} -> 🪵'
                    text += '\n'

        if not action_type:
            text += f'\n{data_act_player.user_name} Выберите действие:\n' \
                    '- Удар: Нанести удар по дереву\n' \
                    '- Мощный удар: Исползует всю силу динозавра\n' \
                    '- Паутина: В случае успеха противник пропустит ход\n' \
                    '- Отобрать топор: В случае успеха противник не сможет использовать топор\n'
        if action_type == 'simplehit':
            text += '\nВыбранное действие: Удар по дереву\n' \
                    '- Ожидайте пока кубики упадут, после чего динозавр нанесёт удар по дереву.' 


        await self.MesageUpdate('main', text=text, 
                                reply_markup=await self.game_main_reply_markup(user_id))


PowerChecker().RegistryMe() # Регистрация класса в реестре
