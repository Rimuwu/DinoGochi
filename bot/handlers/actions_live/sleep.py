from time import time

from telebot.types import Message

from bot.config import mongo_client
from bot.exec import bot
from bot.modules.items.accessory import check_accessory
from bot.modules.user.advert import auto_ads
from bot.modules.data_format import list_to_keyboard, seconds_to_str
from bot.modules.dinosaur.dinosaur  import Dino, check_status, end_sleep, set_status, start_sleep
from bot.modules.inline import inline_menu
from bot.modules.localization import get_data, t, get_lang
from bot.modules.markup import markups_menu as m
from bot.modules.dinosaur.mood import add_mood
from bot.modules.states_tools import ChooseIntState, ChooseOptionState
from bot.modules.user.user import User
from bot.modules.decorators import HDMessage
 
from bot.modules.overwriting.DataCalsses import DBconstructor
dinosaurs = DBconstructor(mongo_client.dinosaur.dinosaurs)
long_activity = DBconstructor(mongo_client.dino_activity.long_activity)

async def short_sleep(number: int, transmitted_data: dict):
    """ Отправляем в которкий сон
    """
    userid = transmitted_data['userid']
    lang = transmitted_data['lang']
    chatid = transmitted_data['chatid']
    dino: Dino = transmitted_data['last_dino']

    res_dino_status = await check_status(dino._id)
    if res_dino_status:
        if res_dino_status != 'pass':
            await bot.send_message(chatid, t('alredy_busy', lang), reply_markup= await m(userid, 'last_menu', lang))
            return

    await check_accessory(dino, 'bear', True)
    await start_sleep(dino._id, 'short', number * 60)
    message = await bot.send_message(chatid, 
                t('put_to_bed.sleep', lang),
                reply_markup= await m(userid, 'last_menu', lang, True)
                )
    await auto_ads(message)

async def long_sleep(dino: Dino, userid: int, lang: str):
    """ Отправляем дино в длинный сон
    """

    res_dino_status = await check_status(dino._id)
    if res_dino_status:
        if res_dino_status != 'pass':
            await bot.send_message(userid, t('alredy_busy', lang), reply_markup= await m(userid, 'last_menu', lang))
            return

    await start_sleep(dino._id, 'long')
    message = await bot.send_message(userid, 
                t('put_to_bed.sleep', lang),
                reply_markup= await m(userid, 'last_menu', lang, True)
                )
    await auto_ads(message)

async def end_choice(option: str, transmitted_data: dict):
    """Функция обработки выбора варианта (длинный или короткий сон)
    """
    userid = transmitted_data['userid']
    lang = transmitted_data['lang']
    chatid = transmitted_data['chatid']
    last_dino = transmitted_data['last_dino']

    if await last_dino.status == 'pass':
        if option == 'short':
            # Если короткий, то спрашиваем сколько дино должен спать
            cancel_button = t('buttons_name.cancel', lang)
            buttons = list_to_keyboard([cancel_button])
            transmitted_data = { 
                    'last_dino': last_dino
                }
            await ChooseIntState(short_sleep, userid, 
                                chatid, lang, min_int=5, max_int=480, transmitted_data=transmitted_data)

            await bot.send_message(userid, 
                                t('put_to_bed.choice_time', lang), 
                                reply_markup=buttons)

        elif option == 'long':
            await long_sleep(last_dino, userid, lang)

    else:
        await bot.send_message(userid, t('alredy_busy', lang),
            reply_markup=inline_menu('dino_profile', lang, 
            dino_alt_id_markup=last_dino.alt_id))

@bot.message_handler(pass_bot=True, text='commands_name.actions.put_to_bed', dino_pass=True)
@HDMessage
async def put_to_bed(message: Message):
    """Уложить спать динозавра
    """
    userid = message.from_user.id
    lang = await get_lang(message.from_user.id)
    chatid = message.chat.id

    user = await User().create(userid)
    last_dino = await user.get_last_dino()

    if last_dino:
        if last_dino.stats['energy'] >= 90:
            await bot.send_message(message.chat.id, 
                                    t('put_to_bed.dont_want', lang)
                                    )
        else:
            if not await check_accessory(last_dino, 'bear'):
                # Если нет мишки, то просто длинный сон
                await long_sleep(last_dino, userid, lang)
            else:
                # Даём выбор сна
                sl_buttons = get_data('put_to_bed.buttons', lang).copy()
                cancel_button = t('buttons_name.cancel', lang)
                sl_buttons.append(cancel_button)

                buttons = list_to_keyboard(sl_buttons, 2, one_time_keyboard=True)
                options = {
                    sl_buttons[0][0]: 'long',
                    sl_buttons[0][1]: 'short'
                }
                trans_data = { 
                    'last_dino': last_dino
                }

                await ChooseOptionState(end_choice, userid, chatid, lang, options, trans_data) # Ожидаем выбор варианта
                await bot.send_message(userid, 
                        t('put_to_bed.choice', lang), 
                        reply_markup=buttons)
    else:
        await bot.send_message(userid, t('edit_dino_button.notfouned', lang),
                reply_markup= await m(userid, 'last_menu', lang))

@bot.message_handler(pass_bot=True, text='commands_name.actions.awaken')
@HDMessage
async def awaken(message: Message):
    """Пробуждение динозавра
    """
    userid = message.from_user.id
    lang = await get_lang(message.from_user.id)
    chatid = message.chat.id

    user = await User().create(userid)
    last_dino = await user.get_last_dino()

    if last_dino:
        if await last_dino.status == 'sleep':
            sleeper = await long_activity.find_one({'dino_id': last_dino._id,
            'activity_type': 'sleep'}, comment='awaken_sleeper')
            if sleeper:
                if sleeper['sleep_type'] == 'long':
                    sleep_time = int(time()) - sleeper['sleep_start']
                    healthy_sleep = 6 * 3600 # Время здорового сна

                    if sleep_time >= healthy_sleep \
                        or last_dino.stats['energy'] == 100:

                        await end_sleep(last_dino._id, sleep_time)
                    else:
                        # Если динозавр в долгом сне проспал меньше 6-ми часов, то штраф
                        await add_mood(last_dino._id, 'bad_sleep', -1, 10800)
                        await end_sleep(last_dino._id, sleep_time, False)

                        await bot.send_message(chatid, 
                                               t('awaken.down_mood', lang, 
                                                 time_end=seconds_to_str(sleep_time, lang)),
                                               reply_markup= await m(userid, 'last_menu', lang))
                elif sleeper['sleep_type'] == 'short':
                    sleep_time = sleeper['sleep_end'] - sleeper['sleep_start']
                    await end_sleep(last_dino._id, sleep_time, False)
            else:
                await set_status(last_dino._id, 'pass')
                await bot.send_message(chatid, t('awaken.not_sleep', lang),
                reply_markup= await m(userid, 'last_menu', lang))
        else:
            await bot.send_message(chatid, t('awaken.not_sleep', lang),
                reply_markup= await m(userid, 'last_menu', lang))
    else:
        await bot.send_message(chatid, t('edit_dino_button.notfouned', lang),
                reply_markup= await m(userid, 'last_menu', lang))

    await auto_ads(message)