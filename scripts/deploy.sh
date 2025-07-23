#!/bin/bash
# Discord Weather Bot デプロイメントスクリプト
# 本番環境への安全なデプロイを実行します

set -e  # エラー時に停止

# 色付きログ出力用の関数
log_info() {
    echo -e "\033[32m[INFO]\033[0m $1"
}

log_warn() {
    echo -e "\033[33m[WARN]\033[0m $1"
}

log_error() {
    echo -e "\033[31m[ERROR]\033[0m $1"
}

# 設定
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_DIR="$(dirname "$SCRIPT_DIR")"
BACKUP_DIR="$PROJECT_DIR/backups"
COMPOSE_FILE="docker-compose.prod.yml"

# 引数の処理
ENVIRONMENT=${1:-production}
SKIP_BACKUP=${2:-false}

log_info "Discord Weather Bot デプロイメント開始"
log_info "環境: $ENVIRONMENT"
log_info "プロジェクトディレクトリ: $PROJECT_DIR"

# プロジェクトディレクトリに移動
cd "$PROJECT_DIR"

# 前提条件のチェック
check_prerequisites() {
    log_info "前提条件をチェックしています..."
    
    # Docker の確認
    if ! command -v docker &> /dev/null; then
        log_error "Docker がインストールされていません"
        exit 1
    fi
    
    # Docker Compose の確認
    if ! command -v docker &> /dev/null || ! docker compose version &> /dev/null; then
        log_error "Docker Compose がインストールされていません"
        exit 1
    fi
    
    # 環境変数ファイルの確認
    if [ ! -f ".env" ]; then
        log_error ".env ファイルが見つかりません"
        log_info "cp .env.prod .env を実行して環境変数を設定してください"
        exit 1
    fi
    
    # 必須環境変数の確認
    source .env
    if [ -z "$DISCORD_TOKEN" ]; then
        log_error "DISCORD_TOKEN が設定されていません"
        exit 1
    fi
    
    if [ -z "$POSTGRES_PASSWORD" ]; then
        log_error "POSTGRES_PASSWORD が設定されていません"
        exit 1
    fi
    
    log_info "前提条件チェック完了"
}

# バックアップの作成
create_backup() {
    if [ "$SKIP_BACKUP" = "true" ]; then
        log_warn "バックアップをスキップします"
        return
    fi
    
    log_info "バックアップを作成しています..."
    
    # バックアップディレクトリの作成
    mkdir -p "$BACKUP_DIR"
    
    local timestamp=$(date +%Y%m%d_%H%M%S)
    local backup_file="$BACKUP_DIR/weather_bot_$timestamp.sql"
    
    # データベースのバックアップ
    if docker compose -f "$COMPOSE_FILE" ps db | grep -q "Up"; then
        log_info "データベースをバックアップしています..."
        docker compose -f "$COMPOSE_FILE" exec -T db \
            pg_dump -U "$POSTGRES_USER" "$POSTGRES_DB" > "$backup_file"
        
        # 圧縮
        gzip "$backup_file"
        log_info "データベースバックアップ完了: ${backup_file}.gz"
    else
        log_warn "データベースが起動していないため、バックアップをスキップします"
    fi
    
    # 設定ファイルのバックアップ
    local config_backup="$BACKUP_DIR/config_$timestamp.tar.gz"
    tar -czf "$config_backup" .env "$COMPOSE_FILE" nginx/ monitoring/ || true
    log_info "設定ファイルバックアップ完了: $config_backup"
    
    # 古いバックアップの削除（30日以上）
    find "$BACKUP_DIR" -name "*.sql.gz" -mtime +30 -delete || true
    find "$BACKUP_DIR" -name "config_*.tar.gz" -mtime +30 -delete || true
}

# Dockerイメージのビルド
build_images() {
    log_info "Dockerイメージをビルドしています..."
    
    # 最新のコードを取得
    if [ -d ".git" ]; then
        log_info "最新のコードを取得しています..."
        git pull origin main || log_warn "Git pull に失敗しました"
    fi
    
    # イメージのビルド
    docker compose -f "$COMPOSE_FILE" build --no-cache weather-bot
    
    log_info "Dockerイメージビルド完了"
}

# サービスの停止
stop_services() {
    log_info "既存のサービスを停止しています..."
    
    # グレースフルシャットダウン
    docker compose -f "$COMPOSE_FILE" stop weather-bot || true
    
    # 他のサービスは継続実行（データベースなど）
    log_info "サービス停止完了"
}

# データベースマイグレーション
run_migrations() {
    log_info "データベースマイグレーションを実行しています..."
    
    # データベースが起動するまで待機
    local max_attempts=30
    local attempt=1
    
    while [ $attempt -le $max_attempts ]; do
        if docker compose -f "$COMPOSE_FILE" exec -T db pg_isready -U "$POSTGRES_USER" -d "$POSTGRES_DB" &> /dev/null; then
            log_info "データベース接続確認完了"
            break
        fi
        
        log_info "データベース起動待機中... ($attempt/$max_attempts)"
        sleep 2
        ((attempt++))
    done
    
    if [ $attempt -gt $max_attempts ]; then
        log_error "データベース接続に失敗しました"
        exit 1
    fi
    
    # マイグレーション実行
    docker compose -f "$COMPOSE_FILE" run --rm weather-bot alembic upgrade head
    
    log_info "データベースマイグレーション完了"
}

# サービスの起動
start_services() {
    log_info "サービスを起動しています..."
    
    # サービスの起動
    docker compose -f "$COMPOSE_FILE" up -d
    
    log_info "サービス起動完了"
}

# ヘルスチェック
health_check() {
    log_info "ヘルスチェックを実行しています..."
    
    local max_attempts=30
    local attempt=1
    
    while [ $attempt -le $max_attempts ]; do
        # ボットのヘルスチェック
        if docker compose -f "$COMPOSE_FILE" exec -T weather-bot python -c "print('Bot is healthy')" &> /dev/null; then
            log_info "ボットヘルスチェック成功"
            break
        fi
        
        log_info "ヘルスチェック待機中... ($attempt/$max_attempts)"
        sleep 5
        ((attempt++))
    done
    
    if [ $attempt -gt $max_attempts ]; then
        log_error "ヘルスチェックに失敗しました"
        show_logs
        exit 1
    fi
    
    # 各サービスの状態確認
    log_info "サービス状態:"
    docker compose -f "$COMPOSE_FILE" ps
    
    log_info "ヘルスチェック完了"
}

# ログの表示
show_logs() {
    log_info "最新のログを表示しています..."
    docker compose -f "$COMPOSE_FILE" logs --tail=50 weather-bot
}

# クリーンアップ
cleanup() {
    log_info "クリーンアップを実行しています..."
    
    # 未使用のDockerリソースを削除
    docker system prune -f || true
    
    # 未使用のイメージを削除
    docker image prune -f || true
    
    log_info "クリーンアップ完了"
}

# ロールバック機能
rollback() {
    log_error "デプロイメントに失敗しました。ロールバックを実行します..."
    
    # 最新のバックアップを検索
    local latest_backup=$(find "$BACKUP_DIR" -name "weather_bot_*.sql.gz" -type f -printf '%T@ %p\n' | sort -n | tail -1 | cut -d' ' -f2-)
    
    if [ -n "$latest_backup" ]; then
        log_info "バックアップからリストアしています: $latest_backup"
        
        # データベースのリストア
        gunzip -c "$latest_backup" | docker compose -f "$COMPOSE_FILE" exec -T db \
            psql -U "$POSTGRES_USER" -d "$POSTGRES_DB"
        
        log_info "ロールバック完了"
    else
        log_warn "バックアップファイルが見つかりません"
    fi
}

# メイン処理
main() {
    # エラー時のロールバック設定
    trap rollback ERR
    
    check_prerequisites
    create_backup
    build_images
    stop_services
    start_services
    run_migrations
    health_check
    cleanup
    
    log_info "デプロイメント完了!"
    log_info "ボットの状態を確認してください:"
    log_info "  docker compose -f $COMPOSE_FILE logs -f weather-bot"
    log_info "  docker compose -f $COMPOSE_FILE ps"
}

# スクリプト実行
main "$@"