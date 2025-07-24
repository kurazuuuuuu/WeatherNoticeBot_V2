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