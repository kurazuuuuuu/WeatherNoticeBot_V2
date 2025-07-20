"""Discord天気情報ボットのメインエントリーポイント"""

import asyncio
import discord
from discord.ext import commands
from src.config import config
from src.utils.logging import logger


class WeatherBot(commands.Bot):
    """Discord天気情報ボットのメインクラス"""
    
    def __init__(self):
        """必要なインテントと設定でボットを初期化"""
        intents = discord.Intents.default()
        # スラッシュコマンドのみを使用するため、message_content intentは不要
        # intents.message_content = True
        
        super().__init__(
            command_prefix=config.COMMAND_PREFIX,
            intents=intents,
            help_command=None
        )
    
    async def setup_hook(self):
        """ボット起動時のセットアップ処理"""
        logger.info("Discord天気情報ボットをセットアップ中...")
        
        # 設定の検証
        try:
            config.validate()
            logger.info("設定の検証が完了しました")
        except ValueError as e:
            logger.error(f"設定の検証に失敗しました: {e}")
            raise
        
        # コマンドの登録
        await self._load_commands()
        
        # スラッシュコマンドの同期
        try:
            if config.DISCORD_GUILD_ID:
                guild = discord.Object(id=int(config.DISCORD_GUILD_ID))
                self.tree.copy_global_to(guild=guild)
                await self.tree.sync(guild=guild)
                logger.info(f"コマンドをギルド {config.DISCORD_GUILD_ID} に同期しました")
            else:
                await self.tree.sync()
                logger.info("コマンドをグローバルに同期しました")
        except Exception as e:
            logger.error(f"コマンドの同期に失敗しました: {e}")
    
    async def _load_commands(self):
        """コマンドハンドラーを読み込み"""
        try:
            # 天気情報コマンドの読み込み
            from src.commands.weather_commands import WeatherCommands
            await self.add_cog(WeatherCommands(self))
            logger.info("天気情報コマンドを読み込みました")
            
            # ユーザー設定コマンドの読み込み
            from src.commands.user_commands import UserCommands
            await self.add_cog(UserCommands(self))
            logger.info("ユーザー設定コマンドを読み込みました")
            
            # 管理者コマンドの読み込み
            from src.commands.admin_commands import AdminCommands
            await self.add_cog(AdminCommands(self))
            logger.info("管理者コマンドを読み込みました")
            
        except ImportError as e:
            logger.warning(f"コマンドの読み込みに失敗しました（まだ実装されていない可能性があります）: {e}")
        except Exception as e:
            logger.error(f"コマンドの読み込み中にエラーが発生しました: {e}")
    
    async def on_ready(self):
        """ボットが準備完了時に呼び出される"""
        logger.info(f"ボットが準備完了しました！ {self.user} としてログイン")
        logger.info(f"ボットは {len(self.guilds)} のサーバーに参加しています")
        
        # ボットのステータスを設定
        activity = discord.Activity(
            type=discord.ActivityType.watching,
            name="天気予報 ☀️"
        )
        await self.change_presence(activity=activity)
        logger.info("ボットのステータスを設定しました")
    
    async def on_error(self, event, *args, **kwargs):
        """ボットエラーを処理"""
        logger.error(f"イベント {event} でボットエラーが発生しました", exc_info=True)
    
    async def on_command_error(self, ctx, error):
        """コマンドエラーを処理"""
        if isinstance(error, commands.CommandNotFound):
            return  # 不明なコマンドは無視
        
        logger.error(f"コマンド {ctx.command} でエラーが発生しました: {error}", exc_info=True)
        
        # ユーザーにエラーメッセージを送信
        try:
            await ctx.send("申し訳ありませんが、エラーが発生しました。後でもう一度お試しください。")
        except discord.HTTPException:
            logger.error("ユーザーへのエラーメッセージ送信に失敗しました")
    
    async def close(self):
        """ボットのシャットダウン処理"""
        logger.info("ボットをシャットダウン中...")
        await super().close()
        logger.info("ボットのシャットダウンが完了しました")


async def main():
    """ボットを実行するメイン関数"""
    bot = WeatherBot()
    
    try:
        await bot.start(config.DISCORD_TOKEN)
    except KeyboardInterrupt:
        logger.info("ボットのシャットダウンが要求されました")
    except Exception as e:
        logger.error(f"ボットの起動に失敗しました: {e}", exc_info=True)
    finally:
        await bot.close()


if __name__ == "__main__":
    asyncio.run(main())