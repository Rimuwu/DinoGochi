


import time
from bot.minigames.powerchecker.minigame_powerchecker import PowerChecker
from bot.modules.decorators import register_method
from bot.modules.localization import t, get_all_locales
from bot.modules.user.user import User, take_coins
from aiogram import types
from bot.models.dinosaur import Dino
from bot.exec import bot

@register_method(PowerChecker)
async def on_preparation(self) -> None:
    owner_player = await self.GetPlayer(self.owner_id)
    owner_has_dino = 'dino' in owner_player.data and owner_player.data['dino']

    if owner_has_dino and self.bet > 0 and self.max_players > 1:
        bt = self.ButtonsRegister['wait_users_start']
        bt.active = True

        await self.EditButton('wait_users_start', bt)
        # await self.MessageGenerator('preparation', self.owner_id)

@register_method(PowerChecker)
async def PreparationMarkup(self):
    buttons = [
        {'text': '👥 Игроки', 'callback_data': self.CallbackGenerator('max_col')},
        {'text': '🦕 Динозавр', 'callback_data': self.CallbackGenerator('choose_dino')},
        {'text': '💰 Ставка', 'callback_data': self.CallbackGenerator('choose_bet')},
        {'text': '💢 Сложность', 'callback_data': self.CallbackGenerator('hard_lvl')},
        {'text': '🚪 Завершить игру', 'callback_data': self.CallbackGenerator('end_game'), 
         'ignore_row': 'True'},
    ]

    language_name = t('language_name', self.LANGUAGE)
    buttons.insert(3, {
        'text': language_name, 'callback_data': self.CallbackGenerator('change_language')
    })

    owner_player = await self.GetPlayer(self.owner_id)
    owner_has_dino = 'dino' in owner_player.data and owner_player.data['dino']

    if owner_has_dino and self.bet > 0 and self.max_players > 1:
        buttons.insert(0, {
            'text': '🌐 Начать игру', 'callback_data': self.CallbackGenerator('wait_users_start'), 'ignore_row': 'true'
            })

    return self.list_to_inline(buttons)

@register_method(PowerChecker)
async def PreparationGenerator(self, user_id) -> None:

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

    text = f'Динозавр: {dino_name}\nСтавка: {bet_text}\nМакс. игроков: {self.max_players}\n{time_left_text}'
    markup = await self.PreparationMarkup()
    await self.AddMessageToQueue('main', text=text, reply_markup=markup)


@register_method(PowerChecker)
async def max_playersMarkup(self):
    buttons = [
        {'text': '2 игрока', 'callback_data': self.CallbackGenerator('col_players', '2')},
        {'text': '3 игрока', 'callback_data': self.CallbackGenerator('col_players', '3')},
        {'text': '4 игрока', 'callback_data': self.CallbackGenerator('col_players', '4')},
        {'text': 'back', 'callback_data': self.CallbackGenerator('to_preparation')},
    ]
    
    buttons[self.max_players - 2]['text'] = '✅ ' + buttons[self.max_players - 2]['text']
        
    
    return self.list_to_inline(buttons, 3)

@register_method(PowerChecker)
async def delete_only_for(self):
    buttons = [
        {'text': '🔓 Открыть доступ для всех', 'callback_data': self.CallbackGenerator('delete_only_for', '2')},
        {'text': 'back', 'callback_data': self.CallbackGenerator('to_preparation')},
    ]
    return self.list_to_inline(buttons, 1)

@register_method(PowerChecker)
async def DeleteOnlyFor(self, callback) -> None:
    self.only_for = 0
    await self.Update()
    await self.MyMessGenerator(callback.from_user.id)

@register_method(PowerChecker)
async def MaxPlayersGenerator(self, user_id) -> None:
    markup = await self.max_playersMarkup()
    text = 'Выберите максимальное количество игроков:'

    if self.only_for != 0:
        player_data = await self.GetPlayer(user_id)
        if player_data is not None:
            onl_user = await bot.get_chat_member(chat_id=player_data.chat_id, user_id=self.only_for)

            onl_name = onl_user.user.first_name if onl_user.user.first_name else 'пользователь'

            text = f"Игра доступна только для {onl_name}.\n\n" \
                f"Вы можете сбросить защищённый режим нажав на кнопку ниже."
            markup = await self.delete_only_for()

    await self.AddMessageToQueue('main', text=text, reply_markup=markup)


@register_method(PowerChecker)
async def ColPlayers_set(self, callback) -> None:
    max_players = callback.data.split(':')[3]
    self.max_players = int(max_players)
    await self.Update()

    await self.MyMessGenerator(callback.from_user.id)

@register_method(PowerChecker)
async def ChooseDino_set(self, callback) -> None:
    dino_name = callback.data.split(':')[3]
    user_id = callback.from_user.id
    player = await self.GetPlayer(user_id)
    if player:
        old_dino = player.data.get('dino', None)
        if old_dino != dino_name:
            player.data['dino'] = dino_name
            await self.EditPlayer(user_id, player)
            await self.UpdateImage('main')

    await self.Update()
    await self.SetStage('preparation')

@register_method(PowerChecker)
async def ChooseDinoGenerator(self, user_id) -> None:
    markup = await self.dino_markup(user_id)
    text = 'Выберите динозавра:'
    await self.AddMessageToQueue('main', text=text, reply_markup=markup)


@register_method(PowerChecker)
async def choose_betMarkup(self):
    buttons = [
        {'text': '🪙 1000', 'callback_data': self.CallbackGenerator('choose_bet_set', '1000')},
        {'text': '🪙 5000', 'callback_data': self.CallbackGenerator('choose_bet_set', '5000')},
        {'text': '🪙 10000', 'callback_data': self.CallbackGenerator('choose_bet_set', '10000')},
        {'text': 'back', 'callback_data': self.CallbackGenerator('to_preparation')},
    ]
    
    bet_lst = [1000, 5000, 10000]
    if self.bet in bet_lst:
        buttons[bet_lst.index(self.bet)]['text'] = f'✅ {buttons[bet_lst.index(self.bet)]["text"][2:]}'
    else:
        buttons.insert(3, {
            'text': '✅ ' + str(self.bet), 
            'callback_data': self.CallbackGenerator('choose_bet_set', str(self.bet)),
            'ignore_row': 'true'
        })

    return self.list_to_inline(buttons, 3)

@register_method(PowerChecker)
async def bet_check(self, user_id, coins):
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

        await self.MessageGenerator('choose_bet', user_id)


@register_method(PowerChecker)
async def ChooseBetGenerator(self, user_id) -> None:
    markup = await self.choose_betMarkup()
    text = 'Выберите ставку:'
    await self.AddMessageToQueue('main', text=text, reply_markup=markup)

@register_method(PowerChecker)
async def ChooseBet_set(self, callback) -> None:
    bet = callback.data.split(':')[3]

    await self.bet_check(callback.from_user.id, int(bet))

@register_method(PowerChecker)
async def IntWaiter(self, message: types.Message, command: bool = False):
    if command: 
        coins = int(message.text.split(' ')[3]) # type: ignore
    else:
        coins = int(message.text) # type: ignore

    try:
        await message.delete()
    except: pass

    await self.bet_check(message.from_user.id, coins)

@register_method(PowerChecker)
async def EndGame_c(self, callback) -> None:
    await self.EndGame()

@register_method(PowerChecker)
async def language_markup(self):
    
    buttons = []
    langs = get_all_locales('language_name')

    for lang_key, lang_name in langs.items():
        if lang_key == self.LANGUAGE:
            lang_name = '✅ ' + lang_name[2:]
        buttons.append({
            'text': lang_name, 
            'callback_data': self.CallbackGenerator('choose_language_set', lang_key)
        })

    buttons.append({
        'text': 'back',
        'callback_data': self.CallbackGenerator('to_preparation'),
        'ignore_row': 'true'
    })

    return self.list_to_inline(buttons, 3)

@register_method(PowerChecker)
async def ChangeLanguageGenerator(self, user_id) -> None:
    markup = await self.language_markup()
    text = 'Выберите язык (для всех):'
    await self.AddMessageToQueue('main', text=text, reply_markup=markup)

@register_method(PowerChecker)
async def ChangeLanguage_set(self, callback) -> None:
    lang_key = callback.data.split(':')[3]

    self.LANGUAGE = lang_key
    await self.Update()

    # await self.MessageGenerator('change_language', callback.from_user.id)
    await self.MyMessGenerator(callback.from_user.id)

@register_method(PowerChecker)
async def hard_lvl_markup(self):
    buttons = [
        {'text': 'Легкий', 'callback_data': self.CallbackGenerator('hard_lvl_set', '1')},
        {'text': 'Средний', 'callback_data': self.CallbackGenerator('hard_lvl_set', '2')},
        {'text': 'Сложный', 'callback_data': self.CallbackGenerator('hard_lvl_set', '3')},
        {'text': 'back', 'callback_data': self.CallbackGenerator('to_preparation'),
         'ignore_row': 'true'},
    ]

    buttons[ self.hard_lvl - 1 ]['text'] = \
        f'✅ {buttons[ self.hard_lvl - 1 ]["text"]}'

    return self.list_to_inline(buttons, 3)

@register_method(PowerChecker)
async def HardLvlGenerator(self, user_id) -> None:

    markup = await self.hard_lvl_markup()
    text = 'От сложности зависит прочность древа.\n' \
           'Выберите сложность:\n' \
           '1 - Легкий (20 - 40)\n' \
           '2 - Средний (50 - 80)\n' \
           '3 - Сложный (80 - 150)\n'
    await self.AddMessageToQueue('main', text=text, reply_markup=markup)

@register_method(PowerChecker)
async def HardLvl_set(self, callback) -> None:

    hard_lvl = callback.data.split(':')[3]

    self.hard_lvl = int(hard_lvl)
    await self.Update()

    await self.MessageGenerator('hard_lvl', callback.from_user.id)

@register_method(PowerChecker)
async def ToPreparation(self, callback) -> None:

    waiter = self.WaiterRegister['int']
    waiter.active = False

    await self.EditWaiter('wait_bet', waiter)