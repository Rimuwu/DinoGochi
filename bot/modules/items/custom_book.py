



from bot.modules.items.items import ItemInBase
from bot.modules.localization import t
from bot.modules.markup import confirm_markup, markups_menu
from bot.modules.states_fabric.state_handlers import ChooseConfirmHandler
from bot.exec import bot

from bot.dbmanager import mongo_client
from bot.modules.overwriting.DataCalsses import DBconstructor
items = DBconstructor(mongo_client.items.items)

async def edit_custom_book_confirm(_: bool, transmitted_data: dict):
    """ Функция редактирует кастомную книгу
    """
    userid = transmitted_data['userid']
    chatid = transmitted_data['chatid']
    lang = transmitted_data['lang']

    item_id = transmitted_data['item_id']
    content = transmitted_data['content']

    item = ItemInBase()
    await item.link_for_id(item_id)

    item.items_data.abilities['content'] = content
    item.items_data.abilities['author'] = userid
    await item.update()

    await bot.send_message(chatid, '✅', 
            reply_markup=await markups_menu(userid, 'last_menu', lang))


async def edit_custom_book(return_data: dict, transmitted_data: dict):
    """ Функция редактирует кастомную книгу
    """
    userid = transmitted_data['userid']
    chatid = transmitted_data['chatid']
    lang = transmitted_data['lang']

    transmitted_data['content'] = return_data['content']

    await ChooseConfirmHandler(
        edit_custom_book_confirm, userid, chatid, lang, True, 
        transmitted_data=transmitted_data).start()

    await bot.send_message(chatid, t('custom_book.confirm_edit', lang),
                           reply_markup=confirm_markup(lang))