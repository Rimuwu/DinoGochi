
from bot.models.user import User
from bot.models.items import Item
from aiogram.types import InlineKeyboardMarkup

from bot.dbmanager import mongo_client
from bot.const import GAME_SETTINGS as GS
from bot.exec import bot
from bot.modules.data_format import escape_markdown, list_to_inline
from bot.modules.items.item import get_item_dict, item_code
from bot.modules.items.item_tools import AddItemToUser, use_item
from bot.modules.localization import get_data, t
from bot.models.dinosaur import Dino




def dialog_system(name: str, lang: str, 
                  key: str = 'start', end_keys: list | None = None, 
                  dialog_name: str = '', **kwargs):
    """ Основаная функция генерации текста для диалога, возвращает статус законченности, текст, клавиатуру, и последний обработанный ключ
    """
    if end_keys is None: end_keys = []

    text, markup = '', None

    end_status = False
    data = get_data('dialogs.' + dialog_name, lang)

    now_data = data[key]
    previous_data = {}

    user_name = escape_markdown(name)
    people_content: str = data[key]["text"].format(
        user_name = escape_markdown(name),
        people_name = data["people_name"],
        **kwargs
    )

    if 'previous' in now_data:
        previous_data = data[now_data['previous']]

    if previous_data:
        answer = previous_data['buttons'][key]['answer']
        text += f'👥 <b>{user_name}</b>: - {answer}'

    if now_data.get('system', False):
        text += f'\n\n{people_content}'
    else:
        text += f'\n<b>{data["people_name"]}</b>: - {people_content}'

    if data[key].get('buttons', {}):
        buttons = {}
        for i_key, item in data[key]['buttons'].items():
            buttons[item['text']] = f'dialog {dialog_name} {i_key}'
        markup = list_to_inline([buttons], 2)

    if key in end_keys: end_status = True
    return end_status, text, markup, key

async def dead_last_dino(userid: int, name: str, lang: str, 
                   key: str = 'start'):
    end_keys = ['end-y', 'end-n']
    dialog_name = 'dead_last_dino'

    markup = None
    status = False
    text = ''

    user = await User.find_one(User.userid == userid)
    if user:

        if await Dino.dead_check(userid):
            status = True
            dead_dinos = await user.get_dead_dinos()
            dead_count = len(dead_dinos)

            end_status, text, markup, end_key = dialog_system(
                name, lang, key, end_keys, dialog_name, dead_dinos_count=dead_count)

            if end_status:
                if end_key == "end-y":
                    coins = (user.coins // 100) * 80
                else:
                    coins = (user.coins // 100) * 70

                await user.remove_coins(coins)
                await Item.find(Item.owner_id == userid).delete()

                await AddItemToUser(userid, GS['dead_dialog_item'], 1,
                                    {'interact': False})
                item_egg_data = get_item_dict(
                    GS['dead_dialog_item'], {'interact': False})

                await use_item(userid, userid, lang, item_egg_data, 1)

    return status, text, markup

dialogs = {
    'dead_last_dino': dead_last_dino
}