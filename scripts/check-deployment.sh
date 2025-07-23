#!/bin/bash
# Discord Weather Bot デプロイメント状態確認スクリプト

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
COMPOSE_FILE="docker-compose.prod.yml"

# プロジェクトディレクトリに移動
cd "$PROJECT_DIR"

log_info "Discord Weather Bot デプロイメント状態確認"
log_info "プロジェクトディレクトリ: $PROJECT_DIR"

# サービス状態の確認
check_services() {
    log_info "サービス状態を確認しています..."
    
    # サービスの状態を表示
    docker compose -f "$COMPOSE_FILE" ps
    
    # 各サービスの状態を確認
    if ! docker compose -f "$COMPOSE_FILE" ps | grep -q "weather-bot.*Up"; then
        log_error "Weather Bot サービスが実行されていません"
        return 1
    fi
    
    if ! docker compose -f "$COMPOSE_FILE" ps | grep -q "db.*Up"; then
        log_warn "データベースサービスが実行されていません"
    fi
    
    log_info "サービス状態確認完了"
    return 0
}

# ヘルスチェック
health_check() {
    log_info "ヘルスチェックを実行しています..."
    
    # ボットのヘルスチェック
    if docker compose -f "$COMPOSE_FILE" exec -T weather-bot python -c "print('Bot is healthy')" &> /dev/null; then
        log_info "ボットヘルスチェック成功"
    else
        log_error "ボットヘルスチェック失敗"
        return 1
    fi
    
    # データベースのヘルスチェック
    if docker compose -f "$COMPOSE_FILE" ps | grep -q "db.*Up"; then
        if docker compose -f "$COMPOSE_FILE" exec -T db pg_isready &> /dev/null; then
            log_info "データベースヘルスチェック成功"
        else
            log_error "データベースヘルスチェック失敗"
            return 1
        fi
    fi
    
    log_info "ヘルスチェック完了"
    return 0
}

# リソース使用状況の確認
check_resources() {
    log_info "リソース使用状況を確認しています..."
    
    # コンテナのリソース使用状況
    docker stats --no-stream
    
    # ディスク使用量
    log_info "ディスク使用量:"
    df -h | grep -E "(Filesystem|/$|/opt)"
    
    # メモリ使用量
    log_info "メモリ使用量:"
    free -h
    
    log_info "リソース確認完了"
}

# ログの確認
check_logs() {
    log_info "最新のログを確認しています..."
    
    # エラーログの確認
    log_info "エラーログ:"
    docker compose -f "$COMPOSE_FILE" logs --tail=20 weather-bot | grep -i -E "error|exception|fail" || echo "エラーは見つかりませんでした"
    
    # 最新のログ
    log_info "最新のログ:"
    docker compose -f "$COMPOSE_FILE" logs --tail=10 weather-bot
    
    log_info "ログ確認完了"
}

# バックアップ状態の確認
check_backups() {
    log_info "バックアップ状態を確認しています..."
    
    # バックアップディレクトリの確認
    BACKUP_DIR="$PROJECT_DIR/backups"
    if [ ! -d "$BACKUP_DIR" ]; then
        log_warn "バックアップディレクトリが存在しません: $BACKUP_DIR"
        return 1
    fi
    
    # 最新のバックアップを確認
    local latest_db_backup=$(find "$BACKUP_DIR" -name "weather_bot_db_*.sql.gz" -type f -printf '%T@ %p\n' 2>/dev/null | sort -n | tail -1 | cut -d' ' -f2-)
    local latest_config_backup=$(find "$BACKUP_DIR" -name "weather_bot_config_*.tar.gz" -type f -printf '%T@ %p\n' 2>/dev/null | sort -n | tail -1 | cut -d' ' -f2-)
    
    if [ -n "$latest_db_backup" ]; then
        log_info "最新のDBバックアップ: $(basename "$latest_db_backup") ($(date -r "$latest_db_backup" "+%Y-%m-%d %H:%M:%S"))"
    else
        log_warn "データベースバックアップが見つかりません"
    fi
    
    if [ -n "$latest_config_backup" ]; then
        log_info "最新の設定バックアップ: $(basename "$latest_config_backup") ($(date -r "$latest_config_backup" "+%Y-%m-%d %H:%M:%S"))"
    else
        log_warn "設定バックアップが見つかりません"
    fi
    
    # バックアップの総数と合計サイズ
    local backup_count=$(find "$BACKUP_DIR" -type f | wc -l)
    local backup_size=$(du -sh "$BACKUP_DIR" 2>/dev/null | cut -f1)
    
    log_info "バックアップ総数: $backup_count"
    log_info "バックアップ合計サイズ: $backup_size"
    
    log_info "バックアップ確認完了"
}

# 環境変数の確認
check_env() {
    log_info "環境変数を確認しています..."
    
    # 環境変数ファイルの存在確認
    if [ ! -f ".env" ]; then
        log_error ".env ファイルが見つかりません"
        return 1
    fi
    
    # 必須環境変数の確認（値は表示しない）
    local required_vars=("DISCORD_TOKEN" "POSTGRES_DB" "POSTGRES_USER" "POSTGRES_PASSWORD")
    local missing_vars=0
    
    for var in "${required_vars[@]}"; do
        if ! grep -q "^$var=" .env; then
            log_error "必須環境変数が設定されていません: $var"
            missing_vars=$((missing_vars + 1))
        fi
    done
    
    if [ $missing_vars -eq 0 ]; then
        log_info "すべての必須環境変数が設定されています"
    else
        log_error "$missing_vars 個の必須環境変数が設定されていません"
        return 1
    fi
    
    log_info "環境変数確認完了"
}

# メイン処理
main() {
    local exit_code=0
    
    check_services || exit_code=$((exit_code + 1))
    health_check || exit_code=$((exit_code + 1))
    check_resources
    check_logs
    check_backups
    check_env || exit_code=$((exit_code + 1))
    
    if [ $exit_code -eq 0 ]; then
        log_info "すべてのチェックが正常に完了しました"
    else
        log_warn "$exit_code 個のチェックで問題が見つかりました"
    fi
    
    return $exit_code
}

# スクリプト実行
main "$@"