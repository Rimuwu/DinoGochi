from telebot.types import CallbackQuery
from bot.exec import bot
from bot.modules.decorators import HDCallback
from bot.modules.localization import get_lang


@bot.callback_query_handler(pass_bot=True, func=lambda call: call.data.startswith('transformation') , is_authorized=True)
@HDCallback
async def transformation(callback: CallbackQuery):
    chatid = callback.message.chat.id
    userid = callback.from_user.id
    lang = await get_lang(callback.from_user.id)
    data = callback.data.split()

    alt_code = data[1]
    action = data[2]

    if action == 'send_dino':
        ...