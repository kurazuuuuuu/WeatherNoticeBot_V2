"""
WeatherServiceの拡張機能

主要都市リスト機能を実装するための拡張
"""

import logging
from typing import Dict, List, Optional, Any
from ..models.weather import AreaInfo
from ..models.major_cities import MajorCity, RegionCities, MAJOR_CITIES_DATA, PREFECTURE_TO_REGION, JAPAN_REGIONS


class WeatherServiceMajorCitiesExtension:
    """WeatherServiceの主要都市機能拡張"""
    
    async def get_major_cities(self) -> Dict[str, RegionCities]:
        """
        主要都市のリストを地域別に取得
        
        Returns:
            地域コードをキーとした主要都市情報の辞書
            
        Raises:
            WeatherAPIError: API呼び出しに失敗した場合
        """
        self.logger.info("主要都市リストを取得しています")
        
        # 地域情報を取得
        area_dict = await self.get_area_list()
        
        # 地域ごとの都市リスト
        region_cities: Dict[str, List[MajorCity]] = {
            region_code: [] for region_code in JAPAN_REGIONS.keys()
        }
        
        # 主要都市データと地域コードをマッピング
        for city_data in MAJOR_CITIES_DATA:
            city_name = city_data["name"]
            prefecture = city_data["prefecture"]
            
            # 地域コードを検索
            matches = []
            for area_code, area_info in area_dict.items():
                if city_name in area_info.name and self._is_city_code(area_code):
                    matches.append((area_code, area_info))
            
            if not matches:
                self.logger.warning(f"都市 '{city_name}' の地域コードが見つかりませんでした")
                continue
                
            # 最適なマッチを選択（完全一致を優先）
            best_match = None
            for area_code, area_info in matches:
                if area_info.name == city_name:
                    best_match = (area_code, area_info)
                    break
            
            if best_match is None and matches:
                best_match = matches[0]
                
            if best_match:
                area_code, area_info = best_match
                
                # 地域を特定
                region_code = PREFECTURE_TO_REGION.get(prefecture, "other")
                
                # MajorCityオブジェクトを作成
                major_city = MajorCity(
                    code=area_code,
                    name=city_data["name"],
                    en_name=city_data["en_name"],
                    kana=city_data["kana"],
                    parent=area_info.parent,
                    prefecture=prefecture,
                    region=region_code
                )
                
                # 地域リストに追加
                if region_code in region_cities:
                    region_cities[region_code].append(major_city)
        
        # RegionCitiesオブジェクトを作成
        result = {}
        for region_code, cities in region_cities.items():
            if cities:  # 都市がある地域のみ追加
                region_info = JAPAN_REGIONS[region_code]
                result[region_code] = RegionCities(
                    region_name=region_info["name"],
                    region_en_name=region_info["en_name"],
                    cities=sorted(cities, key=lambda x: x.name)
                )
        
        self.logger.info(f"主要都市リストを取得しました: {sum(len(r.cities) for r in result.values())}件")
        return result
    
    def _is_city_code(self, area_code: str) -> bool:
        """
        地域コードが都市コードかどうかを判定
        
        Args:
            area_code: 地域コード
            
        Returns:
            都市コードの場合True
        """
        # 気象庁APIの都市コードは通常6桁の数字で、特定のパターンを持つ
        if not area_code or not isinstance(area_code, str):
            return False
            
        # 数字のみで構成されているかチェック
        if not area_code.isdigit():
            return False
            
        # 長さをチェック（通常は6桁）
        if len(area_code) != 6:
            return False
            
        # 都市コードの特定パターン（最後の2桁が00でない）
        # これは気象庁APIの仕様に基づく推測であり、実際の仕様に合わせて調整が必要
        if area_code.endswith("00"):
            return False
            
        return True