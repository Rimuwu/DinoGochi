from random import randint

from telebot.types import Message

from bot.config import mongo_client
from bot.const import GAME_SETTINGS
from bot.exec import bot
from bot.modules.accessory import check_accessory
from bot.modules.data_format import list_to_inline
from bot.modules.dinosaur import Dino, end_game
from bot.modules.friends import send_action_invite
from bot.modules.images import dino_game
from bot.modules.localization import get_data, t, get_lang
from bot.modules.markup import cancel_markup
from bot.modules.markup import markups_menu as m
from bot.modules.mood import add_mood, check_breakdown, check_inspiration
from bot.modules.states_tools import ChooseStepState
from bot.modules.user import User, premium
from bot.modules.quests import quest_process
from time import time
 

dinosaurs = mongo_client.dinosaur.dinosaurs
game_task = mongo_client.dino_activity.game

async def start_game_ent(userid: int, chatid: int, 
                         lang: str, dino: Dino, 
                         friend: int = 0, join: bool = True, 
                         join_dino: str = ''):
    """ Запуск активности игра
        friend - id друга при наличии
        join - присоединяется ли человек к игре
    """
    transmitted_data = {
        'dino': dino, 
        'friend': friend, 'join': join,
        'join_dino': join_dino
    }

    # Создание первого выбора
    game_data = get_data('entertainments', lang)
    game_buttons, options = [], {}
    last_game = '-'
    need = ['console', 'snake', 'pin-pong', 'ball']

    if await check_accessory(dino, 'board_games'):
        need += ["puzzles", "chess", "jenga", "dnd"]

    if await premium(userid):
        need += ["monopolia", "bowling", "darts", "golf"]

    for key, value in game_data['game'].items():
        if key in need:
            options[value] = key
            game_buttons.append(value)

    if dino.memory['games']:
        last = dino.memory['games'][0]
        last_game = t(f'entertainments.game.{last}', lang)

    # Второе сообщение
    buttons = {}
    cc = randint(1, 100)

    for key, value in get_data('entertainments.time', lang).items():
        buttons[value['text']] = f'chooseinline {cc} {key}'
    markup = list_to_inline([buttons])

    steps = [
        {"type": 'pages', "name": 'game', 
          "data": {"options": options}, 
          'translate_message': True,
          'translate_args': {'last_game': last_game},
          'message': {'text': 'entertainments.answer_game'}
        },
        {
            "type": 'update_data', 'name': 'zero',
            'function': delete_markup,
            'async': True
        },
        {"type": 'inline', "name": 'time', "data": {'custom_code': cc}, 
          'translate_message': True,
          'delete_message': True,
          'message': {'text': 'entertainments.answer_text',
                      'reply_markup': markup
              }
        }
    ]

    await ChooseStepState(game_start, userid, chatid, lang, steps, transmitted_data)

async def delete_markup(transmitted_data):
    chatid = transmitted_data['chatid']
    lang = transmitted_data['lang']
    
    text = t(f'entertainments.zero', lang)
    await bot.send_message(chatid, text, reply_markup=cancel_markup(lang))
    return transmitted_data, 0

async def game_start(return_data: dict, 
                     transmitted_data: dict):
    userid = transmitted_data['userid']
    chatid = transmitted_data['chatid']
    lang = transmitted_data['lang']
    dino: Dino = transmitted_data['dino']

    friend = transmitted_data['friend']
    join_status = transmitted_data['join']
    join_dino = transmitted_data['join_dino']
    friend_dino_id = 0

    game = return_data['game']
    code = return_data['time']

    res_dino_status = await dinosaurs.find_one({"_id": dino._id}, {'status': 1})
    if res_dino_status:
        if res_dino_status['status'] != 'pass':
            await bot.send_message(chatid, t('alredy_busy', lang), reply_markup= await m(userid, 'last_menu', lang))
            return

    percent, repeat = await dino.memory_percent('games', game)

    if friend and join_status and join_dino:
        dino_f = await dinosaurs.find_one({'alt_id': join_dino})
        if dino_f:
            friend_dino_id = dino_f['data_id']
            res = await game_task.find_one({'dino_id': dino_f['_id']})
            if not res: 
                join_dino = 0
                text_m = t('entertainments.join_end', lang)
                await bot.send_message(chatid, text_m)
            else: 
                percent += 0.5

                res = await game_task.find_one({'dino_id': dino_f['data_id']})
                if res and res['game_percent'] < 2.0:
                    await game_task.update_one({'dino_id': dino_f['data_id']}, 
                                        {'$inc': {'game_percent': 0.5}})

                await add_mood(dino._id, 'playing_together', 1, 1800)
                await add_mood(dino_f['data_id'], 'playing_together', 1, 1800)

                text_m = t('entertainments.dino_join', lang, 
                            dinoname=dino.name)
                image = await dino_game(friend_dino_id, dino.data_id)
                await bot.send_photo(friend, image, text_m)

    r_t = get_data('entertainments', lang)['time'][code]['data']
    game_time = randint(*r_t) * 60

    res = await check_inspiration(dino._id, 'game')
    if res: percent += 1.0

    await dino.game(game_time, percent)
    image = await dino_game(dino.data_id, friend_dino_id)

    text = t(f'entertainments.game_text.m{str(repeat)}', lang, 
            game=t(f'entertainments.game.{game}', lang)) + '\n'
    if percent < 1.0:
        text += t(f'entertainments.game_text.penalty', lang, percent=int(percent*100))

    await bot.send_photo(chatid, image, text, 
                         reply_markup=await m(userid, 'last_menu', lang, True))

    # Пригласить друга
    if friend and not join_status:
        await send_action_invite(userid, friend, 'game', dino.alt_id, lang)
    elif not friend:
        text = t('entertainments.invite_friend.text', lang)
        button = t('entertainments.invite_friend.button', lang)
        markup = list_to_inline([
            {button: f'invite_to_action game {dino.alt_id}'}
        ])
        await bot.send_message(chatid, text, reply_markup=markup)

@bot.message_handler(pass_bot=True, text='commands_name.actions.entertainments', dino_pass=True, nothing_state=True)
async def entertainments(message: Message):
    userid = message.from_user.id
    lang = await get_lang(message.from_user.id)
    chatid = message.chat.id

    user = await User().create(userid)
    dino = await user.get_last_dino()
    if dino: await start_game_ent(userid, chatid, lang, dino)

@bot.message_handler(pass_bot=True, text='commands_name.actions.stop_game')
async def stop_game(message: Message):
    userid = message.from_user.id
    lang = await get_lang(message.from_user.id)
    chatid = message.chat.id

    user = await User().create(userid)
    last_dino = await user.get_last_dino()
    if last_dino:
        penalties = GAME_SETTINGS['penalties']["games"]
        game_data = await game_task.find_one({'dino_id': last_dino._id})
        random_tear, text = 1, ''

        res = await check_breakdown(last_dino._id, 'unrestrained_play')

        if not res:
            if game_data:
                # Определение будет ли дебафф к настроению
                if game_data['game_percent'] == penalties['0']:
                    random_tear = randint(1, 2)
                elif game_data['game_percent'] == penalties['1']:
                    random_tear = randint(1, 3)
                elif game_data['game_percent'] == penalties['2']:
                    random_tear = randint(0, 2)
                elif game_data['game_percent'] == penalties['3']:
                    random_tear = 0

                if randint(1, 2) == 1 or not random_tear:
                    
                    if random_tear == 1:
                        # Дебафф к настроению
                        text = t('stop_game.like', lang)
                        await add_mood(last_dino._id, 'stop_game', randint(-2, -1), 3600)
                    elif random_tear == 0:
                        # Не нравится динозавру играть, без дебаффа
                        text = t('stop_game.dislike', lang)
                    else:
                        # Завершение без дебаффа
                        text = t('stop_game.whatever', lang)

                    await end_game(last_dino._id, False)
                    game_time = (int(time()) - game_data['game_start']) // 60
                    await quest_process(userid, 'game', game_time)
                else:
                    # Невозможно оторвать от игры
                    text = t('stop_game.dont_tear', lang)
                await bot.send_message(chatid, text, reply_markup= await m(userid, 'last_menu', lang, True))

            else:
                if last_dino.status == 'game':
                    await last_dino.update({'$set': {'status': 'pass'}})
                await bot.send_message(chatid, '❌', reply_markup= await m(userid, 'last_menu', lang, True))
        else:
            await bot.send_message(chatid, t('stop_game.unrestrained_play', lang))