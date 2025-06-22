import subprocess
import datetime
import os
from typing import Optional

from bot.modules.time_counter import time_counter
import shutil
from bot.config import conf

standart_path = "/backups"

def create_mongo_dump(prefix: str = "", alternative_path: Optional[str] = None,
                      save_as_last: bool = True
                      ) -> str:
    """
    Создает дамп всей базы MongoDB с именем файла в виде даты и времени.
    :param db_name: Имя базы данных MongoDB.
    :param backup_dir: Папка для сохранения дампа.
    :param prefix: Префикс для имени файла дампа.
    :param alternative_path: Альтернативный имя для сохранения дампа.
    :param save_as_last: Если True, сохраняет копию дампа как последний бэкап.
    :return: Путь к созданному дампу.
    """
    os.makedirs(standart_path, exist_ok=True)
    timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
    if not alternative_path:
        backup_path = os.path.join(standart_path, f"{prefix}mongo_backup_{timestamp}.gz")
    else:
        backup_path = os.path.join(standart_path, f"{alternative_path}.gz")

    command = [
        "mongodump",
        "--uri", conf.mongo_url,
        "--archive=" + backup_path,
        "--gzip"
    ]

    time_counter('create_mongo_dump', f'Дамп базы данных в {backup_path}')
    try:
        subprocess.run(command, check=True, capture_output=True, text=True)
    except subprocess.CalledProcessError as e:
        print(f"Error running mongodump: {e.stderr}")
        raise

    time_counter('create_mongo_dump', f'Дамп базы данных')

    if save_as_last:
        # Копируем дамп как последний
        last_backup_path = os.path.join(standart_path, "last_mongo_backup.gz")
        if os.path.exists(last_backup_path):
            os.remove(last_backup_path)
        shutil.copy2(backup_path, last_backup_path)

    return backup_path

def restore_mongo_dump(path_name: str) -> None:
    """
    Восстанавливает базу данных MongoDB из дампа.
    :param db_name: Имя базы данных MongoDB.
    :param backup_path: Путь к архиву дампа.
    """
    # Создаем бэкап текущей базы перед восстановлением
    time_counter('create_mongo_dump_restore', f'Дамп базы данных в {standart_path}')
    create_mongo_dump(prefix="restore_")
    time_counter('create_mongo_dump_restore', f'Дамп базы данных в {standart_path}')

    command = [
        "mongorestore",
        "--uri", conf.mongo_url,
        "--archive=" + standart_path + "/" + path_name,
        "--gzip",
        "--drop"
    ]

    time_counter('create_mongo_dump_restore', f'Восстановление дампа базы в {standart_path}')
    subprocess.run(command, check=True)

    time_counter('create_mongo_dump_restore', f'Восстановление дампа базы  в {standart_path}')