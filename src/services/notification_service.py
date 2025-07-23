"""
通知サービス
定時天気情報のDM送信機能を提供する
"""

import asyncio
import logging
from typing import Optional, Dict, Any
from datetime import datetime

import discord
from discord.ext import commands

from .user_service import UserService
from .weather_service import WeatherService
from .ai_service import AIMessageService, WeatherContext, weather_data_to_context
from ..utils.embed_utils import WeatherEmbedBuilder

logger = logging.getLogger(__name__)


class NotificationService:
    """定時通知の送信を管理するサービス"""
    
    # リトライ設定
    MAX_RETRIES = 3
    RETRY_DELAY = 2.0  # 秒
    BACKOFF_FACTOR = 2.0
    
    def __init__(
        self, 
        bot_client: Optional[discord.Client] = None,
        user_service: Optional[UserService] = None,
        weather_service: Optional[WeatherService] = None,
        ai_service: Optional[AIMessageService] = None
    ):
        """
        通知サービスを初期化
        
        Args:
            bot_client: Discordボットクライアント
            user_service: ユーザー管理サービス
            weather_service: 天気情報サービス
            ai_service: AIメッセージ生成サービス
        """
        self.bot_client = bot_client
        self.user_service = user_service or UserService()
        self.weather_service = weather_service or WeatherService()
        self.ai_service = ai_service or AIMessageService()
    
    def set_bot_client(self, bot_client: discord.Client) -> None:
        """
        Discordボットクライアントを設定
        
        Args:
            bot_client: Discordボットクライアント
        """
        self.bot_client = bot_client
    
    async def send_scheduled_weather_update(self, user_id: int) -> bool:
        """
        定時天気情報をDMで送信
        
        Args:
            user_id: DiscordユーザーID
            
        Returns:
            bool: 送信成功時はTrue、失敗時はFalse
        """
        if not self.bot_client:
            logger.error("Discordボットクライアントが設定されていません")
            return False
        
        try:
            # ユーザー情報を取得
            user_settings = await self.user_service.get_user_settings(user_id)
            if not user_settings:
                logger.warning(f"ユーザー設定が見つかりません: {user_id}")
                return False
            
            # 位置情報が設定されているかチェック
            if not user_settings.get('area_code') or not user_settings.get('area_name'):
                logger.warning(f"ユーザー {user_id} の位置情報が設定されていません")
                await self._send_location_setup_message(user_id)
                return False
            
            # 天気情報を取得
            area_code = user_settings['area_code']
            area_name = user_settings['area_name']
            
            weather_data = await self._get_weather_data_with_retry(area_code)
            if not weather_data:
                logger.error(f"天気情報の取得に失敗しました: {area_code}")
                await self._send_error_message(user_id, "天気情報の取得に失敗しました")
                return False
            
            # AIメッセージを生成
            weather_context = weather_data_to_context(weather_data)
            ai_message = await self._generate_ai_message_with_retry(weather_context)
            
            # DMを送信
            success = await self._send_weather_dm_with_retry(user_id, weather_data, ai_message)
            
            if success:
                logger.info(f"定時天気情報を送信しました: ユーザー {user_id}, 地域 {area_name}")
            else:
                logger.error(f"定時天気情報の送信に失敗しました: ユーザー {user_id}")
            
            return success
            
        except Exception as e:
            logger.error(f"定時天気情報送信中に予期しないエラーが発生しました: ユーザー {user_id} - {str(e)}")
            return False
    
    async def _get_weather_data_with_retry(self, area_code: str, retries: int = 0):
        """
        リトライ機能付きで天気データを取得
        
        Args:
            area_code: 地域コード
            retries: 現在のリトライ回数
            
        Returns:
            天気データまたはNone
        """
        try:
            async with self.weather_service:
                return await self.weather_service.get_current_weather(area_code)
                
        except Exception as e:
            logger.warning(f"天気データ取得エラー (試行 {retries + 1}/{self.MAX_RETRIES}): {str(e)}")
            
            if retries < self.MAX_RETRIES - 1:
                delay = self.RETRY_DELAY * (self.BACKOFF_FACTOR ** retries)
                logger.info(f"天気データ取得をリトライします: {delay}秒後")
                await asyncio.sleep(delay)
                return await self._get_weather_data_with_retry(area_code, retries + 1)
            else:
                logger.error(f"天気データ取得の最大リトライ回数に達しました: {area_code}")
                return None
    
    async def _generate_ai_message_with_retry(self, weather_context: WeatherContext, retries: int = 0) -> str:
        """
        リトライ機能付きでAIメッセージを生成
        
        Args:
            weather_context: 天気情報のコンテキスト
            retries: 現在のリトライ回数
            
        Returns:
            生成されたメッセージ
        """
        try:
            # 時間帯に応じてメッセージタイプを決定
            current_hour = datetime.now().hour
            if 5 <= current_hour < 12:
                message_type = "morning"
            elif 17 <= current_hour < 21:
                message_type = "evening"
            else:
                message_type = "general"
            
            return await self.ai_service.generate_positive_message(weather_context, message_type)
            
        except Exception as e:
            logger.warning(f"AIメッセージ生成エラー (試行 {retries + 1}/{self.MAX_RETRIES}): {str(e)}")
            
            if retries < self.MAX_RETRIES - 1:
                delay = self.RETRY_DELAY * (self.BACKOFF_FACTOR ** retries)
                logger.info(f"AIメッセージ生成をリトライします: {delay}秒後")
                await asyncio.sleep(delay)
                return await self._generate_ai_message_with_retry(weather_context, retries + 1)
            else:
                logger.warning("AIメッセージ生成の最大リトライ回数に達しました。フォールバックメッセージを使用します")
                return self.ai_service._get_fallback_message(weather_context, "general")
    
    async def _send_weather_dm_with_retry(self, user_id: int, weather_data, ai_message: str, retries: int = 0) -> bool:
        """
        リトライ機能付きでDMを送信
        
        Args:
            user_id: DiscordユーザーID
            weather_data: 天気データ
            ai_message: AIメッセージ
            retries: 現在のリトライ回数
            
        Returns:
            送信成功時はTrue
        """
        try:
            # Discordユーザーを取得
            user = await self.bot_client.fetch_user(user_id)
            if not user:
                logger.error(f"Discordユーザーが見つかりません: {user_id}")
                return False
            
            # AIメッセージが長すぎる場合は切り詰める
            if ai_message and len(ai_message) > 1000:
                ai_message = WeatherEmbedBuilder.truncate_field_value(ai_message, 1000)
            
            # Embedメッセージを作成
            embed = WeatherEmbedBuilder.create_current_weather_embed(weather_data, ai_message)
            embed = WeatherEmbedBuilder.validate_embed_limits(embed)
            
            # DMを送信
            await user.send(embed=embed)
            logger.debug(f"DM送信成功: ユーザー {user_id}")
            return True
            
        except discord.Forbidden:
            logger.warning(f"ユーザー {user_id} にDMを送信する権限がありません")
            return False
            
        except discord.NotFound:
            logger.warning(f"ユーザー {user_id} が見つかりません")
            return False
            
        except discord.HTTPException as e:
            logger.warning(f"DM送信エラー (試行 {retries + 1}/{self.MAX_RETRIES}): ユーザー {user_id} - {str(e)}")
            
            if retries < self.MAX_RETRIES - 1:
                delay = self.RETRY_DELAY * (self.BACKOFF_FACTOR ** retries)
                logger.info(f"DM送信をリトライします: {delay}秒後")
                await asyncio.sleep(delay)
                return await self._send_weather_dm_with_retry(user_id, weather_data, ai_message, retries + 1)
            else:
                logger.error(f"DM送信の最大リトライ回数に達しました: ユーザー {user_id}")
                return False
                
        except Exception as e:
            logger.error(f"DM送信中に予期しないエラーが発生しました: ユーザー {user_id} - {str(e)}")
            return False
    

    
    async def _send_location_setup_message(self, user_id: int) -> None:
        """
        位置情報設定を促すメッセージを送信
        
        Args:
            user_id: DiscordユーザーID
        """
        try:
            user = await self.bot_client.fetch_user(user_id)
            if user:
                embed = WeatherEmbedBuilder.create_error_embed(
                    "位置情報の設定が必要です",
                    "定時天気通知を受け取るには、まず位置情報を設定してください。\n\n"
                    "**設定方法:**\n"
                    "`/set-location <地域名>` コマンドを使用して位置を設定してください。\n\n"
                    "**例:**\n"
                    "`/set-location 東京都` または `/set-location 大阪府`",
                    "not_found"
                )
                
                await user.send(embed=embed)
                
        except Exception as e:
            logger.error(f"位置情報設定メッセージの送信に失敗しました: ユーザー {user_id} - {str(e)}")
    
    async def _send_error_message(self, user_id: int, error_message: str) -> None:
        """
        エラーメッセージを送信
        
        Args:
            user_id: DiscordユーザーID
            error_message: エラーメッセージ
        """
        try:
            user = await self.bot_client.fetch_user(user_id)
            if user:
                embed = WeatherEmbedBuilder.create_error_embed(
                    "天気情報の取得に失敗しました",
                    f"{error_message}\n\n"
                    "**対処方法:**\n"
                    "しばらく時間をおいてから再度お試しください。問題が続く場合は管理者にお問い合わせください。",
                    "api_error"
                )
                
                await user.send(embed=embed)
                
        except Exception as e:
            logger.error(f"エラーメッセージの送信に失敗しました: ユーザー {user_id} - {str(e)}")
    
    async def send_test_notification(self, user_id: int) -> bool:
        """
        テスト通知を送信（デバッグ用）
        
        Args:
            user_id: DiscordユーザーID
            
        Returns:
            送信成功時はTrue
        """
        logger.info(f"テスト通知を送信します: ユーザー {user_id}")
        return await self.send_scheduled_weather_update(user_id)
    
    async def get_notification_stats(self) -> Dict[str, Any]:
        """
        通知サービスの統計情報を取得
        
        Returns:
            統計情報の辞書
        """
        try:
            # 通知有効ユーザー数を取得
            enabled_users = await self.user_service.get_users_with_notifications_enabled()
            
            return {
                "enabled_users_count": len(enabled_users),
                "weather_service_available": self.weather_service is not None,
                "ai_service_available": self.ai_service.is_available() if self.ai_service else False,
                "bot_client_available": self.bot_client is not None,
                "last_check": datetime.now().isoformat()
            }
            
        except Exception as e:
            logger.error(f"通知統計情報の取得に失敗しました: {str(e)}")
            return {
                "error": str(e),
                "last_check": datetime.now().isoformat()
            }