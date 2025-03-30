

from bot.dataclasess.minigame import Button, Stage, stageButton
from bot.minigames.powerchecker.minigame_powerchecker import PowerChecker
from bot.modules.decorators import register_method
from bot.modules.user.user import User, user_name
from aiogram import types

@register_method(PowerChecker)
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
        )
    }

    await self.Update()
    await self.SetStage('wait_user')

@register_method(PowerChecker)
async def Endandleave(self, callback) -> None:
    """ Покинуть игру или завершить если создатель"""
    if callback.from_user.id == self.owner_id:
        await self.EndGame()
    else:
        await self.DeletePlayer(callback.from_user.id)
        await callback.answer('Вы покинули игру')

        await self.on_user_col_edit()
        await self.MessageGenerator('main', callback.from_user.id)

@register_method(PowerChecker)
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

@register_method(PowerChecker)
async def WaitUsersStartGenerator(self, user_id: int) -> None:
    markup = await self.waituser_inline(user_id)
    text = 'Ожидание игроков'
    players = self.PLAYERS.values()

    table = "\n".join(
        [f"{player.user_name} - {'Готов' if player.data.get('dino') else 'Не готов'}" for player in players]
    )
    text += f"\n\nСостояние игроков:\n{table}"
    await self.MesageUpdate(text=text, reply_markup=markup)

@register_method(PowerChecker)
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

@register_method(PowerChecker)
async def waituser_CancelChoose(self, callback) -> None:
    """ Отмена выбора динозавра и удаление сообщения с выбором """
    user_id = callback.from_user.id

    await self.DeletePlayer(user_id)
    await self.DeleteMessage(f'choose_dino_{user_id}')
    self.message_generators.pop(f'choose_dino_{user_id}')
    await self.Update()

    await self.MessageGenerator('main', user_id)

@register_method(PowerChecker)
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

@register_method(PowerChecker)
async def enter_dino_generator(self, user_id) -> None:
    markup = await self.dino_markup(user_id) # type: ignore
    text = f'{user_id} Выберите динозавра:'
    await self.MesageUpdate(f'choose_dino_{user_id}', 
                            text=text, reply_markup=markup)

@register_method(PowerChecker)
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

@register_method(PowerChecker)
async def waituser_NextStage(self, callback) -> None:
    self.D_log('waituser_NextStage', True)
    ready = 0
    for player in self.PLAYERS.values():
        if player.data.get('ready'):
            ready += 1

    this_player = await self.GetPlayer(callback.from_user.id)
    if this_player:
        this_player.data['ready'] = not this_player.data.get('ready', False)
        if this_player.data['ready']: ready += 1
        
        if ready != len(self.PLAYERS):
            await self.EditPlayer(callback.from_user.id, this_player)
            await self.MessageGenerator('main', callback.from_user.id)

    if ready == len(self.PLAYERS):
        self.D_log('StartGame -------------', True)
        await self.game_StartGame()