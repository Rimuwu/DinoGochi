from bot.models.user import User as BeanieUser
from bot.models.market import Seller
from aiogram.types import ReplyKeyboardMarkup, KeyboardButton

from bot.dbmanager import mongo_client
from bot.const import GAME_SETTINGS as gs
from bot.modules.data_format import chunks, crop_text, list_to_keyboard, seconds_to_str
from bot.models.dinosaur import Dino, Egg
from bot.models.activity import KDActivity
from bot.modules.localization import t, tranlate_data
from bot.modules.logs import log
from bot.models.user import Referral
from bot.modules.user.user import User, premium
from aiogram.utils.keyboard import ReplyKeyboardBuilder, InlineKeyboardBuilder



async def back_menu(userid) -> str:
    """Возвращает предыдущее меню
    """
    markup_key = 'main_menu'
    menus_list = ['main_menu', 'settings_menu', 'settings2_menu', 'settings3_menu',
                  'main_menu', 'actions_menu', 'live_actions_menu',
                  'main_menu', 'actions_menu', 'speed_actions_menu',
                  'main_menu', 'actions_menu', 'skills_actions_menu',
                  'main_menu', 'actions_menu', 'extraction_actions_menu',
                  'main_menu', 'backgrounds_menu',
                  'main_menu', 'map_menu', 'market_menu', 'seller_menu',
                  'main_menu', 'profile_menu', 'about_menu',
                  'main_menu', 'friends_menu', 'referal_menu',
                  'main_menu', 'map_menu', 'dino_tavern_menu',
                  'main_menu', 'map_menu', 'blacksmith_menu',
                  'main_menu', 'map_menu'
                 ] # схема всех путей меню клавиатур
    user_model = await BeanieUser.find_one(BeanieUser.userid == userid)
    user_dict = user_model.dict() if user_model else None
    if user_dict:
        markup_key = user_dict.get('last_markup', 'main_menu')

    if markup_key != 'main_menu':
        menu_ind = menus_list.index(markup_key)
        result = menus_list[menu_ind - 1]
        return result
    else: return 'main_menu'

async def get_buttons(dino: Dino) -> list:
    status = await dino.status
    data = ['journey', 'put_to_bed', 'collecting', 'entertainments']
    if status == 'journey': data[0] = 'events'
    elif status == 'sleep': data[1] = 'awaken'
    elif status == 'collecting': data[2] = 'progress'
    elif status == 'game': data[3] = 'stop_game'
    return data

async def markups_menu(userid: int, markup_key: str = 'main_menu', 
                 language_code: str = 'en', last_markup: bool = False):
    """Главная функция создания меню для клавиатур
       >>> menus:
       main_menu, settings_menu, settings2_menu, profile_menu, about_menu, friends_menu, market_menu, dino_tavern_menu, referal_menu, actions_menu
       last_menu\n\n

       last_markup - Если True, то меню будет изменено только если,
       последнее меню совпадает с тем, на которое будет изменено
       Пример:

       markup_key: settings_menu, last_markup: profile_menu
       >>> last_menu: True -> Меню не изменится
       >>> last_menu: False -> Меню изменится
    """
    prefix, buttons = 'commands_name.', []
    add_back_button = False
    kwargs = {}
    old_last_menu = None

    user_model = await BeanieUser.find_one(BeanieUser.userid == userid)
    user_dict = user_model.dict() if user_model else None

    if markup_key == 'last_menu':
       """ Возращает к последнему меню
       """
       if user_dict:
           markup_key = user_dict.get('last_markup')

    else: #Сохранение последнего markup
        if last_markup:
            if user_dict:
                old_last_menu = user_dict.get('last_markup')

        if user_model:
            await user_model.set_last_markup(markup_key)

    if user_dict and user_dict['last_markup'] == "dino_tavern_menu":
        from bot.modules.user.tavern_redis import remove_from_tavern
        await remove_from_tavern(userid)

    if markup_key == 'main_menu':
        # Главное меню
        buttons = [
            ['dino_profile', 'actions_menu', 'profile_menu'],
            ['settings_menu', 'friends_menu'],
            ['map-bt']
        ]

    elif markup_key == 'settings_menu':
        # Меню настроек
        prefix = 'commands_name.settings.'
        buttons = [
            ['notification', 'inventory'],
            ['dino_name', 'inv_sort'],
            ['dino_profile', 'delete_me'],
            ['noprefix.buttons_name.back', 'settings_page_2']
        ]

    elif markup_key == 'settings2_menu':
        prefix = 'commands_name.settings2.'
        add_back_button = False
        buttons = [
            ['my_name', 'lang'],
            ['dino_talk', 'nick'],
            ['reset_avatar', 'confidentiality'],
            ['noprefix.buttons_name.back', 'settings_page_3']
        ]

    elif markup_key == 'settings3_menu':
        prefix = 'commands_name.settings3.'
        add_back_button = True
        buttons = [
            ['rare_emoji', 'only_emoji'],
            ['inv_columns']
        ]

    elif markup_key == 'profile_menu':
        # Меню профиля
        prefix = 'commands_name.profile.'
        add_back_button = True
        buttons = [
            ['information', 'inventory', 'rayting'],
            ['about', 'support'],
        ]

    elif markup_key == 'about_menu':
        # Меню о боте
        prefix = 'commands_name.about.'
        add_back_button = True
        buttons = [
            ['team', 'grafs'],
            ['links', 'my_collection', 'faq'],
        ]

    elif markup_key == 'friends_menu':
        # Меню друзей
        prefix = 'commands_name.friends.'
        add_back_button = True
        buttons = [
            ['add_friend', 'friends_list', 'remove_friend'],
            ['requests', 'referal'],
        ]

    elif markup_key == 'market_menu':
        # Меню рынка
        prefix = 'commands_name.market.'
        add_back_button = True
        buttons = [
            ['random', 'find'],
            ['seller_profile', 'search_markets'],
        ]
    
    elif markup_key == 'backgrounds_menu':
        # Меню разных магазинов
        prefix = 'commands_name.backgrounds.'
        add_back_button = True
        buttons = [
            ['backgrounds', 'standart']
        ]

        if await premium(userid): buttons.append(['custom_profile'])

    elif markup_key == 'seller_menu':
        # Меню магазина
        prefix = 'commands_name.seller_profile.'
        add_back_button = True

        seller_exists = await Seller.find_one(Seller.owner_id == userid) is not None
        if seller_exists:
            buttons = [
                ['add_product', 'my_products'],
                ['my_market'],
            ]
        else:
            buttons = [
                ['create_market']
            ]

    elif markup_key == 'dino_tavern_menu':
        # Меню таверны
        prefix = 'commands_name.dino_tavern.'
        add_back_button = True
        buttons = [
            ['hoarder', 'quests'],
            ['edit', 'daily_award', 'events'],
        ]

    elif markup_key == 'blacksmith_menu':
        # Меню кузнеца
        prefix = 'commands_name.blacksmith.'
        add_back_button = True
        buttons = [
            ['upgrade', 'my_items'],
            ['erase_name', 'info']
        ]

    elif markup_key == 'referal_menu':
        # Меню рефералов
        prefix = 'commands_name.referal.'
        add_back_button = True

        referal = await Referral.get_user_code(userid)
        friend_code = await Referral.get_user_sub(userid)
        buttons = [
                ['code', 'enter_code'],
            ]
        if referal:
            my_code = referal.code
            buttons[0][0] = f'notranslate.{t("commands_name.referal.my_code", language_code)} {my_code}'

        if friend_code:
            buttons[0][1] = f'notranslate.{t("commands_name.referal.friend_code", language_code)} {friend_code.code}'

    elif markup_key == 'actions_menu':
        # Меню действий
        prefix = 'commands_name.action_ask.'
        add_back_button = True
        user = await User().create(userid)
        col_dinos = await user.get_col_dinos #Сохраняем кол. динозавров

        if col_dinos == 0:
            buttons = [
                ['no_dino', 'noprefix.buttons_name.back']
            ]
        if col_dinos == 1:
            buttons = [
                ['speed_actions'],
                ['skills_actions', 'live_actions', 'extraction']
            ]

        else:
            add_back_button = False
            dino = await user.get_last_dino()
            if dino:
                dino_button = f'notranslate.{t("commands_name.action_ask.dino_button", language_code)} {crop_text(dino.name, 6)}'

                buttons = [
                    ['speed_actions'],
                    ['skills_actions', 'live_actions', 'extraction'],
                    [dino_button, "noprefix.buttons_name.back"]
                ]

    elif markup_key == 'live_actions_menu':
        # Меню действий жизненных активностей
        prefix = 'commands_name.actions.'
        add_back_button = False

        user = await User().create(userid)
        dino = await user.get_last_dino()
        if dino:
            dp_buttons = await get_buttons(dino)
            buttons = [
                ["feed", dp_buttons[1]],
                [dp_buttons[3], dp_buttons[0], dp_buttons[2]],
                ["noprefix.buttons_name.back"]
            ]

            # kd_coll_time = await KDActivity.check_activity(dino._id, 'collecting')
            # if kd_coll_time != 0 and dp_buttons[2] == 'collecting':
            #     buttons[1][2] = (
            #         f"notranslate.{t('commands_name.actions.collecting', language_code)} "
            #         f"({seconds_to_str(kd_coll_time, language_code, True, 'hour')})"
            #     )

    elif markup_key == 'extraction_actions_menu':
        # Меню работ
        prefix = 'commands_name.extraction_actions.'
        add_back_button = True
        buttons = []

        user = await User().create(userid)
        dino = await user.get_last_dino()

        if dino:
            buttons = [
                ['mine', 'bank'],
                ['sawmill'] # farm
            ]

            if await dino.status in ['farm', 'mine', 'bank', 'sawmill']:
                buttons = [
                    ['progress', 'stop_work']
                ]

    elif markup_key == 'skills_actions_menu':
        # Меню повышения навыков
        prefix = 'commands_name.skills_actions.'
        add_back_button = True
        buttons = []

        user = await User().create(userid)
        dino = await user.get_last_dino()

        if dino:
            kd = await KDActivity.check_all_activity(dino._id)

            bd = {
                'gym': f"notranslate.{t('commands_name.skills_actions.gym', language_code)}",
                'library': f"notranslate.{t('commands_name.skills_actions.library', language_code)}",
                'park': f"notranslate.{t('commands_name.skills_actions.park', language_code)}",
                'swimming_pool': f"notranslate.{t('commands_name.skills_actions.swimming_pool', language_code)}",
            }

            for key, value in kd.items():
                if key in bd:
                    bd[key] += f' ({seconds_to_str(value, language_code, True, "hour")})'

            buttons = [
                [bd['gym'], bd['library']],
                [bd['park'], bd['swimming_pool']]
            ]
            
            if await dino.status in ['gym', 'library', 'park', 'swimming_pool']:
                buttons.append(
                    ['stop_work']
                )

    elif markup_key == 'speed_actions_menu':
        # Меню повышения навыков
        prefix = 'commands_name.speed_actions.'
        add_back_button = True
        buttons = []

        user = await User().create(userid)
        dino = await user.get_last_dino()

        if dino:
            kd = await KDActivity.check_all_activity(dino._id)

            bd = {
                'pet': f"notranslate.{t('commands_name.speed_actions.pet', language_code)}",
                'fighting': f"notranslate.{t('commands_name.speed_actions.fighting', language_code)}",
                'talk': f"notranslate.{t('commands_name.speed_actions.talk', language_code)}",
            }

            for key, value in kd.items():
                if key in bd:
                    bd[key] += f' ({seconds_to_str(value, language_code, True, "minute")})'

            buttons = [
                [bd['pet'], bd['talk']],
                [bd['fighting']]
            ]

    elif markup_key == 'map_menu':
        # Меню перехода в разные меню
        prefix = 'commands_name.map.'
        add_back_button = True

        buttons = [
            ['market', 'dino-tavern_menu'],
            ['blacksmith']
        ]

    else:
        log(prefix='Markup', 
            message=f'not_found_key User: {userid}, Data: {markup_key}', lvl=2)
        return await markups_menu(userid, 'main_menu', language_code)

    buttons = tranlate_data(
        data=buttons, 
        locale=language_code, 
        key_prefix=prefix,
        **kwargs
        ) #Переводим текст внутри списка

    if add_back_button:
        buttons.append([t('buttons_name.back', language_code)])

    result = list_to_keyboard(buttons)
    if last_markup:
        if user_dict:
            if not old_last_menu:
                old_last_menu = user_dict.get('last_markup')

            if old_last_menu != markup_key:
                result = None
    return result

def get_answer_keyboard(elements: list, lang: str='en') -> dict:
    """
       elements - Dino | Egg
    
       return 
       {'case': 0} - нет динозавров / яиц
       {'case': 1, 'element': Dino | Egg} - 1 динозавр / яйцо 
       {'case': 2, 'keyboard': ReplyMarkup, 'data_names': dict} - несколько динозавров / яиц
    """
    if len(elements) == 0:
        return {'case': 0}

    elif len(elements) == 1: # возвращает 
        return {'case': 1, 'element': elements[0]}

    else: # Несколько динозавров / яиц
        names, data_names = [], {}
        n, txt = 0, ''
        for element in elements:
            n += 1

            if type(element) == Dino:
                txt = f'{n}🦕 {element.name}'
            elif type(element) == Egg:
                txt = f'{n}🥚'

            data_names[txt] = element
            names.append(txt)

        buttons_list = chunks(names, 2) #делим на строчки по 2 элемента
        buttons_list.append([t('buttons_name.cancel', lang)]) #добавляем кнопку отмены
        keyboard = list_to_keyboard(buttons_list, 2) #превращаем список в клавиатуру

        return {'case': 2, 'keyboard': keyboard, 'data_names': data_names}

def count_markup(max_count: int=1, lang: str='en') -> ReplyKeyboardMarkup:
    """Создаёт клавиатуру для быстрого выбора числа
        Предлагает выбрать 1, max_count // 2, max_count

    Args:
        max_count (int): Максимальное доступное вводимое число
        lang (str): Язык кнопки отмены
    """
    counts = ["1"]
    if max_count > 1: counts.append(f"{max_count}")
    if max_count >= 4: counts.insert(1, f"{max_count // 2}")

    return list_to_keyboard([counts, t('buttons_name.cancel', lang)])

def feed_count_markup(dino_eat: int, item_act: int, 
                      max_col: int, item_name: str, lang):
    if item_act == 0: item_act = 1

    col_to_full = (100 - dino_eat) // item_act
    one_col = dino_eat + item_act
    return_list = []
    bt_3 = None

    if col_to_full > max_col: col_to_full = max_col
    if one_col > 100: one_col = 100

    from bot.modules.data_format import parse_custom_emoji_markdown
    clean_name, emoji_id, alt_emoji = parse_custom_emoji_markdown(item_name)

    if emoji_id:
        emoji_prefix = f"![{alt_emoji}](tg://emoji?id={emoji_id})"
        bt_1 = f"{emoji_prefix} {one_col}% = 1"
        bt_2 = f"{emoji_prefix} {dino_eat + item_act * col_to_full}% = {col_to_full}"

        if dino_eat + item_act * col_to_full < 100:
            mxx = dino_eat + item_act * (col_to_full + 1)
            if mxx > 100: mxx = 100
            bt_3 = f"{emoji_prefix} {mxx}% = {col_to_full + 1}"
    else:
        emoji = item_name[:1]
        bt_1 = f"{one_col}% = {emoji} 1"
        bt_2 = f"{dino_eat + item_act * col_to_full}% = {emoji} {col_to_full}"

        if dino_eat + item_act * col_to_full < 100:
            mxx = dino_eat + item_act * (col_to_full + 1)
            if mxx > 100: mxx = 100
            bt_3 = f"{mxx}% = {emoji} {col_to_full + 1}"

    if col_to_full == 1:
        if bt_3: return_list += [bt_1, bt_3]
        else: return_list += [bt_1]

    elif col_to_full != 1 and col_to_full != 0:
        if bt_3: return_list += [bt_1, bt_2, bt_3]
        else: return_list += [bt_1, bt_2]

    if not return_list: return_list += [bt_1]

    return list_to_keyboard([return_list, [t('buttons_name.cancel', lang)]])

def confirm_markup(lang: str='en') -> ReplyKeyboardMarkup:
    """Создаёт клавиатуру для подтверждения

    Args:
        lang (str, optional):  Язык кнопок
    """
    return list_to_keyboard([
        [{"text": t('buttons_name.confirm', lang), "style": "success", "custom_emoji_id": "thumbs_up"}], 
        [{"text": t('buttons_name.cancel', lang), "style": "danger", "custom_emoji_id": "forbidden"}]
    ])

def answer_markup(lang: str='en') -> ReplyKeyboardMarkup:
    """Создаёт клавиатуру для выбора да / нет

    Args:
        lang (str, optional):  Язык кнопок
    """
    return list_to_keyboard([
        [{"text": t('buttons_name.yes', lang), "style": "success", "custom_emoji_id": "thumbs_up"}, 
         {"text": t('buttons_name.no', lang), "style": "danger", "custom_emoji_id": "thumbs_down"}], 
        [{"text": t('buttons_name.cancel', lang), "style": "danger", "custom_emoji_id": "forbidden"}]
    ])

def cancel_markup(lang: str='en') -> ReplyKeyboardMarkup:
    """Создаёт клавиатуру для отмены

    Args:
        lang (str, optional):  Язык кнопки
    """
    return list_to_keyboard([{"text": t('buttons_name.cancel', lang), "style": "danger", "custom_emoji_id": "forbidden"}])

def down_menu(markup: ReplyKeyboardMarkup, 
              arrows: bool = True, lang: str = 'en', is_premium: bool = True): 
    """Добавления нижнего меню для страничных клавиатур
    """
    from bot.modules.data_format import resolve_button_data, strip_emoji_prefix

    markup_n = ReplyKeyboardBuilder().from_markup(markup)

    def make_btn(text, custom_emoji_key=None, style=None):
        if custom_emoji_key:
            text = strip_emoji_prefix(text)
        txt, emoji_id = resolve_button_data(text, custom_emoji_key, is_premium=is_premium)
        kwargs = {"text": txt}
        if emoji_id is not None:
            kwargs["icon_custom_emoji_id"] = emoji_id
        if style is not None:
            kwargs["style"] = style
        return KeyboardButton(**kwargs)

    cancel_text = strip_emoji_prefix(t('buttons_name.cancel', lang))

    if arrows:
        back_btn = make_btn(gs['back_button'], style='primary')
        cancel_btn = make_btn(cancel_text, 'forbidden', style='danger')
        forward_btn = make_btn(gs['forward_button'], style='primary')
        markup_n.row(back_btn, cancel_btn, forward_btn)
    else: 
        cancel_btn = make_btn(cancel_text, 'forbidden', style='danger')
        markup_n.row(cancel_btn)

    return markup_n.as_markup(resize_keyboard=True)
