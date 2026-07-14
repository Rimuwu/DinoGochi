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
            await bot.send_message(chatid, text, reply_markup=markup, parse_mode='Markdown')

@main_router.callback_query(IsPrivateChat(), F.data.startswith('rayting'))
async def rayting_call(callback: CallbackQuery):
    chatid = callback.message.chat.id
    userid = callback.from_user.id
    data = callback.data.split()
    lang = await get_lang(callback.from_user.id)
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
                metric_str = t(f"rayting.ach_metric.{ach_id}", lang, value=value_formatted)
                text += f"🏆 *{ach_name}*\n├ 📝 {ach_desc}\n├ 📊 {metric_str}\n└ 👤 *{username}*\n\n"
            try:
                await bot.edit_message_text(resolve_custom_emojis(text), None, chatid, callback.message.message_id, parse_mode='Markdown')
            except Exception as e:
                log(message=f'Rayting achievements edit error {e}', lvl=2)
        return

    rayt_data = {}
    rayt_data = await redis_get(f'rayting:{data[1]}')
    if len(data) > 2: 
        max_ind = int(data[2]) + 4
        min_ind = max_ind - 10
    else:  max_ind, min_ind = 10, 0

    if rayt_data:
        add_my_rivals, text = False, ''
        markup, my_place = None, 0
        place_str = "1000+"

        if userid in rayt_data['ids']:
            my_place = rayt_data['ids'].index(userid) + 1
            place_str = f"{my_place:,}".replace(",", ".")
        top_10 = rayt_data['data'][min_ind:max_ind]
        if my_place > 10: add_my_rivals = True

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

        if add_my_rivals:
            but_name = t("rayting.my_place", lang)
            buttons = [{but_name: f'rayting {data[1]} {my_place}'}]
            markup = list_to_inline(buttons)

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
            mark = list_to_inline([
                {t('rayting.donate_30d', lang): 'donate_rayting 30d'},
                {t('rayting.donate_all', lang): 'donate_rayting all'}
            ])

            await message.edit_text(t("rayting.donate_choose", lang), parse_mode='Markdown', reply_markup=mark)

        else:
            code = data[1]
            rayt_data = await redis_get(f'rayting:dontaion_{code}')
            
            if rayt_data:
                top_30 = rayt_data['data'][:15]
                text = t(f"rayting.rayting_donate_{code}", lang) + '\n\n'

                for user in top_30:
                    sign, add_text = '*├*', ''
                    if user == top_30[-1]: sign = '*└*'

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
                                    )
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
                                    parse_mode='Markdown'
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
                                await bot.send_message(chatid, resolve_custom_emojis(text), parse_mode='Markdown')
                            else:
                                await message.edit_text(resolve_custom_emojis(text), parse_mode='Markdown')
                        except Exception as e:
                            log(message=f'Donation rayting edit fallback error {e}', lvl=2)
                except Exception as e:
                    log(message=f'Donation rayting process error {e}', lvl=2)