from asyncio import sleep
import random
import time

from annotated_types import T

from bot.exec import bot

from aiogram import types
from bot.minigames.minigame import MiniGame, Button, PlayerData, SMessage, Stage, Thread, Waiter, stageButton, stageThread, stageWaiter
from bot.modules.data_format import seconds_to_str
from bot.models import dinosaur
from bot.modules.images_creators.more_dinos import MiniGame_image
from bot.modules.user.user import User, take_coins, user_name
from bot.models.dinosaur import Dino
from typing import Optional, overload

hards_lvl = {
    1: (20, 40),
    2: (50, 80),
    3: (80, 150),
}

class PowerChecker(MiniGame):

    def get_GAME_ID(self): return 'PowerChecker'
    
    async def initialization(self):
        self._excluded_from_save += ['time_wait']
        self.DEBUG_MODE = True
        self.time_wait = 120

        self.start_image_generator = 'main'
        self.start_image_name = 'main'

        self.ImageGenerators = {
            'main': 'main_image',
        }
        
        self.NextButtonTimeActivationDelay = 0.5
        self.NextUpdateMessageTimeDelay = 0.5

    async def start_data(self, only_for: int = 0):

        self.only_for: int = only_for
        self.max_players: int = 4
        self.bet: int = 0
        self.hard_lvl: int = 2

        self.ButtonsRegister = {
            'max_col': Button(stage='max_players', filters=['owner_filter'], active=False),
            'choose_dino': Button(stage='choose_dino', filters=['owner_filter'], active=False),
            'choose_bet': Button(stage='choose_bet', filters=['owner_filter'], active=False),
            'end_game': Button(function='EndGame_c', filters=['owner_filter'], active=True),
            'start_game': Button(function='StartGame', filters=['owner_filter'], active=False),
            'change_language': Button(stage='choose_language', 
                                filters=['owner_filter'], active=False),
            'hard_lvl': Button(stage='choose_hard_lvl', 
                               filters=['owner_filter'], active=False),

            # Кнопка для возвращения в меню подготовки
            'to_preparation': Button(function='ToPreparation',
                            stage='preparation', filters=['owner_filter'], active=False),

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

            # Кнопка для установки уровня сложности
            'hard_lvl_set': Button(function='HardLvl_set', filters=['owner_filter'], active=False),

            # Кнопка для выбора языка
            'choose_language_set': Button(function='ChangeLanguage_set', filters=['owner_filter'], active=False),
        }

        self.ThreadsRegister['end_game_timer'] = Thread(repeat=60, col_repeat='inf', 
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
            'change_language': 'ChangeLanguageGenerator',
            'hard_lvl': 'HardLvlGenerator',
        }

        self.Stages = {
            'preparation': Stage(
                threads_active=[],
                buttons_active=[
                    stageButton(button='max_col', data={'active': True}),
                    stageButton(button='choose_dino', data={'active': True}),
                    stageButton(button='choose_bet', data={'active': True}),
                    stageButton(button='end_game', data={'active': True}),
                    stageButton(button='change_language', data={'active': True}),
                    stageButton(button='hard_lvl', data={'active': True}),
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
                    stageButton(button='choose_bet_set', data={'active': True}),
                ],
                waiter_active=[
                    stageWaiter(waiter='int', data={'active': True}),
                ],
                stage_generator='choose_bet',
                to_function='',
                data={}
            ),
            'choose_language': Stage(
                threads_active=[],
                buttons_active=[
                    stageButton(button='to_preparation', data={'active': True}),
                    stageButton(button='choose_language_set', data={'active': True}),
                ],
                waiter_active=[],
                stage_generator='change_language',
                to_function='',
                data={}
            ),
            'choose_hard_lvl': Stage(
                threads_active=[],
                buttons_active=[
                    stageButton(button='to_preparation', data={'active': True}),
                    stageButton(button='hard_lvl_set', data={'active': True}),
                ],
                waiter_active=[],
                stage_generator='hard_lvl',
                to_function='',
                data={}
            )
        }

        await self.Update()

    async def main_image(self):
        """
        Генерация изображения для главного меню игры
        """
        dinosaurs = []
        for player_id, player_data in self.PLAYERS.items():
            dino = await Dino().create(player_data.data['dino'])
            if dino:
                dinosaurs.append({
                    'dino_id': dino.data_id,
                    'name': dino.name,
                })

        image = await MiniGame_image(dinosaurs, 'backgrounds/1.png')
        return image

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
        if self.STAGE in ['preparation', 'wait_user']:
            if time.time() - self.LAST_ACTION >= self.time_wait and self.LAST_ACTION != 0:
                await self.EndGame()
            else:
                if 'main' in self.session_masseges and 'author' in self.session_masseges['main'].data:

                    user_id = self.session_masseges['main'].data['author']
                    player = await self.GetPlayer(user_id)

                    if player.stage == 'preparation': # type: ignore
                        await self.MessageGenerator('preparation', user_id)

        if self.STAGE == 'game':
            player = await self.GetPlayer(int(self.active_player))
            if time.time() - self.LAST_ACTION >= self.time_wait and self.LAST_ACTION != 0:
                self.LAST_ACTION = time.time()
                await self.Update()

                if player:
                    player.data['sleep'] += 1
                    await self.EditPlayer(int(self.active_player), player)

                    if player.data['sleep'] >= 3:
                        self.D_log(f'Игрок {player.user_name} пропускает ход и кикается')
                        res = await self.playerexit(int(self.active_player))
                        if res:
                            await self.MessageGenerator('main', int(self.active_player))
                    else:
                        await self.game_Pass(None)
                else:
                    await self.next_player()
                    user_id = int(self.active_player)
                    await self.MessageGenerator('main', user_id)

            else:
                if await self.AllHaveGeneralStage:

                    user_id = int(self.active_player)
                    await self.MessageGenerator('main', user_id)

    async def Custom_StartGame(self, user_id, chat_id, message, 
                               only_for = None) -> None:
        await self.start_data(only_for if only_for else 0)

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

        if self.STAGE == 'game':
            for player in self.PLAYERS.values():
                if player.user_id != int(self.active_player):
                    await self.DeletePlayer(player.user_id)
                else:
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
            "cancel": Button(stage='game', filters=['active_player_filter'], active=False)
        }

        self.message_generators = {
            'main': 'game_GameGenerator',
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

        self.ThreadsRegister['service_deleter'].active = False
        # self.ThreadsRegister['end_game_timer'].active = True
        
        self.active_player: str = list(self.PLAYERS.keys())[0]
        self.power = random.randint(*hards_lvl[self.hard_lvl])

        await self.DeleteVar('only_for')
        await self.DeleteVar('max_players')
        await self.DeleteVar('hard_lvl')

        self.log: list = []

        self.max_net_lim = 2
        self.max_without_lim = 2

        # Общая победная ставка
        self.bet = self.bet * len(self.PLAYERS)

        for player_id, player_data in self.PLAYERS.items():
            dino = await Dino().create(player_data.data['dino'])
            if not dino: continue

            # Игровые данные
            player_data.data = {
                'dino': dino.alt_id,
                'units': self.power,
                'dino_power': dino.stats['power'],
                'dino_dexterity': dino.stats['dexterity'],
                'intelligence': dino.stats['intelligence'],
                'dino_overload': 0,
                'in_net': False,
                'without_tools': False,
                'without_limit': 2,
                'net_limit': 2,
                'sleep': 0
            }

            await self.EditPlayer(int(player_id), player_data)

        self.active_player = random.choice(list(self.PLAYERS.keys()))

        await self.Update()

        await self.SetStage('game')
        await self.MessageGenerator('main', self.owner_id)

    async def button_control(self, userid: int):
        """
        Функция отключает кнопки, если динозавр в паутине, без топора или перегружен
        """

        player = await self.GetPlayer(userid)
        if player:
            if player.data['dino_overload'] == 3 or player.data['in_net']:
                await self.OffButtons(['simple_hit', 'powerful_hit', 'net_dino', 'take_axe'])

            elif player.data['without_tools']:
                await self.OffButtons(['simple_hit', 'net_dino', 'take_axe'])

            else:
                await self.OnButtons(['simple_hit', 'powerful_hit', 'net_dino', 'take_axe'])

    async def next_player(self):

        now_player = await self.GetPlayer(int(self.active_player))

        if now_player and now_player.data['units'] <= 0:
            await self.EndGame()
            return

        if now_player and now_player.data['in_net']:
            now_player.data['in_net'] = False
            await self.EditPlayer(int(self.active_player), now_player)

        elif now_player and now_player.data['without_tools']:
            now_player.data['without_tools'] = False
            await self.EditPlayer(int(self.active_player), now_player)

        now = self.active_player
        keys = list(self.PLAYERS.keys())

        if len(keys) != 1:

            if now == keys[-1]:
                self.active_player = keys[0]
            else:
                self.active_player = keys[
                    keys.index(now) + 1
                ]

            await self.Update()
            await self.button_control(int(self.active_player))

            next_player = await self.GetPlayer(int(self.active_player))
            if next_player: 

                # Проверка на перегрузку
                if next_player.data['dino_overload'] == 3:
                    next_player.data['dino_overload'] -= random.randint(1, 3)
                    await self.EditPlayer(int(self.active_player), next_player)

    async def active_player_filter(self, callback: types.CallbackQuery) -> bool:
        if int(callback.from_user.id) != int(self.active_player):
            await callback.answer('Сейчас не ваш ход или вы не участник игры!')
            return False

        return True

    async def EndGameGenerator(self) -> None:
        text = f'Игра {self.session_key} завершена'

        if self.STAGE == 'game':
            player = await self.GetPlayer(int(self.active_player))
            if player:
                dino = await Dino().create(player.data['dino'])
                if dino:
                    text = f'Игра {self.session_key} завершена\n' \
                        f'Выиграл игрок: {player.user_name} с динозавром {dino.name}\n' \
                        f'Выигрыш {self.bet} монет.'

        await self.MessageUpdate('main', text=text)

    async def playerexit(self, user_id: int) -> bool:
        if user_id == int(self.active_player): 
            await self.next_player()

        await self.DeletePlayer(user_id)
        # Снятие статуса с динозавра

        if len(self.PLAYERS) == 1:
            await self.EndGame()
            return False

        return True

    async def game_ExitGame(self, callback: types.CallbackQuery) -> None:

        who_click = callback.from_user.id
        res = await self.playerexit(who_click)
        if res:
            await self.MessageGenerator('main', who_click)

    async def game_SimpleHit(self, callback: types.CallbackQuery) -> None:
        d1, d2 = await self.game_RollDice(callback, 'simplehit')

        if d1 and d2:
            active_player = await self.GetPlayer(int(self.active_player))

            if active_player:
                power = active_player.data['dino_power']

                active_player.data['units'] -= d1 + d2 + power // 50
                await self.EditPlayer(int(self.active_player), active_player)

                self.log.append(
                    [int(self.active_player), 
                     'simplehit', [f'🎲 {d1}+{d2}', f'💪 {int(power // 50)}'], 'wood']
                )
                await self.Update()

                await self.next_player()
                await self.MessageGenerator('main', int(self.active_player))

    async def game_PowerfulHit(self, callback: types.CallbackQuery) -> None:
        
        active_player = await self.GetPlayer(int(self.active_player))

        if active_player:
            d_p = active_player.data['dino_power']
            power = random.randint(int(d_p // 100 * 20), int(d_p))
            power += 3

            active_player.data['units'] -= power
            active_player.data['dino_overload'] += 1
            await self.EditPlayer(int(self.active_player), active_player)

            self.log.append(
                [int(self.active_player), 
                    'powerfulhit', [f'💪 {int(power)}+3'], 'wood']
            )
            await self.Update()

            await self.next_player()
            await self.MessageGenerator('main', int(self.active_player))

    async def game_choose_dino_reply(self, dinos: list, action: str) -> types.InlineKeyboardMarkup:
        buttons = []
        for dino in dinos:
            buttons.append({
                'text': dino.name,
                'callback_data': self.CallbackGenerator('set_dino_to_attack', f'{dino.alt_id}:{action}'),
            })

        buttons += [
            {'text': 'Отмена', 'callback_data': self.CallbackGenerator('cancel'), 'ignore_row': 'true'},
        ]

        return self.list_to_inline(buttons, 2, False)

    async def game_ChooseDinoGenerator(self, user_id: int) -> None:
        dinos = []
        text = f'Выберите динозавра для атаки:\n'
        # Перебираем всех игроков, кроме себя
        for pid, pdata in self.PLAYERS.items():
            if int(pid) == int(user_id):
                continue

            dino = await Dino().create(pdata.data['dino'])
            if dino:
                dinos.append(dino)
                text += f'{dino.name} ({pdata.user_name})'
                text += f'\n💪 Сила: {dino.stats["power"]}'
                text += f'\n🦵 Ловкость: {dino.stats["dexterity"]}'
                text += f'\n💥 Перегрузка: {pdata.data["dino_overload"]}\n\n'

        if not dinos:
            text += 'Нет доступных динозавров для атаки.'

        us_stage = await self.UserStage(user_id)
        if us_stage:
            action = us_stage.data.get('action', 'net')

            await self.AddMessageToQueue('main', text=text, 
                        reply_markup=await self.game_choose_dino_reply(dinos, action))

    async def game_NetDino(self, callback: types.CallbackQuery) -> None:
        
        player = await self.GetPlayer(int(self.active_player))
        if player:
            if player.data['net_limit'] > 0:
                await self.SetStage('choose_dino', callback.from_user.id, {'action': 'net'})
            else:
                await callback.answer('У вас закончились паутины!')

    async def game_TakeAxe(self, callback: types.CallbackQuery) -> None:
        player = await self.GetPlayer(int(self.active_player))
        if player:
            if player.data['without_limit'] > 0:
                await self.SetStage('choose_dino', callback.from_user.id, {'action': 'take_axe'})
            else:
                await callback.answer('У вас закончился крюк!')

    async def game_Pass(self, callback: types.CallbackQuery | None) -> None:
        self.log.append(
                    [int(self.active_player), 'pass', [], None]
                )
        await self.Update()
        await self.next_player()
        await self.MessageGenerator('main', int(self.active_player))

    async def game_ChooseDinoToAttack(self, callback: types.CallbackQuery) -> None:

        player = await self.GetPlayer(int(self.active_player))
        if player:
            data = callback.data.split(':')

            dino_alt_id = data[3]
            action = data[4]
            
            await self.OffButtons(list(self.ButtonsRegister.keys()))
            await self.SetStage('game', callback.from_user.id)

            if action == 'net':
                if player.data['net_limit'] > 0:
                    player.data['net_limit'] -= 1
                    await self.EditPlayer(int(self.active_player), player)

                    attack_player = 0
                    for pid, pdata in self.PLAYERS.items():
                        if pdata.data['dino'] == dino_alt_id:
                            attack_player = pid
                            break

                    if attack_player:

                        attack_player = await self.GetPlayer(int(attack_player))
                        if attack_player:
                            attack_player.data['in_net'] = True
                            await self.EditPlayer(int(attack_player.user_id), attack_player)

                            dino = await Dino().create(dino_alt_id)
                            if dino:
                                self.log.append(
                                    [int(self.active_player), 'net', [], attack_player.user_id]
                                )
            
            if action == 'take_axe':
                if player.data['without_limit'] > 0:
                    player.data['without_limit'] -= 1
                    await self.EditPlayer(int(self.active_player), player)

                    attack_player = 0
                    for pid, pdata in self.PLAYERS.items():
                        if pdata.data['dino'] == dino_alt_id:
                            attack_player = pid
                            break

                    if attack_player:
                        attack_player = await self.GetPlayer(int(attack_player))

                        d1, d2 = await self.game_RollDice(callback, action_type='take_axe')

                        result = d1 + (player.data['dino_dexterity'] // 2)
                        result2 = d2 + (attack_player.data['intelligence'] // 2)

                        if result > result2:

                            if attack_player:
                                attack_player.data['without_tools'] = True
                                await self.EditPlayer(int(attack_player.user_id), attack_player)

                                dino = await Dino().create(dino_alt_id)
                                if dino:
                                    self.log.append(
                                        [int(self.active_player), 'take_axe', [[d1, (player.data['dino_dexterity'] // 2)], [d2, (attack_player.data['intelligence'] // 2)]], attack_player.user_id]
                                    )
                                    await self.Update()
                        else:
                            if attack_player:
                                self.log.append(
                                        [int(self.active_player), 'no_take_axe', [[d1, (player.data['dino_dexterity'] // 2)], [d2, (attack_player.data['intelligence'] // 2)]], attack_player.user_id]
                                    )
                                await callback.answer('Атака не удалась! Динозавр был слишком внимательным!')

            await self.OnButtons(list(self.ButtonsRegister.keys()))
            await self.next_player()
            await self.MessageGenerator('main', int(self.active_player))

    async def game_RollDice(self, callback: types.CallbackQuery, action_type: str):

        await self.OffButtons(list(self.ButtonsRegister.keys()))

        # try:
        #     res = await bot.send_dice(callback.message.chat.id, emoji='🎲', reply_markup=None, reply_to_message_id=callback.message.message_thread_id)

        #     res2 = await bot.send_dice(callback.message.chat.id, emoji='🎲', reply_markup=None, reply_to_message_id=callback.message.message_thread_id)
        # except Exception as e:
        #     self.D_log(f'game_RollDice: {e}')
        #     return 0, 0

        await self.MessageGenerator('main', int(self.active_player), action_type=action_type)
        
        res1, res2 = random.randint(1, 6), random.randint(1, 6)
        await sleep(3)

        # try:
        #     await res.delete()
        #     await res2.delete()
        # except: pass

        await self.OnButtons(list(self.ButtonsRegister.keys()))
        # return res.dice.value, res2.dice.value
        return res1, res2

    async def game_main_reply_markup(self, user_id: int):
        
        player = await self.GetPlayer(user_id)

        dat = player.data
        buttons = [
            {'text': 'Удар', 'callback_data': self.CallbackGenerator('simple_hit')},
            {'text': 'Мощный удар', 'callback_data': self.CallbackGenerator('powerful_hit')},
            {'text': f'Паутина ({dat["net_limit"]} / {self.max_net_lim})', 
                'callback_data': self.CallbackGenerator('net_dino')},
            {'text': f'Крюк ({dat["without_limit"]} / {self.max_without_lim})', 'callback_data': self.CallbackGenerator('take_axe')},
            {'text': 'Пропустить', 'callback_data': self.CallbackGenerator('pass')},
            {'text': 'Выйти', 'callback_data': self.CallbackGenerator('exit')},
        ]
        return self.list_to_inline(buttons, 2, False)

    async def log_generator(self):
        text = ''

        logs = self.log[-3:]
        for who, act_type, list_units, to_object in logs:
            who_player = await self.GetPlayer(who)

            if who_player:
                my_dino = await Dino().create(who_player.data['dino'])
                # ['simplehit', [d1, d2, power // 50], 'wood']
                # ['powerfulhit', [power], 'wood']
                text += '• '

                if act_type in ['simplehit']:
                    text += f'`{who_player.user_name}` ▷ Нанёс удар по 🪵 с силой {" ".join(list_units)}'
                    # text += f'{who_player.user_name} 🪓 {" ".join(list_units)} ▷ 🪵'

                elif act_type in ['powerfulhit']:
                    text += f'`{who_player.user_name}` ▷ Нанёс мощный удар по 🪵 с силой {" ".join(list_units)}'
                    # text += f'{who_player.user_name} 🪓 {" ".join(list_units)} ▷ 🪵'

                elif act_type == 'net':
                    to_player = await self.GetPlayer(to_object)
                    attack_dino = await Dino().create(to_player.data['dino'])
                    if attack_dino:
                        text += f'`{who_player.user_name}` 🕸️ ▷ {attack_dino.name} попал в паутину'
                    # text += f'{who_player.user_name} ▷ {" ".join(list_units)}'

                elif act_type == 'overload':
                    text += f'`{who_player.user_name}` 💥 ▷ Перегружен, пропускает ход'

                elif act_type == 'pass':
                    text += f'`{who_player.user_name}` ▷ Пропускает ход'

                elif act_type == 'take_axe':
                    to_player = await self.GetPlayer(to_object)
                    attack_dino = await Dino().create(to_player.data['dino'])
                    if attack_dino:
                        text += f'`{who_player.user_name}` ▷ Отобрал топор у {attack_dino.name}\n' \
                            f'• 🎲 {list_units[0][0]} 🍃 {list_units[0][1]} > 🎲 {list_units[1][0]} 🧠 {list_units[1][1]}'

                elif act_type == 'no_take_axe':
                    to_player = await self.GetPlayer(to_object)
                    attack_dino = await Dino().create(to_player.data['dino'])
                    if attack_dino:
                        text += f'`{who_player.user_name}` ▷ Не удалось отобрать топор у {attack_dino.name}\n' \
                            f'• 🎲 {list_units[0][0]} 🍃 {list_units[0][1]} < 🎲 {list_units[1][0]} 🧠 {list_units[1][1]}'

                text += '\n'
        return text #[:-1]

    async def game_GameGenerator(self, user_id: int, action_type: str | None = None) -> None:
        data_act_player = self.PLAYERS[self.active_player]
        text = "Игроки\n"
        for player_id, player_data in self.PLAYERS.items():
            remaining_power = player_data.data['units']
            overload = player_data.data['dino_overload']

            percentage = int((remaining_power / self.power) * 100)
            # if player_id == self.active_player: my_percent = percentage

            activ_emoji = '○'
            if player_id == self.active_player: activ_emoji = '▷'

            text += f"{activ_emoji} `{player_data.user_name}` ── 🪵 {percentage}% 💥 {overload}"

            if player_data.data['in_net']:
                text += ' 🕸️'

            if player_data.data['without_tools']:
                text += ' 🪓'

            text += '\n'

        if self.log:
            text += '\nПоследние действия\n'
            text += await self.log_generator()

        if not action_type:
            wait = self.time_wait - (time.time() - self.LAST_ACTION) if self.time_wait - (time.time() - self.LAST_ACTION) > 0 else 0
            str_wait = seconds_to_str(int(wait), self.LANGUAGE)
            
            text += f'\n`{data_act_player.user_name}` Выбирает действие... (`{str_wait} до пропуска`)\n' 

        if action_type == 'simplehit':
            text += '\nВыбранное действие: Удар по дереву\n' \
                    '- Ожидайте пока кубики упадут, после чего динозавр нанесёт удар по дереву.' 
        elif action_type == 'take_axe':
            text += '\nВыбранное действие: Отобрать топор\n' \
                    '- Ожидайте пока кубики упадут, после чего динозавр попытается отобрать топор.\n' \
                    '- Если ловкость вашего динозавра больше, чем интеллект противника, то атака будет успешной.' 

        # await self.button_control(int(self.active_player))

        await self.AddMessageToQueue('main', text=text, 
                                reply_markup=await self.game_main_reply_markup(user_id))


PowerChecker().RegistryMe() # Регистрация класса в реестре
