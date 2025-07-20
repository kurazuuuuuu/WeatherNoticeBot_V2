# デプロイメントガイド

このドキュメントでは、Discord Weather BotのGitHub Actionsを使用した自動デプロイについて説明します。

## 概要

- **自動デプロイ**: mainブランチへのpushで自動的にself-hosted runnerでデプロイ
- **手動デプロイ**: GitHub Actionsの画面から手動実行可能
- **ロールバック**: 問題発生時に前のバージョンに戻すことが可能

## Self-hosted Runnerの設定

### 1. GitHub Runnerの追加

1. GitHubリポジトリの「Settings」→「Actions」→「Runners」に移動
2. 「New self-hosted runner」をクリック
3. OSを選択（Linux/macOS/Windows）
4. 表示されるコマンドを自宅サーバーで実行

### 2. 必要な依存関係のインストール

自宅サーバーに以下をインストールしてください：

```bash
# Docker & Docker Compose
curl -fsSL https://get.docker.com -o get-docker.sh
sudo sh get-docker.sh
sudo usermod -aG docker $USER

# Docker Compose（最新版）
sudo curl -L "https://github.com/docker/compose/releases/latest/download/docker-compose-$(uname -s)-$(uname -m)" -o /usr/local/bin/docker-compose
sudo chmod +x /usr/local/bin/docker-compose

# jq（JSONパーサー）
sudo apt-get update && sudo apt-get install -y jq

# 再ログインしてDockerグループを有効化
newgrp docker
```

### 3. 環境変数の設定

プロジェクトルートに`.env`ファイルを作成：

```bash
cp .env.example .env
# .envファイルを編集して実際の値を設定
```

## デプロイワークフロー

### 自動デプロイ

mainブランチにpushすると自動的に以下の処理が実行されます：

1. **コードのチェックアウト**: 最新のコードを取得
2. **既存コンテナの停止**: 現在動作中のコンテナを停止・削除
3. **イメージのビルド**: 新しいDockerイメージをビルド
4. **アプリケーションの起動**: Docker Composeでアプリケーションを起動
5. **ヘルスチェック**: アプリケーションが正常に起動したか確認

### 手動デプロイ

GitHub Actionsの画面から手動でデプロイを実行できます：

1. GitHubリポジトリの「Actions」タブに移動
2. 「自動デプロイ」ワークフローを選択
3. 「Run workflow」をクリック

### ローカルでのデプロイ

サーバーに直接ログインしてデプロイすることも可能です：

```bash
# 本番環境デプロイ
./scripts/deploy.sh

# 開発環境デプロイ
./scripts/deploy.sh dev
```

## ロールバック

問題が発生した場合、前のバージョンにロールバックできます：

### GitHub Actionsでのロールバック

1. GitHubリポジトリの「Actions」タブに移動
2. 「ロールバック」ワークフローを選択
3. 「Run workflow」をクリック
4. 必要に応じてロールバック先のコミットSHAを指定（省略時は直前のコミット）

### 手動ロールバック

```bash
# 特定のコミットにロールバック
git checkout <コミットSHA>
./scripts/deploy.sh

# 直前のコミットにロールバック
git checkout HEAD~1
./scripts/deploy.sh
```

## 監視とログ

### コンテナの状態確認

```bash
# コンテナの状態を確認
docker compose ps

# ログを確認
docker compose logs -f weather-bot

# 最新のログを確認
docker compose logs --tail=50 weather-bot
```

### ログファイル

- **アプリケーションログ**: `logs/weather_bot.log`
- **エラーログ**: `logs/error.log`
- **デプロイログ**: `logs/deploy.log`

## トラブルシューティング

### よくある問題

#### 1. 環境変数が設定されていない

```bash
# .envファイルの確認
cat .env

# 必要な環境変数が設定されているか確認
docker compose config
```

#### 2. ポートが使用中

```bash
# ポートの使用状況を確認
sudo netstat -tlnp | grep :5432  # PostgreSQL
sudo netstat -tlnp | grep :6379  # Redis

# 使用中のプロセスを停止
sudo kill -9 <PID>
```

#### 3. Dockerイメージのビルドエラー

```bash
# キャッシュをクリアしてビルド
docker compose build --no-cache

# 未使用のイメージを削除
docker system prune -a
```

#### 4. Self-hosted Runnerが応答しない

```bash
# Runnerサービスの状態確認
sudo systemctl status actions.runner.*

# Runnerサービスの再起動
sudo systemctl restart actions.runner.*
```

## セキュリティ考慮事項

1. **環境変数の管理**: 機密情報は`.env`ファイルで管理し、Gitにコミットしない
2. **ファイアウォール**: 必要なポートのみ開放
3. **定期的な更新**: Dockerイメージとシステムの定期的な更新
4. **ログの監視**: 異常なアクセスやエラーの監視

## パフォーマンス最適化

1. **リソース制限**: Docker ComposeでメモリとCPUの制限を設定
2. **ログローテーション**: ログファイルのサイズ制限と自動削除
3. **定期的なクリーンアップ**: 未使用のDockerイメージとコンテナの削除

```bash
# 定期的なクリーンアップ（cronで実行推奨）
docker system prune -f
docker volume prune -f
```