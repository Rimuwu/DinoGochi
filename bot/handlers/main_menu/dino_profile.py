from time import time

from bot.dbmanager import mongo_client
from bot.exec import main_router, bot
from bot.handlers.main_menu.mood_log import send_mood_log
from bot.modules.data_format import (list_to_inline, seconds_to_str)
from bot.modules.decorators import HDCallback, HDMessage
from bot.modules.dinosaur.dinosaur import Dino, Egg, check_status, dead_check
from bot.modules.dinosaur.profile import dino_profile, manage_markup, skills_profile
from bot.modules.images import async_open
from bot.modules.inline import inline_menu
from bot.modules.dinosaur.kindergarten import (check_hours, hours_now, m_hours)
from bot.modules.localization import get_lang, t
from bot.modules.logs import log
from bot.modules.markup import confirm_markup
from bot.modules.markup import markups_menu as m
from bot.modules.overwriting.DataCalsses import DBconstructor
from bot.modules.states_fabric.state_handlers import ChooseConfirmHandler, ChooseDinoHandler
from bot.modules.user.friends import get_friend_data
from bot.modules.user.user import premium
from aiogram import types
from aiogram.types import Message

from bot.filters.translated_text import Text
from bot.filters.private import IsPrivateChat
from bot.filters.authorized import IsAuthorizedUser
from aiogram import F

from bot.handlers.main_menu.egg_profile import egg_profile

dinosaurs = DBconstructor(mongo_client.dinosaur.dinosaurs)
dino_owners = DBconstructor(mongo_client.dinosaur.dino_owners)

users = DBconstructor(mongo_client.user.users)

# Вызов профиля яйца / динозавра через одну кнопку
async def transition(oid, transmitted_data: dict):
    userid = transmitted_data['userid']
    chatid = transmitted_data['chatid']
    lang = transmitted_data['lang']
    custom_url = ''
    egg_find = None

    cl_name = 'Dino'
    dino_find = await Dino().create(oid)
    if not dino_find:
        egg_find = await Egg().create(oid)
        if egg_find:
            cl_name = 'Egg'

    if cl_name == 'Dino':
        element = await Dino().create(oid)
        if element:

            if element.profile['background_type'] == 'custom' and await premium(userid):
                custom_url = element.profile['background_id']

            if element.profile['background_type'] == 'saved':
                idm = element.profile['background_id']
                custom_url = await async_open(f'images/backgrounds/{idm}.png')

    if cl_name == 'Dino':
        element = await Dino().create(oid)
        if element:
            await dino_profile(userid, chatid, element, lang, custom_url)

    elif cl_name == 'Egg' and egg_find:
        element = await Egg().create(oid)
        await egg_profile(chatid, egg_find, lang)

@HDMessage
@main_router.message(Text('commands_name.dino_profile'), IsAuthorizedUser(), IsPrivateChat())
async def dino_handler(message: Message):
    userid = message.from_user.id
    lang = await get_lang(message.from_user.id)

    bstatus, status = await ChooseDinoHandler(transition, userid, message.chat.id, lang, send_error=False).start()

    if not bstatus and status == 'cancel':
        if await dead_check(userid):
            await bot.send_message(userid, t(f'p_profile.dialog', lang), reply_markup=inline_menu('dead_dialog', lang))
        else:
            await bot.send_message(userid, t(f'p_profile.no_dino_no_egg', lang))

@HDCallback
@main_router.callback_query(IsPrivateChat(), F.data.startswith('dino_profile'))
async def dino_profile_callback(call: types.CallbackQuery):
    dino_data = call.data.split()[1]

    userid = call.from_user.id
    chatid = call.message.chat.id
    lang = await get_lang(call.from_user.id)

    trans_data = {
        'userid': userid,
        'chatid': chatid,
        'lang': lang
    }
    dino = await Dino().create(dino_data)
    if dino:
        await transition(dino._id, trans_data)

# Обработчик кнопок профиля динозавра
@HDCallback
@main_router.callback_query(IsPrivateChat(), F.data.startswith('dino_menu'))
async def dino_menu(call: types.CallbackQuery):
    split_d = call.data.split()
    action = split_d[1]
    alt_key = split_d[2]

    userid = call.from_user.id
    chatid = call.message.chat.id
    lang = await get_lang(call.from_user.id)

    dino = await Dino().create(alt_key)
    if dino:
        res = await dino_owners.find_one({'dino_id': dino._id, 
                                    'owner_id': userid}, comment='dino_menu')
        if not res:
            await bot.send_message(userid, t('css.no_dino', lang), reply_markup=await m(userid, 'last_menu', lang))
            return

        if action == 'reset_activ_item':
            log('reset_activ_item - не определён функционал')

        elif action == 'mood_log':
           await send_mood_log(dino._id, lang, userid)

        elif action == 'joint_cancel':
            # Октазать от совместного динозавра
            text = t('cancle_joint.confirm', lang)
            await bot.send_message(userid, text, parse_mode='Markdown', reply_markup=confirm_markup(lang))

            await ChooseConfirmHandler(cnacel_joint, userid, chatid, lang, transmitted_data={'dinoid': dino._id}).start()

        elif action == 'my_joint_cancel':
            # Октазать от совместного динозавра
            text = t('my_joint.confirm', lang)
            await bot.send_message(userid, text, parse_mode='Markdown', reply_markup=confirm_markup(lang))

            await ChooseConfirmHandler(cnacel_myjoint, userid, chatid, lang, transmitted_data={
                'dinoid': dino._id, 
                'user': call.from_user.id}).start()

        elif action == 'kindergarten':
            if not await premium(userid): 
                text = t('no_premium', lang)
                await bot.send_message(userid, text)
            else:
                total, end = await check_hours(userid)
                hours = await hours_now(userid)
                text = t('kindergarten.info', lang,
                            hours_now=m_hours - total,
                            remained=total,
                            days=seconds_to_str(end - int(time()), lang, False, 'hour'),
                            hours=hours, remained_today=12
                            )

                if await check_status(dino._id) == 'kindergarten':
                    reply_buttons = list_to_inline([
                        {
                            t('kindergarten.cancel_name', lang): f'kindergarten stop {alt_key}'
                        }])
                else:
                    reply_buttons = list_to_inline([
                        {
                            t('kindergarten.button_name', lang): f'kindergarten start {alt_key}'
                        }])
                await bot.send_message(userid, text, parse_mode='Markdown', 
                                        reply_markup=reply_buttons)
        
        elif action == 'backgrounds_menu':
            await bot.send_message(chatid, t('menu_text.backgrounds_menu', lang), 
                        reply_markup= await m(userid, 'backgrounds_menu', lang))

        elif action == 'skills':
            await skills_profile(dino, lang, call.message)

        elif action == 'main_message':
            # Страница с информацией о динозавре
            custom_url = ''

            if dino:
                if dino.profile['background_type'] == 'custom' and await premium(userid):
                    custom_url = dino.profile['background_id']

                if dino.profile['background_type'] == 'saved':
                    idm = dino.profile['background_id']
                    custom_url = await async_open(f'images/backgrounds/{idm}.png')

                await dino_profile(userid, chatid, dino, lang, custom_url, 
                                    call.message)

        elif action == 'manage':
            await call.message.edit_reply_markup(
                reply_markup=await manage_markup(dino, userid, lang))

        elif action == 'accessories':
            ...


# Функции обработчиков кнопок
async def cnacel_joint(_:bool, transmitted_data:dict):
    userid = transmitted_data['userid']
    lang = transmitted_data['lang']
    dinoid = transmitted_data['dinoid']

    await dino_owners.delete_one({'dino_id': dinoid, 'owner_id': userid}, 
                                 comment='cnacel_joint')
    await bot.send_message(userid, '✅', 
                           reply_markup = await m(userid, 'last_menu', lang))

    await users.update_one({"userid": userid}, 
                           {"$set": {"settings.last_dino": None}}, 
                           comment='cnacel_joint')

async def cnacel_myjoint(_:bool, transmitted_data:dict):
    userid = transmitted_data['user']
    lang = transmitted_data['lang']
    dinoid = transmitted_data['dinoid']

    res = await dino_owners.find_one({'dino_id': dinoid, 'type': 'add_owner'}, comment='cnacel_myjoint')
    if res: 
        await dino_owners.delete_one({'_id': res['_id']}, 
                                     comment='cnacel_myjoint')
        myname_for_friend = await get_friend_data(res['owner_id'], userid)
        myname_for_friend = myname_for_friend['name']

        text = t("my_joint.m_for_add_owner", lang, username=myname_for_friend)
        await bot.send_message(res['owner_id'], text, 
                               reply_markup = await m(userid, 'last_menu', lang))

        await users.update_one({"userid": res['owner_id']}, 
                               {"$set": {"settings.last_dino": None}}, 
                               comment='cnacel_myjoint')

    await bot.send_message(userid, '✅', 
                           reply_markup = await m(userid, 'last_menu', lang))