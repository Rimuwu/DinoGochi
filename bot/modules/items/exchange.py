
from bson import ObjectId
from bot.dbmanager import mongo_client
from bot.exec import bot
from bot.modules.items.items import (AddItemToUser, 
                                     counts_items,
                                     ItemInBase)
from bot.modules.localization import t
from bot.modules.markup import (confirm_markup, count_markup,
                                 markups_menu)

from bot.modules.states_fabric.state_handlers import ChooseStepHandler
from bot.modules.states_fabric.steps_datatype import ConfirmStepData, FriendStepData, IntStepData, StepMessage

from bot.modules.overwriting.DataCalsses import DBconstructor

items = DBconstructor(mongo_client.items.items)

async def exchange(return_data: dict, transmitted_data: dict):
    item_id: ObjectId = transmitted_data['item_id'] 

    friend: dict = return_data['friend']
    count: int = return_data['count']
    userid: int = transmitted_data['userid']
    chatid: int = transmitted_data['chatid']
    lang: str = transmitted_data['lang']
    username: str = transmitted_data['username']

    item = ItemInBase()
    await item.link_for_id(item_id)

    if item.link_with_real_item:
        await item.minus(count)

        await AddItemToUser(friend['userid'], item.items_data, count)

        await bot.send_message(friend['userid'], t('exchange', lang, 
                            items=counts_items([item.item_id]*count, lang),username=username))

        await bot.send_message(chatid, t('exchange_me', lang),
                            reply_markup=await markups_menu(userid, 'last_menu', lang))

    else:
        ...


async def exchange_item(userid: int, chatid: int, item_id: ObjectId,
                        lang: str, username: str
                        ):

    item = ItemInBase()
    await item.link_for_id(item_id)

    max_count = item.count
    if max_count > 1000: max_count = 1000

    if item.link_with_real_item:

        steps = [
            ConfirmStepData('confirm', StepMessage(
                text=t('confirm_exchange', lang, name=item.items_data.name),
                translate_message=False,
                markup=confirm_markup(lang)
            )),
            IntStepData('count', StepMessage(
                text='css.wait_count',
                translate_message=True,
                markup=count_markup(max_count, lang)),
                autoanswer=False,
                max_int=max_count
            ),
            FriendStepData('friend', None,
                one_element=True
            )
        ]

        transmitted_data = {'item_id': item_id, 'username': username}
        await ChooseStepHandler(exchange, userid,
                                chatid, lang, steps,
                                transmitted_data).start()
