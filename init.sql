-- PostgreSQL初期化スクリプト
-- Docker Compose起動時に自動実行されます

-- データベースの作成（既に存在する場合はスキップ）
-- CREATE DATABASE IF NOT EXISTS weather_bot;

-- 必要に応じて追加の初期化処理をここに記述
-- 例：初期データの挿入、インデックスの作成など

-- タイムゾーンの設定
SET timezone = 'Asia/Tokyo';

-- 接続確認用のコメント
-- このスクリプトが実行されると、PostgreSQLが正常に初期化されています