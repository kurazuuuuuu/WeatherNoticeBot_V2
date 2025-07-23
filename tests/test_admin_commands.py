"""管理者コマンドのテスト"""

import pytest
import discord
from unittest.mock import AsyncMock, MagicMock, patch
from src.commands.admin_commands import AdminCommands
from src.services.server_config_service import ServerConfigService
from src.services.stats_service import StatsService


@pytest.fixture
def mock_bot():
    """モックボットを作成"""
    bot = MagicMock()
    bot.guilds = [MagicMock(member_count=100), MagicMock(member_count=200)]
    bot.latency = 0.05  # 50ms
    return bot


@pytest.fixture
def admin_commands(mock_bot):
    """AdminCommandsインスタンスを作成"""
    return AdminCommands(mock_bot)


@pytest.fixture
def mock_interaction():
    """モックインタラクションを作成"""
    interaction = MagicMock(spec=discord.Interaction)
    interaction.response = AsyncMock()
    interaction.followup = AsyncMock()
    interaction.user = MagicMock()
    interaction.user.guild_permissions = MagicMock()
    interaction.user.guild_permissions.administrator = True
    interaction.guild = MagicMock()
    interaction.guild.id = 12345
    return interaction


class TestAdminCommands:
    """管理者コマンドのテストクラス"""
    
    @pytest.mark.asyncio
    async def test_weather_config_show(self, admin_commands, mock_interaction):
        """weather-config showコマンドのテスト"""
        # モックサーバー設定
        mock_config = MagicMock()
        mock_config.default_area_name = "東京都"
        mock_config.is_weather_enabled = True
        mock_config.is_ai_enabled = True
        mock_config.max_forecast_days = 7
        mock_config.timezone = "Asia/Tokyo"
        mock_config.created_at.strftime.return_value = "2024-01-01 12:00"
        
        with patch.object(ServerConfigService, 'get_server_config', return_value=mock_config):
            await admin_commands.weather_config.callback(admin_commands, mock_interaction, "show")
            
            # レスポンスが呼ばれたことを確認
            mock_interaction.response.defer.assert_called_once_with(ephemeral=True)
            mock_interaction.followup.send.assert_called_once()
            
            # 送信されたembedの内容を確認
            call_args = mock_interaction.followup.send.call_args
            embed = call_args[1]['embed']
            assert embed.title == "🔧 サーバー設定"
    
    @pytest.mark.asyncio
    async def test_weather_config_update(self, admin_commands, mock_interaction):
        """weather-config updateコマンドのテスト"""
        # モック地域検索結果
        mock_area = MagicMock()
        mock_area.code = "130010"
        mock_area.name = "東京都"
        
        # モック更新結果
        mock_config = MagicMock()
        
        with patch.object(admin_commands.weather_service, 'search_area_by_name', return_value=[mock_area]), \
             patch.object(ServerConfigService, 'create_or_update_server_config', return_value=mock_config):
            
            await admin_commands.weather_config.callback(
                admin_commands,
                mock_interaction, 
                "update", 
                default_area="東京都",
                weather_enabled=True,
                ai_enabled=False,
                max_forecast_days=5
            )
            
            # レスポンスが呼ばれたことを確認
            mock_interaction.response.defer.assert_called_once_with(ephemeral=True)
            mock_interaction.followup.send.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_weather_config_permission_denied(self, admin_commands, mock_interaction):
        """権限なしユーザーのテスト"""
        mock_interaction.user.guild_permissions.administrator = False
        
        await admin_commands.weather_config.callback(admin_commands, mock_interaction, "show")
        
        # エラーレスポンスが送信されたことを確認
        mock_interaction.followup.send.assert_called_once()
        call_args = mock_interaction.followup.send.call_args
        embed = call_args[1]['embed']
        assert "権限エラー" in embed.title
    
    @pytest.mark.asyncio
    async def test_bot_stats_basic(self, admin_commands, mock_interaction):
        """bot-stats basicコマンドのテスト"""
        mock_stats = {
            'discord': {
                'guild_count': 2,
                'user_count': 300,
                'latency_ms': 50,
                'uptime': '1時間 30分'
            },
            'database': {
                'total_users': 150,
                'active_users': 100,
                'recent_users': 20,
                'configured_servers': 2
            },
            'system': {
                'cpu_percent': 25.5,
                'memory_percent': 60.0,
                'memory_used_mb': 512,
                'memory_total_mb': 1024,
                'disk_percent': 45.0,
                'disk_used_gb': 10.5,
                'disk_total_gb': 50.0
            }
        }
        
        with patch.object(StatsService, 'get_bot_stats', return_value=mock_stats):
            await admin_commands.stats_command.callback(admin_commands, mock_interaction, "basic")
            
            # レスポンスが呼ばれたことを確認
            mock_interaction.response.defer.assert_called_once_with(ephemeral=True)
            mock_interaction.followup.send.assert_called_once()
            
            # 送信されたembedの内容を確認
            call_args = mock_interaction.followup.send.call_args
            embed = call_args[1]['embed']
            assert embed.title == "📊 ボット基本統計"
    
    @pytest.mark.asyncio
    async def test_health_check(self, admin_commands, mock_interaction):
        """health-checkコマンドのテスト"""
        # モックヘルスチェック結果
        mock_health = {
            'overall': True,
            'components': {
                'データベース': {'healthy': True, 'message': '接続正常'},
                '気象庁API': {'healthy': True, 'message': 'API応答正常'},
                'AIサービス': {'healthy': True, 'message': 'AI応答正常'},
                'Discord接続': {'healthy': True, 'message': 'レイテンシ: 50ms'}
            }
        }
        
        with patch.object(admin_commands, '_perform_health_check', return_value=mock_health):
            await admin_commands.health_check.callback(admin_commands, mock_interaction)
            
            # レスポンスが呼ばれたことを確認
            mock_interaction.response.defer.assert_called_once_with(ephemeral=True)
            mock_interaction.followup.send.assert_called_once()
            
            # 送信されたembedの内容を確認
            call_args = mock_interaction.followup.send.call_args
            embed = call_args[1]['embed']
            assert embed.title == "🏥 ヘルスチェック結果"
            assert embed.color == discord.Color.green()
    
    @pytest.mark.asyncio
    async def test_logs_command(self, admin_commands, mock_interaction):
        """logsコマンドのテスト"""
        mock_log_content = "2024-01-01 12:00:00 INFO: ボットが起動しました\n2024-01-01 12:01:00 ERROR: テストエラー"
        
        with patch.object(admin_commands, '_get_log_content', return_value=mock_log_content):
            await admin_commands.logs.callback(admin_commands, mock_interaction, "ERROR", 20)
            
            # レスポンスが呼ばれたことを確認
            mock_interaction.response.defer.assert_called_once_with(ephemeral=True)
            mock_interaction.followup.send.assert_called_once()
            
            # 送信されたembedの内容を確認
            call_args = mock_interaction.followup.send.call_args
            embed = call_args[1]['embed']
            assert "📋 ログ情報" in embed.title
            assert "ERROR" in embed.title


class TestServerConfigService:
    """サーバー設定サービスのテストクラス"""
    
    @pytest.mark.asyncio
    async def test_get_server_config(self):
        """サーバー設定取得のテスト"""
        with patch('src.services.server_config_service.get_db_session') as mock_session:
            mock_session_instance = AsyncMock()
            mock_session.return_value.__aenter__.return_value = mock_session_instance
            
            mock_config = MagicMock()
            mock_session_instance.query.return_value.filter.return_value.first.return_value = mock_config
            
            result = await ServerConfigService.get_server_config(12345)
            
            assert result == mock_config
    
    @pytest.mark.asyncio
    async def test_create_server_config(self):
        """サーバー設定作成のテスト"""
        with patch('src.services.server_config_service.get_db_session') as mock_session:
            mock_session_instance = AsyncMock()
            mock_session.return_value.__aenter__.return_value = mock_session_instance
            
            # 既存設定なし
            mock_session_instance.query.return_value.filter.return_value.first.return_value = None
            
            result = await ServerConfigService.create_or_update_server_config(
                12345, 
                default_area_code="130010",
                default_area_name="東京都"
            )
            
            # 新規作成が呼ばれたことを確認
            mock_session_instance.add.assert_called_once()
            mock_session_instance.commit.assert_called_once()


class TestStatsService:
    """統計サービスのテストクラス"""
    
    @pytest.mark.asyncio
    async def test_get_bot_stats(self):
        """ボット統計取得のテスト"""
        mock_bot = MagicMock()
        mock_bot.guilds = [MagicMock(member_count=100)]
        mock_bot.latency = 0.05
        
        with patch.object(StatsService, '_get_database_stats', return_value={'total_users': 50}), \
             patch.object(StatsService, '_get_system_stats', return_value={'cpu_percent': 25.0}):
            
            result = await StatsService.get_bot_stats(mock_bot)
            
            assert 'discord' in result
            assert 'database' in result
            assert 'system' in result
            assert result['discord']['guild_count'] == 1
            assert result['discord']['user_count'] == 100
    
    @pytest.mark.asyncio
    async def test_get_user_activity_stats(self):
        """ユーザーアクティビティ統計のテスト"""
        with patch('src.services.stats_service.get_db_session') as mock_session:
            mock_session_instance = AsyncMock()
            mock_session.return_value.__aenter__.return_value = mock_session_instance
            
            # モック地域統計
            mock_session_instance.query.return_value.filter.return_value.group_by.return_value.order_by.return_value.limit.return_value.all.return_value = [
                ('東京都', 10),
                ('大阪府', 5)
            ]
            
            # モック時間統計
            mock_session_instance.query.return_value.filter.return_value.group_by.return_value.order_by.return_value.all.return_value = [
                (9, 5),
                (18, 8)
            ]
            
            result = await StatsService.get_user_activity_stats()
            
            assert 'top_areas' in result
            assert 'notification_hours' in result