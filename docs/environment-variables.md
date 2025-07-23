# Discord Weather Bot 環境変数設定ガイド 🔧

このガイドでは、Discord Weather Botで使用する環境変数について詳しく説明します。

## 📋 目次

1. [環境変数の概要](#環境変数の概要)
2. [必須環境変数](#必須環境変数)
3. [オプション環境変数](#オプション環境変数)
4. [環境別設定](#環境別設定)
5. [セキュリティ設定](#セキュリティ設定)
6. [設定例](#設定例)
7. [トラブルシューティング](#トラブルシューティング)

## 環境変数の概要

Discord Weather Botは、設定を環境変数で管理します。これにより、異なる環境（開発、テスト、本番）で同じコードを使用できます。

### 設定ファイルの種類

- `.env.example` - 設定例とドキュメント
- `.env.dev` - 開発環境用設定
- `.env.prod` - 本番環境用設定
- `.env` - 実際に使用される設定ファイル
- `.env.docker` - Docker環境用設定

### 設定の優先順位

1. システム環境変数（最優先）
2. `.env` ファイル
3. Docker Compose の environment セクション
4. アプリケーションのデフォルト値

## 必須環境変数

これらの環境変数は、ボットが動作するために必須です。

### DISCORD_TOKEN

**説明**: Discord Bot のトークン  
**形式**: 文字列  
**例**: `DISCORD_TOKEN=トークン

**取得方法**:
1. [Discord Developer Portal](https://discord.com/developers/applications/) にアクセス
2. アプリケーションを作成
3. 「Bot」セクションでトークンを取得

**注意事項**:
- トークンは秘密情報です。他人と共有しないでください
- GitHubなどの公開リポジトリにコミットしないでください
- 定期的にトークンを再生成することを推奨します

### データベース関連（本番環境）

#### POSTGRES_DB
**説明**: PostgreSQL データベース名  
**デフォルト**: `weather_bot`  
**例**: `POSTGRES_DB=weather_bot`

#### POSTGRES_USER
**説明**: PostgreSQL ユーザー名  
**デフォルト**: `weather_user`  
**例**: `POSTGRES_USER=weather_user`

#### POSTGRES_PASSWORD
**説明**: PostgreSQL パスワード  
**形式**: 強力なパスワード（最低12文字、英数字記号混合）  
**例**: `POSTGRES_PASSWORD=MySecurePassword123!`

**パスワード生成例**:
```bash
# ランダムパスワード生成
openssl rand -base64 32

# または
python -c "import secrets; print(secrets.token_urlsafe(32))"
```

## オプション環境変数

これらの環境変数は、機能を拡張するために使用されます。

### AI機能関連

#### GEMINI_API_KEY
**説明**: Google Gemini API キー（AI機能用）  
**形式**: 文字列  
**例**: `GEMINI_API_KEY=AIzaSyAbCdEfGhIjKlMnOpQrStUvWxYz1234567890`

**取得方法**:
1. [Google AI Studio](https://makersuite.google.com/app/apikey) にアクセス
2. APIキーを作成

**注意事項**:
- 設定しない場合、AI機能は無効になりますが基本機能は動作します
- APIキーには使用制限があります

### Discord設定

#### DISCORD_GUILD_ID
**説明**: テスト用サーバーID（開発時のみ）  
**形式**: 数値文字列  
**例**: `DISCORD_GUILD_ID=123456789012345678`

**用途**:
- 開発・テスト時にコマンドを即座に反映
- 本番環境では空にしてグローバルコマンドを使用

**取得方法**:
1. Discordで開発者モードを有効化
2. サーバーを右クリック → 「IDをコピー」

### ログ設定

#### LOG_LEVEL
**説明**: ログレベル  
**選択肢**: `DEBUG`, `INFO`, `WARNING`, `ERROR`, `CRITICAL`  
**デフォルト**: `INFO`  
**例**: `LOG_LEVEL=INFO`

**レベル説明**:
- `DEBUG`: 詳細なデバッグ情報（開発時のみ）
- `INFO`: 一般的な情報（推奨）
- `WARNING`: 警告メッセージのみ
- `ERROR`: エラーメッセージのみ
- `CRITICAL`: 致命的エラーのみ

#### LOG_FILE
**説明**: ログファイルのパス  
**デフォルト**: `logs/weather_bot.log`  
**例**: `LOG_FILE=/app/logs/weather_bot.log`

### パフォーマンス設定

#### JMA_API_RATE_LIMIT
**説明**: 気象庁API の1分間あたりのリクエスト制限  
**デフォルト**: `60`  
**例**: `JMA_API_RATE_LIMIT=60`

#### GEMINI_API_RATE_LIMIT
**説明**: Gemini API の1分間あたりのリクエスト制限  
**デフォルト**: `60`  
**例**: `GEMINI_API_RATE_LIMIT=60`

#### NOTIFICATION_RETRY_ATTEMPTS
**説明**: 通知送信の再試行回数  
**デフォルト**: `3`  
**例**: `NOTIFICATION_RETRY_ATTEMPTS=3`

#### NOTIFICATION_RETRY_DELAY
**説明**: 通知送信の再試行間隔（秒）  
**デフォルト**: `300`  
**例**: `NOTIFICATION_RETRY_DELAY=300`

### タイムゾーン設定

#### DEFAULT_TIMEZONE
**説明**: デフォルトタイムゾーン  
**デフォルト**: `Asia/Tokyo`  
**例**: `DEFAULT_TIMEZONE=Asia/Tokyo`

**対応タイムゾーン例**:
- `Asia/Tokyo` - 日本標準時
- `UTC` - 協定世界時
- `America/New_York` - 東部標準時
- `Europe/London` - グリニッジ標準時

## 環境別設定

### 開発環境 (.env.dev)

```bash
# Discord設定
DISCORD_TOKEN=your_dev_discord_token
DISCORD_GUILD_ID=your_test_server_id

# データベース設定（SQLite）
DATABASE_URL=sqlite:///data/weather_bot_dev.db

# ログ設定
LOG_LEVEL=DEBUG
LOG_FILE=logs/weather_bot_dev.log

# AI機能（オプション）
GEMINI_API_KEY=your_dev_gemini_key

# 環境識別
ENVIRONMENT=development
```

### 本番環境 (.env.prod)

```bash
# Discord設定
DISCORD_TOKEN=your_prod_discord_token
DISCORD_GUILD_ID=  # 空にしてグローバルコマンドを使用

# データベース設定（PostgreSQL）
POSTGRES_DB=weather_bot
POSTGRES_USER=weather_user
POSTGRES_PASSWORD=your_secure_password

# Redis設定
REDIS_PASSWORD=your_redis_password

# AI機能
GEMINI_API_KEY=your_prod_gemini_key

# セキュリティ
SECRET_KEY=your_very_secure_secret_key

# ログ設定
LOG_LEVEL=INFO
LOG_FILE=/app/logs/weather_bot.log

# 監視設定
GRAFANA_PASSWORD=your_grafana_password

# 環境識別
ENVIRONMENT=production
```

## セキュリティ設定

### SECRET_KEY
**説明**: アプリケーション用の秘密鍵  
**形式**: 最低32文字のランダム文字列  
**例**: `SECRET_KEY=your_very_secure_secret_key_minimum_32_characters_long`

**生成方法**:
```bash
# Python を使用
python -c "import secrets; print(secrets.token_urlsafe(32))"

# OpenSSL を使用
openssl rand -base64 32

# uuidgen を使用
uuidgen | tr -d '-'
```

### REDIS_PASSWORD
**説明**: Redis のパスワード  
**形式**: 強力なパスワード  
**例**: `REDIS_PASSWORD=MySecureRedisPassword123!`

### 監視・管理用パスワード

#### GRAFANA_PASSWORD
**説明**: Grafana 管理者パスワード  
**例**: `GRAFANA_PASSWORD=MySecureGrafanaPassword123!`

## 設定例

### 最小構成（開発環境）

```bash
# 最低限必要な設定
DISCORD_TOKEN=your_discord_token_here
DISCORD_GUILD_ID=your_test_server_id
```

### 標準構成（本番環境）

```bash
# Discord設定
DISCORD_TOKEN=your_production_discord_token

# データベース設定
POSTGRES_DB=weather_bot
POSTGRES_USER=weather_user
POSTGRES_PASSWORD=SecurePassword123!

# Redis設定
REDIS_PASSWORD=SecureRedisPassword123!

# AI機能
GEMINI_API_KEY=your_gemini_api_key

# セキュリティ
SECRET_KEY=your_32_character_secret_key_here

# 監視
GRAFANA_PASSWORD=SecureGrafanaPassword123!

# 環境設定
ENVIRONMENT=production
LOG_LEVEL=INFO
```

### 完全構成（全機能有効）

```bash
# Discord設定
DISCORD_TOKEN=your_production_discord_token
DISCORD_GUILD_ID=

# データベース設定
POSTGRES_DB=weather_bot
POSTGRES_USER=weather_user
POSTGRES_PASSWORD=SecurePassword123!

# Redis設定
REDIS_PASSWORD=SecureRedisPassword123!

# AI機能
GEMINI_API_KEY=your_gemini_api_key

# セキュリティ
SECRET_KEY=your_32_character_secret_key_here

# ログ設定
LOG_LEVEL=INFO
LOG_FILE=/app/logs/weather_bot.log

# パフォーマンス設定
JMA_API_RATE_LIMIT=60
GEMINI_API_RATE_LIMIT=60
NOTIFICATION_RETRY_ATTEMPTS=3
NOTIFICATION_RETRY_DELAY=300

# タイムゾーン
DEFAULT_TIMEZONE=Asia/Tokyo

# 監視設定
HEALTH_CHECK_PORT=8080
METRICS_PORT=9090
GRAFANA_PASSWORD=SecureGrafanaPassword123!

# SSL設定（Nginx使用時）
SSL_DOMAIN=your-domain.com
SSL_EMAIL=your-email@example.com

# 環境識別
ENVIRONMENT=production
```

## トラブルシューティング

### よくある問題

#### 1. DISCORD_TOKEN が無効

**症状**: ボットがオンラインにならない  
**解決方法**:
```bash
# トークンの形式を確認
echo $DISCORD_TOKEN | wc -c  # 70文字程度であることを確認

# トークンを再生成
# Discord Developer Portal でトークンをリセット
```

#### 2. データベース接続エラー

**症状**: データベース関連のエラー  
**解決方法**:
```bash
# 環境変数を確認
echo "DB: $POSTGRES_DB"
echo "User: $POSTGRES_USER"
echo "Password length: $(echo $POSTGRES_PASSWORD | wc -c)"

# データベース接続をテスト
docker-compose exec db psql -U $POSTGRES_USER -d $POSTGRES_DB -c "SELECT 1;"
```

#### 3. 環境変数が読み込まれない

**症状**: デフォルト値が使用される  
**解決方法**:
```bash
# .env ファイルの存在確認
ls -la .env

# 環境変数の確認
docker-compose config | grep -E "DISCORD_TOKEN|POSTGRES"

# ファイルの権限確認
chmod 600 .env
```

#### 4. 特殊文字を含むパスワード

**症状**: パスワードが正しく認識されない  
**解決方法**:
```bash
# 特殊文字をエスケープまたは引用符で囲む
POSTGRES_PASSWORD='MyPassword!@#$%'

# または特殊文字を避ける
POSTGRES_PASSWORD=MySecurePassword123
```

### 環境変数の検証

#### 検証スクリプト

```bash
#!/bin/bash
# scripts/validate-env.sh

echo "=== 環境変数検証 ==="

# 必須変数のチェック
required_vars=("DISCORD_TOKEN")

if [ "$ENVIRONMENT" = "production" ]; then
    required_vars+=("POSTGRES_PASSWORD" "REDIS_PASSWORD" "SECRET_KEY")
fi

for var in "${required_vars[@]}"; do
    if [ -z "${!var}" ]; then
        echo "❌ $var が設定されていません"
    else
        echo "✅ $var が設定されています"
    fi
done

# トークンの形式チェック
if [[ "$DISCORD_TOKEN" =~ ^[A-Za-z0-9._-]+$ ]]; then
    echo "✅ DISCORD_TOKEN の形式が正しいです"
else
    echo "❌ DISCORD_TOKEN の形式が正しくありません"
fi

# パスワードの強度チェック
if [ ${#POSTGRES_PASSWORD} -ge 12 ]; then
    echo "✅ POSTGRES_PASSWORD の長さが適切です"
else
    echo "❌ POSTGRES_PASSWORD が短すぎます（12文字以上推奨）"
fi

echo "=== 検証完了 ==="
```

### セキュリティチェック

```bash
#!/bin/bash
# scripts/security-check.sh

echo "=== セキュリティチェック ==="

# .env ファイルの権限チェック
if [ -f .env ]; then
    perm=$(stat -c "%a" .env)
    if [ "$perm" = "600" ]; then
        echo "✅ .env ファイルの権限が適切です"
    else
        echo "❌ .env ファイルの権限を修正してください: chmod 600 .env"
    fi
fi

# 機密情報のGit追跡チェック
if git ls-files | grep -q "\.env$"; then
    echo "❌ .env ファイルがGitで追跡されています"
    echo "   git rm --cached .env を実行してください"
else
    echo "✅ .env ファイルはGitで追跡されていません"
fi

# デフォルトパスワードのチェック
default_passwords=("password" "123456" "admin" "weather_password")

for pwd in "${default_passwords[@]}"; do
    if [ "$POSTGRES_PASSWORD" = "$pwd" ]; then
        echo "❌ デフォルトパスワードが使用されています: $pwd"
    fi
done

echo "=== セキュリティチェック完了 ==="
```

---

この環境変数設定ガイドを参考に、安全で適切な設定を行ってください。問題が発生した場合は、トラブルシューティングセクションを参照してください。