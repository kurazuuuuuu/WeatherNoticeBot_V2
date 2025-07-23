"""ユーザー管理サービス - Discord Weather Bot用のユーザー情報管理機能を提供"""

import logging
from typing import List, Optional, Dict, Any
from datetime import datetime

from sqlalchemy import select, text
from sqlalchemy.exc import IntegrityError, SQLAlchemyError
from sqlalchemy.ext.asyncio import AsyncSession

from src.database import get_db_session, db_manager, DatabaseConnectionError, MemoryUserData
from src.models.user import User

logger = logging.getLogger(__name__)


class UserService:
    """ユーザー情報の管理とデータベース操作を担当するサービスクラス"""
    
    def _use_memory_storage(self) -> bool:
        """メモリストレージを使用すべきかどうかを判定"""
        return db_manager.memory_storage.is_enabled()
    
    def _memory_user_to_user_model(self, memory_user: MemoryUserData) -> User:
        """MemoryUserDataをUserモデルに変換"""
        user = User()
        user.discord_id = memory_user.discord_id
        user.area_code = memory_user.area_code
        user.area_name = memory_user.area_name
        user.notification_hour = memory_user.notification_hour
        user.timezone = memory_user.timezone
        user.is_notification_enabled = memory_user.is_notification_enabled
        user.created_at = memory_user.created_at
        user.updated_at = memory_user.updated_at
        return user
    
    def _user_model_to_memory_user(self, user: User) -> MemoryUserData:
        """UserモデルをMemoryUserDataに変換"""
        return MemoryUserData(
            discord_id=user.discord_id,
            area_code=user.area_code,
            area_name=user.area_name,
            notification_hour=user.notification_hour,
            timezone=user.timezone,
            is_notification_enabled=user.is_notification_enabled,
            created_at=user.created_at,
            updated_at=user.updated_at
        )
    
    async def create_user(self, discord_id: int) -> Optional[User]:
        """
        新しいユーザーを作成する
        
        Args:
            discord_id: DiscordユーザーID
            
        Returns:
            作成されたUserオブジェクト、失敗時はNone
        """
        # メモリストレージを使用する場合
        if self._use_memory_storage():
            try:
                # 既存ユーザーの確認
                existing_memory_user = db_manager.memory_storage.get_user(discord_id)
                if existing_memory_user:
                    logger.info(f"ユーザー {discord_id} は既に存在します（メモリストレージ）")
                    return self._memory_user_to_user_model(existing_memory_user)
                
                # 新しいユーザーを作成
                memory_user = MemoryUserData(discord_id=discord_id)
                db_manager.memory_storage.set_user(memory_user)
                
                logger.info(f"新しいユーザーを作成しました（メモリストレージ）: {discord_id}")
                return self._memory_user_to_user_model(memory_user)
                
            except Exception as e:
                logger.error(f"メモリストレージでのユーザー作成エラー (Discord ID: {discord_id}): {e}")
                return None
        
        # 通常のデータベース処理
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
                
        except DatabaseConnectionError:
            # データベース接続エラーの場合、メモリストレージにフォールバック
            logger.warning(f"データベース接続エラーのため、メモリストレージを使用します: {discord_id}")
            try:
                memory_user = MemoryUserData(discord_id=discord_id)
                db_manager.memory_storage.set_user(memory_user)
                return self._memory_user_to_user_model(memory_user)
            except Exception as e:
                logger.error(f"メモリストレージフォールバックでのユーザー作成エラー: {e}")
                return None
                
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
        # メモリストレージを使用する場合
        if self._use_memory_storage():
            try:
                memory_user = db_manager.memory_storage.get_user(discord_id)
                if memory_user:
                    logger.debug(f"ユーザーを取得しました（メモリストレージ）: {discord_id}")
                    return self._memory_user_to_user_model(memory_user)
                else:
                    logger.debug(f"ユーザーが見つかりません（メモリストレージ）: {discord_id}")
                    return None
                    
            except Exception as e:
                logger.error(f"メモリストレージでのユーザー取得エラー (Discord ID: {discord_id}): {e}")
                return None
        
        # 通常のデータベース処理
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
                
        except DatabaseConnectionError:
            # データベース接続エラーの場合、メモリストレージから取得を試行
            logger.warning(f"データベース接続エラーのため、メモリストレージから取得を試行します: {discord_id}")
            try:
                memory_user = db_manager.memory_storage.get_user(discord_id)
                if memory_user:
                    return self._memory_user_to_user_model(memory_user)
                return None
            except Exception as e:
                logger.error(f"メモリストレージフォールバックでのユーザー取得エラー: {e}")
                return None
                
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
        # メモリストレージを使用する場合
        if self._use_memory_storage():
            try:
                # ユーザーを取得または作成
                memory_user = db_manager.memory_storage.get_user(discord_id)
                if not memory_user:
                    memory_user = MemoryUserData(discord_id=discord_id)
                
                # 位置情報を設定
                memory_user.area_code = area_code
                memory_user.area_name = area_name
                memory_user.updated_at = datetime.now()
                
                db_manager.memory_storage.set_user(memory_user)
                
                logger.info(f"ユーザー {discord_id} の位置情報を設定しました（メモリストレージ）: {area_name} ({area_code})")
                return True
                
            except Exception as e:
                logger.error(f"メモリストレージでの位置情報設定エラー (Discord ID: {discord_id}): {e}")
                return False
        
        # 通常のデータベース処理
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
                
        except DatabaseConnectionError:
            # データベース接続エラーの場合、メモリストレージにフォールバック
            logger.warning(f"データベース接続エラーのため、メモリストレージを使用します: {discord_id}")
            try:
                memory_user = db_manager.memory_storage.get_user(discord_id)
                if not memory_user:
                    memory_user = MemoryUserData(discord_id=discord_id)
                
                memory_user.area_code = area_code
                memory_user.area_name = area_name
                memory_user.updated_at = datetime.now()
                
                db_manager.memory_storage.set_user(memory_user)
                return True
            except Exception as e:
                logger.error(f"メモリストレージフォールバックでの位置情報設定エラー: {e}")
                return False
                
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
        # メモリストレージを使用する場合
        if self._use_memory_storage():
            try:
                memory_users = db_manager.memory_storage.get_users_with_notifications(hour)
                users = [self._memory_user_to_user_model(memory_user) for memory_user in memory_users]
                
                logger.debug(f"通知有効ユーザーを取得しました（メモリストレージ）: {len(users)}人")
                return users
                
            except Exception as e:
                logger.error(f"メモリストレージでの通知有効ユーザー取得エラー: {e}")
                return []
        
        # 通常のデータベース処理
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
                
        except DatabaseConnectionError:
            # データベース接続エラーの場合、メモリストレージから取得を試行
            logger.warning("データベース接続エラーのため、メモリストレージから通知有効ユーザーを取得します")
            try:
                memory_users = db_manager.memory_storage.get_users_with_notifications(hour)
                users = [self._memory_user_to_user_model(memory_user) for memory_user in memory_users]
                return users
            except Exception as e:
                logger.error(f"メモリストレージフォールバックでの通知有効ユーザー取得エラー: {e}")
                return []
                
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
    
    async def get_users_with_notifications_enabled(self) -> List[User]:
        """
        通知が有効で通知時間が設定されているユーザーを取得する
        
        Returns:
            通知が有効なユーザーのリスト
        """
        try:
            async with get_db_session() as session:
                stmt = select(User).where(
                    User.is_notification_enabled == True,
                    User.notification_hour.is_not(None)
                )
                
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
    
    async def get_user_count(self) -> int:
        """
        ユーザー数を取得する
        
        Returns:
            登録ユーザー数
        """
        # メモリストレージを使用する場合
        if self._use_memory_storage():
            try:
                count = db_manager.memory_storage.get_user_count()
                logger.debug(f"ユーザー数（メモリストレージ）: {count}")
                return count
                
            except Exception as e:
                logger.error(f"メモリストレージでのユーザー数取得エラー: {e}")
                return 0
        
        # 通常のデータベース処理
        try:
            async with get_db_session() as session:
                from sqlalchemy import func
                stmt = select(func.count(User.id))
                result = await session.execute(stmt)
                count = result.scalar()
                
                logger.debug(f"ユーザー数: {count}")
                return count or 0
                
        except DatabaseConnectionError:
            # データベース接続エラーの場合、メモリストレージから取得を試行
            logger.warning("データベース接続エラーのため、メモリストレージからユーザー数を取得します")
            try:
                count = db_manager.memory_storage.get_user_count()
                return count
            except Exception as e:
                logger.error(f"メモリストレージフォールバックでのユーザー数取得エラー: {e}")
                return 0
                
        except SQLAlchemyError as e:
            logger.error(f"ユーザー数取得時のデータベースエラー: {e}")
            return 0
        except Exception as e:
            logger.error(f"ユーザー数取得時の予期しないエラー: {e}")
            return 0
    
    async def validate_data_integrity(self) -> Dict[str, Any]:
        """
        データ整合性をチェックする
        
        Returns:
            整合性チェック結果
        """
        result = {
            "status": "healthy",
            "checks": [],
            "errors": [],
            "warnings": []
        }
        
        try:
            # メモリストレージを使用している場合の警告
            if self._use_memory_storage():
                result["warnings"].append("メモリストレージを使用中です。データベース復旧後に同期が必要です。")
                result["checks"].append({
                    "name": "memory_storage_check",
                    "status": "warning",
                    "message": f"メモリストレージ内ユーザー数: {db_manager.memory_storage.get_user_count()}"
                })
                return result
            
            # データベースの整合性チェック
            async with get_db_session() as session:
                # 1. 重複するdiscord_idのチェック
                duplicate_check = await session.execute(text("""
                    SELECT discord_id, COUNT(*) as count 
                    FROM users 
                    GROUP BY discord_id 
                    HAVING COUNT(*) > 1
                """))
                duplicates = duplicate_check.fetchall()
                
                if duplicates:
                    result["status"] = "error"
                    for dup in duplicates:
                        result["errors"].append(f"重複するDiscord ID: {dup.discord_id} ({dup.count}件)")
                else:
                    result["checks"].append({
                        "name": "duplicate_discord_id_check",
                        "status": "ok",
                        "message": "重複するDiscord IDはありません"
                    })
                
                # 2. 無効な通知時間のチェック
                invalid_hour_check = await session.execute(text("""
                    SELECT COUNT(*) as count 
                    FROM users 
                    WHERE notification_hour IS NOT NULL 
                    AND (notification_hour < 0 OR notification_hour > 23)
                """))
                invalid_hours = invalid_hour_check.scalar()
                
                if invalid_hours > 0:
                    result["status"] = "error"
                    result["errors"].append(f"無効な通知時間を持つユーザー: {invalid_hours}件")
                else:
                    result["checks"].append({
                        "name": "notification_hour_check",
                        "status": "ok",
                        "message": "通知時間の設定は正常です"
                    })
                
                # 3. 通知が有効だが時間が設定されていないユーザーのチェック
                inconsistent_notification_check = await session.execute(text("""
                    SELECT COUNT(*) as count 
                    FROM users 
                    WHERE is_notification_enabled = true 
                    AND notification_hour IS NULL
                """))
                inconsistent_notifications = inconsistent_notification_check.scalar()
                
                if inconsistent_notifications > 0:
                    result["warnings"].append(f"通知が有効だが時間が未設定のユーザー: {inconsistent_notifications}件")
                    result["checks"].append({
                        "name": "notification_consistency_check",
                        "status": "warning",
                        "message": f"通知設定に不整合があるユーザー: {inconsistent_notifications}件"
                    })
                else:
                    result["checks"].append({
                        "name": "notification_consistency_check",
                        "status": "ok",
                        "message": "通知設定の整合性は正常です"
                    })
                
                # 4. 古いデータのチェック（1年以上更新されていない）
                old_data_check = await session.execute(text("""
                    SELECT COUNT(*) as count 
                    FROM users 
                    WHERE updated_at < datetime('now', '-1 year')
                """))
                old_data_count = old_data_check.scalar()
                
                if old_data_count > 0:
                    result["warnings"].append(f"1年以上更新されていないユーザー: {old_data_count}件")
                    result["checks"].append({
                        "name": "old_data_check",
                        "status": "warning",
                        "message": f"古いデータ: {old_data_count}件"
                    })
                else:
                    result["checks"].append({
                        "name": "old_data_check",
                        "status": "ok",
                        "message": "古いデータはありません"
                    })
                
                # 5. 総ユーザー数の確認
                total_users = await self.get_user_count()
                result["checks"].append({
                    "name": "total_user_count",
                    "status": "info",
                    "message": f"総ユーザー数: {total_users}件"
                })
                
        except DatabaseConnectionError:
            result["status"] = "error"
            result["errors"].append("データベース接続エラーのため整合性チェックを実行できません")
            
        except Exception as e:
            result["status"] = "error"
            result["errors"].append(f"整合性チェック中にエラーが発生しました: {str(e)}")
            logger.error(f"データ整合性チェックエラー: {e}")
        
        return result
    
    async def get_service_health(self) -> Dict[str, Any]:
        """
        ユーザーサービスのヘルスチェック
        
        Returns:
            サービスの健全性情報
        """
        health_info = {
            "service_name": "UserService",
            "timestamp": datetime.now().isoformat(),
            "database_status": "unknown",
            "memory_storage_enabled": self._use_memory_storage(),
            "user_count": 0,
            "notification_enabled_users": 0
        }
        
        try:
            # データベース状態の確認
            db_health = await db_manager.health_check()
            health_info["database_status"] = db_health.get("status", "unknown")
            health_info["database_details"] = db_health
            
            # ユーザー数の取得
            health_info["user_count"] = await self.get_user_count()
            
            # 通知有効ユーザー数の取得
            notification_users = await self.get_users_with_notifications()
            health_info["notification_enabled_users"] = len(notification_users)
            
            # データ整合性チェック
            integrity_check = await self.validate_data_integrity()
            health_info["data_integrity"] = integrity_check
            
            # 全体的な健全性の判定
            if db_health.get("status") == "healthy" and integrity_check["status"] != "error":
                health_info["overall_status"] = "healthy"
            elif self._use_memory_storage():
                health_info["overall_status"] = "degraded"
            else:
                health_info["overall_status"] = "unhealthy"
                
        except Exception as e:
            health_info["overall_status"] = "error"
            health_info["error"] = str(e)
            logger.error(f"ユーザーサービスヘルスチェックエラー: {e}")
        
        return health_info


# グローバルなユーザーサービスインスタンス
user_service = UserService()