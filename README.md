# Discord Weather Bot 🌤️

日本気象庁APIを使用したDiscord天気情報ボット

## 🚀 機能

### 天気情報コマンド
- **`/weather`** - 現在の天気情報を表示
- **`/forecast`** - 5日間の天気予報を表示  
- **`/weather-alerts`** - 気象警報・注意報を表示

### ユーザー設定コマンド
- **`/set-location`** - ユーザー個別の地域設定
- **`/schedule-weather`** - 指定時間に天気情報をDM通知
- **`/unschedule-weather`** - 定時通知を停止
- **`/my-settings`** - 現在の設定を表示

### 管理者コマンド
- **`/weather-config`** - サーバー設定管理（管理者専用）
- **`/stats`** - ボット統計情報表示（管理者専用）

### AI機能
- **Google Gemini AI**によるポジティブなメッセージ生成
- 天気に応じた励ましメッセージ
- フォールバック機能で安定動作

## 🚀 クイックスタート

### 1. 初回セットアップ

```bash
# セットアップスクリプトを実行
./scripts/setup.sh

# 環境変数を設定
cp .env.docker .env
# .envファイルを編集してDISCORD_TOKENとGEMINI_API_KEYを設定
```

### 2. Docker Composeでの起動

#### 本番環境
```bash
# 簡単起動（推奨）
./scripts/start.sh prod

# または手動起動
docker-compose up -d weather-bot
```

#### 開発環境
```bash
# 開発モード（ホットリロード対応）
./scripts/start.sh dev

# または手動起動
docker-compose -f docker-compose.dev.yml up
```

#### 管理コマンド
```bash
./scripts/start.sh stop      # 停止
./scripts/start.sh restart   # 再起動
./scripts/start.sh logs      # ログ表示
./scripts/start.sh status    # 状態確認
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
| `DISCORD_GUILD_ID` | ❌ | テスト用サーバーID（開発時推奨） |
| `LOG_LEVEL` | ❌ | ログレベル（デフォルト: INFO） |

## 🏗️ プロジェクト構造

```
WeatherNoticeBot_V2/
├── src/                    # メインソースコード
│   ├── bot.py              # メインボットファイル
│   ├── config.py           # 設定管理
│   ├── database.py         # データベース接続
│   ├── commands/           # Discordコマンド
│   │   ├── weather_commands.py
│   │   ├── user_commands.py
│   │   └── admin_commands.py
│   ├── services/           # ビジネスロジック
│   │   ├── weather_service.py
│   │   ├── user_service.py
│   │   └── ai_service.py
│   ├── models/             # データモデル
│   │   └── user.py
│   └── utils/              # ユーティリティ
│       ├── logging.py
│       └── migration.py
├── tests/                  # テストファイル
│   ├── test_weather_service.py
│   ├── test_ai_service.py
│   ├── test_user_service.py
│   └── ...
├── debug/                  # デバッグ・開発用
│   ├── debug_api.py        # 気象庁API構造確認
│   ├── debug_forecast.py   # 天気予報API構造確認
│   └── run.py              # ボット起動用
├── scripts/                # 運用スクリプト
│   ├── setup.sh            # 初回セットアップ
│   └── start.sh            # 起動・管理スクリプト
├── alembic/                # データベースマイグレーション
├── data/                   # データファイル（SQLite等）
├── logs/                   # ログファイル
├── docker-compose.yml      # 本番環境用Docker設定
├── docker-compose.dev.yml  # 開発環境用Docker設定
└── Dockerfile              # Dockerイメージ定義
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

## 🧪 テスト・デバッグ

### テスト実行
```bash
# 全テスト実行
uv run python -m pytest tests/

# 特定のテスト実行
uv run python -m pytest tests/test_weather_service.py

# Docker環境でのテスト実行
docker-compose exec weather-bot python -m pytest tests/
```

### デバッグスクリプト
```bash
# 気象庁API構造確認
uv run python debug/debug_api.py

# 天気予報API構造確認
uv run python debug/debug_forecast.py

# ボット起動（デバッグ用）
uv run python debug/run.py
```

## ⏱️ コマンド登録について

### スラッシュコマンドの反映時間
- **グローバルコマンド**: 最大1時間（通常15-30分）
- **ギルド限定コマンド**: 即座（数秒以内）

### 開発時の設定
開発・テスト時は`.env`ファイルで`DISCORD_GUILD_ID`を設定することで、即座にコマンドが反映されます：

```bash
# .envファイル
DISCORD_GUILD_ID=your_test_server_id
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

2. **コマンドが表示されない**
   ```bash
   # コマンド同期状況を確認
   docker-compose logs weather-bot | grep "コマンド"
   
   # ギルドIDを設定して即座反映（開発時）
   echo "DISCORD_GUILD_ID=your_guild_id" >> .env
   ```

3. **データベース接続エラー**
   ```bash
   # データベースサービス確認
   docker-compose ps db
   
   # データベース接続テスト
   docker-compose exec db psql -U weather_user -d weather_bot -c "SELECT 1;"
   ```

4. **権限エラー**
   ```bash
   # ファイル権限確認
   ls -la data/ logs/
   
   # 権限修正
   sudo chown -R 1000:1000 data/ logs/
   ```

5. **AIメッセージが生成されない**
   ```bash
   # Gemini APIキーを確認
   docker-compose exec weather-bot env | grep GEMINI
   
   # フォールバック機能により基本動作は継続されます
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

## 🎯 今後の予定

- [ ] 通知スケジューラーの実装
- [ ] 複数地域の監視機能
- [ ] 天気データのキャッシュ機能
- [ ] Webダッシュボードの追加
- [ ] 多言語対応
- [ ] カスタム天気アラート