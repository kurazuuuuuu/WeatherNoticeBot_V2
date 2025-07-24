"""
ヘルスチェック機能を提供するモジュール
"""

import os
import sys
import logging
from typing import Dict, Any, Optional

# ロギングの設定
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def check_health() -> bool:
    """
    ボットのヘルスチェックを実行します。
    
    以下の項目を確認します:
    1. 必要な環境変数が設定されているか
    2. 必要なディレクトリが存在するか
    3. データベースマイグレーションが最新か（本番環境では確認のみ）
    
    Returns:
        bool: ヘルスチェックが成功した場合はTrue、失敗した場合はFalse
    """
    try:
        # 1. 必要な環境変数のチェック
        required_env_vars = ["DISCORD_TOKEN"]
        for var in required_env_vars:
            if not os.environ.get(var):
                logger.error(f"必須環境変数 {var} が設定されていません")
                return False
        
        # 2. 必要なディレクトリのチェック
        required_dirs = ["/app/data", "/app/logs"]
        for directory in required_dirs:
            if not os.path.isdir(directory):
                logger.error(f"必須ディレクトリ {directory} が存在しません")
                return False
        
        # 3. データベースマイグレーションのチェック
        # 本番環境では、マイグレーションが最新でなくてもエラーにはしない
        # デプロイ時にマイグレーションが実行されるため
        try:
            from alembic.config import Config
            from alembic.script import ScriptDirectory
            from alembic.runtime.migration import MigrationContext
            from sqlalchemy import create_engine, text
            from src.config import config as app_config
            
            # データベースURLを取得
            db_url = app_config.DATABASE_URL
            
            # SQLiteの場合はsqlite:///からsqlite:////appに変換
            if db_url.startswith('sqlite:///'):
                db_url = db_url.replace('sqlite:///', 'sqlite:////app/')
            
            # 同期エンジンを作成
            engine = create_engine(db_url)
            
            # 現在のリビジョンを取得
            with engine.connect() as connection:
                context = MigrationContext.configure(connection)
                current_rev = context.get_current_revision()
            
            # 最新のリビジョンを取得
            alembic_cfg = Config("alembic.ini")
            alembic_cfg.set_main_option("sqlalchemy.url", db_url)
            script = ScriptDirectory.from_config(alembic_cfg)
            head_rev = script.get_current_head()
            
            # 最新でない場合は警告を出すが、エラーにはしない
            if current_rev != head_rev:
                logger.warning(f"データベースマイグレーションが最新ではありません: 現在={current_rev}, 最新={head_rev}")
                # 本番環境ではデプロイ時にマイグレーションが実行されるため、警告のみ
            else:
                logger.info("データベースマイグレーションは最新です")
                
        except Exception as e:
            logger.warning(f"データベースマイグレーションの確認中にエラーが発生しました: {e}")
            # マイグレーション確認に失敗しても、ヘルスチェック自体は失敗としない
        
        # すべてのチェックに合格
        logger.info("ヘルスチェック成功: ボットは正常に動作しています")
        return True
        
    except Exception as e:
        logger.error(f"ヘルスチェック中にエラーが発生しました: {e}")
        return False

if __name__ == "__main__":
    """
    コマンドラインから直接実行された場合、ヘルスチェックを実行し、
    結果に応じた終了コードを返します。
    
    終了コード:
    - 0: ヘルスチェック成功
    - 1: ヘルスチェック失敗
    """
    is_healthy = check_health()
    print("ヘルスチェック結果: " + ("成功" if is_healthy else "失敗"))
    sys.exit(0 if is_healthy else 1)