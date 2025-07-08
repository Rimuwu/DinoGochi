from bson import ObjectId
from bot.dbmanager import mongo_client
from bot.const import GAME_SETTINGS
from bot.exec import main_router, bot
from bot.modules.dinosaur.dino_status import end_collecting, start_collecting
from bot.modules.dinosaur.mood import repeat_activity
# from bot.modules.items.accessory import check_accessory
from bot.modules.user.advert import auto_ads
from bot.modules.data_format import list_to_inline, list_to_keyboard
from bot.modules.decorators import HDCallback, HDMessage
from bot.modules.dinosaur.dinosaur  import Dino, check_status
from bot.modules.images import dino_collecting
from bot.modules.items.item import counts_items
from bot.modules.localization import get_data, get_lang, t
from bot.modules.markup import count_markup
from bot.modules.markup import markups_menu as m
from bot.modules.overwriting.DataCalsses import DBconstructor
from bot.modules.quests import quest_process
from bot.modules.states_fabric.state_handlers import ChooseStepHandler
from bot.modules.states_fabric.steps_datatype import IntStepData, OptionStepData, StepMessage

from bot.modules.user.user import User, count_inventory_items, max_eat
from aiogram.types import CallbackQuery, Message

from bot.filters.translated_text import StartWith, Text
from bot.filters.status import DinoPassStatus
from bot.filters.private import IsPrivateChat
from bot.filters.authorized import IsAuthorizedUser
from aiogram import F

dinosaurs = DBconstructor(mongo_client.dinosaur.dinosaurs)
long_activity = DBconstructor(mongo_client.dino_activity.long_activity)

async def collecting_adapter(return_data, transmitted_data):
    dino_id: ObjectId = transmitted_data['dino']
    count: int = return_data['count']
    option = return_data['option']
    chatid = transmitted_data['chatid']
    userid = transmitted_data['userid']
    lang = transmitted_data['lang']
    
    dino = await Dino().create(dino_id)
    if not dino:
        await bot.send_message(chatid, t('css.no_dino', lang), reply_markup=await m(userid, 'last_menu', lang))
        return

    eat_count = await count_inventory_items(userid, ['eat'])
    if eat_count + count > await max_eat(userid):

        text = t(f'collecting.max_count', lang,
                eat_count=eat_count,
                add_count=count,
                max_c=await max_eat(userid)
                )
        await bot.send_message(chatid, text, reply_markup= await m(
            userid, 'last_menu', lang))
    else:
        res_dino_status = await check_status(dino._id)
        if res_dino_status:
            if res_dino_status != 'pass':
                await bot.send_message(chatid, t('alredy_busy', lang), reply_markup= await m(userid, 'last_menu', lang))
                return

            await start_collecting(dino._id, userid, option, count)
            # await check_accessory(dino, 'basket', True)
            percent, _ = await dino.memory_percent('action', f'collecting.{option}', True)
            await repeat_activity(dino._id, percent)

            image = await dino_collecting(dino.data_id, option)
            text = t(f'collecting.result.{option}', lang,
                    dino_name=dino.name, count=count)
            stop_button = t(f'collecting.stop_button.{option}', lang)
            markup = list_to_inline([
                {stop_button: f'collecting stop {dino.alt_id}'}])

            await bot.send_photo(chatid, image, caption=text, reply_markup=markup)
            message = await bot.send_message(chatid, t('back_text.actions_menu', lang),
                                        reply_markup = await m(userid, 'last_menu', lang)
                                        )

            await auto_ads(message)

@HDMessage
@main_router.message(
    IsPrivateChat(), 
    StartWith('commands_name.actions.collecting'),
    DinoPassStatus()
)
async def collecting_button(message: Message):
    if message.from_user:
        userid = message.from_user.id
        chatid = message.chat.id

        user = await User().create(userid)
        lang = await user.lang
        last_dino = await user.get_last_dino()

        if last_dino:
                if await user.premium:
                    max_count = GAME_SETTINGS['premium_max_collecting']
                else: max_count = GAME_SETTINGS['max_collecting']

                # have_basket = await check_accessory(last_dino, 'basket')
                # if have_basket: max_count += 20

                data_options = get_data('collecting.buttons', lang)
                options = dict(zip(data_options.values(), data_options.keys()))
                markup = list_to_keyboard([list(data_options.values()), 
                                        [t('buttons_name.cancel', lang)]], 2)

                steps = [
                    OptionStepData('option', 
                                StepMessage('collecting.way', markup, True),
                                options=options
                                ),
                    IntStepData('count', 
                                StepMessage('collecting.wait_count',
                                   count_markup(max_count, lang), True),
                                max_int=max_count,
                                )
                ]
                await ChooseStepHandler(collecting_adapter, userid, chatid,
                                        lang, steps, 
                                        transmitted_data={'dino': last_dino._id}
                                    ).start()

@HDMessage
@main_router.message(IsPrivateChat(), Text('commands_name.actions.progress'))
async def collecting_progress(message: Message):
    if message.from_user:
        userid = message.from_user.id
        chatid = message.chat.id

        user = await User().create(userid)
        lang = await user.lang
        last_dino = await user.get_last_dino()
        if last_dino:
            
            data = await long_activity.find_one({'dino_id': last_dino._id, 
                                                'activity_type': 'collecting'},
                                                comment="collecting_progress_data")
            if data:
                stop_button = t(
                    f'collecting.stop_button.{data["collecting_type"]}', lang)

                image = await dino_collecting(last_dino.data_id, data["collecting_type"])
                text = t(f'collecting.progress.{data["collecting_type"]}', lang,
                        now = data['now_count'], max_count=data['max_count']
                        )

                await bot.send_photo(chatid, image, caption=text, 
                                    reply_markup=list_to_inline(
                                    [{stop_button: f'collecting stop {last_dino.alt_id}'}]
                                        ))
            else:
                await bot.send_message(chatid, '❌',
                            reply_markup = await m(userid, 'last_menu', lang))

@HDCallback
@main_router.callback_query(IsPrivateChat(), F.data.startswith('collecting'), IsAuthorizedUser())
async def collecting_callback(callback: CallbackQuery):
    if callback.data:
        dino_data = callback.data.split()[2]
        action = callback.data.split()[1]

        lang = await get_lang(callback.from_user.id)

        dino = await Dino().create(dino_data)
        if not dino:
            await bot.send_message(callback.from_user.id, t('css.no_dino', lang), reply_markup=await m(callback.from_user.id, 'last_menu', lang))
            return
        data = await long_activity.find_one({'dino_id': dino._id, 
                                            'activity_type': 'collecting'},
                                            comment="collecting_callback")
        if data and dino and data:
            items_list = []
            for key, count in data['items'].items():
                items_list += [key] * count

            items_names = counts_items(items_list, lang)

            if action == 'stop':
                await end_collecting(dino._id, 
                                    data['items'], data['sended'], 
                                    items_names)
                await quest_process(data['sended'], data['collecting_type'], 
                            data['now_count'])