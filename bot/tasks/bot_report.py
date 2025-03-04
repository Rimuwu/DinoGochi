import asyncio
import io
import os

import aiofiles
import aiogram.types

from bot.config import conf
from bot.exec import main_router, bot
from bot.modules.logs import (MAX_ERRORS, get_errors_count,
                              get_latest_errors_dif, get_latest_errors, log)
from bot.taskmanager import add_task

REPEAT_MINUTES = 60
DELAY = 300

# Рассылка сообщения разрабу или дев группу
async def report_message(message: str):
    # id рассылки
    report_id = conf.bot_report_id

    tasks = []
    if isinstance(report_id, str):
        channel_id, topic_id = report_id.split('_', 2)
        tasks.append(bot.send_message(channel_id, message, parse_mode='Markdown', message_thread_id=int(topic_id)))
    else: 
        tasks.append(bot.send_message(report_id, message, parse_mode='Markdown'))

    await asyncio.gather(*tasks)


# Рассылка файла логов разрабу или дев группу
async def report_file(file_path: str, file_name: str):
    # id рассылки
    report_id = conf.bot_report_id

    tasks = []
    # Формируем задачи для отправки логов
    try:
            # Открываем последний лог файл
        async with aiofiles.open(f'{file_path}/{file_name}', mode='rb') as f:
            last_log_content = await f.read()  # Читаем содержимое файла
            last_log = aiogram.types.InputFile(io.BytesIO(last_log_content), filename=file_name)
            if isinstance(report_id, str):
                channel_id, topic_id = report_id.split('_', 2)
                tasks.append(bot.send_document(channel_id, last_log, message_thread_id=int(topic_id)))
            else: 
                tasks.append(bot.send_document(report_id, last_log))

    except Exception as e:
        log(f"Ошибка при чтении файла лога: {e}", 3)

    await asyncio.gather(*tasks)

# Создание отчета из последних ошибок и файла логов
async def create_report():
    # Получаем последние ошибки
    errors = get_latest_errors()

    # Формируем текст отчета по ошибкам
    errors_text = ''
    errors_count = 0
    if errors:
        for i in range(len(errors)): 
            s = f"{i+1}) ```{errors[i]}```\n"
            if len(errors_text + s) > 3840:  
                break
            errors_count = i + 1
            errors_text += s
    else: errors_text = 'Ошибок нет, так держать!'
    errors_report_text = f'Отчет по работе бота за `{REPEAT_MINUTES}м`:\nВсего ошибок `{get_errors_count()}`\nОшибок с последнего отчета: `{get_latest_errors_dif()}`\nПоследние `{errors_count}` ошибок:\n\n{errors_text}'

    await report_message(errors_report_text)

    # Получаем список файлов логов
    log_files = os.listdir(conf.logs_dir)
    latest_log_file = max(log_files, key=lambda x: os.path.getctime(os.path.join(conf.logs_dir, x)))
    if not latest_log_file: 
        log("Файлы логов не найдены", 2)
    # Массив задач для асинхронной отправки сообщений

    if latest_log_file:
        await report_file(conf.logs_dir, latest_log_file)


if __name__ != '__main__':
    if conf.active_tasks:
        add_task(create_report, REPEAT_MINUTES * 60, DELAY)