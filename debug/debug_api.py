#!/usr/bin/env python3
"""
気象庁APIのレスポンス構造を確認するデバッグスクリプト
"""

import asyncio
import json
import sys
import os

# プロジェクトのルートディレクトリをパスに追加
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from src.services.weather_service import WeatherService


async def debug_api_structure():
    """APIレスポンス構造をデバッグ"""
    print("=== 気象庁API レスポンス構造デバッグ ===\n")
    
    async with WeatherService() as weather_service:
        try:
            # 1. area.jsonの構造を確認
            print("1. area.json の構造確認")
            url = weather_service._build_area_url()
            print(f"URL: {url}")
            
            data = await weather_service._make_request(url)
            print(f"レスポンスのトップレベルキー: {list(data.keys())}")
            
            # 各キーの構造を確認
            for key, value in data.items():
                print(f"\n--- {key} ---")
                if isinstance(value, dict):
                    print(f"  サブキー: {list(value.keys())}")
                    
                    # さらに詳細を確認
                    for sub_key, sub_value in value.items():
                        if isinstance(sub_value, dict) and len(sub_value) > 0:
                            sample_key = list(sub_value.keys())[0]
                            sample_value = sub_value[sample_key]
                            print(f"    {sub_key}: {len(sub_value)}件")
                            if isinstance(sample_value, dict):
                                print(f"      サンプル構造: {list(sample_value.keys())}")
                                print(f"      サンプルデータ: {json.dumps(sample_value, indent=6, ensure_ascii=False)}")
                            break
                else:
                    print(f"  タイプ: {type(value)}")
                    
            # 東京の地域コードを探してみる
            print("\n\n3. 東京関連の地域コードを検索")
            for key, value in data.items():
                if isinstance(value, dict):
                    for sub_key, sub_value in value.items():
                        if isinstance(sub_value, dict):
                            for code, info in sub_value.items():
                                if isinstance(info, dict) and '東京' in info.get('name', ''):
                                    print(f"  {code}: {info}")
            
        except Exception as e:
            print(f"エラーが発生しました: {e}")
            import traceback
            traceback.print_exc()


if __name__ == "__main__":
    asyncio.run(debug_api_structure())