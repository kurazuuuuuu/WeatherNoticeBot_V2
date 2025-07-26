"""Database connection and session management for Discord Weather Bot."""

import asyncio
import logging
import time
import os
from contextlib import asynccontextmanager
from typing import AsyncGenerator, Optional, Dict, Any, List
from dataclasses import dataclass, field
from datetime import datetime, timedelta

from sqlalchemy import create_engine, event, text
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool
from sqlalchemy.exc import SQLAlchemyError, OperationalError, DisconnectionError

from src.config import config
from src.models.user import Base
# サーバー設定モデルをインポートしてテーブル作成に含める
from src.models.server_config import ServerConfig

logger = logging.getLogger(__name__)


class DatabaseError(Exception):
    """データベース関連のエラー"""
    pass


class DatabaseConnectionError(DatabaseError):
    """データベース接続エラー"""
    pass


class DatabaseTimeoutError(DatabaseError):
    """データベースタイムアウトエラー"""
    pass


@dataclass
class MemoryUserData:
    """一時的なメモリストレージ用のユーザーデータ"""
    discord_id: int
    area_code: Optional[str] = None
    area_name: Optional[str] = None
    notification_hour: Optional[int] = None
    timezone: str = 'Asia/Tokyo'
    is_notification_enabled: bool = False
    created_at: datetime = field(default_factory=datetime.now)
    updated_at: datetime = field(default_factory=datetime.now)
    
    def to_dict(self) -> Dict[str, Any]:
        """辞書形式に変換"""
        return {
            'discord_id': self.discord_id,
            'area_code': self.area_code,
            'area_name': self.area_name,
            'notification_hour': self.notification_hour,
            'timezone': self.timezone,
            'is_notification_enabled': self.is_notification_enabled,
            'created_at': self.created_at,
            'updated_at': self.updated_at
        }


class MemoryStorage:
    """一時的なメモリストレージ"""
    
    def __init__(self):
        self._users: Dict[int, MemoryUserData] = {}
        self._enabled = False
        self._last_sync_attempt = 0.0
        self._sync_interval = 300  # 5分間隔でDB同期を試行
        
    def enable(self):
        """メモリストレージを有効化"""
        self._enabled = True
        logger.warning("データベース接続に問題があるため、一時的なメモリストレージを有効化しました")
        
    def disable(self):
        """メモリストレージを無効化"""
        self._enabled = False
        logger.info("データベース接続が復旧したため、メモリストレージを無効化しました")
        
    def is_enabled(self) -> bool:
        """メモリストレージが有効かどうか"""
        return self._enabled
        
    def should_try_sync(self) -> bool:
        """DB同期を試行すべきかどうか"""
        current_time = time.time()
        return current_time - self._last_sync_attempt > self._sync_interval
        
    def mark_sync_attempt(self):
        """同期試行時刻を記録"""
        self._last_sync_attempt = time.time()
        
    def get_user(self, discord_id: int) -> Optional[MemoryUserData]:
        """ユーザーデータを取得"""
        return self._users.get(discord_id)
        
    def set_user(self, user_data: MemoryUserData):
        """ユーザーデータを保存"""
        user_data.updated_at = datetime.now()
        self._users[user_data.discord_id] = user_data
        logger.debug(f"メモリストレージにユーザーデータを保存: {user_data.discord_id}")
        
    def delete_user(self, discord_id: int) -> bool:
        """ユーザーデータを削除"""
        if discord_id in self._users:
            del self._users[discord_id]
            logger.debug(f"メモリストレージからユーザーデータを削除: {discord_id}")
            return True
        return False
        
    def get_all_users(self) -> List[MemoryUserData]:
        """全ユーザーデータを取得"""
        return list(self._users.values())
        
    def get_users_with_notifications(self, hour: Optional[int] = None) -> List[MemoryUserData]:
        """通知が有効なユーザーを取得"""
        users = []
        for user in self._users.values():
            if user.is_notification_enabled and user.notification_hour is not None:
                if hour is None or user.notification_hour == hour:
                    users.append(user)
        return users
        
    def get_user_count(self) -> int:
        """ユーザー数を取得"""
        return len(self._users)
        
    def clear(self):
        """全データをクリア"""
        self._users.clear()
        logger.info("メモリストレージをクリアしました")


class DatabaseManager:
    """Database connection and session manager."""
    
    def __init__(self, database_url: Optional[str] = None):
        """Initialize database manager with connection URL."""
        self.database_url = database_url or config.DATABASE_URL
        self.async_engine = None
        self.sync_engine = None
        self.async_session_factory = None
        self.sync_session_factory = None
        
        # エラーハンドリング関連
        self._connection_errors = 0
        self._max_connection_errors = 5
        self._last_error_time = 0.0
        self._reconnect_delay = 30.0  # 30秒後に再接続を試行
        self._is_healthy = True
        
        # 一時的なメモリストレージ
        self.memory_storage = MemoryStorage()
        
        # リトライ設定
        self._max_retries = 3
        self._retry_delay = 1.0
        self._backoff_factor = 2.0
        
    def _get_async_url(self, url: str) -> str:
        """Convert sync database URL to async URL."""
        if url.startswith('sqlite:'):
            return url.replace('sqlite:', 'sqlite+aiosqlite:')
        elif url.startswith('postgresql:'):
            return url.replace('postgresql:', 'postgresql+asyncpg:')
        return url
    
    def _get_sync_url(self, url: str) -> str:
        """Ensure sync database URL format."""
        if url.startswith('sqlite+aiosqlite:'):
            return url.replace('sqlite+aiosqlite:', 'sqlite:')
        elif url.startswith('postgresql+asyncpg:'):
            return url.replace('postgresql+asyncpg:', 'postgresql:')
        return url
    
    async def initialize(self) -> None:
        """Initialize database connections and session factories."""
        try:
            await self._initialize_with_retry()
            self._is_healthy = True
            self._connection_errors = 0
            
            # データベース接続が成功した場合、メモリストレージを無効化
            if self.memory_storage.is_enabled():
                await self._sync_memory_to_db()
                self.memory_storage.disable()
                
        except Exception as e:
            logger.error(f"データベースの初期化に失敗しました: {e}")
            self._handle_connection_error()
            raise DatabaseConnectionError(f"データベース初期化エラー: {e}")
    
    async def _initialize_with_retry(self, retries: int = 0) -> None:
        """リトライ機能付きでデータベースを初期化"""
        try:
            # Create async engine
            async_url = self._get_async_url(self.database_url)
            
            if async_url.startswith('sqlite'):
                # SQLite specific configuration
                self.async_engine = create_async_engine(
                    async_url,
                    echo=False,
                    poolclass=StaticPool,
                    connect_args={
                        "check_same_thread": False,
                        "timeout": 20
                    },
                    pool_pre_ping=True,
                    pool_recycle=3600  # 1時間でコネクションをリサイクル
                )
            elif async_url.startswith('postgresql'):
                # PostgreSQL configuration
                # 環境に応じた設定
                if config.ENVIRONMENT == 'production':
                    # 本番環境ではより多くのコネクションとタイムアウト設定
                    self.async_engine = create_async_engine(
                        async_url,
                        echo=False,
                        pool_size=20,
                        max_overflow=30,
                        pool_pre_ping=True,
                        pool_recycle=1800,  # 30分でコネクションをリサイクル
                        pool_timeout=30,    # 30秒のタイムアウト
                        connect_args={
                            "connect_timeout": 10,
                            "server_settings": {
                                "application_name": f"discord_weather_bot_{config.ENVIRONMENT}",
                                "statement_timeout": "30000",  # 30秒のステートメントタイムアウト
                                "idle_in_transaction_session_timeout": "60000",  # 60秒のアイドルタイムアウト
                            }
                        }
                    )
                else:
                    # 開発/ステージング環境
                    self.async_engine = create_async_engine(
                        async_url,
                        echo=False,
                        pool_size=10,
                        max_overflow=20,
                        pool_pre_ping=True,
                        pool_recycle=3600,
                        connect_args={
                            "connect_timeout": 10,
                            "server_settings": {
                                "application_name": f"discord_weather_bot_{config.ENVIRONMENT}",
                            }
                        }
                    )
            else:
                # その他のデータベース（未対応）
                raise ValueError(f"未対応のデータベースタイプ: {async_url}")
            
            # Create sync engine for migrations
            sync_url = self._get_sync_url(self.database_url)
            
            if sync_url.startswith('sqlite'):
                self.sync_engine = create_engine(
                    sync_url,
                    echo=False,
                    poolclass=StaticPool,
                    connect_args={"check_same_thread": False},
                    pool_pre_ping=True
                )
            elif sync_url.startswith('postgresql'):
                # 環境に応じた設定
                if config.ENVIRONMENT == 'production':
                    # 本番環境設定
                    self.sync_engine = create_engine(
                        sync_url,
                        echo=False,
                        pool_size=10,
                        max_overflow=20,
                        pool_pre_ping=True,
                        pool_recycle=1800,
                        pool_timeout=30,
                        connect_args={
                            "connect_timeout": 10,
                            "application_name": f"discord_weather_bot_{config.ENVIRONMENT}_sync",
                        }
                    )
                else:
                    # 開発/ステージング環境
                    self.sync_engine = create_engine(
                        sync_url,
                        echo=False,
                        pool_size=5,
                        max_overflow=10,
                        pool_pre_ping=True,
                        pool_recycle=3600,
                        connect_args={
                            "connect_timeout": 10,
                            "application_name": f"discord_weather_bot_{config.ENVIRONMENT}_sync",
                        }
                    )
            else:
                # その他のデータベース（未対応）
                raise ValueError(f"未対応のデータベースタイプ: {sync_url}")
            
            # Create session factories
            self.async_session_factory = async_sessionmaker(
                bind=self.async_engine,
                class_=AsyncSession,
                expire_on_commit=False
            )
            
            self.sync_session_factory = sessionmaker(
                bind=self.sync_engine,
                expire_on_commit=False
            )
            
            # 接続テスト
            await self._test_connection()
            
            logger.info(f"データベースが正常に初期化されました: {self._mask_url(self.database_url)}")
            
        except Exception as e:
            if retries < self._max_retries:
                delay = self._retry_delay * (self._backoff_factor ** retries)
                logger.warning(f"データベース初期化をリトライします ({retries + 1}/{self._max_retries}) - {delay}秒後")
                await asyncio.sleep(delay)
                await self._initialize_with_retry(retries + 1)
            else:
                raise
    
    async def _test_connection(self) -> None:
        """データベース接続をテスト"""
        try:
            async with self.async_engine.begin() as conn:
                await conn.execute(text("SELECT 1"))
        except Exception as e:
            raise DatabaseConnectionError(f"データベース接続テストに失敗: {e}")
    
    def _handle_connection_error(self) -> None:
        """接続エラーを処理"""
        self._connection_errors += 1
        self._last_error_time = time.time()
        self._is_healthy = False
        
        if self._connection_errors >= self._max_connection_errors:
            logger.error(f"データベース接続エラーが{self._max_connection_errors}回連続で発生しました。メモリストレージを有効化します。")
            self.memory_storage.enable()
        else:
            logger.warning(f"データベース接続エラー ({self._connection_errors}/{self._max_connection_errors})")
    
    async def _attempt_reconnection(self) -> bool:
        """データベース再接続を試行"""
        current_time = time.time()
        if current_time - self._last_error_time < self._reconnect_delay:
            return False
            
        try:
            logger.info("データベース再接続を試行しています...")
            await self._test_connection()
            
            # 再接続成功
            self._is_healthy = True
            self._connection_errors = 0
            logger.info("データベース再接続に成功しました")
            
            # メモリストレージからDBに同期
            if self.memory_storage.is_enabled():
                await self._sync_memory_to_db()
                self.memory_storage.disable()
            
            return True
            
        except Exception as e:
            logger.warning(f"データベース再接続に失敗しました: {e}")
            self._last_error_time = current_time
            return False
    
    async def _sync_memory_to_db(self) -> None:
        """メモリストレージのデータをデータベースに同期"""
        if not self.memory_storage.is_enabled():
            return
            
        try:
            memory_users = self.memory_storage.get_all_users()
            if not memory_users:
                return
                
            logger.info(f"メモリストレージから{len(memory_users)}件のユーザーデータをデータベースに同期します")
            
            async with self.get_async_session() as session:
                from src.models.user import User
                
                for memory_user in memory_users:
                    try:
                        # 既存ユーザーをチェック
                        stmt = text("SELECT id FROM users WHERE discord_id = :discord_id")
                        result = await session.execute(stmt, {"discord_id": memory_user.discord_id})
                        existing_user = result.fetchone()
                        
                        if existing_user:
                            # 既存ユーザーを更新
                            update_stmt = text("""
                                UPDATE users SET 
                                    area_code = :area_code,
                                    area_name = :area_name,
                                    notification_hour = :notification_hour,
                                    timezone = :timezone,
                                    is_notification_enabled = :is_notification_enabled,
                                    updated_at = :updated_at
                                WHERE discord_id = :discord_id
                            """)
                            await session.execute(update_stmt, {
                                "area_code": memory_user.area_code,
                                "area_name": memory_user.area_name,
                                "notification_hour": memory_user.notification_hour,
                                "timezone": memory_user.timezone,
                                "is_notification_enabled": memory_user.is_notification_enabled,
                                "updated_at": memory_user.updated_at,
                                "discord_id": memory_user.discord_id
                            })
                        else:
                            # 新しいユーザーを作成
                            insert_stmt = text("""
                                INSERT INTO users (discord_id, area_code, area_name, notification_hour, 
                                                 timezone, is_notification_enabled, created_at, updated_at)
                                VALUES (:discord_id, :area_code, :area_name, :notification_hour,
                                       :timezone, :is_notification_enabled, :created_at, :updated_at)
                            """)
                            await session.execute(insert_stmt, {
                                "discord_id": memory_user.discord_id,
                                "area_code": memory_user.area_code,
                                "area_name": memory_user.area_name,
                                "notification_hour": memory_user.notification_hour,
                                "timezone": memory_user.timezone,
                                "is_notification_enabled": memory_user.is_notification_enabled,
                                "created_at": memory_user.created_at,
                                "updated_at": memory_user.updated_at
                            })
                            
                    except Exception as e:
                        logger.error(f"ユーザーデータの同期に失敗: {memory_user.discord_id} - {e}")
                        continue
                
                await session.commit()
                logger.info("メモリストレージからデータベースへの同期が完了しました")
                
                # 同期完了後、メモリストレージをクリア
                self.memory_storage.clear()
                
        except Exception as e:
            logger.error(f"メモリストレージ同期中にエラーが発生しました: {e}")
    
    async def create_tables(self) -> None:
        """Create all database tables if they don't exist."""
        try:
            async with self.async_engine.begin() as conn:
                # テーブルが存在するかチェック
                result = await conn.execute(text("""
                    SELECT name FROM sqlite_master 
                    WHERE type='table' AND name='users'
                """))
                existing_tables = result.fetchall()
                
                if not existing_tables:
                    # テーブルが存在しない場合のみ作成
                    await conn.run_sync(Base.metadata.create_all)
                    logger.info("Database tables created successfully")
                else:
                    logger.info("Database tables already exist, skipping creation")
                    
        except Exception as e:
            logger.error(f"Failed to create database tables: {e}")
            raise
    
    async def drop_tables(self) -> None:
        """Drop all database tables."""
        try:
            async with self.async_engine.begin() as conn:
                await conn.run_sync(Base.metadata.drop_all)
            logger.info("Database tables dropped successfully")
        except Exception as e:
            logger.error(f"Failed to drop database tables: {e}")
            raise
    
    @asynccontextmanager
    async def get_async_session(self) -> AsyncGenerator[AsyncSession, None]:
        """Get async database session context manager."""
        if not self.async_session_factory:
            raise RuntimeError("Database not initialized. Call initialize() first.")
        
        # データベースが不健全で、メモリストレージが有効な場合は例外を発生
        if not self._is_healthy and self.memory_storage.is_enabled():
            # 定期的に再接続を試行
            if self.memory_storage.should_try_sync():
                self.memory_storage.mark_sync_attempt()
                if await self._attempt_reconnection():
                    # 再接続成功、通常のセッションを返す
                    pass
                else:
                    raise DatabaseConnectionError("データベースが利用できません。メモリストレージを使用してください。")
            else:
                raise DatabaseConnectionError("データベースが利用できません。メモリストレージを使用してください。")
        
        retries = 0
        while retries <= self._max_retries:
            try:
                async with self.async_session_factory() as session:
                    try:
                        yield session
                        await session.commit()
                        
                        # 成功時はエラーカウントをリセット
                        if self._connection_errors > 0:
                            self._connection_errors = 0
                            self._is_healthy = True
                            logger.info("データベース接続が復旧しました")
                        
                        return
                        
                    except Exception as e:
                        await session.rollback()
                        raise
                    finally:
                        await session.close()
                        
            except (OperationalError, DisconnectionError, DatabaseConnectionError) as e:
                logger.warning(f"データベースセッションエラー (試行 {retries + 1}/{self._max_retries + 1}): {e}")
                
                if retries < self._max_retries:
                    retries += 1
                    delay = self._retry_delay * (self._backoff_factor ** (retries - 1))
                    await asyncio.sleep(delay)
                    continue
                else:
                    # 最大リトライ回数に達した場合
                    self._handle_connection_error()
                    raise DatabaseConnectionError(f"データベース接続に失敗しました: {e}")
                    
            except Exception as e:
                # その他の予期しないエラー
                logger.error(f"データベースセッションで予期しないエラー: {e}")
                raise
    
    def get_sync_session(self) -> Session:
        """Get sync database session for migrations."""
        if not self.sync_session_factory:
            raise RuntimeError("Database not initialized. Call initialize() first.")
        
        return self.sync_session_factory()
    
    async def close(self) -> None:
        """Close database connections."""
        if self.async_engine:
            await self.async_engine.dispose()
            logger.info("Async database engine disposed")
        
        if self.sync_engine:
            self.sync_engine.dispose()
            logger.info("Sync database engine disposed")
    
    def _mask_url(self, url: str) -> str:
        """Mask sensitive information in database URL for logging."""
        if '@' in url:
            # Mask password in URL
            parts = url.split('@')
            if len(parts) == 2:
                auth_part = parts[0]
                if ':' in auth_part:
                    protocol_user = auth_part.rsplit(':', 1)[0]
                    return f"{protocol_user}:***@{parts[1]}"
        return url
    
    async def health_check(self) -> Dict[str, Any]:
        """Check database connection health."""
        try:
            start_time = time.time()
            
            async with self.get_async_session() as session:
                await session.execute(text("SELECT 1"))
                
            response_time = time.time() - start_time
            
            return {
                "status": "healthy",
                "response_time_seconds": round(response_time, 3),
                "connection_errors": self._connection_errors,
                "memory_storage_enabled": self.memory_storage.is_enabled(),
                "memory_storage_user_count": self.memory_storage.get_user_count() if self.memory_storage.is_enabled() else 0
            }
            
        except DatabaseConnectionError:
            return {
                "status": "connection_error",
                "connection_errors": self._connection_errors,
                "memory_storage_enabled": self.memory_storage.is_enabled(),
                "memory_storage_user_count": self.memory_storage.get_user_count() if self.memory_storage.is_enabled() else 0,
                "last_error_time": self._last_error_time
            }
            
        except Exception as e:
            logger.error(f"Database health check failed: {e}")
            return {
                "status": "error",
                "error": str(e),
                "connection_errors": self._connection_errors,
                "memory_storage_enabled": self.memory_storage.is_enabled(),
                "memory_storage_user_count": self.memory_storage.get_user_count() if self.memory_storage.is_enabled() else 0
            }
    
    def get_stats(self) -> Dict[str, Any]:
        """データベース統計情報を取得"""
        return {
            "is_healthy": self._is_healthy,
            "connection_errors": self._connection_errors,
            "last_error_time": self._last_error_time,
            "memory_storage_enabled": self.memory_storage.is_enabled(),
            "memory_storage_user_count": self.memory_storage.get_user_count(),
            "database_url_masked": self._mask_url(self.database_url)
        }


# Global database manager instance
db_manager = DatabaseManager()


# Convenience functions for getting sessions
@asynccontextmanager
async def get_db_session() -> AsyncGenerator[AsyncSession, None]:
    """Get database session context manager."""
    async with db_manager.get_async_session() as session:
        yield session


async def init_database() -> None:
    """Initialize database connection and create tables."""
    await db_manager.initialize()
    await db_manager.create_tables()


async def close_database() -> None:
    """Close database connections."""
    await db_manager.close()