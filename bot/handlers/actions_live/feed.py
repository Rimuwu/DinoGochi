import re
from bson import ObjectId
from bot.dbmanager import mongo_client
from bot.exec import main_router, bot
from bot.filters.private import IsPrivateChat
from bot.modules.decorators import HDCallback, HDMessage
from bot.modules.dinosaur.dinosaur  import Dino
# from bot.modules.inventory_tools import start_inv
from bot.modules.items.item import ItemData, ItemInBase
from bot.modules.items.item import get_name
from bot.modules.items.json_item import Eat
from bot.modules.items.use_item import use_item
from bot.modules.localization import get_lang, t
from bot.modules.markup import feed_count_markup
from bot.modules.markup import markups_menu as m
from bot.modules.overwriting.DataCalsses import DBconstructor

from bot.modules.states_fabric.state_handlers import ChooseIntHandler, ChooseInventoryHandler, ChooseStepHandler
from bot.modules.states_fabric.steps_datatype import DataType, IntStepData, StepMessage
from bot.modules.user.user import User
from aiogram.types import CallbackQuery, Message

from bot.filters.translated_text import Text
from aiogram import F

from aiogram.fsm.context import FSMContext

items = DBconstructor(mongo_client.items.items)

async def adapter_function(return_dict, transmitted_data):
    count = return_dict['count']
    item_id: ObjectId = transmitted_data['item_id']
    userid = transmitted_data['userid']
    chatid = transmitted_data['chatid']
    dino_id = transmitted_data['dino']
    lang = transmitted_data['lang']

    dino = await Dino().create(dino_id)
    if not dino:
        await bot.send_message(chatid, t('css.no_dino', lang), reply_markup=await m(userid, 'last_menu', lang))
        return

    send_status, return_text = await use_item(chatid, lang, item_id, count, dino)
    if send_status:
        await bot.send_message(chatid, return_text, parse_mode='Markdown', 
                               reply_markup = await m(userid, 'last_menu', lang))

async def inventory_adapter(item_id: ObjectId, transmitted_data):
    userid = transmitted_data['userid']
    chatid = transmitted_data['chatid']
    lang = transmitted_data['lang']
    dino_id: ObjectId = transmitted_data['dino']
    transmitted_data['item_id'] = item_id

    dino = await Dino().create(dino_id)
    if not dino:
        await bot.send_message(chatid, t('css.no_dino', lang), reply_markup=await m(userid, 'last_menu', lang))
        return

    item = await ItemInBase().link_for_id(item_id)
    if not isinstance(item.items_data.data, Eat): return

    limiter = 100 # Ограничение по количеству использований за раз 
    item_name = item.items_data.name(lang=lang)

    if item.link_with_real_item:
        if item.count > limiter: max_count = limiter

        percent = 1
        age = await dino.age()
        if age.days >= 10:
            percent, repeat = await dino.memory_percent('eat', item.item_id, False)

        steps: list[DataType] = [
            IntStepData('count', max_int=max_count, autoanswer=False,
                        message=StepMessage('css.wait_count', 
                                feed_count_markup(dino.stats['eat'], int(item.items_data.data.act * percent), max_count, item_name, lang), True))
        ]

        await ChooseStepHandler(
            adapter_function, userid, chatid, lang, steps,
            transmitted_data=transmitted_data
        ).start()

@HDMessage
@main_router.message(IsPrivateChat(), Text('commands_name.actions.feed'))
async def feed(message: Message):
    if message.from_user:
        userid = message.from_user.id
        lang = await get_lang(message.from_user.id)
        chatid = message.chat.id
        user = await User().create(userid)
        
        last_dino = await user.get_last_dino()
        
        if not last_dino:
            await bot.send_message(chatid, t('css.no_dino', lang), reply_markup=await m(userid, 'last_menu', lang))
            return

        transmitted_data = {
            'chatid': chatid,
            'lang': lang,
            'dino': last_dino._id
        }
        if await last_dino.status != 'sleep':
            await ChooseInventoryHandler(
                inventory_adapter, userid, chatid, lang, ['eat'], changing_filters=False, transmitted_data=transmitted_data,
                return_objectid=True
            ).start()

        else:
            await bot.send_message(chatid, t('item_use.eat.sleep', lang), reply_markup=await m(userid, 'last_menu', lang))
            return

@HDCallback
@main_router.callback_query(IsPrivateChat(), F.data.startswith('feed_inl'))
async def feed_inl(callback: CallbackQuery):
    if callback.message:
        lang = await get_lang(callback.from_user.id)
        chatid = callback.message.chat.id

        if callback.data:
            alt_id = callback.data.split()[1]
            userid = callback.from_user.id
            
            dino_d = await Dino().create(alt_id)
            if not dino_d:
                await bot.send_message(chatid, t('css.no_dino', lang), reply_markup=await m(userid, 'last_menu', lang))
                return

            transmitted_data = {
                'chatid': chatid,
                'lang': lang,
                'dino': dino_d._id
            }

            await ChooseInventoryHandler(
                inventory_adapter, userid, chatid, lang, ['eat'], changing_filters=False, transmitted_data=transmitted_data,
                return_objectid=True
            ).start()