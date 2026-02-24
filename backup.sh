#!/usr/bin/env bash
# backup.sh

set -euo pipefail

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

# Оставляем только последние 10 бэкапов (по timestamp в имени файла)
pushd "$BACKUP_DIR" >/dev/null
shopt -s nullglob
backups=(chroma_db_*.tar.gz)
if [ "${#backups[@]}" -gt 10 ]; then
    mapfile -t sorted_backups < <(printf '%s\n' "${backups[@]}" | sort -r)
    for old_backup in "${sorted_backups[@]:10}"; do
        rm -f -- "$old_backup"
    done
fi
popd >/dev/null

echo "✅ Backup complete"
