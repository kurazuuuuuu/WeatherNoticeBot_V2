"""ユーザー管理サービス - Discord Weather Bot用のユーザー情報管理機能を提供"""

import logging
from typing import List, Optional

from sqlalchemy import select
from sqlalchemy.exc import IntegrityError, SQLAlchemyError
from sqlalchemy.ext.asyncio import AsyncSession

from src.database import get_db_session
from src.models.user import User

logger = logging.getLogger(__name__)


class UserService:
    """ユーザー情報の管理とデータベース操作を担当するサービスクラス"""
    
    async def create_user(self, discord_id: int) -> Optional[User]:
        """
        新しいユーザーを作成する
        
        Args:
            discord_id: DiscordユーザーID
            
        Returns:
            作成されたUserオブジェクト、失敗時はNone
        """
        try:
            async with get_db_session() as session:
                # 既存ユーザーの確認
                existing_user = await self.get_user_by_discord_id(discord_id)
                if existing_user:
                    logger.info(f"ユーザー {discord_id} は既に存在します")
                    return existing_user
                
                # 新しいユーザーを作成
                new_user = User.from_discord_id(discord_id)
                session.add(new_user)
                await session.commit()
                await session.refresh(new_user)
                
                logger.info(f"新しいユーザーを作成しました: {discord_id}")
                return new_user
                
        except IntegrityError as e:
            logger.error(f"ユーザー作成時の整合性エラー (Discord ID: {discord_id}): {e}")
            return None
        except SQLAlchemyError as e:
            logger.error(f"ユーザー作成時のデータベースエラー (Discord ID: {discord_id}): {e}")
            return None
        except Exception as e:
            logger.error(f"ユーザー作成時の予期しないエラー (Discord ID: {discord_id}): {e}")
            return None
    
    async def get_user_by_discord_id(self, discord_id: int) -> Optional[User]:
        """
        Discord IDでユーザーを取得する
        
        Args:
            discord_id: DiscordユーザーID
            
        Returns:
            見つかったUserオブジェクト、見つからない場合はNone
        """
        try:
            async with get_db_session() as session:
                stmt = select(User).where(User.discord_id == discord_id)
                result = await session.execute(stmt)
                user = result.scalar_one_or_none()
                
                if user:
                    logger.debug(f"ユーザーを取得しました: {discord_id}")
                else:
                    logger.debug(f"ユーザーが見つかりません: {discord_id}")
                
                return user
                
        except SQLAlchemyError as e:
            logger.error(f"ユーザー取得時のデータベースエラー (Discord ID: {discord_id}): {e}")
            return None
        except Exception as e:
            logger.error(f"ユーザー取得時の予期しないエラー (Discord ID: {discord_id}): {e}")
            return None
    
    async def get_user_by_id(self, user_id: int) -> Optional[User]:
        """
        内部IDでユーザーを取得する
        
        Args:
            user_id: 内部ユーザーID
            
        Returns:
            見つかったUserオブジェクト、見つからない場合はNone
        """
        try:
            async with get_db_session() as session:
                stmt = select(User).where(User.id == user_id)
                result = await session.execute(stmt)
                user = result.scalar_one_or_none()
                
                if user:
                    logger.debug(f"ユーザーを取得しました (ID: {user_id})")
                else:
                    logger.debug(f"ユーザーが見つかりません (ID: {user_id})")
                
                return user
                
        except SQLAlchemyError as e:
            logger.error(f"ユーザー取得時のデータベースエラー (ID: {user_id}): {e}")
            return None
        except Exception as e:
            logger.error(f"ユーザー取得時の予期しないエラー (ID: {user_id}): {e}")
            return None
    
    async def set_user_location(self, discord_id: int, area_code: str, area_name: str) -> bool:
        """
        ユーザーの位置情報を設定する
        
        Args:
            discord_id: DiscordユーザーID
            area_code: 地域コード
            area_name: 地域名
            
        Returns:
            設定成功時はTrue、失敗時はFalse
        """
        try:
            async with get_db_session() as session:
                # ユーザーを取得または作成
                user = await self.get_user_by_discord_id(discord_id)
                if not user:
                    user = await self.create_user(discord_id)
                    if not user:
                        logger.error(f"ユーザーの作成に失敗しました: {discord_id}")
                        return False
                
                # セッションに再アタッチ
                user = await session.merge(user)
                
                # 位置情報を設定
                user.set_location(area_code, area_name)
                await session.commit()
                
                logger.info(f"ユーザー {discord_id} の位置情報を設定しました: {area_name} ({area_code})")
                return True
                
        except SQLAlchemyError as e:
            logger.error(f"位置情報設定時のデータベースエラー (Discord ID: {discord_id}): {e}")
            return False
        except Exception as e:
            logger.error(f"位置情報設定時の予期しないエラー (Discord ID: {discord_id}): {e}")
            return False
    
    async def get_user_location(self, discord_id: int) -> Optional[tuple[str, str]]:
        """
        ユーザーの位置情報を取得する
        
        Args:
            discord_id: DiscordユーザーID
            
        Returns:
            (area_code, area_name)のタプル、設定されていない場合はNone
        """
        try:
            user = await self.get_user_by_discord_id(discord_id)
            if user and user.has_location():
                return (user.area_code, user.area_name)
            return None
            
        except Exception as e:
            logger.error(f"位置情報取得時のエラー (Discord ID: {discord_id}): {e}")
            return None
    
    async def set_notification_schedule(self, discord_id: int, hour: int) -> bool:
        """
        ユーザーの通知スケジュールを設定する
        
        Args:
            discord_id: DiscordユーザーID
            hour: 通知時間（0-23時）
            
        Returns:
            設定成功時はTrue、失敗時はFalse
        """
        try:
            # 時間の妥当性チェック
            if not 0 <= hour <= 23:
                logger.error(f"無効な時間が指定されました: {hour}")
                return False
            
            async with get_db_session() as session:
                # ユーザーを取得または作成
                user = await self.get_user_by_discord_id(discord_id)
                if not user:
                    user = await self.create_user(discord_id)
                    if not user:
                        logger.error(f"ユーザーの作成に失敗しました: {discord_id}")
                        return False
                
                # セッションに再アタッチ
                user = await session.merge(user)
                
                # 通知スケジュールを設定
                user.set_notification_schedule(hour)
                await session.commit()
                
                logger.info(f"ユーザー {discord_id} の通知スケジュールを設定しました: {hour}時")
                return True
                
        except ValueError as e:
            logger.error(f"通知スケジュール設定時の値エラー (Discord ID: {discord_id}): {e}")
            return False
        except SQLAlchemyError as e:
            logger.error(f"通知スケジュール設定時のデータベースエラー (Discord ID: {discord_id}): {e}")
            return False
        except Exception as e:
            logger.error(f"通知スケジュール設定時の予期しないエラー (Discord ID: {discord_id}): {e}")
            return False
    
    async def disable_notifications(self, discord_id: int) -> bool:
        """
        ユーザーの通知を無効化する
        
        Args:
            discord_id: DiscordユーザーID
            
        Returns:
            無効化成功時はTrue、失敗時はFalse
        """
        try:
            async with get_db_session() as session:
                user = await self.get_user_by_discord_id(discord_id)
                if not user:
                    logger.warning(f"通知無効化対象のユーザーが見つかりません: {discord_id}")
                    return False
                
                # セッションに再アタッチ
                user = await session.merge(user)
                
                # 通知を無効化
                user.disable_notifications()
                await session.commit()
                
                logger.info(f"ユーザー {discord_id} の通知を無効化しました")
                return True
                
        except SQLAlchemyError as e:
            logger.error(f"通知無効化時のデータベースエラー (Discord ID: {discord_id}): {e}")
            return False
        except Exception as e:
            logger.error(f"通知無効化時の予期しないエラー (Discord ID: {discord_id}): {e}")
            return False
    
    async def get_user_settings(self, discord_id: int) -> Optional[dict]:
        """
        ユーザーの設定情報を取得する
        
        Args:
            discord_id: DiscordユーザーID
            
        Returns:
            ユーザー設定の辞書、ユーザーが見つからない場合はNone
        """
        try:
            user = await self.get_user_by_discord_id(discord_id)
            if not user:
                return None
            
            return {
                'discord_id': user.discord_id,
                'area_code': user.area_code,
                'area_name': user.area_name,
                'notification_hour': user.notification_hour,
                'timezone': user.timezone,
                'is_notification_enabled': user.is_notification_enabled,
                'has_location': user.has_location(),
                'has_notification_enabled': user.has_notification_enabled(),
                'created_at': user.created_at,
                'updated_at': user.updated_at
            }
            
        except Exception as e:
            logger.error(f"ユーザー設定取得時のエラー (Discord ID: {discord_id}): {e}")
            return None
    
    async def get_users_with_notifications(self, hour: Optional[int] = None) -> List[User]:
        """
        通知が有効なユーザーを取得する
        
        Args:
            hour: 特定の時間のユーザーのみを取得（省略時は全ての通知有効ユーザー）
            
        Returns:
            通知が有効なユーザーのリスト
        """
        try:
            async with get_db_session() as session:
                stmt = select(User).where(User.is_notification_enabled == True)
                
                if hour is not None:
                    if not 0 <= hour <= 23:
                        logger.error(f"無効な時間が指定されました: {hour}")
                        return []
                    stmt = stmt.where(User.notification_hour == hour)
                
                result = await session.execute(stmt)
                users = result.scalars().all()
                
                logger.debug(f"通知有効ユーザーを取得しました: {len(users)}人")
                return list(users)
                
        except SQLAlchemyError as e:
            logger.error(f"通知有効ユーザー取得時のデータベースエラー: {e}")
            return []
        except Exception as e:
            logger.error(f"通知有効ユーザー取得時の予期しないエラー: {e}")
            return []
    
    async def update_user(self, discord_id: int, **kwargs) -> bool:
        """
        ユーザー情報を更新する
        
        Args:
            discord_id: DiscordユーザーID
            **kwargs: 更新するフィールドと値
            
        Returns:
            更新成功時はTrue、失敗時はFalse
        """
        try:
            async with get_db_session() as session:
                user = await self.get_user_by_discord_id(discord_id)
                if not user:
                    logger.warning(f"更新対象のユーザーが見つかりません: {discord_id}")
                    return False
                
                # セッションに再アタッチ
                user = await session.merge(user)
                
                # 指定されたフィールドを更新
                for field, value in kwargs.items():
                    if hasattr(user, field):
                        setattr(user, field, value)
                    else:
                        logger.warning(f"無効なフィールドが指定されました: {field}")
                
                await session.commit()
                
                logger.info(f"ユーザー {discord_id} の情報を更新しました: {kwargs}")
                return True
                
        except SQLAlchemyError as e:
            logger.error(f"ユーザー更新時のデータベースエラー (Discord ID: {discord_id}): {e}")
            return False
        except Exception as e:
            logger.error(f"ユーザー更新時の予期しないエラー (Discord ID: {discord_id}): {e}")
            return False
    
    async def delete_user(self, discord_id: int) -> bool:
        """
        ユーザーを削除する
        
        Args:
            discord_id: DiscordユーザーID
            
        Returns:
            削除成功時はTrue、失敗時はFalse
        """
        try:
            async with get_db_session() as session:
                user = await self.get_user_by_discord_id(discord_id)
                if not user:
                    logger.warning(f"削除対象のユーザーが見つかりません: {discord_id}")
                    return False
                
                # セッションに再アタッチ
                user = await session.merge(user)
                
                await session.delete(user)
                await session.commit()
                
                logger.info(f"ユーザー {discord_id} を削除しました")
                return True
                
        except SQLAlchemyError as e:
            logger.error(f"ユーザー削除時のデータベースエラー (Discord ID: {discord_id}): {e}")
            return False
        except Exception as e:
            logger.error(f"ユーザー削除時の予期しないエラー (Discord ID: {discord_id}): {e}")
            return False
    
    async def get_all_users(self) -> List[User]:
        """
        全てのユーザーを取得する
        
        Returns:
            全ユーザーのリスト
        """
        try:
            async with get_db_session() as session:
                stmt = select(User)
                result = await session.execute(stmt)
                users = result.scalars().all()
                
                logger.debug(f"全ユーザーを取得しました: {len(users)}人")
                return list(users)
                
        except SQLAlchemyError as e:
            logger.error(f"全ユーザー取得時のデータベースエラー: {e}")
            return []
        except Exception as e:
            logger.error(f"全ユーザー取得時の予期しないエラー: {e}")
            return []
    
    async def get_user_count(self) -> int:
        """
        ユーザー数を取得する
        
        Returns:
            登録ユーザー数
        """
        try:
            async with get_db_session() as session:
                from sqlalchemy import func
                stmt = select(func.count(User.id))
                result = await session.execute(stmt)
                count = result.scalar()
                
                logger.debug(f"ユーザー数: {count}")
                return count or 0
                
        except SQLAlchemyError as e:
            logger.error(f"ユーザー数取得時のデータベースエラー: {e}")
            return 0
        except Exception as e:
            logger.error(f"ユーザー数取得時の予期しないエラー: {e}")
            return 0


# グローバルなユーザーサービスインスタンス
user_service = UserService()