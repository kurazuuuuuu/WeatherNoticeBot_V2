"""ユーザー設定関連のDiscordコマンド"""

import discord
from discord.ext import commands
from discord import app_commands
from src.utils.logging import logger
from src.services.weather_service import WeatherService, WeatherAPIError
from src.services.user_service import user_service
from src.utils.embed_utils import WeatherEmbedBuilder


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
                embed = WeatherEmbedBuilder.create_error_embed(
                    "地域が見つかりません",
                    f"「{area}」に該当する地域が見つかりませんでした。\n"
                    "正確な地域名（例：東京都、大阪府、札幌市など）を入力してください。",
                    "not_found"
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
                description = f"地域を「{selected_area.name}」に設定しました。"
                
                # 複数の候補があった場合は他の候補も表示
                if len(area_matches) > 1:
                    other_matches = [match.name for match in area_matches[1:6]]  # 最大5つまで
                    description += f"\n\n**その他の候補:**\n" + "\n".join(other_matches)
                    description += "\n\n別の地域を設定したい場合は、再度コマンドを実行してください。"
                
                embed = WeatherEmbedBuilder.create_success_embed(
                    "地域設定完了",
                    description
                )
                await interaction.followup.send(embed=embed)
            else:
                embed = WeatherEmbedBuilder.create_error_embed(
                    "設定エラー",
                    "地域設定の保存に失敗しました。しばらく時間をおいてからお試しください。",
                    "general"
                )
                await interaction.followup.send(embed=embed)
            
        except WeatherAPIError as e:
            logger.error(f"地域検索API呼び出しエラー: {e}")
            embed = WeatherEmbedBuilder.create_error_embed(
                "API エラー",
                "地域情報の取得中にエラーが発生しました。しばらく時間をおいてからお試しください。",
                "api_error"
            )
            await interaction.followup.send(embed=embed)
        except Exception as e:
            logger.error(f"set-locationコマンドでエラーが発生しました: {e}")
            embed = WeatherEmbedBuilder.create_error_embed(
                "システムエラー",
                "地域設定中にエラーが発生しました。",
                "general"
            )
            await interaction.followup.send(embed=embed)
    
    @app_commands.command(name="schedule-weather", description="定時天気通知を設定します")
    @app_commands.describe(hour="通知時間（0-23時で指定）")
    async def schedule_weather(self, interaction: discord.Interaction, hour: int):
        """定時通知を設定するコマンド"""
        await interaction.response.defer()
        
        try:
            if not (0 <= hour <= 23):
                embed = WeatherEmbedBuilder.create_error_embed(
                    "無効な時間",
                    "時間は0から23の間で指定してください。\n例：`/schedule-weather hour:9` （午前9時に通知）",
                    "general"
                )
                await interaction.followup.send(embed=embed)
                return
            
            # ユーザーの位置情報が設定されているかチェック
            user_location = await user_service.get_user_location(interaction.user.id)
            if not user_location:
                embed = WeatherEmbedBuilder.create_error_embed(
                    "地域未設定",
                    "通知を設定する前に、まず地域を設定してください。\n"
                    "`/set-location` コマンドで地域を設定できます。",
                    "not_found"
                )
                await interaction.followup.send(embed=embed)
                return
            
            # 通知スケジュールを設定
            success = await user_service.set_notification_schedule(interaction.user.id, hour)
            
            if success:
                embed = WeatherEmbedBuilder.create_success_embed(
                    "通知設定完了",
                    f"毎日 {hour:02d}:00 に天気情報をDMでお送りします。\n\n"
                    f"**設定地域:** {user_location[1]}\n"
                    f"**通知時間:** {hour:02d}:00\n\n"
                    "**重要:** DMを受信するには以下の条件が必要です：\n"
                    "• Discordの「プライバシー・安全」設定でDMを許可する\n"
                    "• ボットと共通のサーバーに参加している\n"
                    "• ボットをブロックしていない\n\n"
                    "通知が届くかテストしたい場合は `/test-notification` コマンドをお試しください。\n"
                    "通知を停止したい場合は `/unschedule-weather` コマンドを使用してください。"
                )
                await interaction.followup.send(embed=embed)
            else:
                embed = WeatherEmbedBuilder.create_error_embed(
                    "設定エラー",
                    "通知設定の保存に失敗しました。しばらく時間をおいてからお試しください。",
                    "general"
                )
                await interaction.followup.send(embed=embed)
            
        except Exception as e:
            logger.error(f"schedule-weatherコマンドでエラーが発生しました: {e}")
            embed = WeatherEmbedBuilder.create_error_embed(
                "システムエラー",
                "通知設定中にエラーが発生しました。",
                "general"
            )
            await interaction.followup.send(embed=embed)
    
    @app_commands.command(name="unschedule-weather", description="定時天気通知を停止します")
    async def unschedule_weather(self, interaction: discord.Interaction):
        """定時通知を停止するコマンド"""
        await interaction.response.defer()
        
        try:
            # 現在の設定を確認
            user_settings = await user_service.get_user_settings(interaction.user.id)
            if not user_settings or not user_settings.get('is_notification_enabled'):
                embed = WeatherEmbedBuilder.create_error_embed(
                    "通知未設定",
                    "現在、定時通知は設定されていません。",
                    "not_found"
                )
                await interaction.followup.send(embed=embed)
                return
            
            # 通知を無効化
            success = await user_service.disable_notifications(interaction.user.id)
            
            if success:
                embed = WeatherEmbedBuilder.create_success_embed(
                    "通知停止完了",
                    f"定時天気通知を停止しました。\n\n"
                    f"**停止前の設定:**\n"
                    f"地域: {user_settings.get('area_name', '未設定')}\n"
                    f"通知時間: {user_settings.get('notification_hour', 0):02d}:00\n\n"
                    "再度通知を設定したい場合は `/schedule-weather` コマンドを使用してください。"
                )
                await interaction.followup.send(embed=embed)
            else:
                embed = WeatherEmbedBuilder.create_error_embed(
                    "停止エラー",
                    "通知停止の処理に失敗しました。しばらく時間をおいてからお試しください。",
                    "general"
                )
                await interaction.followup.send(embed=embed)
            
        except Exception as e:
            logger.error(f"unschedule-weatherコマンドでエラーが発生しました: {e}")
            embed = WeatherEmbedBuilder.create_error_embed(
                "システムエラー",
                "通知停止中にエラーが発生しました。",
                "general"
            )
            await interaction.followup.send(embed=embed)
    
    @app_commands.command(name="test-notification", description="定時通知のテスト送信を行います")
    async def test_notification(self, interaction: discord.Interaction):
        """テスト通知を送信するコマンド"""
        await interaction.response.defer()
        
        try:
            # ユーザーの位置情報が設定されているかチェック
            user_location = await user_service.get_user_location(interaction.user.id)
            if not user_location:
                embed = WeatherEmbedBuilder.create_error_embed(
                    "地域未設定",
                    "テスト通知を送信する前に、まず地域を設定してください。\n"
                    "`/set-location` コマンドで地域を設定できます。",
                    "not_found"
                )
                await interaction.followup.send(embed=embed)
                return
            
            # 通知サービスを取得
            from src.services.scheduler_service import get_scheduler_service
            scheduler_service = get_scheduler_service()
            
            if not scheduler_service or not scheduler_service.notification_service:
                embed = WeatherEmbedBuilder.create_error_embed(
                    "サービス未初期化",
                    "通知サービスが初期化されていません。管理者にお問い合わせください。",
                    "general"
                )
                await interaction.followup.send(embed=embed)
                return
            
            # テスト通知を送信
            success = await scheduler_service.notification_service.send_test_notification(interaction.user.id)
            
            if success:
                embed = WeatherEmbedBuilder.create_success_embed(
                    "テスト通知送信完了",
                    f"テスト通知をDMで送信しました。\n\n"
                    f"**設定地域:** {user_location[1]}\n\n"
                    "DMが届かない場合は、以下を確認してください：\n"
                    "• DMの受信設定が有効になっているか\n"
                    "• ボットと共通のサーバーに参加しているか\n"
                    "• ボットをブロックしていないか"
                )
                await interaction.followup.send(embed=embed)
            else:
                embed = WeatherEmbedBuilder.create_error_embed(
                    "テスト通知送信失敗",
                    "テスト通知の送信に失敗しました。\n\n"
                    "**考えられる原因:**\n"
                    "• DMの受信設定が無効になっている\n"
                    "• ボットと共通のサーバーに参加していない\n"
                    "• ボットがブロックされている\n"
                    "• 一時的なDiscord APIの問題\n\n"
                    "**対処方法:**\n"
                    "1. Discordの「プライバシー・安全」設定でDMを許可する\n"
                    "2. ボットが参加しているサーバーに参加する\n"
                    "3. しばらく時間をおいてから再試行する",
                    "general"
                )
                await interaction.followup.send(embed=embed)
            
        except Exception as e:
            logger.error(f"test-notificationコマンドでエラーが発生しました: {e}")
            embed = WeatherEmbedBuilder.create_error_embed(
                "システムエラー",
                "テスト通知送信中にエラーが発生しました。",
                "general"
            )
            await interaction.followup.send(embed=embed)

    @app_commands.command(name="my-settings", description="現在のユーザー設定を表示します")
    async def my_settings(self, interaction: discord.Interaction):
        """ユーザー設定を表示するコマンド"""
        await interaction.response.defer()
        
        try:
            # ユーザー設定を取得
            user_settings = await user_service.get_user_settings(interaction.user.id)
            
            if not user_settings:
                embed = WeatherEmbedBuilder.create_error_embed(
                    "設定なし",
                    "まだ設定が登録されていません。\n"
                    "`/set-location` コマンドで地域を設定してください。",
                    "not_found"
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
                name="🔧 利用可能なコマンド",
                value="• `/set-location` - 地域設定\n"
                      "• `/schedule-weather` - 通知設定\n"
                      "• `/unschedule-weather` - 通知停止\n"
                      "• `/test-notification` - テスト通知送信",
                inline=False
            )
            
            embed.set_footer(text="設定を変更したい場合は、上記のコマンドをご利用ください。")
            await interaction.followup.send(embed=embed)
            
        except Exception as e:
            logger.error(f"my-settingsコマンドでエラーが発生しました: {e}")
            embed = WeatherEmbedBuilder.create_error_embed(
                "システムエラー",
                "設定表示中にエラーが発生しました。",
                "general"
            )
            await interaction.followup.send(embed=embed)


async def setup(bot):
    """Cogをボットに追加"""
    await bot.add_cog(UserCommands(bot))