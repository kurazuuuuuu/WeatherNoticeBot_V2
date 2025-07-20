#!/bin/bash
# Discord Weather Bot 起動スクリプト

set -e

echo "🌤️ Discord Weather Bot を起動しています..."

# 環境変数ファイルの確認
if [ ! -f .env ]; then
    echo "⚠️  .env ファイルが見つかりません"
    if [ -f .env.docker ]; then
        echo "📋 .env.docker をコピーして .env を作成します"
        cp .env.docker .env
        echo "✅ .env ファイルを作成しました"
        echo "🔧 .env ファイルを編集して必要な設定を行ってください"
        echo "   - DISCORD_TOKEN: DiscordボットのトークンID"
        echo "   - GEMINI_API_KEY: Google Gemini APIキー（オプション）"
        exit 1
    else
        echo "❌ .env.docker ファイルも見つかりません"
        exit 1
    fi
fi

# 必要なディレクトリを作成
echo "📁 必要なディレクトリを作成しています..."
mkdir -p data logs

# Docker Composeでサービスを起動
echo "🐳 Docker Composeでサービスを起動しています..."

# 引数に応じて起動モードを選択
case "${1:-prod}" in
    "dev"|"development")
        echo "🔧 開発モードで起動します"
        docker-compose -f docker-compose.dev.yml up --build
        ;;
    "prod"|"production")
        echo "🚀 本番モードで起動します"
        docker-compose up -d --build
        echo "✅ サービスが起動しました"
        echo ""
        echo "📊 サービス状態:"
        docker-compose ps
        echo ""
        echo "📝 ログを確認するには:"
        echo "   docker-compose logs -f weather-bot"
        echo ""
        echo "🛑 サービスを停止するには:"
        echo "   docker-compose down"
        ;;
    "stop")
        echo "🛑 サービスを停止しています..."
        docker-compose down
        docker-compose -f docker-compose.dev.yml down 2>/dev/null || true
        echo "✅ サービスを停止しました"
        ;;
    "restart")
        echo "🔄 サービスを再起動しています..."
        docker-compose down
        docker-compose up -d --build
        echo "✅ サービスを再起動しました"
        ;;
    "logs")
        echo "📝 ログを表示しています..."
        docker-compose logs -f weather-bot
        ;;
    "status")
        echo "📊 サービス状態:"
        docker-compose ps
        ;;
    *)
        echo "使用方法: $0 [dev|prod|stop|restart|logs|status]"
        echo ""
        echo "コマンド:"
        echo "  dev      - 開発モードで起動"
        echo "  prod     - 本番モードで起動（デフォルト）"
        echo "  stop     - サービスを停止"
        echo "  restart  - サービスを再起動"
        echo "  logs     - ログを表示"
        echo "  status   - サービス状態を表示"
        exit 1
        ;;
esac