"""Configuration management for Discord Weather Bot."""

import os
import sys
import logging
from typing import Optional, Dict, Any
from pathlib import Path
from dotenv import load_dotenv

# 環境変数ファイルの読み込み
# 環境に応じた.envファイルを読み込む
env_files = ['.env', '.env.local']
for env_file in env_files:
    if os.path.exists(env_file):
        load_dotenv(env_file)
        break


class Config:
    """Configuration class for the Discord Weather Bot."""
    
    # 環境設定
    ENVIRONMENT: str = os.getenv('ENVIRONMENT', 'development')
    
    # Discord Bot Configuration
    DISCORD_TOKEN: str = os.getenv('DISCORD_TOKEN', '')
    DISCORD_GUILD_ID: Optional[str] = os.getenv('DISCORD_GUILD_ID')
    
    # Database Configuration
    DATABASE_URL: str = os.getenv('DATABASE_URL', 'sqlite:///weather_bot.db')
    USE_POSTGRES: bool = os.getenv('USE_POSTGRES', 'false').lower() == 'true'
    
    # JMA API Configuration
    JMA_BASE_URL: str = 'https://www.jma.go.jp/bosai'
    
    # Google Gemini API Configuration
    GEMINI_API_KEY: str = os.getenv('GEMINI_API_KEY', '')
    
    # Bot Configuration
    COMMAND_PREFIX: str = os.getenv('COMMAND_PREFIX', '/')
    DEFAULT_TIMEZONE: str = os.getenv('DEFAULT_TIMEZONE', 'Asia/Tokyo')
    
    # Notification Configuration
    NOTIFICATION_RETRY_ATTEMPTS: int = int(os.getenv('NOTIFICATION_RETRY_ATTEMPTS', '3'))
    NOTIFICATION_RETRY_DELAY: int = int(os.getenv('NOTIFICATION_RETRY_DELAY', '300'))  # 5 minutes
    
    # API Rate Limiting
    JMA_API_RATE_LIMIT: int = int(os.getenv('JMA_API_RATE_LIMIT', '60'))  # requests per minute
    GEMINI_API_RATE_LIMIT: int = int(os.getenv('GEMINI_API_RATE_LIMIT', '60'))  # requests per minute
    
    # Logging Configuration
    LOG_LEVEL: str = os.getenv('LOG_LEVEL', 'INFO')
    LOG_FILE: str = os.getenv('LOG_FILE', 'logs/weather_bot.log')
    
    # 環境別設定
    def __init__(self):
        """環境に応じた設定を初期化"""
        self._apply_environment_settings()
    
    def _apply_environment_settings(self):
        """環境に応じた設定を適用"""
        if self.ENVIRONMENT == 'development':
            # 開発環境設定
            if not self.LOG_LEVEL:
                self.LOG_LEVEL = 'DEBUG'
            if not self.DATABASE_URL:
                self.DATABASE_URL = 'sqlite:///data/weather_bot_dev.db'
                
        elif self.ENVIRONMENT == 'staging':
            # ステージング環境設定
            if not self.LOG_LEVEL:
                self.LOG_LEVEL = 'INFO'
            # PostgreSQLの使用を推奨
            if self.USE_POSTGRES and 'sqlite' in self.DATABASE_URL:
                self.DATABASE_URL = 'postgresql://weather_user:weather_password@db:5432/weather_bot_staging'
                
        elif self.ENVIRONMENT == 'production':
            # 本番環境設定
            if not self.LOG_LEVEL:
                self.LOG_LEVEL = 'WARNING'
            # PostgreSQLの使用を推奨
            if self.USE_POSTGRES and 'sqlite' in self.DATABASE_URL:
                self.DATABASE_URL = 'postgresql://weather_user:weather_password@db:5432/weather_bot'
        
        # ログファイルパスの調整
        if self.LOG_FILE and not os.path.isabs(self.LOG_FILE):
            log_dir = Path('logs')
            log_dir.mkdir(exist_ok=True)
            self.LOG_FILE = str(log_dir / self.LOG_FILE)
    
    @classmethod
    def validate(cls) -> bool:
        """Validate required configuration values."""
        config_instance = cls()
        required_vars = ['DISCORD_TOKEN']
        missing_vars = []
        
        for var in required_vars:
            if not getattr(config_instance, var):
                missing_vars.append(var)
        
        if missing_vars:
            raise ValueError(f"Missing required environment variables: {', '.join(missing_vars)}")
        
        return True
    
    def get_database_info(self) -> Dict[str, Any]:
        """データベース設定情報を取得"""
        db_type = "SQLite"
        db_name = "weather_bot.db"
        
        if "postgresql" in self.DATABASE_URL:
            db_type = "PostgreSQL"
            # URLからデータベース名を抽出
            db_name = self.DATABASE_URL.split("/")[-1]
        elif "sqlite" in self.DATABASE_URL:
            # URLからファイル名を抽出
            db_path = self.DATABASE_URL.replace("sqlite:///", "")
            db_name = os.path.basename(db_path)
        
        return {
            "type": db_type,
            "name": db_name,
            "url_masked": self._mask_db_url(self.DATABASE_URL),
            "use_postgres": self.USE_POSTGRES
        }
    
    def _mask_db_url(self, url: str) -> str:
        """データベースURLの機密情報をマスク"""
        if "postgresql" in url and "@" in url:
            # PostgreSQL URLの場合、パスワードをマスク
            parts = url.split("@")
            if len(parts) == 2:
                auth_part = parts[0]
                if ":" in auth_part:
                    protocol_user = auth_part.rsplit(":", 1)[0]
                    return f"{protocol_user}:***@{parts[1]}"
        return url
    
    def get_environment_info(self) -> Dict[str, Any]:
        """環境情報を取得"""
        return {
            "environment": self.ENVIRONMENT,
            "python_version": f"{sys.version_info.major}.{sys.version_info.minor}.{sys.version_info.micro}",
            "log_level": self.LOG_LEVEL,
            "log_file": self.LOG_FILE,
            "timezone": self.DEFAULT_TIMEZONE
        }


# Global config instance
config = Config()