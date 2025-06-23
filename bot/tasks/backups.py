from bot.config import conf
from bot.modules.backup.bd_backup import cleanup_old_backups, create_mongo_dump
from bot.modules.backup.tg_base import send_backup, split_gz_archive
from bot.modules.logs import log
from bot.taskmanager import add_task

async def backups_file():
    cleanup_old_backups('/backups', 5)
    b_path = create_mongo_dump()

    splits = split_gz_archive(b_path)
    await send_backup(
        chat_id=conf.backup_group_id,
        parts=splits
    )
    
    log(f'Бэкап базы данных отправлен в группу {conf.backup_group_id}', 1)

if __name__ != '__main__':
    if conf.active_tasks:
        add_task(backups_file, specific_time='0:0')