

from bot.const import GAME_SETTINGS as gs
from bot.exec import main_router, bot
from bot.modules.data_format import chunk_pages, seconds_to_str, str_to_seconds
from bot.modules.decorators import HDCallback, HDMessage
from bot.modules.get_state import get_state
from bot.modules.localization import get_data, get_lang, t
from bot.modules.logs import log
from bot.modules.markup import markups_menu as m
from bot.modules.states_fabric.state_handlers import ChooseConfirmHandler, ChooseCustomHandler, ChooseDinoHandler, ChooseImageHandler, ChooseInlineHandler, ChooseIntHandler, ChooseOptionHandler, ChoosePagesStateHandler, ChooseStringHandler, ChooseTimeHandler
from bot.modules.states_fabric.state_handlers import GeneralStates
from aiogram.types import CallbackQuery, Message

from bot.filters.translated_text import Text

from bot.filters.private import IsPrivateChat
from bot.filters.authorized import IsAuthorizedUser
from aiogram import F
from aiogram.filters import Command, StateFilter

async def cancel(message, text:str = "❌"):
    lang = await get_lang(message.from_user.id)
    if text:
        await bot.send_message(message.chat.id, text, 
            reply_markup= await m(message.from_user.id, 'last_menu', lang))
    
    state = await get_state(message.from_user.id, message.chat.id)
    if state: await state.clear()

@HDMessage
@main_router.message(Text('buttons_name.cancel'), IsPrivateChat())
async def cancel_m(message: Message):
    """Состояние отмены
    """
    await cancel(message)

@HDMessage
@main_router.message(Command(commands=['cancel']), IsPrivateChat())
async def cancel_c(message: Message):
    """Команда отмены
    """
    await cancel(message)

@HDMessage
@main_router.message(IsPrivateChat(), Command(commands=['state']))
async def get_state_cm(message: Message):
    """Состояние
    """

    state = await get_state(message.from_user.id, message.chat.id)
    if state is None:
        await bot.send_message(message.chat.id, 'None')
    else:
        await bot.send_message(message.chat.id, f'{state}')
    try:
        data = await state.get_data()
        log(f'{data}', prefix='get_state')
    except Exception as e:
        await bot.send_message(message.chat.id, str(e))

@HDMessage
@main_router.message(StateFilter(GeneralStates.ChooseDino), IsAuthorizedUser())
async def ChoseDino(message: Message):
    """Общая функция для выбора динозавра
    """
    userid = message.from_user.id
    lang = await get_lang(message.from_user.id)

    state = await get_state(userid, message.chat.id)
    if data := await state.get_data():
        ret_data = data['dino_names']
        transmitted_data = data['transmitted_data']

    if message.text in ret_data.keys():
        await state.clear()

        if 'steps' in transmitted_data and 'process' in transmitted_data:
            transmitted_data['steps'][transmitted_data['process']]['umessageid'] = message.message_id
        else: transmitted_data['umessageid'] = message.message_id

        await ChooseDinoHandler(**data).call_function(ret_data[message.text])
    else:
        await bot.send_message(message.chat.id, 
                t('states.ChooseDino.error_not_dino', lang))

@HDMessage
@main_router.message(StateFilter(GeneralStates.ChooseInt), IsAuthorizedUser())
async def ChooseInt(message: Message):
    """Общая функция для ввода числа
    """
    lang = await get_lang(message.from_user.id)
    number = 0

    state = await get_state(message.from_user.id, message.chat.id)
    if data := await state.get_data():
        min_int: int = data['min_int']
        max_int: int = data['max_int']
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
        await state.clear()

        if 'steps' in transmitted_data and 'process' in transmitted_data:
            transmitted_data['steps'][transmitted_data['process']]['umessageid'] = message.message_id
        else: transmitted_data['umessageid'] = message.message_id

        await ChooseIntHandler(**data).call_function(number)

@HDMessage
@main_router.message(StateFilter(GeneralStates.ChooseString), IsAuthorizedUser())
async def ChooseString(message: Message):
    """Общая функция для ввода сообщения
    """
    lang = await get_lang(message.from_user.id)

    state = await get_state(message.from_user.id, message.chat.id)
    if data := await state.get_data():
        max_len: int = data['max_len']
        min_len: int = data['min_len']
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
        await state.clear()

        if 'steps' in transmitted_data and 'process' in transmitted_data:
            transmitted_data['steps'][transmitted_data['process']]['umessageid'] = message.message_id
        else: transmitted_data['umessageid'] = message.message_id

        await ChooseStringHandler(**data).call_function(content)

@HDMessage
@main_router.message(StateFilter(GeneralStates.ChooseConfirm), IsAuthorizedUser())
async def ChooseConfirm(message: Message):
    """Общая функция для подтверждения
    """
    lang = await get_lang(message.from_user.id)
    content = str(message.text)

    state = await get_state(message.from_user.id, message.chat.id)
    if data := await state.get_data():
        transmitted_data = data['transmitted_data']
        cancel_status = data['cancel']

    buttons = get_data('buttons_name', lang)
    buttons_data = {
        buttons['enable']: True,
        buttons['confirm']: True,
        buttons['disable']: False,
        buttons['yes']: True,
        buttons['no']: False,
        'true': True,
        'false': False,
    }

    if content in buttons_data:
        if not(buttons_data[content]) and cancel_status:
            await cancel(message)
        else:
            await state.clear()

            if 'steps' in transmitted_data and 'process' in transmitted_data:
                transmitted_data['steps'][transmitted_data['process']]['umessageid'] = message.message_id
            else: transmitted_data['umessageid'] = message.message_id

            await ChooseConfirmHandler(**data).call_function(buttons_data[content])

    else:
        await bot.send_message(message.chat.id, 
                t('states.ChooseConfirm.error_not_confirm', lang))

@HDMessage
@main_router.message(StateFilter(GeneralStates.ChooseOption), IsAuthorizedUser())
async def ChooseOption(message: Message):
    """Общая функция для выбора из предложенных вариантов
    """
    lang = await get_lang(message.from_user.id)

    state = await get_state(message.from_user.id, message.chat.id)
    if data := await state.get_data():
        options: dict = data['options']
        transmitted_data = data['transmitted_data']

    if message.text in options.keys():
        if 'steps' in transmitted_data and 'process' in transmitted_data:
            transmitted_data['steps'][transmitted_data['process']]['umessageid'] = message.message_id
        else: transmitted_data['umessageid'] = message.message_id

        await state.clear()
        await ChooseOptionHandler(**data).call_function(options[message.text])
    else:
        await bot.send_message(message.chat.id, 
                t('states.ChooseOption.error_not_option', lang))

@HDMessage
@main_router.message(StateFilter(GeneralStates.ChooseCustom), IsAuthorizedUser())
async def ChooseCustom(message: Message):
    """Кастомный обработчик, принимает данные и отправляет в обработчик
    """

    state = await get_state(message.from_user.id, message.chat.id)
    if data := await state.get_data():
        transmitted_data = data['transmitted_data']

    handler = ChooseCustomHandler(**data)

    result, answer = await handler.call_custom_handler(message) # Обязан возвращать bool, Any

    if result:
        if 'steps' in transmitted_data and 'process' in transmitted_data:
            transmitted_data['steps'][transmitted_data['process']]['umessageid'] = message.message_id
        else: transmitted_data['umessageid'] = message.message_id

        await state.clear()
        await ChooseCustomHandler(**data).call_function(answer)

# @HDMessage
@main_router.message(StateFilter(GeneralStates.ChoosePagesState), IsAuthorizedUser())
async def ChooseOptionPages(message: Message):
    """Кастомный обработчик, принимает данные и отправляет в обработчик
    """
    userid = message.from_user.id
    chatid = message.chat.id
    lang = await get_lang(message.from_user.id)

    state = await get_state(message.from_user.id, message.chat.id)
    if data := await state.get_data():
        options: dict = data['options']
        transmitted_data: dict = data['transmitted_data']

        pages: list = data['pages']
        page: int = data['page']
        one_element: bool = data['one_element']

        settings: dict = data['settings']

    handler = ChoosePagesStateHandler(**data)

    if message.text in options.keys():
        if one_element: await state.clear()

        transmitted_data['options'] = options
        transmitted_data['key'] = message.text

        if 'steps' in transmitted_data and 'process' in transmitted_data:
            transmitted_data['steps'][transmitted_data['process']]['umessageid'] = message.message_id
        else: transmitted_data['umessageid'] = message.message_id

        res = await ChoosePagesStateHandler(**data).call_function(options[message.text])

        if not one_element and res and type(res) == dict and 'status' in res:
            # Удаляем состояние
            if res['status'] == 'reset': await state.clear()

            # Обновить все данные
            elif res['status'] == 'update' and 'options' in res:
                pages = chunk_pages(res['options'], settings['horizontal'], settings['vertical'])

                if 'page' in res: page = res['page']
                if page >= len(pages) - 1: page = 0

                await state.update_data(options=res['options'], pages=pages, page=page)
                await handler.call_update_page_function(pages, page, chatid, lang)

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

                await state.update_data(options=options, pages=pages, page=page)
                await handler.call_update_page_function(pages, page, chatid, lang)

    elif message.text == gs['back_button'] and len(pages) > 1:
        if page == 0: page = len(pages) - 1
        else: page -= 1

        if data.get('last_user_message'):
            await bot.delete_message(chatid, data['last_user_message'])

        await state.update_data(page=page)
        mes = await handler.call_update_page_function(pages, page, chatid, lang)
        if isinstance(mes, Message):
            mes_id = mes.message_id

            if data.get('last_updated_message'):
                await bot.delete_message(chatid, data['last_updated_message'])

            await state.update_data(last_updated_message=mes_id, last_user_message=message.message_id)

    elif message.text == gs['forward_button'] and len(pages) > 1:
        if page >= len(pages) - 1: page = 0
        else: page += 1

        if data.get('last_user_message'):
            await bot.delete_message(chatid, data['last_user_message'])

        await state.update_data(page=page)
        mes = await handler.call_update_page_function(pages, page, chatid, lang)
        if isinstance(mes, Message):
            mes_id = mes.message_id
            
            if data.get('last_updated_message'):
                await bot.delete_message(chatid, data['last_updated_message'])

            await state.update_data(last_updated_message=mes_id, last_user_message=message.message_id)
    else:
        await bot.send_message(message.chat.id, 
                t('states.ChooseOption.error_not_option', lang))

@HDCallback
@main_router.callback_query(StateFilter(GeneralStates.ChooseInline), IsAuthorizedUser(), 
                            F.data.startswith('chooseinline'))
async def ChooseInline(callback: CallbackQuery):
    """
    chooseinline <custom_code> <data>
    """
    code = callback.data.split()

    state = await get_state(callback.from_user.id, callback.message.chat.id)
    if data := await state.get_data():
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
                transmitted_data['steps'][transmitted_data['process']]['bmessageid'] = callback.message.message_id
            except Exception as e:
                log(f'ChooseInline error {e}', lvl=2, prefix='ChooseInline')
        else: transmitted_data['bmessageid'] = callback.message.message_id

        try:
            await ChooseInlineHandler(**data).call_function(code)
        except Exception as e:
            log(f'ChooseInline error {e}', lvl=3, prefix='ChooseInline')

@HDMessage
@main_router.message(StateFilter(GeneralStates.ChooseTime), 
                     IsAuthorizedUser())
async def ChooseTime(message: Message):
    """Общая функция для ввода времени
    """
    lang = await get_lang(message.from_user.id)
    number = 0

    state = await get_state(message.from_user.id, message.chat.id)
    if data := await state.get_data():
        min_int: int = data['min_int']
        max_int: int = data['max_int']
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
        await state.clear()

        if 'steps' in transmitted_data and 'process' in transmitted_data:
            transmitted_data['steps'][transmitted_data['process']]['umessageid'] = message.message_id
        else: transmitted_data['umessageid'] = message.message_id

        await ChooseTimeHandler(**data).call_function(number)

@HDMessage
@main_router.message(F.photo, IsAuthorizedUser(), 
                     StateFilter(GeneralStates.ChooseImage))
async def ChooseImage(message: Message):
    """Общая функция для получения изображения
    """
    if not message.from_user or not message.from_user.id:
        return

    if not message.photo:
        lang = await get_lang(message.from_user.id)
        await bot.send_message(message.chat.id, t('css.no_photo', lang))
        return

    userid = message.from_user.id
    state = await get_state(userid, message.chat.id)

    if state and (data := await state.get_data()):
        transmitted_data = data.get('transmitted_data', {})

        await state.clear()

        if message.photo:
            fileID = message.photo[-1].file_id
            if 'temp' not in transmitted_data:
                transmitted_data['temp'] = {}
            transmitted_data['temp']['file'] = message.photo[-1]
        else:
            lang = await get_lang(message.from_user.id)
            await bot.send_message(message.chat.id, t('css.no_photo', lang))
            return

        await ChooseImageHandler(**data).call_function(fileID)

@HDMessage
@main_router.message(IsAuthorizedUser(), StateFilter(GeneralStates.ChooseImage))
async def ChooseImage_0(message: Message):
    """Общая функция для получения изображения
    """

    state = await get_state(message.from_user.id, message.chat.id)
    if message.text == '0':
        if data := await state.get_data():
            need_image = data['need_image']

        if need_image:
            await state.clear()

            await ChooseImageHandler(**data).call_function('no_image')


