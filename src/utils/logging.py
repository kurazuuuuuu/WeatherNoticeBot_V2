"""Logging configuration for Discord Weather Bot."""

import logging
import logging.handlers
import sys
import os
import json
from datetime import datetime
from pathlib import Path
from src.config import config


class JSONFormatter(logging.Formatter):
    """JSON形式のログフォーマッター"""
    
    def format(self, record):
        """ログレコードをJSON形式に変換"""
        log_data = {
            'timestamp': datetime.fromtimestamp(record.created).isoformat(),
            'level': record.levelname,
            'message': record.getMessage(),
            'logger': record.name,
            'module': record.module,
            'function': record.funcName,
            'line': record.lineno,
        }
        
        # 例外情報があれば追加
        if record.exc_info:
            log_data['exception'] = {
                'type': record.exc_info[0].__name__,
                'message': str(record.exc_info[1]),
            }
        
        # 追加のコンテキスト情報があれば追加
        if hasattr(record, 'context') and record.context:
            log_data['context'] = record.context
        
        return json.dumps(log_data)


def setup_logging() -> logging.Logger:
    """Set up logging configuration for the bot."""
    
    # Create logs directory if it doesn't exist
    log_dir = Path("logs")
    log_dir.mkdir(exist_ok=True)
    
    # Create logger
    logger = logging.getLogger("weather_bot")
    logger.setLevel(getattr(logging, config.LOG_LEVEL.upper()))
    
    # Clear existing handlers
    logger.handlers.clear()
    
    # 環境に応じたフォーマッターを選択
    if config.ENVIRONMENT == 'production':
        # 本番環境ではJSON形式
        detailed_formatter = JSONFormatter()
        simple_formatter = logging.Formatter(
            '%(asctime)s - %(levelname)s - %(message)s'
        )
    else:
        # 開発環境では読みやすいテキスト形式
        detailed_formatter = logging.Formatter(
            '%(asctime)s - %(name)s - %(levelname)s - %(filename)s:%(lineno)d - %(message)s'
        )
        simple_formatter = logging.Formatter(
            '%(asctime)s - %(levelname)s - %(message)s'
        )
    
    # Console handler
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setLevel(logging.INFO)
    console_handler.setFormatter(simple_formatter)
    logger.addHandler(console_handler)
    
    # File handler with rotation
    log_file_path = Path(config.LOG_FILE)
    if log_file_path.is_absolute():
        file_path = log_file_path
    else:
        # LOG_FILEが相対パスの場合、ディレクトリを作成
        file_path = log_file_path
        file_path.parent.mkdir(exist_ok=True)
    
    file_handler = logging.handlers.RotatingFileHandler(
        file_path,
        maxBytes=10 * 1024 * 1024,  # 10MB
        backupCount=5
    )
    file_handler.setLevel(logging.DEBUG)
    file_handler.setFormatter(detailed_formatter)
    logger.addHandler(file_handler)
    
    # Error file handler
    error_handler = logging.handlers.RotatingFileHandler(
        log_dir / "error.log",
        maxBytes=10 * 1024 * 1024,  # 10MB
        backupCount=5
    )
    error_handler.setLevel(logging.ERROR)
    error_handler.setFormatter(detailed_formatter)
    logger.addHandler(error_handler)
    
    # 環境別のログ設定
    if config.ENVIRONMENT == 'production':
        # 本番環境では追加のログハンドラーを設定
        
        # 重大エラー専用のログファイル
        critical_handler = logging.handlers.RotatingFileHandler(
            log_dir / "critical.log",
            maxBytes=5 * 1024 * 1024,  # 5MB
            backupCount=10
        )
        critical_handler.setLevel(logging.CRITICAL)
        critical_handler.setFormatter(detailed_formatter)
        logger.addHandler(critical_handler)
        
        # 日付ごとのログファイル
        daily_handler = logging.handlers.TimedRotatingFileHandler(
            log_dir / "daily.log",
            when='midnight',
            backupCount=30
        )
        daily_handler.setLevel(logging.INFO)
        daily_handler.setFormatter(detailed_formatter)
        logger.addHandler(daily_handler)
    
    # 環境情報をログに記録
    logger.info(f"ログシステムを初期化しました - 環境: {config.ENVIRONMENT}, レベル: {config.LOG_LEVEL}")
    
    return logger


class ContextLogger:
    """コンテキスト情報付きのロガー"""
    
    def __init__(self, logger, context=None):
        self.logger = logger
        self.context = context or {}
    
    def _log_with_context(self, level, msg, *args, **kwargs):
        """コンテキスト情報を付加してログを記録"""
        if kwargs.get('extra') is None:
            kwargs['extra'] = {}
        kwargs['extra']['context'] = self.context
        getattr(self.logger, level)(msg, *args, **kwargs)
    
    def debug(self, msg, *args, **kwargs):
        self._log_with_context('debug', msg, *args, **kwargs)
    
    def info(self, msg, *args, **kwargs):
        self._log_with_context('info', msg, *args, **kwargs)
    
    def warning(self, msg, *args, **kwargs):
        self._log_with_context('warning', msg, *args, **kwargs)
    
    def error(self, msg, *args, **kwargs):
        self._log_with_context('error', msg, *args, **kwargs)
    
    def critical(self, msg, *args, **kwargs):
        self._log_with_context('critical', msg, *args, **kwargs)
    
    def with_context(self, **context):
        """新しいコンテキスト情報を追加したロガーを返す"""
        new_context = {**self.context, **context}
        return ContextLogger(self.logger, new_context)


# Global logger instance
base_logger = setup_logging()
logger = ContextLogger(base_logger)