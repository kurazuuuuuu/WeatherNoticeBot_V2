#!/bin/bash
# Discord Weather Bot セットアップスクリプト

set -e

echo "🌤️ Discord Weather Bot セットアップを開始します..."

# 必要なコマンドの確認
check_command() {
    if ! command -v $1 &> /dev/null; then
        echo "❌ $1 がインストールされていません"
        return 1
    else
        echo "✅ $1 が利用可能です"
        return 0
    fi
}

echo "🔍 必要なコマンドを確認しています..."
DOCKER_OK=true
UV_OK=true

if ! check_command docker; then
    DOCKER_OK=false
fi

if ! check_command docker-compose; then
    DOCKER_OK=false
fi

if ! check_command uv; then
    UV_OK=false
fi

# 環境変数ファイルのセットアップ
echo "📋 環境変数ファイルをセットアップしています..."
if [ ! -f .env ]; then
    if [ -f .env.docker ]; then
        cp .env.docker .env
        echo "✅ .env ファイルを作成しました"
    else
        echo "❌ .env.docker ファイルが見つかりません"
        exit 1
    fi
else
    echo "ℹ️  .env ファイルは既に存在します"
fi

# 必要なディレクトリを作成
echo "📁 必要なディレクトリを作成しています..."
mkdir -p data logs

# Docker環境のセットアップ
if [ "$DOCKER_OK" = true ]; then
    echo "🐳 Docker環境をセットアップしています..."
    
    # Dockerイメージをビルド
    echo "🔨 Dockerイメージをビルドしています..."
    docker-compose build
    
    echo "✅ Docker環境のセットアップが完了しました"
    echo ""
    echo "🚀 ボットを起動するには:"
    echo "   ./scripts/start.sh prod    # 本番モード"
    echo "   ./scripts/start.sh dev     # 開発モード"
else
    echo "⚠️  Docker/Docker Composeが利用できません"
    echo "   Dockerをインストールしてください: https://docs.docker.com/get-docker/"
fi

# ローカル開発環境のセットアップ
if [ "$UV_OK" = true ]; then
    echo "🐍 ローカル開発環境をセットアップしています..."
    
    # 依存関係のインストール
    echo "📦 依存関係をインストールしています..."
    uv sync
    
    # データベースマイグレーション
    echo "🗃️ データベースをセットアップしています..."
    uv run alembic upgrade head
    
    echo "✅ ローカル開発環境のセットアップが完了しました"
    echo ""
    echo "🚀 ローカルでボットを起動するには:"
    echo "   uv run python src/bot.py"
else
    echo "⚠️  uv が利用できません"
    echo "   uvをインストールしてください: https://docs.astral.sh/uv/getting-started/installation/"
fi

echo ""
echo "🔧 次のステップ:"
echo "1. .env ファイルを編集して必要な設定を行ってください"
echo "   - DISCORD_TOKEN: DiscordボットのトークンID（必須）"
echo "   - GEMINI_API_KEY: Google Gemini APIキー（オプション）"
echo ""
echo "2. Discord Developer Portalでボットの権限を設定してください"
echo "   - applications.commands (スラッシュコマンド)"
echo "   - bot (ボット基本権限)"
echo "   - View Channels, Send Messages, Embed Links"
echo ""
echo "3. ボットをDiscordサーバーに招待してください"
echo ""
echo "4. ボットを起動してください"
if [ "$DOCKER_OK" = true ]; then
    echo "   Docker: ./scripts/start.sh"
fi
if [ "$UV_OK" = true ]; then
    echo "   ローカル: uv run python src/bot.py"
fi
echo ""
echo "🎉 セットアップが完了しました！"