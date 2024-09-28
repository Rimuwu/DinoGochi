import asyncio
import io
import os

import aiofiles
import telebot.types

from bot.config import conf
from bot.exec import bot
from bot.modules.logs import (MAX_ERRORS, get_errors_count,
                              get_errors_last_count, get_last_errors, log)
from bot.taskmanager import add_task

REPEAT_MINUTES = 60
DELAY = 10

# Создание отчета из последних ошибок и файла логов
async def create_report():
    # Получаем последние ошибки
    errors = get_last_errors()

    # Формируем текст отчета по ошибкам
    errors_text = ''
    if errors:
        for i in range(len(errors)): errors_text += f"{i+1}) `{errors[i]}`\n"
    else: errors_text = 'Ошибок нет, так держать!'
    errors_report_text = f'Отчет по работе бота за `{REPEAT_MINUTES}м`:\nВсего ошибок `{get_errors_count()}`\nОшибок с последнего отчета: `{get_errors_last_count()}`\nПоследние `{MAX_ERRORS}` ошибок:\n\n{errors_text}'

    # Получаем список файлов логов
    logs = os.listdir(conf.logs_dir)
    if not logs: 
        log("Файлы логов не найдены", 2)
    # Массив задач для асинхронной отправки сообщений
    tasks = []

    for dev in conf.bot_devs:
        tasks.append(bot.send_message(dev, f'{errors_report_text}', parse_mode='Markdown'))

    if logs:
        try:
            # Открываем последний лог файл
            async with aiofiles.open(f'{conf.logs_dir}/{logs[-1]}', mode='rb') as f:
                last_log_content = await f.read()  # Читаем содержимое файла
                last_log = telebot.types.InputFile(io.BytesIO(last_log_content), file_name=logs[-1])

                # Формируем задачи для отправки логов
                for dev in conf.bot_devs:
                    tasks.append(bot.send_document(dev, last_log))

        except Exception as e:
            log(f"Ошибка при чтении файла лога: {e}", 3)

    await asyncio.gather(*tasks)


if __name__ != '__main__':
    if conf.active_tasks:
        add_task(create_report, REPEAT_MINUTES * 60, DELAY)