#!/usr/bin/env python3
"""
AIサービスのエラーハンドリングとフォールバック機能のテスト

このテストファイルはAPIエラー時の動作を詳細にテストします。
"""

import asyncio
import sys
import os
from datetime import datetime
from unittest.mock import Mock, patch, AsyncMock

# プロジェクトのルートディレクトリをパスに追加
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

from src.services.ai_service import AIMessageService, WeatherContext
from src.config import Config


async def test_api_key_missing():
    """APIキーが設定されていない場合のテスト"""
    print("=== APIキー未設定テスト ===")
    
    # APIキーを空にした設定を作成
    config = Config()
    original_key = config.GEMINI_API_KEY
    config.GEMINI_API_KEY = ""
    
    try:
        ai_service = AIMessageService(config)
        
        print(f"AIサービス利用可能: {ai_service.is_available()}")
        
        # テスト用の天気コンテキスト
        weather_context = WeatherContext(
            area_name="テスト地域",
            weather_description="晴れ",
            temperature=20.0,
            precipitation_probability=10,
            wind="北の風",
            timestamp=datetime.now()
        )
        
        # メッセージ生成（フォールバックが使用されるはず）
        message = await ai_service.generate_positive_message(weather_context)
        print(f"フォールバックメッセージ: {message}")
        
        # ヘルスチェック
        health = await ai_service.health_check()
        print(f"ヘルスチェック結果: {health['status']}")
        print(f"メッセージ: {health['message']}")
        
    finally:
        # 元のAPIキーを復元
        config.GEMINI_API_KEY = original_key


async def test_api_error_simulation():
    """API呼び出しエラーのシミュレーションテスト"""
    print("\n=== API呼び出しエラーシミュレーションテスト ===")
    
    config = Config()
    ai_service = AIMessageService(config)
    
    # テスト用の天気コンテキスト
    weather_context = WeatherContext(
        area_name="エラーテスト地域",
        weather_description="曇り",
        temperature=18.0,
        precipitation_probability=30,
        wind="西の風",
        timestamp=datetime.now()
    )
    
    # Gemini APIの呼び出しをモックしてエラーを発生させる
    with patch.object(ai_service._model, 'generate_content') as mock_generate:
        # 様々なエラーパターンをテスト
        error_cases = [
            Exception("API接続エラー"),
            Exception("レート制限エラー"),
            Exception("認証エラー"),
            Exception("サービス一時停止")
        ]
        
        for i, error in enumerate(error_cases, 1):
            print(f"\n--- エラーケース {i}: {error} ---")
            
            mock_generate.side_effect = error
            
            # エラー時でもフォールバックメッセージが返されることを確認
            message = await ai_service.generate_positive_message(weather_context)
            print(f"フォールバックメッセージ: {message}")
            print(f"メッセージ長: {len(message)}文字")


async def test_empty_response_handling():
    """空のレスポンス処理テスト"""
    print("\n=== 空のレスポンス処理テスト ===")
    
    config = Config()
    ai_service = AIMessageService(config)
    
    weather_context = WeatherContext(
        area_name="空レスポンステスト",
        weather_description="雨",
        temperature=16.0,
        precipitation_probability=70,
        wind="南の風",
        timestamp=datetime.now()
    )
    
    # 空のレスポンスをシミュレート
    with patch.object(ai_service._model, 'generate_content') as mock_generate:
        # 空のレスポンスオブジェクトを作成
        mock_response = Mock()
        mock_response.text = ""
        mock_generate.return_value = mock_response
        
        message = await ai_service.generate_positive_message(weather_context)
        print(f"空レスポンス時のフォールバックメッセージ: {message}")
        
        # Noneレスポンスもテスト
        mock_generate.return_value = None
        message = await ai_service.generate_positive_message(weather_context)
        print(f"Noneレスポンス時のフォールバックメッセージ: {message}")


async def test_various_weather_conditions():
    """様々な天気条件でのフォールバック機能テスト"""
    print("\n=== 様々な天気条件でのフォールバックテスト ===")
    
    config = Config()
    ai_service = AIMessageService(config)
    
    # 様々な天気条件のテストケース
    weather_conditions = [
        {
            "name": "猛暑日",
            "area_name": "熊谷市",
            "weather_description": "晴れ",
            "temperature": 38.0,
            "precipitation_probability": 0,
            "wind": "南の風 弱く"
        },
        {
            "name": "大雨",
            "area_name": "鹿児島県",
            "weather_description": "大雨",
            "temperature": 22.0,
            "precipitation_probability": 95,
            "wind": "南の風 強く"
        },
        {
            "name": "台風接近",
            "area_name": "沖縄県",
            "weather_description": "暴風雨",
            "temperature": 25.0,
            "precipitation_probability": 100,
            "wind": "南東の風 非常に強く",
            "is_alert": True,
            "alert_description": "暴風警報"
        },
        {
            "name": "雪",
            "area_name": "青森県",
            "weather_description": "雪",
            "temperature": -5.0,
            "precipitation_probability": 80,
            "wind": "北の風 やや強く"
        },
        {
            "name": "霧",
            "area_name": "釧路市",
            "weather_description": "霧",
            "temperature": 12.0,
            "precipitation_probability": 20,
            "wind": "東の風 弱く"
        }
    ]
    
    for condition in weather_conditions:
        print(f"\n--- {condition['name']}の場合 ---")
        
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
        
        # フォールバックメッセージを生成
        fallback_message = ai_service._get_fallback_message(weather_context, "general")
        print(f"地域: {condition['area_name']}")
        print(f"天気: {condition['weather_description']}")
        print(f"気温: {condition['temperature']}°C")
        print(f"フォールバックメッセージ: {fallback_message}")


async def test_message_consistency():
    """メッセージの一貫性テスト"""
    print("\n=== メッセージ一貫性テスト ===")
    
    config = Config()
    ai_service = AIMessageService(config)
    
    # 同じ条件で複数回メッセージを生成して一貫性を確認
    weather_context = WeatherContext(
        area_name="一貫性テスト地域",
        weather_description="晴れ",
        temperature=25.0,
        precipitation_probability=10,
        wind="北の風",
        timestamp=datetime.now()
    )
    
    print("同じ条件で5回フォールバックメッセージを生成:")
    for i in range(5):
        message = ai_service._get_fallback_message(weather_context, "general")
        print(f"{i+1}回目: {message}")


async def test_concurrent_requests():
    """並行リクエストテスト"""
    print("\n=== 並行リクエストテスト ===")
    
    config = Config()
    ai_service = AIMessageService(config)
    
    # 複数の天気コンテキストを作成
    weather_contexts = [
        WeatherContext(
            area_name=f"並行テスト地域{i}",
            weather_description="晴れ",
            temperature=20.0 + i,
            precipitation_probability=10 * i,
            wind="北の風",
            timestamp=datetime.now()
        )
        for i in range(1, 6)
    ]
    
    # 並行してメッセージを生成
    print("5つの地域で並行してメッセージ生成:")
    tasks = [
        ai_service.generate_positive_message(context, "general")
        for context in weather_contexts
    ]
    
    messages = await asyncio.gather(*tasks)
    
    for i, message in enumerate(messages, 1):
        print(f"地域{i}: {message[:50]}...")


async def main():
    """メインテスト関数"""
    print("AIサービス エラーハンドリング・フォールバック機能テスト開始")
    print("=" * 60)
    
    try:
        # APIキー未設定テスト
        await test_api_key_missing()
        
        # API呼び出しエラーシミュレーション
        await test_api_error_simulation()
        
        # 空のレスポンス処理テスト
        await test_empty_response_handling()
        
        # 様々な天気条件でのフォールバックテスト
        await test_various_weather_conditions()
        
        # メッセージ一貫性テスト
        await test_message_consistency()
        
        # 並行リクエストテスト
        await test_concurrent_requests()
        
        print("\n" + "=" * 60)
        print("全てのエラーハンドリングテストが完了しました！")
        
    except Exception as e:
        print(f"\nテスト中にエラーが発生しました: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    asyncio.run(main())