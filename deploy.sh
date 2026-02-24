#!/bin/bash
# deploy.sh

set -e

echo "🚀 GrantFlow Production Deployment"
echo "=================================="

# Проверка Docker
if ! command -v docker &> /dev/null; then
    echo "❌ Docker not installed"
    exit 1
fi

# Проверка docker-compose
if ! command -v docker-compose &> /dev/null; then
    echo "❌ docker-compose not installed"
    exit 1
fi

# Проверка .env
if [ ! -f .env ]; then
    echo "⚠️  .env not found, copying from .env.example"
    cp .env.example .env
    echo "   Please edit .env with your API keys"
fi

echo "✅ Pre-flight checks passed"

# Сборка
echo "📦 Building Docker image..."
docker-compose build

# Запуск
echo "🏃 Starting services..."
docker-compose up -d

# Проверка здоровья
echo "⏳ Waiting for services to start..."
sleep 10

echo "🏥 Checking health..."
curl -f http://localhost:8000/health || {
    echo "❌ Health check failed"
    docker-compose logs api
    exit 1
}

echo ""
echo "✅ Deployment complete!"
echo "   API: http://localhost:8000"
echo "   Docs: http://localhost:8000/docs"
echo ""
echo "📊 View logs: docker-compose logs -f"
echo "🛑 Stop: docker-compose down"
