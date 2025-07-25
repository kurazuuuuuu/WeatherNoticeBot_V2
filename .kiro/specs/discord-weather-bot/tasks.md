# Implementation Plan

- [x] 1. プロジェクト基盤とコア設定の構築

  - プロジェクト構造の作成（ディレクトリ、設定ファイル）
  - 依存関係の定義（requirements.txt）
  - 環境変数設定とコンフィグ管理の実装
  - _Requirements: 1.1, 8.1_

- [x] 2. データベースモデルとマイグレーションの実装

  - SQLAlchemy を使用した User モデルの作成
  - データベース接続とセッション管理の実装
  - マイグレーション機能の実装
  - _Requirements: 3.1, 3.2, 3.3_

- [x] 3. 気象庁 API サービスの実装
- [x] 3.1 基本的な API クライアントの作成

  - aiohttp を使用した HTTP クライアントの実装
  - 気象庁 API のベース URL とエンドポイント定義
  - エラーハンドリングとリトライ機能の実装
  - _Requirements: 1.1, 1.4_

- [x] 3.2 地域情報取得機能の実装

  - area.json から地域情報を取得する機能
  - 地域名検索機能（漢字、かな、英語対応）
  - 地域コードの検証機能
  - _Requirements: 3.1, 3.4_

- [x] 3.3 天気情報取得機能の実装

  - 現在の天気情報取得 API
  - 天気予報取得 API（最大 7 日間）
  - 気象警報・注意報取得 API
  - _Requirements: 1.1, 1.2, 1.3, 4.1, 4.2_

- [x] 4. ユーザー管理サービスの実装
- [x] 4.1 ユーザー位置情報管理

  - ユーザーの地域設定保存機能
  - ユーザー情報の取得・更新機能
  - データベース CRUD 操作の実装
  - _Requirements: 3.1, 3.2, 3.3, 3.5_

- [x] 4.2 通知スケジュール管理

  - 1 時間単位での通知時間設定機能
  - 通知の有効化・無効化機能
  - ユーザー設定の表示機能
  - _Requirements: 5.1, 5.3_

- [x] 5. Google Gemini AI 統合の実装
- [x] 5.1 AI メッセージ生成サービス

  - Google Gemini API クライアントの実装
  - 天気情報に基づくポジティブメッセージ生成
  - API エラー時のフォールバック機能
  - _Requirements: 6.1, 6.2, 6.3, 6.4_

- [x] 6. Discord ボットコアの実装
- [x] 6.1 ボット基盤の構築

  - discord.py を使用したボットクライアントの作成
  - コマンドハンドラーの基本構造実装
  - ボット起動とシャットダウン処理
  - _Requirements: 1.1, 8.1, 8.3_

- [x] 6.2 天気情報コマンドの実装

  - `/weather`コマンド（現在の天気）
  - `/forecast`コマンド（天気予報）
  - `/weather-alerts`コマンド（気象警報）
  - _Requirements: 1.1, 1.2, 1.3, 2.1, 2.2, 4.1, 4.2_

- [x] 6.3 ユーザー設定コマンドの実装

  - `/set-location`コマンド（位置設定）
  - `/schedule-weather`コマンド（通知設定）
  - `/unschedule-weather`コマンド（通知停止）
  - `/my-settings`コマンド（設定表示）
  - _Requirements: 3.1, 3.2, 3.4, 5.1, 5.3_

- [x] 7. 定時通知システムの実装
- [x] 7.1 スケジューラーサービスの構築

  - APScheduler を使用したジョブスケジューラー
  - 1 時間単位での通知スケジュール管理
  - ユーザーごとの個別スケジュール処理
  - _Requirements: 5.1, 5.2_

- [x] 7.2 DM 通知機能の実装

  - 定時天気情報の DM 送信機能
  - AI メッセージ付き天気情報の配信
  - 送信エラー時のリトライ機能
  - _Requirements: 5.1, 5.2, 6.1, 6.2_

- [x] 8. Discord Embed 表示の実装
- [x] 8.1 天気情報の視覚的表示

  - 天気情報用の Discord Embed 作成
  - 天気アイコンと色分けの実装
  - 温度単位（摂氏）での表示
  - _Requirements: 7.1, 7.2, 7.3_

- [x] 8.2 予報情報の表示最適化

  - 複数日予報のページネーション
  - 長いメッセージの分割表示
  - エラーメッセージの適切な表示
  - _Requirements: 7.4, 1.4, 2.3_

- [x] 9. エラーハンドリングとロバストネスの実装
- [x] 9.1 API 障害対応

  - 気象庁 API エラー時の処理
  - Google Gemini API エラー時の処理
  - レート制限とリトライ機能
  - _Requirements: 1.4, 6.4, 8.3_

- [x] 9.2 データベース障害対応

  - データベース接続エラー処理
  - 一時的なメモリストレージ機能
  - データ整合性チェック
  - _Requirements: 3.5, 8.3_

- [x] 10. テストスイートの実装
- [x] 10.1 ユニットテストの作成

  - WeatherService のテスト（API モック使用）
  - UserService のテスト（データベース操作）
  - AIService のテスト（Gemini API モック）
  - _Requirements: 全要件のテストカバレッジ_

- [x] 10.2 統合テストの作成

  - 実際の API との統合テスト
  - データベース統合テスト
  - Discord 統合テスト（テストサーバー使用）
  - _Requirements: 全要件の統合テスト_

- [x] 11. 管理者機能とデプロイメント準備
- [x] 11.1 管理者コマンドの実装

  - `/weather-config`コマンド（サーバー設定）
  - ボット統計情報の表示機能
  - ログ管理とモニタリング機能
  - _Requirements: 8.1, 8.2, 8.3_

- [x] 11.2 本番環境対応

  - PostgreSQL 対応の実装
  - 環境別設定の分離
  - ログ設定とエラー監視
  - _Requirements: 8.3_

- [x] 12. ドキュメントとデプロイメント
- [x] 12.1 ユーザードキュメントの作成

  - コマンド使用方法のドキュメント
  - セットアップガイドの作成
  - トラブルシューティングガイド
  - _Requirements: 全要件のドキュメント化_

- [x] 12.2 デプロイメント設定

  - Docker 設定の作成
  - 環境変数設定ガイド
  - 本番環境デプロイメント手順
  - _Requirements: 8.3_

- [x] 13. 主要都市リスト機能の実装
- [x] 13.1 主要都市データの構築

  - 地域別（関東、関西、九州など）の主要都市データ構造の作成
  - 都道府県情報と都市名（日本語・ローマ字）の整理
  - 地域コードとのマッピング実装
  - _Requirements: 9.1, 9.3, 9.6_

- [x] 13.2 主要都市リスト表示コマンドの実装

  - `/locations`コマンドの実装
  - 地域別の都市リスト表示機能
  - ページネーション機能の実装
  - _Requirements: 9.1, 9.2, 9.5_

- [x] 13.3 都市選択インタラクションの実装
  - リストから都市を選択して天気コマンドで使用する機能
  - ボタンまたはドロップダウンによる選択 UI
  - 選択後の天気情報表示連携
  - _Requirements: 9.4_
