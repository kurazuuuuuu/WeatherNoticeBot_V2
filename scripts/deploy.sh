#!/bin/bash

# Discord Weather Bot デプロイスクリプト
# データベースを保持したままアプリケーションを更新します

set -e

echo "=== Discord Weather Bot デプロイ開始 ==="

# 現在のディレクトリを確認
if [ ! -f "docker-compose.yml" ]; then
    echo "エラー: docker-compose.ymlが見つかりません。プロジェクトルートで実行してください。"
    exit 1
fi

# 環境変数ファイルの確認
if [ ! -f ".env" ]; then
    echo "警告: .envファイルが見つかりません。.env.exampleを参考に作成してください。"
fi

echo "1. 現在のコンテナを停止中..."
docker compose down

echo "2. 最新のイメージをビルド中..."
docker compose build --no-cache

echo "3. データベースボリュームの確認..."
# データベースボリュームが存在するかチェック
if docker volume ls | grep -q "weather_bot_data"; then
    echo "   データベースボリュームが存在します: weather_bot_data"
else
    echo "   データベースボリュームを作成します: weather_bot_data"
    docker volume create weather_bot_data
fi

# ログボリュームの確認
if docker volume ls | grep -q "weather_bot_logs"; then
    echo "   ログボリュームが存在します: weather_bot_logs"
else
    echo "   ログボリュームを作成します: weather_bot_logs"
    docker volume create weather_bot_logs
fi

echo "4. コンテナを起動中..."
docker compose up -d

echo "5. コンテナの起動を待機中..."
sleep 10

echo "6. コンテナの状態を確認中..."
docker compose ps

echo "7. ログの確認..."
docker compose logs --tail=20 weather-bot

echo "=== デプロイ完了 ==="
echo ""
echo "コンテナの状態確認: docker compose ps"
echo "ログの確認: docker compose logs -f weather-bot"
echo "コンテナに接続: docker compose exec weather-bot bash"
echo ""