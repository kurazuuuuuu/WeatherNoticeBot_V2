#!/usr/bin/env python3
"""スケジューラーのテストスクリプト"""

import asyncio
import sys
import os
sys.path.append('/app')

async def test_scheduler():
    from src.services.user_service import UserService
    from src.services.scheduler_service import get_scheduler_service
    from src.database import init_database
    from datetime import datetime
    import pytz
    
    # データベースを初期化
    await init_database()
    
    user_service = UserService()
    scheduler_service = get_scheduler_service()
    
    # テストユーザーを作成
    test_user_id = 123456789
    
    print("=== スケジューラーテスト開始 ===")
    
    # ユーザーを作成
    user = await user_service.create_user(test_user_id)
    print(f'ユーザー作成: {user is not None}')
    
    # 位置情報を設定
    success = await user_service.set_user_location(test_user_id, '130010', '東京都')
    print(f'位置情報設定: {success}')
    
    # 現在時刻を取得
    tokyo_tz = pytz.timezone('Asia/Tokyo')
    current_time = datetime.now(tokyo_tz)
    current_hour = current_time.hour
    next_hour = (current_hour + 1) % 24
    
    print(f'現在時刻: {current_time.strftime("%Y-%m-%d %H:%M:%S")}')
    print(f'通知設定時刻: {next_hour}:00')
    
    # 通知スケジュールを設定
    success = await user_service.set_notification_schedule(test_user_id, next_hour)
    print(f'通知スケジュール設定: {success}')
    
    # スケジューラーの状態を確認
    if scheduler_service:
        status = await scheduler_service.get_scheduler_status()
        print(f'スケジューラー実行中: {status["running"]}')
        print(f'総ジョブ数: {status["total_jobs"]}')
        print(f'通知ユーザー数: {status["scheduled_users"]}')
        
        if status["next_jobs"]:
            for job in status["next_jobs"]:
                print(f'次回実行: {job["name"]} - {job["next_run"]}')
        else:
            print('実行予定のジョブなし')
    else:
        print('スケジューラーサービスが見つかりません')
    
    print("=== テスト完了 ===")

if __name__ == "__main__":
    asyncio.run(test_scheduler())