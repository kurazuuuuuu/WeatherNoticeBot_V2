#!/usr/bin/env python3
"""
Google Gemini AIサービスの詳細テスト

このテストファイルはAIメッセージ生成サービスの各機能を詳細にテストします。
"""

import asyncio
import sys
import os
from datetime import datetime
from unittest.mock import Mock, patch

# プロジェクトのルートディレクトリをパスに追加
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

from src.services.ai_service import AIMessageService, WeatherContext, weather_data_to_context
from src.config import Config


async def test_ai_service_initialization():
    """AIサービスの初期化テスト"""
    print("=== AIサービス初期化テスト ===")
    
    # 設定を作成
    config = Config()
    
    # AIサービスを初期化
    ai_service = AIMessageService(config)
    
    print(f"AIサービス利用可能: {ai_service.is_available()}")
    print(f"Gemini APIキー設定済み: {'Yes' if config.GEMINI_API_KEY else 'No'}")
    
    return ai_service


async def test_weather_context_creation():
    """WeatherContextの作成テスト"""
    print("\n=== WeatherContext作成テスト ===")
    
    # テスト用の天気コンテキストを作成
    weather_context = WeatherContext(
        area_name="東京都",
        weather_description="晴れ",
        temperature=22.5,
        precipitation_probability=10,
        wind="北の風 弱く",
        timestamp=datetime.now(),
        is_alert=False,
        alert_description=None
    )
    
    print(f"地域名: {weather_context.area_name}")
    print(f"天気: {weather_context.weather_description}")
    print(f"気温: {weather_context.temperature}°C")
    print(f"降水確率: {weather_context.precipitation_probability}%")
    print(f"風: {weather_context.wind}")
    print(f"警報: {'あり' if weather_context.is_alert else 'なし'}")
    
    return weather_context


async def test_positive_message_generation(ai_service, weather_context):
    """ポジティブメッセージ生成テスト"""
    print("\n=== ポジティブメッセージ生成テスト ===")
    
    # 各種メッセージタイプをテスト
    message_types = ["general", "morning", "evening", "alert"]
    
    for message_type in message_types:
        print(f"\n--- {message_type}メッセージ ---")
        
        # 警報テスト用のコンテキストを作成
        if message_type == "alert":
            alert_context = WeatherContext(
                area_name="大阪府",
                weather_description="大雨",
                temperature=18.0,
                precipitation_probability=90,
                wind="南の風 強く",
                timestamp=datetime.now(),
                is_alert=True,
                alert_description="大雨警報"
            )
            message = await ai_service.generate_positive_message(alert_context, message_type)
        else:
            message = await ai_service.generate_positive_message(weather_context, message_type)
        
        print(f"生成メッセージ: {message}")
        print(f"文字数: {len(message)}")


async def test_weather_summary_generation(ai_service, weather_context):
    """天気要約メッセージ生成テスト"""
    print("\n=== 天気要約メッセージ生成テスト ===")
    
    summary = await ai_service.generate_weather_summary_message(weather_context, forecast_days=3)
    print(f"要約メッセージ: {summary}")
    print(f"文字数: {len(summary)}")


async def test_fallback_messages(ai_service):
    """フォールバック機能テスト"""
    print("\n=== フォールバック機能テスト ===")
    
    # 様々な天気条件でフォールバックメッセージをテスト
    test_conditions = [
        {
            "area_name": "札幌市",
            "weather_description": "雪",
            "temperature": -2.0,
            "precipitation_probability": 80,
            "wind": "北の風 やや強く",
            "is_alert": False
        },
        {
            "area_name": "沖縄県",
            "weather_description": "晴れ",
            "temperature": 28.0,
            "precipitation_probability": 0,
            "wind": "南の風 弱く",
            "is_alert": False
        },
        {
            "area_name": "福岡県",
            "weather_description": "曇り",
            "temperature": 15.0,
            "precipitation_probability": 40,
            "wind": "西の風",
            "is_alert": True,
            "alert_description": "強風注意報"
        }
    ]
    
    for i, condition in enumerate(test_conditions, 1):
        print(f"\n--- テストケース {i} ---")
        
        weather_context = WeatherContext(
            area_name=condition["area_name"],
            weather_description=condition["weather_description"],
            temperature=condition["temperature"],
            precipitation_probability=condition["precipitation_probability"],
            wind=condition["wind"],
            timestamp=datetime.now(),
            is_alert=condition.get("is_alert", False),
            alert_description=condition.get("alert_description")
        )
        
        # フォールバック機能を強制的にテスト
        fallback_message = ai_service._get_fallback_message(weather_context, "general")
        print(f"地域: {condition['area_name']}")
        print(f"天気: {condition['weather_description']}")
        print(f"フォールバックメッセージ: {fallback_message}")


async def test_health_check(ai_service):
    """ヘルスチェックテスト"""
    print("\n=== ヘルスチェックテスト ===")
    
    health_status = await ai_service.health_check()
    
    print(f"ステータス: {health_status['status']}")
    print(f"メッセージ: {health_status['message']}")
    print(f"フォールバック利用可能: {health_status['fallback_available']}")
    
    if 'test_message_length' in health_status:
        print(f"テストメッセージ長: {health_status['test_message_length']}文字")


async def test_weather_data_conversion():
    """WeatherData変換テスト"""
    print("\n=== WeatherData変換テスト ===")
    
    # モックのWeatherDataオブジェクトを作成
    mock_weather_data = Mock()
    mock_weather_data.area_name = "横浜市"
    mock_weather_data.weather_description = "曇り時々雨"
    mock_weather_data.temperature = 19.5
    mock_weather_data.precipitation_probability = 60
    mock_weather_data.wind = "東の風"
    mock_weather_data.timestamp = datetime.now()
    
    # 変換テスト
    weather_context = weather_data_to_context(mock_weather_data)
    
    print(f"変換結果:")
    print(f"  地域名: {weather_context.area_name}")
    print(f"  天気: {weather_context.weather_description}")
    print(f"  気温: {weather_context.temperature}°C")
    print(f"  降水確率: {weather_context.precipitation_probability}%")
    print(f"  風: {weather_context.wind}")
    print(f"  警報: {'あり' if weather_context.is_alert else 'なし'}")


async def main():
    """メインテスト関数"""
    print("Google Gemini AIサービス詳細テスト開始")
    print("=" * 50)
    
    try:
        # AIサービスの初期化
        ai_service = await test_ai_service_initialization()
        
        # WeatherContextの作成
        weather_context = await test_weather_context_creation()
        
        # WeatherData変換テスト
        await test_weather_data_conversion()
        
        # ポジティブメッセージ生成テスト
        await test_positive_message_generation(ai_service, weather_context)
        
        # 天気要約メッセージ生成テスト
        await test_weather_summary_generation(ai_service, weather_context)
        
        # フォールバック機能テスト
        await test_fallback_messages(ai_service)
        
        # ヘルスチェックテスト
        await test_health_check(ai_service)
        
        print("\n" + "=" * 50)
        print("全てのテストが完了しました！")
        
    except Exception as e:
        print(f"\nテスト中にエラーが発生しました: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    asyncio.run(main())