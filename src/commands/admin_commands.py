"""管理者用のDiscordコマンド"""

import discord
import time
from discord.ext import commands
from discord import app_commands
from typing import Optional
from src.utils.logging import logger
from src.utils.embed_utils import WeatherEmbedBuilder
from src.services.server_config_service import ServerConfigService
from src.services.stats_service import StatsService
from src.services.weather_service import WeatherService


class AdminCommands(commands.Cog):
    """管理者コマンドのCogクラス"""
    
    def __init__(self, bot):
        """AdminCommandsを初期化"""
        self.bot = bot
        self.weather_service = WeatherService()
        logger.info("AdminCommandsが初期化されました")
    
    @app_commands.command(name="weather-config", description="サーバーの天気ボット設定を管理します（管理者専用）")
    @app_commands.describe(
        action="実行するアクション",
        default_area="サーバーのデフォルト地域",
        weather_enabled="天気機能の有効/無効",
        ai_enabled="AI機能の有効/無効",
        max_forecast_days="最大予報日数（1-7）"
    )
    @app_commands.choices(action=[
        app_commands.Choice(name="設定表示", value="show"),
        app_commands.Choice(name="設定更新", value="update"),
        app_commands.Choice(name="設定リセット", value="reset")
    ])
    @app_commands.default_permissions(administrator=True)
    async def weather_config(
        self, 
        interaction: discord.Interaction,
        action: str,
        default_area: Optional[str] = None,
        weather_enabled: Optional[bool] = None,
        ai_enabled: Optional[bool] = None,
        max_forecast_days: Optional[int] = None
    ):
        """サーバー設定を管理するコマンド"""
        await interaction.response.defer(ephemeral=True)
        
        try:
            # 管理者権限チェック
            if not interaction.user.guild_permissions.administrator:
                embed = WeatherEmbedBuilder.create_error_embed(
                    "権限エラー",
                    "このコマンドは管理者のみ使用できます。",
                    "permission"
                )
                await interaction.followup.send(embed=embed, ephemeral=True)
                return
            
            guild_id = interaction.guild.id
            
            if action == "show":
                await self._show_server_config(interaction, guild_id)
            elif action == "update":
                await self._update_server_config(
                    interaction, guild_id, default_area, 
                    weather_enabled, ai_enabled, max_forecast_days
                )
            elif action == "reset":
                await self._reset_server_config(interaction, guild_id)
            
        except Exception as e:
            logger.error(f"weather-configコマンドでエラーが発生しました: {e}")
            embed = WeatherEmbedBuilder.create_error_embed(
                "システムエラー",
                "設定管理中にエラーが発生しました。",
                "general"
            )
            await interaction.followup.send(embed=embed, ephemeral=True)
    
    async def _show_server_config(self, interaction: discord.Interaction, guild_id: int):
        """サーバー設定を表示"""
        config = await ServerConfigService.get_server_config(guild_id)
        
        embed = discord.Embed(
            title="🔧 サーバー設定",
            color=discord.Color.blue()
        )
        
        if config:
            embed.add_field(
                name="デフォルト地域", 
                value=config.default_area_name or "未設定", 
                inline=True
            )
            embed.add_field(
                name="天気機能", 
                value="有効" if config.is_weather_enabled else "無効", 
                inline=True
            )
            embed.add_field(
                name="AI機能", 
                value="有効" if config.is_ai_enabled else "無効", 
                inline=True
            )
            embed.add_field(
                name="最大予報日数", 
                value=f"{config.max_forecast_days}日", 
                inline=True
            )
            embed.add_field(
                name="タイムゾーン", 
                value=config.timezone, 
                inline=True
            )
            embed.add_field(
                name="設定日時", 
                value=config.created_at.strftime("%Y-%m-%d %H:%M"), 
                inline=True
            )
        else:
            embed.description = "このサーバーの設定はまだ作成されていません。"
        
        await interaction.followup.send(embed=embed, ephemeral=True)
    
    async def _update_server_config(
        self, 
        interaction: discord.Interaction, 
        guild_id: int,
        default_area: Optional[str],
        weather_enabled: Optional[bool],
        ai_enabled: Optional[bool],
        max_forecast_days: Optional[int]
    ):
        """サーバー設定を更新"""
        update_data = {}
        
        # 地域設定の検証と更新
        if default_area:
            areas = await self.weather_service.search_area_by_name(default_area)
            if areas:
                area = areas[0]
                update_data['default_area_code'] = area.code
                update_data['default_area_name'] = area.name
            else:
                embed = WeatherEmbedBuilder.create_error_embed(
                    "地域エラー",
                    f"地域「{default_area}」が見つかりませんでした。",
                    "location"
                )
                await interaction.followup.send(embed=embed, ephemeral=True)
                return
        
        # その他の設定更新
        if weather_enabled is not None:
            update_data['is_weather_enabled'] = weather_enabled
        if ai_enabled is not None:
            update_data['is_ai_enabled'] = ai_enabled
        if max_forecast_days is not None:
            if 1 <= max_forecast_days <= 7:
                update_data['max_forecast_days'] = max_forecast_days
            else:
                embed = WeatherEmbedBuilder.create_error_embed(
                    "設定エラー",
                    "最大予報日数は1-7の範囲で指定してください。",
                    "general"
                )
                await interaction.followup.send(embed=embed, ephemeral=True)
                return
        
        if not update_data:
            embed = WeatherEmbedBuilder.create_error_embed(
                "設定エラー",
                "更新する設定項目を指定してください。",
                "general"
            )
            await interaction.followup.send(embed=embed, ephemeral=True)
            return
        
        config = await ServerConfigService.create_or_update_server_config(guild_id, **update_data)
        
        if config:
            embed = discord.Embed(
                title="✅ 設定更新完了",
                description="サーバー設定が正常に更新されました。",
                color=discord.Color.green()
            )
            
            # 更新された項目を表示
            for key, value in update_data.items():
                if key == 'default_area_name':
                    embed.add_field(name="デフォルト地域", value=value, inline=True)
                elif key == 'is_weather_enabled':
                    embed.add_field(name="天気機能", value="有効" if value else "無効", inline=True)
                elif key == 'is_ai_enabled':
                    embed.add_field(name="AI機能", value="有効" if value else "無効", inline=True)
                elif key == 'max_forecast_days':
                    embed.add_field(name="最大予報日数", value=f"{value}日", inline=True)
        else:
            embed = WeatherEmbedBuilder.create_error_embed(
                "設定エラー",
                "設定の更新に失敗しました。",
                "general"
            )
        
        await interaction.followup.send(embed=embed, ephemeral=True)
    
    async def _reset_server_config(self, interaction: discord.Interaction, guild_id: int):
        """サーバー設定をリセット"""
        success = await ServerConfigService.delete_server_config(guild_id)
        
        if success:
            embed = discord.Embed(
                title="🔄 設定リセット完了",
                description="サーバー設定がリセットされました。",
                color=discord.Color.orange()
            )
        else:
            embed = WeatherEmbedBuilder.create_error_embed(
                "設定エラー",
                "設定のリセットに失敗しました。",
                "general"
            )
        
        await interaction.followup.send(embed=embed, ephemeral=True)
    
    @app_commands.command(name="stats", description="ボットの詳細統計情報を表示します（管理者専用）")
    @app_commands.describe(category="表示する統計カテゴリ")
    @app_commands.choices(category=[
        app_commands.Choice(name="基本情報", value="basic"),
        app_commands.Choice(name="システム情報", value="system"),
        app_commands.Choice(name="ユーザー活動", value="activity"),
        app_commands.Choice(name="全て", value="all")
    ])
    @app_commands.default_permissions(administrator=True)
    async def stats_command(self, interaction: discord.Interaction, category: str = "basic"):
        """ボット統計情報を表示するコマンド"""
        await interaction.response.defer(ephemeral=True)
        
        try:
            # 管理者権限チェック
            if not interaction.user.guild_permissions.administrator:
                embed = WeatherEmbedBuilder.create_error_embed(
                    "権限エラー",
                    "このコマンドは管理者のみ使用できます。",
                    "permission"
                )
                await interaction.followup.send(embed=embed, ephemeral=True)
                return
            
            # 統計情報を取得
            stats = await StatsService.get_bot_stats(self.bot)
            
            if category == "basic" or category == "all":
                await self._send_basic_stats(interaction, stats, category == "all")
            
            if category == "system" or category == "all":
                await self._send_system_stats(interaction, stats, category == "all")
            
            if category == "activity" or category == "all":
                await self._send_activity_stats(interaction, category == "all")
            
        except Exception as e:
            logger.error(f"statsコマンドでエラーが発生しました: {e}")
            embed = WeatherEmbedBuilder.create_error_embed(
                "システムエラー",
                "統計情報の取得中にエラーが発生しました。",
                "general"
            )
            await interaction.followup.send(embed=embed, ephemeral=True)
    
    async def _send_basic_stats(self, interaction: discord.Interaction, stats: dict, is_followup: bool = False):
        """基本統計情報を送信"""
        discord_stats = stats.get('discord', {})
        db_stats = stats.get('database', {})
        
        embed = discord.Embed(
            title="📊 ボット基本統計",
            color=discord.Color.blue()
        )
        
        # Discord統計
        embed.add_field(
            name="🌐 Discord",
            value=f"サーバー数: {discord_stats.get('guild_count', 0)}\n"
                  f"ユーザー数: {discord_stats.get('user_count', 0):,}\n"
                  f"レイテンシ: {discord_stats.get('latency_ms', 0)}ms\n"
                  f"稼働時間: {discord_stats.get('uptime', '不明')}",
            inline=True
        )
        
        # データベース統計
        embed.add_field(
            name="💾 データベース",
            value=f"登録ユーザー: {db_stats.get('total_users', 0):,}\n"
                  f"アクティブユーザー: {db_stats.get('active_users', 0):,}\n"
                  f"新規ユーザー(7日): {db_stats.get('recent_users', 0):,}\n"
                  f"設定済みサーバー: {db_stats.get('configured_servers', 0):,}",
            inline=True
        )
        
        if is_followup:
            await interaction.followup.send(embed=embed, ephemeral=True)
        else:
            await interaction.followup.send(embed=embed, ephemeral=True)
    
    async def _send_system_stats(self, interaction: discord.Interaction, stats: dict, is_followup: bool = False):
        """システム統計情報を送信"""
        system_stats = stats.get('system', {})
        
        embed = discord.Embed(
            title="🖥️ システム統計",
            color=discord.Color.orange()
        )
        
        # CPU・メモリ
        embed.add_field(
            name="⚡ パフォーマンス",
            value=f"CPU使用率: {system_stats.get('cpu_percent', 0):.1f}%\n"
                  f"メモリ使用率: {system_stats.get('memory_percent', 0):.1f}%\n"
                  f"メモリ使用量: {system_stats.get('memory_used_mb', 0):,}MB / {system_stats.get('memory_total_mb', 0):,}MB",
            inline=True
        )
        
        # ディスク
        embed.add_field(
            name="💿 ストレージ",
            value=f"ディスク使用率: {system_stats.get('disk_percent', 0)}%\n"
                  f"使用量: {system_stats.get('disk_used_gb', 0)}GB / {system_stats.get('disk_total_gb', 0)}GB",
            inline=True
        )
        
        await interaction.followup.send(embed=embed, ephemeral=True)
    
    async def _send_activity_stats(self, interaction: discord.Interaction, is_followup: bool = False):
        """ユーザー活動統計を送信"""
        activity_stats = await StatsService.get_user_activity_stats()
        
        embed = discord.Embed(
            title="👥 ユーザー活動統計",
            color=discord.Color.green()
        )
        
        # 人気地域TOP5
        top_areas = activity_stats.get('top_areas', [])[:5]
        if top_areas:
            area_text = "\n".join([f"{area['area']}: {area['count']}人" for area in top_areas])
            embed.add_field(name="🏙️ 人気地域 TOP5", value=area_text, inline=True)
        
        # 通知時間分布
        hour_stats = activity_stats.get('notification_hours', [])
        if hour_stats:
            # 時間帯別にグループ化
            morning = sum(h['count'] for h in hour_stats if 6 <= h['hour'] < 12)
            afternoon = sum(h['count'] for h in hour_stats if 12 <= h['hour'] < 18)
            evening = sum(h['count'] for h in hour_stats if 18 <= h['hour'] < 24)
            night = sum(h['count'] for h in hour_stats if 0 <= h['hour'] < 6)
            
            embed.add_field(
                name="⏰ 通知時間帯",
                value=f"朝 (6-12時): {morning}人\n"
                      f"昼 (12-18時): {afternoon}人\n"
                      f"夕 (18-24時): {evening}人\n"
                      f"夜 (0-6時): {night}人",
                inline=True
            )
        
        await interaction.followup.send(embed=embed, ephemeral=True)


    @app_commands.command(name="logs", description="ボットのログ情報を表示します（管理者専用）")
    @app_commands.describe(
        level="ログレベル",
        lines="表示する行数（最大100行）"
    )
    @app_commands.choices(level=[
        app_commands.Choice(name="エラー", value="ERROR"),
        app_commands.Choice(name="警告", value="WARNING"),
        app_commands.Choice(name="情報", value="INFO"),
        app_commands.Choice(name="全て", value="ALL")
    ])
    @app_commands.default_permissions(administrator=True)
    async def logs(self, interaction: discord.Interaction, level: str = "ERROR", lines: int = 20):
        """ログ情報を表示するコマンド"""
        await interaction.response.defer(ephemeral=True)
        
        try:
            # 管理者権限チェック
            if not interaction.user.guild_permissions.administrator:
                embed = WeatherEmbedBuilder.create_error_embed(
                    "権限エラー",
                    "このコマンドは管理者のみ使用できます。",
                    "permission"
                )
                await interaction.followup.send(embed=embed, ephemeral=True)
                return
            
            # 行数制限
            lines = min(max(lines, 1), 100)
            
            log_content = await self._get_log_content(level, lines)
            
            if not log_content:
                embed = discord.Embed(
                    title="📋 ログ情報",
                    description="指定された条件のログが見つかりませんでした。",
                    color=discord.Color.light_grey()
                )
                await interaction.followup.send(embed=embed, ephemeral=True)
                return
            
            # ログ内容が長すぎる場合は分割
            if len(log_content) > 1900:
                log_content = log_content[:1900] + "\n... (省略)"
            
            embed = discord.Embed(
                title=f"📋 ログ情報 ({level} - 最新{lines}行)",
                description=f"```\n{log_content}\n```",
                color=self._get_log_color(level)
            )
            
            await interaction.followup.send(embed=embed, ephemeral=True)
            
        except Exception as e:
            logger.error(f"logsコマンドでエラーが発生しました: {e}")
            embed = WeatherEmbedBuilder.create_error_embed(
                "システムエラー",
                "ログ情報の取得中にエラーが発生しました。",
                "general"
            )
            await interaction.followup.send(embed=embed, ephemeral=True)
    
    async def _get_log_content(self, level: str, lines: int) -> str:
        """ログファイルからコンテンツを取得"""
        import os
        
        log_files = []
        
        # ログファイルのパスを確認
        if os.path.exists("logs/weather_bot.log"):
            log_files.append("logs/weather_bot.log")
        if os.path.exists("logs/error.log"):
            log_files.append("logs/error.log")
        
        if not log_files:
            return ""
        
        all_logs = []
        
        for log_file in log_files:
            try:
                with open(log_file, 'r', encoding='utf-8') as f:
                    file_lines = f.readlines()
                    
                    # レベルフィルタリング
                    if level != "ALL":
                        file_lines = [line for line in file_lines if level in line]
                    
                    # 最新の行を取得
                    recent_lines = file_lines[-lines:] if len(file_lines) > lines else file_lines
                    all_logs.extend(recent_lines)
                    
            except Exception as e:
                logger.error(f"ログファイル読み込みエラー ({log_file}): {e}")
                continue
        
        # 時系列でソート（簡易的）
        all_logs.sort()
        
        return "".join(all_logs[-lines:]).strip()
    
    def _get_log_color(self, level: str) -> discord.Color:
        """ログレベルに応じた色を取得"""
        color_map = {
            "ERROR": discord.Color.red(),
            "WARNING": discord.Color.orange(),
            "INFO": discord.Color.blue(),
            "ALL": discord.Color.light_grey()
        }
        return color_map.get(level, discord.Color.light_grey())
    
    @app_commands.command(name="health-check", description="ボットのヘルスチェックを実行します（管理者専用）")
    @app_commands.default_permissions(administrator=True)
    async def health_check(self, interaction: discord.Interaction):
        """ボットのヘルスチェックを実行するコマンド"""
        await interaction.response.defer(ephemeral=True)
        
        try:
            # 管理者権限チェック
            if not interaction.user.guild_permissions.administrator:
                embed = WeatherEmbedBuilder.create_error_embed(
                    "権限エラー",
                    "このコマンドは管理者のみ使用できます。",
                    "permission"
                )
                await interaction.followup.send(embed=embed, ephemeral=True)
                return
            
            health_status = await self._perform_health_check()
            
            embed = discord.Embed(
                title="🏥 ヘルスチェック結果",
                color=discord.Color.green() if health_status['overall'] else discord.Color.red()
            )
            
            # 各コンポーネントの状態を表示
            for component, status in health_status['components'].items():
                status_emoji = "✅" if status['healthy'] else "❌"
                embed.add_field(
                    name=f"{status_emoji} {component}",
                    value=status['message'],
                    inline=False
                )
            
            # 全体的な状態
            overall_status = "正常" if health_status['overall'] else "異常"
            embed.add_field(
                name="🎯 総合状態",
                value=f"**{overall_status}**",
                inline=False
            )
            
            await interaction.followup.send(embed=embed, ephemeral=True)
            
        except Exception as e:
            logger.error(f"health-checkコマンドでエラーが発生しました: {e}")
            embed = WeatherEmbedBuilder.create_error_embed(
                "システムエラー",
                "ヘルスチェック中にエラーが発生しました。",
                "general"
            )
            await interaction.followup.send(embed=embed, ephemeral=True)
    
    async def _perform_health_check(self) -> dict:
        """ヘルスチェックを実行"""
        components = {}
        
        # データベース接続チェック
        try:
            from src.database import get_db_session, db_manager
            from sqlalchemy import text
            
            # 詳細なデータベース健全性チェック
            db_health = await db_manager.health_check()
            
            if db_health["status"] == "healthy":
                components['データベース'] = {
                    'healthy': True, 
                    'message': f'接続正常 ({db_health["response_time_seconds"]}秒)'
                }
            else:
                components['データベース'] = {
                    'healthy': False, 
                    'message': f'接続エラー: {db_health["status"]}'
                }
                
            # メモリストレージの状態も確認
            if db_health.get("memory_storage_enabled", False):
                components['メモリストレージ'] = {
                    'healthy': True,
                    'message': f'有効 (ユーザー数: {db_health.get("memory_storage_user_count", 0)})'
                }
                
        except Exception as e:
            components['データベース'] = {'healthy': False, 'message': f'接続エラー: {str(e)[:50]}'}
        
        # 気象庁APIチェック
        try:
            start_time = time.time()
            weather_data = await self.weather_service.get_api_contents()
            response_time = time.time() - start_time
            
            if weather_data:
                components['気象庁API'] = {
                    'healthy': True, 
                    'message': f'API応答正常 ({response_time:.2f}秒)'
                }
            else:
                components['気象庁API'] = {'healthy': False, 'message': 'API応答なし'}
        except Exception as e:
            components['気象庁API'] = {'healthy': False, 'message': f'APIエラー: {str(e)[:50]}'}
        
        # AI サービスチェック
        try:
            from src.services.ai_service import AIMessageService
            ai_service = AIMessageService()
            
            start_time = time.time()
            # 簡単なテストメッセージ生成
            test_message = await ai_service.generate_positive_message({
                'weather_description': '晴れ',
                'temperature': 20
            })
            response_time = time.time() - start_time
            
            if test_message:
                components['AIサービス'] = {
                    'healthy': True, 
                    'message': f'AI応答正常 ({response_time:.2f}秒)'
                }
            else:
                components['AIサービス'] = {'healthy': False, 'message': 'AI応答なし'}
        except Exception as e:
            components['AIサービス'] = {'healthy': False, 'message': f'AIエラー: {str(e)[:50]}'}
        
        # Discord接続チェック
        try:
            latency = self.bot.latency * 1000
            if latency < 1000:  # 1秒未満
                components['Discord接続'] = {'healthy': True, 'message': f'レイテンシ: {latency:.0f}ms'}
            else:
                components['Discord接続'] = {'healthy': False, 'message': f'高レイテンシ: {latency:.0f}ms'}
        except Exception as e:
            components['Discord接続'] = {'healthy': False, 'message': f'接続エラー: {str(e)[:50]}'}
        
        # システムリソースチェック
        try:
            import psutil
            
            # CPU使用率
            cpu_percent = psutil.cpu_percent(interval=1)
            cpu_healthy = cpu_percent < 80  # 80%以上は警告
            
            # メモリ使用率
            memory = psutil.virtual_memory()
            memory_percent = memory.percent
            memory_healthy = memory_percent < 85  # 85%以上は警告
            
            # ディスク使用率
            disk = psutil.disk_usage('/')
            disk_percent = disk.percent
            disk_healthy = disk_percent < 90  # 90%以上は警告
            
            components['システムリソース'] = {
                'healthy': cpu_healthy and memory_healthy and disk_healthy,
                'message': f'CPU: {cpu_percent:.1f}% | メモリ: {memory_percent:.1f}% | ディスク: {disk_percent:.1f}%'
            }
        except Exception as e:
            components['システムリソース'] = {'healthy': True, 'message': f'リソース情報取得エラー: {str(e)[:50]}'}
        
        # 全体的な健康状態を判定
        overall_healthy = all(comp['healthy'] for comp in components.values())
        
        return {
            'overall': overall_healthy,
            'components': components
        }


async def setup(bot):
    """Cogをボットに追加"""
    await bot.add_cog(AdminCommands(bot))