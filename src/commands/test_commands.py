"""テスト用のDiscordコマンド（開発・デバッグ用）"""

import discord
from discord.ext import commands
from discord import app_commands
from src.utils.logging import logger
from src.utils.embed_utils import WeatherEmbedBuilder


class TestCommands(commands.Cog):
    """テストコマンドのCogクラス"""
    
    def __init__(self, bot):
        """TestCommandsを初期化"""
        self.bot = bot
        logger.info("TestCommandsが初期化されました")
    
    @app_commands.command(name="test-long-message", description="長いメッセージの分割テスト（開発者専用）")
    @app_commands.default_permissions(administrator=True)
    async def test_long_message(self, interaction: discord.Interaction):
        """長いメッセージの分割機能をテスト"""
        await interaction.response.defer()
        
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
            
            # 長いテストメッセージを作成
            long_message = """
これは長いメッセージの分割機能をテストするためのサンプルテキストです。
Discordのメッセージには文字数制限があり、Embedの説明欄は4096文字、フィールド値は1024文字までという制限があります。

この機能では以下のような処理を行います：
1. メッセージの長さをチェック
2. 制限を超える場合は適切な位置で分割
3. 複数のEmbedまたはメッセージに分けて送信
4. ページ番号を表示してユーザーにわかりやすく提示

天気情報ボットでは、以下の場面でこの機能が活用されます：
- 長いAIメッセージの表示
- 多数の気象警報の表示
- 詳細な天気予報の表示
- エラーメッセージの詳細情報表示

この機能により、ユーザーは情報を見やすい形で受け取ることができ、
Discordの制限に引っかかることなく、必要な情報をすべて確認できます。

さらに詳細な情報が必要な場合は、ページネーション機能と組み合わせて
複数のページに分けて表示することも可能です。

これにより、ユーザーエクスペリエンスが大幅に向上し、
情報の可読性と利便性が向上します。

テストメッセージはここで終了です。
            """.strip()
            
            # 長いメッセージを複数のEmbedに分割
            embeds = WeatherEmbedBuilder.create_multi_embed_message(
                "長いメッセージ分割テスト",
                long_message,
                color=0x00FF00
            )
            
            # 各Embedを順次送信
            for i, embed in enumerate(embeds):
                if i == 0:
                    await interaction.followup.send(embed=embed)
                else:
                    await interaction.followup.send(embed=embed)
            
            # 完了メッセージ
            completion_embed = WeatherEmbedBuilder.create_success_embed(
                "テスト完了",
                f"長いメッセージを{len(embeds)}個のEmbedに分割して送信しました。"
            )
            await interaction.followup.send(embed=completion_embed)
            
        except Exception as e:
            logger.error(f"test-long-messageコマンドでエラーが発生しました: {e}")
            embed = WeatherEmbedBuilder.create_error_embed(
                "テストエラー",
                "テスト実行中にエラーが発生しました。",
                "general"
            )
            await interaction.followup.send(embed=embed, ephemeral=True)
    
    @app_commands.command(name="test-embed-limits", description="Embed制限のテスト（開発者専用）")
    @app_commands.default_permissions(administrator=True)
    async def test_embed_limits(self, interaction: discord.Interaction):
        """Embed制限の検証機能をテスト"""
        await interaction.response.defer()
        
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
            
            # 制限を超えるEmbedを作成
            very_long_title = "非常に長いタイトル" * 50  # 256文字制限をテスト
            very_long_description = "非常に長い説明文" * 500  # 4096文字制限をテスト
            
            embed = discord.Embed(
                title=very_long_title,
                description=very_long_description,
                color=0xFF0000
            )
            
            # 長いフィールドを追加
            very_long_field_value = "非常に長いフィールド値" * 100  # 1024文字制限をテスト
            embed.add_field(
                name="テストフィールド",
                value=very_long_field_value,
                inline=False
            )
            
            # 制限を検証して調整
            validated_embed = WeatherEmbedBuilder.validate_embed_limits(embed)
            
            await interaction.followup.send(embed=validated_embed)
            
            # 結果レポート
            report_embed = WeatherEmbedBuilder.create_success_embed(
                "制限検証完了",
                f"Embedの制限検証が完了しました。\n\n"
                f"**元のサイズ:**\n"
                f"タイトル: {len(very_long_title)}文字\n"
                f"説明: {len(very_long_description)}文字\n"
                f"フィールド値: {len(very_long_field_value)}文字\n\n"
                f"**調整後のサイズ:**\n"
                f"タイトル: {len(validated_embed.title or '')}文字\n"
                f"説明: {len(validated_embed.description or '')}文字\n"
                f"フィールド値: {len(validated_embed.fields[0].value) if validated_embed.fields else 0}文字"
            )
            await interaction.followup.send(embed=report_embed)
            
        except Exception as e:
            logger.error(f"test-embed-limitsコマンドでエラーが発生しました: {e}")
            embed = WeatherEmbedBuilder.create_error_embed(
                "テストエラー",
                "テスト実行中にエラーが発生しました。",
                "general"
            )
            await interaction.followup.send(embed=embed, ephemeral=True)


async def setup(bot):
    """Cogをボットに追加"""
    await bot.add_cog(TestCommands(bot))