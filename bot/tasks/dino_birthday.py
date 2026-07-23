"""
Периодическая проверка дней рождения динозавров.
Выполняется 1 раз в сутки.
День рождения вычисляется строго по created_at (без учета доп. дней от эликсиров).
"""
import datetime
from bot.models.dinosaur import Dino, DinoMood, DinoOwners
from bot.models.enums import DinoOwnerType
from bot.modules.localization import t, get_lang
from bot.exec import bot
from bot.taskmanager import add_task
from bot.config import conf


async def check_dino_birthdays():
    now = datetime.datetime.now(datetime.timezone.utc)
    today_month, today_day, current_year = now.month, now.day, now.year

    dinos = await Dino.find().to_list()
    for dino in dinos:
        try:
            created_ts = dino.created_at or int(dino.id.generation_time.timestamp())
            birth_dt = datetime.datetime.fromtimestamp(created_ts, tz=datetime.timezone.utc)

            # Проверяем совпадение месяца и дня (и что с момента рождения прошёл хотя бы 1 год)
            if birth_dt.month == today_month and birth_dt.day == today_day and current_year > birth_dt.year:
                last_year = dino.notifications.get('last_birthday_year', 0)
                if last_year != current_year:
                    age_years = current_year - birth_dt.year
                    # Настроение +20 на 24 часа
                    await DinoMood.add(dino.id, 'birthday', 20, 86400)
                    # Фиксируем год
                    await dino.save_notification('last_birthday_year', current_year)

                    # Находим владельца
                    owner_conn = await DinoOwners.find_one(
                        DinoOwners.dino.id == dino.id,
                        DinoOwners.type == DinoOwnerType.OWNER
                    )
                    if owner_conn:
                        owner_id = owner_conn.owner_id
                        lang = await get_lang(owner_id)
                        text = t(
                            'dino_birthday.notification', lang,
                            name=dino.name, years=age_years,
                            default=f"🎂 <b>С Днём Рождения, {dino.name}!</b> 🎉\n\nСегодня твоему любимому динозавру исполнилось <b>{age_years}</b> год(а)! 🎈\nВ честь праздника настроение динозавра повышено на +20 на весь день! 🥳✨"
                        )
                        try:
                            await bot.send_message(owner_id, text)
                        except Exception:
                            pass
        except Exception:
            pass


if __name__ != '__main__':
    if conf.active_tasks:
        add_task(check_dino_birthdays, 86400, 30.0)
