from bot.modules.images_save import send_SmartPhoto
from bot.models.user import User
from time import time
from bot.redismanager import redis_get

from bot.exec import main_router, bot
from bot.modules.data_format import (list_to_inline,
                                     seconds_to_str)
from bot.modules.localization import get_data, get_lang, t, resolve_custom_emojis
from bot.modules.logs import log

from aiogram.types import CallbackQuery, Message

from bot.filters.translated_text import Text
from bot.filters.private import IsPrivateChat
from bot.filters.authorized import IsAuthorizedUser
from aiogram import F


@main_router.message(IsPrivateChat(), Text('commands_name.profile.rayting'), 
                     IsAuthorizedUser())
async def rayting(message: Message):
    chatid = message.chat.id
    lang = await get_lang(message.from_user.id)
    time_update_rayt = 0

    t_upd = await redis_get('rayting:update_time')
    if t_upd:
        time_update_rayt = seconds_to_str(int(time()) - t_upd['time'], lang)
        if t_upd['time'] == 0:

            text = t("rayting.no_rayting", lang)
            await bot.send_message(chatid, text)
        else:
            text = f'{t("rayting.info", lang)}\n_{time_update_rayt}_'

            buttons = {}
            for i in ['lvl', 'coins', 'super', 'achievements']:
                buttons[t(f"rayting.{i}", lang)] = f'rayting {i}'

            buttons[t("rayting.donate", lang)] = f'donate_rayting'

            markup = list_to_inline([buttons], row_width=2)
            await send_SmartPhoto(
                chatid, 'images/rayting/rayting_placeholder.png',
                caption=resolve_custom_emojis(text), parse_mode='Markdown', reply_markup=markup
            )

@main_router.callback_query(IsPrivateChat(), F.data.startswith('rayting'))
async def rayting_call(callback: CallbackQuery):
    chatid = callback.message.chat.id
    userid = callback.from_user.id
    data = callback.data.split()
    lang = await get_lang(callback.from_user.id)

    if len(data) < 2:
        await rayting_main_callback(callback)
        return

    if data[1] == 'achievements':
        rayt_data = await redis_get('rayting:achievements')
        if rayt_data:
            text = t("rayting.rayting_achievements", lang) + '\n\n'
            for item in rayt_data['data']:
                ach_id = item['ach_id']
                username = item['username']
                ach_name = t(f"achievements.{ach_id}.name", lang)
                ach_desc = t(f"achievements.{ach_id}.description", lang)
                value = item.get("value", 0)
                value_formatted = f"{value:,}".replace(",", ".") if isinstance(value, int) else value
                
                kwargs = {"value": value_formatted}
                if "item_id" in item:
                    from bot.modules.items.item import get_name
                    kwargs["item_name"] = get_name(item["item_id"], lang)
                else:
                    kwargs["item_name"] = ""

                metric_str = t(f"rayting.ach_metric.{ach_id}", lang, **kwargs)
                text += f"🏆 *{ach_name}*\n├ 📝 {ach_desc}\n├ 📊 {metric_str}\n└ 👤 *{username}*\n\n"
            
            back_name = t("buttons_name.back", lang)
            markup = list_to_inline([[{"text": back_name, "callback_data": "rayting_main"}]])

            has_photo = hasattr(callback.message, 'photo') and callback.message.photo is not None
            try:
                if has_photo:
                    await callback.message.edit_caption(
                        caption=resolve_custom_emojis(text),
                        parse_mode='Markdown',
                        reply_markup=markup
                    )
                else:
                    await callback.message.edit_text(
                        text=resolve_custom_emojis(text),
                        parse_mode='Markdown',
                        reply_markup=markup
                    )
            except Exception as e:
                log(message=f'Rayting achievements edit error {e}', lvl=2)
        return

    rayt_data = await redis_get(f'rayting:{data[1]}')
    
    page = 1
    if len(data) > 2:
        val_str = data[2]
        if val_str.startswith('p_'):
            page = int(val_str.split('_')[1])
        elif val_str.startswith('r_'):
            place = int(val_str.split('_')[1])
            page = (place - 1) // 10 + 1
        else:
            try:
                val = int(val_str)
                page = (val - 1) // 10 + 1
            except ValueError:
                page = 1

    if rayt_data:
        text = ''
        markup, my_place = None, 0
        place_str = "1000+"

        if userid in rayt_data['ids']:
            my_place = rayt_data['ids'].index(userid) + 1
            place_str = f"{my_place:,}".replace(",", ".")

        total_items = len(rayt_data['data'])
        total_pages = (total_items - 1) // 10 + 1 if total_items > 0 else 1
        page = max(1, min(page, total_pages))

        min_ind = (page - 1) * 10
        max_ind = page * 10
        top_10 = rayt_data['data'][min_ind:max_ind]

        text += t(f"rayting.rayting_{data[1]}", lang) + '\n'
        text += t("rayting.place", lang, place=place_str) + '\n\n'

        for user in top_10:
            sign, add_text = '*├*', ''
            if user == top_10[-1]: sign = '*└*'

            name = str(user['userid'])
            rayt_user = await User.find_one(User.userid == user['userid'])
            if rayt_user: 
                name = await User.get_user_name(user['userid'])
                if name == 'NoName_NoUser': name = str(user['userid'])

            n_val = rayt_data['ids'].index(user['userid']) + 1
            if n_val == 1:
                n = '{custom_emoji:top1}'
            elif n_val == 2:
                n = '{custom_emoji:top2}'
            elif n_val == 3:
                n = '{custom_emoji:top3}'
            else:
                n = f'#{n_val:,}'.replace(",", ".")

            if rayt_user and await rayt_user.premium:
                add_text += t(f"rayting.premium", lang) + '\n     '

            user_formatted = {}
            for k, v in user.items():
                if isinstance(v, int) and k != 'userid':
                    user_formatted[k] = f"{v:,}".replace(",", ".")
                else:
                    user_formatted[k] = v

            add_text += t(f"rayting.{data[1]}_text", lang, **user_formatted)
            text += f'{sign} {n} *{name}*\n     {add_text}\n'

        buttons_list = []
        
        # Row 1: Pagination
        row1 = []
        if total_pages > 1:
            prev_page = page - 1 if page > 1 else total_pages
            next_page = page + 1 if page < total_pages else 1
            row1.append({"text": "◀️", "callback_data": f"rayting {data[1]} p_{prev_page}"})
            row1.append({"text": f"{page}/{total_pages}", "callback_data": "none"})
            row1.append({"text": "▶️", "callback_data": f"rayting {data[1]} p_{next_page}"})
        else:
            row1.append({"text": f"{page}/{total_pages}", "callback_data": "none"})
        buttons_list.append(row1)
        
        # Row 2: My rivals & Back
        row2 = []
        my_place_page = (my_place - 1) // 10 + 1 if my_place > 0 else 0
        if my_place > 0 and page != my_place_page:
            but_name = t("rayting.my_place", lang)
            row2.append({"text": but_name, "callback_data": f"rayting {data[1]} r_{my_place}"})
            
        back_name = t("buttons_name.back", lang)
        row2.append({"text": back_name, "callback_data": "rayting_main"})
        buttons_list.append(row2)
        
        markup = list_to_inline(buttons_list)

        import os
        from bot.redismanager import redis_set
        from aiogram.types import InputMediaPhoto, FSInputFile

        img_path = f"temp/rayting_{data[1]}.png"
        file_id_key = f"rayting:file_id:{data[1]}"
        file_id = await redis_get(file_id_key)

        # Генерация на лету, если картинки нет
        if not file_id and not os.path.exists(img_path):
            try:
                from bot.modules.images_creators.rayting_image import generate_rayting_image
                await generate_rayting_image(data[1], rayt_data['data'][:3])
            except Exception as e:
                log(f"Error on-the-fly generating rating image: {e}", lvl=2)

        has_photo = hasattr(callback.message, 'photo') and callback.message.photo is not None
        media_input = file_id if file_id else (FSInputFile(img_path) if os.path.exists(img_path) else None)

        if media_input:
            if has_photo:
                try:
                    res = await callback.message.edit_media(
                        media=InputMediaPhoto(
                            media=media_input,
                            caption=resolve_custom_emojis(text),
                            parse_mode='Markdown'
                        ),
                        reply_markup=markup
                    )
                    if not file_id and res and res.photo:
                        new_file_id = res.photo[-1].file_id
                        await redis_set(file_id_key, new_file_id)
                except Exception as e:
                    log(message=f'Rayting edit media error {e}', lvl=2)
            else:
                try:
                    await callback.message.delete()
                except Exception:
                    pass
                try:
                    res = await bot.send_photo(
                        chat_id=chatid,
                        photo=media_input,
                        caption=resolve_custom_emojis(text),
                        parse_mode='Markdown',
                        reply_markup=markup
                    )
                    if not file_id and res and res.photo:
                        new_file_id = res.photo[-1].file_id
                        await redis_set(file_id_key, new_file_id)
                except Exception as e:
                    log(message=f'Rayting send photo error {e}', lvl=2)
        else:
            try:
                if has_photo:
                    try:
                        await callback.message.delete()
                    except Exception:
                        pass
                    await bot.send_message(chatid, resolve_custom_emojis(text), parse_mode='Markdown', reply_markup=markup)
                else:
                    await bot.edit_message_text(resolve_custom_emojis(text), None, chatid, callback.message.message_id, parse_mode='Markdown', reply_markup=markup)
            except Exception as e:
                log(message=f'Rayting edit fallback error {e}', lvl=2)

@main_router.callback_query(IsPrivateChat(), F.data.startswith('donate_rayting'))
async def donate_rayting(callback: CallbackQuery):
    chatid = callback.message.chat.id
    userid = callback.from_user.id
    data = callback.data.split()
    lang = await get_lang(callback.from_user.id)
    message = callback.message
    
    if isinstance(message, Message):
        if len(data) == 1:
            back_name = t("buttons_name.back", lang)
            mark = list_to_inline([
                {t('rayting.donate_30d', lang): 'donate_rayting 30d'},
                {t('rayting.donate_all', lang): 'donate_rayting all'},
                {back_name: 'rayting_main'}
            ], row_width=2)

            has_photo = hasattr(message, 'photo') and message.photo is not None
            if has_photo:
                try:
                    await message.edit_caption(caption=t("rayting.donate_choose", lang), parse_mode='Markdown', reply_markup=mark)
                except Exception as e:
                    log(message=f'Donate rayting choose edit caption error {e}', lvl=2)
            else:
                try:
                    await message.edit_text(t("rayting.donate_choose", lang), parse_mode='Markdown', reply_markup=mark)
                except Exception as e:
                    log(message=f'Donate rayting choose edit text error {e}', lvl=2)

        else:
            code = data[1]
            rayt_data = await redis_get(f'rayting:dontaion_{code}')
            
            page = 1
            if len(data) > 2:
                val_str = data[2]
                if val_str.startswith('p_'):
                    page = int(val_str.split('_')[1])
                elif val_str.startswith('r_'):
                    place = int(val_str.split('_')[1])
                    page = (place - 1) // 10 + 1
                else:
                    try:
                        val = int(val_str)
                        page = (val - 1) // 10 + 1
                    except ValueError:
                        page = 1
            
            if rayt_data:
                my_place = 0
                if userid in rayt_data['ids']:
                    my_place = rayt_data['ids'].index(userid) + 1
                    
                total_items = len(rayt_data['data'])
                total_pages = (total_items - 1) // 10 + 1 if total_items > 0 else 1
                page = max(1, min(page, total_pages))
                
                min_ind = (page - 1) * 10
                max_ind = page * 10
                top_page = rayt_data['data'][min_ind:max_ind]
                
                text = t(f"rayting.rayting_donate_{code}", lang) + '\n'
                
                place_str = "1000+"
                if my_place > 0:
                    place_str = f"{my_place:,}".replace(",", ".")
                text += t("rayting.place", lang, place=place_str) + '\n\n'

                for user in top_page:
                    sign, add_text = '*├*', ''
                    if user == top_page[-1]: sign = '*└*'

                    rayt_user = await User.find_one(User.userid == user['userid'])
                    if rayt_user: 
                        name = await User.get_user_name(user['userid'])
                        if name == 'NoName_NoUser': name = str(user['userid'])
                    else:
                        name = str(user['userid'])

                    n_val = rayt_data['ids'].index(user['userid']) + 1
                    if n_val == 1:
                        n = '{custom_emoji:top1}'
                    elif n_val == 2:
                        n = '{custom_emoji:top2}'
                    elif n_val == 3:
                        n = '{custom_emoji:top3}'
                    else:
                        n = f'#{n_val:,}'.replace(",", ".")

                    if rayt_user and await rayt_user.premium:
                        add_text += t(f"rayting.premium", lang) + '\n     '

                    stars_fmt = f"{user['amount']:,}".replace(",", ".")
                    add_text += t(f"rayting.donate_text", lang, stars=stars_fmt)
                    text += f'{sign} {n} *{name}*\n     {add_text}\n'

                buttons_list = []
                
                # Row 1: Pagination
                row1 = []
                if total_pages > 1:
                    prev_page = page - 1 if page > 1 else total_pages
                    next_page = page + 1 if page < total_pages else 1
                    row1.append({"text": "◀️", "callback_data": f"donate_rayting {code} p_{prev_page}"})
                    row1.append({"text": f"{page}/{total_pages}", "callback_data": "none"})
                    row1.append({"text": "▶️", "callback_data": f"donate_rayting {code} p_{next_page}"})
                else:
                    row1.append({"text": f"{page}/{total_pages}", "callback_data": "none"})
                buttons_list.append(row1)
                
                # Row 2: My rivals & Back
                row2 = []
                my_place_page = (my_place - 1) // 10 + 1 if my_place > 0 else 0
                if my_place > 0 and page != my_place_page:
                    but_name = t("rayting.my_place", lang)
                    row2.append({"text": but_name, "callback_data": f"donate_rayting {code} r_{my_place}"})
                    
                back_name = t("buttons_name.back", lang)
                row2.append({"text": back_name, "callback_data": "donate_rayting"})
                buttons_list.append(row2)
                
                markup = list_to_inline(buttons_list)

                try:
                    import os
                    from bot.redismanager import redis_set
                    from aiogram.types import InputMediaPhoto, FSInputFile

                    rating_key = f"dontaion_{code}"
                    img_path = f"temp/rayting_{rating_key}.png"
                    file_id_key = f"rayting:file_id:{rating_key}"
                    file_id = await redis_get(file_id_key)

                    # Генерация на лету, если картинки нет
                    if not file_id and not os.path.exists(img_path):
                        try:
                            from bot.modules.images_creators.rayting_image import generate_rayting_image
                            await generate_rayting_image(rating_key, rayt_data['data'][:3])
                        except Exception as e:
                            log(f"Error on-the-fly generating donation rating image: {e}", lvl=2)

                    has_photo = hasattr(callback.message, 'photo') and callback.message.photo is not None
                    media_input = file_id if file_id else (FSInputFile(img_path) if os.path.exists(img_path) else None)

                    if media_input:
                        if has_photo:
                            try:
                                res = await callback.message.edit_media(
                                    media=InputMediaPhoto(
                                        media=media_input,
                                        caption=resolve_custom_emojis(text),
                                        parse_mode='Markdown'
                                    ),
                                    reply_markup=markup
                                )
                                if not file_id and res and res.photo:
                                    new_file_id = res.photo[-1].file_id
                                    await redis_set(file_id_key, new_file_id)
                            except Exception as e:
                                log(message=f'Donation rayting edit media error {e}', lvl=2)
                        else:
                            try:
                                await callback.message.delete()
                            except Exception:
                                pass
                            try:
                                res = await bot.send_photo(
                                    chat_id=chatid,
                                    photo=media_input,
                                    caption=resolve_custom_emojis(text),
                                    parse_mode='Markdown',
                                    reply_markup=markup
                                )
                                if not file_id and res and res.photo:
                                    new_file_id = res.photo[-1].file_id
                                    await redis_set(file_id_key, new_file_id)
                            except Exception as e:
                                log(message=f'Donation rayting send photo error {e}', lvl=2)
                    else:
                        try:
                            if has_photo:
                                try:
                                    await callback.message.delete()
                                except Exception:
                                    pass
                                await bot.send_message(chatid, resolve_custom_emojis(text), parse_mode='Markdown', reply_markup=markup)
                            else:
                                await message.edit_text(resolve_custom_emojis(text), parse_mode='Markdown', reply_markup=markup)
                        except Exception as e:
                            log(message=f'Donation rayting edit fallback error {e}', lvl=2)
                except Exception as e:
                    log(message=f'Donation rayting process error {e}', lvl=2)

@main_router.callback_query(IsPrivateChat(), F.data == 'rayting_main')
async def rayting_main_callback(callback: CallbackQuery):
    chatid = callback.message.chat.id
    lang = await get_lang(callback.from_user.id)
    time_update_rayt = 0

    t_upd = await redis_get('rayting:update_time')
    if t_upd:
        time_update_rayt = seconds_to_str(int(time()) - t_upd['time'], lang)
        if t_upd['time'] == 0:
            text = t("rayting.no_rayting", lang)
            markup = None
        else:
            text = f'{t("rayting.info", lang)}\n_{time_update_rayt}_'

            buttons = {}
            for i in ['lvl', 'coins', 'super', 'achievements']:
                buttons[t(f"rayting.{i}", lang)] = f'rayting {i}'

            buttons[t("rayting.donate", lang)] = f'donate_rayting'

            markup = list_to_inline([buttons], row_width=2)
            
        has_photo = hasattr(callback.message, 'photo') and callback.message.photo is not None
        
        if has_photo:
            from bot.redismanager import redis_set
            from aiogram.types import InputMediaPhoto, FSInputFile
            file_id_key = "rayting:file_id:placeholder"
            file_id = await redis_get(file_id_key)
            media_input = file_id if file_id else FSInputFile('images/rayting/rayting_placeholder.png')
            
            try:
                res = await callback.message.edit_media(
                    media=InputMediaPhoto(
                        media=media_input,
                        caption=resolve_custom_emojis(text),
                        parse_mode='Markdown'
                    ),
                    reply_markup=markup
                )
                if not file_id and res and res.photo:
                    await redis_set(file_id_key, res.photo[-1].file_id)
            except Exception as e:
                log(message=f'Rayting main edit media error {e}', lvl=2)
        else:
            try:
                await callback.message.edit_text(
                    text=resolve_custom_emojis(text),
                    parse_mode='Markdown',
                    reply_markup=markup
                )
            except Exception as e:
                log(message=f'Rayting main edit text error {e}', lvl=2)
