from bot.models.user import User
from bot.models.market import Preferential
from datetime import datetime, timedelta, timezone
from random import choice

from bot.const import GAME_SETTINGS as GS
from bot.exec import main_router, bot
from bot.modules.images_save import send_SmartPhoto
from bot.modules.user.advert import auto_ads
from bot.modules.data_format import list_to_inline, seconds_to_str
from bot.modules.items.item import counts_items
from bot.modules.localization import get_data, get_lang, t
from bot.modules.market.market import preview_product
from bot.modules.markup import back_menu
from bot.modules.markup import markups_menu as m
from bot.modules.managment.statistic import get_now_statistic
from bot.modules.user.friends import get_friend_data
from bot.models.user import User
from aiogram.types import CallbackQuery, InlineKeyboardMarkup, Message

from bot.filters.translated_text import Text
from bot.filters.private import IsPrivateChat
from bot.filters.authorized import IsAuthorizedUser
from aiogram import F



@main_router.message(
    IsPrivateChat(), Text('buttons_name.back'), IsAuthorizedUser())
async def back_buttom(message: Message):
    userid = message.from_user.id
    lang = await get_lang(message.from_user.id)
    back_m = await back_menu(userid)
    # Переделать таверну полностью

    text = t(f'back_text.{back_m}', lang)
    await bot.send_message(message.chat.id, text, 
                           reply_markup=await m(userid, back_m, lang))

@main_router.message(
    IsPrivateChat(), Text('commands_name.settings_menu'), IsAuthorizedUser())
async def settings_menu(message: Message):
    userid = message.from_user.id
    lang = await get_lang(message.from_user.id)
    prf_view_ans = get_data('profile_view.ans', lang)

    user = await User.find_one(User.userid == userid)
    if user:
        user_dict = user.dict()
        settings = user_dict['settings']
        text = t('menu_text.settings', lang, 
                notif=settings['notifications'],
                profile_view=prf_view_ans[settings['profile_view']-1],
                inv_view=f"{settings['inv_view'][0]} | {settings['inv_view'][1]}"
                )
        text = text.replace('True', '✅').replace('False', '❌')

        await bot.send_message(message.chat.id, text, 
                               reply_markup= await m(userid, 'settings_menu', lang))
    
        await auto_ads(message)

@main_router.message(
    IsPrivateChat(), 
    Text('commands_name.settings.settings_page_2'), 
    IsAuthorizedUser()
    )
async def settings2_menu(message: Message):
    userid = message.from_user.id
    lang = await get_lang(message.from_user.id)

    user = await User.find_one(User.userid == userid)
    if user:
        user_dict = user.dict()
        my_name = None
        settings = user_dict['settings']

        if 'my_name' in settings: my_name = settings['my_name']
        if not my_name: my_name = t('owner', lang)

        talk_mode = user_dict['settings'].get('no_talk', False)
        confidentiality = user_dict['settings'].get('confidentiality', False)

        text = t('menu_text.settings2', lang, 
                 my_name=my_name,
                 lang=t('language_name', lang),
                 talk_mode=str(talk_mode).replace('True', '✅').replace('False', '❌'),
                 conf_mode=str(confidentiality).replace('True', '✅').replace('False', '❌')
                 )

        await bot.send_message(message.chat.id, text,
                               reply_markup= await m(userid, 'settings2_menu', lang))

        await auto_ads(message)

@main_router.message(
    IsPrivateChat(), 
    Text('commands_name.profile_menu'), 
    IsAuthorizedUser()
    )
async def profile_menu(message: Message):
    userid = message.from_user.id
    lang = await get_lang(message.from_user.id)

    await bot.send_message(message.chat.id, t('menu_text.profile', lang), 
                           reply_markup= await m(userid, 'profile_menu', lang))

    await auto_ads(message)

@main_router.message(IsPrivateChat(), Text('commands_name.friends_menu'), IsAuthorizedUser())
async def friends_menu(message: Message):
    userid = message.from_user.id
    lang = await get_lang(message.from_user.id)

    await bot.send_message(message.chat.id, t('menu_text.friends', lang), 
                           reply_markup= await m(userid, 'friends_menu', lang))

    await auto_ads(message)

@main_router.message(IsPrivateChat(), Text('commands_name.map.market'), IsAuthorizedUser())
async def market_menu(message: Message):
    userid = message.from_user.id
    lang = await get_lang(message.from_user.id)

    await bot.send_message(message.chat.id, t('menu_text.market.info', lang), 
                           reply_markup= await m(userid, 'market_menu', lang), parse_mode='Markdown')

    user_obj = await User.find_one(User.userid == userid)
    if user_obj:
        products_pref = await Preferential.find(Preferential.user.id != user_obj.id, fetch_links=True).to_list()
    else:
        products_pref = await Preferential.find(fetch_links=True).to_list()
    rand_p = {}

    if products_pref:
        for _ in range(3):
            if products_pref:
                prd = choice(products_pref)
                products_pref.remove(prd)

                product = prd.product
                if product:
                    prd_dict = product.dict()
                    rand_p[
                        preview_product(prd_dict['items'], prd_dict['price'], 
                                        prd_dict['type'], lang)
                    ] = f'product_info info {prd_dict["alt_id"]}'

        if rand_p:
            markup = list_to_inline([rand_p], 1)
            await bot.send_message(message.chat.id, t('menu_text.market.products', lang), 
                                reply_markup=markup, parse_mode='Markdown')
    
    await auto_ads(message)

@main_router.message(IsPrivateChat(), Text('commands_name.actions_menu'), IsAuthorizedUser())
async def actions_menu(message: Message):
    userid = message.from_user.id
    lang = await get_lang(message.from_user.id)

    await bot.send_message(message.chat.id, t('menu_text.actions', lang), 
                           reply_markup = await m(userid, 'actions_menu', lang))
    
    await auto_ads(message)

@main_router.message(IsPrivateChat(), Text('commands_name.map.dino-tavern_menu'), IsAuthorizedUser())
async def tavern_menu(message: Message):
    userid = message.from_user.id
    lang = await get_lang(message.from_user.id)
    text = ''

    photo = 'images/remain/taverna/dino_taverna.png'
    await send_SmartPhoto(message.chat.id, photo, 
                          t('menu_text.dino_tavern.info', lang), 'Markdown',
            show_caption_above_media=True)

    from bot.modules.user.friends import get_frineds
    friends_data = await get_frineds(userid)
    friends = friends_data['friends']

    data_enter = get_data('tavern_enter', lang)
    text = f'🍻 {choice(data_enter)}'
    await bot.send_message(message.chat.id, text, reply_markup= await m(userid, 'dino_tavern_menu', lang))

    from bot.modules.user.tavern_redis import add_to_tavern, is_in_tavern, get_tavern_count

    if not await is_in_tavern(userid):
        uname = await User.get_user_name(message.from_user.id)
        await add_to_tavern(userid, uname, lang)
        friends_in_tavern = []
        for i in friends:
            if await is_in_tavern(i): 
                friends_in_tavern.append(i)

        msg = await bot.send_message(message.chat.id, 
                t('menu_text.dino_tavern.friends', lang))

        text = t('menu_text.dino_tavern.friends2', lang)

        if len(friends_in_tavern):
            text += '\n'
            for friendid in friends_in_tavern:
                friend_lang = await get_lang(friendid)
                friend = await get_friend_data(friendid, userid)

                if friend:
                    buttons = t('menu_text.dino_tavern.button', friend_lang)
                    buttons = list_to_inline([{buttons: f"buy_ale {userid}"}])

                    text += f' • {friend["name"]}\n'
                    text_to_friend = t('menu_text.dino_tavern.went', 
                                    friend_lang, 
                                    name=uname)
                    try:
                        await bot.send_message(
                            friendid, text_to_friend, reply_markup=buttons)
                    except:
                        try: 
                            await bot.send_message(
                                friendid, text_to_friend, reply_markup=buttons)
                        except: pass
        else: text += '❌'

        col = await get_tavern_count()
        text += '\n' + t('menu_text.dino_tavern.tavern_col', lang, col=col)

        await bot.edit_message_text(text=text, chat_id=userid, message_id=msg.message_id)
    
    await auto_ads(message)

@main_router.message(IsPrivateChat(), Text('commands_name.map.blacksmith'), IsAuthorizedUser())
async def blacksmith_menu(message: Message):
    userid = message.from_user.id
    lang = await get_lang(message.from_user.id)
    from bot.handlers.blacksmith import open_blacksmith_menu

    await open_blacksmith_menu(userid, message.chat.id, lang)


@main_router.message(IsPrivateChat(), Text('commands_name.profile.about'), IsAuthorizedUser())
async def about_menu(message: Message):
    userid = message.from_user.id
    lang = await get_lang(message.from_user.id)

    iambot = await bot.get_me()
    bot_name = iambot.username
    col_u, col_d, col_i, col_g, update_time = '?', '?', '?', '?', '?'

    statistic = await get_now_statistic()
    if statistic:
        col_u = statistic['users']
        col_d = statistic['dinosaurs']
        col_i = statistic['items']
        col_g = statistic['groups']

        create = statistic['_id'].generation_time
        now = datetime.now(timezone.utc)
        delta: timedelta = now - create

        update_time = seconds_to_str(delta.seconds, lang, True)

    photo = 'images/remain/about/menu.png'
    await send_SmartPhoto(message.chat.id, photo, 
            t('menu_text.about', lang, bot_name=bot_name,
              col_u=col_u, col_d=col_d, 
              col_i=col_i, col_g=col_g,
              update_time=update_time), 'HTML',
            await m(userid, 'about_menu', lang)
        )

@main_router.message(IsPrivateChat(), Text('commands_name.friends.referal'), IsAuthorizedUser(), IsPrivateChat())
async def referal_menu(message: Message):
    userid = message.from_user.id
    lang = await get_lang(message.from_user.id)

    coins = GS['referal']['coins']
    items = GS['referal']['items']
    award_items = GS['referal']['award_items']
    lvl = GS['referal']['award_lvl']

    award_text = counts_items(award_items, lang, t('menu_text.referal_separator', lang))
    names = counts_items(items, lang)

    await bot.send_message(message.chat.id, t(
                'menu_text.referal', lang, 
                coins=coins, items=names, 
                award_text=award_text, lvl=lvl), 
                parse_mode='Markdown',
                reply_markup= await m(userid, 'referal_menu', lang))

    await auto_ads(message)

@main_router.callback_query(IsPrivateChat(), F.data.startswith('buy_ale'))
async def buy_ale(callback: CallbackQuery):
    chatid = callback.message.chat.id
    userid = callback.from_user.id
    data = callback.data.split()
    lang = await get_lang(callback.from_user.id)

    friend = int(data[1])
    from bot.modules.overwriting.DataCalsses import Transaction
    async with Transaction():
        user = await User.find_one(User.userid == userid)
        friend_user = await User.find_one(User.userid == friend)
        if user and friend_user and await user.remove_coins(150):
            await friend_user.add_item('ale')

            friend_lang = await get_lang(friend)

            text = t('buy_ale.me', lang)
            await bot.edit_message_reply_markup(None, chatid, callback.message.message_id, 
                                                reply_markup=InlineKeyboardMarkup(inline_keyboard=[]))
            await bot.answer_callback_query(callback.id, text, True)

            text_recipient = t('buy_ale.friend', friend_lang, username=await User.get_user_name(userid))
            await bot.send_message(friend, text_recipient)
        else:
            text = t('buy_ale.no_coins', lang)
            await bot.answer_callback_query(callback.id, text, True)

@main_router.message(IsPrivateChat(), Text('commands_name.market.seller_profile'), IsAuthorizedUser())
async def seller_profile(message: Message):
    userid = message.from_user.id
    lang = await get_lang(message.from_user.id)

    await bot.send_message(message.chat.id, t('menu_text.seller', lang), 
                           reply_markup= await m(userid, 'seller_menu', lang))
    
    await auto_ads(message)

@main_router.message(IsPrivateChat(), Text('commands_name.market.background_market'), IsAuthorizedUser())
async def backgrounds(message: Message):
    userid = message.from_user.id
    lang = await get_lang(message.from_user.id)

    await bot.send_message(message.chat.id, t('menu_text.backgrounds_menu', lang), 
                           reply_markup= await m(userid, 'backgrounds_menu', lang))

    await auto_ads(message)

@main_router.message(IsPrivateChat(), Text('commands_name.action_ask.live_actions'), IsAuthorizedUser())
async def live_actions(message: Message):
    userid = message.from_user.id
    lang = await get_lang(message.from_user.id)

    await bot.send_message(message.chat.id, t('menu_text.live_actions', lang), 
                           reply_markup= await m(userid, 'live_actions_menu', lang))

    await auto_ads(message)

@main_router.message(IsPrivateChat(), Text('commands_name.action_ask.extraction'), IsAuthorizedUser())
async def extraction(message: Message):
    userid = message.from_user.id
    lang = await get_lang(message.from_user.id)

    await bot.send_message(message.chat.id, t('menu_text.extraction', lang), 
            reply_markup= await m(userid, 'extraction_actions_menu', lang))

    await auto_ads(message)

@main_router.message(IsPrivateChat(), Text('commands_name.action_ask.skills_actions'), IsAuthorizedUser())
async def skills_actions(message: Message):
    userid = message.from_user.id
    lang = await get_lang(message.from_user.id)

    await bot.send_message(message.chat.id, t('menu_text.skills_actions', lang), 
            reply_markup= await m(userid, 'skills_actions_menu', lang))

    await auto_ads(message)

@main_router.message(IsPrivateChat(), Text('commands_name.action_ask.speed_actions'), IsAuthorizedUser())
async def speed_actions(message: Message):
    userid = message.from_user.id
    lang = await get_lang(message.from_user.id)

    await bot.send_message(message.chat.id, t('menu_text.speed_actions', lang), 
            reply_markup= await m(userid, 'speed_actions_menu', lang))

    await auto_ads(message)