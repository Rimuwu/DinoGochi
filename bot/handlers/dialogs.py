
from bot.exec import bot, botworker
from bot.modules.data_format import user_name
from bot.modules.decorators import HDCallback
from bot.modules.dialogs import dialogs
from bot.modules.localization import get_lang
from aiogram.types import CallbackQuery, InlineKeyboardMarkup

from bot.filters.translated_text import StartWith, Text
from bot.filters.states import NothingState
from bot.filters.status import DinoPassStatus
from bot.filters.private import IsPrivateChat
from bot.filters.authorized import IsAuthorizedUser
from bot.filters.kd import KDCheck
from bot.filters.admin import IsAdminUser
from aiogram import F
from aiogram.filters import Command

@bot.callback_query(F.data.startswith('dialog'),   
                            IsAuthorizedUser())
@HDCallback
async def dialog(callback: CallbackQuery):
    dialog_key = callback.data.split()[1]
    dialog_action = callback.data.split()[2]
    lang = await get_lang(callback.from_user.id)
    userid = callback.from_user.id
    chatid = callback.message.chat.id
    message = callback.message

    name = user_name(callback.from_user)

    status, text, markup = await dialogs[dialog_key](userid, name, lang, dialog_action)
    if status:

        if dialog_action == 'start':
            await botworker.send_message(userid, text, reply_markup=markup, parse_mode='Markdown')
            await botworker.edit_message_reply_markup(None, chatid, message.id, 
                                   reply_markup=InlineKeyboardMarkup(inline_keyboard=[]))
        else:
            if len(str(message.text) + text) + 4 >= 2000:
                content = text
            else:  content = str(message.text) + '\n\n' + text

            await botworker.edit_message_text(content, chatid, message.id, reply_markup=markup, parse_mode='Markdown')