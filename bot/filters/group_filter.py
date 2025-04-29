
from typing import Optional
from aiogram.filters import BaseFilter
from aiogram.types import Message, InlineKeyboardButton, CallbackQuery
from aiogram.utils.keyboard import InlineKeyboardBuilder

from bot.config import conf
from bot.modules.data_format import list_to_inline
from bot.modules.groups import add_group_user, add_message, get_group, insert_group, group_user
from bot.modules.user.user import User, user_in_chat
from bot.modules.localization import get_lang, t

class GroupRules(BaseFilter):
    def __init__(self, allow_pm: bool = False) -> None:
        """
            Фильтр для проверки соответствию правилам группы.
            То есть - является ли топик правилным
            
            Так же создаёт настройки для группы если их нет
            Создаёт юзера если он не был создан при входе
        """
        self.allow_pm = allow_pm

    async def __call__(self, var: Message | CallbackQuery) -> bool:
        if isinstance(var, CallbackQuery): 
            message = var.message
            from_user = var.from_user
        else:
            message = var
            from_user = message.from_user

        if message.chat.type not in ['group', 'supergroup'] and not self.allow_pm:
            return False
        if message.chat.type == 'private' and self.allow_pm:
            return True

        group = await get_group(message.chat.id)
        if not group:
            await insert_group(message.chat.id)
            group = await get_group(message.chat.id) # type: ignore

        user = await group_user(message.chat.id, from_user.id)
        if not user:
            await add_group_user(message.chat.id, from_user.id)
            user = await group_user(message.chat.id, from_user.id)

        if not user:
            text = t('group_filter.no_account', 
                     from_user.language_code)

            markup_inline = InlineKeyboardBuilder()
            markup_inline.add(
                InlineKeyboardButton(
                text=t('group_filter.to_bot', from_user.language_code), 
                url=f'https://t.me/DinoGochi_bot?start=group_{message.chat.id}'
            ))

            mes = await message.answer(text, reply_markup=markup_inline.as_markup())
            await add_message(message.chat.id, mes.message_id)
            return False


        if group:
            if group['topic_link'] == 0: return True
            else:
                if group['topic_link'] == message.message_thread_id:
                    return True
                else:
                    if group['topic_incorrect_message']:

                        if message.chat.username:
                            url = f'https://t.me/{message.chat.username}/{group["topic_link"]}'
                        else:
                            url = f'https://t.me/c/{str(message.chat.id)[4:]}/{group["topic_link"]}'

                        user_status = await user_in_chat(
                            from_user.id, message.chat.id)
                        user_lang = await get_lang(from_user.id)

                        if user_status in ['administrator', 'creator']:
                            text = t('group_filter.incorrect_topic_admin', 
                                     user_lang)

                            markup_inline = InlineKeyboardBuilder()
                            markup_inline.add(
                                InlineKeyboardButton(
                                text=t('group_filter.null_topic', user_lang), 
                                callback_data='groups_setting null_topic')
                            )
                            markup_inline.add(
                                InlineKeyboardButton(
                                    text=t('group_filter.to_topic', user_lang), 
                                    url=url
                                )
                            )
 
                        else:
                            text = t('group_filter.incorrect_topic_user', user_lang)
                            markup_inline = InlineKeyboardBuilder()
                            markup_inline.add(
                                InlineKeyboardButton(
                                    text=t('group_filter.to_topic', user_lang), 
                                    url=url
                                )
                            )

                        mes = await message.answer(text, 
                                    reply_markup=markup_inline.as_markup())
                        await add_message(message.chat.id, mes.message_id)
                    return False
        await add_message(message.chat.id, message.message_id)
        return True
