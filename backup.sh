#!/bin/bash
# backup.sh

set -e

BACKUP_DIR="./backups"
TIMESTAMP=$(date +%Y%m%d_%H%M%S)

echo "💾 Backing up ChromaDB data..."

mkdir -p "$BACKUP_DIR"

# Копируем данные ChromaDB
if [ -d "./chroma_db" ]; then
    tar -czf "$BACKUP_DIR/chroma_db_$TIMESTAMP.tar.gz" ./chroma_db
    echo "✅ Backup created: $BACKUP_DIR/chroma_db_$TIMESTAMP.tar.gz"
else
    echo "⚠️  chroma_db directory not found"
fi

# Оставляем только последние 10 бэкапов
cd "$BACKUP_DIR"
ls -t chroma_db_*.tar.gz 2>/dev/null | tail -n +11 | xargs -r rm
cd -

echo "✅ Backup complete"
