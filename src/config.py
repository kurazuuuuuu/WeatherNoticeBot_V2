"""Configuration management for Discord Weather Bot."""

import os
from typing import Optional
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()


class Config:
    """Configuration class for the Discord Weather Bot."""
    
    # Discord Bot Configuration
    DISCORD_TOKEN: str = os.getenv('DISCORD_TOKEN', '')
    DISCORD_GUILD_ID: Optional[str] = os.getenv('DISCORD_GUILD_ID')
    
    # Database Configuration
    DATABASE_URL: str = os.getenv('DATABASE_URL', 'sqlite:///weather_bot.db')
    
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
    LOG_FILE: str = os.getenv('LOG_FILE', 'weather_bot.log')
    
    @classmethod
    def validate(cls) -> bool:
        """Validate required configuration values."""
        required_vars = ['DISCORD_TOKEN']
        missing_vars = []
        
        for var in required_vars:
            if not getattr(cls, var):
                missing_vars.append(var)
        
        if missing_vars:
            raise ValueError(f"Missing required environment variables: {', '.join(missing_vars)}")
        
        return True


# Global config instance
config = Config()