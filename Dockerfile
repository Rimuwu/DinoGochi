# Необходимая версия python
FROM python:3.13.5-slim

# Рабочий каталог в контейнере
WORKDIR /bot

# Отключение внутреннего буфера питона
ENV PYTHONUNBUFFERED=1

RUN apt-get update && apt-get install -y wget gnupg && \
	wget -qO - https://www.mongodb.org/static/pgp/server-6.0.asc | apt-key add - && \
	echo "deb [ arch=amd64,arm64 ] https://repo.mongodb.org/apt/debian bookworm/mongodb-org/6.0 main" | tee /etc/apt/sources.list.d/mongodb-org-6.0.list && \
	apt-get update && apt-get install -y mongodb-database-tools && \
	rm -rf /var/lib/apt/lists/*

# Зависимости
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Файлы
COPY main.py .

# Каталоги
COPY fonts/ ./fonts/
COPY images/ ./images/
COPY bot/ ./bot/

# Запуск
CMD ["python", "main.py"]
