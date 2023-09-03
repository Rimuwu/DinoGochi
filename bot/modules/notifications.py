from random import choice
from time import time
from asyncio import sleep

from bson.objectid import ObjectId
from telebot.types import InlineKeyboardMarkup

from bot.config import mongo_client, conf
from bot.exec import bot
from bot.modules.data_format import seconds_to_str
from bot.modules.inline import inline_menu
from bot.modules.localization import get_data, t, get_lang
from bot.modules.logs import log
from bot.modules.item import get_name

dinosaurs = mongo_client.dinosaur.dinosaurs
dino_owners = mongo_client.dinosaur.dino_owners
users = mongo_client.user.users
dino_mood = mongo_client.dinosaur.dino_mood

tracked_notifications = [
    'need_heal', 'need_eat',
    'need_mood', 'need_game',
    'need_energy'
] # Уведомления отслыющиеся в потоках и требующие проверки перед отправкой

replics_notifications = [
    'need_heal', 'need_eat',
    'need_mood', 'need_game',
    'need_energy', 'game_end', 
    'breakdown', 'inspiration'
] # Уведомления которые имею разные реплики

critical_line = {
    'heal': 30, 'eat': 40, 
    'game': 50, 'mood': 50,
    'energy': 30
}

def save_notification(dino_id: ObjectId, not_type: str):
    """ Сохраняет уведомление и его время отправки
    """
    dinosaurs.update_one({'_id': dino_id}, {'$set': 
                            {f'notifications.{not_type}': int(time())}})

def dino_notification_delete(dino_id: ObjectId, not_type: str):
    """ Обнуляет уведомление
    """
    dino = dinosaurs.find_one({"_id": dino_id})
    if dino:
        if not_type in dino['notifications']:
            dinosaurs.update_one({'_id': dino_id}, {'$unset': 
                                    {f'notifications.{not_type}': 1}})

def check_dino_notification(dino_id: ObjectId, not_type: str, save: bool = True):
    """ Проверяет отслеживаемые уведомления, а так же удаляет его если 
        
        Return
        True - уведомления нет или не отслеживается или время ожидания истекло
        False - уведомление уже отослано или динозавр не найден
    """
    dino = dinosaurs.find_one({"_id": dino_id})
    if not dino: return False
    else:
        if not_type not in tracked_notifications: return True
        elif not_type in dino['notifications'].keys():
            if dino['notifications'][not_type] + 14400 <= int(time()):
                if save: save_notification(dino_id, not_type)
                return True
            else: return False
        return True

async def dino_notification(dino_id: ObjectId, not_type: str, **kwargs):
    """ Те уведомления, которые нужно отслеживать и отсылать 1 раз
        В аргументы автоматически добавляется имя динозавра.
        Так же это те уведомления, которые привязаны к динозавру и отправляются всем владельцам.

        Если передать add_time_end=True то в аргументы дополнительно будет добавлен ключ time_end в формате времени, секудны берутся из ключа secs.
        
        Если мы хотим добавить какое то сообщение в тексте, но мы не хотим запрашивать владельца и получать его язык, мы можем добавить ключ add_message c путём к тексту.
    """
    dino = dinosaurs.find_one({"_id": dino_id})
    owners = list(dino_owners.find({'dino_id': dino_id}))
    text, markup_inline = not_type, InlineKeyboardMarkup()

    if 'unit' in kwargs and kwargs['unit'] < 0: kwargs['unit'] = 0

    async def send_not(text, markup_inline):
        for owner in owners:
            lang = get_lang(owner["owner_id"])

            user = users.find_one({'userid': owner['owner_id']})
            if user:

                # Добавление переменных в данные
                if kwargs.get('add_time_end', False):
                    # Данные об времени окончания
                    kwargs['time_end'] = seconds_to_str(
                        kwargs.get('secs', 0), lang)

                if user['settings'].get('my_name', False):
                    # Имя хозяина
                    kwargs['owner_name'] = user['settings']['my_name']
                    if not kwargs['owner_name']:
                        kwargs['owner_name'] = t('owner', lang)
                else: kwargs['owner_name'] = t('owner', lang)

                if 'add_message' in kwargs:
                    # Если мы хотим добавить какое то сообщение в тексте, но мы не хотим запрашивать владельца и получать его язык, мы можем добавить ключ add_message c путём к тексту
                    # Ключ будет message
                    kwargs['message'] = t(kwargs['add_message'], lang, **kwargs)

                if 'item_id' in kwargs:
                    # Получение имени предмета
                    kwargs['item_name'] = get_name(kwargs['item_id'], lang)

                # Формирование текста
                if not_type in replics_notifications:
                    # Тут мы выбираем случайную реплику для динозавра
                    replics = get_data(
                        f'notifications.{not_type}.replics', lang)

                    text = choice(replics).format(**kwargs)
                    markup = get_data(
                        f'notifications.{not_type}.inline_menu', lang)
                    markup_inline = inline_menu(markup, lang, **kwargs)
                else:
                    data = get_data(f'notifications.{not_type}', lang)
                    if type(data) == dict:
                        text = data['text'].format(**kwargs)
                        markup_inline = inline_menu(data['inline_menu'], lang, **kwargs)
                    else:
                        text = data.format(**kwargs)

                # Уведомление
                log(prefix='DinoNotification', 
                    message=f'User: {owner["owner_id"]} DinoId: {dino_id}, Data: {not_type} Kwargs: {kwargs}', lvl=0)
                try:
                    try:
                        await sleep(0.05)
                        await bot.send_message(owner['owner_id'], text, reply_markup=markup_inline, parse_mode='Markdown')
                    except Exception:
                        await bot.send_message(owner['owner_id'], text, reply_markup=markup_inline)
                except Exception as error:
                    if conf.debug:
                        log(prefix='DinoNotification Error', 
                            message=f'User: {owner["owner_id"]} DinoId: {dino_id}, Data: {not_type} Error: {error}', 
                            lvl=3)
    if dino: # type: dict
        kwargs['dino_name'] = dino['name']
        kwargs['dino_alt_id_markup'] = dino['alt_id']
        res = dino_mood.find_one({'dino_id': dino_id, 
                            'type': 'breakdown', 'action': 'seclusion'})
        # Отменя уведолмения если динозавр спит или у него нервный срыв
        if dino['status'] != 'sleep' and not res:
            if not_type in tracked_notifications:

                if check_dino_notification(dino_id, not_type):
                    save_notification(dino_id, not_type)
                    await send_not(text, markup_inline)
                else:
                    log(prefix='Notification Repeat', 
                        message=f'DinoId: {dino_id}, Data: {not_type} Kwargs: {kwargs}', lvl=0)

            else: await send_not(text, markup_inline)

async def user_notification(user_id: int, not_type: str, 
                            lang: str='', **kwargs):
    """ Те уведомления которые в любом случае отправятся 1 раз

        add_way - дополнительный аргумент, учитывает уведомление по not_type но текст в зависимости от аргумента add_way 
    """
    text, markup_inline = not_type, InlineKeyboardMarkup()
    standart_notification = [
        'donation', 'lvl_up', 
        'product_delete' # необходим preview
    ]
    unstandart_notification = [
        'incubation_ready', # необходим dino_alt_id_markup, user_name
        'send_request', #необходим user_name
        'not_independent_dead', 'independent_dead', 'daily_award',
        'product_buy', # необходим col, price, name, alt_id
        'kindergarten' # dino_name dino_alt_id_markup
    ]
    add_way = '.'+kwargs.get('add_way', '')

    if not lang:
        try:
            chat_user = await bot.get_chat_member(user_id, user_id)
            lang = get_lang(chat_user.user.id)
        except: lang = 'en'

    if not_type in standart_notification:
        text = t(f'notifications.{not_type}{add_way}', lang, **kwargs)

    elif not_type in unstandart_notification:
        data = get_data(f'notifications.{not_type}', lang)
        text = data['text'].format(**kwargs)
        markup_inline = inline_menu(data['inline_menu'], lang, **kwargs)

    else:
        log(prefix='Notification not_type', 
            message=f'Тип уведомления {not_type} не найден!', 
            lvl=3)

    log(prefix='Notification', 
        message=f'User: {user_id}, Data: {not_type} Kwargs: {kwargs}', lvl=0)
    try:
        try:
            await sleep(0.05)
            await bot.send_message(user_id, text, reply_markup=markup_inline, parse_mode='Markdown')
        except Exception:
            await bot.send_message(user_id, text, reply_markup=markup_inline)
    except Exception as error: 
        log(prefix='Notification Error', 
            message=f'User: {user_id}, Data: {not_type} Error: {error}', 
            lvl=0)

async def notification_manager(dino_id: ObjectId, stat: str, unit: int):
    """ Автоматически отсылает / удаляет уведомления
    """
    notif = f'need_{stat}'

    if critical_line[stat] >= unit:
        if check_dino_notification(dino_id, notif, False):
            # Отправка уведомления
            await dino_notification(dino_id, notif, unit=unit)

    elif unit >= critical_line[stat] + 20:
        # Удаляем уведомление 
        dino_notification_delete(dino_id, notif)