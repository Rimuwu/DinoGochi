from typing import Optional

from bson import ObjectId


from bot.dbmanager import mongo_client

from bot.modules.data_format import list_to_inline
from time import time, strftime, gmtime

from bot.modules.localization import t

from bot.modules.overwriting.DataCalsses import DBconstructor


links = DBconstructor(mongo_client.tracking.links)
members = DBconstructor(mongo_client.tracking.members)
users = DBconstructor(mongo_client.user.users)
dino_owners = DBconstructor(mongo_client.dinosaur.dino_owners)
incubation = DBconstructor(mongo_client.dinosaur.incubation)
langs = DBconstructor(mongo_client.user.langs)

async def creat_track(code: str, who_create: str = "system"):
    """Создаёт ссылку отслеживания и добавляет её в БД
        None - уже отслеживается
        dict - создано

        who_create - кто создал ссылку отслеживания
        - who_create = system - автоматическое создание при старте с данной ссылкой
        - who_create = admin - создание админом

        concern - К какой трек ссылке относится данная ссылка
        - То есть ссылка KJHk354 ни к чему не будет относится
        - А ссылка KJHk354@@medium будет относится к ссылке medium
 
        И соответсвенно в concern будет хранится id ссылки KJHk354
    """

    assert who_create in ["system", "admin"], f"who_create {who_create} not in list" 

    concern = None
    if "__" in code:
        base_code, concern_code = code.split("__", 1)
        concern_track = await links.find_one({'code': concern_code}, comment='find_base_track')
        if concern_track:
            concern = concern_track['_id']

    data = {
        "code": code,
        "start": int(time()),
        "who_create": who_create,
        "concern": concern
    }

    res = await links.find_one({'code': code}, comment='check_track')
    if res: return None
    else:
        return await links.insert_one(data, comment='create_track')

async def user_first_status(userid: int):

    user_b = await users.find_one({'userid': userid}, comment='user_status')

    if not user_b:
        return 'click_start'
    else:
        dinos = await dino_owners.find_one({'owner_id': userid}, comment='user_first_status_dinos')
        eggs = await incubation.find_one({'owner_id': userid}, comment='user_first_status_eggs')

        if dinos: return 'gaming'
        elif eggs: return 'incubate'

    return 'create_account'


async def add_track_user(code: str, userid: int):
    """

    status:
    - click_start - пользователь нажал на ссылку
    - create_account - пользователь создал аккаунт
    - incubate - пользователь инкубирует динозавра
    - gaming - пользователь играет в игру
    - delete_account - пользователь удалил аккаунт

    returns:
    - True - добавлено
    - False - не добавлено

    """
    res = await links.find_one({'code': code}, comment='add_track_user')
    if res:
        track_id = res['_id']
        res2 = await members.find_one(
            {'userid': userid, "track_id": track_id}, comment='add_track_user_res2')

        if not res2:
            already_in_bot = await users.find_one(
                {'userid': userid}, comment='add_track_user_already_in_bot')

            first_status = await user_first_status(userid)

            data = {
                "track_id": track_id,
                "userid": userid,
                "enter": int(time()),
                "status": first_status,
                "first_status": first_status,
                "already_in_bot": bool(already_in_bot)
            }

            return await members.insert_one(data, comment='add_track_user_insert')
    return None

async def edit_track_user(code: str, userid: int, status: str):
    """Изменяет статус пользователя по ссылке отслеживания"""

    assert status in [
        "click_start",
        "create_account",
        "incubate",
        "delete_account",
        "gaming",
    ], f"Status {status} not in list"

    res = await links.find_one({'code': code}, comment='edit_track_user')
    if res:
        res2 = await members.find_one(
            {'userid': userid, "track_id": res['_id']}, comment='edit_track_user_res2')
        if res2:
                await members.update_one(
                    {'userid': userid, "track_id": res['_id']},
                    {'$set': {"status": status}}, comment='edit_track_user_update')
                return True
    return False

async def get_track_data(code: str):

    res = await links.find_one({'code': code}, comment='get_track_data')
    if res:
        members_track = await members.find(
            {'track_id': res['_id']}, comment='get_track_data_members')

        concern_links = await links.find(
            {'concern': res['_id']}, comment='get_track_data_concern_links')

        data = {
            'code': res['code'],
            'start': res['start'],
            'who_create': res['who_create'],
            'concern': res['concern'],
            'members': members_track,
            'concern_links': concern_links
        }
        return data
    return {}

async def statistic_track(code: str) -> Optional[dict]:
    """Собирает статистику по ссылке отслеживания"""

    data = await get_track_data(code)
    if data:
        total_members = len(data['members'])
        if total_members == 0:
            return {
                'status_percentages': {},
                'first_status_percentages': {},
                'already_in_bot_percentages': {},
                'concern_links_statistics': {}
            }

        # Подсчёт процентного соотношения статусов
        status_counts = {}
        first_status_counts = {}
        already_in_bot_counts = {'True': 0, 'False': 0}

        for member in data['members']:
            status_counts[member['status']] = status_counts.get(member['status'], 0) + 1
            first_status_counts[member['first_status']] = first_status_counts.get(member['first_status'], 0) + 1
            already_in_bot_counts[str(member['already_in_bot'])] += 1

        status_percentages = {k: (v / total_members) * 100 for k, v in status_counts.items()}
        first_status_percentages = {k: (v / total_members) * 100 for k, v in first_status_counts.items()}
        already_in_bot_percentages = {k: (v / total_members) * 100 for k, v in already_in_bot_counts.items()}

        # Статистика для concern_links
        concern_links_statistics = {}
        for concern_link in data['concern_links']:
            concern_members = await members.find(
                {'track_id': concern_link['_id']}, comment='statistic_track_concern_members'
            )

            total_concern_members = len(concern_members)
            if total_concern_members == 0:
                concern_links_statistics[concern_link['code']] = {
                    'status_percentages': {},
                    'first_status_percentages': {},
                    'already_in_bot_percentages': {}
                }
                continue

            concern_status_counts = {}
            concern_first_status_counts = {}
            concern_already_in_bot_counts = {'True': 0, 'False': 0}

            for member in concern_members:
                concern_status_counts[member['status']] = concern_status_counts.get(member['status'], 0) + 1
                concern_first_status_counts[member['first_status']] = concern_first_status_counts.get(member['first_status'], 0) + 1
                concern_already_in_bot_counts[str(member['already_in_bot'])] += 1

            concern_links_statistics[concern_link['code']] = {
                'status_percentages': {k: (v / total_concern_members) * 100 for k, v in concern_status_counts.items()},
                'first_status_percentages': {k: (v / total_concern_members) * 100 for k, v in concern_first_status_counts.items()},
                'already_in_bot_percentages': {k: (v / total_concern_members) * 100 for k, v in concern_already_in_bot_counts.items()},
                'members_count': len(concern_members)
            }

        return {
            'status_percentages': status_percentages,
            'first_status_percentages': first_status_percentages,
            'already_in_bot_percentages': already_in_bot_percentages,
            'concern_links_statistics': concern_links_statistics
        }

    return None

async def delete_track(code: str):
    res = await links.find_one({'code': code}, comment='delete_track_res')
    if res:
        await links.delete_one({'code': code}, comment='delete_track')
        await members.delete_many({'track_id': res['_id']}, comment='delete_track_members')
        return True
    return False

async def track_info(code: str, lang: str):
    res = await links.find_one({'code': code}, comment='track_info_res')
    text, markup = t("create_tracking.track_info.not_found", lang), None

    if res:
        # Получение данных о ссылке
        data = await get_track_data(code)
        if not data:
            return t("create_tracking.track_info.not_found", lang), None

        # Подсчёт количества переходов за последние 1, 7 и 30 дней
        current_time = int(time())
        one_day_ago = current_time - 86400
        seven_days_ago = current_time - 604800
        thirty_days_ago = current_time - 2592000

        last_day_count = sum(1 for member in data['members'] if member['enter'] >= one_day_ago)
        last_week_count = sum(1 for member in data['members'] if member['enter'] >= seven_days_ago)
        last_month_count = sum(1 for member in data['members'] if member['enter'] >= thirty_days_ago)

        # Подсчёт количества concern_links
        concern_links_count = len(data['concern_links'])

        # Получение статистики
        statistics = await statistic_track(code)

        concern_name = t("create_tracking.track_info.dependency", lang, concern_name="нет зависимости")
        if data['concern']:
            concern_data = await links.find_one({'_id': data['concern']}, comment='track_info_concern_name')
            if concern_data:
                concern_name = concern_data['code']

        # Формирование текста
        text = (
            f"{t('create_tracking.track_info.code', lang, code=data['code'])}\n"
            f"{t('create_tracking.track_info.track_link', lang, code=data['code'])}\n"
            f"{t('create_tracking.track_info.creation_date', lang, creation_date=strftime('%Y-%m-%d %H:%M:%S', gmtime(data['start'])))}\n\n"
            f"{t('create_tracking.track_info.created_by', lang, who_create=data['who_create'])}\n"
            f"{t('create_tracking.track_info.dependency', lang, concern_name=concern_name)}\n\n"
            f"{t('create_tracking.track_info.user_count', lang, user_count=len(data['members']))}\n"
            f"{t('create_tracking.track_info.status_count', lang)}\n"
        )

        status_counts = {}
        for member in data['members']:
            status_counts[member['status']] = status_counts.get(member['status'], 0) + 1

        total_members = len(data['members'])
        for status, count in status_counts.items():
            percentage = (count / total_members) * 100 if total_members > 0 else 0
            text += t("create_tracking.track_info.status_entry", lang, status=status, count=count, percentage=int(percentage)) + "\n"

        text += (
            f"\n{t('create_tracking.track_info.last_day_transitions', lang, last_day_count=last_day_count)}\n"
            f"{t('create_tracking.track_info.last_week_transitions', lang, last_week_count=last_week_count)}\n"
            f"{t('create_tracking.track_info.last_month_transitions', lang, last_month_count=last_month_count)}\n"
        )

        if concern_links_count:
            text += f"\n{t('create_tracking.track_info.concern_links_count', lang, concern_links_count=concern_links_count)}\n"

        if statistics:
            # Статистика для главной ссылки
            text += f"\n{t('create_tracking.track_info.main_link_statistics', lang)}\n"
            text += f"{t('create_tracking.track_info.first_status_percentages', lang)}\n"
            for status, percentage in statistics['first_status_percentages'].items():
                text += t("create_tracking.track_info.first_status_entry", lang, status=status, percentage=int(percentage)) + "\n"

            text += f"\n{t('create_tracking.track_info.already_in_bot_percentages', lang)}\n"
            for status, percentage in statistics['already_in_bot_percentages'].items():
                text += t("create_tracking.track_info.already_in_bot_entry", lang, status=status, percentage=int(percentage)) + "\n"

            # Суммарная статистика для concern_links
            if concern_links_count:
                text += f"\n{t('create_tracking.track_info.concern_links_summary', lang)}\n"
                total_concern_first_status_counts = {}
                total_concern_status_counts = {}
                total_concern_already_in_bot_counts = {'True': 0, 'False': 0}
                total_concern_members = 0

                for link_stats in statistics['concern_links_statistics'].values():
                    total_concern_members += link_stats['members_count']
                    
                    for status, percentage in link_stats['status_percentages'].items():
                        total_concern_status_counts[status] = \
                            total_concern_status_counts.get(status, 0) + percentage

                    for status, percentage in link_stats['first_status_percentages'].items():
                        total_concern_first_status_counts[status] = \
                            total_concern_first_status_counts.get(status, 0) + percentage

                    for status, percentage in link_stats['already_in_bot_percentages'].items():
                        total_concern_already_in_bot_counts[status] += percentage

                text += t("create_tracking.track_info.total_concern_links", lang, concern_links_count=concern_links_count) + "\n"
                text += t("create_tracking.track_info.total_concern_users", lang, total_concern_members=total_concern_members) + "\n\n"

                text += f"{t('create_tracking.track_info.concern_first_status_percentages', lang)}\n"
                for status, percentage in total_concern_first_status_counts.items():
                    text += f'<code>{status}</code>: {int(percentage / concern_links_count)}%\n'

                text += "Процентное соотношение статуса\n"#f"{t('create_tracking.track_info.concern_first_status_percentages', lang)}\n"
                for status, percentage in total_concern_status_counts.items():
                    text += f'<code>{status}</code>: {int(percentage / concern_links_count)}%\n'

                text += f"\n{t('create_tracking.track_info.concern_already_in_bot_percentages', lang)}\n"
                for status, percentage in total_concern_already_in_bot_counts.items():
                    text += f'<code>{status}</code>: {int(percentage / concern_links_count)}%\n'

                # Вывод первых трёх ссылок
                text += f"\n{t('create_tracking.track_info.top_three_links', lang)}\n"
                for i, concern_link in enumerate(data['concern_links'][:3], start=1):
                    text += t("create_tracking.track_info.top_three_entry", lang, index=i, code=concern_link['code']) + "\n"

        # Формирование кнопок
        markup = list_to_inline([
            {
                t('create_tracking.track_info.delete', lang): f'track delete {code}',
            },
        ])

    return text, markup

async def detailed_statistics(code: str):
    """Собирает подробную статистику для пользователей со статусом 'gaming'
    """
    data = await get_track_data(code)
    if not data:
        return None

    gaming_users = [member for member in data['members'] if member['status'] == 'gaming']
    if not gaming_users:
        return {
            'average_level': 0,
            'total_coins': 0,
            'total_super_coins': 0,
            'language_statistics': {}
        }

    total_level = sum(user.get('level', 0) for user in gaming_users)
    total_coins = sum(user.get('coins', 0) for user in gaming_users)
    total_super_coins = sum(user.get('super_coins', 0) for user in gaming_users)

    average_level = total_level / len(gaming_users)
    average_coins = total_coins / len(gaming_users)
    average_super_coins = total_super_coins / len(gaming_users)

    # Подсчёт статистики по языкам
    language_counts = {}
    for user in gaming_users:
        user_lang = await langs.find_one({'userid': user['userid']}, comment='detailed_statistics_language')
        if user_lang:
            lang_code = user_lang.get('lang', 'unknown')
            language_counts[lang_code] = language_counts.get(lang_code, 0) + 1

    return {
        'average_level': average_level,
        'average_coins': average_coins,
        'average_super_coins': average_super_coins,
        'language_statistics': language_counts
    }


async def auto_action(code: str, userid: int):
    """


    """

    track_res = await creat_track(code, who_create='system')
    if track_res:
        tracking_link_id = track_res.inserted_id
    else:

        existing_track = await links.find_one({'code': code}, comment='auto_action_existing_track')
        tracking_link_id = existing_track['_id'] if existing_track else None


    user_res = await add_track_user(code, userid)
    user_tracking_id = user_res.inserted_id if user_res else None

    return tracking_link_id, user_tracking_id

async def get_track_pages(traks_dt: Optional[list[ObjectId]] = None) -> dict:
    """
    """
    
    if traks_dt is None:
        traks = await links.find({}, comment='get_track_pages')
    else:
        tracks = []
        for track_id in traks_dt:
            track = await links.find_one({'_id': track_id}, comment='get_track_pages')
            if track:
                tracks.append(track)

    buttons = {}
    for track in traks:
        buttons[track['code']] = track['code']

    return buttons

def update_all_user_track(userid: int, status: str):
    """Обновляет статус пользователя в трекинге, если он отличается от текущего"""
    assert status in [
        "click_start",
        "create_account",
        "incubate",
        "delete_account",
        "gaming",
    ], f"Status {status} not in list"

    return members.update_many(
        {'userid': userid, 'status': {'$ne': status}},  # Обновляем только если статус отличается
        {'$set': {'status': status}}, comment='update_all_user_track'
    )
