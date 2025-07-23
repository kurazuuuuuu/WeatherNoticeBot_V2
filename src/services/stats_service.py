"""統計情報管理サービス"""

import psutil
import os
from datetime import datetime, timedelta
from typing import Dict, Any, List
from sqlalchemy.orm import Session
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy import func
from src.database import get_db_session
from src.models.user import User
from src.models.server_config import ServerConfig
from src.utils.logging import logger


class StatsService:
    """ボット統計情報を管理するサービス"""
    
    @staticmethod
    async def get_bot_stats(bot) -> Dict[str, Any]:
        """ボットの基本統計情報を取得"""
        try:
            # Discord関連の統計
            guild_count = len(bot.guilds)
            user_count = sum(guild.member_count for guild in bot.guilds)
            latency = round(bot.latency * 1000)
            
            # データベース関連の統計
            db_stats = await StatsService._get_database_stats()
            
            # システム関連の統計
            system_stats = StatsService._get_system_stats()
            
            return {
                'discord': {
                    'guild_count': guild_count,
                    'user_count': user_count,
                    'latency_ms': latency,
                    'uptime': StatsService._get_uptime()
                },
                'database': db_stats,
                'system': system_stats
            }
        except Exception as e:
            logger.error(f"統計情報取得エラー: {e}")
            return {}
    
    @staticmethod
    async def _get_database_stats() -> Dict[str, Any]:
        """データベース統計情報を取得"""
        try:
            async with get_db_session() as session:
                from sqlalchemy import select, func
                
                # ユーザー統計
                total_stmt = select(func.count(User.id))
                total_result = await session.execute(total_stmt)
                total_users = total_result.scalar()
                
                active_stmt = select(func.count(User.id)).where(
                    User.is_notification_enabled == True
                )
                active_result = await session.execute(active_stmt)
                active_users = active_result.scalar()
                
                # 最近のユーザー登録数（過去7日間）
                week_ago = datetime.utcnow() - timedelta(days=7)
                recent_stmt = select(func.count(User.id)).where(
                    User.created_at >= week_ago
                )
                recent_result = await session.execute(recent_stmt)
                recent_users = recent_result.scalar()
                
                # サーバー設定統計
                server_stmt = select(func.count(ServerConfig.id))
                server_result = await session.execute(server_stmt)
                configured_servers = server_result.scalar()
                
                return {
                    'total_users': total_users,
                    'active_users': active_users,
                    'recent_users': recent_users,
                    'configured_servers': configured_servers
                }
        except SQLAlchemyError as e:
            logger.error(f"データベース統計取得エラー: {e}")
            return {
                'total_users': 0,
                'active_users': 0,
                'recent_users': 0,
                'configured_servers': 0
            }
    
    @staticmethod
    def _get_system_stats() -> Dict[str, Any]:
        """システム統計情報を取得"""
        try:
            # CPU使用率
            cpu_percent = psutil.cpu_percent(interval=1)
            
            # メモリ使用率
            memory = psutil.virtual_memory()
            memory_percent = memory.percent
            memory_used_mb = round(memory.used / 1024 / 1024)
            memory_total_mb = round(memory.total / 1024 / 1024)
            
            # ディスク使用率
            disk = psutil.disk_usage('/')
            disk_percent = round((disk.used / disk.total) * 100, 1)
            disk_used_gb = round(disk.used / 1024 / 1024 / 1024, 1)
            disk_total_gb = round(disk.total / 1024 / 1024 / 1024, 1)
            
            return {
                'cpu_percent': cpu_percent,
                'memory_percent': memory_percent,
                'memory_used_mb': memory_used_mb,
                'memory_total_mb': memory_total_mb,
                'disk_percent': disk_percent,
                'disk_used_gb': disk_used_gb,
                'disk_total_gb': disk_total_gb
            }
        except Exception as e:
            logger.error(f"システム統計取得エラー: {e}")
            return {}
    
    @staticmethod
    def _get_uptime() -> str:
        """ボットの稼働時間を取得"""
        try:
            # プロセスの開始時間を取得
            process = psutil.Process(os.getpid())
            start_time = datetime.fromtimestamp(process.create_time())
            uptime = datetime.now() - start_time
            
            days = uptime.days
            hours, remainder = divmod(uptime.seconds, 3600)
            minutes, _ = divmod(remainder, 60)
            
            if days > 0:
                return f"{days}日 {hours}時間 {minutes}分"
            elif hours > 0:
                return f"{hours}時間 {minutes}分"
            else:
                return f"{minutes}分"
        except Exception as e:
            logger.error(f"稼働時間取得エラー: {e}")
            return "不明"
    
    @staticmethod
    async def get_user_activity_stats() -> Dict[str, Any]:
        """ユーザーアクティビティ統計を取得"""
        try:
            async with get_db_session() as session:
                from sqlalchemy import select, func
                
                # 地域別ユーザー数
                area_stmt = select(
                    User.area_name,
                    func.count(User.id).label('count')
                ).where(
                    User.area_name.isnot(None)
                ).group_by(User.area_name).order_by(
                    func.count(User.id).desc()
                ).limit(10)
                
                area_result = await session.execute(area_stmt)
                area_stats = area_result.all()
                
                # 通知時間別ユーザー数
                hour_stmt = select(
                    User.notification_hour,
                    func.count(User.id).label('count')
                ).where(
                    User.notification_hour.isnot(None)
                ).group_by(User.notification_hour).order_by(
                    User.notification_hour
                )
                
                hour_result = await session.execute(hour_stmt)
                hour_stats = hour_result.all()
                
                return {
                    'top_areas': [{'area': area, 'count': count} for area, count in area_stats],
                    'notification_hours': [{'hour': hour, 'count': count} for hour, count in hour_stats]
                }
        except SQLAlchemyError as e:
            logger.error(f"ユーザーアクティビティ統計取得エラー: {e}")
            return {'top_areas': [], 'notification_hours': []}