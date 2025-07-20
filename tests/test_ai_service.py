"""
Google Gemini AIサービスのテスト

このテストファイルはAIメッセージ生成サービスの動作を確認します。
"""

import asyncio
import os
from datetime import datetime
from src.services.ai_service import AIMessageService, WeatherContext
from src.config import Config


async def test_ai_service():
    """AIサービスの基本的な動作をテスト"""
    print("=== Google Gemini AIサービステスト ===\n")
    
    # 設定を初期化
    config = Config()
    
    # AIサービスを初期化
    ai_service = AIMessageService(config)
    
    # サービスの可用性をチェック
    print(f"AIサービス利用可能: {ai_service.is_available()}")
    
    # ヘルスチェック
    health_status = await ai_service.health_check()
    print(f"ヘルスチェック結果: {health_status}\n")
    
    # テスト用の天気コンテキストを作成
    test_contexts = [
        WeatherContext(
            area_name="東京都",
            weather_description="晴れ",
            temperature=25.0,
            precipitation_probability=10,
            wind="北の風 弱く",
            timestamp=datetime.now()
        ),
        WeatherContext(
            area_name="大阪府",
            weather_description="雨",
            temperature=18.0,
            precipitation_probability=80,
            wind="南の風 やや強く",
            timestamp=datetime.now()
        ),
        WeatherContext(
            area_name="北海道",
            weather_description="雪",
            temperature=-2.0,
            precipitation_probability=90,
            wind="北西の風 強く",
            timestamp=datetime.now()
        ),
        WeatherContext(
            area_name="沖縄県",
            weather_description="曇り",
            temperature=28.0,
            precipitation_probability=30,
            wind="東の風 弱く",
            timestamp=datetime.now(),
            is_alert=True,
            alert_description="大雨警報"
        )
    ]
    
    # 各コンテキストでメッセージを生成
    for i, context in enumerate(test_contexts, 1):
        print(f"--- テストケース {i}: {context.area_name} ---")
        print(f"天気: {context.weather_description}")
        print(f"気温: {context.temperature}°C")
        print(f"降水確率: {context.precipitation_probability}%")
        if context.is_alert:
            print(f"警報: {context.alert_description}")
        
        # 一般的なメッセージを生成
        general_message = await ai_service.generate_positive_message(context, "general")
        print(f"一般メッセージ: {general_message}")
        
        # 朝のメッセージを生成
        morning_message = await ai_service.generate_positive_message(context, "morning")
        print(f"朝のメッセージ: {morning_message}")
        
        # 要約メッセージを生成
        summary_message = await ai_service.generate_weather_summary_message(context)
        print(f"要約メッセージ: {summary_message}")
        
        print()
    
    print("=== テスト完了 ===")


if __name__ == "__main__":
    asyncio.run(test_ai_service())