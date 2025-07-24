# Discord Weather Bot 🌤️

日本気象庁 API を使用した Discord 天気情報ボット

## 🚀 機能

### 天気情報コマンド

- **`/weather`** - 現在の天気情報を表示（地域指定可能）
- **`/forecast`** - 5 日間の天気予報を表示
- **`/weather-alerts`** - 気象警報・注意報を表示
- **`/locations`** - 主要都市の一覧を表示（地域指定可能）

### ユーザー設定コマンド

- **`/set-location`** - ユーザー個別の地域設定
- **`/schedule-weather`** - 指定時間に天気情報を DM 通知
- **`/unschedule-weather`** - 定時通知を停止
- **`/my-settings`** - 現在の設定を表示

### 管理者コマンド

- **`/weather-config`** - サーバー設定管理（管理者専用）
- **`/stats`** - ボット統計情報表示（管理者専用）

### AI 機能

- **Google Gemini AI**によるポジティブなメッセージ生成
- 天気に応じた励ましメッセージ
- フォールバック機能で安定動作

### スケジューラー機能

- 定時通知システム
- ユーザー個別のスケジュール管理
- 自動的な天気情報配信

## 🚀 クイックスタート

### 1. 初回セットアップ

```bash
# 環境変数を設定
cp .env.example .env
# .envファイルを編集してDISCORD_TOKENとGEMINI_API_KEYを設定
```

### 2. Docker Compose での起動

#### 本番環境

```bash
# 本番環境での起動（デタッチモード）
docker compose -f docker-compose.prod.yml up -d
```

#### 開発環境

```bash
# 開発環境での起動（デタッチモード）
docker compose -f docker-compose.dev.yml up -d
```

#### 標準環境

```bash
# 標準設定での起動（デタッチモード）
docker compose up -d
```

#### 管理コマンド

```bash
docker compose stop      # 停止
docker compose restart   # 再起動
docker compose logs -f   # ログ表示
docker compose ps        # 状態確認
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

### 開発用コマンド

```bash
# コードフォーマット
uv run ruff format .

# リンター実行
uv run ruff check .

# テスト実行
uv run pytest
```

## 📋 必要な設定

### Discord Bot 設定

1. [Discord Developer Portal](https://discord.com/developers/applications/)でボットを作成
2. 以下の権限を設定：
   - `applications.commands` (スラッシュコマンド)
   - `bot` (ボット基本権限)
   - View Channels, Send Messages, Embed Links, Use Slash Commands

### 環境変数

詳細な環境変数の説明は[環境変数ドキュメント](docs/environment-variables.md)を参照してください。

| 変数名              | 必須 | 説明                                           |
| ------------------- | ---- | ---------------------------------------------- |
| `DISCORD_TOKEN`     | ✅   | Discord ボットのトークン ID                    |
| `GEMINI_API_KEY`    | ❌   | Google Gemini API キー（AI 機能用）            |
| `DATABASE_URL`      | ❌   | データベース接続 URL（デフォルト: SQLite）     |
| `DISCORD_GUILD_ID`  | ❌   | テスト用サーバー ID（開発時推奨）              |
| `LOG_LEVEL`         | ❌   | ログレベル（デフォルト: INFO）                 |
| `SCHEDULER_ENABLED` | ❌   | スケジューラー機能の有効化（デフォルト: true） |

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
│   │   ├── weather_service_major_cities.py
│   │   ├── user_service.py
│   │   ├── ai_service.py
│   │   └── scheduler_service.py
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
│   ├── check_area_codes.py # エリアコード確認
│   └── run.py              # ボット起動用
├── docs/                   # ドキュメント
│   ├── setup-guide.md      # セットアップガイド
│   ├── user-guide.md       # ユーザーガイド
│   ├── environment-variables.md # 環境変数説明
│   ├── deployment.md       # デプロイメント手順
│   └── troubleshooting-guide.md # トラブルシューティング
├── .github/workflows/      # GitHub Actions
│   ├── deploy.yml          # デプロイワークフロー
│   └── rollback.yml        # ロールバックワークフロー
├── alembic/                # データベースマイグレーション
├── data/                   # データファイル（SQLite等）
├── logs/                   # ログファイル
├── docker-compose.yml      # 標準Docker設定
├── docker-compose.dev.yml  # 開発環境用Docker設定
├── docker-compose.prod.yml # 本番環境用Docker設定
├── Dockerfile              # Dockerイメージ定義
└── pyproject.toml          # Python プロジェクト設定
```

## 🔧 Docker Compose 構成

### サービス構成

- **weather-bot**: メインの Discord ボット
- **db**: PostgreSQL データベース（オプション）

### ボリューム

- `./data`: データベースファイル（SQLite 使用時）
- `./logs`: ログファイル
- `postgres_data`: PostgreSQL データ

### ネットワーク

- `weather-bot-network`: 内部通信用ネットワーク

### 環境別設定

- **docker-compose.yml**: 標準設定（SQLite 使用）
- **docker-compose.dev.yml**: 開発環境（ホットリロード対応）
- **docker-compose.prod.yml**: 本番環境（PostgreSQL 使用）

## 📊 監視・ヘルスチェック

```bash
# サービス状態確認
docker compose ps

# ヘルスチェック状態確認
docker compose exec weather-bot python -c "print('Bot is healthy')"

# ログ監視
docker compose logs -f weather-bot

# 特定のサービスのログ監視
docker compose logs -f db
```

## 🧪 テスト・デバッグ

### テスト実行

```bash
# 全テスト実行
uv run pytest

# 特定のテスト実行
uv run pytest tests/test_weather_service.py

# カバレッジ付きテスト実行
uv run pytest --cov=src

# Docker環境でのテスト実行
docker compose exec weather-bot python -m pytest tests/
```

### デバッグスクリプト

```bash
# 気象庁API構造確認
uv run python debug/debug_api.py

# 天気予報API構造確認
uv run python debug/debug_forecast.py

# エリアコード確認
uv run python debug/check_area_codes.py

# ボット起動（デバッグ用）
uv run python debug/run.py
```

## ⏱️ コマンド登録について

### スラッシュコマンドの反映時間

- **グローバルコマンド**: 最大 1 時間（通常 15-30 分）
- **ギルド限定コマンド**: 即座（数秒以内）

### 開発時の設定

開発・テスト時は`.env`ファイルで`DISCORD_GUILD_ID`を設定することで、即座にコマンドが反映されます：

```bash
# .envファイル
DISCORD_GUILD_ID=your_test_server_id
```

## 🚨 トラブルシューティング

詳細なトラブルシューティングガイドは[こちら](docs/troubleshooting-guide.md)を参照してください。

### よくある問題

1. **ボットが起動しない**

   ```bash
   # ログを確認
   docker compose logs weather-bot

   # 環境変数を確認
   docker compose exec weather-bot env | grep DISCORD
   ```

2. **コマンドが表示されない**

   ```bash
   # コマンド同期状況を確認
   docker compose logs weather-bot | grep "コマンド"

   # ギルドIDを設定して即座反映（開発時）
   echo "DISCORD_GUILD_ID=your_guild_id" >> .env
   ```

3. **データベース接続エラー**

   ```bash
   # データベースサービス確認
   docker compose ps db

   # データベース接続テスト
   docker compose exec db psql -U weather_user -d weather_bot -c "SELECT 1;"
   ```

4. **権限エラー**

   ```bash
   # ファイル権限確認
   ls -la data/ logs/

   # 権限修正
   sudo chown -R 1000:1000 data/ logs/
   ```

5. **AI メッセージが生成されない**

   ```bash
   # Gemini APIキーを確認
   docker compose exec weather-bot env | grep GEMINI

   # フォールバック機能により基本動作は継続されます
   ```

6. **スケジューラーが動作しない**

   ```bash
   # スケジューラーサービスの状態確認
   docker compose logs weather-bot | grep "scheduler"

   # 環境変数確認
   docker compose exec weather-bot env | grep SCHEDULER_ENABLED
   ```

## 📝 ライセンス

このプロジェクトは MIT ライセンスの下で公開されています。

## 🤝 コントリビューション

1. このリポジトリをフォーク
2. 機能ブランチを作成 (`git checkout -b feature/amazing-feature`)
3. 変更をコミット (`git commit -m 'Add amazing feature'`)
4. ブランチにプッシュ (`git push origin feature/amazing-feature`)
5. プルリクエストを作成

## 📞 サポート

問題や質問がある場合は、GitHub の Issues ページでお知らせください。

## 🎯 今後の予定

- [x] 通知スケジューラーの実装
- [x] 主要都市の天気情報表示機能
- [ ] 複数地域の監視機能
- [ ] 天気データのキャッシュ機能
- [ ] Web ダッシュボードの追加
- [ ] 多言語対応
- [ ] カスタム天気アラート
- [ ] 気象データの統計分析機能

## 📚 ドキュメント

詳細なドキュメントは以下を参照してください：

- [セットアップガイド](docs/setup-guide.md)
- [ユーザーガイド](docs/user-guide.md)
- [環境変数説明](docs/environment-variables.md)
- [デプロイメント手順](docs/deployment.md)
- [コマンドリファレンス](docs/command-reference.md)
- [トラブルシューティング](docs/troubleshooting-guide.md)
