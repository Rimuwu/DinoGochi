import datetime
import json
import os
import shutil
import subprocess
from typing import List

from bot.exec import bot
from bot.modules.logs import log
from aiogram.types import FSInputFile, BufferedInputFile
from io import BytesIO

def split_gz_archive(archive_path: str, part_size: str = "25M") -> List[str]:
    """
    Разделяет архив .gz на части с помощью split и возвращает список имён файлов.
    :param archive_path: Путь к исходному архиву .gz
    :param part_size: Размер каждой части (по умолчанию 25M)
    :return: Список имён файлов частей
    """
    temp_dir = 'bot/temp/'
    os.makedirs(temp_dir, exist_ok=True)
    base_name = os.path.join(temp_dir, "backup_part_")

    if not os.path.isfile(archive_path):
        raise FileNotFoundError(f"Файл {archive_path} не найден")

    subprocess.run([
        "split",
        "-b", part_size,
        archive_path,
        base_name
    ], check=True)

    # Получаем список файлов, отсортированных по имени
    parts = sorted([
        f for f in os.listdir(temp_dir)
        if f.startswith("backup_part_")
    ])
    # Возвращаем полные пути к файлам
    return [os.path.join(temp_dir, f) for f in parts]

def combine_backup_parts(parts: list, output_archive: str) -> None:
    """
    Объединяет части бэкапа в один архив с помощью cat.
    :param parts: Список путей к частям архива.
    :param output_archive: Имя итогового архива.
    """

    with open(output_archive, 'wb') as outfile:
        for part in parts:
            with open(part, 'rb') as infile:
                shutil.copyfileobj(infile, outfile)

async def send_backup(chat_id: int, parts: List[str]) -> None:
    """
    Отправляет части бэкапа в указанный чат.
    :param chat_id: ID чата, куда отправлять
    :param parts: Список частей бэкапа
    """
    bp_data = {
        'chat_id': chat_id,
        'timestamp': datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        'parts': {key: None for key in parts}
    }

    for part_number, part in enumerate(parts, start=1):
        try:
            m = await bot.send_document(
                chat_id=chat_id,
                document=FSInputFile(part),
                caption=f"Часть {part_number}/{len(parts)} бэкапа",
            )
            bp_data['parts'][part] = m.message_id

        except Exception as e:
            log(prefix='send_backup', message=f'Error sending backup part {part}: {e}', lvl=4)

        os.remove(part)  # Удаляем файл после отправки

    # Отправляем bp_data как файл без сохранения на диск
    bp_data_bytes = json.dumps(bp_data, ensure_ascii=False, 
                               indent=4).encode('utf-8')
    bp_data_file = BytesIO(bp_data_bytes)

    await bot.send_document(
        chat_id=chat_id,
        document=
        BufferedInputFile(bp_data_file.read(), 
                          filename=f'bp_data.json'),
        caption="Файл bp_data с информацией о частях бэкапа"
    )