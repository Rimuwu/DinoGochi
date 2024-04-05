
from telebot.types import CallbackQuery, InlineKeyboardMarkup

from bot.exec import bot
from bot.modules.data_format import user_name
from bot.modules.dialogs import dialogs
from bot.modules.localization import  get_lang
from bot.modules.over_functions import send_message



@bot.callback_query_handler(pass_bot=True, 
                            func=lambda call: call.data.startswith('dialog'),   
                            is_authorized=True)
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
            await bot.send_message(userid, text, reply_markup=markup, parse_mode='Markdown')
            await bot.edit_message_reply_markup(chatid, message.id, 
                                   reply_markup=InlineKeyboardMarkup())
        else:
            if len(str(message.text) + text) + 4 >= 2000:
                content = text
            else:  content = str(message.text) + '\n\n' + text

            await bot.edit_message_text(content, chatid, message.id, reply_markup=markup, parse_mode='Markdown')