# Используем стабильный Python 3.11
FROM python:3.11-slim

# Устанавливаем системные зависимости
RUN apt-get update && apt-get install -y \
    build-essential \
    gcc \
    && rm -rf /var/lib/apt/lists/*

# Создаём рабочую директорию
WORKDIR /app

# Копируем зависимости
COPY requirements.txt .

# Обновляем pip и устанавливаем зависимости
RUN pip install --upgrade pip \
    && pip install -r requirements.txt

# Копируем код
COPY . .

# Команда по умолчанию
CMD ["python", "main.py"]
