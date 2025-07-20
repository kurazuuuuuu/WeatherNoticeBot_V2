#!/bin/bash

# デプロイメント環境チェックスクリプト
# GitHub Actions self-hosted runnerの設定状況を確認

set -e

# 色付きログ関数
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

log_info() {
    echo -e "${BLUE}[INFO]${NC} $1"
}

log_success() {
    echo -e "${GREEN}[SUCCESS]${NC} $1"
}

log_warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1"
}

log_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

# ヘッダー
echo "=================================================="
echo "Discord Weather Bot デプロイメント環境チェック"
echo "=================================================="

# 1. Docker環境の確認
log_info "Docker環境をチェック中..."

if command -v docker &> /dev/null; then
    DOCKER_VERSION=$(docker --version)
    log_success "Docker: $DOCKER_VERSION"
else
    log_error "Dockerがインストールされていません"
    exit 1
fi

if command -v docker compose &> /dev/null; then
    COMPOSE_VERSION=$(docker compose version)
    log_success "Docker Compose: $COMPOSE_VERSION"
else
    log_error "Docker Composeがインストールされていません"
    exit 1
fi

# 2. 必要なツールの確認
log_info "必要なツールをチェック中..."

if command -v jq &> /dev/null; then
    JQ_VERSION=$(jq --version)
    log_success "jq: $JQ_VERSION"
else
    log_warning "jqがインストールされていません（推奨）"
fi

if command -v git &> /dev/null; then
    GIT_VERSION=$(git --version)
    log_success "Git: $GIT_VERSION"
else
    log_error "Gitがインストールされていません"
    exit 1
fi

# 3. 環境変数ファイルの確認
log_info "環境変数ファイルをチェック中..."

if [ -f .env ]; then
    log_success ".envファイルが存在します"
    
    # 必要な環境変数の確認
    required_vars=("DISCORD_TOKEN" "GEMINI_API_KEY")
    for var in "${required_vars[@]}"; do
        if grep -q "^${var}=" .env && ! grep -q "^${var}=$" .env && ! grep -q "^${var}=your_" .env; then
            log_success "$var が設定されています"
        else
            log_warning "$var が設定されていないか、デフォルト値のままです"
        fi
    done
else
    log_warning ".envファイルが存在しません"
    log_info ".env.exampleを参考に作成してください"
fi

# 4. GitHub Actions設定ファイルの確認
log_info "GitHub Actions設定をチェック中..."

if [ -f .github/workflows/deploy.yml ]; then
    log_success "デプロイワークフローが設定されています"
else
    log_error "デプロイワークフローが見つかりません"
fi

if [ -f .github/workflows/rollback.yml ]; then
    log_success "ロールバックワークフローが設定されています"
else
    log_warning "ロールバックワークフローが見つかりません"
fi

# 5. スクリプトファイルの確認
log_info "デプロイスクリプトをチェック中..."

if [ -f scripts/deploy.sh ] && [ -x scripts/deploy.sh ]; then
    log_success "デプロイスクリプトが実行可能です"
else
    log_warning "デプロイスクリプトが見つからないか実行権限がありません"
fi

# 6. Docker Composeファイルの確認
log_info "Docker Compose設定をチェック中..."

if [ -f docker-compose.yml ]; then
    log_success "本番用docker-compose.ymlが存在します"
    
    # 設定の妥当性チェック
    if docker compose config &> /dev/null; then
        log_success "Docker Compose設定は有効です"
    else
        log_error "Docker Compose設定にエラーがあります"
        docker compose config
    fi
else
    log_error "docker-compose.ymlが見つかりません"
fi

if [ -f docker-compose.dev.yml ]; then
    log_success "開発用docker-compose.dev.ymlが存在します"
else
    log_warning "開発用docker-compose.dev.ymlが見つかりません"
fi

# 7. ログディレクトリの確認
log_info "ログディレクトリをチェック中..."

if [ -d logs ]; then
    log_success "logsディレクトリが存在します"
    
    # 書き込み権限の確認
    if [ -w logs ]; then
        log_success "logsディレクトリに書き込み権限があります"
    else
        log_warning "logsディレクトリに書き込み権限がありません"
    fi
else
    log_warning "logsディレクトリが存在しません（自動作成されます）"
    mkdir -p logs
    log_info "logsディレクトリを作成しました"
fi

# 8. データディレクトリの確認
log_info "データディレクトリをチェック中..."

if [ -d data ]; then
    log_success "dataディレクトリが存在します"
    
    # 書き込み権限の確認
    if [ -w data ]; then
        log_success "dataディレクトリに書き込み権限があります"
    else
        log_warning "dataディレクトリに書き込み権限がありません"
    fi
else
    log_warning "dataディレクトリが存在しません（自動作成されます）"
    mkdir -p data
    log_info "dataディレクトリを作成しました"
fi

# 9. 現在のコンテナ状況の確認
log_info "現在のコンテナ状況をチェック中..."

if docker compose ps &> /dev/null; then
    RUNNING_CONTAINERS=$(docker compose ps --format json 2>/dev/null | jq -r '.[].State' 2>/dev/null || echo "")
    
    if [ -n "$RUNNING_CONTAINERS" ]; then
        log_info "現在のコンテナ状況:"
        docker compose ps
    else
        log_info "現在実行中のコンテナはありません"
    fi
else
    log_info "Docker Composeプロジェクトは初期化されていません"
fi

# 10. Self-hosted Runnerの確認
log_info "Self-hosted Runnerをチェック中..."

if systemctl is-active --quiet actions.runner.* 2>/dev/null; then
    log_success "GitHub Actions Runnerサービスが実行中です"
    
    # Runnerの詳細情報
    for service in $(systemctl list-units --type=service --state=active | grep actions.runner | awk '{print $1}'); do
        log_info "アクティブなRunner: $service"
    done
else
    log_warning "GitHub Actions Runnerサービスが見つからないか停止しています"
    log_info "Self-hosted Runnerの設定については docs/deployment.md を参照してください"
fi

# 11. ネットワークポートの確認
log_info "ネットワークポートをチェック中..."

# PostgreSQLポート
if netstat -tlnp 2>/dev/null | grep -q :5432; then
    log_warning "ポート5432（PostgreSQL）が使用中です"
    netstat -tlnp 2>/dev/null | grep :5432
else
    log_success "ポート5432（PostgreSQL）は利用可能です"
fi

# Redisポート
if netstat -tlnp 2>/dev/null | grep -q :6379; then
    log_warning "ポート6379（Redis）が使用中です"
    netstat -tlnp 2>/dev/null | grep :6379
else
    log_success "ポート6379（Redis）は利用可能です"
fi

# 結果サマリー
echo ""
echo "=================================================="
echo "チェック完了"
echo "=================================================="

log_info "詳細なデプロイ手順については docs/deployment.md を参照してください"
log_info "問題がある場合は、上記の警告とエラーを確認して修正してください"

echo ""
echo "次のステップ:"
echo "1. 環境変数（.env）の設定"
echo "2. GitHub Self-hosted Runnerの設定"
echo "3. mainブランチへのpushでデプロイテスト"