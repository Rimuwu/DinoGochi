

import time
from typing import Any, Callable, Dict, Optional, Type, Union, List
from aiogram.fsm.state import StatesGroup, State
from aiogram.types import InlineKeyboardMarkup
from bson import ObjectId
from bot.exec import bot
from bot.modules.data_format import (chunk_pages, list_to_inline,
                                     list_to_keyboard)
from aiogram.types import Message
from bot.modules.functransport import func_to_str, str_to_func
from bot.modules.get_state import get_state
from bot.modules.images import async_open
from bot.modules.inventory.inventory_tools import InventoryStates, generate, inventory_pages, send_item_info, swipe_page
from bot.modules.localization import get_data, t
from bot.modules.logs import log
from bot.modules.markup import down_menu, get_answer_keyboard
from bot.modules.markup import markups_menu as m
from bot.modules.overwriting.DataCalsses import DBconstructor
from bot.modules.states_fabric.steps_datatype import BaseDataType, BaseUpdateType, DataType, InlineStepData, StepMessage, get_step_data
from bot.modules.user.friends import get_friend_data
from bot.modules.user.user import User, get_frineds, get_inventory, user_info, user_profile_markup
from bot.modules.managment.events import check_event
import inspect
from bot.dbmanager import mongo_client
from bson import (
    Binary, Code, Decimal128, Int64, MaxKey, MinKey, Regex, Timestamp
)

sellers = DBconstructor(mongo_client.market.sellers)
states_data = DBconstructor(mongo_client.other.states)
users = DBconstructor(mongo_client.user.users)

MongoValueType = Union[
    str,
    int,
    float,
    bool,
    None,
    Dict[str, Any],
    List[Any],
    ObjectId,
    bytes,
    Binary,
    Code,
    Decimal128,
    Int64,
    MaxKey,
    MinKey,
    Regex,
    Timestamp,
]


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
    group_name = GeneralStates
    state_name = 'zero'
    indenf: str = 'zero'
    deleted_keys: list[str] = ['message']

    def setState(self):
        """
        Получение состояния из группы состояний и установка его в качестве типового состояния.
        """

        return getattr(self.group_name, self.state_name, None)

    def __init__(self, function: Callable | str, 
                 userid: int, chatid: int, lang: str, 
                 transmitted_data: Optional[dict[str, MongoValueType]] = None,
                 message: Optional[StepMessage] = None,
                 messages_list: Optional[List[int]] = None
                 ):
        if isinstance(function, str):
            self.function = function
        elif callable(function):
            self.function = func_to_str(function)
        else:
            raise TypeError("Функция должна быть строкой или вызываемым объектом.")

        self.userid: int = userid
        self.chatid: int = chatid
        self.lang: str = lang
        self.transmitted_data = transmitted_data or {}

        self.state_type = self.setState()
        self.message: Optional[StepMessage] = message
        self.messages_list: list[int] = messages_list or []

    async def pre_data(self, value: Any) -> Any:
        """
        Предварительная обработка данных перед вызовом функции.
        """
        # Здесь можно добавить логику предварительной обработки данных, если необходимо.
        return value

    async def call_function(self, value: Any):
        value = await self.pre_data(value)
        func = str_to_func(self.function)

        transmitted_data = self.transmitted_data.copy()
        transmitted_data.update(
            {
                'userid': self.userid,
                'chatid': self.chatid,
                'lang': self.lang,
                'messages_list': self.messages_list # Список с id всех отправленных в состоянии сообщений
            }
        )

        if inspect.iscoroutinefunction(func):
            return await func(value, 
                              transmitted_data=transmitted_data)
        else:
            return func(value, 
                        transmitted_data=transmitted_data)

    async def setup(self) -> tuple[bool, str]:
        """
        Настройка состояния. Должна быть переопределена в дочерних классах.
        """
        raise NotImplementedError("Метод setup должен быть переопределен в дочернем классе.")

    async def message_sender(self) -> None:
        """
        Отправка сообщения пользователю.
        """

        if isinstance(self.message, StepMessage):
            text = self.message.get_text(self.lang)
            markup = self.message.markup
            parse_mode = self.message.parse_mode
            image = self.message.image

            if image:
                photo = await async_open(image, True)
                res = await bot.send_photo(self.chatid, 
                        photo, caption=text, 
                        parse_mode=parse_mode, reply_markup=markup)
            else:
                res = await bot.send_message(self.chatid, 
                        text, parse_mode=parse_mode, 
                        reply_markup=markup)
            self.messages_list.append(res.message_id)

        return

    async def start(self) -> tuple[bool, str]:
        """
        Запуск состояния. 
        Делаем стандартные действия и вызывает setup()
        """
        user_state = await get_state(self.userid, self.chatid)
        await user_state.clear()
        res = await self.setup()
        await self.message_sender()
        return res

    async def set_data(self) -> None:
        state = await get_state(self.userid, self.chatid)

        data = self.get_data()
        await state.set_data(data)

    def get_data(self) -> dict:
        data = self.__dict__.copy()

        del data['state_type']
        for i in self.deleted_keys: del data[i]

        if 'time_start' not in data:
            data['time_start'] = int(time.time())

        return data

    async def set_state(self) -> None:
        user_state = await get_state(self.userid, self.chatid)
        await user_state.set_state(self.state_type)

class ChooseDinoHandler(BaseStateHandler):
    state_name = 'ChooseDino'
    indenf = 'dino'
    deleted_keys = ['add_egg', 'all_dinos', 'send_error', 'status_filter']

    def __init__(self, function, userid, chatid, lang,
                 add_egg=True, all_dinos=True,
                 transmitted_data: Optional[dict[str, MongoValueType]]=None, send_error=True,
                 message_key: Optional[str] = None,
                 status_filter: Optional[str] = None,
                 **kwargs
                 ):
        """ Устанавливает состояние ожидания динозавра
            all_dinos - Если False то не будет совместных динозавров 
            send_error - Если True то будет уведомлять о том, что нет динозавров / яиц

            В function передаёт 
            >>> element: (Dino | Egg, class_name: str), transmitted_data: dict

            Return:
                Возвращает 2 если был создано состояние, 1 если завершилось автоматически (1 вариант выбора), 0 - невозможно завершить
            """
        super().__init__(function, userid, chatid, lang, transmitted_data)
        self.add_egg: bool = add_egg
        self.all_dinos: bool = all_dinos
        self.send_error: bool = send_error
        self.dino_names: dict = {}
        self.status_filter: Optional[str] = status_filter

        if message_key is None:
            self.message_key = 'css.dino'
        else:
            self.message_key = message_key

    async def setup(self):
        user = await User().create(self.userid)
        elements = await user.get_dinos(self.all_dinos)

        if self.status_filter is not None:
            elements = [dino for dino in elements if await dino.status == self.status_filter]

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
            await self.call_function(ret_data['element']._id)
            return False, self.indenf

        elif ret_data['case'] == 2:
            # self.dino_names = ret_data['data_names']
            for name, dino in ret_data['data_names'].items():
                self.dino_names[name] = dino._id

            await self.set_state()
            await self.set_data()

            await bot.send_message(self.chatid, t(self.message_key, self.lang), reply_markup=ret_data['keyboard'])
            return True, self.indenf

        else:
            return False, 'error'

class ChooseIntHandler(BaseStateHandler):
    state_name =  'ChooseInt'
    indenf = 'int'
    deleted_keys = ['autoanswer']

    def __init__(self, function, userid, chatid, lang, 
                 min_int=1, max_int=10, autoanswer=True, 
                 transmitted_data:Optional[dict[str, MongoValueType]]=None,
                 message: Optional[StepMessage] = None,
                 messages_list: Optional[List[int]] = None,
                 **kwargs):
        """
            Устанавливает состояние ожидания числа

            В function передаёт 
            >>> number: int, transmitted_data: dict
            
            Если max_int == 0, значит нет ограничения.

            >>> return: Возвращает True если был создано состояние, False если завершилось автоматически (минимальный и максимальный вариант совпадают)
        """

        super().__init__(function, userid, chatid, lang, transmitted_data, 
                         message=message, messages_list=messages_list)
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
                 transmitted_data:Optional[dict[str, MongoValueType]]=None,
                 message: Optional[StepMessage] = None,
                 messages_list: Optional[List[int]] = None,
                 **kwargs):
        """ Устанавливает состояние ожидания сообщения

            В function передаёт 
            >>> string: str, transmitted_data: dict
            
            Return:
            Возвращает True если был создано состояние, не может завершится автоматически
        """
        super().__init__(function, userid, chatid, lang, transmitted_data,
                         message=message, messages_list=messages_list)
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
                 min_int=1, max_int=10, 
                 transmitted_data:Optional[dict[str, MongoValueType]]=None, 
                 message: Optional[StepMessage] = None,
                 messages_list: Optional[List[int]] = None,
                 **kwargs):
        """ Устанавливает состояние ожидания сообщения в формате времени

            В function передаёт 
            >>> string: str, transmitted_data: dict
            
            Return:
            Возвращает True если был создано состояние, не может завершится автоматически
        """
        super().__init__(function, userid, chatid, lang, transmitted_data,
                         message=message, messages_list=messages_list)
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
                 cancel=False, transmitted_data:Optional[dict[str, MongoValueType]]=None, 
                 message: Optional[StepMessage] = None,
                 messages_list: Optional[List[int]] = None,
                 **kwargs):
        """ Устанавливает состояние ожидания подтверждения действия

            В function передаёт 
            >>> answer: bool, transmitted_data: dict

            cancel - если True, то при отказе вызывает возврат в меню

            Return:
            Возвращает True если был создано состояние, не может завершится автоматически
        """
        super().__init__(function, userid, chatid, lang, transmitted_data,
                         message=message, messages_list=messages_list)
        self.cancel = cancel

    async def setup(self):
        await self.set_state()
        await self.set_data()
        return True, self.indenf

class ChooseOptionHandler(BaseStateHandler):
    state_name = 'ChooseOption'
    indenf = 'option'

    def __init__(self, function, userid, chatid, lang, 
                 options: Optional[dict] = None, 
                 transmitted_data:Optional[dict[str, MongoValueType]]=None,
                 message: Optional[StepMessage] = None,
                 messages_list: Optional[List[int]] = None,
                 **kwargs):
        """ Устанавливает состояние ожидания выбора опции

            В function передаёт 
            >>> answer: ???, transmitted_data: dict

            options - {"кнопка": данные}

            Return:
            Возвращает True если был создано состояние, False если завершилось автоматически (1 вариант выбора)
        """
        super().__init__(function, userid, chatid, lang, transmitted_data,
                         message=message, messages_list=messages_list)
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

class ChooseInlineInventory(BaseStateHandler):
    state_name = 'ChooseInline'
    indenf = 'inline-inventory'

    def __init__(self, function, userid, chatid, lang, 
                 custom_code: str, 
                 one_element: bool = True,
                 transmitted_data: Optional[dict[str, MongoValueType]] = None,
                 message: Optional[StepMessage] = None,
                 messages_list: Optional[List[int]] = None,
                 **kwargs):
        """ Устанавливает состояние ожидания нажатия кнопки
            Все ключи callback должны начинаться с 'chooseinline'
            custom_code - код сессии запроса кнопок (индекс 1)

            В function передаёт 
            >>> answer: list, transmitted_data: dict
        """
        super().__init__(function, userid, chatid, lang, transmitted_data,
                         message=message, messages_list=messages_list)
        self.custom_code: str = custom_code
        self.one_element: bool = one_element

    async def setup(self):
        inventory, count = await get_inventory(self.userid, return_objectid=True)

        self.items_data = await inventory_pages(inventory, self.lang)

        await self.set_state()
        await self.set_data()
        return True, self.indenf

class ChooseInlineHandler(BaseStateHandler):
    state_name = 'ChooseInline'
    indenf = 'inline'

    def __init__(self, function, userid, chatid, lang, 
                 custom_code: str, 
                 transmitted_data: Optional[dict[str, MongoValueType]] = None,
                 one_element: bool = True,
                 message: Optional[StepMessage] = None,
                 messages_list: Optional[List[int]] = None,
                 **kwargs):
        """ Устанавливает состояние ожидания нажатия кнопки
            Все ключи callback должны начинаться с 'chooseinline'
            custom_code - код сессии запроса кнопок (индекс 1)

            В function передаёт 
            >>> answer: list, transmitted_data: dict
        """
        super().__init__(function, userid, chatid, lang, transmitted_data,
                         message=message, messages_list=messages_list)
        self.custom_code: str = custom_code
        self.one_element: bool = one_element

    async def setup(self):
        await self.set_state()
        await self.set_data()
        return True, self.indenf

class ChooseCustomHandler(BaseStateHandler):
    state_name = 'ChooseCustom'
    indenf = 'custom'

    def __init__(self, function, 
                 custom_handler, userid, 
                 chatid, lang, 
                 transmitted_data:Optional[dict[str, MongoValueType]]=None,
                 message: Optional[StepMessage] = None,
                 messages_list: Optional[List[int]] = None,
                 **kwargs):
        """
            Устанавливает состояние ожидания чего-либо, все проверки идут через custom_handler.

            custom_handler -> bool, Any !
            В custom_handler передаётся (Message, transmitted_data)

            В function передаёт:
            >>> answer: ???, transmitted_data: dict

            Return:
                result - второе возвращаемое из custom_handler
        """
        super().__init__(function, userid, chatid, lang, transmitted_data,
                         message=message, messages_list=messages_list)

        if isinstance(custom_handler, str):
            self.custom_handler = custom_handler
        elif callable(custom_handler):
            self.custom_handler = func_to_str(custom_handler)

    async def call_custom_handler(self, message: Message) -> tuple[bool, Any]:
        func = str_to_func(self.custom_handler)

        transmitted_data = self.transmitted_data.copy()
        transmitted_data.update(
            {
                'userid': self.userid,
                'chatid': self.chatid,
                'lang': self.lang
            }
        )

        if inspect.iscoroutinefunction(func):
            return await func(message, transmitted_data=transmitted_data)
        else:
            return func(message, transmitted_data=transmitted_data)

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

    return await bot.send_message(chat_id, t('optionplus.update_page', lang), reply_markup=keyboard)

class ChoosePagesStateHandler(BaseStateHandler):
    state_name = 'ChoosePagesState'
    indenf = 'pages'
    deleted_keys = ['autoanswer']

    def __init__(self, function, userid, 
                 chatid, lang,
                 options=None, 
                 horizontal=2, vertical=3,
                 transmitted_data:Optional[dict[str, MongoValueType]]=None, 
                 autoanswer=True, one_element=True, 
                 settings: Optional[dict]=None,
                 update_page_function: Optional[Callable]=None,
                 pages: Optional[list] = None,
                 page: int = 0,
                 message: Optional[StepMessage] = None,
                 messages_list: Optional[List[int]] = None,
                 **kwargs):
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
        super().__init__(function, userid, chatid, lang, transmitted_data,
                         message=message, messages_list=messages_list)

        self.options: dict = options or {}
        self.autoanswer: bool = autoanswer
        self.one_element: bool = one_element

        if update_page_function is None:
            self.update_page_function = func_to_str(update_page)
        elif isinstance(update_page_function, str):
            self.update_page_function = update_page_function
        elif callable(update_page_function):
            self.update_page_function = func_to_str(update_page_function)

        self.pages: list = pages or []
        self.page: int = page
        self.settings: dict = {
            'horizontal': horizontal,
            'vertical': vertical
        }

        if settings:
            self.settings.update(settings)

    async def call_update_page_function(self, pages: 
        list, page: int, chatid: int, lang: str):
        func = str_to_func(self.update_page_function)

        if inspect.iscoroutinefunction(func):
            return await func(pages, page, chatid, lang)
        else:
            return func(pages, page, chatid, lang)

    async def setup(self):
        # Чанкует страницы и добавляем пустые элементы для сохранения структуры
        self.pages = chunk_pages(self.options, 
                                 self.settings['horizontal'], self.settings['vertical'])

        if len(self.options) > 1 or not self.autoanswer:
            await self.set_state()
            await self.set_data()

            await self.call_update_page_function(self.pages, 
                                self.page, self.chatid, self.lang)
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
    profile_mrk = await user_profile_markup(friend_id,
                                            lang, 'main', 0)
    buttons = {}

    for key, text_b in get_data('friend_list.buttons', lang).items():
        buttons[text_b] = f'{key} {friend_id}'

    if not await check_event("new_year"):
        del buttons[get_data(f'friend_list.buttons.new_year', lang)]

    market = await sellers.find_one({'owner_id': friend_id}, comment='friend_handler_market')
    if not market:
        del buttons[get_data(f'friend_list.buttons.open_market', lang)]

    markup = list_to_inline([buttons], 2)
    msg = t('friend_list.friend_menu', lang, name=friend['name'])

    if avatar:
        await bot.send_photo(chatid, avatar, caption=text, parse_mode='Markdown', reply_markup=profile_mrk)
    else:
        await bot.send_message(chatid, text, parse_mode='Markdown', reply_markup=profile_mrk)

    await bot.send_message(chatid, msg, reply_markup=markup)

class ChooseFriendHandler(ChoosePagesStateHandler):
    state_name = 'ChoosePagesState'
    indenf = 'friend'

    def __init__(self, function, userid, chatid, lang,
                    one_element: bool=False,
                    transmitted_data:Optional[dict[str, MongoValueType]] = None,
                    message: Optional[StepMessage] = None,
                    messages_list: Optional[List[int]] = None,
                    **kwargs):
        """
            Устанавливает состояние ожидания выбора друга

            В function передаёт 
            >>> friend: dict, transmitted_data: dict

            Return:
                Возвращает True если был создано состояние
        """
        if function is None: function = friend_handler

        super().__init__(function, userid, chatid, lang, transmitted_data=transmitted_data)
        self.options: dict = {}
        self.autoanswer: bool = False
        self.one_element: bool = one_element
        self.pages: list = []
        self.page: int = 0
        self.settings: dict = {
            'horizontal': 2,
            'vertical': 3
        }

    async def setup(self):
        res = await get_frineds(self.userid)
        friends = res['friends']

        options = {}

        a = 0
        for friend_id in friends:
            friend_res = await get_friend_data(friend_id, self.userid)
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

        self.options = options
        return await super().setup()

class ChooseImageHandler(BaseStateHandler):
    state_name = 'ChooseImage'
    indenf = 'image'

    def __init__(self, function, userid, chatid, lang,
                    need_image=True, 
                    transmitted_data:Optional[dict[str, MongoValueType]]=None,
                    message: Optional[StepMessage] = None,
                    messages_list: Optional[List[int]] = None,
                    **kwargs):
        """
            Устанавливает состояние ожидания ввода изображения

            need_image - если True, разрешает ответ 'no_image' вместо file_id

            В function передаёт:
            >>> image_url: str, transmitted_data: dict

            Return:
                True, 'image'
        """
        super().__init__(function, userid, chatid, lang, transmitted_data,
                         message=message, messages_list=messages_list)
        self.need_image = need_image

    async def setup(self):
        await self.set_state()
        await self.set_data()
        return True, self.indenf

class ChooseInventoryHandler(BaseStateHandler):
    group_name = InventoryStates
    state_name = 'Inventory'
    indenf = 'inv'
    deleted_keys = ['exclude_ids', 'inventory']

    def __init__(self, function, userid, chatid, lang,
                    type_filter: list | None = None, 
                    item_filter: list | None = None, 
                    exclude_ids: list | None = None,
                    start_page: int = 0, 
                    changing_filters: bool = True,
                    inventory: list | None = None, 
                    delete_search: bool = False,
                    transmitted_data: Optional[dict[str, MongoValueType]] = None,
                    settings: dict = {},
                    inline_func = None, inline_code = '',
                    return_objectid: bool = False,
                    message: Optional[StepMessage] = None,
                    messages_list: Optional[List[int]] = None,
                    **kwargs
                ):
        """ Функция запуска инвентаря
            type_filter - фильтр типов предметов
            item_filter - фильтр по id предметам
            start_page - стартовая страница
            exclude_ids - исключаемые id
            changing_filters - разрешено ли изменять фильтры
            one_time_pages - сколько генерировать страниц за раз, все если 0
            delete_search - Убрать поиск
            inventory - Возможность закинуть уже обработанный инвентарь, если пусто - сам сгенерирует инвентарь
            return_objectid - Если True, то возвращает ObjectId предмета, иначе возвращает данные предмета

            >> Создано для steps, при активации перенаправляет данные при нажатии
            на inline_func, а при нажатии на кнопку начинающийся на inventoryinline {inline_code}
            перенаправляет данные, выбранные по кнопке в function

            >> В inline_func так же передаётся inline_code в transmitted_data

            inline_func - Если нужна функция для обработки калбек запросов 
                - Все кнопки должны начинаться с "inventoryinline {inline_code}" 
        """
        if function is None: function = send_item_info
        if type_filter is None: type_filter = []
        if item_filter is None: item_filter = []
        if exclude_ids is None: exclude_ids = []
        if inventory is None: inventory = []

        super().__init__(function, userid, chatid, lang, transmitted_data,
                         message=message, messages_list=messages_list)
        self.pages = []
        self.items_data = {}

        self.filters = type_filter
        self.items = item_filter

        if settings == {}:
            self.settings = {
                'view': [2, 3], 'lang': lang, 
                'row': 1, 'page': start_page,
                'changing_filters': changing_filters,
                'delete_search': delete_search
            }
        else:
            self.settings = settings

        self.main_message = 0
        self.up_message = 0

        if inline_func is not None:
            if isinstance(inline_func, str):
                self.settings['inline_func'] = inline_func
            elif callable(inline_func):
                self.settings['inline_func'] = func_to_str(inline_func)
            elif inline_func is None:
                self.settings['inline_func'] = None
            self.settings['inline_code'] = inline_code

        self.inventory = inventory
        self.exclude_ids = exclude_ids
        self.return_objectid = return_objectid

        if settings:
            self.settings.update(settings)

    async def call_inline_func(self, *args, **kwargs):
        func = str_to_func(self.settings['inline_func'])

        if inspect.iscoroutinefunction(func):
            return await func(*args, **kwargs)
        else:
            return func(*args, **kwargs)

    async def setup(self):
        user_settings = await users.find_one(
            {'userid': self.userid}, 
            {'settings': 1}, comment='start_inv_user_settings')
        if user_settings: 
            self.settings['inv_view'] = user_settings['settings']['inv_view']

        if not self.inventory:
            inventory, count = await get_inventory(self.userid, 
                                                   self.exclude_ids,
                                                   self.return_objectid
                                                   )
        else:
            inventory = self.inventory
            count = len(inventory)

        self.items_data = await inventory_pages(inventory, 
                                           self.lang, self.filters, 
                                           self.items)
        self.pages, self.settings['row'] = await generate(self.items_data, 
                                         *self.settings['inv_view'])
        if not self.pages:
            await bot.send_message(self.chatid, t('inventory.null', self.lang), 
                           reply_markup=await m(self.chatid, 'last_menu', language_code=self.lang))
            return False, 'cancel'

        else:
            await self.set_state()
            await self.set_data()

            log(f'open inventory userid {self.userid} count {count}')
            await swipe_page(self.chatid, self.userid)
            return True, self.indenf

class BaseUpdateHandler():

    def __init__(self, function: Callable | str, 
                 transmitted_data: Optional[dict] = None,
                 ):

        if isinstance(function, str):
            self.function = function
        elif callable(function):
            self.function = func_to_str(function)

        self.transmitted_data: dict = transmitted_data or {}

    async def start(self) -> tuple[dict[str, Any], bool]:
        func = str_to_func(self.function)

        if inspect.iscoroutinefunction(func):
            return await func(self.transmitted_data)
        else:
            return func(self.transmitted_data)

    async def get_data(self) -> dict[str, Any]:
        return self.__dict__

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
    'friend': ChooseFriendHandler,
    'image': ChooseImageHandler,
    'inv': ChooseInventoryHandler,
}

# Пример функции для запуска состояния по типу
async def run_state_handler(state_type: str, *args, **kwargs):
    handler_cls = state_handler_registry.get(state_type)
    if not handler_cls:
        raise ValueError(f"State handler for type '{state_type}' not found.")
    handler = handler_cls(*args, **kwargs)
    return await handler.setup()

class ChooseStepHandler():

    def __init__(self, function: Callable | str, 
                 userid: int, chatid: int, 
                 lang: str, 
                 steps: list[DataType],
                 transmitted_data:Optional[dict[str, MongoValueType]] = None):
        """ Конвейерная Система Состояний (КСС)
            Устанавливает ожидание нескольких ответов, запуская состояния по очереди.

            steps = [
                DinoStepData('step_name', # тут лежит type состояния
                    None,
                    data={
                        'add_egg': True, 'all_dinos': True,
                    }
                ),
                IntStepData('step_name_int',
                    StepMessage('text_int', markup_int), # отсюда получается текст через get_text
                    data={
                        'min_value': 0, 'max_value': 100,
                    }
                ),
            ]
            type - тип опроса пользователя (BaseDataType)
            или BaseUpdateType c функцией для обновления данных 
            (получает и возвращает transmitted_data) + возвращает ответ для сохранения

            Функция автоматически вызывается асинхронно, если она не является корутиной.

            Возвращает:
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
        self.transmitted_data: dict = transmitted_data or {}
        for key, value in self.transmitted_data.items():
            if not isinstance(value, (str, int, float, bool, type(None), dict, list, ObjectId, bytes, Binary, Code, Decimal128, Int64, MaxKey, MinKey, Regex, Timestamp)):
                raise TypeError(f"Value for key '{key}' is not a valid MongoValueType: {type(value)}")

        for i in steps:
            if not isinstance(i, DataType):
                raise TypeError("Шаги должны быть наследниками BaseDataType")

        self.steps = steps

        if isinstance(function, str):
            self.function = function
        elif callable(function):
            self.function = func_to_str(function)
        else:
            raise TypeError("Функция должна быть строкой или вызываемым объектом.")

        self.userid: int = userid
        self.chatid: int = chatid
        self.lang: str = lang

    async def start(self) -> None:
        steps_data = []
        for step in self.steps:
            steps_data.append(
                step.to_dict()
            )

        self.transmitted_data.update(
            {
                'userid': self.userid,
                'chatid': self.chatid,
                'lang': self.lang,
                'return_function': self.function,
                'steps': steps_data,
                'process': 0,
                'return_data': {}
            }
        )

        await next_step(0, self.transmitted_data, start=True)


async def exit_chose(state, transmitted_data: dict):
    await state.clear()

    return_function: str = transmitted_data['return_function']
    return_data = transmitted_data['return_data']
    for i in ['return_function', 'return_data', 'process']:
        del transmitted_data[i]

    call_func = str_to_func(return_function)
    if inspect.iscoroutinefunction(call_func):
        await call_func(return_data, transmitted_data)
    else:
        call_func(return_data, transmitted_data)

async def next_step(answer: Any, 
                    transmitted_data: dict, 
                    start: bool = False):
    """Обработчик КСС*

    Args:
        answer (_type_): Ответ переданный из функции ожидания
        transmitted_data (dict): Переданная дата
        start (bool, optional): Является ли функция стартом КСС Defaults to False.

        Для фото, добавить в message ключ image с путём до фото

        Для edit_message требуется добавление message_data в transmitted_data.temp
        (Использовать только для inline состояний, не подойдёт для MessageSteps)
    """

    userid = transmitted_data['userid']
    chatid = transmitted_data['chatid']
    lang = transmitted_data['lang']
    steps_raw = transmitted_data['steps']
    process = transmitted_data['process']
    return_data = transmitted_data['return_data']

    user_state = await get_state(userid, chatid)
    temp = {}

    # Преобразование в дата классы для удобной работы
    steps: list[Union[Type[BaseDataType], BaseUpdateType]] = []
    for raw_step in steps_raw.copy():
        if raw_step['type'] in state_handler_registry.keys():
            step = get_step_data(**raw_step)
        else:
            new_step: dict = raw_step.copy()
            new_step.pop('type', None)
            step = BaseUpdateType(**new_step)

        steps.append(step)

    current_step: Union[Type[BaseDataType], BaseUpdateType] = steps[process]

    # Обновление внутренних данных
    if not start:

        # Обновляем данные в return_data если есть имя
        if isinstance(current_step, (BaseDataType)):
            name = current_step.name
            if name:
                # Добавление данных в return_data
                if name in return_data:
                    if isinstance(return_data[name], list):
                        return_data[name].append(answer)
                    else:
                        return_data[name] = [
                            return_data[name], answer
                            ]
                else: 
                    return_data[name] = answer
        process += 1

    # Выполнение работы для последнего выполненного шага
    if process - 1 >= 0:
        last_step: Union[Type[BaseDataType], BaseUpdateType] = steps[process - 1]
        raw_dat = steps_raw[process - 1]

        if isinstance(last_step, InlineStepData):
            if last_step.delete_markup:
                messageid = raw_dat.get('messageid', None)
                if messageid:
                    await bot.edit_message_reply_markup(None, chatid, 
                            messageid, 
                            reply_markup=InlineKeyboardMarkup(inline_keyboard=[]))

            if last_step.delete_message:
                messageid = raw_dat.get('bmessageid', None)
                if messageid:
                    await bot.delete_message(chatid, messageid)

            if last_step.delete_user_message:
                messageid = raw_dat.get('umessageid', None)
                if messageid:
                    await bot.delete_message(chatid, messageid)

    # Работа с новым шагом
    if process < len(steps):
        next_step_obj: DataType = steps[process]
        step_data = next_step_obj.to_handler_data()

        if isinstance(next_step_obj, BaseUpdateType):
            # Обновление данных между запросами
            transmitted_data['process'] = process
            transmitted_data['return_data'] = return_data
            handler = BaseUpdateHandler

            self_handler = handler(**step_data, transmitted_data=transmitted_data)
            transmitted_data, answer = await self_handler.start() # Передаём transmitted_data,
            # Получаем transmitted_data и ответ для сохранения

            process = transmitted_data['process']

            new_steps: list[dict] = []
            for raw_step in transmitted_data['steps'].copy():
                if not isinstance(raw_step, dict):
                    new_steps.append(raw_step.to_dict())
                else:
                    new_steps.append(raw_step)

            transmitted_data['steps'] = new_steps

            if process >= len(steps):
                # Если это последний шаг, то удаляем состояние и завершаем работу
                await exit_chose(user_state, transmitted_data)
                return

            await user_state.update_data(transmitted_data=transmitted_data)
            await next_step(answer, transmitted_data)
            return

        if transmitted_data.get('temp', False):
            # Если это inline состояние, то обновляем сообщение
            temp = transmitted_data['temp'].copy()
            del transmitted_data['temp']

        if isinstance(next_step_obj, (BaseDataType)):
            # Запуск следующего состояния
            type_handler = next_step_obj.type
            handler = state_handler_registry[type_handler]

            transmitted_data['process'] = process
            transmitted_data['return_data'] = return_data

            self_handler = handler(**step_data, userid=userid, chatid=chatid, 
                                   lang=lang, function=next_step, transmitted_data=transmitted_data)

            func_answer, func_type = await self_handler.start()

            # Если состояние завершилось автоматически, то удаляем состояние
            if func_type == 'cancel': await user_state.clear()

            if func_answer:
                # Отправка сообщения / фото из image, если None - ничего
                edit_message, last_message = False, None
                bmessage = None
                message_data = next_step_obj.message

                if 'edit_message' in transmitted_data:
                    edit_message = transmitted_data['edit_message']

                if 'message_data' in temp:
                    last_message = temp['message_data']

                if message_data:
                    step_0: (BaseDataType) = steps[0] # type: ignore
                    if edit_message and last_message:
                        if step_0.message and step_0.message.image:
                            markup = None

                            if isinstance(message_data.markup, InlineKeyboardMarkup):
                                markup = message_data.markup

                            await bot.edit_message_caption(
                                chat_id=chatid, message_id=last_message.message_id,
                                parse_mode='Markdown', 
                                caption=message_data.get_text(lang),
                                reply_markup=markup,
                                )
 
                        if step_0.message and not step_0.message.image:

                            markup = None
                            if isinstance(message_data.markup, InlineKeyboardMarkup):
                                markup = message_data.markup

                            await bot.edit_message_text(text=message_data.get_text(lang), 
                                chat_id=chatid, message_id=last_message.message_id,
                                parse_mode='Markdown', 
                                reply_markup=markup,
                                )

                        bmessage = last_message

                    else:
                        if message_data.image:
                            photo = await async_open(message_data.image, True)
                            bmessage = await bot.send_photo(chatid, 
                                photo=photo, parse_mode='Markdown', 
                                caption=message_data.get_text(lang),
                                reply_markup=message_data.markup,
                            )
                        else:
                            try:
                                bmessage = await bot.send_message(chatid, 
                                        parse_mode='Markdown', text=message_data.get_text(lang), reply_markup=message_data.markup)
                            except:
                                bmessage = await bot.send_message(chatid,          
                                        text=message_data.get_text(lang), reply_markup=message_data.markup)

                if bmessage:
                    steps_raw[process]['bmessageid'] = bmessage.message_id

            # Обновление данных состояния
            if not start and func_answer:
                transmitted_data['steps'] = steps_raw
                await user_state.update_data(transmitted_data=transmitted_data)

    else:
        await exit_chose(user_state, transmitted_data)
