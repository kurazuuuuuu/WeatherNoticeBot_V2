#!/usr/bin/env python3
"""
気象庁APIの地域コードを確認するスクリプト
"""

import asyncio
import sys
import os
import json
import aiohttp

# プロジェクトのルートディレクトリをパスに追加
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

# 地域コードのリスト
AREA_CODES = [
    # 北海道
    "016000", "017000", "012000", "014000", "014100",
    # 東北
    "020000", "040000", "050000", "060000", "030000", "070000",
    # 関東
    "130000", "140000", "110000", "120000", "080000", "090000", "100000",
    # 中部
    "150000", "160000", "170000", "180000", "190000", "200000", "210000", "220000", "230000",
    # 近畿
    "270000", "260000", "280000", "290000", "250000", "300000", "240000",
    # 中国
    "310000", "320000", "330000", "340000", "350000",
    # 四国
    "360000", "370000", "380000", "390000",
    # 九州・沖縄
    "400000", "410000", "420000", "430000", "440000", "450000", "460100", "471000", "474000",
    # 福岡の別の形式を試す
    "400010", "400020", "400030"
]

async def check_area_code(session, area_code):
    """地域コードの有効性を確認"""
    url = f"https://www.jma.go.jp/bosai/forecast/data/forecast/{area_code}.json"
    try:
        async with session.get(url) as response:
            if response.status == 200:
                return area_code, True, "OK"
            else:
                return area_code, False, f"HTTP {response.status}"
    except Exception as e:
        return area_code, False, str(e)

async def main():
    """メイン関数"""
    print("気象庁API 地域コード確認")
    print("=" * 50)
    
    async with aiohttp.ClientSession() as session:
        tasks = [check_area_code(session, code) for code in AREA_CODES]
        results = await asyncio.gather(*tasks)
        
        valid_codes = []
        invalid_codes = []
        
        for code, is_valid, message in results:
            if is_valid:
                valid_codes.append((code, message))
            else:
                invalid_codes.append((code, message))
        
        print("\n有効な地域コード:")
        for code, message in valid_codes:
            print(f"  {code}: {message}")
        
        print("\n無効な地域コード:")
        for code, message in invalid_codes:
            print(f"  {code}: {message}")
        
        # 有効なコードの一つからデータ構造を確認
        if valid_codes:
            sample_code = valid_codes[0][0]
            url = f"https://www.jma.go.jp/bosai/forecast/data/forecast/{sample_code}.json"
            async with session.get(url) as response:
                data = await response.json()
                print("\nデータ構造サンプル:")
                if data and len(data) > 0:
                    # 地域情報を抽出
                    areas = []
                    for forecast in data:
                        for time_series in forecast.get('timeSeries', []):
                            for area in time_series.get('areas', []):
                                area_info = area.get('area', {})
                                if area_info:
                                    areas.append((area_info.get('code', ''), area_info.get('name', '')))
                    
                    # 重複を削除
                    unique_areas = list(set(areas))
                    print("地域情報:")
                    for code, name in unique_areas:
                        print(f"  {code}: {name}")

if __name__ == "__main__":
    asyncio.run(main())