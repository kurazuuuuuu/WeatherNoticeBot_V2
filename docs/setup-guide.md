# Discord Weather Bot セットアップガイド 🚀

このガイドでは、Discord Weather Botのセットアップ方法について詳しく説明します。

## 📋 目次

1. [事前準備](#事前準備)
2. [Discord Bot の作成](#discord-bot-の作成)
3. [API キーの取得](#api-キーの取得)
4. [環境構築](#環境構築)
5. [デプロイメント](#デプロイメント)
6. [初期設定](#初期設定)
7. [動作確認](#動作確認)

## 事前準備

### 必要なソフトウェア

#### Docker を使用する場合（推奨）
- [Docker](https://www.docker.com/get-started) 20.10+
- [Docker Compose](https://docs.docker.com/compose/install/) 2.0+

#### ローカル開発の場合
- [Python](https://www.python.org/downloads/) 3.12+
- [uv](https://docs.astral.sh/uv/) (Python パッケージマネージャー)

### システム要件

- **メモリ**: 最小 512MB、推奨 1GB
- **ストレージ**: 最小 1GB
- **OS**: Linux、macOS、Windows（WSL2推奨）

## Discord Bot の作成

### 1. Discord Developer Portal にアクセス

1. [Discord Developer Portal](https://discord.com/developers/applications/) にアクセス
2. Discordアカウントでログイン

### 2. 新しいアプリケーションを作成

1. 「New Application」をクリック
2. アプリケーション名を入力（例: "Weather Bot"）
3. 「Create」をクリック

### 3. Bot を作成

1. 左側メニューから「Bot」を選択
2. 「Add Bot」をクリック
3. 「Yes, do it!」で確認

### 4. Bot の設定

#### 基本設定
- **Username**: ボットの表示名を設定
- **Icon**: ボットのアイコンを設定（オプション）

#### 権限設定
「Privileged Gateway Intents」セクションで以下を有効化：
- ✅ **Message Content Intent** (メッセージ内容の読み取り)

#### Bot Token の取得
1. 「Token」セクションで「Reset Token」をクリック
2. 表示されたトークンをコピー（後で使用）
3. ⚠️ **重要**: このトークンは秘密情報です。他人と共有しないでください

### 5. OAuth2 設定

1. 左側メニューから「OAuth2」→「URL Generator」を選択
2. **Scopes** で以下を選択：
   - ✅ `bot`
   - ✅ `applications.commands`

3. **Bot Permissions** で以下を選択：
   - ✅ View Channels
   - ✅ Send Messages
   - ✅ Send Messages in Threads
   - ✅ Embed Links
   - ✅ Attach Files
   - ✅ Read Message History
   - ✅ Use Slash Commands

4. 生成されたURLをコピーしてブラウザで開く
5. ボットを追加したいサーバーを選択
6. 「認証」をクリック

## API キーの取得

### Google Gemini API キー（オプション）

AI機能を使用する場合に必要です。

1. [Google AI Studio](https://makersuite.google.com/app/apikey) にアクセス
2. Googleアカウントでログイン
3. 「Create API Key」をクリック
4. APIキーをコピー（後で使用）

**注意**: Gemini APIキーがない場合でも、ボットは基本的な天気情報機能で動作します。

## 環境構築

### Docker を使用する場合（推奨）

#### 1. プロジェクトのクローン

```bash
git clone <repository-url>
cd discord-weather-bot
```

#### 2. 環境変数の設定

```bash
# 環境変数ファイルをコピー
cp .env.example .env

# Docker環境用の設定ファイルをコピー（必要に応じて）
cp .env.docker .env

# 環境変数を編集
nano .env  # または vim .env
```

#### 3. 環境変数の設定内容

```bash
# 必須設定
DISCORD_TOKEN=your_discord_bot_token_here

# オプション設定
GEMINI_API_KEY=your_gemini_api_key_here
DATABASE_URL=sqlite:///data/weather_bot.db
LOG_LEVEL=INFO

# 開発時のみ（即座にコマンド反映）
DISCORD_GUILD_ID=your_test_server_id

# PostgreSQLを使用する場合（オプション）
USE_POSTGRES=true
POSTGRES_DB=weather_bot
POSTGRES_USER=weather_user
POSTGRES_PASSWORD=secure_password
```

#### 4. セットアップスクリプトの実行

```bash
# 自動セットアップ
./scripts/setup.sh

# または手動セットアップ
chmod +x scripts/*.sh
mkdir -p data logs
```

### ローカル開発の場合

#### 1. Python 環境の準備

```bash
# uv のインストール（まだの場合）
curl -LsSf https://astral.sh/uv/install.sh | sh

# プロジェクトのクローン
git clone <repository-url>
cd discord-weather-bot

# 依存関係のインストール
uv sync
```

#### 2. 環境変数の設定

```bash
cp .env.example .env
# .env ファイルを編集
```

#### 3. データベースの初期化

```bash
# マイグレーションの実行
uv run alembic upgrade head
```

## デプロイメント

### Docker Compose を使用したデプロイ

#### 本番環境

```bash
# 本番環境での起動
./scripts/start.sh prod

# または手動起動
docker compose -f docker-compose.prod.yml up -d

# 注意: 新しいDocker Composeでは「docker compose」（スペース区切り）を使用します
# 古いバージョンでは「docker-compose」（ハイフン区切り）を使用します
```

#### 開発環境

```bash
# 開発環境での起動（ホットリロード対応）
./scripts/start.sh dev

# または手動起動
docker compose -f docker-compose.dev.yml up -d
```

#### 管理コマンド

```bash
# サービス状態確認
./scripts/start.sh status

# ログ確認
./scripts/start.sh logs

# 停止
./scripts/start.sh stop

# 再起動
./scripts/start.sh restart
```

### ローカル実行

```bash
# ボットの起動
uv run python src/bot.py

# または開発用スクリプト
uv run python debug/run.py
```

## 初期設定

### 1. ボットの動作確認

ボットが正常に起動したら、以下を確認：

```bash
# ログの確認
docker-compose logs weather-bot

# または
tail -f logs/weather_bot.log
```

正常な起動ログの例：
```
INFO - ボットが正常に起動しました
INFO - コマンドを同期しています...
INFO - コマンド同期が完了しました
INFO - ボットがオンラインになりました
```

### 2. Discord サーバーでの確認

1. ボットを追加したDiscordサーバーにアクセス
2. ボットがオンライン状態であることを確認
3. スラッシュコマンドが利用可能であることを確認

### 3. 基本的なテスト

```
/weather 東京都
```

このコマンドで天気情報が表示されれば、セットアップ完了です。

## 動作確認

### 基本機能のテスト

#### 1. 天気情報の取得

```
/weather 東京都
/forecast 大阪府
/weather-alerts 沖縄県
```

#### 2. ユーザー設定

```
/set-location 東京都
/my-settings
/schedule-weather 7
```

#### 3. 管理者機能（管理者権限が必要）

```
/weather-config
/stats
```

### トラブルシューティング

#### コマンドが表示されない場合

1. **権限の確認**
   ```bash
   # ボットの権限を確認
   docker-compose logs weather-bot | grep "権限"
   ```

2. **コマンド同期の確認**
   ```bash
   # コマンド同期ログを確認
   docker-compose logs weather-bot | grep "コマンド"
   ```

3. **ギルドIDの設定（開発時）**
   ```bash
   # .env ファイルに追加
   echo "DISCORD_GUILD_ID=your_guild_id" >> .env
   docker-compose restart weather-bot
   ```

#### ボットが応答しない場合

1. **ボットの状態確認**
   ```bash
   docker-compose ps
   ```

2. **ログの確認**
   ```bash
   docker-compose logs weather-bot
   ```

3. **環境変数の確認**
   ```bash
   docker-compose exec weather-bot env | grep DISCORD
   ```

#### データベースエラーの場合

1. **データベースの確認**
   ```bash
   # SQLite の場合
   ls -la data/
   
   # PostgreSQL の場合
   docker-compose ps db
   ```

2. **マイグレーションの実行**
   ```bash
   docker-compose exec weather-bot alembic upgrade head
   ```

## セキュリティ設定

### 1. 環境変数の保護

- `.env` ファイルを `.gitignore` に追加
- 本番環境では環境変数を直接設定
- APIキーの定期的な更新

### 2. Discord Bot の権限

- 必要最小限の権限のみを付与
- 管理者権限は避ける
- サーバー固有の権限設定

### 3. ログ管理

- 機密情報をログに出力しない
- ログファイルのアクセス制限
- 定期的なログローテーション

## パフォーマンス最適化

### 1. リソース制限

```yaml
# docker-compose.yml での設定例
services:
  weather-bot:
    deploy:
      resources:
        limits:
          memory: 512M
          cpus: '0.5'
```

### 2. データベース最適化

- 定期的なデータベースクリーンアップ
- インデックスの最適化
- 古いログの削除

### 3. 監視設定

```bash
# ヘルスチェック
docker-compose exec weather-bot python -c "print('Bot is healthy')"

# リソース使用量確認
docker stats weather-bot
```

## バックアップ

### データベースのバックアップ

```bash
# SQLite の場合
cp data/weather_bot.db data/weather_bot_backup_$(date +%Y%m%d).db

# PostgreSQL の場合
docker-compose exec db pg_dump -U weather_user weather_bot > backup_$(date +%Y%m%d).sql
```

### 設定ファイルのバックアップ

```bash
# 重要な設定ファイルをバックアップ
tar -czf config_backup_$(date +%Y%m%d).tar.gz .env docker-compose.yml
```

## 更新とメンテナンス

### ボットの更新

```bash
# 最新版の取得
git pull origin main

# 依存関係の更新
docker-compose pull

# 再起動
docker-compose down
docker-compose up -d
```

### 定期メンテナンス

- ログファイルのローテーション
- データベースの最適化
- 不要なDockerイメージの削除

```bash
# Docker クリーンアップ
docker system prune -f
```

---

これでDiscord Weather Botのセットアップが完了です！問題が発生した場合は、トラブルシューティングガイドを参照してください。