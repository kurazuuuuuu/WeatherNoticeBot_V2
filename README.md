# Discord Weather Bot 🌤️

日本気象庁APIを使用したDiscord天気情報ボット

## 🚀 機能

- **天気情報取得**: `/weather` - 現在の天気情報を表示
- **天気予報**: `/forecast` - 5日間の天気予報を表示  
- **気象警報**: `/weather-alerts` - 気象警報・注意報を表示
- **地域設定**: `/set-location` - ユーザー個別の地域設定
- **定時通知**: `/schedule-weather` - 指定時間に天気情報をDM通知
- **設定管理**: `/my-settings` - 現在の設定を表示
- **AI機能**: Google Gemini AIによるポジティブなメッセージ生成

## 🐳 Docker Composeでの起動

### 1. 環境変数の設定

```bash
# 環境変数ファイルをコピー
cp .env.docker .env

# .envファイルを編集して必要な値を設定
# - DISCORD_TOKEN: DiscordボットのトークンID
# - GEMINI_API_KEY: Google Gemini APIキー（オプション）
```

### 2. 本番環境での起動

```bash
# 全サービス起動（PostgreSQL + Redis + Bot）
docker-compose up -d

# ボットのみ起動（SQLite使用）
docker-compose up -d weather-bot

# ログ確認
docker-compose logs -f weather-bot
```

### 3. 開発環境での起動

```bash
# 開発モードで起動（ホットリロード対応）
docker-compose -f docker-compose.dev.yml up

# バックグラウンドで起動
docker-compose -f docker-compose.dev.yml up -d
```

## 🛠️ ローカル開発

### 必要な環境

- Python 3.12+
- uv (Python package manager)

### セットアップ

```bash
# 依存関係のインストール
uv sync

# 環境変数の設定
cp .env.example .env
# .envファイルを編集

# データベースマイグレーション
uv run alembic upgrade head

# ボット起動
uv run python src/bot.py
```

## 📋 必要な設定

### Discord Bot設定

1. [Discord Developer Portal](https://discord.com/developers/applications/)でボットを作成
2. 以下の権限を設定：
   - `applications.commands` (スラッシュコマンド)
   - `bot` (ボット基本権限)
   - View Channels, Send Messages, Embed Links, Use Slash Commands

### 環境変数

| 変数名 | 必須 | 説明 |
|--------|------|------|
| `DISCORD_TOKEN` | ✅ | DiscordボットのトークンID |
| `GEMINI_API_KEY` | ❌ | Google Gemini APIキー（AI機能用） |
| `DATABASE_URL` | ❌ | データベース接続URL（デフォルト: SQLite） |
| `LOG_LEVEL` | ❌ | ログレベル（デフォルト: INFO） |

## 🏗️ アーキテクチャ

```
src/
├── bot.py              # メインボットファイル
├── config.py           # 設定管理
├── database.py         # データベース接続
├── commands/           # Discordコマンド
│   ├── weather_commands.py
│   ├── user_commands.py
│   └── admin_commands.py
├── services/           # ビジネスロジック
│   ├── weather_service.py
│   ├── user_service.py
│   └── ai_service.py
├── models/             # データモデル
│   └── user.py
└── utils/              # ユーティリティ
    ├── logging.py
    └── migration.py
```

## 🔧 Docker Compose構成

### サービス構成

- **weather-bot**: メインのDiscordボット
- **db**: PostgreSQL データベース（オプション）
- **redis**: Redis キャッシュ（将来の機能拡張用）

### ボリューム

- `./data`: データベースファイル（SQLite使用時）
- `./logs`: ログファイル
- `postgres_data`: PostgreSQLデータ
- `redis_data`: Redisデータ

### ネットワーク

- `weather-bot-network`: 内部通信用ネットワーク

## 📊 監視・ヘルスチェック

```bash
# サービス状態確認
docker-compose ps

# ヘルスチェック状態確認
docker-compose exec weather-bot python -c "print('Bot is healthy')"

# ログ監視
docker-compose logs -f weather-bot
```

## 🚨 トラブルシューティング

### よくある問題

1. **ボットが起動しない**
   ```bash
   # ログを確認
   docker-compose logs weather-bot
   
   # 環境変数を確認
   docker-compose exec weather-bot env | grep DISCORD
   ```

2. **データベース接続エラー**
   ```bash
   # データベースサービス確認
   docker-compose ps db
   
   # データベース接続テスト
   docker-compose exec db psql -U weather_user -d weather_bot -c "SELECT 1;"
   ```

3. **権限エラー**
   ```bash
   # ファイル権限確認
   ls -la data/ logs/
   
   # 権限修正
   sudo chown -R 1000:1000 data/ logs/
   ```

## 📝 ライセンス

このプロジェクトはMITライセンスの下で公開されています。

## 🤝 コントリビューション

1. このリポジトリをフォーク
2. 機能ブランチを作成 (`git checkout -b feature/amazing-feature`)
3. 変更をコミット (`git commit -m 'Add amazing feature'`)
4. ブランチにプッシュ (`git push origin feature/amazing-feature`)
5. プルリクエストを作成

## 📞 サポート

問題や質問がある場合は、GitHubのIssuesページでお知らせください。