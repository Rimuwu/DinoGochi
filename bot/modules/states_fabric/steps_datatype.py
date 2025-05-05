from optparse import Option
from typing import Optional, Type, Union, Callable
from aiogram.types import ReplyKeyboardMarkup, InlineKeyboardMarkup
from matplotlib.pyplot import step

from bot.modules.functransport import func_to_str
from bot.modules.localization import t

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
        for key in self.data_keys:
            if key in self.data:
                setattr(self, key, self.data[key])

    def to_dict(self):
        ret_data = self.__dict__.copy()

        for i in self.data_keys:
            ret_data['data'][i] = getattr(self, i)
            del ret_data[i]

        # del ret_data['data_keys']
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
            data['markup'] = self.markup.__dict__

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
        for key in self.data_keys:
            if key in self.data:
                setattr(self, key, self.data[key])

    def to_dict(self):
        ret_data = self.__dict__.copy()

        for i in self.data_keys:
            ret_data['data'][i] = getattr(self, i)
            del ret_data[i]

        # del ret_data['data_keys']
        if isinstance(self.message, StepMessage):
            ret_data['message'] = self.message.to_dict()

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
                 max_int: int = 1,
                 min_int: int = 10
                 ) -> None:
        super().__init__(name, message, data)
        self.max_int: int = max_int
        self.min_int: int = min_int

class StringStepData(BaseDataType):
    type: str = 'string'
    data_keys: list[str] = ['min_len', 'max_len']

    def __init__(self, name: Optional[str], 
                 message: StepMessage, 
                 data: Optional[dict] = None,
                 min_len: int = 1,
                 max_len: int = 10
                 ) -> None:
        super().__init__(name, message, data)
        self.min_len: int = min_len
        self.max_len: int = max_len

class TimeStepData(BaseDataType):
    type: str = 'time'
    data_keys: list[str] = ['min_int', 'max_int']

    def __init__(self, name: Optional[str], 
                 message: StepMessage, 
                 data: Optional[dict] = None,
                 min_int: int = 1,
                 max_int: int = 10
                 ) -> None:
        super().__init__(name, message, data)
        self.min_int: int = min_int
        self.max_int: int = max_int

class ConfirmStepData(BaseDataType):
    type: str = 'confirm'
    data_keys: list[str] = ['cancel']

    def __init__(self, name: Optional[str], 
                 message: StepMessage, 
                 data: Optional[dict] = None,
                 cancel: bool = False
                 ) -> None:
        super().__init__(name, message, data)
        self.cancel: bool = cancel

class OptionStepData(BaseDataType):
    type: str = 'option'
    data_keys: list[str] = ['options']

    def __init__(self, name: Optional[str], message: StepMessage, data: Optional[dict] = None, options: Optional[dict] = None):
        super().__init__(name, message, data)
        self.options: dict = options or {}

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
        super().__init__(name, message, data)
        self.custom_code: str = custom_code
        self.delete_markup: bool = delete_markup
        self.delete_user_message: bool = delete_user_message
        self.delete_message: bool = delete_message

class CustomStepData(BaseDataType):
    type: str = 'custom'
    data_keys: list[str] = ['custom_handler']

    def __init__(self, name: Optional[str], 
                 message: StepMessage, 
                 data: Optional[dict] = None, 
                 custom_handler: Optional[Callable] = None):
        super().__init__(name, message, data)

        if isinstance(custom_handler, str):
            self.custom_handler = custom_handler
        elif callable(custom_handler):
            self.custom_handler = func_to_str(custom_handler)

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
        super().__init__(name, message, data)
        self.options: dict = options or {}
        self.horizontal: int = horizontal
        self.vertical: int = vertical
        self.autoanswer: bool = autoanswer
        self.one_element: bool = one_element
        self.settings: dict = settings or {}
        self.update_page_function: Optional[Callable] = update_page_function

class ImageStepData(BaseDataType):
    type: str = 'image'
    data_keys: list[str] = ['need_image']

    def __init__(self, name: Optional[str], 
                 message: StepMessage, 
                 data: Optional[dict] = None, 
                 need_image: bool = True):
        super().__init__(name, message, data)
        self.need_image: bool = need_image

class FriendStepData(BaseDataType):
    type: str = 'friend'
    data_keys: list[str] = ['one_element']

    def __init__(self, name: Optional[str], 
                 message: StepMessage, 
                 data: Optional[dict] = None, 
                 one_element: bool = False):
        super().__init__(name, message, data)
        self.one_element: bool = one_element

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
        super().__init__(name, message, data)
        self.type_filter = type_filter
        self.item_filter = item_filter
        self.exclude_ids = exclude_ids
        self.start_page = start_page
        self.changing_filters = changing_filters
        self.inventory = inventory
        self.delete_search = delete_search
        self.settings = settings or {}
        self.inline_func = inline_func
        self.inline_code = inline_code

steps_data_registry = {
    'dino': DinoStepData,
    'int': IntStepData,
    'string': StringStepData,
    'time': TimeStepData,
    'confirm': ConfirmStepData,
    'option': OptionStepData,
    'inline': InlineStepData,
    'custom': CustomStepData,
    'pages': PagesStepData,
    'image': ImageStepData,
    'friend': FriendStepData,
    'inv': InventoryStepData,
    'update': BaseUpdateType,
}

def get_step_data(type: str, 
                  name: Optional[str], 
                  message: StepMessage, 
                  data: Optional[dict] = None) -> Type[BaseDataType]:

    step_class = steps_data_registry.get(type, BaseDataType)
    if step_class:
        return step_class(name, message, data)
    else:
        raise ValueError(f"Unknown step type: {type}")