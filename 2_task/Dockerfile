FROM python:3.12-slim

RUN apt-get update && apt-get install -y \
    build-essential \
    libpq-dev \
    gcc \
    curl \
    git \
    gnupg \
    docker \
    lsb-release \
    && apt-get clean \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
RUN pip install pytest pytest-asyncio

# Копируем исходный код в контейнер
COPY .. .

RUN pytest -vv

# Указываем команду для запуска приложения
CMD ["python3", "main.py"]
