#!/usr/bin/env python3
"""
気象庁APIから特定の地域コードを確認するスクリプト
"""

import asyncio
import sys
import os
import json
import aiohttp

# プロジェクトのルートディレクトリをパスに追加
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

# 確認する地域コード
AREA_CODES = [
    # 鹿児島
    "460100", "460000", "461000",
    # 沖縄
    "471000", "470000", "471010", "471100", "472000", "473000", "474000"
]

async def check_area_code(session, code):
    """地域コードの有効性を確認"""
    url = f"https://www.jma.go.jp/bosai/forecast/data/forecast/{code}.json"
    try:
        async with session.get(url) as response:
            if response.status == 200:
                data = await response.json()
                # 地域名を取得
                area_name = "不明"
                if data and len(data) > 0:
                    office = data[0].get('publishingOffice', '')
                    if office:
                        area_name = office
                return code, True, area_name
            else:
                return code, False, f"HTTP {response.status}"
    except Exception as e:
        return code, False, str(e)

async def main():
    """メイン関数"""
    print("気象庁API 特定地域コード確認")
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
        for code, name in valid_codes:
            print(f"  \"{name}\": \"{code}\",")
        
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