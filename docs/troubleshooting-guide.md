# Discord Weather Bot トラブルシューティングガイド 🔧

このガイドでは、Discord Weather Botで発生する可能性のある問題とその解決方法について説明します。

## 📋 目次

1. [一般的な問題](#一般的な問題)
2. [起動・接続の問題](#起動接続の問題)
3. [コマンドの問題](#コマンドの問題)
4. [データベースの問題](#データベースの問題)
5. [API関連の問題](#api関連の問題)
6. [通知機能の問題](#通知機能の問題)
7. [パフォーマンスの問題](#パフォーマンスの問題)
8. [ログの確認方法](#ログの確認方法)
9. [緊急時の対応](#緊急時の対応)

## 一般的な問題

### ❌ ボットがオフライン状態

**症状**: Discordでボットがオフライン表示される

**原因と解決方法**:

1. **Docker コンテナの状態確認**
   ```bash
   # コンテナの状態を確認
   docker compose ps
   
   # 停止している場合は起動
   docker compose up -d weather-bot
   
   # 注意: 新しいDocker Composeでは「docker compose」（スペース区切り）を使用します
   # 古いバージョンでは「docker-compose」（ハイフン区切り）を使用します
   ```

2. **ログの確認**
   ```bash
   # エラーログを確認
   docker-compose logs weather-bot
   
   # リアルタイムでログを監視
   docker-compose logs -f weather-bot
   ```

3. **環境変数の確認**
   ```bash
   # Discord トークンが正しく設定されているか確認
   docker-compose exec weather-bot env | grep DISCORD_TOKEN
   ```

4. **ネットワーク接続の確認**
   ```bash
   # Discord APIへの接続テスト
   docker-compose exec weather-bot ping discord.com
   ```

### ❌ コマンドが表示されない

**症状**: スラッシュコマンドが Discord で表示されない

**原因と解決方法**:

1. **コマンド同期の確認**
   ```bash
   # コマンド同期のログを確認
   docker-compose logs weather-bot | grep "コマンド"
   ```

2. **権限の確認**
   - ボットに `applications.commands` 権限があるか確認
   - サーバーでボットが適切な権限を持っているか確認

3. **ギルド限定コマンドの設定（開発時）**
   ```bash
   # .env ファイルにギルドIDを追加
   echo "DISCORD_GUILD_ID=your_guild_id" >> .env
   docker-compose restart weather-bot
   ```

4. **時間の経過を待つ**
   - グローバルコマンドは反映に最大1時間かかる場合があります
   - ギルド限定コマンドは数秒で反映されます

### ❌ 天気情報が取得できない

**症状**: 天気コマンドでエラーが発生する

**原因と解決方法**:

1. **気象庁APIの接続確認**
   ```bash
   # 気象庁APIへの接続テスト
   docker-compose exec weather-bot curl -I https://www.jma.go.jp/bosai/common/const/area.json
   ```

2. **地域名の確認**
   - 正しい地域名を使用しているか確認
   - 対応している地域形式を使用しているか確認

3. **APIレート制限の確認**
   ```bash
   # レート制限関連のログを確認
   docker-compose logs weather-bot | grep -i "rate\|limit"
   ```

## 起動・接続の問題

### 🚀 ボットが起動しない

#### Docker 関連の問題

**症状**: `docker-compose up` でエラーが発生

**解決方法**:

1. **Docker サービスの確認**
   ```bash
   # Docker が起動しているか確認
   sudo systemctl status docker
   
   # 起動していない場合
   sudo systemctl start docker
   ```

2. **ポートの競合確認**
   ```bash
   # 使用中のポートを確認
   sudo netstat -tulpn | grep :5432  # PostgreSQL
   sudo netstat -tulpn | grep :6379  # Redis
   ```

3. **ディスク容量の確認**
   ```bash
   # ディスク使用量を確認
   df -h
   
   # Docker の使用量を確認
   docker system df
   ```

4. **権限の問題**
   ```bash
   # ファイル権限を修正
   sudo chown -R $USER:$USER data/ logs/
   chmod 755 data/ logs/
   ```

#### 環境変数の問題

**症状**: 環境変数関連のエラー

**解決方法**:

1. **環境変数ファイルの確認**
   ```bash
   # .env ファイルが存在するか確認
   ls -la .env
   
   # 内容を確認（機密情報に注意）
   cat .env | grep -v TOKEN | grep -v KEY
   ```

2. **必須環境変数の確認**
   ```bash
   # 必須変数が設定されているか確認
   docker-compose config | grep -E "DISCORD_TOKEN|DATABASE_URL"
   ```

3. **環境変数の形式確認**
   ```bash
   # 正しい形式の例
   DISCORD_TOKEN=your_token_here
   DATABASE_URL=sqlite:///data/weather_bot.db
   LOG_LEVEL=INFO
   ```

### 🔌 ネットワーク接続の問題

**症状**: 外部APIへの接続が失敗する

**解決方法**:

1. **DNS解決の確認**
   ```bash
   # DNS解決をテスト
   docker-compose exec weather-bot nslookup discord.com
   docker-compose exec weather-bot nslookup www.jma.go.jp
   ```

2. **ファイアウォールの確認**
   ```bash
   # ファイアウォール状態を確認
   sudo ufw status
   
   # 必要に応じてポートを開放
   sudo ufw allow out 443/tcp  # HTTPS
   sudo ufw allow out 80/tcp   # HTTP
   ```

3. **プロキシ設定の確認**
   ```bash
   # プロキシ環境変数を確認
   env | grep -i proxy
   ```

## コマンドの問題

### ⚡ コマンドが応答しない

**症状**: コマンドを実行しても応答がない

**解決方法**:

1. **ボットの応答確認**
   ```bash
   # ボットのプロセス状態を確認
   docker-compose exec weather-bot ps aux
   ```

2. **メモリ使用量の確認**
   ```bash
   # メモリ使用量を確認
   docker stats weather-bot --no-stream
   ```

3. **ログレベルの調整**
   ```bash
   # デバッグログを有効化
   echo "LOG_LEVEL=DEBUG" >> .env
   docker-compose restart weather-bot
   ```

### 🔍 特定のコマンドでエラー

**症状**: 特定のコマンドのみエラーが発生

**解決方法**:

1. **コマンド固有のログ確認**
   ```bash
   # 特定のコマンドのエラーログを検索
   docker-compose logs weather-bot | grep -i "weather\|forecast\|alert"
   ```

2. **データベース接続の確認**
   ```bash
   # データベース接続をテスト
   docker-compose exec weather-bot python -c "
   from src.database import get_db_session
   with get_db_session() as session:
       print('Database connection OK')
   "
   ```

3. **API接続の個別テスト**
   ```bash
   # 気象庁API接続テスト
   docker-compose exec weather-bot python debug/debug_api.py
   
   # 天気予報API接続テスト
   docker-compose exec weather-bot python debug/debug_forecast.py
   ```

## データベースの問題

### 💾 データベース接続エラー

**症状**: データベース関連のエラーが発生

**解決方法**:

#### SQLite の場合

1. **ファイル権限の確認**
   ```bash
   # データベースファイルの権限を確認
   ls -la data/weather_bot.db
   
   # 権限を修正
   chmod 664 data/weather_bot.db
   chown $USER:$USER data/weather_bot.db
   ```

2. **ディスク容量の確認**
   ```bash
   # ディスク容量を確認
   df -h data/
   ```

3. **データベースファイルの整合性確認**
   ```bash
   # SQLite の整合性チェック
   sqlite3 data/weather_bot.db "PRAGMA integrity_check;"
   ```

#### PostgreSQL の場合

1. **PostgreSQL サービスの確認**
   ```bash
   # PostgreSQL コンテナの状態確認
   docker-compose ps db
   
   # PostgreSQL ログの確認
   docker-compose logs db
   ```

2. **接続テスト**
   ```bash
   # データベースへの接続テスト
   docker-compose exec db psql -U weather_user -d weather_bot -c "SELECT 1;"
   ```

3. **データベースの再作成**
   ```bash
   # データベースを再作成（データが失われます）
   docker-compose down
   docker volume rm $(docker volume ls -q | grep postgres)
   docker-compose up -d db
   
   # マイグレーションを実行
   docker-compose exec weather-bot alembic upgrade head
   ```

### 🔄 マイグレーションの問題

**症状**: データベースマイグレーションでエラー

**解決方法**:

1. **現在のマイグレーション状態確認**
   ```bash
   # マイグレーション履歴を確認
   docker-compose exec weather-bot alembic history
   
   # 現在のリビジョンを確認
   docker-compose exec weather-bot alembic current
   ```

2. **マイグレーションの修復**
   ```bash
   # 特定のリビジョンにダウングレード
   docker-compose exec weather-bot alembic downgrade base
   
   # 最新にアップグレード
   docker-compose exec weather-bot alembic upgrade head
   ```

3. **手動でのテーブル作成**
   ```bash
   # 緊急時の手動テーブル作成
   docker-compose exec weather-bot python -c "
   from src.database import engine
   from src.models import Base
   Base.metadata.create_all(engine)
   "
   ```

## API関連の問題

### 🌐 気象庁API の問題

**症状**: 天気情報の取得に失敗

**解決方法**:

1. **API エンドポイントの確認**
   ```bash
   # 気象庁APIの状態確認
   curl -I https://www.jma.go.jp/bosai/common/const/area.json
   ```

2. **レート制限の確認**
   ```bash
   # レート制限関連のログを確認
   docker-compose logs weather-bot | grep -i "rate\|429\|limit"
   ```

3. **API レスポンスの確認**
   ```bash
   # デバッグスクリプトでAPI応答を確認
   docker-compose exec weather-bot python debug/debug_api.py
   ```

4. **キャッシュの確認**
   ```bash
   # キャッシュされたデータの確認
   docker-compose exec weather-bot python -c "
   from src.services.weather_service import WeatherService
   service = WeatherService()
   # キャッシュ状態を確認
   "
   ```

### 🤖 Google Gemini API の問題

**症状**: AI メッセージが生成されない

**解決方法**:

1. **API キーの確認**
   ```bash
   # Gemini API キーが設定されているか確認
   docker-compose exec weather-bot env | grep GEMINI_API_KEY
   ```

2. **API 接続テスト**
   ```bash
   # Gemini API の接続テスト
   docker-compose exec weather-bot python -c "
   import os
   import google.generativeai as genai
   genai.configure(api_key=os.getenv('GEMINI_API_KEY'))
   model = genai.GenerativeModel('gemini-pro')
   response = model.generate_content('Hello')
   print('API connection OK')
   "
   ```

3. **フォールバック機能の確認**
   ```bash
   # AI機能なしでの動作確認
   unset GEMINI_API_KEY
   docker-compose restart weather-bot
   ```

## 通知機能の問題

### 📱 DM 通知が送信されない

**症状**: 定時通知が届かない

**解決方法**:

1. **スケジューラーの状態確認**
   ```bash
   # スケジューラー関連のログを確認
   docker-compose logs weather-bot | grep -i "schedule\|notification"
   ```

2. **ユーザー設定の確認**
   ```bash
   # データベースでユーザー設定を確認
   docker-compose exec weather-bot python -c "
   from src.database import get_db_session
   from src.models.user import User
   with get_db_session() as session:
       users = session.query(User).filter(User.is_notification_enabled == True).all()
       for user in users:
           print(f'User {user.discord_id}: {user.notification_hour}時')
   "
   ```

3. **DM 権限の確認**
   ```bash
   # ボットがDMを送信できるか確認
   # Discord設定でDMを許可しているか確認
   ```

4. **タイムゾーンの確認**
   ```bash
   # システムのタイムゾーンを確認
   docker-compose exec weather-bot date
   docker-compose exec weather-bot python -c "
   import datetime
   print(datetime.datetime.now())
   "
   ```

### ⏰ スケジュール設定の問題

**症状**: 通知時間が正しく設定されない

**解決方法**:

1. **APScheduler の状態確認**
   ```bash
   # スケジューラーのジョブ一覧を確認
   docker-compose logs weather-bot | grep -i "job\|scheduler"
   ```

2. **時間設定の確認**
   ```bash
   # 設定された通知時間を確認
   docker-compose exec weather-bot python -c "
   from src.services.scheduler_service import SchedulerService
   scheduler = SchedulerService()
   # ジョブ一覧を表示
   "
   ```

## パフォーマンスの問題

### 🐌 応答が遅い

**症状**: コマンドの応答に時間がかかる

**解決方法**:

1. **リソース使用量の確認**
   ```bash
   # CPU・メモリ使用量を確認
   docker stats weather-bot --no-stream
   
   # システム全体のリソース確認
   top
   htop
   ```

2. **データベースクエリの最適化**
   ```bash
   # 遅いクエリの確認
   docker-compose logs weather-bot | grep -i "slow\|timeout"
   ```

3. **ネットワーク遅延の確認**
   ```bash
   # 外部API への応答時間測定
   docker-compose exec weather-bot time curl -s https://www.jma.go.jp/bosai/common/const/area.json > /dev/null
   ```

### 💾 メモリ使用量が多い

**症状**: メモリ使用量が異常に高い

**解決方法**:

1. **メモリリークの確認**
   ```bash
   # メモリ使用量の推移を監視
   watch -n 5 'docker stats weather-bot --no-stream'
   ```

2. **ログファイルのサイズ確認**
   ```bash
   # ログファイルのサイズを確認
   du -sh logs/
   
   # 古いログを削除
   find logs/ -name "*.log" -mtime +7 -delete
   ```

3. **メモリ制限の設定**
   ```yaml
   # docker-compose.yml に追加
   services:
     weather-bot:
       deploy:
         resources:
           limits:
             memory: 512M
   ```

## ログの確認方法

### 📋 基本的なログ確認

```bash
# 全ログを表示
docker-compose logs weather-bot

# 最新100行を表示
docker-compose logs --tail=100 weather-bot

# リアルタイムでログを監視
docker-compose logs -f weather-bot

# 特定の時間範囲のログ
docker-compose logs --since="2024-01-01T00:00:00" --until="2024-01-01T23:59:59" weather-bot
```

### 🔍 ログの検索とフィルタリング

```bash
# エラーログのみを表示
docker-compose logs weather-bot | grep -i error

# 特定のキーワードでフィルタ
docker-compose logs weather-bot | grep -i "weather\|forecast"

# 複数のキーワードで検索
docker-compose logs weather-bot | grep -E "(error|warning|exception)"

# ログレベル別の確認
docker-compose logs weather-bot | grep -E "(INFO|DEBUG|WARNING|ERROR)"
```

### 📊 ログ分析

```bash
# エラーの頻度を確認
docker-compose logs weather-bot | grep -i error | wc -l

# 最も多いエラーを確認
docker-compose logs weather-bot | grep -i error | sort | uniq -c | sort -nr

# 時間別のログ分布
docker-compose logs weather-bot | grep "$(date +%Y-%m-%d)" | cut -d' ' -f1-2 | sort | uniq -c
```

## 緊急時の対応

### 🚨 ボットが完全に停止した場合

1. **即座の復旧**
   ```bash
   # 強制的に再起動
   docker-compose down --remove-orphans
   docker-compose up -d weather-bot
   ```

2. **データの確認**
   ```bash
   # データベースの整合性確認
   docker-compose exec weather-bot python -c "
   from src.database import get_db_session
   with get_db_session() as session:
       print('Database is accessible')
   "
   ```

3. **設定の復元**
   ```bash
   # バックアップから設定を復元
   cp .env.backup .env
   docker-compose restart weather-bot
   ```

### 🔄 ロールバック手順

1. **前のバージョンに戻す**
   ```bash
   # Git で前のコミットに戻す
   git log --oneline -10
   git checkout <previous-commit-hash>
   
   # Docker イメージを再ビルド
   docker-compose build weather-bot
   docker-compose up -d weather-bot
   ```

2. **データベースのロールバック**
   ```bash
   # マイグレーションを前のバージョンに戻す
   docker-compose exec weather-bot alembic downgrade -1
   ```

### 📞 サポートへの連絡

問題が解決しない場合は、以下の情報を含めてサポートに連絡してください：

1. **環境情報**
   ```bash
   # システム情報を収集
   echo "=== System Info ===" > debug_info.txt
   uname -a >> debug_info.txt
   docker --version >> debug_info.txt
   docker-compose --version >> debug_info.txt
   
   echo "=== Container Status ===" >> debug_info.txt
   docker-compose ps >> debug_info.txt
   
   echo "=== Recent Logs ===" >> debug_info.txt
   docker-compose logs --tail=50 weather-bot >> debug_info.txt
   ```

2. **エラーの詳細**
   - 発生した時刻
   - 実行したコマンド
   - エラーメッセージの全文
   - 再現手順

3. **設定情報**
   - 使用している環境（本番/開発）
   - 環境変数の設定（機密情報は除く）
   - カスタマイズした設定

---

このトラブルシューティングガイドで問題が解決しない場合は、GitHub Issues でサポートを求めてください。可能な限り詳細な情報を提供していただけると、迅速な解決につながります。