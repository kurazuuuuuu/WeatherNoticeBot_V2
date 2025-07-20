"""管理者用のDiscordコマンド"""

import discord
from discord.ext import commands
from discord import app_commands
from src.utils.logging import logger


class AdminCommands(commands.Cog):
    """管理者コマンドのCogクラス"""
    
    def __init__(self, bot):
        """AdminCommandsを初期化"""
        self.bot = bot
        logger.info("AdminCommandsが初期化されました")
    
    @app_commands.command(name="weather-config", description="サーバーの天気ボット設定を管理します（管理者専用）")
    @app_commands.default_permissions(administrator=True)
    async def weather_config(self, interaction: discord.Interaction):
        """サーバー設定を管理するコマンド"""
        await interaction.response.defer()
        
        try:
            # 管理者権限チェック
            if not interaction.user.guild_permissions.administrator:
                await interaction.followup.send("このコマンドは管理者のみ使用できます。", ephemeral=True)
                return
            
            # TODO: 実装予定 - サーバー設定ロジック
            embed = discord.Embed(
                title="🔧 サーバー設定",
                description="このコマンドは現在実装中です。",
                color=discord.Color.gold()
            )
            await interaction.followup.send(embed=embed, ephemeral=True)
            
        except Exception as e:
            logger.error(f"weather-configコマンドでエラーが発生しました: {e}")
            await interaction.followup.send("設定管理中にエラーが発生しました。", ephemeral=True)
    
    @app_commands.command(name="stats", description="ボットの統計情報を表示します（管理者専用）")
    @app_commands.default_permissions(administrator=True)
    async def stats(self, interaction: discord.Interaction):
        """ボット統計情報を表示するコマンド"""
        await interaction.response.defer()
        
        try:
            # 管理者権限チェック
            if not interaction.user.guild_permissions.administrator:
                await interaction.followup.send("このコマンドは管理者のみ使用できます。", ephemeral=True)
                return
            
            # 基本的な統計情報を取得
            guild_count = len(self.bot.guilds)
            user_count = sum(guild.member_count for guild in self.bot.guilds)
            
            embed = discord.Embed(
                title="📊 ボット統計情報",
                color=discord.Color.blue()
            )
            embed.add_field(name="サーバー数", value=f"{guild_count}", inline=True)
            embed.add_field(name="ユーザー数", value=f"{user_count}", inline=True)
            embed.add_field(name="レイテンシ", value=f"{round(self.bot.latency * 1000)}ms", inline=True)
            
            await interaction.followup.send(embed=embed, ephemeral=True)
            
        except Exception as e:
            logger.error(f"bot-statsコマンドでエラーが発生しました: {e}")
            await interaction.followup.send("統計情報の取得中にエラーが発生しました。", ephemeral=True)


async def setup(bot):
    """Cogをボットに追加"""
    await bot.add_cog(AdminCommands(bot))