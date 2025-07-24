#!/usr/bin/env python3
"""
気象庁APIから都道府県コードを確認するスクリプト
"""

import asyncio
import sys
import os
import json
import aiohttp

# プロジェクトのルートディレクトリをパスに追加
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

# 都道府県コードのリスト
PREFECTURE_CODES = [
    # 北海道
    "010000", "011000", "012000", "013000", "014000", "015000", "016000", "017000",
    # 東北
    "020000", "030000", "040000", "050000", "060000", "070000",
    # 関東
    "080000", "090000", "100000", "110000", "120000", "130000", "140000",
    # 中部
    "150000", "160000", "170000", "180000", "190000", "200000", "210000", "220000", "230000",
    # 近畿
    "240000", "250000", "260000", "270000", "280000", "290000", "300000",
    # 中国
    "310000", "320000", "330000", "340000", "350000",
    # 四国
    "360000", "370000", "380000", "390000",
    # 九州・沖縄
    "400000", "410000", "420000", "430000", "440000", "450000", "460000", "470000"
]

async def check_prefecture_code(session, code):
    """都道府県コードの有効性を確認"""
    url = f"https://www.jma.go.jp/bosai/forecast/data/forecast/{code}.json"
    try:
        async with session.get(url) as response:
            if response.status == 200:
                data = await response.json()
                # 都道府県名を取得
                prefecture_name = "不明"
                if data and len(data) > 0:
                    office = data[0].get('publishingOffice', '')
                    if office:
                        prefecture_name = office
                return code, True, prefecture_name
            else:
                return code, False, f"HTTP {response.status}"
    except Exception as e:
        return code, False, str(e)

async def main():
    """メイン関数"""
    print("気象庁API 都道府県コード確認")
    print("=" * 50)
    
    async with aiohttp.ClientSession() as session:
        tasks = [check_prefecture_code(session, code) for code in PREFECTURE_CODES]
        results = await asyncio.gather(*tasks)
        
        valid_codes = []
        invalid_codes = []
        
        for code, is_valid, message in results:
            if is_valid:
                valid_codes.append((code, message))
            else:
                invalid_codes.append((code, message))
        
        print("\n有効な都道府県コード:")
        for code, name in valid_codes:
            print(f"  \"{name}\": \"{code}\",")
        
        print("\n無効な都道府県コード:")
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