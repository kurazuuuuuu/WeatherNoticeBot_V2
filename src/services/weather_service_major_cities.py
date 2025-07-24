"""
WeatherServiceの主要都市機能

主要都市リスト機能を実装するためのWeatherServiceの拡張
"""

import logging
from typing import Dict, List, Optional, Tuple
from ..models.weather import AreaInfo
from ..models.major_cities import MajorCity, RegionCities, MAJOR_CITIES_DATA, PREFECTURE_TO_REGION, JAPAN_REGIONS, CITY_CODE_CACHE
from ..models.city_codes import CITY_CODES


class WeatherServiceMajorCities:
    """WeatherServiceの主要都市機能"""
    
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
            
            # 1. 事前定義された地域コードを確認
            if city_name in CITY_CODES:
                area_code = CITY_CODES[city_name]
                area_info = None
                
                # 地域コードが存在するか確認
                if area_code in area_dict:
                    area_info = area_dict[area_code]
                else:
                    # 親地域を探す
                    parent_code = area_code[:4] + "00"
                    if parent_code in area_dict:
                        area_code = parent_code
                        area_info = area_dict[parent_code]
                    else:
                        # 都道府県レベルのコードを探す
                        prefecture_code = area_code[:2] + "0000"
                        if prefecture_code in area_dict:
                            area_code = prefecture_code
                            area_info = area_dict[prefecture_code]
                
                if area_info:
                    # キャッシュに保存
                    CITY_CODE_CACHE[city_name] = area_code
                    
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
                    continue
            
            # 2. キャッシュから地域コードを取得
            if city_name in CITY_CODE_CACHE:
                area_code = CITY_CODE_CACHE[city_name]
                area_info = area_dict.get(area_code)
                if area_info:
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
                    continue
            
            # 3. 地域コードを検索
            area_code, area_info = await self._find_city_code(city_name, area_dict)
            
            if area_code and area_info:
                # キャッシュに保存
                CITY_CODE_CACHE[city_name] = area_code
                
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
    
    async def _find_city_code(self, city_name: str, area_dict: Dict[str, AreaInfo]) -> Tuple[Optional[str], Optional[AreaInfo]]:
        """
        都市名から地域コードを検索
        
        Args:
            city_name: 都市名
            area_dict: 地域情報辞書
            
        Returns:
            (地域コード, 地域情報)のタプル。見つからない場合は(None, None)
        """
        # 1. 事前定義された地域コードを確認
        if city_name in CITY_CODES:
            area_code = CITY_CODES[city_name]
            if area_code in area_dict:
                return area_code, area_dict[area_code]
            
            # 地域コードが見つからない場合は、親地域を探す
            # 例: 130010 (東京地方) が見つからない場合、130000 (東京都) を探す
            parent_code = area_code[:4] + "00"
            if parent_code in area_dict:
                return parent_code, area_dict[parent_code]
                
            # 都道府県レベルのコードを探す
            prefecture_code = area_code[:2] + "0000"
            if prefecture_code in area_dict:
                return prefecture_code, area_dict[prefecture_code]
        
        matches = []
        
        # 2. 完全一致検索
        for area_code, area_info in area_dict.items():
            if city_name == area_info.name and self._is_city_code(area_code):
                return area_code, area_info
        
        # 3. 部分一致検索
        for area_code, area_info in area_dict.items():
            if city_name in area_info.name and self._is_city_code(area_code):
                matches.append((area_code, area_info))
        
        # 最適なマッチを選択
        if matches:
            # 名前の長さが最も近いものを選択
            matches.sort(key=lambda x: abs(len(x[1].name) - len(city_name)))
            return matches[0]
        
        # 見つからない場合
        self.logger.warning(f"都市 '{city_name}' の地域コードが見つかりませんでした")
        return None, None
    
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
    
    async def get_city_by_region(self, region_code: str) -> Optional[RegionCities]:
        """
        指定した地域の主要都市リストを取得
        
        Args:
            region_code: 地域コード
            
        Returns:
            地域の主要都市情報。見つからない場合はNone
        """
        if region_code not in JAPAN_REGIONS:
            return None
            
        all_regions = await self.get_major_cities()
        return all_regions.get(region_code)
    
    async def get_all_regions(self) -> List[Dict[str, str]]:
        """
        すべての地域情報を取得
        
        Returns:
            地域情報のリスト
        """
        return [
            {
                "code": code,
                "name": info["name"],
                "en_name": info["en_name"]
            }
            for code, info in JAPAN_REGIONS.items()
        ]