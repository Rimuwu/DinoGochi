import asyncio
import datetime
import os

from bot.config import conf
from bot.taskmanager import add_task
from bot.modules.bd_backup import create_mongo_dump, send_backup_to_topic, cleanup_old_backups
from bot.modules.logs import log

# 12 hours in seconds
REPEAT_SECONDS = 12 * 3600

def get_seconds_to_next_12():
    now = datetime.datetime.now()
    candidates = []
    
    # candidate 1: today at 12:00 (noon)
    dt1 = now.replace(hour=12, minute=0, second=0, microsecond=0)
    if dt1 > now:
        candidates.append(dt1)
        
    # candidate 2: today at 24:00 (midnight) -> tomorrow 00:00
    dt2 = (now + datetime.timedelta(days=1)).replace(hour=0, minute=0, second=0, microsecond=0)
    if dt2 > now:
        candidates.append(dt2)
        
    # candidate 3: tomorrow at 12:00
    dt3 = (now + datetime.timedelta(days=1)).replace(hour=12, minute=0, second=0, microsecond=0)
    if dt3 > now:
        candidates.append(dt3)
        
    next_12 = min(candidates)
    return int((next_12 - now).total_seconds())

async def auto_backup_database():
    connection_string = conf.mongo_url
    log("Запуск автоматического бэкапа базы данных...", lvl=1)
    try:
        backup_path = create_mongo_dump(connection_string=connection_string)
        log(f"Автоматический бэкап создан: {backup_path}. Отправка в топик...", lvl=1)
        await send_backup_to_topic(backup_path)
        log("Автоматический бэкап успешно отправлен в топик.", lvl=1)
        
        # Cleanup old backups (keep 10 backups)
        cleanup_old_backups("/backups", max_files=10)
    except Exception as e:
        log(f"Ошибка при автоматическом бэкапе базы данных: {e}", lvl=4)

if __name__ != '__main__':
    if conf.active_tasks:
        delay = get_seconds_to_next_12()
        log(f"Автоматический бэкап запланирован раз в 12 часов. До следующего запуска (в 12:00/00:00): {delay} сек.", lvl=1)
        add_task(auto_backup_database, REPEAT_SECONDS, delay)
