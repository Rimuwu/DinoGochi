
from typing import Optional, Union
from aiogram.types import ReplyKeyboardMarkup, InlineKeyboardMarkup

from bot.modules.localization import t


class StepMessage():

    def __init__(self, text: str,
                 reply_markup: Union[ReplyKeyboardMarkup, dict, InlineKeyboardMarkup, None] = None,
                 translate_message: bool = False, 
                 text_data: Optional[dict] = None
                 ):
        self.translate_message: bool = translate_message
        self.text = text
        self.text_data: dict = text_data or {}

        if isinstance(reply_markup, dict):
            self.reply_markup = ReplyKeyboardMarkup(**reply_markup)
        else:
            self.reply_markup = reply_markup

    def to_dict(self): 
        data = self.__dict__.copy()

        if isinstance(self.reply_markup, ReplyKeyboardMarkup):
            data['reply_markup'] = self.reply_markup.__dict__

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
                 message: StepMessage, 
                 data: Optional[dict] = None
                 ) -> None:
        if name: self.name: str = name
        self.data: dict = data or {}
        self.message: StepMessage = message

    def to_dict(self):
        ret_data = self.__dict__.copy()

        for i in self.data_keys:
            ret_data['data'][i] = getattr(self, i)
            del ret_data[i]

        # del ret_data['data_keys']
        ret_data['message'] = self.message.to_dict()

        return ret_data

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