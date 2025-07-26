#!/bin/bash

# Discord Weather Bot データベース復元スクリプト

set -e

if [ $# -ne 1 ]; then
    echo "使用方法: $0 <バックアップファイル>"
    echo "例: $0 ./backups/weather_bot_backup_20241226_120000.db"
    exit 1
fi

BACKUP_FILE="$1"

if [ ! -f "$BACKUP_FILE" ]; then
    echo "エラー: バックアップファイルが見つかりません: $BACKUP_FILE"
    exit 1
fi

echo "=== データベース復元開始 ==="
echo "バックアップファイル: $BACKUP_FILE"

# 確認
read -p "本当にデータベースを復元しますか？現在のデータは失われます。(y/N): " -n 1 -r
echo
if [[ ! $REPLY =~ ^[Yy]$ ]]; then
    echo "復元をキャンセルしました"
    exit 1
fi

# コンテナを停止
echo "1. コンテナを停止中..."
docker compose down

echo "2. バックアップファイルをコンテナにコピー中..."
# 一時的にコンテナを起動してファイルをコピー
docker compose run --rm weather-bot bash -c "mkdir -p /app/data"
docker compose cp "$BACKUP_FILE" weather-bot:/app/data/weather_bot.db

echo "3. コンテナを再起動中..."
docker compose up -d

echo "4. 復元の確認..."
sleep 5
docker compose logs --tail=10 weather-bot

echo "=== データベース復元完了 ==="