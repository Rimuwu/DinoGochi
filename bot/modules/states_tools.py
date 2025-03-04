from optparse import Option
from typing import Optional, Union
from aiogram.fsm.state import StatesGroup, State
from aiogram.types import InlineKeyboardMarkup
from aiogram.fsm.context import FSMContext
from bot.exec import bot
from bot.modules.data_format import (chunk_pages, list_to_inline,
                                     list_to_keyboard)
from bot.modules.get_state import get_state
from bot.modules.images import async_open
from bot.modules.inventory_tools import start_inv
from bot.modules.localization import get_data, t
from bot.modules.logs import log
from bot.modules.markup import down_menu, get_answer_keyboard
from bot.modules.markup import markups_menu as m
from bot.modules.overwriting.DataCalsses import DBconstructor
from bot.modules.user.friends import get_friend_data
from bot.modules.user.user import User, get_frineds, user_info, user_name
from aiogram.fsm.context import FSMContext
from bot.modules.managment.events import check_event
import inspect
from bot.dbmanager import mongo_client

sellers = DBconstructor(mongo_client.market.sellers)

class GeneralStates(StatesGroup):
    ChooseDino = State() # Состояние для выбора динозавра
    ChooseInt = State() # Состояние для ввода числа
    ChooseString = State() # Состояние для ввода текста
    ChooseConfirm = State() # Состояние для подтверждения (да / нет)
    ChooseOption = State() # Состояние для выбора среди вариантов
    ChooseInline = State() # Состояние для выбора кнопки
    ChoosePagesState = State() # Состояние для выбора среди вариантов, а так же поддерживает страницы
    ChooseCustom = State() # Состояние для кастомного обработчика
    ChooseTime = State() # Состояние для ввода времени
    ChooseImage = State() # Состояние для ввода загрузки изображения

def add_if_not(data: dict, userid: int, chatid: int, lang: str, state: FSMContext | None):
    """Добавляет минимальные данные для работы"""
    if 'userid' not in data: data['userid'] = userid
    if 'chatid' not in data: data['chatid'] = chatid
    if 'lang' not in data: data['lang'] = lang
    if 'state' not in data: 
        if state: data['state'] = state
    return data

async def ChooseDinoState(function, 
                          userid: int, chatid: int, 
        lang: str, add_egg: bool=True, all_dinos: bool=True,
        transmitted_data=None, send_error: bool = True, state: Union[FSMContext, None] = None):
    """ Устанавливает состояние ожидания динозавра
        all_dinos - Если False то не будет совместных динозавров 
        send_error - Если True то будет уведомлять о том, что нет динозавров / яиц

       В function передаёт 
       >>> element: Dino | Egg, transmitted_data: dict
       
       Return:
        Возвращает 2 если был создано состояние, 1 если завершилось автоматически (1 вариант выбора), 0 - невозможно завершить
    """
    if not state: state = await get_state(userid, chatid)

    user = await User().create(userid)
    elements = await user.get_dinos(all_dinos)

    if add_egg: elements += await user.get_eggs
    if not transmitted_data: transmitted_data = {}

    transmitted_data = add_if_not(transmitted_data, userid, chatid, lang, state)
    ret_data = get_answer_keyboard(elements, lang)

    if ret_data['case'] == 0:
        if send_error:
            await bot.send_message(chatid, 
                t('css.no_dino', lang),
                reply_markup= await m(userid, 'last_menu', lang))
        return False, 'cancel'

    elif ret_data['case'] == 1: #1 динозавр / яйцо, передаём инфу в функцию
        element = ret_data['element']
        await function(element, transmitted_data)
        return False, 'dino'

    elif ret_data['case'] == 2:# Несколько динозавров / яиц
        # Устанавливаем состояния и передаём данные
        await state.set_state(GeneralStates.ChooseDino)

        data = {}
        data['function'] = function
        data['dino_names'] = ret_data['data_names']
        data['transmitted_data'] = transmitted_data
        await state.set_data(data)

        await bot.send_message(chatid, t('css.dino', lang), reply_markup=ret_data['keyboard'])
        return True, 'dino'

    else: return False, 'error'

async def ChooseIntState(function, 
                         userid: int, chatid: int, lang: str,
                         min_int: int = 1, max_int: int = 10,
                         autoanswer: bool = True,
                         transmitted_data=None, state: Union[FSMContext, None] = None):
    """ Устанавливает состояние ожидания числа

        В function передаёт 
        >>> number: int, transmitted_data: dict
        
        Если max_int == 0, значит нет ограничения.
        
        Return:
         Возвращает True если был создано состояние, False если завершилось автоматически (минимальный и максимальный вариант совпадают)
    """
    if not state: state = await get_state(userid, chatid)

    if not transmitted_data: transmitted_data = {}
    transmitted_data = add_if_not(transmitted_data, userid, chatid, lang, state)

    if min_int != max_int or not autoanswer:
        await state.set_state(GeneralStates.ChooseInt)

        data = {}
        data['function'] = function
        data['transmitted_data'] = transmitted_data
        data['min_int'] = min_int
        data['max_int'] = max_int
        await state.set_data(data)

        return True, 'int'
    else:
        await function(min_int, transmitted_data)
        return False, 'int'

async def ChooseStringState(function, 
                            userid: int, chatid: int, lang: str,
                            min_len: int = 1, max_len: int = 10,
                            transmitted_data=None, state: Union[FSMContext, None] = None):
    """ Устанавливает состояние ожидания сообщения

        В function передаёт 
        >>> string: str, transmitted_data: dict
        
        Return:
         Возвращает True если был создано состояние, не может завершится автоматически
    """
    if not state: state = await get_state(userid, chatid)
    if not transmitted_data: transmitted_data = {}

    transmitted_data = add_if_not(transmitted_data, userid, chatid, lang, state)
    await state.set_state(GeneralStates.ChooseString)

    data = {}
    data['function'] = function
    data['transmitted_data'] = transmitted_data
    data['min_len'] = min_len
    data['max_len'] = max_len
    await state.set_data(data)

    return True, 'string'

async def ChooseTimeState(function, 
                          userid: int, 
                          chatid: int, lang: str,
                          min_int: int = 1, max_int: int = 10,
                          transmitted_data=None, state: Union[FSMContext, None] = None):
    """ Устанавливает состояние ожидания сообщения в формате времени

        В function передаёт 
        >>> string: str, transmitted_data: dict
        
        Return:
         Возвращает True если был создано состояние, не может завершится автоматически
    """
    if not state: state = await get_state(userid, chatid)
    if not transmitted_data: transmitted_data = {}

    transmitted_data = add_if_not(transmitted_data, userid, chatid, lang, state)
    await state.set_state(GeneralStates.ChooseTime)

    data = {}
    data['function'] = function
    data['transmitted_data'] = transmitted_data
    data['min_int'] = min_int
    data['max_int'] = max_int
    await state.set_data(data)

    return True, 'time'

async def ChooseConfirmState(function, 
                             userid: int, 
                             chatid: int, lang: str, cancel: bool=False,
                             transmitted_data=None, state: Union[FSMContext, None] = None):
    """ Устанавливает состояние ожидания подтверждения действия

        В function передаёт 
        >>> answer: bool, transmitted_data: dict

        cancel - если True, то при отказе вызывает возврат в меню

        Return:
         Возвращает True если был создано состояние, не может завершится автоматически
    """
    if not state: state = await get_state(userid, chatid)

    if not transmitted_data: transmitted_data = {}
    transmitted_data['cancel'] = cancel

    transmitted_data = add_if_not(transmitted_data, userid, chatid, lang, state)
    await state.set_state(GeneralStates.ChooseConfirm)

    data = {}
    data['function'] = function
    data['transmitted_data'] = transmitted_data
    await state.set_data(data)

    return True, 'confirm'

async def ChooseOptionState(function, 
                            userid: int, 
                            chatid: int, lang: str,
                            options: dict = {},
                            transmitted_data=None, state: Union[FSMContext, None] = None):
    """ Устанавливает состояние ожидания выбора опции

        В function передаёт 
        >>> answer: ???, transmitted_data: dict

        options - {"кнопка": данные}

        Return:
         Возвращает True если был создано состояние, False если завершилось автоматически (1 вариант выбора)
    """
    if not state: state = await get_state(userid, chatid)
    if not transmitted_data: transmitted_data = {}

    transmitted_data = add_if_not(transmitted_data, userid, chatid, lang, state)

    if len(options) > 1:
        await state.set_state(GeneralStates.ChooseOption)

        data = {}
        data['function'] = function
        data['transmitted_data'] = transmitted_data
        data['options'] = options
        await state.set_data(data)

        return True, 'option'
    else:
        element = None
        if len(options.keys()) > 0:
            element = options[list(options.keys())[0]]
        await function(element, transmitted_data)
        return False, 'option'

async def ChooseInlineState(function, 
                            userid: int, 
                         chatid: int, lang: str,
                         custom_code: str,
                         transmitted_data=None, state: Union[FSMContext, None] = None):
    """ Устанавливает состояние ожидания нажатия кнопки
        Все ключи callback должны начинаться с 'chooseinline'
        custom_code - код сессии запроса кнопок (индекс 1)

        В function передаёт 
        >>> answer: list transmitted_data: dict
    """
    if not state: state = await get_state(userid, chatid)
    if not transmitted_data: transmitted_data = {}

    transmitted_data = add_if_not(transmitted_data, userid, chatid, lang, state)

    await state.set_state(GeneralStates.ChooseInline)

    data = {}
    data['function'] = function
    data['transmitted_data'] = transmitted_data
    data['custom_code'] = custom_code
    await state.set_data(data)

    return True, 'inline'

async def ChooseCustomState(function, 
                            custom_handler, userid: int, 
                            chatid: int, lang: str,
                            transmitted_data=None, state: Union[FSMContext, None] = None):
    """ Устанавливает состояние ожидания чего либо, все проверки идут через custom_handler
    
        custom_handler -> bool, Any !
        в custom_handler передаётся (Message, transmitted_data)

        В function передаёт 
        >>> answer: ???, transmitted_data: dict
        
        Return:
         result - второе возвращаемое из custom_handler
    """
    if not state: state = await get_state(userid, chatid)

    if not transmitted_data: transmitted_data = {}
    transmitted_data = add_if_not(transmitted_data, userid, chatid, lang, state)

    await state.set_state(GeneralStates.ChooseCustom)

    data = {}
    data['function'] = function
    data['transmitted_data'] = transmitted_data
    data['custom_handler'] = custom_handler
    await state.set_data(data)

    return True, 'custom'

async def update_page(pages: list, page: int, chat_id: int, lang: str):
    keyboard = list_to_keyboard(pages[page])
    keyboard = down_menu(keyboard, len(pages) > 1, lang)

    await bot.send_message(chat_id, t('optionplus.update_page', lang), reply_markup=keyboard)

async def ChoosePagesState(function, 
                           userid: int, chatid: int, lang: str,
                           options: dict = {}, 
                           horizontal: int=2, vertical: int=3,
                           transmitted_data=None, 
                           autoanswer: bool = True, one_element: bool = True,
                           update_page_function = update_page, state: Union[FSMContext, None] = None):
    """ Устанавливает состояние ожидания выбора опции
    
        options = {
            'button_name': data
        }

        autoanswer - надо ли делать авто ответ, при 1-ом варианте
        horizontal, vertical - размер страницы
        one_element - будет ли завершаться работа после выбора одного элемента

        В function передаёт 
        >>> answer: ???, transmitted_data: dict
            return 
               - если не требуется ничего обновлять, можно ничего не возвращать.
               - если требуется после какого то элемента удалить состояние - {'status': 'reset'}
               - если требуется обновить страницу с переданными данными - {'status': 'update', 'options': {}} (по желанию ключ 'page')
               - если требуется удалить или добавить элемент, при этом обновив страницу 
               {'status': 'edit', 'elements': {'add' | 'delete': data}}
                 - 'add' - в data требуется передать словарь с ключами, данные объединяются
                 - 'delete' - в data требуется передать список с ключами, ключи будут удалены

        В update_page_function передаёт 
        >>> pages: list, page: int, chat_id: int, lang: str

        Return:
         Возвращает True если был создано состояние, False если завершилось автоматически (1 вариант выбора)
    """
    if not state: state = await get_state(userid, chatid)
    if not transmitted_data: transmitted_data = {}

    transmitted_data = add_if_not(transmitted_data, userid, chatid, lang, state)

    # Чанкует страницы и добавляем пустые элементы для сохранения структуры
    pages = chunk_pages(options, horizontal, vertical)

    if len(options) > 1 or not autoanswer:
        await state.set_state(GeneralStates.ChoosePagesState)

        data = {}
        data['function'] = function
        data['update_page'] = update_page_function

        data['transmitted_data'] = transmitted_data
        data['options'] = options
        data['pages'] = pages

        data['page'] = 0
        data['one_element'] = one_element

        data['settings'] = {'horizontal': horizontal, "vertical": vertical}
        await state.set_data(data)

        await update_page_function(pages, 0, chatid, lang)
        return True, pages
    else:
        if len(options) == 0: element = None
        else: element = options[list(options.keys())[0]]

        await function(element, transmitted_data)
        return False, pages


async def friend_handler(friend: dict, transmitted_data: dict):
    lang = transmitted_data['lang']
    chatid = transmitted_data['chatid']
    friend_id = friend['userid']

    text, avatar = await user_info(friend_id, lang)
    buttons = {}

    for key, text_b in get_data('friend_list.buttons', lang).items():
        buttons[text_b] = f'{key} {friend_id}'

    if not await check_event("new_year"):
        del buttons[get_data(f'friend_list.buttons.new_year', lang)]

    market = await sellers.find_one({'owner_id': friend_id}, comment='friend_handler_market')
    if not market:
        del buttons[get_data(f'friend_list.buttons.open_market', lang)]

    markup = list_to_inline([buttons], 2)

    if avatar:
        await bot.send_photo(chatid, avatar, caption=text, parse_mode='Markdown', reply_markup=markup)
    else:
        await bot.send_message(chatid, text, parse_mode='Markdown', reply_markup=markup)

async def start_friend_menu(function,
                userid: int, chatid: int, lang: str, 
                one_element: bool=False,
                transmitted_data = None, state: Union[FSMContext, None] = None):
    res = await get_frineds(userid)
    friends = res['friends']
    options = {}

    if function == None: function = friend_handler

    a = 0
    for friend_id in friends:
        friend_res = await get_friend_data(friend_id, userid)
        if friend_res:
            if friend_res['name'] in options:
                a += 1 
                options[friend_res['name'] + f'# {a}'] = {
                    'userid': friend_id, 
                    'name': friend_res['name']}
            else:
                options[friend_res['name']] = {
                    'userid': friend_id, 
                    'name': friend_res['name']}

    await ChoosePagesState(
        function, userid, chatid, lang, options, 
        horizontal=2, vertical=3,
        autoanswer=False, one_element=one_element,  
        transmitted_data=transmitted_data, state=state)
    return True, 'friend'

async def ChooseImageState(function, 
                           userid: int, chatid: int, lang: str,
                           need_image: bool = True,
                           transmitted_data: Optional[dict] = None, state: Union[FSMContext, None] = None):
    """ Устанавливает состояние ожидания вводу изображения
        if need_image == True: даёт возможность на ответ 0 возвращать не file_id, а 'no_image'

        В function передаёт 
        >>> image_url: str transmitted_data: dict
    """

    if not isinstance(userid, int): raise TypeError('userid must be int')
    if not isinstance(chatid, int): raise TypeError('chatid must be int')
    if not isinstance(lang, str): raise TypeError('lang must be str')
    if not isinstance(need_image, bool): raise TypeError('need_image must be bool')
    if transmitted_data is not None and not isinstance(transmitted_data, dict): raise TypeError('transmitted_data must be dict or None')

    if not state: state = await get_state(userid, chatid)
    if not transmitted_data: transmitted_data = {}

    transmitted_data = add_if_not(transmitted_data, userid, chatid, lang, state)
    await state.set_state(GeneralStates.ChooseImage)

    data = {}
    data['function'] = function
    data['need_image'] = need_image
    data['transmitted_data'] = transmitted_data
    await state.set_data(data)

    return True, 'image'

chooses = {
    'dino': ChooseDinoState,
    'int': ChooseIntState,
    'time': ChooseTimeState,
    'str': ChooseStringState,
    'bool': ChooseConfirmState,
    'option': ChooseOptionState,
    'inline': ChooseInlineState,
    'custom': ChooseCustomState,
    'pages': ChoosePagesState,
    'inv': start_inv,
    'friend': start_friend_menu,
    'image': ChooseImageState
}

def prepare_steps(steps: list, userid: int, chatid: int, lang: str, 
                  state: FSMContext | None = None):
    for step in steps:
        if step['type'] in chooses:
            step['function'] = chooses[step['type']]

            step['data'] = dict(add_if_not(
                step['data'], userid, chatid, lang, None))
        elif step['type'] == 'update_data': pass
            # В данных уже должен быть ключ function
            # function получает transmitted_data
            # function должна возвращать transmitted_data, answer
        else: steps.remove(step)
    return steps

async def ChooseStepState(function,
                          userid: int, chatid: int, lang: str,
                          steps: list = [],
                          transmitted_data=None, state: Union[FSMContext, None] = None):
    """ Конвейерная Система Состояний
        Устанавливает ожидание нескольких ответов, запуская состояния по очереди.
        
        steps = [
            {"type": str, "name": str, "data": dict, 
                'message': {'text': str, 'reply_markup': markup}}
        ]
        type - тип опроса пользователя (chooses)
          или 'update_data' c функцией для обновления данных (получает и возвращает transmitted_data) + возвращает ответ для сохранения
          В данных можно указать async: True для асинхронной функции
          Параметр name тоже обязателен.

        name - имя ключа в возвращаемом инвентаре (при повторении, будет создан список с записями)
        data - данные для функции создания опроса
        message - данные для отправляемо сообщения перед опросом
        translate_message (bool, optional) - если наш текст это чистый ключ из данных, то можно переводить на ходу
            translate_args - словарь с аргументами для перевода
        image (str, optional) - если нам надо отправить картинку, то добавляем сюда путь к ней

        ТОЛЬКО ДЛЯ Inline
          delete_markup  (bool, optional) - удаляет клавиатуру после завершения

        delete_user_message (boll, optional) - удалить сообщение пользователя на следующем этапе
        delete_message (boll, optional) - удалить сообщения бота на следующем этапе

        transmitted_data
          edit_message (bool, optional) - если нужно не отсылать сообщения, а обновлять, то можно добавить этот ключ.
          delete_steps (bool, optional) - можно добавить для удаления данных отработанных шагов

        В function передаёт 
        >>> answer: dict, transmitted_data: dict
    """
    if not state: state = await get_state(userid, chatid)
    if not transmitted_data: transmitted_data = {}

    steps = prepare_steps(steps, userid,  chatid, lang, state)

    transmitted_data = dict(add_if_not(transmitted_data, 
                            userid, chatid, lang, state))

    transmitted_data['steps'] = steps
    transmitted_data['return_function'] = function
    transmitted_data['return_data'] = {}
    transmitted_data['process'] = 0
    await next_step(0, transmitted_data, True)


async def exit_chose(transmitted_data: dict, state: FSMContext):
    await state.clear()

    return_function = transmitted_data['return_function']
    return_data = transmitted_data['return_data']
    del transmitted_data['return_function']
    del transmitted_data['return_data']
    del transmitted_data['process']

    if 'temp' in transmitted_data:
        del transmitted_data['temp']

    await return_function(return_data, transmitted_data)

# Должен быть ниже всех других обработчиков, 
# для возможности их использования
async def next_step(answer, 
                    transmitted_data: dict, start: bool=False, state: Union[FSMContext, None] = None):
    """Обработчик КСС*

    Args:
        answer (_type_): Ответ переданный из функции ожидания
        transmitted_data (dict): Переданная дата
        start (bool, optional): Является ли функция стартом КСС Defaults to False.

        Для фото, добавить в message ключ image с путём до фото

        Для edit_message требуется добавление message_data в transmitted_data.temp
        (Использовать только для inline состояний, не подойдёт для MessageSteps)
    """

    if not isinstance(transmitted_data, dict): raise ValueError('transmitted_data must be dict')
    if not isinstance(start, bool): raise ValueError('start must be bool')

    userid = transmitted_data['userid']
    chatid = transmitted_data['chatid']
    lang = transmitted_data['lang']

    if not state: state = await get_state(userid, chatid)

    steps = transmitted_data.get('steps', [])
    temp = {}

    # Обновление внутренних данных
    if not start:
        name = steps[transmitted_data.get('process', 0)]['name']
        if name:
            if name in transmitted_data.get('return_data', {}):
                if isinstance(transmitted_data['return_data'][name], list):
                    transmitted_data['return_data'][name].append(answer)
                else:
                    transmitted_data['return_data'][name] = [transmitted_data['return_data'][name], answer]
            else: transmitted_data['return_data'][name] = answer
            transmitted_data['process'] = transmitted_data.get('process', 0) + 1
        else: print('Имя не указано, бесконечный запрос данных')

    if transmitted_data.get('process', 0) - 1 >= 0:
        last_step = steps[transmitted_data.get('process', 0) - 1]

        if steps[transmitted_data.get('process', 0) - 1]['type'] == 'inline':
            if 'delete_markup' in last_step and last_step['delete_markup']:
                await bot.edit_message_reply_markup(None, chatid, last_step.get('messageid'), reply_markup=InlineKeyboardMarkup(inline_keyboard=[]))

        if 'delete_message' in last_step and last_step['delete_message']:
            await bot.delete_message(chatid, last_step.get('bmessageid', 0))

        if 'delete_user_message' in last_step and last_step['delete_user_message']:
            await bot.delete_message(chatid, last_step.get('umessageid', 0))

    if transmitted_data.get('process', 0) < len(steps): #Получение данных по очереди
        ret_data = steps[transmitted_data.get('process', 0)]
        add_data = {}
        if 'data' in ret_data: add_data = ret_data['data']

        if ret_data['type'] == 'update_data':
            # Обработчик данных между запросами
            # Теперь может быть последним!

            if inspect.iscoroutinefunction(ret_data['function']):
                transmitted_data, answer = await ret_data['function'](transmitted_data, **add_data)
            else:
                transmitted_data, answer = ret_data['function'](transmitted_data, **add_data)
            steps = transmitted_data.get('steps', [])
            if ret_data['name']:
                transmitted_data['return_data'][ret_data['name']] = answer
            transmitted_data['process'] = transmitted_data.get('process', 0) + 1
            if transmitted_data.get('process', 0) < len(steps):
                ret_data = steps[transmitted_data.get('process', 0)]
            else: # Заверщение
                return await exit_chose(transmitted_data, state)

        # Очистка данных
        if 'delete_steps' in transmitted_data and transmitted_data['delete_steps'] and transmitted_data.get('process', 0) != 0:
            # Для экономия места мы можем удалять данные отработанных шагов
            transmitted_data['steps'][transmitted_data.get('process', 0)-1] = {}

        if 'temp' in transmitted_data: 
            temp = transmitted_data['temp'].copy()
            del transmitted_data['temp']

        # Следующая функция по счёту
        func_answer, func_type = await ret_data['function'](next_step, 
                    transmitted_data=transmitted_data, **ret_data['data']
        )
        # Отправка если состояние было добавлено и не была завершена автоматически
        if func_type == 'cancel':
            # Если функция возвращает не свой тип, а "cancel" - её надо принудительно завершить
            await state.clear()

        if func_answer:
            # Отправка сообщения / фото из image, если None - ничего
            if ret_data.get('message'):
                edit_message, last_message = False, None
                trans_d = {}

                if 'edit_message' in transmitted_data:
                    edit_message = transmitted_data['edit_message']

                if 'message_data' in temp:
                    last_message = temp['message_data']

                if 'translate_message' in ret_data:
                    if ret_data['translate_message']:
                        if 'translate_args' in ret_data:
                            trans_d = ret_data['translate_args']

                        if 'caption' in ret_data['message']:
                            ret_data['message']['caption'] = t(ret_data['message']['caption'], lang, **trans_d)
                        elif 'text' in ret_data['message']:
                            ret_data['message']['text'] = t(ret_data['message']['text'], lang, **trans_d)

                if edit_message and transmitted_data.get('process', 0) != 0 and last_message:
                    if 'image' in steps[0] or 'caption' in ret_data['message']:
                        await bot.edit_message_caption(None, 
                            chat_id=chatid, message_id=last_message.message_id,
                            parse_mode='Markdown', **ret_data['message'])
                    else:
                        await bot.edit_message_text(
                            chat_id=chatid, message_id=last_message.message_id, parse_mode='Markdown', **ret_data['message'])
                    bmessage = last_message.message_id
                else:
                    if 'image' in ret_data:
                        photo = await async_open(ret_data['image'], True)

                        bmessage = await bot.send_photo(chatid, photo=photo, parse_mode='Markdown', **ret_data['message'])
                    else:
                        if 'text' in ret_data['message']:
                            try:
                                bmessage = await bot.send_message(chatid, parse_mode='Markdown', **ret_data['message'])
                            except:
                                bmessage = await bot.send_message(chatid, **ret_data['message'])
                            ret_data['bmessageid'] = bmessage.message_id

        # Обновление данных состояния
        if not start and func_answer:
            await state.update_data(transmitted_data=transmitted_data)

    else: #Все данные получены
        return await exit_chose(transmitted_data, state)
