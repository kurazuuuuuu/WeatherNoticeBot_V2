"""サーバー設定管理サービス"""

from typing import Optional, Dict, Any
from sqlalchemy.orm import Session
from sqlalchemy.exc import SQLAlchemyError
from src.database import get_db_session
from src.models.server_config import ServerConfig
from src.utils.logging import logger


class ServerConfigService:
    """サーバー設定を管理するサービス"""
    
    @staticmethod
    async def get_server_config(guild_id: int) -> Optional[ServerConfig]:
        """サーバー設定を取得"""
        try:
            async with get_db_session() as session:
                from sqlalchemy import select
                stmt = select(ServerConfig).where(ServerConfig.guild_id == guild_id)
                result = await session.execute(stmt)
                config = result.scalar_one_or_none()
                return config
        except SQLAlchemyError as e:
            logger.error(f"サーバー設定取得エラー (guild_id: {guild_id}): {e}")
            return None
    
    @staticmethod
    async def create_or_update_server_config(guild_id: int, **kwargs) -> Optional[ServerConfig]:
        """サーバー設定を作成または更新"""
        try:
            async with get_db_session() as session:
                from sqlalchemy import select
                stmt = select(ServerConfig).where(ServerConfig.guild_id == guild_id)
                result = await session.execute(stmt)
                config = result.scalar_one_or_none()
                
                if config:
                    # 既存設定を更新
                    for key, value in kwargs.items():
                        if hasattr(config, key):
                            setattr(config, key, value)
                else:
                    # 新規設定を作成
                    config = ServerConfig(guild_id=guild_id, **kwargs)
                    session.add(config)
                
                await session.commit()
                await session.refresh(config)
                logger.info(f"サーバー設定を更新しました (guild_id: {guild_id})")
                return config
                
        except SQLAlchemyError as e:
            logger.error(f"サーバー設定更新エラー (guild_id: {guild_id}): {e}")
            return None
    
    @staticmethod
    async def get_server_stats() -> Dict[str, Any]:
        """全サーバーの統計情報を取得"""
        try:
            async with get_db_session() as session:
                from sqlalchemy import select, func
                
                # 総サーバー数
                total_stmt = select(func.count(ServerConfig.id))
                total_result = await session.execute(total_stmt)
                total_servers = total_result.scalar()
                
                # 有効サーバー数
                enabled_stmt = select(func.count(ServerConfig.id)).where(
                    ServerConfig.is_weather_enabled == True
                )
                enabled_result = await session.execute(enabled_stmt)
                enabled_servers = enabled_result.scalar()
                
                # AI有効サーバー数
                ai_stmt = select(func.count(ServerConfig.id)).where(
                    ServerConfig.is_ai_enabled == True
                )
                ai_result = await session.execute(ai_stmt)
                ai_enabled_servers = ai_result.scalar()
                
                return {
                    'total_servers': total_servers,
                    'enabled_servers': enabled_servers,
                    'ai_enabled_servers': ai_enabled_servers,
                    'disabled_servers': total_servers - enabled_servers
                }
        except SQLAlchemyError as e:
            logger.error(f"サーバー統計取得エラー: {e}")
            return {
                'total_servers': 0,
                'enabled_servers': 0,
                'ai_enabled_servers': 0,
                'disabled_servers': 0
            }
    
    @staticmethod
    async def delete_server_config(guild_id: int) -> bool:
        """サーバー設定を削除"""
        try:
            async with get_db_session() as session:
                from sqlalchemy import select, delete
                stmt = select(ServerConfig).where(ServerConfig.guild_id == guild_id)
                result = await session.execute(stmt)
                config = result.scalar_one_or_none()
                
                if config:
                    delete_stmt = delete(ServerConfig).where(ServerConfig.guild_id == guild_id)
                    await session.execute(delete_stmt)
                    await session.commit()
                    logger.info(f"サーバー設定を削除しました (guild_id: {guild_id})")
                    return True
                return False
                
        except SQLAlchemyError as e:
            logger.error(f"サーバー設定削除エラー (guild_id: {guild_id}): {e}")
            return False