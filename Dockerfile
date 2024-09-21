# Необходимая версия python
FROM python:3.11-slim
# Рабочий каталог в контейнере
WORKDIR /bot
# Зависимости
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
# Файлы
COPY main.py .
# Каталоги
COPY fonts/ ./fonts/
COPY images/ ./images/
COPY tools/ ./tools/
COPY bot/ ./bot/
# Запуск
CMD ["python","-u","main.py"]