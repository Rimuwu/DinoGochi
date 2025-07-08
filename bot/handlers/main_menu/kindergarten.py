
from aiogram import F, types
from bot.exec import main_router, bot

from bot.filters.private import IsPrivateChat
from bot.modules.data_format import list_to_keyboard
from bot.modules.decorators import HDCallback
from bot.modules.dinosaur.dino_status import check_status
from bot.modules.dinosaur.dinosaur import Dino
from bot.modules.dinosaur.kindergarten import check_hours, dino_kind, hours_now, minus_hours
from bot.modules.localization import get_lang, t
from bot.modules.states_fabric.state_handlers import ChooseOptionHandler
from bot.modules.markup import markups_menu as m


from bot.dbmanager import mongo_client
from bot.modules.overwriting.DataCalsses import DBconstructor
kindergarten_bd = DBconstructor(mongo_client.dino_activity.kindergarten)
dinosaurs = DBconstructor(mongo_client.dinosaur.dinosaurs)

@HDCallback
@main_router.callback_query(IsPrivateChat(), F.data.startswith('kindergarten'))
async def kindergarten(call: types.CallbackQuery):
    split_d = call.data.split()
    action = split_d[1]
    alt_key = split_d[2]

    userid = call.from_user.id
    chatid = call.message.chat.id
    lang = await get_lang(call.from_user.id)

    dino = await dinosaurs.find_one({'alt_id': alt_key}, comment='kindergarten_dino')
    if dino:
        if action == 'start':
            if await check_status(dino['_id']) == 'pass':
                all_h, end = await check_hours(userid)
                h = await hours_now(userid)

                if h < 12 and all_h:
                    options = {}

                    if 6 - h != 0:
                        options[f"1 {t('time_format.hour.0', lang)}"] = 1
                    if 6 - h >= 3:
                        options[f"3 {t('time_format.hour.1', lang)}"] = 3
                    if 6 - h == 6:
                        options[f"6 {t('time_format.hour.2', lang)}"] = 6

                    bb = list_to_keyboard([
                        list(options.keys()), [t('buttons_name.cancel', lang)]
                    ], 2)

                    await ChooseOptionHandler(start_kind, userid, chatid, lang, options,
                                              transmitted_data={'dino': dino['_id']}).start()
                    await bot.send_message(userid, t('kindergarten.choose_house', lang),
                                           reply_markup=bb)
                else:
                    await bot.send_message(userid, t('kindergarten.no_hours', lang))
            else:
                await bot.send_message(userid, t('alredy_busy', lang))

        elif action == 'stop':
            if await check_status(dino['_id']) == 'kindergarten':
                await kindergarten_bd.delete_one({'dinoid': dino['_id']}, comment='kindergarten_stop')
                await bot.send_message(userid, t('kindergarten.stop', lang))

async def start_kind(col, transmitted_data):
    chatid = transmitted_data['chatid']
    userid = transmitted_data['userid']
    lang = transmitted_data['lang']
    # dino = transmitted_data['dino']
    dino_id = transmitted_data['dino']
    dino = await Dino().create(dino_id)

    if dino is None:
        await bot.send_message(chatid, t('kindergarten.error', lang), 
                               reply_markup= await m(userid, 'last_menu', lang))
        return

    await minus_hours(userid, col)
    await dino_kind(dino_id, col)
    await bot.send_message(chatid, t('kindergarten.ok', lang), 
                           reply_markup= await m(userid, 'last_menu', lang))