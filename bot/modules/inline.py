from telebot.types import InlineKeyboardButton, InlineKeyboardMarkup

from bot.modules.data_format import list_to_inline
from bot.modules.item import counts_items
from bot.modules.item import get_data as get_item_data
from bot.modules.item import get_item_dict, get_name, item_code
from bot.modules.localization import get_data as get_loc_data
from bot.modules.localization import t
from bot.modules.logs import log


def inline_menu(markup_data, lang: str = 'en', **kwargs):
    markup_inline = InlineKeyboardMarkup()
    text, callback = '-', '-'
    standart_keys = get_loc_data('inline_menu', lang)
    # 'dino_profile', 'dino_rename' # dino_alt_id_markup
    # 'send_request' # userid

    if type(markup_data) == str: markup_data = [markup_data]

    for markup_key in markup_data:
        if markup_key in standart_keys:
            text = t(f'inline_menu.{markup_key}.text', lang, **kwargs)
            callback = t(f'inline_menu.{markup_key}.callback', lang, **kwargs)

        else:
            log(prefix='InlineMarkup', 
                message=f'not_found_key Data: {markup_key}', lvl=2)

        markup_inline.add(
            InlineKeyboardButton(text=text, callback_data=callback))
    return markup_inline

def item_info_markup(item: dict, lang):
    item_data = get_item_data(item['item_id'])
    loc_data = get_loc_data('item_info.static.buttons', lang)
    code = item_code(item)
    buttons_dict = {}

    if item_data['type'] not in ['material', 'ammunition', 'dummy']:
        buttons_dict[loc_data['use'][item_data['type']]] = f'item use {code}'

    if not('abilities' in item and 'interact' in item['abilities'] and not(item['abilities']['interact'])):
        buttons_dict[loc_data['delete']] = f'item delete {code}'

        if 'cant_sell' not in item_data or ('cant_sell' in item_data and not item_data['cant_sell']):
            buttons_dict[loc_data['exchange']] = f'item exchange {code}'

    markup_inline = list_to_inline([buttons_dict], 2)

    if 'buyer' not in item_data or (item_data['buyer'] == True):
        # Скупщик

        markup_inline.add(
                InlineKeyboardButton(text=loc_data['buyer'],
                            callback_data=f'buyer {code}')
                )

    if item_data['type'] == 'recipe':
        for item_cr in item_data['create']:
            data = get_item_dict(item_cr['item'])
            name = loc_data['created_item'].format(
                        item=get_name(item_cr['item'], lang))

            markup_inline.add(InlineKeyboardButton(text=name,
                        callback_data=f'item info {item_code(data)}'))

    if 'ns_craft' in item_data:
        for cr_dct_id in item_data['ns_craft'].keys():
            bt_text = ''
            cr_dct = item_data['ns_craft'][cr_dct_id]

            bt_text += counts_items(cr_dct['materials'], lang)
            bt_text += ' = '
            bt_text += counts_items(cr_dct['create'], lang)

            markup_inline.add(
                InlineKeyboardButton(text=bt_text,
                            callback_data=f'ns_craft {code} {cr_dct_id}')
                )

    return markup_inline

def dino_profile_markup(add_acs_button: bool, lang: str, 
                        alt_id: str, joint_dino: bool, my_joint: bool):
    # Инлайн меню с быстрыми действиями. Например как снять аксессуар
    # joint_dino - Отказаться от динозавра
    # my_joint - Отменить второго владельца

    buttons = {}
    rai = get_loc_data('p_profile.inline_menu', lang)

    if add_acs_button:
        buttons[rai['reset_activ_item']['text']] = \
        rai['reset_activ_item']['data']

    buttons[rai['mood_log']['text']] = rai['mood_log']['data']
    if joint_dino: 
        buttons[rai['joint_dino']['text']] = rai['joint_dino']['data']
    if my_joint: 
        buttons[rai['my_joint']['text']] = rai['my_joint']['data']

    buttons[rai['kindergarten']['text']] = rai['kindergarten']['data']

    for but in buttons: buttons[but] = buttons[but].format(dino=alt_id)
    return list_to_inline([buttons], 2)