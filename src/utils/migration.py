"""Database migration utilities for Discord Weather Bot."""

import logging
import subprocess
import sys
import os
from pathlib import Path
from typing import List, Optional, Dict, Any

from alembic import command
from alembic.config import Config
from alembic.runtime.migration import MigrationContext
from alembic.script import ScriptDirectory
from sqlalchemy import text

from src.database import db_manager
from src.config import config
from src.utils.environment import is_production, is_docker

logger = logging.getLogger(__name__)


class MigrationManager:
    """Manager for database migrations using Alembic."""
    
    def __init__(self, alembic_cfg_path: Optional[str] = None):
        """Initialize migration manager."""
        self.alembic_cfg_path = alembic_cfg_path or "alembic.ini"
        self.alembic_cfg = Config(self.alembic_cfg_path)
        
        # 環境に応じた設定を適用
        self._apply_environment_settings()
    
    def _apply_environment_settings(self):
        """環境に応じた設定を適用"""
        # データベースURLを設定
        self.alembic_cfg.set_main_option("sqlalchemy.url", config.DATABASE_URL)
        
        # 環境別の設定
        if is_production():
            # 本番環境では自動マイグレーションを無効化
            self.auto_migrate = False
            # 本番環境ではダウングレードを制限
            self.allow_downgrade = False
        else:
            # 開発/ステージング環境では自動マイグレーションを有効化
            self.auto_migrate = True
            # 開発/ステージング環境ではダウングレードを許可
            self.allow_downgrade = True
        
        # Docker環境での設定
        if is_docker():
            # Dockerコンテナ内ではスクリプトディレクトリのパスを調整
            script_location = os.path.join(os.getcwd(), "alembic")
            self.alembic_cfg.set_main_option("script_location", script_location)
        
    def get_current_revision(self) -> Optional[str]:
        """Get current database revision."""
        try:
            with db_manager.sync_engine.connect() as connection:
                context = MigrationContext.configure(connection)
                return context.get_current_revision()
        except Exception as e:
            logger.error(f"Failed to get current revision: {e}")
            return None
    
    def get_head_revision(self) -> Optional[str]:
        """Get head revision from migration scripts."""
        try:
            script = ScriptDirectory.from_config(self.alembic_cfg)
            return script.get_current_head()
        except Exception as e:
            logger.error(f"Failed to get head revision: {e}")
            return None
    
    def is_database_up_to_date(self) -> bool:
        """Check if database is up to date with migrations."""
        current = self.get_current_revision()
        head = self.get_head_revision()
        return current == head and current is not None
    
    def get_pending_migrations(self) -> List[str]:
        """Get list of pending migration revisions."""
        try:
            script = ScriptDirectory.from_config(self.alembic_cfg)
            with db_manager.sync_engine.connect() as connection:
                context = MigrationContext.configure(connection)
                current_rev = context.get_current_revision()
                
                if current_rev is None:
                    # No migrations applied yet, return all revisions
                    return [rev.revision for rev in script.walk_revisions()]
                
                # Get revisions between current and head
                pending = []
                for rev in script.walk_revisions(current_rev, "head"):
                    if rev.revision != current_rev:
                        pending.append(rev.revision)
                
                return pending
        except Exception as e:
            logger.error(f"Failed to get pending migrations: {e}")
            return []
    
    def upgrade_database(self, revision: str = "head") -> bool:
        """Upgrade database to specified revision."""
        try:
            command.upgrade(self.alembic_cfg, revision)
            logger.info(f"Database upgraded to revision: {revision}")
            return True
        except Exception as e:
            logger.error(f"Failed to upgrade database: {e}")
            return False
    
    def downgrade_database(self, revision: str) -> bool:
        """Downgrade database to specified revision."""
        # 本番環境でダウングレードが許可されていない場合は拒否
        if is_production() and not self.allow_downgrade:
            logger.error("本番環境ではデータベースのダウングレードは許可されていません")
            return False
            
        try:
            command.downgrade(self.alembic_cfg, revision)
            logger.info(f"Database downgraded to revision: {revision}")
            return True
        except Exception as e:
            logger.error(f"Failed to downgrade database: {e}")
            return False
    
    def create_migration(self, message: str, autogenerate: bool = True) -> bool:
        """Create a new migration."""
        try:
            if autogenerate:
                command.revision(self.alembic_cfg, message=message, autogenerate=True)
            else:
                command.revision(self.alembic_cfg, message=message)
            logger.info(f"Migration created: {message}")
            return True
        except Exception as e:
            logger.error(f"Failed to create migration: {e}")
            return False
    
    def get_migration_history(self) -> List[dict]:
        """Get migration history."""
        try:
            script = ScriptDirectory.from_config(self.alembic_cfg)
            history = []
            
            for rev in script.walk_revisions():
                history.append({
                    'revision': rev.revision,
                    'down_revision': rev.down_revision,
                    'message': rev.doc,
                    'create_date': getattr(rev.module, 'create_date', None)
                })
            
            return history
        except Exception as e:
            logger.error(f"Failed to get migration history: {e}")
            return []
    
    async def check_database_health(self) -> dict:
        """Check database health and migration status."""
        health_info = {
            'database_connected': False,
            'current_revision': None,
            'head_revision': None,
            'is_up_to_date': False,
            'pending_migrations': [],
            'migration_history': []
        }
        
        try:
            # Check database connection
            health_info['database_connected'] = await db_manager.health_check()
            
            if health_info['database_connected']:
                # Get migration information
                health_info['current_revision'] = self.get_current_revision()
                health_info['head_revision'] = self.get_head_revision()
                health_info['is_up_to_date'] = self.is_database_up_to_date()
                health_info['pending_migrations'] = self.get_pending_migrations()
                health_info['migration_history'] = self.get_migration_history()
        
        except Exception as e:
            logger.error(f"Database health check failed: {e}")
        
        return health_info
    
    def reset_database(self) -> bool:
        """Reset database by dropping all tables and running migrations."""
        try:
            # Drop all tables
            with db_manager.sync_engine.connect() as connection:
                # Drop alembic version table
                connection.execute(text("DROP TABLE IF EXISTS alembic_version"))
                connection.commit()
            
            # Drop all application tables
            from src.models.user import Base
            Base.metadata.drop_all(db_manager.sync_engine)
            
            # Run migrations from scratch
            command.upgrade(self.alembic_cfg, "head")
            
            logger.info("Database reset successfully")
            return True
        except Exception as e:
            logger.error(f"Failed to reset database: {e}")
            return False


# Global migration manager instance
migration_manager = MigrationManager()


# Convenience functions
async def check_and_upgrade_database() -> bool:
    """Check database status and upgrade if needed."""
    try:
        if not migration_manager.is_database_up_to_date():
            # 自動マイグレーションが有効な場合のみ実行
            if migration_manager.auto_migrate:
                logger.info("データベースが最新ではありません。マイグレーションを実行します...")
                return migration_manager.upgrade_database()
            else:
                # 本番環境などでは警告のみ
                logger.warning("データベースが最新ではありませんが、自動マイグレーションは無効です")
                logger.warning("手動でマイグレーションを実行してください: alembic upgrade head")
                return False
        else:
            logger.info("データベースは最新の状態です")
            return True
    except Exception as e:
        logger.error(f"データベースの確認とアップグレードに失敗しました: {e}")
        return False


async def get_database_status() -> dict:
    """Get current database and migration status."""
    return await migration_manager.check_database_health()