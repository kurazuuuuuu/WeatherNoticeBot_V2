"""Discord天気情報ボットのメインエントリーポイント"""

import asyncio
import discord
import sys
import os
from discord.ext import commands
from src.config import config
from src.utils.logging import logger
from src.utils.environment import get_environment_info, get_database_info, is_production, is_development


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
        
        # スケジューラーの初期化（環境に応じた設定）
        try:
            from src.services.scheduler_service_init import init_scheduler
            await init_scheduler(self)
            logger.info("スケジューラーを初期化しました")
        except Exception as e:
            logger.error(f"スケジューラーの初期化に失敗しました: {e}")
            if is_production():
                raise  # 本番環境では致命的なエラーとして扱う
        
        # コマンドの登録
        await self._load_commands()
        
        # スラッシュコマンドの同期
        try:
            # 環境に応じたコマンド同期戦略
            if is_development() and config.DISCORD_GUILD_ID:
                # 開発環境では特定のギルドにのみ同期（高速）
                guild = discord.Object(id=int(config.DISCORD_GUILD_ID))
                self.tree.copy_global_to(guild=guild)
                await self.tree.sync(guild=guild)
                logger.info(f"開発モード: コマンドをギルド {config.DISCORD_GUILD_ID} に同期しました")
            elif is_production():
                # 本番環境ではグローバルに同期（時間がかかる）
                await self.tree.sync()
                logger.info("本番モード: コマンドをグローバルに同期しました")
            else:
                # その他の環境
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
            if is_production():
                raise  # 本番環境では致命的なエラーとして扱う
    
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
            
            # テストコマンドの読み込み（開発環境のみ）
            if is_development():
                try:
                    from src.commands.test_commands import TestCommands
                    await self.add_cog(TestCommands(self))
                    logger.info("テストコマンドを読み込みました（開発環境のみ）")
                except ImportError:
                    logger.debug("テストコマンドは利用できません")
            
        except ImportError as e:
            logger.warning(f"コマンドの読み込みに失敗しました（まだ実装されていない可能性があります）: {e}")
            if is_production():
                # 本番環境では致命的なエラーとして扱う
                raise
        except Exception as e:
            logger.error(f"コマンドの読み込み中にエラーが発生しました: {e}")
            if is_production():
                # 本番環境では致命的なエラーとして扱う
                raise
    
    async def on_ready(self):
        """ボットが準備完了時に呼び出される"""
        logger.info(f"ボットが準備完了しました！ {self.user} としてログイン")
        logger.info(f"ボットは {len(self.guilds)} のサーバーに参加しています")
        
        # 環境に応じたステータスを設定
        if is_production():
            activity = discord.Activity(
                type=discord.ActivityType.watching,
                name="天気予報 ☀️"
            )
        elif is_development():
            activity = discord.Activity(
                type=discord.ActivityType.playing,
                name="開発モード 🛠️"
            )
        else:
            activity = discord.Activity(
                type=discord.ActivityType.watching,
                name="天気予報 (テスト) 🧪"
            )
            
        await self.change_presence(activity=activity)
        logger.info(f"ボットのステータスを設定しました: {activity.name}")
        
        # 通知スケジューラーの開始
        try:
            from src.services.scheduler_service_init import start_scheduler
            await start_scheduler()
            logger.info("通知スケジューラーを開始しました")
        except Exception as e:
            logger.error(f"通知スケジューラーの開始に失敗しました: {e}")
            if is_production():
                # 本番環境では重大なエラーとしてログ記録
                logger.critical("本番環境で通知スケジューラーの開始に失敗しました")
    
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
        
        # スケジューラーの停止
        try:
            from src.services.scheduler_service_init import stop_scheduler
            await stop_scheduler()
            logger.info("スケジューラーを停止しました")
        except Exception as e:
            logger.error(f"スケジューラーの停止に失敗しました: {e}")
        
        await super().close()
        logger.info("ボットのシャットダウンが完了しました")


async def setup_database():
    """データベースの初期化とマイグレーション"""
    try:
        from src.database import init_database
        from src.utils.migration import check_and_upgrade_database
        
        # データベース接続の初期化
        await init_database()
        logger.info("データベース接続を初期化しました")
        
        # データベースマイグレーションの確認と実行
        migration_success = await check_and_upgrade_database()
        if migration_success:
            logger.info("データベースマイグレーションが完了しました")
        else:
            if is_production():
                logger.error("本番環境でデータベースマイグレーションに失敗しました")
                return False
            else:
                logger.warning("データベースマイグレーションに問題がありますが、開発環境のため続行します")
        
        return True
    except Exception as e:
        logger.error(f"データベースのセットアップに失敗しました: {e}", exc_info=True)
        return False


async def main():
    """ボットを実行するメイン関数"""
    # 環境情報をログに記録
    env_info = get_environment_info()
    db_info = get_database_info()
    
    logger.info(f"環境: {env_info['environment']}, Python: {env_info['python_version']}, プラットフォーム: {env_info['platform']}")
    logger.info(f"データベース: {db_info['type']} ({db_info['name']})")
    
    # データベースのセットアップ
    db_setup_success = await setup_database()
    if not db_setup_success and is_production():
        logger.critical("本番環境でデータベースのセットアップに失敗したため、ボットを起動できません")
        sys.exit(1)
    
    # ボットの初期化と起動
    bot = WeatherBot()
    
    try:
        await bot.start(config.DISCORD_TOKEN)
    except KeyboardInterrupt:
        logger.info("ボットのシャットダウンが要求されました")
    except Exception as e:
        logger.error(f"ボットの起動に失敗しました: {e}", exc_info=True)
    finally:
        # データベース接続のクローズ
        try:
            from src.database import close_database
            await close_database()
            logger.info("データベース接続をクローズしました")
        except Exception as e:
            logger.error(f"データベース接続のクローズに失敗しました: {e}")
        
        # ボットのクローズ
        await bot.close()


if __name__ == "__main__":
    asyncio.run(main())