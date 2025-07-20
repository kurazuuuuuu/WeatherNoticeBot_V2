#!/usr/bin/env python3
"""
WeatherServiceのテストスクリプト
地域情報取得機能をテストします
"""

import asyncio
import sys
import os

# プロジェクトのルートディレクトリをパスに追加
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

from services.weather_service import WeatherService


async def test_area_functions():
    """地域情報関連の機能をテスト"""
    print("=== WeatherService 地域情報機能テスト ===\n")
    
    async with WeatherService() as weather_service:
        try:
            # 1. 地域情報の取得テスト
            print("1. 地域情報の取得テスト")
            area_dict = await weather_service.get_area_list()
            print(f"取得した地域数: {len(area_dict)}")
            
            # いくつかの地域を表示
            count = 0
            for code, area in area_dict.items():
                if count < 5:
                    print(f"  {area.code}: {area.name} ({area.kana}) [{area.en_name}]")
                    count += 1
                else:
                    break
            print()
            
            # 2. 地域名検索テスト
            print("2. 地域名検索テスト")
            test_searches = ["東京", "大阪", "tokyo", "おおさか", "北海道"]
            
            for search_term in test_searches:
                results = await weather_service.search_area_by_name(search_term)
                print(f"'{search_term}' の検索結果: {len(results)}件")
                for i, area in enumerate(results[:3]):  # 最初の3件を表示
                    print(f"  {i+1}. {area.code}: {area.name} ({area.kana})")
                print()
            
            # 3. 地域コード検証テスト
            print("3. 地域コード検証テスト")
            test_codes = ["130000", "270000", "invalid", "12345", "1234567"]
            
            for code in test_codes:
                is_valid = weather_service.validate_area_code(code)
                print(f"'{code}': {'有効' if is_valid else '無効'}")
            print()
            
            # 4. 有効な地域コード取得テスト
            print("4. 有効な地域コード取得テスト")
            test_inputs = ["東京", "130000", "大阪府", "invalid_area"]
            
            for input_str in test_inputs:
                valid_code = await weather_service.get_valid_area_code(input_str)
                if valid_code:
                    area_info = area_dict.get(valid_code)
                    area_name = area_info.name if area_info else "不明"
                    print(f"'{input_str}' -> {valid_code} ({area_name})")
                else:
                    print(f"'{input_str}' -> 見つかりません")
            
        except Exception as e:
            print(f"エラーが発生しました: {e}")
            import traceback
            traceback.print_exc()


if __name__ == "__main__":
    asyncio.run(test_area_functions())