
from asyncio import sleep
from bot.const import GAME_SETTINGS as gs
from bot.exec import bot
from bot.modules.data_format import chunk_pages, seconds_to_str, str_to_seconds
from bot.modules.decorators import HDCallback, HDMessage
from bot.modules.localization import get_data, get_lang, t
from bot.modules.logs import log
from bot.modules.markup import markups_menu as m
from bot.modules.states_tools import GeneralStates
from telebot.types import CallbackQuery, Message, InputMedia


async def cancel(message, text:str = "❌"):
    lang = await get_lang(message.from_user.id)
    if text:
        await bot.send_message(message.chat.id, text, 
            reply_markup= await m(message.from_user.id, 'last_menu', lang))
    await bot.delete_state(message.from_user.id, message.chat.id)
    await bot.reset_data(message.from_user.id,  message.chat.id)

@bot.message_handler(pass_bot=True, text='buttons_name.cancel', state='*', private=True)
@HDMessage
async def cancel_m(message: Message):
    """Состояние отмены
    """
    await cancel(message)

@bot.message_handler(pass_bot=True, commands=['cancel'], state='*', private=True)
@HDMessage
async def cancel_c(message: Message):
    """Команда отмены
    """
    await cancel(message)


@bot.message_handler(pass_bot=True, commands=['state'])
@HDMessage
async def get_state(message: Message):
    """Состояние
    """
    state = await bot.get_state(message.from_user.id, message.chat.id)
    if state is None:
        await bot.send_message(message.chat.id, 'None')
    else:
        await bot.send_message(message.chat.id, f'{state}')
    try:
        async with bot.retrieve_data(message.from_user.id, 
                                 message.chat.id) as data: log(data)
    except Exception as e:
        await bot.send_message(message.chat.id, str(e))

@bot.message_handler(pass_bot=True, state=GeneralStates.ChooseDino, is_authorized=True)
@HDMessage
async def ChoseDino(message: Message):
    """Общая функция для выбора динозавра
    """
    userid = message.from_user.id
    lang = await get_lang(message.from_user.id)

    async with bot.retrieve_data(userid, message.chat.id) as data:
        ret_data = data['dino_names']
        func = data['function']
        transmitted_data = data['transmitted_data']

    if message.text in ret_data.keys():
        await bot.delete_state(userid, message.chat.id)
        await bot.reset_data(message.from_user.id, message.chat.id)
        if 'steps' in transmitted_data and 'process' in transmitted_data:
            transmitted_data['steps'][transmitted_data['process']]['umessageid'] = message.id
        else: transmitted_data['umessageid'] = message.id

        await func(ret_data[message.text], transmitted_data=transmitted_data)
    else:
        await bot.send_message(message.chat.id, 
                t('states.ChooseDino.error_not_dino', lang))

@bot.message_handler(pass_bot=True, state=GeneralStates.ChooseInt, is_authorized=True)
@HDMessage
async def ChooseInt(message: Message):
    """Общая функция для ввода числа
    """
    userid = message.from_user.id
    lang = await get_lang(message.from_user.id)
    number = 0

    async with bot.retrieve_data(userid, message.chat.id) as data:
        min_int: int = data['min_int']
        max_int: int = data['max_int']
        func = data['function']
        transmitted_data = data['transmitted_data']

    for iter_word in str(message.text).split():
        if iter_word.isdigit():
            number = int(iter_word)

    if not number and number != 0:
        await bot.send_message(message.chat.id, 
                t('states.ChooseInt.error_not_int', lang))
    elif max_int != 0 and number > max_int:
        await bot.send_message(message.chat.id, 
                t('states.ChooseInt.error_max_int', lang,
                number = number, max = max_int))
    elif number < min_int:
        await bot.send_message(message.chat.id, 
                t('states.ChooseInt.error_min_int', lang,
                number = number, min = min_int))
    else:
        await bot.delete_state(userid, message.chat.id)
        await bot.reset_data(message.from_user.id, message.chat.id)

        if 'steps' in transmitted_data and 'process' in transmitted_data:
            transmitted_data['steps'][transmitted_data['process']]['umessageid'] = message.id
        else: transmitted_data['umessageid'] = message.id

        await func(number, transmitted_data=transmitted_data)

@bot.message_handler(pass_bot=True, state=GeneralStates.ChooseString, is_authorized=True)
@HDMessage
async def ChooseString(message: Message):
    """Общая функция для ввода сообщения
    """
    userid = message.from_user.id
    lang = await get_lang(message.from_user.id)

    async with bot.retrieve_data(userid, message.chat.id) as data:
        max_len: int = data['max_len']
        min_len: int = data['min_len']
        func = data['function']
        transmitted_data = data['transmitted_data']

    content = str(message.text)
    content_len = len(content)

    if content_len > max_len and max_len != 0:
        await bot.send_message(message.chat.id, 
                t('states.ChooseString.error_max_len', lang,
                number = content_len, max = max_len))
    elif content_len < min_len:
        await bot.send_message(message.chat.id, 
                t('states.ChooseString.error_min_len', lang,
                number = content_len, min = min_len))
    else:
        await bot.delete_state(userid, message.chat.id)
        await bot.reset_data(message.from_user.id,  message.chat.id)
        if 'steps' in transmitted_data and 'process' in transmitted_data:
            transmitted_data['steps'][transmitted_data['process']]['umessageid'] = message.id
        else: transmitted_data['umessageid'] = message.id

        await func(content, transmitted_data=transmitted_data)

@bot.message_handler(pass_bot=True, state=GeneralStates.ChooseConfirm, is_authorized=True)
@HDMessage
async def ChooseConfirm(message: Message):
    """Общая функция для подтверждения
    """
    userid = message.from_user.id
    lang = await get_lang(message.from_user.id)
    content = str(message.text)

    async with bot.retrieve_data(userid, message.chat.id) as data:
        func = data['function']
        transmitted_data = data['transmitted_data']
        cancel_status = transmitted_data['cancel']

    buttons = get_data('buttons_name', lang)
    buttons_data = {
        buttons['enable']: True,
        buttons['confirm']: True,
        buttons['disable']: False,
        buttons['yes']: True,
        buttons['no']: False
    }

    if content in buttons_data:
        if not(buttons_data[content]) and cancel_status:
            await cancel(message)
        else:
            await bot.delete_state(userid, message.chat.id)
            await bot.reset_data(message.from_user.id,  message.chat.id)
            if 'steps' in transmitted_data and 'process' in transmitted_data:
                transmitted_data['steps'][transmitted_data['process']]['umessageid'] = message.id
            else: transmitted_data['umessageid'] = message.id

            await func(buttons_data[content], transmitted_data=transmitted_data)

    else:
        await bot.send_message(message.chat.id, 
                t('states.ChooseConfirm.error_not_confirm', lang))

@bot.message_handler(pass_bot=True, state=GeneralStates.ChooseOption, is_authorized=True)
@HDMessage
async def ChooseOption(message: Message):
    """Общая функция для выбора из предложенных вариантов
    """
    userid = message.from_user.id
    lang = await get_lang(message.from_user.id)

    async with bot.retrieve_data(userid, message.chat.id) as data:
        options: dict = data['options']
        func = data['function']
        transmitted_data = data['transmitted_data']

    if message.text in options.keys():
        if 'steps' in transmitted_data and 'process' in transmitted_data:
            transmitted_data['steps'][transmitted_data['process']]['umessageid'] = message.id
        else: transmitted_data['umessageid'] = message.id

        await bot.delete_state(userid, message.chat.id)
        await bot.reset_data(message.from_user.id,  message.chat.id)
        await func(options[message.text], transmitted_data=transmitted_data)
    else:
        await bot.send_message(message.chat.id, 
                t('states.ChooseOption.error_not_option', lang))

@bot.message_handler(pass_bot=True, state=GeneralStates.ChooseCustom, is_authorized=True)
@HDMessage
async def ChooseCustom(message: Message):
    """Кастомный обработчик, принимает данные и отправляет в обработчик
    """
    userid = message.from_user.id

    async with bot.retrieve_data(userid, message.chat.id) as data:
        custom_handler = data['custom_handler']
        func = data['function']
        transmitted_data = data['transmitted_data']

    result, answer = await custom_handler(message, transmitted_data) # Обязан возвращать bool, Any
    
    if result:
        if 'steps' in transmitted_data and 'process' in transmitted_data:
            transmitted_data['steps'][transmitted_data['process']]['umessageid'] = message.id
        else: transmitted_data['umessageid'] = message.id

        await bot.delete_state(userid, message.chat.id)
        await bot.reset_data(message.from_user.id,  message.chat.id)
        await func(answer, transmitted_data=transmitted_data)
    
@bot.message_handler(pass_bot=True, state=GeneralStates.ChoosePagesState, is_authorized=True)
@HDMessage
async def ChooseOptionPages(message: Message):
    """Кастомный обработчик, принимает данные и отправляет в обработчик
    """
    userid = message.from_user.id
    chatid = message.chat.id
    lang = await get_lang(message.from_user.id)

    async with bot.retrieve_data(userid, message.chat.id) as data:
        func = data['function']
        update_page = data['update_page']

        options: dict = data['options']
        transmitted_data: dict = data['transmitted_data']

        pages: list = data['pages']
        page: int = data['page']
        one_element: bool = data['one_element']
        
        settings: dict = data['settings']

    if message.text in options.keys():
        if one_element:
            await bot.delete_state(userid, message.chat.id)
            await bot.reset_data(message.from_user.id,  message.chat.id)

        transmitted_data['options'] = options
        transmitted_data['key'] = message.text

        if 'steps' in transmitted_data and 'process' in transmitted_data:
            transmitted_data['steps'][transmitted_data['process']]['umessageid'] = message.id
        else: transmitted_data['umessageid'] = message.id

        res = await func(
            options[message.text], transmitted_data=transmitted_data)

        if not one_element and res and type(res) == dict and 'status' in res:
            # Удаляем состояние
            if res['status'] == 'reset':
                await bot.delete_state(userid, message.chat.id)
                await bot.reset_data(message.from_user.id,  message.chat.id)

            # Обновить все данные
            elif res['status'] == 'update' and 'options' in res:
                pages = chunk_pages(res['options'], settings['horizontal'], settings['vertical'])

                if 'page' in res: page = res['page']
                if page >= len(pages) - 1: page = 0

                async with bot.retrieve_data(userid, message.chat.id) as data:
                    data['options'] = res['options']
                    data['pages'] = pages
                    data['page'] = page

                await update_page(pages, page, chatid, lang)

            # Добавить или удалить элемент
            elif res['status'] == 'edit' and 'elements' in res:
                
                for key, value in res['elements'].items():
                    if key == 'add':
                        for iter_key, iter_value in value.items():
                            options[iter_key] = iter_value
                    elif key == 'delete':
                        for i in value: del options[i]

                pages = chunk_pages(options, settings['horizontal'], settings['vertical'])

                if page >= len(pages) - 1: page = 0

                async with bot.retrieve_data(userid, message.chat.id) as data:
                    data['options'] = options
                    data['pages'] = pages
                    data['page'] = page

                await update_page(pages, page, chatid, lang)

    elif message.text == gs['back_button'] and len(pages) > 1:
        if page == 0: page = len(pages) - 1
        else: page -= 1

        async with bot.retrieve_data(userid, chatid) as data: data['page'] = page
        await update_page(pages, page, chatid, lang)

    elif message.text == gs['forward_button'] and len(pages) > 1:
        if page >= len(pages) - 1: page = 0
        else: page += 1

        async with bot.retrieve_data(userid, chatid) as data: data['page'] = page
        await update_page(pages, page, chatid, lang)
    else:
        await bot.send_message(message.chat.id, 
                t('states.ChooseOption.error_not_option', lang))

@bot.callback_query_handler(pass_bot=True, state=GeneralStates.ChooseInline, is_authorized=True, 
                            func=lambda call: call.data.startswith('chooseinline'))
@HDCallback
async def ChooseInline(callback: CallbackQuery):
    code = callback.data.split()
    chatid = callback.message.chat.id
    userid = callback.from_user.id

    async with bot.retrieve_data(userid, chatid) as data:
        if not data:
            log(f'ChooseInline data corrupted', lvl=2, prefix='ChooseInline')
            return

        func = data.get('function')
        transmitted_data = data.get('transmitted_data')
        custom_code = data.get('custom_code')

        if not func or not transmitted_data or custom_code is None:
            log(f'ChooseInline data corrupted', lvl=2, prefix='ChooseInline')
            return

    code.pop(0)
    if code[0] == str(custom_code):
        code.pop(0)
        if len(code) == 1: code = code[0]

        transmitted_data['temp'] = {}
        transmitted_data['temp']['message_data'] = callback.message

        if 'steps' in transmitted_data and 'process' in transmitted_data:
            try:
                transmitted_data['steps'][transmitted_data['process']]['bmessageid'] = callback.message.id
            except Exception as e:
                log(f'ChooseInline error {e}', lvl=2, prefix='ChooseInline')
        else: transmitted_data['bmessageid'] = callback.message.id

        try:
            await func(code, transmitted_data=transmitted_data)
        except Exception as e:
            log(f'ChooseInline error {e}', lvl=3, prefix='ChooseInline')

@bot.message_handler(pass_bot=True, state=GeneralStates.ChooseTime, is_authorized=True)
@HDMessage
async def ChooseTime(message: Message):
    """Общая функция для ввода времени
    """
    userid = message.from_user.id
    lang = await get_lang(message.from_user.id)
    number = 0

    async with bot.retrieve_data(userid, message.chat.id) as data:
        min_int: int = data['min_int']
        max_int: int = data['max_int']
        func = data['function']
        transmitted_data = data['transmitted_data']

    number = str_to_seconds(str(message.text))

    if not number and min_int != 0:
        await bot.send_message(message.chat.id, 
                t('states.ChooseTime.zero_seconds', lang))
    elif max_int != 0 and number > max_int:
        await bot.send_message(message.chat.id, 
                t('states.ChooseTime.error_max_int', lang,
                number = seconds_to_str(number, lang), 
                max = seconds_to_str(max_int, lang)))
    elif number < min_int:
        await bot.send_message(message.chat.id, 
                t('states.ChooseTime.error_min_int', lang,
                number = seconds_to_str(number, lang), 
                min = seconds_to_str(min_int, lang)))
    else:
        await bot.delete_state(userid, message.chat.id)
        await bot.reset_data(message.from_user.id,  message.chat.id)
        if 'steps' in transmitted_data and 'process' in transmitted_data:
            transmitted_data['steps'][transmitted_data['process']]['umessageid'] = message.id
        else: transmitted_data['umessageid'] = message.id

        await func(number, transmitted_data=transmitted_data)

@bot.message_handler(content_types=['photo'], pass_bot=True, is_authorized=True, state=GeneralStates.ChooseImage)
@HDMessage
async def ChooseImage(message: Message):
    """Общая функция для получения изображения
    """
    userid = message.from_user.id

    async with bot.retrieve_data(userid, message.chat.id) as data:
        func = data['function']
        transmitted_data = data['transmitted_data']

    await bot.delete_state(userid, message.chat.id)
    await bot.reset_data(message.from_user.id,  message.chat.id)
    fileID = message.photo[-1].file_id
    transmitted_data['file'] = message.photo[-1]
    await func(fileID, transmitted_data=transmitted_data)

@bot.message_handler(pass_bot=True, is_authorized=True, state=GeneralStates.ChooseImage)
@HDMessage
async def ChooseImage_0(message: Message):
    """Общая функция для получения изображения
    """
    userid = message.from_user.id

    if message.text == '0':
        async with bot.retrieve_data(userid, message.chat.id) as data:
            func = data['function']
            transmitted_data = data['transmitted_data']
            need_image = data['need_image']

        if need_image:
            await bot.delete_state(userid, message.chat.id)
            await bot.reset_data(message.from_user.id,  message.chat.id)
            await func('no_image', transmitted_data=transmitted_data)



