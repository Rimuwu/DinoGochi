import shutil
import subprocess
import datetime
import os
from typing import Optional

standart_path = "/backups"

def create_mongo_dump(
    connection_string: str,
    prefix: str = "", 
    alternative_path: Optional[str] = None,
    save_as_last: bool = True
                      ) -> str:
    """
    Создает дамп всей базы MongoDB с именем файла в виде даты и времени.\n
    :param db_name: Имя базы данных MongoDB.
    :param backup_dir: Папка для сохранения дампа.
    :param prefix: Префикс для имени файла дампа.
    :param alternative_path: Альтернативный имя для сохранения дампа.
    :param save_as_last: Если True, сохраняет копию дампа как последний бэкап.
    :param connection_string: Строка подключения к MongoDB.
    :return: Путь к созданному дампу.
    """

    os.makedirs(standart_path, exist_ok=True)
    timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")

    if not alternative_path:
        backup_path = os.path.join(
            standart_path, f"{prefix}mongo_backup_{timestamp}.gz")
    else:
        backup_path = os.path.join(
            standart_path, f"{alternative_path}.gz")

    command = [
        "mongodump",
        "--uri", connection_string,
        "--archive=" + backup_path,
        "--gzip"
    ]

    try:
        subprocess.run(
            command, check=True, capture_output=True, text=True)
    except subprocess.CalledProcessError as e:
        print(f"Error running mongodump: {e.stderr}")
        raise e

    if save_as_last:
        # Копируем дамп как последний
        last_backup_path = os.path.join(
            standart_path, "last_mongo_backup.gz")
        if os.path.exists(last_backup_path):
            os.remove(last_backup_path)

        shutil.copy2(backup_path, last_backup_path)

    return backup_path

def restore_mongo_dump(
    path_name: str, 
    connection_string: str
    ) -> None:
    """
    Восстанавливает базу данных MongoDB из дампа.\n

    :param backup_path: Путь к архиву дампа.
    :param connection_string: Строка подключения к MongoDB.
    """
    # Создаем бэкап текущей базы перед восстановлением
    create_mongo_dump(
        connection_string=connection_string, prefix="before_restore_"
        )

    command = [
        "mongorestore",
        "--uri", connection_string,
        "--archive=" + standart_path + "/" + path_name,
        "--gzip",
        "--drop"
    ]

    subprocess.run(command, check=True)


def cleanup_old_backups(
    backup_dir: str, 
    max_files: int = 10, 
    exclude_last: bool = True
    ) -> None:
    """
    Удаляет самые старые файлы бэкапов в папке, оставляя только max_files последних.\n

    :param backup_dir: Папка с бэкапами
    :param max_files: Максимальное количество файлов для хранения
    :param exclude_last: Не удалять файл с именем 'last' (без расширения)
    """
    if not os.path.isdir(backup_dir):
        raise ValueError(f"Backup directory {backup_dir} does not exist or is not a directory.")

    files = [
        f for f in os.listdir(backup_dir)
        if os.path.isfile(os.path.join(backup_dir, f))
    ]

    if exclude_last:
        files = [f for f in files if not f.startswith('last')]

    files_with_mtime = [
        (f, os.path.getmtime(os.path.join(backup_dir, f)))
        for f in files
    ]
    files_with_mtime.sort(key=lambda x: x[1])  # по времени модификации (старые первыми)

    to_delete = len(files_with_mtime) - max_files
    for i in range(to_delete):
        file_path = os.path.join(
            backup_dir, files_with_mtime[i][0])
        try:
            os.remove(file_path)
        except Exception as e:
            print(f"Error deleting file {file_path}: {e}")