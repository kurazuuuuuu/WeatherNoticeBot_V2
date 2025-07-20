#!/usr/bin/env python3
"""
AIサービスの統合テスト

このテストファイルはAIサービスと他のサービスとの統合を確認します。
"""

import asyncio
import sys
import os
from datetime import datetime
from unittest.mock import Mock

# プロジェクトのルートディレクトリをパスに追加
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

from src.services.ai_service import AIMessageService, WeatherContext, weather_data_to_context
from src.config import Config


def create_mock_weather_data(area_name: str, weather_desc: str, temp: float, precip: int, wind: str):
    """モックのWeatherDataオブジェクトを作成"""
    mock_weather = Mock()
    mock_weather.area_name = area_name
    mock_weather.weather_description = weather_desc
    mock_weather.temperature = temp
    mock_weather.precipitation_probability = precip
    mock_weather.wind = wind
    mock_weather.timestamp = datetime.now()
    return mock_weather


async def test_weather_service_integration():
    """WeatherServiceとの統合テスト"""
    print("=== WeatherService統合テスト ===")
    
    config = Config()
    ai_service = AIMessageService(config)
    
    # 様々な天気データをシミュレート
    weather_scenarios = [
        {
            "name": "東京の晴れ",
            "data": create_mock_weather_data("東京都", "晴れ", 25.0, 10, "北の風 弱く")
        },
        {
            "name": "大阪の雨",
            "data": create_mock_weather_data("大阪府", "雨", 18.0, 80, "南の風 やや強く")
        },
        {
            "name": "北海道の雪",
            "data": create_mock_weather_data("北海道", "雪", -2.0, 70, "北西の風 強く")
        }
    ]
    
    for scenario in weather_scenarios:
        print(f"\n--- {scenario['name']} ---")
        
        # WeatherDataをWeatherContextに変換
        weather_context = weather_data_to_context(scenario['data'])
        
        print(f"変換後のコンテキスト:")
        print(f"  地域: {weather_context.area_name}")
        print(f"  天気: {weather_context.weather_description}")
        print(f"  気温: {weather_context.temperature}°C")
        print(f"  降水確率: {weather_context.precipitation_probability}%")
        
        # AIメッセージを生成
        message = await ai_service.generate_positive_message(weather_context)
        print(f"生成メッセージ: {message}")


async def test_notification_service_integration():
    """NotificationServiceとの統合を想定したテスト"""
    print("\n=== NotificationService統合テスト ===")
    
    config = Config()
    ai_service = AIMessageService(config)
    
    # 定時通知用のメッセージ生成をシミュレート
    notification_scenarios = [
        {
            "time": "morning",
            "weather": create_mock_weather_data("横浜市", "曇り", 20.0, 30, "東の風")
        },
        {
            "time": "evening", 
            "weather": create_mock_weather_data("福岡市", "晴れ", 22.0, 5, "西の風 弱く")
        }
    ]
    
    for scenario in notification_scenarios:
        print(f"\n--- {scenario['time']}の通知メッセージ ---")
        
        weather_context = weather_data_to_context(scenario['weather'])
        
        # 時間帯に応じたメッセージを生成
        message = await ai_service.generate_positive_message(
            weather_context, 
            message_type=scenario['time']
        )
        
        print(f"通知メッセージ: {message}")
        print(f"文字数: {len(message)}")


async def test_discord_embed_integration():
    """Discord Embedとの統合を想定したテスト"""
    print("\n=== Discord Embed統合テスト ===")
    
    config = Config()
    ai_service = AIMessageService(config)
    
    # Discord Embedで使用される形式のデータを作成
    embed_weather_data = create_mock_weather_data(
        "神奈川県", "晴れ時々曇り", 24.5, 20, "南の風"
    )
    
    weather_context = weather_data_to_context(embed_weather_data)
    
    # 通常のメッセージ
    general_message = await ai_service.generate_positive_message(weather_context)
    
    # 要約メッセージ
    summary_message = await ai_service.generate_weather_summary_message(weather_context)
    
    print("Discord Embed用メッセージ:")
    print(f"メインメッセージ: {general_message}")
    print(f"要約メッセージ: {summary_message}")
    
    # Embedフィールド用の短いメッセージをシミュレート
    short_context = WeatherContext(
        area_name=weather_context.area_name,
        weather_description=weather_context.weather_description,
        temperature=weather_context.temperature,
        precipitation_probability=weather_context.precipitation_probability,
        wind=weather_context.wind,
        timestamp=weather_context.timestamp
    )
    
    # フォールバック（短いメッセージ）
    fallback_message = ai_service._get_fallback_message(short_context, "general")
    print(f"フォールバックメッセージ: {fallback_message}")


async def test_batch_message_generation():
    """バッチでのメッセージ生成テスト"""
    print("\n=== バッチメッセージ生成テスト ===")
    
    config = Config()
    ai_service = AIMessageService(config)
    
    # 複数ユーザーの天気データをシミュレート
    user_weather_data = [
        {"user_id": 1, "weather": create_mock_weather_data("札幌市", "雪", -1.0, 80, "北の風")},
        {"user_id": 2, "weather": create_mock_weather_data("仙台市", "曇り", 15.0, 40, "東の風")},
        {"user_id": 3, "weather": create_mock_weather_data("名古屋市", "晴れ", 26.0, 10, "南の風")},
        {"user_id": 4, "weather": create_mock_weather_data("広島市", "雨", 19.0, 70, "西の風")},
        {"user_id": 5, "weather": create_mock_weather_data("那覇市", "晴れ", 28.0, 5, "南東の風")}
    ]
    
    print("5人のユーザーに対してバッチでメッセージ生成:")
    
    # 並行してメッセージを生成
    tasks = []
    for user_data in user_weather_data:
        weather_context = weather_data_to_context(user_data["weather"])
        task = ai_service.generate_positive_message(weather_context, "morning")
        tasks.append((user_data["user_id"], task))
    
    # 全てのタスクを並行実行
    results = []
    for user_id, task in tasks:
        message = await task
        results.append((user_id, message))
    
    for user_id, message in results:
        weather_data = next(u["weather"] for u in user_weather_data if u["user_id"] == user_id)
        print(f"\nユーザー{user_id} ({weather_data.area_name}):")
        print(f"  天気: {weather_data.weather_description}")
        print(f"  メッセージ: {message[:60]}...")


async def test_performance_metrics():
    """パフォーマンス測定テスト"""
    print("\n=== パフォーマンス測定テスト ===")
    
    config = Config()
    ai_service = AIMessageService(config)
    
    weather_context = WeatherContext(
        area_name="パフォーマンステスト",
        weather_description="晴れ",
        temperature=23.0,
        precipitation_probability=15,
        wind="北の風",
        timestamp=datetime.now()
    )
    
    # 10回のメッセージ生成時間を測定
    import time
    
    print("10回のメッセージ生成時間を測定:")
    
    start_time = time.time()
    for i in range(10):
        message = await ai_service.generate_positive_message(weather_context)
        if i == 0:
            print(f"最初のメッセージ: {message[:50]}...")
    
    end_time = time.time()
    total_time = end_time - start_time
    avg_time = total_time / 10
    
    print(f"総時間: {total_time:.2f}秒")
    print(f"平均時間: {avg_time:.2f}秒/メッセージ")
    print(f"スループット: {10/total_time:.2f}メッセージ/秒")


async def test_error_recovery():
    """エラー回復テスト"""
    print("\n=== エラー回復テスト ===")
    
    config = Config()
    ai_service = AIMessageService(config)
    
    weather_context = WeatherContext(
        area_name="エラー回復テスト",
        weather_description="曇り",
        temperature=21.0,
        precipitation_probability=35,
        wind="西の風",
        timestamp=datetime.now()
    )
    
    # 正常なメッセージ生成
    print("1. 正常なメッセージ生成:")
    normal_message = await ai_service.generate_positive_message(weather_context)
    print(f"   {normal_message[:50]}...")
    
    # ヘルスチェック
    print("\n2. ヘルスチェック:")
    health = await ai_service.health_check()
    print(f"   ステータス: {health['status']}")
    
    # サービス利用可能性確認
    print(f"\n3. サービス利用可能: {ai_service.is_available()}")
    
    # フォールバック機能確認
    print("\n4. フォールバック機能:")
    fallback_message = ai_service._get_fallback_message(weather_context, "general")
    print(f"   {fallback_message}")


async def main():
    """メインテスト関数"""
    print("AIサービス統合テスト開始")
    print("=" * 50)
    
    try:
        # WeatherServiceとの統合テスト
        await test_weather_service_integration()
        
        # NotificationServiceとの統合テスト
        await test_notification_service_integration()
        
        # Discord Embedとの統合テスト
        await test_discord_embed_integration()
        
        # バッチメッセージ生成テスト
        await test_batch_message_generation()
        
        # パフォーマンス測定テスト
        await test_performance_metrics()
        
        # エラー回復テスト
        await test_error_recovery()
        
        print("\n" + "=" * 50)
        print("全ての統合テストが完了しました！")
        
    except Exception as e:
        print(f"\nテスト中にエラーが発生しました: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    asyncio.run(main())