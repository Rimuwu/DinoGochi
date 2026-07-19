# Необходимая версия python
FROM python:3.11-slim
# Рабочий каталог в контейнере
WORKDIR /bot

# Отключение внутреннего буфера питона
ENV PYTHONUNBUFFERED=1

RUN apt-get update && apt-get install -y curl gnupg gcc g++ zlib1g-dev libjpeg62-turbo-dev && \
	curl -fsSL https://www.mongodb.org/static/pgp/server-8.0.asc | gpg --dearmor | tee /etc/apt/trusted.gpg.d/mongodb-org.gpg > /dev/null && \
	echo "deb [ arch=amd64,arm64 signed-by=/etc/apt/trusted.gpg.d/mongodb-org.gpg ] https://repo.mongodb.org/apt/debian bookworm/mongodb-org/8.0 main" | tee /etc/apt/sources.list.d/mongodb-org-8.0.list && \
	apt-get update && apt-get install -y mongodb-database-tools && \
	rm -rf /var/lib/apt/lists/*

RUN pip install --no-cache-dir --upgrade pip uv

# Копируем и устанавливаем зависимости
COPY requirements.txt .
RUN uv pip install -r requirements.txt --system

# Файлы
COPY main.py .
COPY bot/ ./bot/

# Запуск
CMD ["python", "main.py"]
