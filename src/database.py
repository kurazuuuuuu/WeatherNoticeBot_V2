"""Database connection and session management for Discord Weather Bot."""

import logging
from contextlib import asynccontextmanager
from typing import AsyncGenerator, Optional

from sqlalchemy import create_engine, event
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

from src.config import config
from src.models.user import Base

logger = logging.getLogger(__name__)


class DatabaseManager:
    """Database connection and session manager."""
    
    def __init__(self, database_url: Optional[str] = None):
        """Initialize database manager with connection URL."""
        self.database_url = database_url or config.DATABASE_URL
        self.async_engine = None
        self.sync_engine = None
        self.async_session_factory = None
        self.sync_session_factory = None
        
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
                    }
                )
            else:
                # PostgreSQL configuration
                self.async_engine = create_async_engine(
                    async_url,
                    echo=False,
                    pool_size=10,
                    max_overflow=20,
                    pool_pre_ping=True
                )
            
            # Create sync engine for migrations
            sync_url = self._get_sync_url(self.database_url)
            
            if sync_url.startswith('sqlite'):
                self.sync_engine = create_engine(
                    sync_url,
                    echo=False,
                    poolclass=StaticPool,
                    connect_args={"check_same_thread": False}
                )
            else:
                self.sync_engine = create_engine(
                    sync_url,
                    echo=False,
                    pool_size=10,
                    max_overflow=20,
                    pool_pre_ping=True
                )
            
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
            
            logger.info(f"Database initialized with URL: {self._mask_url(self.database_url)}")
            
        except Exception as e:
            logger.error(f"Failed to initialize database: {e}")
            raise
    
    async def create_tables(self) -> None:
        """Create all database tables."""
        try:
            async with self.async_engine.begin() as conn:
                await conn.run_sync(Base.metadata.create_all)
            logger.info("Database tables created successfully")
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
        
        async with self.async_session_factory() as session:
            try:
                yield session
                await session.commit()
            except Exception:
                await session.rollback()
                raise
            finally:
                await session.close()
    
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
    
    async def health_check(self) -> bool:
        """Check database connection health."""
        try:
            from sqlalchemy import text
            async with self.get_async_session() as session:
                await session.execute(text("SELECT 1"))
            return True
        except Exception as e:
            logger.error(f"Database health check failed: {e}")
            return False


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