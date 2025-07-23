#!/bin/bash
# Discord Weather Bot バックアップスクリプト

# 設定
BACKUP_DIR="/opt/discord-weather-bot/backups"
DATE=$(date +%Y%m%d_%H%M%S)
DB_BACKUP_FILE="$BACKUP_DIR/weather_bot_db_$DATE.sql"
CONFIG_BACKUP_FILE="$BACKUP_DIR/weather_bot_config_$DATE.tar.gz"
LOG_FILE="$BACKUP_DIR/backup_log_$DATE.log"

# バックアップディレクトリの作成
mkdir -p $BACKUP_DIR

# ログ開始
echo "===== バックアップ開始: $(date) =====" > $LOG_FILE

# 現在のディレクトリを確認
cd $(dirname $(readlink -f $0))/..
echo "作業ディレクトリ: $(pwd)" >> $LOG_FILE

# データベースのバックアップ
echo "データベースのバックアップを作成中..." >> $LOG_FILE

# PostgreSQLが使用されているか確認
if grep -q "USE_POSTGRES=true" .env; then
    echo "PostgreSQLバックアップを実行中..." >> $LOG_FILE
    docker compose -f docker-compose.prod.yml exec -T db pg_dump -U weather_user weather_bot > $DB_BACKUP_FILE 2>> $LOG_FILE
    if [ $? -eq 0 ]; then
        echo "PostgreSQLバックアップ成功: $DB_BACKUP_FILE" >> $LOG_FILE
    else
        echo "PostgreSQLバックアップ失敗" >> $LOG_FILE
    fi
else
    echo "SQLiteバックアップを実行中..." >> $LOG_FILE
    cp data/weather_bot.db $BACKUP_DIR/weather_bot_db_$DATE.db 2>> $LOG_FILE
    if [ $? -eq 0 ]; then
        echo "SQLiteバックアップ成功: $BACKUP_DIR/weather_bot_db_$DATE.db" >> $LOG_FILE
    else
        echo "SQLiteバックアップ失敗" >> $LOG_FILE
    fi
fi

# 設定ファイルのバックアップ
echo "設定ファイルのバックアップを作成中..." >> $LOG_FILE
tar -czf $CONFIG_BACKUP_FILE .env .env.prod docker-compose.prod.yml 2>> $LOG_FILE
if [ $? -eq 0 ]; then
    echo "設定ファイルのバックアップ成功: $CONFIG_BACKUP_FILE" >> $LOG_FILE
else
    echo "設定ファイルのバックアップ失敗" >> $LOG_FILE
fi

# バックアップの圧縮
if [ -f $DB_BACKUP_FILE ]; then
    echo "データベースバックアップを圧縮中..." >> $LOG_FILE
    gzip $DB_BACKUP_FILE
    echo "圧縮完了: ${DB_BACKUP_FILE}.gz" >> $LOG_FILE
fi

# 古いバックアップの削除（30日以上）
echo "古いバックアップを削除中..." >> $LOG_FILE
find $BACKUP_DIR -name "weather_bot_db_*.sql.gz" -mtime +30 -delete
find $BACKUP_DIR -name "weather_bot_db_*.db" -mtime +30 -delete
find $BACKUP_DIR -name "weather_bot_config_*.tar.gz" -mtime +30 -delete
echo "古いバックアップの削除完了" >> $LOG_FILE

# バックアップ情報の表示
echo "===== バックアップ完了: $(date) =====" >> $LOG_FILE
echo "バックアップディレクトリ: $BACKUP_DIR" >> $LOG_FILE
echo "データベースバックアップ: ${DB_BACKUP_FILE}.gz" >> $LOG_FILE
echo "設定バックアップ: $CONFIG_BACKUP_FILE" >> $LOG_FILE

# 結果の表示
echo "===== バックアップ完了 ====="
echo "詳細はログファイルを確認してください: $LOG_FILE"