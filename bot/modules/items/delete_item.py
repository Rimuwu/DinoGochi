


from bson import ObjectId
from bot.exec import bot
from bot.modules.localization import t
from bot.modules.markup import confirm_markup, count_markup, markups_menu
from bot.modules.states_fabric.state_handlers import ChooseStepHandler
from bot.modules.states_fabric.steps_datatype import ConfirmStepData, IntStepData, StepMessage
from bot.modules.items.item import ItemInBase


async def delete_action(return_data: dict, transmitted_data: dict):
    userid = transmitted_data['userid']
    chatid = transmitted_data['chatid']
    lang = transmitted_data['lang']
    count = return_data['count']

    item_id = transmitted_data['item_id']
    item_name = transmitted_data['item_name']

    item = ItemInBase()
    await item.link_for_id(item_id)

    try:
        await item.minus(count)
        res = True
    except ValueError:
        res = False

    if res:
        await bot.send_message(chatid, t('delete_action.delete', lang,  
                                         name=item_name, count=count), 
                               reply_markup=
                               await markups_menu(userid, 'last_menu', lang))
    else:
        await bot.send_message(chatid, t('delete_action.error', lang), 
                               reply_markup=
                               await markups_menu(userid, 'last_menu', lang))

async def delete_item_action(userid: int, chatid:int, 
                             item_id: ObjectId, lang: str):
    item = ItemInBase()
    await item.link_for_id(item_id)

    if item.link_with_real_item:
        transmitted_data = {'item_id': item_id, 
                            'item_name': item.items_data.name}

        steps = [
            ConfirmStepData('confirm', StepMessage(
                text=t('css.delete', lang, name=item.items_data.name),
                translate_message=False,
                markup=confirm_markup(lang)),
                cancel=True
            ),
            IntStepData('count', StepMessage(
                text='css.wait_count',
                translate_message=True,
                markup=count_markup(item.count, lang)),
                max_int=item.count
            )
        ]

        await ChooseStepHandler(delete_action, userid, chatid, lang, steps,
                                transmitted_data=transmitted_data).start()

    else:
        await bot.send_message(chatid, t('delete_action.error', lang), 
                               reply_markup=
                               await markups_menu(userid, 'last_menu', lang))
