#!/usr/bin/env bash
# deploy.sh

set -euo pipefail

echo "🚀 GrantFlow Production Deployment"
echo "=================================="

# Проверка Docker
if ! command -v docker >/dev/null 2>&1; then
    echo "❌ Docker not installed"
    exit 1
fi

compose() {
    if command -v docker-compose >/dev/null 2>&1; then
        docker-compose "$@"
        return
    fi

    if docker compose version >/dev/null 2>&1; then
        docker compose "$@"
        return
    fi

    echo "❌ docker-compose (or 'docker compose') not installed"
    exit 1
}

# Проверка .env
if [ ! -f .env ]; then
    echo "⚠️  .env not found, copying from .env.example"
    cp .env.example .env
    echo "   Please edit .env with your API keys"
fi

echo "✅ Pre-flight checks passed"

# Сборка
echo "📦 Building Docker image..."
compose build

# Запуск
echo "🏃 Starting services..."
compose up -d

# Проверка здоровья
echo "⏳ Waiting for services to start..."
sleep 10

echo "🏥 Checking health..."
curl -fsS http://localhost:8000/health || {
    echo "❌ Health check failed"
    compose logs api
    exit 1
}

echo ""
echo "✅ Deployment complete!"
echo "   API: http://localhost:8000"
echo "   Docs: http://localhost:8000/docs"
echo ""
echo "📊 View logs: docker compose logs -f"
echo "🛑 Stop: docker compose down"
