
from typing import Callable, Dict, Optional, Type
from aiogram.fsm.state import StatesGroup, State
from aiogram.types import InlineKeyboardMarkup
from bot.exec import bot
from bot.modules.data_format import (chunk_pages, list_to_inline,
                                     list_to_keyboard)
from bot.modules.functransport import func_to_str, str_to_func
from bot.modules.get_state import get_state
from bot.modules.images import async_open
from bot.modules.inventory_tools import start_inv
from bot.modules.localization import get_data, t
from bot.modules.markup import down_menu, get_answer_keyboard
from bot.modules.markup import markups_menu as m
from bot.modules.overwriting.DataCalsses import DBconstructor
from bot.modules.user.friends import get_friend_data
from bot.modules.user.user import User, get_frineds, user_info
from bot.modules.managment.events import check_event
import inspect
from bot.dbmanager import mongo_client

sellers = DBconstructor(mongo_client.market.sellers)

class GeneralStates(StatesGroup):
    zero = State() # Состояние по умолчанию
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

class BaseStateHandler():
    """
    Абстрактный базовый класс для обработчиков состояний выбора.
    """
    state_name = 'zero'
    indenf: str = 'zero'

    def setState(self):
        """
        Получение состояния из группы состояний и установка его в качестве типового состояния.
        """
        return getattr(GeneralStates, 
                       self.state_name, None)

    def __init__(self, function: Callable | str, 
                 userid: int, chatid: int, lang: str, 
                 transmitted_data: Optional[dict] = None):
        if isinstance(function, str):
            self.function = function
        elif callable(function):
            self.function = func_to_str(function)
        else:
            raise TypeError("Функция должна быть строкой или вызываемым объектом.")

        self.userid: int = userid
        self.chatid: int = chatid
        self.lang: str = lang
        self.transmitted_data: dict = transmitted_data or {}

        self.state_type = self.setState()

    async def call_function(self, *args, **kwargs):
        func = str_to_func(self.function)
        if inspect.iscoroutinefunction(func):
            return await func(*args, **kwargs, 
                              transmitted_data=self.transmitted_data)
        else:
            return func(*args, **kwargs, 
                              transmitted_data=self.transmitted_data)

    async def setup(self) -> tuple[bool, str]:
        """
        Настройка состояния. Должна быть переопределена в дочерних классах.
        """
        raise NotImplementedError("Метод setup должен быть переопределен в дочернем классе.")

    async def start(self) -> tuple[bool, str]:
        """
        Запуск состояния. 
        Делаем стандартные действия и вызывает setup()
        """
        user_state = await get_state(self.userid, self.chatid)
        await user_state.clear()
        return await self.setup()

    async def set_data(self) -> None:
        state = await get_state(self.userid, self.chatid)

        data = self.get_data()
        await state.set_data(data)

    def get_data(self) -> dict:
        data = self.__dict__.copy()
        del data['state_type']

        return data

    async def set_state(self) -> None:
        user_state = await get_state(self.userid, self.chatid)
        await user_state.set_state(self.state_type)

class ChooseDinoHandler(BaseStateHandler):
    state_name = 'ChooseDino'
    indenf = 'dino'

    def __init__(self, function, userid, chatid, lang,
                 add_egg=True, all_dinos=True,
                 transmitted_data=None, send_error=True):
        """ Устанавливает состояние ожидания динозавра
            all_dinos - Если False то не будет совместных динозавров 
            send_error - Если True то будет уведомлять о том, что нет динозавров / яиц

            В function передаёт 
            >>> element: Dino | Egg, transmitted_data: dict
            
            Return:
                Возвращает 2 если был создано состояние, 1 если завершилось автоматически (1 вариант выбора), 0 - невозможно завершить
            """
        super().__init__(function, userid, chatid, lang, transmitted_data)
        self.add_egg: bool = add_egg
        self.all_dinos: bool = all_dinos
        self.send_error: bool = send_error
        self.dino_names: dict = {}

    async def setup(self):
        user = await User().create(self.userid)
        elements = await user.get_dinos(self.all_dinos)

        if self.add_egg: elements += await user.get_eggs

        ret_data = get_answer_keyboard(elements, self.lang)
        if ret_data['case'] == 0:
            if self.send_error:
                await bot.send_message(self.chatid,
                    t('css.no_dino', self.lang),
                        reply_markup = await m(
                            self.userid, 'last_menu', self.lang))
            return False, 'cancel'

        elif ret_data['case'] == 1:
            element = ret_data['element']
            await self.call_function(element)
            return False, self.indenf

        elif ret_data['case'] == 2:
            self.dino_names = ret_data['data_names']
            await self.set_state()
            await self.set_data()

            await bot.send_message(self.chatid, t('css.dino', self.lang), reply_markup=ret_data['keyboard'])
            return True, 'dino'

        else:
            return False, 'error'

class ChooseIntHandler(BaseStateHandler):
    state_name =  'ChooseInt'
    indenf = 'int'

    def __init__(self, function, userid, chatid, lang, 
                 min_int=1, max_int=10, autoanswer=True, transmitted_data=None):
        """
            Устанавливает состояние ожидания числа

            В function передаёт 
            >>> number: int, transmitted_data: dict
            
            Если max_int == 0, значит нет ограничения.

            >>> return: Возвращает True если был создано состояние, False если завершилось автоматически (минимальный и максимальный вариант совпадают)
        """

        super().__init__(function, userid, chatid, lang, transmitted_data)
        self.min_int = min_int
        self.max_int = max_int
        self.autoanswer = autoanswer

    async def setup(self) -> tuple[bool, str]:

        if self.min_int != self.max_int or not self.autoanswer:
           await self.set_state()
           await self.set_data()
           return True, self.indenf

        else:
            await self.call_function(self.min_int)
            return False, self.indenf

class ChooseStringHandler(BaseStateHandler):
    state_name =  'ChooseString'
    indenf = 'string'

    def __init__(self, function, userid, chatid, lang, 
                 min_len=1, max_len=10, 
                 transmitted_data=None):
        """ Устанавливает состояние ожидания сообщения

            В function передаёт 
            >>> string: str, transmitted_data: dict
            
            Return:
            Возвращает True если был создано состояние, не может завершится автоматически
        """
        super().__init__(function, userid, chatid, lang, transmitted_data)
        self.min_len = min_len
        self.max_len = max_len

    async def setup(self):
        await self.set_state()
        await self.set_data()
        return True, self.indenf

class ChooseTimeHandler(BaseStateHandler):
    state_name = 'ChooseTime'
    indenf = 'time'

    def __init__(self, function, userid, chatid, lang,
                 min_int=1, max_int=10, transmitted_data=None):
        """ Устанавливает состояние ожидания сообщения в формате времени

            В function передаёт 
            >>> string: str, transmitted_data: dict
            
            Return:
            Возвращает True если был создано состояние, не может завершится автоматически
        """
        super().__init__(function, userid, chatid, lang, transmitted_data)
        self.min_int = min_int
        self.max_int = max_int

    async def setup(self):
        await self.set_state()
        await self.set_data()
        return True, self.indenf

class ChooseConfirmHandler(BaseStateHandler):
    state_name = 'ChooseConfirm'
    indenf = 'confirm'

    def __init__(self, function, userid, chatid, lang, 
                 cancel=False, transmitted_data=None):
        """ Устанавливает состояние ожидания подтверждения действия

            В function передаёт 
            >>> answer: bool, transmitted_data: dict

            cancel - если True, то при отказе вызывает возврат в меню

            Return:
            Возвращает True если был создано состояние, не может завершится автоматически
        """
        super().__init__(function, userid, chatid, lang, transmitted_data)
        self.cancel = cancel

    async def setup(self):
        await self.set_state()
        await self.set_data()
        return True, self.indenf

class ChooseOptionHandler(BaseStateHandler):
    state_name = 'ChooseOption'
    indenf = 'option'

    def __init__(self, function, userid, chatid, lang, 
                 options: Optional[dict] = None, transmitted_data=None):
        """ Устанавливает состояние ожидания выбора опции

            В function передаёт 
            >>> answer: ???, transmitted_data: dict

            options - {"кнопка": данные}

            Return:
            Возвращает True если был создано состояние, False если завершилось автоматически (1 вариант выбора)
        """
        super().__init__(function, userid, chatid, lang, transmitted_data)
        if options is None: 
            self.options = {}
        else: self.options = options

    async def setup(self):
        if len(self.options) > 1:
            await self.set_state()
            await self.set_data()
            return True, self.indenf

        else:
            element = None
            if len(self.options.keys()) > 0:
                element = self.options[list(self.options.keys())[0]]
            await self.call_function(element)
            return False, self.indenf

class ChooseInlineHandler(BaseStateHandler):
    state_name = 'ChooseInline'
    indenf = 'inline'

    def __init__(self, function, userid, chatid, lang, 
                 custom_code, transmitted_data=None):
        """ Устанавливает состояние ожидания нажатия кнопки
            Все ключи callback должны начинаться с 'chooseinline'
            custom_code - код сессии запроса кнопок (индекс 1)

            В function передаёт 
            >>> answer: list, transmitted_data: dict
        """
        super().__init__(function, userid, chatid, lang, transmitted_data)
        self.custom_code: str = custom_code

    async def setup(self):
        await self.set_state()
        await self.set_data()
        return True, self.indenf

class ChooseCustomHandler(BaseStateHandler):
    state_name = 'ChooseCustom'
    indenf = 'custom'

    def __init__(self, function, custom_handler, userid, chatid, lang, transmitted_data=None):
        """
            Устанавливает состояние ожидания чего-либо, все проверки идут через custom_handler.

            custom_handler -> bool, Any !
            В custom_handler передаётся (Message, transmitted_data)

            В function передаёт:
            >>> answer: ???, transmitted_data: dict

            Return:
                result - второе возвращаемое из custom_handler
        """
        super().__init__(function, userid, chatid, lang, transmitted_data)
        self.custom_handler = custom_handler

    async def setup(self):
        await self.set_state()
        await self.set_data()
        return True, self.indenf


async def update_page(pages: list, page: int, chat_id: int, lang: str):
    """
        Стандартная функция обновления страницы, которая будет передаваться в состояние выбора страниц.
    """
    keyboard = list_to_keyboard(pages[page])
    keyboard = down_menu(keyboard, len(pages) > 1, lang)

    await bot.send_message(chat_id, t('optionplus.update_page', lang), reply_markup=keyboard)

class ChoosePagesStateHandler(BaseStateHandler):
    state_name = 'ChoosePagesState'
    indenf = 'pages'

    def __init__(self, function, userid, chatid, lang,
                    options=None, horizontal=2, vertical=3,
                    transmitted_data=None, autoanswer=True, one_element=True,
                    update_page_function=update_page):
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
        super().__init__(function, userid, chatid, lang, transmitted_data)

        self.options: dict = options or {}
        self.autoanswer: bool = autoanswer
        self.one_element: bool = one_element
        self.update_page_function: Callable = update_page_function
        self.pages: list = []
        self.page: int = 0
        self.settings: dict = {
            'horizontal': horizontal,
            'vertical': vertical
        }

    async def setup(self):
        # Чанкует страницы и добавляем пустые элементы для сохранения структуры
        self.pages = chunk_pages(self.options, 
                                 self.settings['horizontal'], self.settings['vertical'])

        if len(self.options) > 1 or not self.autoanswer:
            await self.set_state()
            await self.set_data()

            await self.update_page_function(self.pages, 0, self.chatid, self.lang)
            return True, self.pages
        else:
            if len(self.options) == 0:
                element = None
            else:
                element = self.options[list(self.options.keys())[0]]
            await self.call_function(element)
            return False, self.pages


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

class ChooseFriendHandler(ChoosePagesStateHandler):
    state_name = 'ChooseFriend'
    indenf = 'friend'

    async def __init__(self, function, userid, chatid, lang,
                 one_element: bool = True,
                 transmitted_data=None):
        """
            Устанавливает состояние ожидания выбора друга

            В function передаёт 
            >>> friend: dict, transmitted_data: dict

            Return:
                Возвращает True если был создано состояние, False если завершилось автоматически (1 вариант выбора)
        """
        friends = await get_frineds(self.userid)
        if len(friends) > 1:
            await self.set_state()
            await self.set_data()

        else:
            friend = None
            if len(friends) > 0:
                friend = friends[list(friends.keys())[0]]

        super().__init__(function, userid, chatid, lang, one_element, transmitted_data)




class ChooseImageHandler(BaseStateHandler):
    state_name = 'ChooseImage'
    indenf = 'image'

    def __init__(self, function, userid, chatid, lang,
                    need_image=True, transmitted_data=None):
        """
            Устанавливает состояние ожидания ввода изображения

            need_image - если True, разрешает ответ 'no_image' вместо file_id

            В function передаёт:
            >>> image_url: str, transmitted_data: dict

            Return:
                True, 'image'
        """
        super().__init__(function, userid, chatid, lang, transmitted_data)
        self.need_image = need_image

    async def setup(self):
        await self.set_state()
        await self.set_data()
        return True, self.indenf

# Пример реестра классов-состояний
state_handler_registry: Dict[str, Type[BaseStateHandler]] = {
    'dino': ChooseDinoHandler,
    'int': ChooseIntHandler,
    'time': ChooseTimeHandler,
    'str': ChooseStringHandler,
    'bool': ChooseConfirmHandler,
    'option': ChooseOptionHandler,
    'inline': ChooseInlineHandler,
    'custom': ChooseCustomHandler,
    'pages': ChoosePagesStateHandler,
    # 'inv': start_inv,
    'friend': start_friend_menu,
    'image': ChooseImageHandler
}

# Пример функции для запуска состояния по типу
async def run_state_handler(state_type: str, *args, **kwargs):
    handler_cls = state_handler_registry.get(state_type)
    if not handler_cls:
        raise ValueError(f"State handler for type '{state_type}' not found.")
    handler = handler_cls(*args, **kwargs)
    return await handler.setup()
