"""天気情報関連のDiscordコマンド"""

import discord
from discord.ext import commands
from discord import app_commands
from src.utils.logging import logger
from src.services.weather_service import WeatherService, WeatherAPIError
from src.services.user_service import user_service
from src.services.ai_service import AIMessageService


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
                await interaction.followup.send(
                    "地域が指定されていないか、無効な地域名です。\n"
                    "`/set-location` コマンドで地域を設定するか、有効な地域名を指定してください。"
                )
                return
            
            # 天気情報を取得
            async with self.weather_service:
                weather_data = await self.weather_service.get_current_weather(area_code)
                
            if not weather_data:
                await interaction.followup.send("天気情報を取得できませんでした。後でもう一度お試しください。")
                return
            
            # AIメッセージを生成
            ai_message = await self._generate_ai_message(weather_data)
            
            # Embedを作成
            embed = await self._create_weather_embed(weather_data, ai_message)
            await interaction.followup.send(embed=embed)
            
        except WeatherAPIError as e:
            logger.error(f"天気API呼び出しエラー: {e}")
            await interaction.followup.send("天気情報の取得中にエラーが発生しました。しばらく時間をおいてからお試しください。")
        except Exception as e:
            logger.error(f"weatherコマンドでエラーが発生しました: {e}")
            await interaction.followup.send("天気情報の取得中にエラーが発生しました。")
    
    @app_commands.command(name="forecast", description="指定した地域の天気予報を取得します")
    @app_commands.describe(location="天気予報を取得したい地域名（省略時は登録済みの地域を使用）")
    async def forecast(self, interaction: discord.Interaction, location: str = None):
        """天気予報を取得するコマンド"""
        await interaction.response.defer()
        
        try:
            # 地域コードを取得
            area_code = await self._get_area_code(interaction.user.id, location)
            if not area_code:
                await interaction.followup.send(
                    "地域が指定されていないか、無効な地域名です。\n"
                    "`/set-location` コマンドで地域を設定するか、有効な地域名を指定してください。"
                )
                return
            
            # 天気予報を取得（5日間）
            async with self.weather_service:
                forecast_data = await self.weather_service.get_forecast(area_code, days=5)
                
            if not forecast_data:
                await interaction.followup.send("天気予報を取得できませんでした。後でもう一度お試しください。")
                return
            
            # Embedを作成
            embed = await self._create_forecast_embed(forecast_data, area_code)
            await interaction.followup.send(embed=embed)
            
        except WeatherAPIError as e:
            logger.error(f"天気予報API呼び出しエラー: {e}")
            await interaction.followup.send("天気予報の取得中にエラーが発生しました。しばらく時間をおいてからお試しください。")
        except Exception as e:
            logger.error(f"forecastコマンドでエラーが発生しました: {e}")
            await interaction.followup.send("天気予報の取得中にエラーが発生しました。")
    
    @app_commands.command(name="weather-alerts", description="指定した地域の気象警報・注意報を取得します")
    @app_commands.describe(location="気象警報を取得したい地域名（省略時は登録済みの地域を使用）")
    async def weather_alerts(self, interaction: discord.Interaction, location: str = None):
        """気象警報・注意報を取得するコマンド"""
        await interaction.response.defer()
        
        try:
            # 地域コードを取得
            area_code = await self._get_area_code(interaction.user.id, location)
            if not area_code:
                await interaction.followup.send(
                    "地域が指定されていないか、無効な地域名です。\n"
                    "`/set-location` コマンドで地域を設定するか、有効な地域名を指定してください。"
                )
                return
            
            # 気象警報を取得
            async with self.weather_service:
                alerts = await self.weather_service.get_weather_alerts(area_code)
                
            # Embedを作成
            embed = await self._create_alerts_embed(alerts, area_code)
            await interaction.followup.send(embed=embed)
            
        except WeatherAPIError as e:
            logger.error(f"気象警報API呼び出しエラー: {e}")
            await interaction.followup.send("気象警報の取得中にエラーが発生しました。しばらく時間をおいてからお試しください。")
        except Exception as e:
            logger.error(f"weather-alertsコマンドでエラーが発生しました: {e}")
            await interaction.followup.send("気象警報の取得中にエラーが発生しました。")
    
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
        # 天気に応じた色を設定
        color = self._get_weather_color(weather_data.weather_code)
        
        embed = discord.Embed(
            title=f"🌤️ {weather_data.area_name} の天気",
            description=ai_message,
            color=color,
            timestamp=weather_data.publish_time
        )
        
        # 天気情報フィールドを追加
        embed.add_field(
            name="☁️ 天気",
            value=f"{self._get_weather_emoji(weather_data.weather_code)} {weather_data.weather_description}",
            inline=True
        )
        
        if weather_data.temperature is not None:
            embed.add_field(
                name="🌡️ 気温",
                value=f"{weather_data.temperature}°C",
                inline=True
            )
        
        if weather_data.precipitation_probability > 0:
            embed.add_field(
                name="☔ 降水確率",
                value=f"{weather_data.precipitation_probability}%",
                inline=True
            )
        
        if weather_data.wind:
            embed.add_field(
                name="💨 風",
                value=weather_data.wind,
                inline=False
            )
        
        if weather_data.wave:
            embed.add_field(
                name="🌊 波",
                value=weather_data.wave,
                inline=False
            )
        
        embed.set_footer(text="気象庁データ")
        return embed
    
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
        
        embed = discord.Embed(
            title=f"📅 {area_name} の天気予報",
            description="5日間の天気予報をお知らせします",
            color=discord.Color.green()
        )
        
        for i, forecast in enumerate(forecast_data[:5]):  # 最大5日分
            date_str = forecast.date.strftime("%m/%d (%a)")
            weather_emoji = self._get_weather_emoji(forecast.weather_code)
            
            # 気温情報を構築
            temp_info = []
            if forecast.temp_max is not None:
                temp_info.append(f"最高 {forecast.temp_max}°C")
            if forecast.temp_min is not None:
                temp_info.append(f"最低 {forecast.temp_min}°C")
            
            temp_str = " / ".join(temp_info) if temp_info else "気温情報なし"
            
            # 降水確率
            pop_str = f"降水確率 {forecast.precipitation_probability}%" if forecast.precipitation_probability > 0 else ""
            
            field_value = f"{weather_emoji} {forecast.weather_description}\n{temp_str}"
            if pop_str:
                field_value += f"\n{pop_str}"
            
            embed.add_field(
                name=date_str,
                value=field_value,
                inline=True
            )
            
            # 3つごとに改行を入れる
            if (i + 1) % 3 == 0:
                embed.add_field(name="\u200b", value="\u200b", inline=False)
        
        embed.set_footer(text="気象庁データ")
        return embed
    
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
        
        if not alerts:
            embed = discord.Embed(
                title=f"✅ {area_name} の気象警報・注意報",
                description="現在、発表されている気象警報・注意報はありません。",
                color=discord.Color.green()
            )
        else:
            # 重要度に応じて色を設定
            max_severity = max(alert.severity for alert in alerts)
            if max_severity == "高":
                color = discord.Color.red()
                title_emoji = "🚨"
            elif max_severity == "中":
                color = discord.Color.orange()
                title_emoji = "⚠️"
            else:
                color = discord.Color.yellow()
                title_emoji = "⚡"
            
            embed = discord.Embed(
                title=f"{title_emoji} {area_name} の気象警報・注意報",
                description=f"{len(alerts)}件の警報・注意報が発表されています。",
                color=color
            )
            
            for i, alert in enumerate(alerts[:10]):  # 最大10件まで表示
                severity_emoji = "🚨" if alert.severity == "高" else "⚠️" if alert.severity == "中" else "⚡"
                issued_time = alert.issued_at.strftime("%m/%d %H:%M")
                
                embed.add_field(
                    name=f"{severity_emoji} {alert.title}",
                    value=f"{alert.description}\n発表: {issued_time}",
                    inline=False
                )
        
        embed.set_footer(text="気象庁データ")
        return embed
    
    def _get_weather_emoji(self, weather_code: str) -> str:
        """天気コードに対応する絵文字を取得"""
        if not weather_code:
            return "❓"
        
        # 天気コードの最初の桁で大まかな天気を判定
        first_digit = weather_code[0] if weather_code else "0"
        
        emoji_map = {
            "1": "☀️",  # 晴れ
            "2": "☁️",  # くもり
            "3": "🌧️",  # 雨
            "4": "❄️",  # 雪
        }
        
        return emoji_map.get(first_digit, "🌤️")
    
    def _get_weather_color(self, weather_code: str) -> discord.Color:
        """天気コードに対応する色を取得"""
        if not weather_code:
            return discord.Color.blue()
        
        # 天気コードの最初の桁で大まかな天気を判定
        first_digit = weather_code[0] if weather_code else "0"
        
        color_map = {
            "1": discord.Color.gold(),      # 晴れ - 金色
            "2": discord.Color.light_grey(), # くもり - 薄いグレー
            "3": discord.Color.blue(),      # 雨 - 青
            "4": discord.Color.lighter_grey(), # 雪 - より薄いグレー
        }
        
        return color_map.get(first_digit, discord.Color.blue())


async def setup(bot):
    """Cogをボットに追加"""
    await bot.add_cog(WeatherCommands(bot))