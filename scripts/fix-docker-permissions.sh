#!/bin/bash

# Docker権限修正スクリプト
# GitHub Actions self-hosted runnerでDocker実行権限を設定

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

echo "=================================================="
echo "Docker権限修正スクリプト"
echo "=================================================="

# 現在のユーザー情報を表示
log_info "現在のユーザー: $(whoami)"
log_info "ユーザーID: $(id -u)"
log_info "グループID: $(id -g)"
log_info "所属グループ: $(groups)"

# Dockerの状態確認
log_info "Dockerサービスの状態を確認中..."
if systemctl is-active --quiet docker; then
    log_success "Dockerサービスが実行中です"
else
    log_error "Dockerサービスが停止しています"
    log_info "Dockerサービスを開始します..."
    sudo systemctl start docker
    sudo systemctl enable docker
fi

# dockerグループの存在確認
log_info "dockerグループの確認中..."
if getent group docker > /dev/null 2>&1; then
    log_success "dockerグループが存在します"
    log_info "dockerグループのメンバー:"
    getent group docker
else
    log_warning "dockerグループが存在しません。作成します..."
    sudo groupadd docker
fi

# 現在のユーザーをdockerグループに追加
CURRENT_USER=$(whoami)
log_info "ユーザー $CURRENT_USER をdockerグループに追加中..."

if groups $CURRENT_USER | grep -q docker; then
    log_success "ユーザー $CURRENT_USER は既にdockerグループのメンバーです"
else
    log_info "ユーザー $CURRENT_USER をdockerグループに追加します..."
    sudo usermod -aG docker $CURRENT_USER
    log_success "ユーザー $CURRENT_USER をdockerグループに追加しました"
fi

# Docker socketの権限確認
log_info "Docker socketの権限を確認中..."
ls -la /var/run/docker.sock

# Docker socketの権限修正（必要に応じて）
if [ ! -w /var/run/docker.sock ]; then
    log_warning "Docker socketに書き込み権限がありません"
    log_info "権限を修正します..."
    sudo chmod 666 /var/run/docker.sock
    log_success "Docker socketの権限を修正しました"
else
    log_success "Docker socketに適切な権限があります"
fi

# GitHub Actions Runnerサービスの確認と再起動
log_info "GitHub Actions Runnerサービスを確認中..."

# アクティブなRunnerサービスを検索
RUNNER_SERVICES=$(systemctl list-units --type=service --state=active | grep actions.runner | awk '{print $1}' || true)

if [ -n "$RUNNER_SERVICES" ]; then
    log_info "見つかったRunnerサービス:"
    echo "$RUNNER_SERVICES"
    
    log_info "Runnerサービスを再起動してグループ変更を反映します..."
    for service in $RUNNER_SERVICES; do
        log_info "サービス $service を再起動中..."
        sudo systemctl restart "$service"
        sleep 2
        
        if systemctl is-active --quiet "$service"; then
            log_success "サービス $service が正常に再起動されました"
        else
            log_error "サービス $service の再起動に失敗しました"
        fi
    done
else
    log_warning "アクティブなGitHub Actions Runnerサービスが見つかりません"
    log_info "手動でRunnerを再起動する必要があります"
fi

# Docker接続テスト
log_info "Docker接続をテスト中..."
if docker info > /dev/null 2>&1; then
    log_success "Dockerに正常に接続できます"
    
    # Docker Composeのテスト
    log_info "Docker Composeをテスト中..."
    if docker compose version > /dev/null 2>&1; then
        log_success "Docker Composeが正常に動作します"
    else
        log_error "Docker Composeでエラーが発生しました"
    fi
else
    log_error "Dockerに接続できません"
    log_info "以下の手順を試してください："
    echo "1. ターミナルを再起動してください"
    echo "2. または以下のコマンドを実行してください："
    echo "   newgrp docker"
    echo "3. GitHub Actions Runnerを手動で再起動してください"
fi

echo ""
echo "=================================================="
echo "修正完了"
echo "=================================================="

log_info "重要な注意事項："
echo "1. グループ変更を反映するため、GitHub Actions Runnerの再起動が必要です"
echo "2. 問題が続く場合は、サーバー全体を再起動してください"
echo "3. セキュリティ上の理由で、本番環境では適切な権限管理を行ってください"

echo ""
echo "次のステップ："
echo "1. GitHub Actions Runnerが自動で再起動されない場合は手動で再起動"
echo "2. デプロイワークフローを再実行してテスト"
echo "3. 問題が続く場合はサーバーを再起動"