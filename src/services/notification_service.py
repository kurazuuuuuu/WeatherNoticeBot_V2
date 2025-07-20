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
            
            # Embedメッセージを作成
            embed = self._create_weather_embed(weather_data, ai_message)
            
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
    
    def _create_weather_embed(self, weather_data, ai_message: str) -> discord.Embed:
        """
        天気情報のDiscord Embedを作成
        
        Args:
            weather_data: 天気データ
            ai_message: AIメッセージ
            
        Returns:
            Discord Embed
        """
        # 天気に応じた色を設定
        color = self._get_weather_color(weather_data.weather_description)
        
        # Embedを作成
        embed = discord.Embed(
            title=f"🌤️ {weather_data.area_name}の天気情報",
            description=ai_message,
            color=color,
            timestamp=datetime.now()
        )
        
        # 天気情報フィールドを追加
        embed.add_field(
            name="☀️ 天気",
            value=weather_data.weather_description,
            inline=True
        )
        
        if weather_data.temperature is not None:
            embed.add_field(
                name="🌡️ 気温",
                value=f"{weather_data.temperature}°C",
                inline=True
            )
        
        embed.add_field(
            name="☔ 降水確率",
            value=f"{weather_data.precipitation_probability}%",
            inline=True
        )
        
        if weather_data.wind:
            embed.add_field(
                name="💨 風",
                value=weather_data.wind,
                inline=True
            )
        
        # 発表時刻を追加
        embed.add_field(
            name="📅 発表時刻",
            value=weather_data.publish_time.strftime("%Y年%m月%d日 %H時%M分"),
            inline=False
        )
        
        # フッターを設定
        embed.set_footer(text="気象庁データより | 定時天気通知")
        
        return embed
    
    def _get_weather_color(self, weather_description: str) -> int:
        """
        天気説明に基づいてEmbedの色を決定
        
        Args:
            weather_description: 天気説明
            
        Returns:
            色コード（整数）
        """
        weather_lower = weather_description.lower()
        
        # 晴れ系
        if "晴" in weather_lower:
            return 0xFFD700  # ゴールド
        
        # 雨系
        elif "雨" in weather_lower or "雷" in weather_lower:
            return 0x4682B4  # スチールブルー
        
        # 雪系
        elif "雪" in weather_lower:
            return 0xF0F8FF  # アリスブルー
        
        # 曇り系
        elif "曇" in weather_lower or "くもり" in weather_lower:
            return 0x708090  # スレートグレー
        
        # デフォルト
        else:
            return 0x87CEEB  # スカイブルー
    
    async def _send_location_setup_message(self, user_id: int) -> None:
        """
        位置情報設定を促すメッセージを送信
        
        Args:
            user_id: DiscordユーザーID
        """
        try:
            user = await self.bot_client.fetch_user(user_id)
            if user:
                embed = discord.Embed(
                    title="📍 位置情報の設定が必要です",
                    description="定時天気通知を受け取るには、まず位置情報を設定してください。",
                    color=0xFFA500  # オレンジ
                )
                embed.add_field(
                    name="設定方法",
                    value="`/set-location <地域名>` コマンドを使用して位置を設定してください。",
                    inline=False
                )
                embed.add_field(
                    name="例",
                    value="`/set-location 東京都` または `/set-location 大阪府`",
                    inline=False
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
                embed = discord.Embed(
                    title="⚠️ 天気情報の取得に失敗しました",
                    description=error_message,
                    color=0xFF6B6B  # 赤
                )
                embed.add_field(
                    name="対処方法",
                    value="しばらく時間をおいてから再度お試しください。問題が続く場合は管理者にお問い合わせください。",
                    inline=False
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