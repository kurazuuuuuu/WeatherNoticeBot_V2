#!/usr/bin/env python3
"""
天気予報APIのレスポンス構造を確認するデバッグスクリプト
"""

import asyncio
import json
import sys
import os

# プロジェクトのルートディレクトリをパスに追加
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from src.services.weather_service import WeatherService


async def debug_forecast_structure():
    """天気予報APIレスポンス構造をデバッグ"""
    print("=== 天気予報API レスポンス構造デバッグ ===\n")
    
    async with WeatherService() as weather_service:
        try:
            # 東京都の天気予報データを取得
            test_area_code = "130000"
            url = weather_service._build_forecast_url(test_area_code)
            print(f"URL: {url}")
            
            data = await weather_service._make_request(url)
            
            print(f"レスポンス配列の長さ: {len(data)}")
            
            # 全ての要素を確認
            for data_index, forecast_data in enumerate(data):
                print(f"\n=== data[{data_index}] ===")
                print(f"キー: {list(forecast_data.keys())}")
                
                # timeSeriesの構造を確認
                time_series = forecast_data.get('timeSeries', [])
                print(f"timeSeries配列の長さ: {len(time_series)}")
                
                for i, series in enumerate(time_series):
                    print(f"\n--- data[{data_index}].timeSeries[{i}] ---")
                    print(f"キー: {list(series.keys())}")
                    
                    # timeDefinesを確認
                    time_defines = series.get('timeDefines', [])
                    print(f"timeDefines数: {len(time_defines)}")
                    if time_defines:
                        print(f"最初のtimeDefine: {time_defines[0]}")
                        if len(time_defines) > 1:
                            print(f"2番目のtimeDefine: {time_defines[1]}")
                        if len(time_defines) > 2:
                            print(f"最後のtimeDefine: {time_defines[-1]}")
                    
                    # areasを確認
                    areas = series.get('areas', [])
                    if areas:
                        area = areas[0]
                        print(f"area情報のキー: {list(area.keys())}")
                        
                        # 各データの最初の数個を表示
                        for key, value in area.items():
                            if isinstance(value, list):
                                print(f"  {key}: {value[:5] if len(value) > 5 else value}")
                            elif isinstance(value, dict):
                                print(f"  {key}: {value}")
                            else:
                                print(f"  {key}: {value}")
                
                # 週間予報データを探す
                print(f"\n=== data[{data_index}]の週間予報データの検索 ===")
                for i, series in enumerate(time_series):
                    time_defines = series.get('timeDefines', [])
                    if len(time_defines) >= 5:  # 5日以上のデータがある
                        print(f"週間予報候補: timeSeries[{i}]")
                        print(f"  timeDefines数: {len(time_defines)}")
                        print(f"  最初の日付: {time_defines[0]}")
                        print(f"  最後の日付: {time_defines[-1]}")
                        
                        areas = series.get('areas', [])
                        if areas:
                            area = areas[0]
                            print(f"  利用可能なデータ: {list(area.keys())}")
            
        except Exception as e:
            print(f"エラーが発生しました: {e}")
            import traceback
            traceback.print_exc()


if __name__ == "__main__":
    asyncio.run(debug_forecast_structure())