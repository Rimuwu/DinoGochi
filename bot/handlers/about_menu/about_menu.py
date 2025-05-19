
from asyncio import sleep
from bot.exec import main_router, bot
from bot.modules import markup
from bot.modules.data_format import list_to_inline
from bot.modules.decorators import HDCallback, HDMessage
from bot.modules.images_save import edit_SmartPhoto, send_SmartPhoto
from bot.modules.localization import get_data, get_lang, t
from aiogram.types import (CallbackQuery, InlineKeyboardButton, Message)
from aiogram.utils.keyboard import  InlineKeyboardBuilder
from bot.filters.translated_text import Text
from bot.filters.private import IsPrivateChat
from bot.filters.authorized import IsAuthorizedUser
from aiogram.filters import Command
from aiogram import F
from bot.const import GAME_SETTINGS as GS
from bot.modules.sub_award import award_for_entry, check_award, check_for_entry

@HDMessage
@main_router.message(IsPrivateChat(), Text('commands_name.about.team'), 
                     IsAuthorizedUser())
async def team(message: Message):
    lang = await get_lang(message.from_user.id)
    chatid = message.chat.id

    lang_text = t('language_name', lang)
    author_loc = t('localization_author', lang)

    await bot.send_message(chatid, t('about_menu.team', lang, 
                                     lang_name=lang_text,
                                     author=author_loc
                                    ), parse_mode='html')

@HDMessage
@main_router.message(Command('links'), IsPrivateChat())
@main_router.message(IsPrivateChat(), Text('commands_name.about.links'), 
                     IsAuthorizedUser())
async def links(message: Message, mes_edit: int = 0, 
                lang: str = '', userid: int = 0):
    if not lang:
        lang = await get_lang(message.from_user.id)
    if not userid:
        userid = message.from_user.id

    chatid = message.chat.id
    image = 'images/remain/about/dino_links.png'

    award_forum = GS['forum_subs_reward']
    award_channel = GS['channel_subs_reward']

    if await check_award(userid, 'forum'):
        award_forum = t('link_reward.already_awarded', lang)

    if await check_award(userid, 'channel'):
        award_channel = t('link_reward.already_awarded', lang)

    text = t('about_menu.links', lang,
             forum_reward=award_forum,
             channel_reward=award_channel
             )

    markup_inline = InlineKeyboardBuilder()
    markup_inline.row(
        InlineKeyboardButton(
            text=t('about_menu.buttons.forum', lang),
            url=GS['bot_forum']
        ),
        InlineKeyboardButton(
            text=t('about_menu.buttons.channel', lang),
            url=GS['bot_channel']
        ),
        InlineKeyboardButton(
            text=t('about_menu.buttons.boost', lang),
            url=GS['bot_channel'] + '?boost'
        ),
        width=2
    )

    markup_inline.row(
        InlineKeyboardButton(
            text=t('about_menu.buttons.check', lang),
            callback_data='link_reward'
        ),
        width=1
    )

    if not mes_edit:
        await send_SmartPhoto(chatid, image, text, 'Markdown', reply_markup=markup_inline.as_markup(resize_keyboard=True))
    else:
        await edit_SmartPhoto(chatid, mes_edit, image, text, 'Markdown', reply_markup=markup_inline.as_markup(resize_keyboard=True))

@main_router.callback_query(IsPrivateChat(), F.data == 'link_reward')
async def link_reward(call: CallbackQuery):
    lang = await get_lang(call.from_user.id)
    chatid = call.message.chat.id
    
    checks = ['channel', 'forum']
    # Проверяем наличие пользователя в обоих каналах
    in_channel = await check_for_entry(call.from_user.id, 'channel')
    in_forum = await check_for_entry(call.from_user.id, 'forum')

    # Проверяем, получена ли награда за оба канала
    award_channel = await check_award(call.from_user.id, 'channel')
    award_forum = await check_award(call.from_user.id, 'forum')

    if (in_channel and not award_channel) or (in_forum and not award_forum):
        res = 'susseful'
    elif not in_channel or not in_forum:
        res = 'no_in_chat'
    elif award_channel and award_forum:
        res = 'alredy_award'

    text = t(f'link_reward.{res}', lang)
    await call.answer(text, show_alert=True)
    if res == 'susseful':
        for check in checks:
            if await check_for_entry(call.from_user.id, check):
                await award_for_entry(call.from_user.id, check)

        await sleep(2)
        await links(call.message, call.message.message_id, lang, 
                    call.from_user.id)

async def faq_func(lang, chatid):
    faq_data = get_data('faq', lang)
    buttons = faq_data['inline_buttons']

    markup_inline = InlineKeyboardBuilder()
    row = []
    for key, name in buttons.items():
        if key.startswith('null'):
            markup_inline.row(*row, width=3)
            row = []
            row.append(
                InlineKeyboardButton(
                    text=' ', 
                    callback_data='faq ' + key
                )
            )
            markup_inline.row(*row, width=3)
            row = []
        else:
            if len(name) > 10 and len(row) == 2:
                markup_inline.row(*row, width=3)
                row = []
            row.append(
                InlineKeyboardButton(
                    text=name, 
                    callback_data='faq ' + key
                )
            )
    markup_inline.row(*row, width=3)

    await bot.send_message(chatid, faq_data['text'], parse_mode='Markdown', reply_markup=markup_inline.as_markup(resize_keyboard=True))


@HDMessage
@main_router.message(IsPrivateChat(), Text('commands_name.about.faq'), 
                     IsAuthorizedUser())
async def faq(message: Message):
    await faq_func(await get_lang(message.from_user.id), message.chat.id)

@HDMessage
@main_router.message(IsPrivateChat(), Command(commands=['faq']))
async def faq_com(message: Message):
    await faq_func(await get_lang(message.from_user.id), message.chat.id)

@HDCallback
@main_router.callback_query(IsPrivateChat(), F.data.startswith('open_faq'))
async def open_faq(call: CallbackQuery):
    await faq_func(await get_lang(call.from_user.id), call.message.chat.id)

@HDCallback
@main_router.callback_query(IsPrivateChat(), F.data.startswith('faq'))
async def faq_buttons(call: CallbackQuery):
    data = call.data.split()[1]
    chatid = call.message.chat.id
    lang = await get_lang(call.from_user.id)

    if data and not data.startswith('null'):
        text = t(f'faq.{data}', lang)
        await bot.send_message(chatid, text, parse_mode='Markdown')
    else:
        await call.answer()