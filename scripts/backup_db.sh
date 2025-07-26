#!/bin/bash

# Discord Weather Bot データベースバックアップスクリプト

set -e

BACKUP_DIR="./backups"
TIMESTAMP=$(date +"%Y%m%d_%H%M%S")
BACKUP_FILE="weather_bot_backup_${TIMESTAMP}.db"

echo "=== データベースバックアップ開始 ==="

# バックアップディレクトリを作成
mkdir -p "$BACKUP_DIR"

# コンテナが実行中かチェック
if ! docker compose ps | grep -q "weather-bot.*Up"; then
    echo "エラー: weather-botコンテナが実行されていません"
    exit 1
fi

echo "1. データベースファイルをコピー中..."
docker compose exec weather-bot cp /app/data/weather_bot.db /tmp/backup.db

echo "2. バックアップファイルを取得中..."
docker compose cp weather-bot:/tmp/backup.db "$BACKUP_DIR/$BACKUP_FILE"

echo "3. 一時ファイルを削除中..."
docker compose exec weather-bot rm -f /tmp/backup.db

echo "=== バックアップ完了 ==="
echo "バックアップファイル: $BACKUP_DIR/$BACKUP_FILE"

# 古いバックアップファイルを削除（7日以上古いもの）
echo "4. 古いバックアップファイルを削除中..."
find "$BACKUP_DIR" -name "weather_bot_backup_*.db" -mtime +7 -delete

echo "現在のバックアップファイル:"
ls -la "$BACKUP_DIR"/weather_bot_backup_*.db 2>/dev/null || echo "バックアップファイルがありません"