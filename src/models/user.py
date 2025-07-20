"""User model for Discord Weather Bot."""

from datetime import datetime
from typing import Optional

from sqlalchemy import BigInteger, Boolean, Column, DateTime, Integer, String
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.sql import func

Base = declarative_base()


class User(Base):
    """User model for storing Discord user information and preferences."""
    
    __tablename__ = 'users'
    
    # Primary key
    id = Column(Integer, primary_key=True, autoincrement=True)
    
    # Discord user ID (unique identifier)
    discord_id = Column(BigInteger, unique=True, nullable=False, index=True)
    
    # Location information
    area_code = Column(String(10), nullable=True)
    area_name = Column(String(100), nullable=True)
    
    # Notification settings
    notification_hour = Column(Integer, nullable=True)  # 0-23時で通知時間を指定
    timezone = Column(String(50), default='Asia/Tokyo', nullable=False)
    is_notification_enabled = Column(Boolean, default=False, nullable=False)
    
    # Timestamps
    created_at = Column(DateTime, default=func.now(), nullable=False)
    updated_at = Column(DateTime, default=func.now(), onupdate=func.now(), nullable=False)
    
    def __repr__(self) -> str:
        """String representation of User model."""
        return (
            f"<User(id={self.id}, discord_id={self.discord_id}, "
            f"area_name='{self.area_name}', notification_enabled={self.is_notification_enabled})>"
        )
    
    def to_dict(self) -> dict:
        """Convert User model to dictionary."""
        return {
            'id': self.id,
            'discord_id': self.discord_id,
            'area_code': self.area_code,
            'area_name': self.area_name,
            'notification_hour': self.notification_hour,
            'timezone': self.timezone,
            'is_notification_enabled': self.is_notification_enabled,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None,
        }
    
    @classmethod
    def from_discord_id(cls, discord_id: int) -> 'User':
        """Create a new User instance with Discord ID."""
        return cls(discord_id=discord_id)
    
    def set_location(self, area_code: str, area_name: str) -> None:
        """Set user's location information."""
        self.area_code = area_code
        self.area_name = area_name
    
    def set_notification_schedule(self, hour: int) -> None:
        """Set notification schedule (0-23 hour format)."""
        if not 0 <= hour <= 23:
            raise ValueError("Hour must be between 0 and 23")
        self.notification_hour = hour
        self.is_notification_enabled = True
    
    def disable_notifications(self) -> None:
        """Disable notifications for this user."""
        self.is_notification_enabled = False
        self.notification_hour = None
    
    def has_location(self) -> bool:
        """Check if user has set a location."""
        return self.area_code is not None and self.area_name is not None
    
    def has_notification_enabled(self) -> bool:
        """Check if user has notifications enabled."""
        return self.is_notification_enabled and self.notification_hour is not None