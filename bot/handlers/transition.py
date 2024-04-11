from asyncio import sleep
from datetime import datetime, timedelta, timezone
from random import choice
from time import time

from telebot.types import Message, CallbackQuery, InlineKeyboardMarkup

from bot.config import mongo_client
from bot.const import GAME_SETTINGS as GS
from bot.exec import bot
from bot.modules.advert import auto_ads
from bot.modules.data_format import list_to_inline, seconds_to_str, user_name
from bot.modules.images import async_open
from bot.modules.item import counts_items, AddItemToUser
from bot.modules.localization import get_data, t, get_lang
from bot.modules.markup import back_menu
from bot.modules.markup import markups_menu as m
from bot.modules.statistic import get_now_statistic
from bot.modules.user import User, take_coins
from bot.modules.market import preview_product
 

users = mongo_client.user.users
tavern = mongo_client.tavern.tavern
preferential = mongo_client.market.preferential
products = mongo_client.market.products

@bot.message_handler(pass_bot=True, text='buttons_name.back', is_authorized=True)
async def back_buttom(message: Message):
    userid = message.from_user.id
    lang = await get_lang(message.from_user.id)
    back_m = await back_menu(userid)
    # Переделать таверну полностью

    text = t(f'back_text.{back_m}', lang)
    await bot.send_message(message.chat.id, text, 
                           reply_markup=await m(userid, back_m, lang))

@bot.message_handler(pass_bot=True, text='commands_name.settings_menu', is_authorized=True)
async def settings_menu(message: Message):
    userid = message.from_user.id
    lang = await get_lang(message.from_user.id)
    prf_view_ans = get_data('profile_view.ans', lang)

    user = await users.find_one({'userid': userid})
    if user:
        settings = user['settings']
        text = t('menu_text.settings', lang, 
                notif=settings['notifications'],
                profile_view=prf_view_ans[settings['profile_view']-1],
                inv_view=f"{settings['inv_view'][0]} | {settings['inv_view'][1]}"
                )
        text = text.replace('True', '✅').replace('False', '❌')

        await bot.send_message(message.chat.id, text, 
                               reply_markup= await m(userid, 'settings_menu', lang))
    
        await auto_ads(message)

@bot.message_handler(pass_bot=True, text='commands_name.settings.settings_page_2', is_authorized=True)
async def settings2_menu(message: Message):
    userid = message.from_user.id
    lang = await get_lang(message.from_user.id)

    user = await users.find_one({'userid': userid})
    if user:
        my_name = None
        settings = user['settings']

        if 'my_name' in settings: my_name = settings['my_name']
        if not my_name: my_name = t('owner', lang)
        
        text = t('menu_text.settings2', lang, my_name=my_name)

        await bot.send_message(message.chat.id, text, 
                               reply_markup= await m(userid, 'settings2_menu', lang))
        
        await auto_ads(message)

@bot.message_handler(pass_bot=True, text='commands_name.profile_menu', is_authorized=True)
async def profile_menu(message: Message):
    userid = message.from_user.id
    lang = await get_lang(message.from_user.id)

    await bot.send_message(message.chat.id, t('menu_text.profile', lang), 
                           reply_markup= await m(userid, 'profile_menu', lang))

    await auto_ads(message)
    
@bot.message_handler(pass_bot=True, text='commands_name.friends_menu', is_authorized=True)
async def friends_menu(message: Message):
    userid = message.from_user.id
    lang = await get_lang(message.from_user.id)

    await bot.send_message(message.chat.id, t('menu_text.friends', lang), 
                           reply_markup= await m(userid, 'friends_menu', lang))

    await auto_ads(message)

@bot.message_handler(pass_bot=True, text='commands_name.profile.market', is_authorized=True)
async def market_menu(message: Message):
    userid = message.from_user.id
    lang = await get_lang(message.from_user.id)

    await bot.send_message(message.chat.id, t('menu_text.market.info', lang), 
                           reply_markup= await m(userid, 'market_menu', lang), parse_mode='Markdown')

    products_pref = list(await preferential.find({"owner_id": {"$ne": userid}}).to_list(None)).copy()
    rand_p = {}

    if products_pref:
        for _ in range(3):
            if products_pref:
                prd = choice(products_pref)
                products_pref.remove(prd)

                product = await products.find_one({'_id': prd['product_id']})
                if product:
                    rand_p[
                        preview_product(product['items'], product['price'], 
                                        product['type'], lang)
                    ] = f'product_info info {product["alt_id"]}'

        if rand_p:
            markup = list_to_inline([rand_p], 1)
            await bot.send_message(message.chat.id, t('menu_text.market.products', lang), 
                                reply_markup=markup, parse_mode='Markdown')
    
    await auto_ads(message)


@bot.message_handler(pass_bot=True, text='commands_name.actions_menu', is_authorized=True)
async def actions_menu(message: Message):
    userid = message.from_user.id
    lang = await get_lang(message.from_user.id)

    await bot.send_message(message.chat.id, t('menu_text.actions', lang), 
                           reply_markup = await m(userid, 'actions_menu', lang))
    
    await auto_ads(message)

@bot.message_handler(pass_bot=True, text='commands_name.dino-tavern_menu', is_authorized=True)
async def tavern_menu(message: Message):
    userid = message.from_user.id
    lang = await get_lang(message.from_user.id)
    text = ''

    photo = await async_open('images/remain/taverna/dino_taverna.png', True)
    await bot.send_photo(message.chat.id, photo, 
            t('menu_text.dino_tavern.info', lang))

    user = await User().create(userid)
    friends_data = await user.get_friends
    friends = friends_data['friends']

    data_enter = get_data('tavern_enter', lang)
    text = f'🍻 {choice(data_enter)}'
    await bot.send_message(message.chat.id, text, reply_markup= await m(userid, 'dino_tavern_menu', lang))

    if not await tavern.find_one({'userid': userid}):
        await tavern.insert_one({
            'userid': userid,
            'time_in': int(time()),
            'lang': lang,
            'name': user_name(message.from_user, False)
        })
        friends_in_tavern = []
        for i in friends:
            if await tavern.find_one({"userid": i}): friends_in_tavern.append(i)

        msg = await bot.send_message(message.chat.id, 
                t('menu_text.dino_tavern.friends', lang))

        text = t('menu_text.dino_tavern.friends2', lang)
        buttons = t('menu_text.dino_tavern.button', lang)
        buttons = list_to_inline([{buttons: f"buy_ale {userid}"}])

        if len(friends_in_tavern):
            text += '\n'
            for friendid in friends_in_tavern:
                friendChat = await bot.get_chat_member(friendid, friendid)
                friend = friendChat.user
                if friend:
                    text += f' 🎱 {user_name(friend)}\n'
                    text_to_friend = t('menu_text.dino_tavern.went', 
                                    await get_lang(friend.id), 
                                    name=user_name(message.from_user))
                    try:
                        await bot.send_message(
                            friendid, text_to_friend, reply_markup=buttons)
                    except:
                        await sleep(0.3)
                        try: 
                            await bot.send_message(
                                friendid, text_to_friend, reply_markup=buttons)
                        except: pass
        else: text += '❌'
        
        text += '\n' + t('menu_text.dino_tavern.tavern_col', lang,
                col = await tavern.count_documents({}))

        await bot.edit_message_text(text=text, chat_id=userid, message_id=msg.message_id)
    
    await auto_ads(message)

@bot.message_handler(pass_bot=True, text='commands_name.profile.about', is_authorized=True)
async def about_menu(message: Message):
    userid = message.from_user.id
    lang = await get_lang(message.from_user.id)

    iambot = await bot.get_me()
    bot_name = iambot.username
    col_u, col_d, col_i, update_time = '?', '?', '?', '?'

    statistic = await get_now_statistic()
    if statistic:
        col_u = statistic['users']
        col_d = statistic['dinosaurs']
        col_i = statistic['items']

        create = statistic['_id'].generation_time
        now = datetime.now(timezone.utc)
        delta: timedelta = now - create
        
        update_time = seconds_to_str(delta.seconds, lang, True)

    photo = await async_open('images/remain/about/menu.png', True)
    await bot.send_photo(message.chat.id, photo, 
            t('menu_text.about', lang, bot_name=bot_name,
              col_u=col_u, col_d=col_d, 
              col_i=col_i, update_time=update_time
        ), reply_markup = await m(userid, 'about_menu', lang),
           parse_mode ='HTML'
           )

    await auto_ads(message)

@bot.message_handler(pass_bot=True, text='commands_name.friends.referal', is_authorized=True)
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

@bot.callback_query_handler(pass_bot=True, func=lambda call: call.data.startswith('buy_ale'))
async def buy_ale(callback: CallbackQuery):
    chatid = callback.message.chat.id
    userid = callback.from_user.id
    data = callback.data.split()
    lang = await get_lang(callback.from_user.id)

    friend = int(data[1])
    if await take_coins(userid, -50, True):
        await AddItemToUser(friend, 'ale')

        text = t('buy_ale.me', lang)
        await bot.edit_message_reply_markup(chatid, callback.message.id, reply_markup=InlineKeyboardMarkup())
        await bot.answer_callback_query(callback.id, text, True)

        text = t('buy_ale.friend', lang, username=user_name(callback.from_user))
        await bot.send_message(friend, text)
    else:
        text = t('buy_ale.no_coins', lang)
        await bot.send_message(friend, text)

@bot.message_handler(pass_bot=True, text='commands_name.market.seller_profile', is_authorized=True)
async def seller_profile(message: Message):
    userid = message.from_user.id
    lang = await get_lang(message.from_user.id)

    await bot.send_message(message.chat.id, t('menu_text.seller', lang), 
                           reply_markup= await m(userid, 'seller_menu', lang))
    
    await auto_ads(message)
    
@bot.message_handler(pass_bot=True, text='commands_name.market.background_market', is_authorized=True)
async def backgrounds(message: Message):
    userid = message.from_user.id
    lang = await get_lang(message.from_user.id)

    await bot.send_message(message.chat.id, t('menu_text.backgrounds_menu', lang), 
                           reply_markup= await m(userid, 'backgrounds_menu', lang))

    await auto_ads(message)