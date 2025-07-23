"""サーバー設定モデル"""

from sqlalchemy import Column, BigInteger, Boolean, String, DateTime, Integer
from sqlalchemy.sql import func
from src.database import Base


class ServerConfig(Base):
    """サーバー設定テーブル"""
    __tablename__ = 'server_configs'
    
    id = Column(Integer, primary_key=True)
    guild_id = Column(BigInteger, unique=True, nullable=False, index=True)
    default_area_code = Column(String(10))  # サーバーのデフォルト地域コード
    default_area_name = Column(String(100))  # サーバーのデフォルト地域名
    admin_channel_id = Column(BigInteger)  # 管理者通知チャンネル
    is_weather_enabled = Column(Boolean, default=True)  # 天気機能の有効/無効
    is_ai_enabled = Column(Boolean, default=True)  # AI機能の有効/無効
    max_forecast_days = Column(Integer, default=7)  # 最大予報日数
    timezone = Column(String(50), default='Asia/Tokyo')  # タイムゾーン
    created_at = Column(DateTime, server_default=func.now())
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now())
    
    def __repr__(self):
        return f"<ServerConfig(guild_id={self.guild_id}, area={self.default_area_name})>"