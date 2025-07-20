"""Test script to verify database models and migration functionality."""

import asyncio
import logging
import sys
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent / "src"))

from src.database import db_manager, get_db_session, init_database
from src.models.user import User
from src.utils.migration import migration_manager, get_database_status

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


async def test_database_functionality():
    """Test database models and migration functionality."""
    try:
        logger.info("Starting database functionality test...")
        
        # Initialize database
        await init_database()
        logger.info("✓ Database initialized successfully")
        
        # Check migration status
        status = await get_database_status()
        logger.info(f"✓ Database status: {status}")
        
        # Test User model CRUD operations
        test_discord_id = 123456789012345678
        
        # Create a new user
        async with get_db_session() as session:
            # Check if user already exists
            existing_user = await session.get(User, test_discord_id)
            if existing_user:
                await session.delete(existing_user)
                await session.commit()
            
            # Create new user
            user = User.from_discord_id(test_discord_id)
            user.set_location("130010", "東京都")
            user.set_notification_schedule(9)  # 9 AM
            
            session.add(user)
            await session.commit()
            logger.info(f"✓ User created: {user}")
        
        # Read user
        async with get_db_session() as session:
            from sqlalchemy import select
            
            stmt = select(User).where(User.discord_id == test_discord_id)
            result = await session.execute(stmt)
            user = result.scalar_one_or_none()
            
            if user:
                logger.info(f"✓ User retrieved: {user}")
                logger.info(f"  - Has location: {user.has_location()}")
                logger.info(f"  - Has notifications: {user.has_notification_enabled()}")
                logger.info(f"  - User dict: {user.to_dict()}")
            else:
                logger.error("✗ User not found")
                return False
        
        # Update user
        async with get_db_session() as session:
            stmt = select(User).where(User.discord_id == test_discord_id)
            result = await session.execute(stmt)
            user = result.scalar_one_or_none()
            
            if user:
                user.set_location("270000", "大阪府")
                user.disable_notifications()
                await session.commit()
                logger.info(f"✓ User updated: {user}")
        
        # Verify update
        async with get_db_session() as session:
            stmt = select(User).where(User.discord_id == test_discord_id)
            result = await session.execute(stmt)
            user = result.scalar_one_or_none()
            
            if user and user.area_name == "大阪府" and not user.has_notification_enabled():
                logger.info("✓ User update verified")
            else:
                logger.error("✗ User update verification failed")
                return False
        
        # Delete user
        async with get_db_session() as session:
            stmt = select(User).where(User.discord_id == test_discord_id)
            result = await session.execute(stmt)
            user = result.scalar_one_or_none()
            
            if user:
                await session.delete(user)
                await session.commit()
                logger.info("✓ User deleted")
        
        # Verify deletion
        async with get_db_session() as session:
            stmt = select(User).where(User.discord_id == test_discord_id)
            result = await session.execute(stmt)
            user = result.scalar_one_or_none()
            
            if user is None:
                logger.info("✓ User deletion verified")
            else:
                logger.error("✗ User deletion verification failed")
                return False
        
        logger.info("✓ All database functionality tests passed!")
        return True
        
    except Exception as e:
        logger.error(f"✗ Database test failed: {e}")
        return False
    
    finally:
        # Close database connections
        await db_manager.close()


if __name__ == "__main__":
    success = asyncio.run(test_database_functionality())
    sys.exit(0 if success else 1)