#!/usr/bin/env python3
"""
気象庁APIから公式の地域コードリストを取得するスクリプト
"""

import asyncio
import sys
import os
import json
import aiohttp

# プロジェクトのルートディレクトリをパスに追加
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

async def get_area_list():
    """地域情報を取得"""
    url = "https://www.jma.go.jp/bosai/common/const/area.json"
    async with aiohttp.ClientSession() as session:
        async with session.get(url) as response:
            if response.status == 200:
                return await response.json()
            else:
                print(f"エラー: HTTP {response.status}")
                return None

def extract_city_codes(area_data):
    """地域コードを抽出"""
    city_codes = {}
    
    # 各カテゴリを処理
    for category_name, category_data in area_data.items():
        if isinstance(category_data, dict):
            # 各地域情報を処理
            for area_code, area_info in category_data.items():
                if isinstance(area_info, dict) and 'name' in area_info:
                    name = area_info.get('name', '')
                    if name:
                        # 都市名をキーとして地域コードを保存
                        if name in city_codes:
                            city_codes[name].append((area_code, category_name))
                        else:
                            city_codes[name] = [(area_code, category_name)]
    
    return city_codes

async def main():
    """メイン関数"""
    print("気象庁API 公式地域コードリスト取得")
    print("=" * 50)
    
    area_data = await get_area_list()
    if not area_data:
        print("地域情報の取得に失敗しました")
        return
    
    # カテゴリ情報を表示
    print("\nカテゴリ一覧:")
    for category in area_data.keys():
        print(f"  {category}")
    
    # 地域コードを抽出
    city_codes = extract_city_codes(area_data)
    
    # 主要都市の地域コードを表示
    target_cities = [
        "札幌", "函館", "旭川", "帯広", "釧路",
        "青森", "仙台", "秋田", "山形", "盛岡", "福島", "郡山",
        "東京", "横浜", "さいたま", "千葉", "水戸", "宇都宮", "前橋",
        "新潟", "富山", "金沢", "福井", "甲府", "長野", "岐阜", "静岡", "名古屋",
        "大阪", "京都", "神戸", "奈良", "大津", "和歌山", "津",
        "鳥取", "松江", "岡山", "広島", "山口",
        "徳島", "高松", "松山", "高知",
        "福岡", "佐賀", "長崎", "熊本", "大分", "宮崎", "鹿児島", "那覇"
    ]
    
    print("\n主要都市の地域コード:")
    for city in target_cities:
        if city in city_codes:
            codes = city_codes[city]
            print(f"\n{city}:")
            for code, category in codes:
                print(f"  {code} ({category})")
        else:
            print(f"\n{city}: 見つかりません")
    
    # 地域コードの検証
    print("\n地域コードの検証:")
    async with aiohttp.ClientSession() as session:
        tasks = []
        for city in target_cities:
            if city in city_codes:
                for code, category in city_codes[city]:
                    url = f"https://www.jma.go.jp/bosai/forecast/data/forecast/{code}.json"
                    tasks.append((city, code, category, session.get(url)))
        
        for city, code, category, task in tasks:
            try:
                response = await task
                status = response.status
                if status == 200:
                    print(f"  {city} ({code}, {category}): OK")
                else:
                    print(f"  {city} ({code}, {category}): エラー (HTTP {status})")
            except Exception as e:
                print(f"  {city} ({code}, {category}): 例外 ({str(e)})")
    
    # 推奨コードの生成
    print("\n推奨地域コード:")
    recommended_codes = {}
    
    for city in target_cities:
        if city in city_codes:
            valid_codes = []
            for code, category in city_codes[city]:
                url = f"https://www.jma.go.jp/bosai/forecast/data/forecast/{code}.json"
                async with aiohttp.ClientSession() as session:
                    async with session.get(url) as response:
                        if response.status == 200:
                            valid_codes.append((code, category))
            
            if valid_codes:
                # 優先順位: offices > class10s > class15s > class20s > centers
                priority = {"offices": 1, "class10s": 2, "class15s": 3, "class20s": 4, "centers": 5}
                valid_codes.sort(key=lambda x: priority.get(x[1], 99))
                recommended_codes[city] = valid_codes[0][0]
                print(f"  \"{city}\": \"{valid_codes[0][0]}\",")
    
    # 推奨コードをファイルに保存
    with open("recommended_city_codes.py", "w", encoding="utf-8") as f:
        f.write("# 推奨地域コード\n")
        f.write("RECOMMENDED_CITY_CODES = {\n")
        for city, code in recommended_codes.items():
            f.write(f"    \"{city}\": \"{code}\",\n")
        f.write("}\n")
    
    print("\n推奨コードを recommended_city_codes.py に保存しました")

if __name__ == "__main__":
    asyncio.run(main())