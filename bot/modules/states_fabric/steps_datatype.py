
from typing import Optional, Type, Union, Callable
from aiogram.types import ReplyKeyboardMarkup, InlineKeyboardMarkup
from bson import ObjectId

from bot.modules.functransport import func_to_str
from bot.modules.localization import t
from typing import Any, Dict, List, Union

class BaseUpdateType():

    type: str = 'update'
    data_keys: list[str] = []

    def __init__(self, 
                 function: Optional[Callable] = None,
                 data: Optional[dict] = None
                 ) -> None:
        if isinstance(function, str):
            self.function: str = function
        else:
            self.function: str = func_to_str(function)
        self.data: dict = data or {}

        # Приоритет значениям из data
        for key in self.data.keys():
            if key in self.data_keys:
                setattr(self, key, self.data[key])

    def to_dict(self):
        ret_data = self.__dict__.copy()

        for i in self.data_keys:
            ret_data['data'][i] = getattr(self, i)
            del ret_data[i]

        # del ret_data['data_keys']
        ret_data['type'] = self.type
        return ret_data

    def to_handler_data(self):
        ret_data = self.__dict__.copy()

        for i in self.data.keys():
            ret_data[i] = getattr(self, i)

        del ret_data['data']
        return ret_data

class StepMessage():

    def __init__(self, text: str,
                 markup: Union[ReplyKeyboardMarkup, dict, InlineKeyboardMarkup, None] = None,
                 translate_message: bool = False, 
                 text_data: Optional[dict] = None,
                 image: Optional[str] = None,
                 ):
        self.translate_message: bool = translate_message
        self.text = text
        self.text_data: dict = text_data or {}
        self.image: Optional[str] = image

        if isinstance(markup, dict):
            self.markup = ReplyKeyboardMarkup(**markup)
        else:
            self.markup = markup

    def to_dict(self): 
        data = self.__dict__.copy()

        if isinstance(self.markup, ReplyKeyboardMarkup):
            data['markup'] = self.markup.model_dump()

        return data

    def get_text(self, lang: str):

        if self.translate_message:
            return t(self.text, lang, True, **self.text_data)
        else:
            return self.text

class BaseDataType():

    type: str = 'base'
    data_keys: list[str] = []

    def __init__(self, name: Optional[str], 
                 message: Union[StepMessage, dict, None], 
                 data: Optional[dict] = None
                 ) -> None:
        self.name: Optional[str] = name
        self.data: dict = data or {}

        self.message: Optional[StepMessage] = None
        if isinstance(message, dict):
            self.message: Optional[StepMessage] = StepMessage(**message)
        elif isinstance(message, StepMessage):
            self.message: Optional[StepMessage] = message

        # Приоритет значениям из data
        for key in self.data.keys():
            if key in self.data_keys:
                setattr(self, key, self.data[key])

    def to_dict(self):
        ret_data = self.__dict__.copy()

        for i in self.data_keys:
            ret_data['data'][i] = getattr(self, i)
            del ret_data[i]

        if isinstance(self.message, StepMessage):
            ret_data['message'] = self.message.to_dict()

        ret_data['type'] = self.type
        return ret_data
    
    def to_handler_data(self):
        ret_data = self.__dict__.copy()

        for i in self.data.keys():
            ret_data[i] = getattr(self, i)

        del ret_data['data']
        del ret_data['message']
        del ret_data['name']
        return ret_data

class DinoStepData(BaseDataType):

    type: str = 'dino'
    data_keys: list[str] = ['add_egg', 'all_dinos', 'send_error']

    def __init__(self, name: Optional[str], 
                 message: StepMessage, 
                 data: Optional[dict] = None,
                 add_egg: bool = True,
                 all_dinos: bool = True,
                 send_error: bool = True
                 ) -> None:
        super().__init__(name, message, data)
        self.add_egg: bool = add_egg
        self.all_dinos: bool = all_dinos
        self.send_error: bool = send_error

class IntStepData(BaseDataType):

    type: str = 'int'
    data_keys: list[str] = ['max_int', 'min_int']

    def __init__(self, name: Optional[str], 
                 message: StepMessage, 
                 data: Optional[dict] = None,
                 max_int: int = 10,
                 min_int: int = 1,
                 autoanswer: bool = False
                 ) -> None:
        self.max_int: int = max_int
        self.min_int: int = min_int
        self.autoanswer: bool = autoanswer
        super().__init__(name, message, data)

class StringStepData(BaseDataType):
    type: str = 'str'
    data_keys: list[str] = ['min_len', 'max_len']

    def __init__(self, name: Optional[str], 
                 message: StepMessage, 
                 data: Optional[dict] = None,
                 min_len: int = 1,
                 max_len: int = 10
                 ) -> None:
        self.min_len: int = min_len
        self.max_len: int = max_len
        super().__init__(name, message, data)

class TimeStepData(BaseDataType):
    type: str = 'time'
    data_keys: list[str] = ['min_int', 'max_int']

    def __init__(self, name: Optional[str], 
                 message: StepMessage, 
                 data: Optional[dict] = None,
                 min_int: int = 1,
                 max_int: int = 10
                 ) -> None:
        self.min_int: int = min_int
        self.max_int: int = max_int
        super().__init__(name, message, data)

class ConfirmStepData(BaseDataType):
    type: str = 'bool'
    data_keys: list[str] = ['cancel']

    def __init__(self, name: Optional[str], 
                 message: StepMessage, 
                 data: Optional[dict] = None,
                 cancel: bool = False
                 ) -> None:
        self.cancel: bool = cancel
        super().__init__(name, message, data)

class OptionStepData(BaseDataType):
    type: str = 'option'
    data_keys: list[str] = ['options']

    def __init__(self, name: Optional[str], 
                 message: StepMessage, 
                 data: Optional[dict] = None, 
                 options: Optional[dict] = None):
        self.options: dict = options or {}
        super().__init__(name, message, data)

class InlineStepData(BaseDataType):
    type: str = 'inline'
    data_keys: list[str] = ['custom_code']

    def __init__(self, name: Optional[str], 
                 message: StepMessage, 
                 data: Optional[dict] = None, 
                 custom_code: str = '',
                 delete_markup: bool = False,
                 delete_user_message: bool = False,
                 delete_message: bool = False,
                 ):
        self.custom_code: str = custom_code
        self.delete_markup: bool = delete_markup
        self.delete_user_message: bool = delete_user_message
        self.delete_message: bool = delete_message
        super().__init__(name, message, data)

class CustomStepData(BaseDataType):
    type: str = 'custom'
    data_keys: list[str] = ['custom_handler']

    def __init__(self, name: Optional[str], 
                 message: StepMessage, 
                 data: Optional[dict] = None, 
                 custom_handler: Optional[Callable] = None):
        if isinstance(custom_handler, str):
            self.custom_handler = custom_handler
        elif callable(custom_handler):
            self.custom_handler = func_to_str(custom_handler)

        super().__init__(name, message, data)

class PagesStepData(BaseDataType):
    type: str = 'pages'
    data_keys: list[str] = ['options', 'horizontal', 'vertical', 'autoanswer', 'one_element', 'settings', 'update_page_function']

    def __init__(self, name: Optional[str], 
                 message: StepMessage, 
                 data: Optional[dict] = None, 
                 options: Optional[dict] = None,
                 horizontal: int = 2, vertical: int = 3,
                 autoanswer: bool = True, 
                 one_element: bool = True,
                 settings: Optional[dict] = None,
                 update_page_function: Optional[Callable] = None,
                ):
        self.options: dict = options or {}
        self.horizontal: int = horizontal
        self.vertical: int = vertical
        self.autoanswer: bool = autoanswer
        self.one_element: bool = one_element
        self.settings: dict = settings or {}
        if isinstance(update_page_function, str):
            self.update_page_function = update_page_function
        elif callable(update_page_function):
            self.update_page_function = func_to_str(update_page_function)
        if update_page_function is None:
            self.update_page_function = None

        super().__init__(name, message, data)

class ImageStepData(BaseDataType):
    type: str = 'image'
    data_keys: list[str] = ['need_image']

    def __init__(self, name: Optional[str], 
                 message: StepMessage, 
                 data: Optional[dict] = None, 
                 need_image: bool = True):
        self.need_image: bool = need_image
        super().__init__(name, message, data)

class FriendStepData(BaseDataType):
    type: str = 'friend'
    data_keys: list[str] = ['one_element']

    def __init__(self, name: Optional[str], 
                 message: StepMessage, 
                 data: Optional[dict] = None, 
                 one_element: bool = False):
        self.one_element: bool = one_element
        super().__init__(name, message, data)

class InventoryStepData(BaseDataType):
    type: str = 'inv'
    data_keys: list[str] = [
        'type_filter', 'item_filter', 'exclude_ids', 'start_page', 'changing_filters',
        'inventory', 'delete_search', 'settings', 'inline_func', 'inline_code'
    ]

    def __init__(self, name: Optional[str], 
                 message: StepMessage, 
                 data: Optional[dict] = None,
                 type_filter: Optional[list] = None, item_filter: Optional[list] = None,
                 exclude_ids: Optional[list] = None, start_page: int = 0, 
                 changing_filters: bool = True,
                 inventory: Optional[list] = None, delete_search: bool = False, settings: Optional[dict] = None,
                 inline_func=None, inline_code: str = ''):
        self.type_filter = type_filter
        self.item_filter = item_filter
        self.exclude_ids = exclude_ids
        self.start_page = start_page
        self.changing_filters = changing_filters
        self.inventory = inventory
        self.delete_search = delete_search
        self.settings = settings or {}
        if isinstance(inline_func, str):
            self.inline_func = inline_func
        elif callable(inline_func):
            self.inline_func = func_to_str(inline_func)
        if inline_func is None:
            self.inline_func = None
        self.inline_code = inline_code
        super().__init__(name, message, data)

steps_data_registry = {
    'dino': DinoStepData,
    'int': IntStepData,
    'str': StringStepData,
    'time': TimeStepData,
    'bool': ConfirmStepData,
    'option': OptionStepData,
    'inline': InlineStepData,
    'custom': CustomStepData,
    'pages': PagesStepData,
    'image': ImageStepData,
    'friend': FriendStepData,
    'inv': InventoryStepData,
    'update': BaseUpdateType,
}

DataType = Union[
    DinoStepData, IntStepData, StringStepData, TimeStepData, ConfirmStepData,
    OptionStepData, InlineStepData, CustomStepData, PagesStepData,
    ImageStepData, FriendStepData, InventoryStepData, BaseUpdateType
]

def get_step_data(type: str, 
                  name: Optional[str], 
                  message: StepMessage, 
                  data: Optional[dict] = None,
                  **kwargs) -> Type[BaseDataType]:

    step_class = steps_data_registry.get(type, BaseDataType)
    if step_class:
        return step_class(name, message, data)
    else:
        raise ValueError(f"Unknown step type: {type}")