from bot.models.items import Item
from bson import ObjectId
from bot.exec import main_router, bot
from bot.filters.private import IsPrivateChat
from bot.models.dinosaur import Dino
from bot.modules.items.item import get_data as get_item_data
from bot.modules.items.item import get_name
from bot.modules.items.item_tools import use_item
from bot.modules.localization import get_lang, t
from bot.modules.markup import feed_count_markup
from bot.modules.markup import markups_menu as m
from bot.modules.states_fabric.state_handlers import ChooseInventoryHandler, ChooseStepHandler
from bot.modules.states_fabric.steps_datatype import DataType, IntStepData, StepMessage
from bot.modules.user.user import User
from aiogram.types import CallbackQuery, Message

from bot.filters.translated_text import Text
from aiogram import F
from aiogram.filters import Command

async def adapter_function(return_dict, transmitted_data):
    count = return_dict['count']
    item = transmitted_data['item']
    userid = transmitted_data['userid']
    chatid = transmitted_data['chatid']
    dino_id = transmitted_data['dino']
    lang = transmitted_data['lang']

    dino = await Dino().create(dino_id)
    if not dino:
        await bot.send_message(chatid, t('css.no_dino', lang), 
        reply_markup = await m(userid, 'last_menu', lang))
        return

    send_status, return_text = await use_item(
        userid, chatid, lang, item, count, dino)

    if send_status:
        await bot.send_message(chatid, return_text, parse_mode='Markdown', 
                               reply_markup= await m(userid, 'last_menu', lang))

        from bot.modules.tutorial import advance_tutorial_if_step
        await advance_tutorial_if_step(userid, chatid, lang, bot, expected_step="feed_wait")

async def inventory_adapter(item, transmitted_data):
    userid = transmitted_data['userid']
    chatid = transmitted_data['chatid']
    lang = transmitted_data['lang']
    dino_id: ObjectId = transmitted_data['dino']

    dino = await Dino().create(dino_id)
    if not dino:
        await bot.send_message(chatid, t('css.no_dino', lang), reply_markup=await m(userid, 'last_menu', lang))
        return

    transmitted_data['item'] = item

    limiter = 100 # Ограничение по количеству использований за раз
    item_data = get_item_data(item['item_id'])
    item_name = get_name(item['item_id'], lang, item.get('abilities', {}))

    abilities = item.get('abilities', {})
    from bot.modules.items.item import get_item_dict
    item_dict = get_item_dict(item['item_id'], abilities)
    user_obj = await User.find_one(User.userid == userid)
    if not user_obj:
        return

    if not abilities:
        base_item = await Item.find_one(
            Item.owner.id == user_obj.id,
            Item.items_data.item_id == item['item_id'],
            {
                "$or": [
                    {"items_data.abilities": {"$exists": False}},
                    {"items_data.abilities": {}}
                ]
            }
        )
        all_items = await Item.find(
            Item.owner.id == user_obj.id,
            Item.items_data.item_id == item['item_id'],
            {
                "$or": [
                    {"items_data.abilities": {"$exists": False}},
                    {"items_data.abilities": {}}
                ]
            }
        ).to_list()
    else:
        base_item = await Item.find_one(Item.owner.id == user_obj.id, Item.items_data == item_dict)
        all_items = await Item.find(Item.owner.id == user_obj.id, Item.items_data == item_dict).to_list()

    if base_item:
        max_count = 0
        for i in all_items:
            if 'abilities' in i.items_data.keys() and 'uses' in i.items_data['abilities']:
                max_count += i.items_data['abilities']['uses']
            else:
                max_count += i.count
            if max_count >= limiter: break

        if max_count > limiter: max_count = limiter

        percent = 1
        age = await dino.age()
        if age.days >= 10:
            percent, repeat = await dino.memory_percent('eat', item['item_id'], False)

        steps: list[DataType] = [
            IntStepData('count', max_int=max_count, autoanswer=False,
                message=StepMessage('css.wait_count', 
                feed_count_markup(
                    dino.stats['eat'], int(item_data['act'] * percent), 
                    max_count, item_name, lang), True)
            )
        ]

        await ChooseStepHandler(
            adapter_function, userid, chatid, lang, steps,
            transmitted_data=transmitted_data
        ).start()

@main_router.message(IsPrivateChat(), Text('commands_name.actions.feed'))
@main_router.message(IsPrivateChat(), Command(commands=['feed']))
async def feed(message: Message):
    if message.from_user:
        userid = message.from_user.id
        lang = await get_lang(message.from_user.id)
        chatid = message.chat.id
        user = await User().create(userid)

        last_dino = await user.get_last_dino()

        if not last_dino:
            await bot.send_message(chatid, t('css.no_dino', lang), 
            reply_markup = await m(userid, 'last_menu', lang))
            return

        transmitted_data = {
            'chatid': chatid,
            'lang': lang,
            'dino': last_dino._id
        }
        dino_status = await last_dino.status
        if dino_status == 'sleep':
            await bot.send_message(chatid, t('item_use.eat.sleep', lang), reply_markup = await m(userid, 'last_menu', lang))
            return
        elif dino_status == 'journey':
            await bot.send_message(chatid, t('item_use.eat.journey', lang), reply_markup = await m(userid, 'last_menu', lang))
            return
        else:
            await ChooseInventoryHandler(
                inventory_adapter, userid, chatid, lang, ['eat'], changing_filters=False, transmitted_data=transmitted_data
            ).start()

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
                await bot.send_message(chatid, t('css.no_dino', lang), reply_markup = await m(userid, 'last_menu', lang))
                return

            dino_status = await dino_d.status
            if dino_status == 'sleep':
                await bot.send_message(chatid, t('item_use.eat.sleep', lang), reply_markup = await m(userid, 'last_menu', lang))
                return
            elif dino_status == 'journey':
                await bot.send_message(chatid, t('item_use.eat.journey', lang), reply_markup = await m(userid, 'last_menu', lang))
                return

            transmitted_data = {
                'chatid': chatid,
                'lang': lang,
                'dino': dino_d._id
            }

            await ChooseInventoryHandler(
                inventory_adapter, userid, chatid, lang, ['eat'], changing_filters=False, transmitted_data=transmitted_data
            ).start()