

from bot.const import GAME_SETTINGS as gs
from bot.exec import main_router, bot
from bot.modules.data_format import chunk_pages, seconds_to_str, str_to_seconds
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
    
    state = await get_state(message.from_user.id, message.chat.id)
    reply_to_id = None
    if state:
        state_data = await state.get_data()
        if state_data:
            reply_to_id = state_data.get('transmitted_data', {}).get('reply_to_message_id')
            journey_cancel_msg_id = state_data.get('journey_cancel_msg_id')
            if journey_cancel_msg_id:
                try:
                    await bot.delete_message(message.chat.id, journey_cancel_msg_id)
                except Exception:
                    pass
            edit_message_id = state_data.get('edit_message_id') or state_data.get('main_message') or state_data.get('transmitted_data', {}).get('edit_message_id')
            if edit_message_id:
                try:
                    await bot.delete_message(message.chat.id, edit_message_id)
                except Exception:
                    pass
        state_str = await state.get_state()
        if state_str and 'ChooseMultiInventory' in state_str:
            from bot.modules.get_state import clear_multi_inventory_state
            await clear_multi_inventory_state(message.from_user.id, message.chat.id, state=state)
        else:
            await state.clear()

    if text:
        if message.chat.id == message.from_user.id:
            await bot.send_message(message.chat.id, text, 
                reply_markup= await m(message.from_user.id, 'last_menu', lang))
        else:
            await bot.send_message(message.chat.id, text, reply_to_message_id=reply_to_id or message.message_id)

@main_router.message(Text('buttons_name.cancel'), IsPrivateChat())
async def cancel_m(message: Message):
    """Состояние отмены
    """
    await cancel(message)
    from bot.modules.tutorial import advance_tutorial_if_step
    lang = await get_lang(message.from_user.id)
    await advance_tutorial_if_step(message.from_user.id, message.chat.id, lang, bot, expected_step="profile_inventory")

@main_router.message(Command(commands=['cancel']), IsPrivateChat())
async def cancel_c(message: Message):
    """Команда отмены
    """
    await cancel(message)
    from bot.modules.tutorial import advance_tutorial_if_step
    lang = await get_lang(message.from_user.id)
    await advance_tutorial_if_step(message.from_user.id, message.chat.id, lang, bot, expected_step="profile_inventory")

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

@main_router.message(StateFilter(GeneralStates.ChooseDino), IsAuthorizedUser())
async def ChoseDino(message: Message):
    """Общая функция для выбора динозавра
    """
    userid = message.from_user.id
    lang = await get_lang(message.from_user.id)

    state = await get_state(userid, message.chat.id)
    if data := await state.get_data():
        ret_data = data['dino_names']
        func = data['function']
        transmitted_data = data['transmitted_data']

    if message.text in ret_data.keys():
        await state.clear()

        if 'steps' in transmitted_data and 'process' in transmitted_data:
            transmitted_data['steps'][transmitted_data['process']]['umessageid'] = message.message_id
        else: transmitted_data['umessageid'] = message.message_id

        await ChooseDinoHandler(**data).call_function(ret_data[message.text])
        # await func(ret_data[message.text], transmitted_data=transmitted_data)
    else:
        await bot.send_message(message.chat.id, 
                t('states.ChooseDino.error_not_dino', lang))

@main_router.message(StateFilter(GeneralStates.ChooseInt), IsAuthorizedUser())
async def ChooseInt(message: Message):
    """Общая функция для ввода числа
    """
    lang = await get_lang(message.from_user.id)
    number = 0

    state = await get_state(message.from_user.id, message.chat.id)
    data = await state.get_data()
    if not data:
        await state.clear()
        return

    min_int: int = data.get('min_int', 0)
    max_int: int = data.get('max_int', 0)
    func = data.get('function')
    transmitted_data = data.get('transmitted_data', {})

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
        # await func(number, transmitted_data=transmitted_data)

@main_router.message(StateFilter(GeneralStates.ChooseString), IsAuthorizedUser())
async def ChooseString(message: Message):
    """Общая функция для ввода сообщения
    """
    lang = await get_lang(message.from_user.id)

    state = await get_state(message.from_user.id, message.chat.id)
    data = await state.get_data()
    if not data:
        await state.clear()
        return

    max_len: int = data.get('max_len', 0)
    min_len: int = data.get('min_len', 0)
    func = data.get('function')
    transmitted_data = data.get('transmitted_data', {})

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
        # await func(content, transmitted_data=transmitted_data)

@main_router.message(StateFilter(GeneralStates.ChooseConfirm), IsAuthorizedUser())
async def ChooseConfirm(message: Message):
    """Общая функция для подтверждения
    """
    lang = await get_lang(message.from_user.id)
    content = str(message.text)

    state = await get_state(message.from_user.id, message.chat.id)
    data = await state.get_data()
    if not data:
        await state.clear()
        return

    func = data.get('function')
    transmitted_data = data.get('transmitted_data', {})
    cancel_status = data.get('cancel', False)

    buttons = get_data('buttons_name', lang)
    buttons_data = {
        buttons['enable']: True,
        buttons['confirm']: True,
        buttons['disable']: False,
        buttons['yes']: True,
        buttons['no']: False,
        buttons['cancel']: False,
        'true': True,
        'false': False,
    }

    import re
    def clean_confirm_text(text: str) -> str:
        if not text:
            return ""
        # Strip any leading non-alphanumeric characters (like emojis and spaces)
        cleaned = re.sub(r'^[^a-zA-Zа-яА-Я0-9ёЁ]+', '', text)
        return cleaned.strip().lower()

    clean_buttons_data = {clean_confirm_text(k): v for k, v in buttons_data.items()}
    content_clean = clean_confirm_text(content)

    if content_clean in clean_buttons_data:
        if not(clean_buttons_data[content_clean]) and cancel_status:
            await cancel(message)
        else:
            await state.clear()

            if 'steps' in transmitted_data and 'process' in transmitted_data:
                transmitted_data['steps'][transmitted_data['process']]['umessageid'] = message.message_id
            else: transmitted_data['umessageid'] = message.message_id

            await ChooseConfirmHandler(**data).call_function(clean_buttons_data[content_clean])
            # await func(buttons_data[content], transmitted_data=transmitted_data)

    else:
        await bot.send_message(message.chat.id, 
                t('states.ChooseConfirm.error_not_confirm', lang))

@main_router.message(StateFilter(GeneralStates.ChooseOption), IsAuthorizedUser())
async def ChooseOption(message: Message):
    """Общая функция для выбора из предложенных вариантов
    """
    lang = await get_lang(message.from_user.id)

    state = await get_state(message.from_user.id, message.chat.id)
    data = await state.get_data()
    if not data:
        await state.clear()
        return

    options: dict = data.get('options', {})
    func = data.get('function')
    transmitted_data = data.get('transmitted_data', {})

    matched_key = None
    if message.text in options.keys():
        matched_key = message.text
    else:
        from bot.modules.data_format import parse_custom_emoji_markdown, remove_alt_emoji_from_text, strip_emoji_prefix
        for key in options.keys():
            clean_text, emoji_id, alt_emoji = parse_custom_emoji_markdown(key)
            text_without_alt = remove_alt_emoji_from_text(clean_text, alt_emoji)
            expected_text = f"{alt_emoji} {clean_text}" if alt_emoji else clean_text
            clean_prefix = strip_emoji_prefix(clean_text)
            if message.text.strip() in [key.strip(), clean_text.strip(), expected_text.strip(), text_without_alt.strip(), clean_prefix.strip()]:
                matched_key = key
                break

    if matched_key:
        if 'steps' in transmitted_data and 'process' in transmitted_data:
            transmitted_data['steps'][transmitted_data['process']]['umessageid'] = message.message_id
        else: transmitted_data['umessageid'] = message.message_id

        await state.clear()
        # await func(options[matched_key], transmitted_data=transmitted_data)
        await ChooseOptionHandler(**data).call_function(options[matched_key])
    else:
        await bot.send_message(message.chat.id, 
                t('states.ChooseOption.error_not_option', lang))

@main_router.message(StateFilter(GeneralStates.ChooseCustom), IsAuthorizedUser())
async def ChooseCustom(message: Message):
    """Кастомный обработчик, принимает данные и отправляет в обработчик
    """

    state = await get_state(message.from_user.id, message.chat.id)
    data = await state.get_data()
    if not data:
        await state.clear()
        return

    custom_handler = data.get('custom_handler')
    func = data.get('function')
    transmitted_data = data.get('transmitted_data', {})

    handler = ChooseCustomHandler(**data)

    result, answer = await handler.call_custom_handler(message) # Обязан возвращать bool, Any

    if result:
        if 'steps' in transmitted_data and 'process' in transmitted_data:
            transmitted_data['steps'][transmitted_data['process']]['umessageid'] = message.message_id
        else: transmitted_data['umessageid'] = message.message_id

        await state.clear()
        # await func(answer, transmitted_data=transmitted_data)
        await ChooseCustomHandler(**data).call_function(answer)

@main_router.message(StateFilter(GeneralStates.ChoosePagesState), IsAuthorizedUser())
async def ChooseOptionPages(message: Message):
    """Кастомный обработчик, принимает данные и отправляет в обработчик
    """
    userid = message.from_user.id
    chatid = message.chat.id
    lang = await get_lang(message.from_user.id)

    state = await get_state(message.from_user.id, message.chat.id)
    data = await state.get_data()
    if not data:
        await state.clear()
        return

    func = data.get('function')
    update_page = data.get('update_page_function')

    options: dict = data.get('options', {})
    transmitted_data: dict = data.get('transmitted_data', {})

    pages: list = data.get('pages', [])
    page: int = data.get('page', 0)
    one_element: bool = data.get('one_element', False)

    settings: dict = data.get('settings', {})

    handler = ChoosePagesStateHandler(**data)

    matched_key = None
    if message.text in options.keys():
        matched_key = message.text
    else:
        from bot.modules.data_format import parse_custom_emoji_markdown, remove_alt_emoji_from_text, strip_emoji_prefix
        for key in options.keys():
            clean_text, emoji_id, alt_emoji = parse_custom_emoji_markdown(key)
            text_without_alt = remove_alt_emoji_from_text(clean_text, alt_emoji)
            expected_text = f"{alt_emoji} {clean_text}" if alt_emoji else clean_text
            clean_prefix = strip_emoji_prefix(clean_text)
            if message.text.strip() in [key.strip(), clean_text.strip(), expected_text.strip(), text_without_alt.strip(), clean_prefix.strip()]:
                matched_key = key
                break

    if matched_key:
        if one_element: await state.clear()

        transmitted_data['options'] = options
        transmitted_data['key'] = matched_key

        if 'steps' in transmitted_data and 'process' in transmitted_data:
            transmitted_data['steps'][transmitted_data['process']]['umessageid'] = message.message_id
        else: transmitted_data['umessageid'] = message.message_id

        res = await ChoosePagesStateHandler(**data).call_function(options[matched_key])
        # res = await func(
            # options[matched_key], transmitted_data=transmitted_data)

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
                # await update_page(pages, page, chatid, lang)

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
                # await update_page(pages, page, chatid, lang)

    elif message.text == gs['back_button'] and len(pages) > 1:
        if page == 0: page = len(pages) - 1
        else: page -= 1

        if data.get('last_user_message'):
            await bot.delete_message(chatid, data['last_user_message'])

        await state.update_data(page=page)
        # await update_page(pages, page, chatid, lang)
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
        # await update_page(pages, page, chatid, lang)
        mes = await handler.call_update_page_function(pages, page, chatid, lang)
        if isinstance(mes, Message):
            mes_id = mes.message_id
            
            if data.get('last_updated_message'):
                await bot.delete_message(chatid, data['last_updated_message'])

            await state.update_data(last_updated_message=mes_id, last_user_message=message.message_id)
    else:
        await bot.send_message(message.chat.id, 
                t('states.ChooseOption.error_not_option', lang))

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
            # await func(code, transmitted_data=transmitted_data)
        except Exception as e:
            log(f'ChooseInline error {e}', lvl=3, prefix='ChooseInline')

@main_router.callback_query(StateFilter(GeneralStates.ChooseDinoList), IsAuthorizedUser(),
                            F.data.startswith('dinosel:'))
async def ChooseDinoList_callback(callback: CallbackQuery):
    chatid = callback.message.chat.id
    userid = callback.from_user.id
    lang = await get_lang(userid)

    state = await get_state(userid, chatid)
    state_data = await state.get_data()
    if not state_data:
        return

    action_parts = callback.data.split(':')
    action = action_parts[1]

    if action == 'cancel':
        cancel_cb = state_data.get('cancel_callback')
        await state.clear()
        if cancel_cb:
            if cancel_cb == 'j_active_menu':
                from bot.handlers.actions_live.journey import active_menu_callback
                await active_menu_callback(callback)
            elif cancel_cb == 'arena_menu':
                from bot.handlers.arena import show_arena_menu_callback
                await show_arena_menu_callback(callback)
            else:
                await callback.message.delete()
                await bot.send_message(chatid, "❌", reply_markup=await m(userid, 'last_menu', lang))
        else:
            await callback.message.delete()
            await bot.send_message(chatid, "❌", reply_markup=await m(userid, 'last_menu', lang))
        await callback.answer()
        return

    elif action == 'toggle':
        dino_id_str = action_parts[2]
        max_dinos = state_data.get('max_dinos', 6)
        selected = list(state_data.get('selected_dino_ids', []))

        if max_dinos == 1:
            edit_message = state_data.get('edit_message', False)
            if not edit_message:
                try:
                    await callback.message.delete()
                except Exception:
                    pass
            else:
                if 'transmitted_data' not in state_data or not isinstance(state_data['transmitted_data'], dict):
                    state_data['transmitted_data'] = {}
                state_data['transmitted_data']['edit_message_id'] = callback.message.message_id

            await state.clear()
            from bot.modules.states_fabric.state_handlers import ChooseDinoListHandler
            handler = ChooseDinoListHandler(**state_data)
            await callback.answer()
            await handler.call_function([dino_id_str])
            return

        if dino_id_str in selected:
            selected.remove(dino_id_str)
        else:
            if len(selected) >= max_dinos:
                await callback.answer(t("journey_setup.max_dinos", lang, max_count=max_dinos, default=f"Вы можете выбрать максимум {max_dinos} динозавров!"), show_alert=True)
                return
            selected.append(dino_id_str)

        await state.update_data(selected_dino_ids=selected)

        from bot.models.dinosaur import Dino
        from bson import ObjectId
        free_dino_ids = state_data.get('free_dino_ids', [])
        free_dinos = []
        for d_id in free_dino_ids:
            d = await Dino.find_one(Dino.id == ObjectId(d_id))
            if d:
                free_dinos.append(d)

        from bot.modules.states_fabric.state_handlers import render_dino_list_screen
        await render_dino_list_screen(
            chatid=chatid,
            free_dinos=free_dinos,
            selected_ids=selected,
            lang=lang,
            cancel_callback=state_data.get('cancel_callback'),
            message_key=state_data.get('message_key'),
            max_dinos=max_dinos,
            message=callback.message
        )
        await callback.answer()

    elif action == 'done':
        min_dinos = state_data.get('min_dinos', 1)
        selected = state_data.get('selected_dino_ids', [])

        if len(selected) < min_dinos:
            await callback.answer(t("journey_setup.select_at_least_one_dino", lang, min_count=min_dinos, default=f"❌ Выберите хотя бы {min_dinos} динозавров!"), show_alert=True)
            return

        edit_message = state_data.get('edit_message', False)
        if not edit_message:
            try:
                await callback.message.delete()
            except Exception:
                pass
        else:
            if 'transmitted_data' not in state_data or not isinstance(state_data['transmitted_data'], dict):
                state_data['transmitted_data'] = {}
            state_data['transmitted_data']['edit_message_id'] = callback.message.message_id

        await state.clear()
        from bot.modules.states_fabric.state_handlers import ChooseDinoListHandler
        handler = ChooseDinoListHandler(**state_data)
        await callback.answer()
        await handler.call_function(selected)

@main_router.callback_query(StateFilter(GeneralStates.ChooseMultiInventory, GeneralStates.ChooseMultiInventorySearch), IsAuthorizedUser(), 
                            F.data.startswith('multinv:'))
async def ChooseMultiInventory_callback(callback: CallbackQuery):
    answered = False
    chatid = callback.message.chat.id
    userid = callback.from_user.id
    lang = await get_lang(userid)

    state = await get_state(userid, chatid)
    state_data = await state.get_data()
    if not state_data:
        return

    from bot.modules.states_fabric.state_handlers import ChooseMultiInventoryHandler, chunk_pages

    action_parts = callback.data.split(':')
    action = action_parts[1]

    selected = state_data.get('selected', {})
    page = state_data.get('page', 0)
    detail_key = state_data.get('detail_key', None)
    items_data = state_data.get('items_data', {})
    meta_data = state_data.get('meta_data', {})

    if action == 'noop':
        return
    elif action == 'select':
        idx_str = action_parts[2]
        if idx_str.isdigit():
            idx = int(idx_str)
            virtual_pages = state_data.get('virtual_pages', [])
            review_mode_list = state_data.get('review_mode', False)
            all_names = {}
            for page_data in virtual_pages:
                for name, _, _ in page_data:
                    if review_mode_list and selected.get(name, 0) == 0:
                        continue
                    all_names[name] = True
            all_names_list = list(all_names.keys())
            if 0 <= idx < len(all_names_list):
                detail_key = all_names_list[idx]
            else:
                detail_key = idx_str
        else:
            detail_key = idx_str

        max_diff = state_data.get('max_different_items', None)
        if max_diff is not None:
            current_diff = sum(1 for k, v in selected.items() if v > 0)
            if selected.get(detail_key, 0) == 0 and current_diff >= max_diff:
                await callback.answer(t('multinv.limit_different_items', lang, limit=max_diff), show_alert=True)
                answered = True
                return

        await state.update_data(detail_key=detail_key)
    elif action == 'back':
        await state.update_data(detail_key=None)
    elif action == 'prev' or action == 'next':
        virtual_pages = state_data.get('virtual_pages', [])
        review_mode_list = state_data.get('review_mode', False)
        horizontal = state_data.get('horizontal', 2)
        vertical = state_data.get('vertical', 4)
        all_names = {}
        for page_data in virtual_pages:
            for name, _, _ in page_data:
                if review_mode_list and selected.get(name, 0) == 0:
                    continue
                all_names[name] = True
        pages = chunk_pages(all_names, horizontal, vertical)
        total_pages = len(pages)
        if total_pages > 0:
            if action == 'prev':
                page = (page - 1) % total_pages
            else:
                page = (page + 1) % total_pages
            await state.update_data(page=page)
    elif action == 'change':
        delta = int(action_parts[2])
        if detail_key:
            meta = meta_data.get(detail_key, {})
            max_qty = meta.get('count', 1)
            current_qty = selected.get(detail_key, 0)
            
            limit = state_data.get('limit', None)
            
            if limit is not None:
                step = 1 if delta > 0 else -1
                temp_qty = current_qty
                for _ in range(abs(delta)):
                    next_qty = temp_qty + step
                    if next_qty < 0 or next_qty > max_qty:
                        break
                    temp_selected = selected.copy()
                    temp_selected[detail_key] = next_qty
                    temp_total = sum(temp_selected.values())
                    effective_limit = limit
                    if state_data.get('limit_type') == 'journey_bag':
                        from bot.modules.items.item import get_item_capacity, get_data as get_item_data_
                        bonus = sum(get_item_capacity(items_data[n]) * qty
                                    for n, qty in temp_selected.items() if n in items_data
                                    and get_item_data_(items_data[n].get('item_id', '')).get('type') == 'journey')
                        effective_limit = limit + bonus
                    if temp_total > effective_limit:
                        break
                    temp_qty = next_qty
                new_qty = temp_qty
            else:
                new_qty = max(0, min(max_qty, current_qty + delta))
                
            if new_qty == current_qty:
                if delta > 0:
                    await callback.answer(t('multinv.limit_reached', lang), show_alert=True)
                else:
                    await callback.answer()
                return

            max_diff = state_data.get('max_different_items', None)
            if max_diff is not None:
                current_diff = sum(1 for k, v in selected.items() if v > 0)
                if current_qty == 0 and new_qty > 0 and current_diff >= max_diff:
                    await callback.answer(t('multinv.limit_different_items', lang, limit=max_diff), show_alert=True)
                    answered = True
                    return

            selected[detail_key] = new_qty
            await state.update_data(selected=selected)
    elif action == 'clear':
        await state.update_data(selected={}, detail_key=None)
    elif action == 'cancel':
        reply_to_id = state_data.get('transmitted_data', {}).get('reply_to_message_id')
        await state.clear()
        try:
            await bot.delete_message(chatid, callback.message.message_id)
        except:
            pass
        if chatid == userid:
            from bot.modules.markup import markups_menu as m
            await bot.send_message(chatid, "❌", reply_markup=await m(userid, 'last_menu', lang))
        else:
            await bot.send_message(chatid, "❌", reply_to_message_id=reply_to_id)
        return
    elif action == 'confirm':
        # First check if anything selected
        if not any(v > 0 for v in selected.values()):
            if not state_data.get('empty_allowed', False):
                await callback.answer(t('inventory.no_select', lang), show_alert=True)
                answered = True
                return
        # Enter review mode — show only selected items for final check
        await state.update_data(review_mode=True, page=0)

    elif action == 'exit_review':
        await state.update_data(review_mode=False, page=0)

    elif action == 'final_confirm':
        # Prepare list of items with their selected counts
        chosen_items = []
        raw_inventory = state_data.get('raw_inventory', [])
        filter_interact = state_data.get('filter_interact', True)
        filter_cant_sell = state_data.get('filter_cant_sell', True)
        from bot.modules.items.item import get_data as get_item_data
        filtered_inventory = []
        for item in raw_inventory:
            i_data = item.get('items_data', {})
            item_id = i_data.get('item_id', '')
            item_cfg = get_item_data(item_id) if item_id else {}
            if filter_interact and 'abilities' in i_data and 'interact' in i_data['abilities'] and not i_data['abilities']['interact']:
                continue
            if filter_cant_sell and item_cfg.get('cant_sell'):
                continue
            filtered_inventory.append(item)

        from bot.models.user import User as BeanieUser
        user_obj = await BeanieUser.find_one(BeanieUser.userid == userid)
        user_settings = user_obj.dict() if user_obj else None
        rare_emoji = True
        only_emoji = False
        if user_settings and 'settings' in user_settings:
            rare_emoji = user_settings['settings'].get('rare_emoji', True)
            only_emoji = user_settings['settings'].get('only_emoji', False)

        from bot.modules.inventory_tools import filter_and_sort_inventory
        all_possible = filter_and_sort_inventory(filtered_inventory, lang, [], [], rare_emoji=rare_emoji, only_emoji=only_emoji)
        all_items = {}
        for name, item, _ in all_possible:
            all_items[name] = item

        combined_items = items_data.copy()
        combined_items.update(all_items)

        for name, qty in selected.items():
            if qty > 0 and name in combined_items:
                item = dict(combined_items[name])
                item['count'] = qty
                chosen_items.append(item)

        if not chosen_items:
            # Nothing selected
            if not state_data.get('empty_allowed', False):
                await callback.answer(t('inventory.no_select', lang), show_alert=True)
                answered = True
                return

        # Exit state and call function
        transmitted_data = state_data.get('transmitted_data', {})
        transmitted_data['selected_multinv'] = selected

        await state.clear()
        delete_msg = state_data.get('delete_message', True)
        if not delete_msg:
            transmitted_data['edit_message_id'] = callback.message.message_id
        else:
            try:
                await bot.delete_message(chatid, callback.message.message_id)
            except:
                pass

        # Invoke callback function
        func = state_data.get('function')
        transmitted_data = state_data.get('transmitted_data', {})
        if 'steps' in transmitted_data and 'process' in transmitted_data:
            transmitted_data['steps'][transmitted_data['process']]['bmessageid'] = callback.message.message_id

        # Re-initialize the handler from data dict to call the function
        handler = ChooseMultiInventoryHandler(**state_data)
        if not answered:
            await callback.answer()
        await handler.call_function(chosen_items)
        return

    elif action == 'search':
        # Prompt search text
        await state.set_state(GeneralStates.ChooseMultiInventorySearch)
        from aiogram.utils.keyboard import InlineKeyboardBuilder
        inl_builder = InlineKeyboardBuilder()
        inl_builder.button(text=t('buttons_name.cancel', lang), callback_data="multinv:clear_search_exit")
        
        prompt_msg = await bot.send_message(
            chatid, 
            t('inventory.search', lang), 
            reply_markup=inl_builder.as_markup(),
            reply_to_message_id=callback.message.message_id
        )
        # Keep track of prompt message id to clean up later
        await state.update_data(prompt_msg_id=prompt_msg.message_id)
        return
    elif action == 'clear_search_exit':
        await state.set_state(GeneralStates.ChooseMultiInventory)
        prompt_msg_id = state_data.get('prompt_msg_id')
        if prompt_msg_id:
            try:
                await bot.delete_message(chatid, prompt_msg_id)
            except: pass
        from bot.modules.states_fabric.state_handlers import ChooseMultiInventoryHandler
        handler = ChooseMultiInventoryHandler(**state_data)
        await handler.render()
        return
    elif action == 'clear_search':
        await state.update_data(search_query='')
        from bot.modules.states_fabric.state_handlers import update_multi_inventory
        await update_multi_inventory(state, userid, chatid, lang)
    elif action == 'clear_filters':
        await state.update_data(type_filter=[])
        from bot.modules.states_fabric.state_handlers import update_multi_inventory
        await update_multi_inventory(state, userid, chatid, lang)
    elif action == 'sort':
        sorts = ['name_asc', 'name_desc', 'count_asc', 'count_desc']
        current_sort = state_data.get('inv_sort', 'name_asc')
        try:
            next_idx = (sorts.index(current_sort) + 1) % len(sorts)
        except ValueError:
            next_idx = 0
        await state.update_data(inv_sort=sorts[next_idx])
        from bot.modules.states_fabric.state_handlers import update_multi_inventory
        await update_multi_inventory(state, userid, chatid, lang)
    elif action == 'filters':
        # Show picker: collect unique types from raw_inventory and show as buttons
        raw_inventory = state_data.get('raw_inventory', [])
        from bot.modules.items.item import get_data as get_item_data_
        from bot.modules.inventory_tools import get_group_type
        types_in_inv = set()
        for it in raw_inventory:
            i_data = (
                it.get('items_data', {}) if isinstance(it, dict) and 'items_data' in it
                else (it.get('item', {}) if isinstance(it, dict) and 'item' in it
                else it)
            )
            item_id = i_data.get('item_id', '') if isinstance(i_data, dict) else ''
            if not item_id and isinstance(it, dict) and 'item_id' in it:
                item_id = it['item_id']
            if item_id:
                itype = get_item_data_(item_id).get('type', '')
                if itype:
                    types_in_inv.add(get_group_type(itype))
        await state.update_data(filter_picker=True, available_types=sorted(list(types_in_inv)))
        from bot.modules.states_fabric.state_handlers import update_multi_inventory
        await update_multi_inventory(state, userid, chatid, lang)
    elif action == 'set_filter':
        # Toggle/apply the selected type filter
        filter_type = action_parts[2] if len(action_parts) > 2 else ''
        if filter_type:
            type_filter = state_data.get('type_filter', []) or []
            if filter_type in type_filter:
                type_filter.remove(filter_type)
            else:
                type_filter.append(filter_type)
            await state.update_data(type_filter=type_filter)
        else:
            await state.update_data(type_filter=[])
        from bot.modules.states_fabric.state_handlers import update_multi_inventory
        await update_multi_inventory(state, userid, chatid, lang)
    elif action == 'close_filters':
        await state.update_data(filter_picker=False)
        from bot.modules.states_fabric.state_handlers import update_multi_inventory
        await update_multi_inventory(state, userid, chatid, lang)

    # Refresh render
    state_data = await state.get_data()
    handler = ChooseMultiInventoryHandler(**state_data)
    if not answered:
        await callback.answer()
    await handler.render(edit_message_id=callback.message.message_id)

@main_router.message(StateFilter(GeneralStates.ChooseMultiInventorySearch), IsAuthorizedUser())
async def ChooseMultiInventorySearch_message(message: Message):
    from bot.modules.states_fabric.state_handlers import ChooseMultiInventoryHandler
    userid = message.from_user.id
    chatid = message.chat.id
    lang = await get_lang(userid)
    query = message.text

    state = await get_state(userid, chatid)
    state_data = await state.get_data()
    
    # Clean up prompt message and user's query message
    prompt_msg_id = state_data.get('prompt_msg_id')
    if prompt_msg_id:
        try:
            await bot.delete_message(chatid, prompt_msg_id)
        except: pass
    try:
        await bot.delete_message(chatid, message.message_id)
    except: pass

    if query == t('buttons_name.cancel', lang):
        # Reset state back to ChooseMultiInventory
        await state.set_state(GeneralStates.ChooseMultiInventory)
        handler = ChooseMultiInventoryHandler(**state_data)
        await handler.render()
        return

    await state.update_data(search_query=query)
    await state.set_state(GeneralStates.ChooseMultiInventory)

    from bot.modules.states_fabric.state_handlers import update_multi_inventory
    await update_multi_inventory(state, userid, chatid, lang)
    
    state_data = await state.get_data()
    handler = ChooseMultiInventoryHandler(**state_data)
    await handler.render()

@main_router.message(StateFilter(GeneralStates.ChooseMultiInventory), IsAuthorizedUser())
async def ChooseMultiInventory_message(message: Message):
    lang = await get_lang(message.from_user.id)
    state = await get_state(message.from_user.id, message.chat.id)

    state_data = await state.get_data()
    reply_to_id = state_data.get('transmitted_data', {}).get('reply_to_message_id') if state_data else None

    from bot.modules.get_state import clear_multi_inventory_state
    await clear_multi_inventory_state(message.from_user.id, message.chat.id, state=state)

    if message.chat.id == message.from_user.id:
        from bot.modules.markup import markups_menu as m
        await bot.send_message(message.chat.id, "❌", reply_markup=await m(message.from_user.id, 'last_menu', lang))
    else:
        from aiogram.exceptions import TelegramBadRequest
        try:
            await bot.send_message(message.chat.id, "❌", reply_to_message_id=reply_to_id or message.message_id)
        except TelegramBadRequest:
            await bot.send_message(message.chat.id, "❌")

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
        await state.clear()

        if 'steps' in transmitted_data and 'process' in transmitted_data:
            transmitted_data['steps'][transmitted_data['process']]['umessageid'] = message.message_id
        else: transmitted_data['umessageid'] = message.message_id

        await ChooseTimeHandler(**data).call_function(number)
        # await func(number, transmitted_data=transmitted_data)

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
        func = data['function']
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
        # await func(fileID, transmitted_data=transmitted_data)

@main_router.message(IsAuthorizedUser(), StateFilter(GeneralStates.ChooseImage))
async def ChooseImage_0(message: Message):
    """Общая функция для получения изображения
    """

    state = await get_state(message.from_user.id, message.chat.id)
    if message.text == '0':
        if data := await state.get_data():
            func = data['function']
            transmitted_data = data['transmitted_data']
            need_image = data['need_image']

        if need_image:
            await state.clear()

            await ChooseImageHandler(**data).call_function('no_image')
            # await func('no_image', transmitted_data=transmitted_data)



