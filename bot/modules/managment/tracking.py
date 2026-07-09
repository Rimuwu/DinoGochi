
from bot.models.user import Lang
from bot.models.tracking import Link, TrackingMember
from bot.models.user import User
from bot.models.dinosaur import DinoOwners, Egg
from typing import Optional

from bson import ObjectId

from bot.modules.data_format import list_to_inline
from time import time, strftime, gmtime

from bot.modules.localization import t




async def creat_track(code: str, who_create: str = "system"):
    res = await Link.create_track(code, who_create)
    if res:
        # returns an object that has .inserted_id for compatibility
        class InsertedIdCompat:
            def __init__(self, obj_id):
                self.inserted_id = obj_id
        return InsertedIdCompat(res.id)
    return None

async def user_first_status(userid: int):
    return await TrackingMember.user_first_status(userid)

async def add_track_user(code: str, userid: int):
    res = await TrackingMember.add_track_user(code, userid)
    if res:
        class InsertedIdCompat:
            def __init__(self, obj_id):
                self.inserted_id = obj_id
        return InsertedIdCompat(res.id)
    return None

async def edit_track_user(code: str, userid: int, status: str):
    return await TrackingMember.edit_track_user(code, userid, status)

async def get_track_data(code: str):
    return await Link.get_track_data(code)

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
            concern_members_models = await TrackingMember.find(
                TrackingMember.track_id == concern_link['_id']
            ).to_list()
            concern_members = [m.dict() for m in concern_members_models]

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
    return await Link.delete_track(code)

async def track_info(code: str, lang: str):
    res = await Link.find_one(Link.code == code)
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
            concern_data = await Link.find_one(Link.id == data['concern'])
            if concern_data:
                concern_name = concern_data.code

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
        user_obj = await User.find_one(User.userid == user['userid'])
        if user_obj:
            user_lang = await Lang.find_one(Lang.userid == user_obj.userid)
            if user_lang:
                lang_code = user_lang.lang
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

        existing_track = await Link.find_one(Link.code == code)
        tracking_link_id = existing_track.id if existing_track else None


    user_res = await add_track_user(code, userid)
    user_tracking_id = user_res.inserted_id if user_res else None

    return tracking_link_id, user_tracking_id

async def get_track_pages(traks_dt: Optional[list[ObjectId]] = None) -> dict:
    if traks_dt is None:
        traks = await Link.find_all().to_list()
    else:
        traks = []
        for track_id in traks_dt:
            track = await Link.find_one(Link.id == track_id)
            if track:
                traks.append(track)

    buttons = {}
    for track in traks:
        buttons[track.code] = track.code

    return buttons

def update_all_user_track(userid: int, status: str):
    assert status in [
        "click_start",
        "create_account",
        "incubate",
        "delete_account",
        "gaming",
    ], f"Status {status} not in list"

    return TrackingMember.update_all_user_track(userid, status)
