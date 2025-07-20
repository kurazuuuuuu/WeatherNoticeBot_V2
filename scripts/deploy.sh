#!/bin/bash

# Discord Weather Bot デプロイスクリプト
# 使用方法: ./scripts/deploy.sh [環境]
# 環境: prod (本番環境, デフォルト) | dev (開発環境)

set -e  # エラー時に停止

# 設定
ENVIRONMENT=${1:-prod}
PROJECT_NAME="discord-weather-bot"
LOG_FILE="logs/deploy.log"

# ログ関数
log() {
    echo "[$(date '+%Y-%m-%d %H:%M:%S')] $1" | tee -a "$LOG_FILE"
}

# エラーハンドリング
error_exit() {
    log "❌ エラー: $1"
    exit 1
}

# メイン処理開始
log "🚀 Discord Weather Bot デプロイを開始します..."
log "環境: $ENVIRONMENT"

# 環境に応じた設定
if [ "$ENVIRONMENT" = "dev" ]; then
    COMPOSE_FILE="docker-compose.dev.yml"
    SERVICE_NAME="weather-bot-dev"
else
    COMPOSE_FILE="docker-compose.yml"
    SERVICE_NAME="weather-bot"
fi

log "使用するCompose ファイル: $COMPOSE_FILE"

# 前提条件チェック
log "📋 前提条件をチェック中..."

# Dockerの確認
if ! command -v docker &> /dev/null; then
    error_exit "Dockerがインストールされていません"
fi

# Docker Composeの確認
if ! command -v docker compose &> /dev/null; then
    error_exit "Docker Composeがインストールされていません"
fi

# 環境変数ファイルの確認
if [ ! -f .env ]; then
    log "⚠️  警告: .envファイルが見つかりません"
    log "📝 .env.exampleを参考に.envファイルを作成してください"
    
    # 対話的に作成するか確認
    read -p "続行しますか？ (y/N): " -n 1 -r
    echo
    if [[ ! $REPLY =~ ^[Yy]$ ]]; then
        error_exit "デプロイを中止しました"
    fi
fi

# 既存のコンテナを停止
log "🛑 既存のコンテナを停止中..."
if [ "$ENVIRONMENT" = "dev" ]; then
    docker compose -f "$COMPOSE_FILE" down || log "既存のコンテナが見つかりませんでした"
else
    docker compose down || log "既存のコンテナが見つかりませんでした"
fi

# イメージのビルド
log "🔨 Dockerイメージをビルド中..."
if [ "$ENVIRONMENT" = "dev" ]; then
    docker compose -f "$COMPOSE_FILE" build --no-cache
else
    docker compose build --no-cache
fi

# アプリケーションの起動
log "▶️  アプリケーションを起動中..."
if [ "$ENVIRONMENT" = "dev" ]; then
    docker compose -f "$COMPOSE_FILE" up -d
else
    docker compose up -d
fi

# 起動待機
log "⏳ アプリケーションの起動を待機中..."
sleep 15

# ヘルスチェック
log "🏥 ヘルスチェックを実行中..."
max_attempts=30
attempt=1

while [ $attempt -le $max_attempts ]; do
    if [ "$ENVIRONMENT" = "dev" ]; then
        status=$(docker compose -f "$COMPOSE_FILE" ps --format json | jq -r '.[0].State' 2>/dev/null || echo "unknown")
    else
        status=$(docker compose ps --format json | jq -r '.[] | select(.Service=="weather-bot") | .State' 2>/dev/null || echo "unknown")
    fi
    
    if [[ "$status" == *"running"* ]] || [[ "$status" == *"healthy"* ]]; then
        log "✅ アプリケーションが正常に起動しました！"
        break
    else
        log "⏳ 起動を待機中... ($attempt/$max_attempts) - 状態: $status"
        sleep 10
        attempt=$((attempt + 1))
    fi
done

if [ $attempt -gt $max_attempts ]; then
    log "❌ アプリケーションの起動に失敗しました"
    log "📋 コンテナの状態:"
    if [ "$ENVIRONMENT" = "dev" ]; then
        docker compose -f "$COMPOSE_FILE" ps
        log "📋 ログ:"
        docker compose -f "$COMPOSE_FILE" logs --tail=50 "$SERVICE_NAME"
    else
        docker compose ps
        log "📋 ログ:"
        docker compose logs --tail=50 "$SERVICE_NAME"
    fi
    error_exit "デプロイに失敗しました"
fi

# デプロイ完了
log "🎉 デプロイが完了しました！"
log "📊 コンテナの状態:"
if [ "$ENVIRONMENT" = "dev" ]; then
    docker compose -f "$COMPOSE_FILE" ps
else
    docker compose ps
fi

log "📋 最新のログ:"
if [ "$ENVIRONMENT" = "dev" ]; then
    docker compose -f "$COMPOSE_FILE" logs --tail=10 "$SERVICE_NAME"
else
    docker compose logs --tail=10 "$SERVICE_NAME"
fi

log "✨ デプロイが正常に完了しました！"