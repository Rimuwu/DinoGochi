from aiogram.types import InlineKeyboardButton

from bot.modules.data_format import list_to_inline
from bot.modules.items.item import counts_items, is_standart
from bot.modules.items.item import get_data as get_item_data
from bot.modules.items.item import get_item_dict, get_name, item_code
from bot.modules.localization import get_data as get_loc_data
from bot.modules.localization import t
from bot.modules.logs import log
from aiogram.utils.keyboard import InlineKeyboardBuilder

def inline_menu(markup_data, lang: str = 'en', **kwargs):
    markup_inline = InlineKeyboardBuilder()
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
    return markup_inline.as_markup()

async def item_info_markup(item: dict, lang: str, userid: int):

    item_data = get_item_data(item['item_id'])
    loc_data = get_loc_data('item_info.static.buttons', lang)
    code = await item_code(item_dict=item, userid=userid)
    buttons_dict = {}

    if item_data['type'] not in ['material', 'ammunition', 'dummy']:
        use_text = loc_data['use'][item_data['type']]

        if 'abilities' in item and 'uses' in item['abilities'] and item['abilities']['uses'] != -666:
            use_text += f' ({item["abilities"]["uses"]}/{item_data["abilities"]["uses"]})'

        if item_data['type'] == 'special' and item_data['class'] == 'custom_book':
            use_text = loc_data['custom_book']

            if 'abilities' in item and 'content' in item['abilities'] and item['abilities']['content']:
                # Кнопка прочитать если внутри есть текст
                buttons_dict[ loc_data['read_custom_book'] ] = f'item custom_book_read {code}'

        buttons_dict[use_text] = f'item use {code}'

    if not('abilities' in item and 'interact' in item['abilities'] and not(item['abilities']['interact'])):
        buttons_dict[loc_data['delete']] = f'item delete {code}'

        if 'cant_sell' not in item_data or ('cant_sell' in item_data and not item_data['cant_sell']):
            buttons_dict[loc_data['exchange']] = f'item exchange {code}'

    if is_standart(item):
        if 'buyer' not in item_data or (item_data['buyer'] == True):
            # Скупщик

            buttons_dict[loc_data['buyer']] = f'buyer {code}'

    markup_st = list_to_inline([buttons_dict], 2)
    markup_inline = InlineKeyboardBuilder().from_markup(markup_st)

    if item_data['type'] == 'recipe':
        ignore_craft = item_data.get('ignore_preview', [])
        
        for rep in item_data['create']:
            if rep not in ignore_craft:
                for item_cr in item_data['create'][rep]:
                    data = get_item_dict(item_cr['item'])
                    code_for_item = await item_code(item_dict=data, userid=userid)

                    if item_cr['type'] != 'preview':
                        name = loc_data['created_item'].format(
                                    item=get_name(item_cr['item'], 
                                                lang, item_cr.get('abilities', {})))

                        markup_inline.row(InlineKeyboardButton(text=name,
                                    callback_data=f'item info {code_for_item}'), width=2)

    if 'ns_craft' in item_data:
        for cr_dct_id in item_data['ns_craft'].keys():
            bt_text = ''
            cr_dct = item_data['ns_craft'][cr_dct_id]

            bt_text += counts_items(cr_dct['materials'], lang)
            bt_text += ' = '
            bt_text += counts_items(cr_dct['create'], lang)

            markup_inline.row(
                InlineKeyboardButton(text=bt_text,
                            callback_data=f'ns_craft {code} {cr_dct_id}'), width=2
                )

    return markup_inline.as_markup()

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
    buttons[rai['skills']['text']] = rai['skills']['data']
    buttons[rai['backgrounds']['text']] = rai['backgrounds']['data']

    for but in buttons: buttons[but] = buttons[but].format(dino=alt_id)
    return list_to_inline([buttons], 2)