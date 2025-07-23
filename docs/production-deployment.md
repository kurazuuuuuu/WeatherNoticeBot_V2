# Discord Weather Bot 本番環境デプロイメントガイド 🚀

このガイドでは、Discord Weather Botを本番環境にデプロイするための詳細な手順を説明します。

## 📋 目次

1. [デプロイメント準備](#デプロイメント準備)
2. [サーバー環境の設定](#サーバー環境の設定)
3. [Docker環境のセットアップ](#docker環境のセットアップ)
4. [本番環境の設定](#本番環境の設定)
5. [デプロイメント手順](#デプロイメント手順)
6. [監視とメンテナンス](#監視とメンテナンス)
7. [バックアップと復元](#バックアップと復元)
8. [トラブルシューティング](#トラブルシューティング)

## デプロイメント準備

### 必要なもの

1. **サーバー環境**
   - Linux サーバー（Ubuntu 20.04 LTS以上推奨）
   - 最小要件: 1GB RAM, 10GB ストレージ
   - 推奨: 2GB RAM, 20GB SSD ストレージ

2. **必要なアカウント**
   - Discord Developer アカウントとBot Token
   - Google Gemini API キー（オプション）

3. **ドメイン名**（オプション）
   - 監視ダッシュボードやAPIエンドポイント用

### 事前準備チェックリスト

- [ ] Discord Bot Tokenの取得
- [ ] Google Gemini API Keyの取得（オプション）
- [ ] サーバーへのSSHアクセス
- [ ] ドメイン名のDNS設定（オプション）

## サーバー環境の設定

### 基本的なサーバーセットアップ

```bash
# システムの更新
sudo apt update && sudo apt upgrade -y

# 基本的なツールのインストール
sudo apt install -y curl git ufw htop

# ファイアウォールの設定
sudo ufw allow ssh
sudo ufw allow http
sudo ufw allow https
sudo ufw enable
```

### ユーザー設定

```bash
# 専用ユーザーの作成
sudo adduser weatherbot

# sudoグループに追加
sudo usermod -aG sudo weatherbot

# ユーザーに切り替え
su - weatherbot
```

## Docker環境のセットアップ

### Docker と Docker Compose のインストール

```bash
# Dockerのインストール
curl -fsSL https://get.docker.com -o get-docker.sh
sudo sh get-docker.sh

# 現在のユーザーをdockerグループに追加
sudo usermod -aG docker $USER

# 変更を適用するためにシェルを再起動
newgrp docker

# Docker Composeのインストール
sudo apt install -y docker-compose-plugin

# バージョン確認
docker --version
docker compose version
```

### プロジェクトのセットアップ

```bash
# アプリケーションディレクトリの作成
sudo mkdir -p /opt/discord-weather-bot
sudo chown $USER:$USER /opt/discord-weather-bot

# リポジトリのクローン
git clone https://github.com/yourusername/discord-weather-bot.git /opt/discord-weather-bot
cd /opt/discord-weather-bot

# 必要なディレクトリの作成
mkdir -p data logs
chmod 755 data logs
chmod +x scripts/*.sh
```

## 本番環境の設定

### 環境変数の設定

```bash
# 本番環境用の設定ファイルをコピー
cp .env.example .env.prod

# 設定ファイルの編集
nano .env.prod
```

### 本番環境用の.env.prodファイル例

```bash
# Discord Bot Configuration
DISCORD_TOKEN=your_discord_bot_token_here
DISCORD_GUILD_ID=  # 本番環境では空にする

# Database Configuration
USE_POSTGRES=true
POSTGRES_DB=weather_bot
POSTGRES_USER=weather_user
POSTGRES_PASSWORD=your_secure_password_here
DATABASE_URL=postgresql://${POSTGRES_USER}:${POSTGRES_PASSWORD}@db:5432/${POSTGRES_DB}

# Google Gemini API Configuration
GEMINI_API_KEY=your_gemini_api_key_here

# Redis Configuration
REDIS_PASSWORD=your_secure_redis_password_here

# Security Configuration
SECRET_KEY=your_very_secure_secret_key_here

# Logging Configuration
LOG_LEVEL=INFO
LOG_FILE=/app/logs/weather_bot.log

# Monitoring Configuration
GRAFANA_PASSWORD=your_secure_grafana_password_here

# Environment
ENVIRONMENT=production
```

### セキュリティキーの生成

```bash
# ランダムなシークレットキーの生成
SECRET_KEY=$(openssl rand -base64 32)
echo "SECRET_KEY=$SECRET_KEY" >> .env.prod

# 安全なパスワードの生成
DB_PASSWORD=$(openssl rand -base64 16)
echo "POSTGRES_PASSWORD=$DB_PASSWORD" >> .env.prod

REDIS_PASSWORD=$(openssl rand -base64 16)
echo "REDIS_PASSWORD=$REDIS_PASSWORD" >> .env.prod

GRAFANA_PASSWORD=$(openssl rand -base64 16)
echo "GRAFANA_PASSWORD=$GRAFANA_PASSWORD" >> .env.prod
```

### 本番環境用の設定ファイルの適用

```bash
# 本番環境用の設定を.envにコピー
cp .env.prod .env

# 設定ファイルの権限を制限
chmod 600 .env .env.prod
```

## デプロイメント手順

### 本番環境のデプロイ

```bash
# 本番環境用のDockerコンテナを起動
docker compose -f docker-compose.prod.yml up -d

# サービスの状態を確認
docker compose -f docker-compose.prod.yml ps

# ログの確認
docker compose -f docker-compose.prod.yml logs -f weather-bot
```

### デプロイメントスクリプトの使用

```bash
# デプロイメントスクリプトの実行
./scripts/deploy.sh

# または
./scripts/start.sh prod
```

### データベースマイグレーション

```bash
# マイグレーションの実行
docker compose -f docker-compose.prod.yml exec weather-bot alembic upgrade head

# マイグレーション状態の確認
docker compose -f docker-compose.prod.yml exec weather-bot alembic current
```

## 監視とメンテナンス

### ログの確認

```bash
# リアルタイムでログを監視
docker compose -f docker-compose.prod.yml logs -f weather-bot

# 最新の100行を表示
docker compose -f docker-compose.prod.yml logs --tail=100 weather-bot

# エラーログのみを表示
docker compose -f docker-compose.prod.yml logs weather-bot | grep -i error
```

### システムリソースの監視

```bash
# コンテナのリソース使用状況
docker stats

# ディスク使用量
df -h

# メモリ使用量
free -h
```

### Prometheus & Grafanaの設定

1. **Prometheusへのアクセス**
   - http://your-server-ip:9090

2. **Grafanaへのアクセス**
   - http://your-server-ip:3000
   - ユーザー名: admin
   - パスワード: .env.prodで設定したGRAFANA_PASSWORD

3. **Grafanaダッシュボードのインポート**
   - Grafanaにログイン後、「+」→「Import」をクリック
   - JSONファイルをアップロードまたはIDを入力

### 定期的なメンテナンス

```bash
# ログローテーション
find logs -name "*.log" -size +100M -exec gzip {} \;

# 古いログの削除
find logs -name "*.log.gz" -mtime +30 -delete

# Dockerシステムのクリーンアップ
docker system prune -f
```

## バックアップと復元

### データベースのバックアップ

```bash
# バックアップディレクトリの作成
mkdir -p /opt/discord-weather-bot/backups

# PostgreSQLデータベースのバックアップ
docker compose -f docker-compose.prod.yml exec db pg_dump -U weather_user weather_bot > /opt/discord-weather-bot/backups/weather_bot_$(date +%Y%m%d).sql

# バックアップの圧縮
gzip /opt/discord-weather-bot/backups/weather_bot_$(date +%Y%m%d).sql
```

### 設定ファイルのバックアップ

```bash
# 設定ファイルのバックアップ
tar -czf /opt/discord-weather-bot/backups/config_$(date +%Y%m%d).tar.gz -C /opt/discord-weather-bot .env .env.prod docker-compose.prod.yml
```

### 自動バックアップの設定

```bash
# cronジョブの編集
crontab -e

# 毎日午前3時にデータベースをバックアップ
0 3 * * * /opt/discord-weather-bot/scripts/backup.sh

# 毎週日曜日に設定ファイルをバックアップ
0 4 * * 0 tar -czf /opt/discord-weather-bot/backups/config_$(date +\%Y\%m\%d).tar.gz -C /opt/discord-weather-bot .env .env.prod docker-compose.prod.yml
```

### データベースの復元

```bash
# バックアップからの復元
gunzip -c /opt/discord-weather-bot/backups/weather_bot_20240723.sql.gz | docker compose -f docker-compose.prod.yml exec -T db psql -U weather_user weather_bot
```

## トラブルシューティング

### 一般的な問題と解決策

#### ボットがオンラインにならない

```bash
# ログの確認
docker compose -f docker-compose.prod.yml logs weather-bot

# Discord Tokenの確認
docker compose -f docker-compose.prod.yml exec weather-bot env | grep DISCORD_TOKEN

# ボットの再起動
docker compose -f docker-compose.prod.yml restart weather-bot
```

#### データベース接続エラー

```bash
# データベースの状態確認
docker compose -f docker-compose.prod.yml ps db

# データベースログの確認
docker compose -f docker-compose.prod.yml logs db

# データベース接続テスト
docker compose -f docker-compose.prod.yml exec db psql -U weather_user -d weather_bot -c "SELECT 1;"
```

#### メモリ不足エラー

```bash
# メモリ使用量の確認
docker stats

# スワップの追加
sudo fallocate -l 2G /swapfile
sudo chmod 600 /swapfile
sudo mkswap /swapfile
sudo swapon /swapfile
echo '/swapfile none swap sw 0 0' | sudo tee -a /etc/fstab
```

### 緊急時の対応

#### サービスの完全再起動

```bash
# すべてのサービスを停止
docker compose -f docker-compose.prod.yml down

# サービスを再起動
docker compose -f docker-compose.prod.yml up -d

# ログの確認
docker compose -f docker-compose.prod.yml logs -f
```

#### 以前のバージョンへのロールバック

```bash
# 現在のコミットハッシュを確認
git log --oneline -5

# 特定のコミットに戻る
git checkout <commit-hash>

# サービスを再ビルドして起動
docker compose -f docker-compose.prod.yml down
docker compose -f docker-compose.prod.yml build
docker compose -f docker-compose.prod.yml up -d
```

---

このガイドに従って、Discord Weather Botを本番環境に安全かつ効率的にデプロイしてください。問題が発生した場合は、トラブルシューティングセクションを参照するか、開発チームにお問い合わせください。