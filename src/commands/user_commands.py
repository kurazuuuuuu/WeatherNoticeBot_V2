"""ユーザー設定関連のDiscordコマンド"""

import discord
from discord.ext import commands
from discord import app_commands
from src.utils.logging import logger
from src.services.weather_service import WeatherService, WeatherAPIError
from src.services.user_service import user_service


class UserCommands(commands.Cog):
    """ユーザー設定コマンドのCogクラス"""
    
    def __init__(self, bot):
        """UserCommandsを初期化"""
        self.bot = bot
        self.weather_service = WeatherService()
        logger.info("UserCommandsが初期化されました")
    
    @app_commands.command(name="set-location", description="天気情報を取得する地域を設定します")
    @app_commands.describe(area="設定したい地域名（例：東京都、大阪府など）")
    async def set_location(self, interaction: discord.Interaction, area: str):
        """ユーザーの位置を設定するコマンド"""
        await interaction.response.defer()
        
        try:
            # 地域名から地域コードを検索
            async with self.weather_service:
                area_matches = await self.weather_service.search_area_by_name(area)
            
            if not area_matches:
                embed = discord.Embed(
                    title="❌ 地域が見つかりません",
                    description=f"「{area}」に該当する地域が見つかりませんでした。\n"
                               "正確な地域名（例：東京都、大阪府、札幌市など）を入力してください。",
                    color=discord.Color.red()
                )
                await interaction.followup.send(embed=embed)
                return
            
            # 複数の候補がある場合は最初のマッチを使用
            selected_area = area_matches[0]
            
            # ユーザーの位置情報を保存
            success = await user_service.set_user_location(
                interaction.user.id,
                selected_area.code,
                selected_area.name
            )
            
            if success:
                embed = discord.Embed(
                    title="✅ 地域設定完了",
                    description=f"地域を「{selected_area.name}」に設定しました。",
                    color=discord.Color.green()
                )
                
                # 複数の候補があった場合は他の候補も表示
                if len(area_matches) > 1:
                    other_matches = [match.name for match in area_matches[1:6]]  # 最大5つまで
                    embed.add_field(
                        name="その他の候補",
                        value="\n".join(other_matches),
                        inline=False
                    )
                    embed.set_footer(text="別の地域を設定したい場合は、再度コマンドを実行してください。")
                
                await interaction.followup.send(embed=embed)
            else:
                embed = discord.Embed(
                    title="❌ 設定エラー",
                    description="地域設定の保存に失敗しました。しばらく時間をおいてからお試しください。",
                    color=discord.Color.red()
                )
                await interaction.followup.send(embed=embed)
            
        except WeatherAPIError as e:
            logger.error(f"地域検索API呼び出しエラー: {e}")
            await interaction.followup.send("地域情報の取得中にエラーが発生しました。しばらく時間をおいてからお試しください。")
        except Exception as e:
            logger.error(f"set-locationコマンドでエラーが発生しました: {e}")
            await interaction.followup.send("地域設定中にエラーが発生しました。")
    
    @app_commands.command(name="schedule-weather", description="定時天気通知を設定します")
    @app_commands.describe(hour="通知時間（0-23時で指定）")
    async def schedule_weather(self, interaction: discord.Interaction, hour: int):
        """定時通知を設定するコマンド"""
        await interaction.response.defer()
        
        try:
            if not (0 <= hour <= 23):
                embed = discord.Embed(
                    title="❌ 無効な時間",
                    description="時間は0から23の間で指定してください。\n例：`/schedule-weather hour:9` （午前9時に通知）",
                    color=discord.Color.red()
                )
                await interaction.followup.send(embed=embed)
                return
            
            # ユーザーの位置情報が設定されているかチェック
            user_location = await user_service.get_user_location(interaction.user.id)
            if not user_location:
                embed = discord.Embed(
                    title="❌ 地域未設定",
                    description="通知を設定する前に、まず地域を設定してください。\n"
                               "`/set-location` コマンドで地域を設定できます。",
                    color=discord.Color.red()
                )
                await interaction.followup.send(embed=embed)
                return
            
            # 通知スケジュールを設定
            success = await user_service.set_notification_schedule(interaction.user.id, hour)
            
            if success:
                embed = discord.Embed(
                    title="✅ 通知設定完了",
                    description=f"毎日 {hour:02d}:00 に天気情報をDMでお送りします。",
                    color=discord.Color.green()
                )
                embed.add_field(
                    name="設定地域",
                    value=user_location[1],  # area_name
                    inline=True
                )
                embed.add_field(
                    name="通知時間",
                    value=f"{hour:02d}:00",
                    inline=True
                )
                embed.set_footer(text="通知を停止したい場合は /unschedule-weather コマンドを使用してください。")
                await interaction.followup.send(embed=embed)
            else:
                embed = discord.Embed(
                    title="❌ 設定エラー",
                    description="通知設定の保存に失敗しました。しばらく時間をおいてからお試しください。",
                    color=discord.Color.red()
                )
                await interaction.followup.send(embed=embed)
            
        except Exception as e:
            logger.error(f"schedule-weatherコマンドでエラーが発生しました: {e}")
            await interaction.followup.send("通知設定中にエラーが発生しました。")
    
    @app_commands.command(name="unschedule-weather", description="定時天気通知を停止します")
    async def unschedule_weather(self, interaction: discord.Interaction):
        """定時通知を停止するコマンド"""
        await interaction.response.defer()
        
        try:
            # 現在の設定を確認
            user_settings = await user_service.get_user_settings(interaction.user.id)
            if not user_settings or not user_settings.get('is_notification_enabled'):
                embed = discord.Embed(
                    title="ℹ️ 通知未設定",
                    description="現在、定時通知は設定されていません。",
                    color=discord.Color.blue()
                )
                await interaction.followup.send(embed=embed)
                return
            
            # 通知を無効化
            success = await user_service.disable_notifications(interaction.user.id)
            
            if success:
                embed = discord.Embed(
                    title="✅ 通知停止完了",
                    description="定時天気通知を停止しました。",
                    color=discord.Color.green()
                )
                embed.add_field(
                    name="停止前の設定",
                    value=f"地域: {user_settings.get('area_name', '未設定')}\n"
                          f"通知時間: {user_settings.get('notification_hour', 0):02d}:00",
                    inline=False
                )
                embed.set_footer(text="再度通知を設定したい場合は /schedule-weather コマンドを使用してください。")
                await interaction.followup.send(embed=embed)
            else:
                embed = discord.Embed(
                    title="❌ 停止エラー",
                    description="通知停止の処理に失敗しました。しばらく時間をおいてからお試しください。",
                    color=discord.Color.red()
                )
                await interaction.followup.send(embed=embed)
            
        except Exception as e:
            logger.error(f"unschedule-weatherコマンドでエラーが発生しました: {e}")
            await interaction.followup.send("通知停止中にエラーが発生しました。")
    
    @app_commands.command(name="my-settings", description="現在のユーザー設定を表示します")
    async def my_settings(self, interaction: discord.Interaction):
        """ユーザー設定を表示するコマンド"""
        await interaction.response.defer()
        
        try:
            # ユーザー設定を取得
            user_settings = await user_service.get_user_settings(interaction.user.id)
            
            if not user_settings:
                embed = discord.Embed(
                    title="ℹ️ 設定なし",
                    description="まだ設定が登録されていません。\n"
                               "`/set-location` コマンドで地域を設定してください。",
                    color=discord.Color.blue()
                )
                await interaction.followup.send(embed=embed)
                return
            
            # 設定情報を表示するEmbedを作成
            embed = discord.Embed(
                title="⚙️ あなたの設定",
                description=f"<@{interaction.user.id}> さんの現在の設定です",
                color=discord.Color.purple()
            )
            
            # 地域設定
            if user_settings.get('has_location'):
                embed.add_field(
                    name="📍 設定地域",
                    value=f"{user_settings.get('area_name', '未設定')}\n"
                          f"地域コード: {user_settings.get('area_code', '未設定')}",
                    inline=False
                )
            else:
                embed.add_field(
                    name="📍 設定地域",
                    value="未設定\n`/set-location` コマンドで設定してください",
                    inline=False
                )
            
            # 通知設定
            if user_settings.get('has_notification_enabled'):
                notification_hour = user_settings.get('notification_hour', 0)
                embed.add_field(
                    name="⏰ 定時通知",
                    value=f"有効 - 毎日 {notification_hour:02d}:00 にDM通知\n"
                          f"タイムゾーン: {user_settings.get('timezone', 'Asia/Tokyo')}",
                    inline=False
                )
            else:
                embed.add_field(
                    name="⏰ 定時通知",
                    value="無効\n`/schedule-weather` コマンドで設定してください",
                    inline=False
                )
            
            # アカウント情報
            created_at = user_settings.get('created_at')
            updated_at = user_settings.get('updated_at')
            
            if created_at:
                embed.add_field(
                    name="📅 登録日時",
                    value=created_at.strftime("%Y年%m月%d日 %H:%M"),
                    inline=True
                )
            
            if updated_at:
                embed.add_field(
                    name="🔄 最終更新",
                    value=updated_at.strftime("%Y年%m月%d日 %H:%M"),
                    inline=True
                )
            
            # 利用可能なコマンドの案内
            embed.add_field(
                name="🔧 設定変更コマンド",
                value="• `/set-location` - 地域設定\n"
                      "• `/schedule-weather` - 通知設定\n"
                      "• `/unschedule-weather` - 通知停止",
                inline=False
            )
            
            embed.set_footer(text="設定を変更したい場合は、上記のコマンドをご利用ください。")
            await interaction.followup.send(embed=embed)
            
        except Exception as e:
            logger.error(f"my-settingsコマンドでエラーが発生しました: {e}")
            await interaction.followup.send("設定表示中にエラーが発生しました。")


async def setup(bot):
    """Cogをボットに追加"""
    await bot.add_cog(UserCommands(bot))