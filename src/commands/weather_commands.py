"""天気情報関連のDiscordコマンド"""

import discord
from discord.ext import commands
from discord import app_commands
from src.utils.logging import logger
from src.services.weather_service import WeatherService, WeatherAPIError
from src.services.user_service import user_service
from src.services.ai_service import AIMessageService
from src.utils.embed_utils import WeatherEmbedBuilder


class WeatherCommands(commands.Cog):
    """天気情報コマンドのCogクラス"""
    
    def __init__(self, bot):
        """WeatherCommandsを初期化"""
        self.bot = bot
        self.weather_service = WeatherService()
        self.ai_service = AIMessageService()
        logger.info("WeatherCommandsが初期化されました")
    
    @app_commands.command(name="weather", description="指定した地域の現在の天気情報を取得します")
    @app_commands.describe(location="天気情報を取得したい地域名（省略時は登録済みの地域を使用）")
    async def weather(self, interaction: discord.Interaction, location: str = None):
        """現在の天気情報を取得するコマンド"""
        await interaction.response.defer()
        
        try:
            # 地域コードを取得
            area_code = await self._get_area_code(interaction.user.id, location)
            if not area_code:
                suggestions = [
                    "`/set-location 東京都` で地域を設定",
                    "正確な地域名を指定（例：大阪府、札幌市）",
                    "`/my-settings` で現在の設定を確認"
                ]
                error_embed = WeatherEmbedBuilder.create_error_embed(
                    "地域情報エラー",
                    "地域が指定されていないか、無効な地域名です。",
                    "not_found",
                    details=f"指定された地域: {location}" if location else "地域が指定されていません",
                    suggestions=suggestions
                )
                await interaction.followup.send(embed=error_embed)
                return
            
            # 天気情報を取得
            async with self.weather_service:
                weather_data = await self.weather_service.get_current_weather(area_code)
                
            if not weather_data:
                suggestions = [
                    "数分後に再度お試しください",
                    "別の地域で試してみてください",
                    "管理者に問題を報告してください"
                ]
                error_embed = WeatherEmbedBuilder.create_error_embed(
                    "データ取得エラー",
                    "天気情報を取得できませんでした。",
                    "api_error",
                    details=f"地域コード: {area_code}",
                    suggestions=suggestions
                )
                await interaction.followup.send(embed=error_embed)
                return
            
            # AIメッセージを生成
            ai_message = await self._generate_ai_message(weather_data)
            
            # AIメッセージが長すぎる場合は切り詰める
            if ai_message and len(ai_message) > 1000:
                ai_message = WeatherEmbedBuilder.truncate_field_value(ai_message, 1000)
            
            # Embedを作成
            embed = await self._create_weather_embed(weather_data, ai_message)
            
            # Embedの制限を検証
            embed = WeatherEmbedBuilder.validate_embed_limits(embed)
            
            await interaction.followup.send(embed=embed)
            
        except WeatherAPIError as e:
            logger.error(f"天気API呼び出しエラー: {e}")
            error_embed = WeatherEmbedBuilder.create_error_embed(
                "API エラー",
                "天気情報の取得中にエラーが発生しました。しばらく時間をおいてからお試しください。",
                "api_error"
            )
            await interaction.followup.send(embed=error_embed)
        except Exception as e:
            logger.error(f"weatherコマンドでエラーが発生しました: {e}")
            error_embed = WeatherEmbedBuilder.create_error_embed(
                "システムエラー",
                "天気情報の取得中にエラーが発生しました。",
                "general"
            )
            await interaction.followup.send(embed=error_embed)
    
    @app_commands.command(name="forecast", description="指定した地域の天気予報を取得します")
    @app_commands.describe(location="天気予報を取得したい地域名（省略時は登録済みの地域を使用）")
    async def forecast(self, interaction: discord.Interaction, location: str = None):
        """天気予報を取得するコマンド"""
        await interaction.response.defer()
        
        try:
            # 地域コードを取得
            area_code = await self._get_area_code(interaction.user.id, location)
            if not area_code:
                error_embed = WeatherEmbedBuilder.create_error_embed(
                    "地域情報エラー",
                    "地域が指定されていないか、無効な地域名です。\n"
                    "`/set-location` コマンドで地域を設定するか、有効な地域名を指定してください。",
                    "not_found"
                )
                await interaction.followup.send(embed=error_embed)
                return
            
            # 天気予報を取得（5日間）
            async with self.weather_service:
                forecast_data = await self.weather_service.get_forecast(area_code, days=5)
                
            if not forecast_data:
                error_embed = WeatherEmbedBuilder.create_error_embed(
                    "データ取得エラー",
                    "天気予報を取得できませんでした。後でもう一度お試しください。",
                    "api_error"
                )
                await interaction.followup.send(embed=error_embed)
                return
            
            # 地域名を取得
            area_name = "指定地域"
            try:
                async with self.weather_service:
                    area_dict = await self.weather_service.get_area_list()
                    if area_code in area_dict:
                        area_name = area_dict[area_code].name
            except Exception:
                pass
            
            # AIメッセージを生成（予報用）
            ai_message = None
            try:
                if forecast_data:
                    # 予報データからコンテキストを作成してAIメッセージを生成
                    forecast_context = f"今後5日間の天気予報: {', '.join([f.weather_description for f in forecast_data[:5]])}"
                    ai_message = await self.ai_service.generate_positive_message(forecast_context)
                    
                    # AIメッセージが長すぎる場合は切り詰める
                    if ai_message and len(ai_message) > 800:
                        ai_message = WeatherEmbedBuilder.truncate_field_value(ai_message, 800)
            except Exception as e:
                logger.warning(f"予報用AIメッセージ生成に失敗しました: {e}")
            
            # 予報データが多い場合はページネーション
            if len(forecast_data) > 5:
                embeds = WeatherEmbedBuilder.create_paginated_forecast_embeds(
                    forecast_data, area_name, ai_message, items_per_page=3
                )
                # 各Embedの制限を検証
                embeds = [WeatherEmbedBuilder.validate_embed_limits(embed) for embed in embeds]
                
                # 最初のページを送信
                await interaction.followup.send(embed=embeds[0])
                
                # 追加のページがある場合は順次送信
                for embed in embeds[1:]:
                    await interaction.followup.send(embed=embed)
            else:
                # 通常の表示
                embed = await self._create_forecast_embed(forecast_data, area_code)
                embed = WeatherEmbedBuilder.validate_embed_limits(embed)
                await interaction.followup.send(embed=embed)
            
        except WeatherAPIError as e:
            logger.error(f"天気予報API呼び出しエラー: {e}")
            error_embed = WeatherEmbedBuilder.create_error_embed(
                "API エラー",
                "天気予報の取得中にエラーが発生しました。しばらく時間をおいてからお試しください。",
                "api_error"
            )
            await interaction.followup.send(embed=error_embed)
        except Exception as e:
            logger.error(f"forecastコマンドでエラーが発生しました: {e}")
            error_embed = WeatherEmbedBuilder.create_error_embed(
                "システムエラー",
                "天気予報の取得中にエラーが発生しました。",
                "general"
            )
            await interaction.followup.send(embed=error_embed)
    
    @app_commands.command(name="weather-alerts", description="指定した地域の気象警報・注意報を取得します")
    @app_commands.describe(location="気象警報を取得したい地域名（省略時は登録済みの地域を使用）")
    async def weather_alerts(self, interaction: discord.Interaction, location: str = None):
        """気象警報・注意報を取得するコマンド"""
        await interaction.response.defer()
        
        try:
            # 地域コードを取得
            area_code = await self._get_area_code(interaction.user.id, location)
            if not area_code:
                error_embed = WeatherEmbedBuilder.create_error_embed(
                    "地域情報エラー",
                    "地域が指定されていないか、無効な地域名です。\n"
                    "`/set-location` コマンドで地域を設定するか、有効な地域名を指定してください。",
                    "not_found"
                )
                await interaction.followup.send(embed=error_embed)
                return
            
            # 気象警報を取得
            async with self.weather_service:
                alerts = await self.weather_service.get_weather_alerts(area_code)
                
            # 警報が多い場合はページネーション
            if len(alerts) > 5:
                # 地域名を取得
                area_name = "指定地域"
                try:
                    async with self.weather_service:
                        area_dict = await self.weather_service.get_area_list()
                        if area_code in area_dict:
                            area_name = area_dict[area_code].name
                except Exception:
                    pass
                
                embeds = WeatherEmbedBuilder.create_paginated_alert_embeds(
                    alerts, area_name, items_per_page=5
                )
                # 最初のページを送信
                await interaction.followup.send(embed=embeds[0])
                
                # 追加のページがある場合は順次送信
                for embed in embeds[1:]:
                    await interaction.followup.send(embed=embed)
            else:
                # 通常の表示
                embed = await self._create_alerts_embed(alerts, area_code)
                await interaction.followup.send(embed=embed)
            
        except WeatherAPIError as e:
            logger.error(f"気象警報API呼び出しエラー: {e}")
            error_embed = WeatherEmbedBuilder.create_error_embed(
                "API エラー",
                "気象警報の取得中にエラーが発生しました。しばらく時間をおいてからお試しください。",
                "api_error"
            )
            await interaction.followup.send(embed=error_embed)
        except Exception as e:
            logger.error(f"weather-alertsコマンドでエラーが発生しました: {e}")
            error_embed = WeatherEmbedBuilder.create_error_embed(
                "システムエラー",
                "気象警報の取得中にエラーが発生しました。",
                "general"
            )
            await interaction.followup.send(embed=error_embed)
    
    async def _get_area_code(self, discord_id: int, location: str = None) -> str:
        """地域コードを取得するヘルパーメソッド"""
        try:
            if location:
                # 指定された地域名から地域コードを取得
                async with self.weather_service:
                    area_code = await self.weather_service.get_valid_area_code(location)
                return area_code
            else:
                # ユーザーの登録済み地域を取得
                user_location = await user_service.get_user_location(discord_id)
                if user_location:
                    return user_location[0]  # area_code
                return None
        except Exception as e:
            logger.error(f"地域コード取得エラー: {e}")
            return None
    
    async def _generate_ai_message(self, weather_data) -> str:
        """AIメッセージを生成するヘルパーメソッド"""
        try:
            from src.services.ai_service import weather_data_to_context
            weather_context = weather_data_to_context(weather_data)
            return await self.ai_service.generate_positive_message(weather_context)
        except Exception as e:
            logger.warning(f"AIメッセージ生成に失敗しました: {e}")
            # フォールバック用のデフォルトメッセージ
            return "今日も素敵な一日をお過ごしください！ ☀️"
    
    async def _create_weather_embed(self, weather_data, ai_message: str) -> discord.Embed:
        """現在の天気情報用のEmbedを作成"""
        return WeatherEmbedBuilder.create_current_weather_embed(weather_data, ai_message)
    
    async def _create_forecast_embed(self, forecast_data, area_code: str) -> discord.Embed:
        """天気予報用のEmbedを作成"""
        # 地域名を取得
        area_name = "指定地域"
        try:
            async with self.weather_service:
                area_dict = await self.weather_service.get_area_list()
                if area_code in area_dict:
                    area_name = area_dict[area_code].name
        except Exception:
            pass
        
        # AIメッセージを生成（予報用）
        ai_message = None
        try:
            if forecast_data:
                # 予報データからコンテキストを作成してAIメッセージを生成
                forecast_context = f"今後5日間の天気予報: {', '.join([f.weather_description for f in forecast_data[:5]])}"
                ai_message = await self.ai_service.generate_positive_message(forecast_context)
        except Exception as e:
            logger.warning(f"予報用AIメッセージ生成に失敗しました: {e}")
        
        return WeatherEmbedBuilder.create_forecast_embed(forecast_data, area_name, ai_message)
    
    async def _create_alerts_embed(self, alerts, area_code: str) -> discord.Embed:
        """気象警報用のEmbedを作成"""
        # 地域名を取得
        area_name = "指定地域"
        try:
            async with self.weather_service:
                area_dict = await self.weather_service.get_area_list()
                if area_code in area_dict:
                    area_name = area_dict[area_code].name
        except Exception:
            pass
        
        return WeatherEmbedBuilder.create_alert_embed(alerts, area_name)
    



async def setup(bot):
    """Cogをボットに追加"""
    await bot.add_cog(WeatherCommands(bot))