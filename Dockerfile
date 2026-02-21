# Dockerfile

FROM python:3.11-slim

WORKDIR /app

# Системные зависимости
RUN apt-get update && apt-get install -y \
    gcc \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Копируем requirements
COPY aidgraph/requirements.txt .

# Устанавливаем Python-зависимости
RUN pip install --no-cache-dir -r requirements.txt

# Копируем код
COPY . .

# Создаём директорию для ChromaDB
RUN mkdir -p /app/chroma_db

# Переменные окружения по умолчанию
ENV AIDGRAPH_API_HOST=0.0.0.0
ENV AIDGRAPH_API_PORT=8000
ENV AIDGRAPH_DEBUG=false
ENV AIDGRAPH_CHROMA_DIR=/app/chroma_db

# Открываем порт
EXPOSE 8000

# Запуск
CMD ["uvicorn", "aidgraph.api.app:app", "--host", "0.0.0.0", "--port", "8000"]
