from aiogram.types import InlineKeyboardMarkup

from bot.dbmanager import mongo_client
from bot.const import GAME_SETTINGS as GS
from bot.exec import bot
from bot.modules.data_format import escape_markdown, list_to_inline
from bot.modules.images import create_eggs_image
from bot.modules.items.item import get_item_dict, item_code
from bot.modules.items.item_tools import AddItemToUser
from bot.modules.localization import get_data, t
from bot.modules.dinosaur.dinosaur  import dead_check

from bot.modules.overwriting.DataCalsses import DBconstructor
from bot.modules.user.user import take_coins
users = DBconstructor(mongo_client.user.users)
items = DBconstructor(mongo_client.items.items)

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
        text += f'👥 *{user_name}*: - {answer}'

    if now_data.get('system', False):
        text += f'\n\n{people_content}'
    else:
        text += f'\n*{data["people_name"]}*: - {people_content}'

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

    user = await users.find_one({'userid': userid}, comment='dead_last_dino_user')
    if user:

        if await dead_check(userid):
            status = True

            end_status, text, markup, end_key = dialog_system(
                name, lang, key, end_keys, dialog_name)

            if end_status:
                if end_key == "end-y":
                    coins = (user['coins'] // 100) * 80
                else:
                    coins = (user['coins'] // 100) * 70

                await take_coins(userid, -coins, True)
                await items.delete_many({'owner_id': userid}, comment='dead_last_dino')

                code_res, ins_id = await AddItemToUser(userid, GS['dead_dialog_item'], 1, {'interact': False})

                buttons = {}
                image, eggs = await create_eggs_image()
                code = await item_code(item_id=ins_id)

                for i in range(3):
                    buttons[f'🥚 {i+1}'] = f'item egg {code} {eggs[i]}'
                buttons = list_to_inline([buttons])

                await bot.send_photo(userid, image, 
                                    caption=t('item_use.egg.egg_answer', lang), 
                                    parse_mode='Markdown', reply_markup=buttons)

    return status, text, markup

dialogs = {
    'dead_last_dino': dead_last_dino
}