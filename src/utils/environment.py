"""環境設定ユーティリティ"""

import os
import sys
import platform
import psutil
from typing import Dict, Any
from src.config import config


def get_environment_info() -> Dict[str, Any]:
    """環境情報を取得"""
    return {
        "environment": config.ENVIRONMENT,
        "python_version": f"{sys.version_info.major}.{sys.version_info.minor}.{sys.version_info.micro}",
        "platform": platform.platform(),
        "processor": platform.processor(),
        "cpu_count": psutil.cpu_count(logical=True),
        "memory_total_gb": round(psutil.virtual_memory().total / (1024 ** 3), 2),
        "timezone": config.DEFAULT_TIMEZONE
    }


def get_database_info() -> Dict[str, Any]:
    """データベース情報を取得"""
    return config.get_database_info()


def is_production() -> bool:
    """本番環境かどうかを判定"""
    return config.ENVIRONMENT == 'production'


def is_development() -> bool:
    """開発環境かどうかを判定"""
    return config.ENVIRONMENT == 'development'


def is_staging() -> bool:
    """ステージング環境かどうかを判定"""
    return config.ENVIRONMENT == 'staging'


def is_docker() -> bool:
    """Dockerコンテナ内で実行されているかどうかを判定"""
    # Dockerコンテナ内で実行されているかどうかを確認する方法
    return os.path.exists('/.dockerenv') or os.path.isfile('/proc/self/cgroup') and any('docker' in line for line in open('/proc/self/cgroup'))


def get_log_directory() -> str:
    """ログディレクトリのパスを取得"""
    log_dir = os.path.dirname(config.LOG_FILE)
    if not log_dir:
        log_dir = 'logs'
    return log_dir