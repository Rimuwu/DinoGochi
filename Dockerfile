FROM python:3.11-slim

WORKDIR /bot

COPY requirements.txt .

RUN pip install --no-cache-dir -r requirements.txt

COPY main.py .

COPY fonts/ ./fonts/
COPY images/ ./images/
COPY tools/ ./tools/
COPY bot/ ./bot/


CMD ["python", "main.py"]
