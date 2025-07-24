"""
気象庁APIサービス

日本気象庁のAPIを使用して天気情報を取得するサービス
"""

import asyncio
import logging
import json
import time
from typing import Dict, List, Optional, Any
from datetime import datetime, date
import aiohttp
from aiohttp import ClientTimeout, ClientError, ClientResponseError

from ..models.weather import AreaInfo, WeatherData, ForecastData, AlertData
from ..models.major_cities import MajorCity, RegionCities, MAJOR_CITIES_DATA, PREFECTURE_TO_REGION, JAPAN_REGIONS
from .weather_service_major_cities import WeatherServiceMajorCities


class WeatherAPIError(Exception):
    """気象庁API関連のエラー"""
    def __init__(self, message: str, status_code: Optional[int] = None, retry_after: Optional[int] = None):
        super().__init__(message)
        self.status_code = status_code
        self.retry_after = retry_after


class WeatherAPIRateLimitError(WeatherAPIError):
    """レート制限エラー"""
    pass


class WeatherAPIServerError(WeatherAPIError):
    """サーバーエラー"""
    pass


class WeatherAPITimeoutError(WeatherAPIError):
    """タイムアウトエラー"""
    pass


class WeatherService(WeatherServiceMajorCities):
    """気象庁APIサービス"""
    
    # 気象庁APIのベースURL
    BASE_URL = "https://www.jma.go.jp/bosai"
    
    # リトライ設定
    MAX_RETRIES = 3
    RETRY_DELAY = 1.0  # 秒
    BACKOFF_FACTOR = 2.0
    MAX_RETRY_DELAY = 60.0  # 最大リトライ間隔
    
    # タイムアウト設定
    REQUEST_TIMEOUT = 30  # 秒
    CONNECT_TIMEOUT = 10  # 接続タイムアウト
    
    # レート制限設定
    RATE_LIMIT_WINDOW = 60  # 1分間のウィンドウ
    MAX_REQUESTS_PER_WINDOW = 100  # 1分間の最大リクエスト数
    
    # キャッシュ設定
    CACHE_DURATION = 300  # 5分間のキャッシュ
    
    def __init__(self):
        """WeatherServiceの初期化"""
        self.logger = logging.getLogger(__name__)
        self.session: Optional[aiohttp.ClientSession] = None
        
        # レート制限管理
        self._request_times: List[float] = []
        self._last_request_time = 0.0
        
        # 簡易キャッシュ
        self._cache: Dict[str, Dict[str, Any]] = {}
        self._cache_timestamps: Dict[str, float] = {}
        
    async def __aenter__(self):
        """非同期コンテキストマネージャーの開始"""
        await self.start_session()
        return self
        
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """非同期コンテキストマネージャーの終了"""
        await self.close_session()
        
    async def start_session(self):
        """HTTPセッションを開始"""
        if self.session is None or self.session.closed:
            timeout = ClientTimeout(
                total=self.REQUEST_TIMEOUT,
                connect=self.CONNECT_TIMEOUT
            )
            connector = aiohttp.TCPConnector(
                limit=10,  # 最大接続数
                limit_per_host=5,  # ホスト毎の最大接続数
                ttl_dns_cache=300,  # DNS キャッシュTTL
                use_dns_cache=True,
            )
            self.session = aiohttp.ClientSession(
                timeout=timeout,
                connector=connector,
                headers={
                    'User-Agent': 'WeatherBot/1.0 (Discord Bot)',
                    'Accept': 'application/json',
                    'Accept-Encoding': 'gzip, deflate'
                }
            )
            self.logger.info("HTTPセッションを開始しました")
            
    async def close_session(self):
        """HTTPセッションを終了"""
        if self.session and not self.session.closed:
            await self.session.close()
            self.logger.info("HTTPセッションを終了しました")
            
    def _is_cache_valid(self, cache_key: str) -> bool:
        """キャッシュが有効かどうかをチェック"""
        if cache_key not in self._cache_timestamps:
            return False
        
        cache_time = self._cache_timestamps[cache_key]
        return (time.time() - cache_time) < self.CACHE_DURATION
    
    def _get_from_cache(self, cache_key: str) -> Optional[Dict[str, Any]]:
        """キャッシュからデータを取得"""
        if self._is_cache_valid(cache_key):
            self.logger.debug(f"キャッシュからデータを取得: {cache_key}")
            return self._cache.get(cache_key)
        return None
    
    def _set_cache(self, cache_key: str, data: Dict[str, Any]) -> None:
        """データをキャッシュに保存"""
        self._cache[cache_key] = data
        self._cache_timestamps[cache_key] = time.time()
        self.logger.debug(f"データをキャッシュに保存: {cache_key}")
    
    def _check_rate_limit(self) -> None:
        """レート制限をチェック"""
        current_time = time.time()
        
        # 古いリクエスト時刻を削除
        self._request_times = [
            req_time for req_time in self._request_times
            if current_time - req_time < self.RATE_LIMIT_WINDOW
        ]
        
        # レート制限チェック
        if len(self._request_times) >= self.MAX_REQUESTS_PER_WINDOW:
            raise WeatherAPIRateLimitError(
                f"レート制限に達しました。{self.RATE_LIMIT_WINDOW}秒後に再試行してください。"
            )
        
        # 現在のリクエスト時刻を記録
        self._request_times.append(current_time)
        self._last_request_time = current_time
    
    async def _make_request(self, url: str, retries: int = 0, use_cache: bool = True) -> Dict[str, Any]:
        """
        HTTPリクエストを実行（リトライ機能付き）
        
        Args:
            url: リクエストURL
            retries: 現在のリトライ回数
            use_cache: キャッシュを使用するかどうか
            
        Returns:
            APIレスポンスのJSONデータ
            
        Raises:
            WeatherAPIError: API呼び出しに失敗した場合
        """
        # キャッシュチェック
        cache_key = url
        if use_cache:
            cached_data = self._get_from_cache(cache_key)
            if cached_data is not None:
                return cached_data
        
        # レート制限チェック
        try:
            self._check_rate_limit()
        except WeatherAPIRateLimitError as e:
            if retries < self.MAX_RETRIES:
                delay = min(self.RETRY_DELAY * (self.BACKOFF_FACTOR ** retries), self.MAX_RETRY_DELAY)
                self.logger.warning(f"レート制限のためリトライします ({retries + 1}/{self.MAX_RETRIES}) - {delay}秒後")
                await asyncio.sleep(delay)
                return await self._make_request(url, retries + 1, use_cache)
            else:
                raise
        
        if self.session is None or self.session.closed:
            await self.start_session()
            
        try:
            self.logger.debug(f"APIリクエスト開始: {url}")
            
            async with self.session.get(url) as response:
                # レスポンスヘッダーからレート制限情報を取得
                retry_after = None
                if 'Retry-After' in response.headers:
                    try:
                        retry_after = int(response.headers['Retry-After'])
                    except ValueError:
                        pass
                
                # HTTPステータスコードをチェック
                if response.status == 200:
                    try:
                        data = await response.json()
                        self.logger.debug(f"APIリクエスト成功: {url}")
                        
                        # キャッシュに保存
                        if use_cache:
                            self._set_cache(cache_key, data)
                        
                        return data
                    except json.JSONDecodeError as e:
                        self.logger.error(f"JSONデコードエラー: {url} - {str(e)}")
                        raise WeatherAPIError(f"レスポンスのJSONデコードに失敗しました: {str(e)}")
                        
                elif response.status == 429:  # レート制限
                    self.logger.warning(f"レート制限に達しました: {url}")
                    raise WeatherAPIRateLimitError(
                        f"レート制限に達しました (HTTP {response.status})",
                        status_code=response.status,
                        retry_after=retry_after
                    )
                    
                elif response.status == 404:  # Not Found
                    self.logger.warning(f"リソースが見つかりません: {url}")
                    raise WeatherAPIError(
                        f"リソースが見つかりません (HTTP {response.status})",
                        status_code=response.status
                    )
                    
                elif response.status >= 500:  # サーバーエラー
                    self.logger.warning(f"サーバーエラー: {url} (HTTP {response.status})")
                    raise WeatherAPIServerError(
                        f"サーバーエラー (HTTP {response.status})",
                        status_code=response.status,
                        retry_after=retry_after
                    )
                    
                else:
                    self.logger.error(f"APIリクエスト失敗: {url} (HTTP {response.status})")
                    raise WeatherAPIError(
                        f"APIリクエスト失敗 (HTTP {response.status})",
                        status_code=response.status
                    )
                    
        except asyncio.TimeoutError:
            self.logger.error(f"タイムアウトエラー: {url}")
            
            # タイムアウトの場合もリトライ
            if retries < self.MAX_RETRIES:
                delay = min(self.RETRY_DELAY * (self.BACKOFF_FACTOR ** retries), self.MAX_RETRY_DELAY)
                self.logger.info(f"タイムアウトのためリトライします ({retries + 1}/{self.MAX_RETRIES}) - {delay}秒後")
                await asyncio.sleep(delay)
                return await self._make_request(url, retries + 1, use_cache)
            else:
                raise WeatherAPITimeoutError(f"リクエストがタイムアウトしました: {url}")
                
        except ClientResponseError as e:
            self.logger.error(f"HTTPレスポンスエラー: {url} - {str(e)}")
            
            # サーバーエラーの場合はリトライ
            if e.status >= 500 and retries < self.MAX_RETRIES:
                delay = min(self.RETRY_DELAY * (self.BACKOFF_FACTOR ** retries), self.MAX_RETRY_DELAY)
                self.logger.info(f"サーバーエラーのためリトライします ({retries + 1}/{self.MAX_RETRIES}) - {delay}秒後")
                await asyncio.sleep(delay)
                return await self._make_request(url, retries + 1, use_cache)
            else:
                raise WeatherAPIError(f"HTTPレスポンスエラー: {str(e)}", status_code=e.status)
                
        except ClientError as e:
            self.logger.error(f"ネットワークエラー: {url} - {str(e)}")
            
            # ネットワークエラーの場合もリトライ
            if retries < self.MAX_RETRIES:
                delay = min(self.RETRY_DELAY * (self.BACKOFF_FACTOR ** retries), self.MAX_RETRY_DELAY)
                self.logger.info(f"ネットワークエラーのためリトライします ({retries + 1}/{self.MAX_RETRIES}) - {delay}秒後")
                await asyncio.sleep(delay)
                return await self._make_request(url, retries + 1, use_cache)
            else:
                raise WeatherAPIError(f"ネットワークエラー: {str(e)}")
                
        except Exception as e:
            self.logger.error(f"予期しないエラー: {url} - {str(e)}")
            raise WeatherAPIError(f"予期しないエラー: {str(e)}")
            
    async def get_api_contents(self) -> Dict[str, Any]:
        """
        APIの利用可能なコンテンツ情報を取得
        
        Returns:
            利用可能なAPIコンテンツの情報
            
        Raises:
            WeatherAPIError: API呼び出しに失敗した場合
        """
        url = f"{self.BASE_URL}/common/const/contents.json"
        return await self._make_request(url)
        
    def _build_forecast_url(self, area_code: str) -> str:
        """天気予報APIのURLを構築"""
        return f"{self.BASE_URL}/forecast/data/forecast/{area_code}.json"
        
    def _build_warning_url(self, area_code: str) -> str:
        """気象警報APIのURLを構築"""
        return f"{self.BASE_URL}/warning/data/warning/{area_code}.json"
        
    def _build_area_url(self) -> str:
        """地域情報APIのURLを構築"""
        return f"{self.BASE_URL}/common/const/area.json"
        
    async def get_area_list(self) -> Dict[str, AreaInfo]:
        """
        地域情報を取得 (area.json)
        
        Returns:
            地域コードをキーとした地域情報の辞書
            
        Raises:
            WeatherAPIError: API呼び出しに失敗した場合
        """
        url = self._build_area_url()
        data = await self._make_request(url)
        
        area_dict = {}
        
        # 各地域カテゴリを処理
        # データ構造: {centers: {code: info}, offices: {code: info}, class10s: {code: info}, ...}
        for category_name, category_data in data.items():
            if isinstance(category_data, dict):
                # 各カテゴリ内の地域情報を処理
                for area_code, area_info in category_data.items():
                    if isinstance(area_info, dict):
                        area_dict[area_code] = AreaInfo(
                            code=area_code,
                            name=area_info.get('name', ''),
                            en_name=area_info.get('enName', ''),
                            kana=area_info.get('kana', ''),
                            parent=area_info.get('parent', '')
                        )
        
        self.logger.info(f"地域情報を取得しました: {len(area_dict)}件")
        return area_dict
        
    async def search_area_by_name(self, area_name: str) -> List[AreaInfo]:
        """
        地域名から地域コードを検索
        漢字名、かな名、英語名での検索をサポート
        
        Args:
            area_name: 検索する地域名
            
        Returns:
            マッチした地域情報のリスト
            
        Raises:
            WeatherAPIError: API呼び出しに失敗した場合
        """
        area_dict = await self.get_area_list()
        search_name = area_name.strip().lower()
        matches = []
        
        for area_info in area_dict.values():
            # 漢字名での検索
            if search_name in area_info.name.lower():
                matches.append(area_info)
                continue
                
            # かな名での検索
            if search_name in area_info.kana.lower():
                matches.append(area_info)
                continue
                
            # 英語名での検索
            if search_name in area_info.en_name.lower():
                matches.append(area_info)
                continue
                
            # 部分一致検索（ひらがな・カタカナの変換も考慮）
            if self._is_similar_name(search_name, area_info.name):
                matches.append(area_info)
                continue
                
        # 完全一致を優先してソート
        matches.sort(key=lambda x: (
            x.name.lower() != search_name,  # 完全一致を最初に
            len(x.name),  # 短い名前を優先
            x.name
        ))
        
        self.logger.debug(f"地域検索結果: '{area_name}' -> {len(matches)}件")
        return matches
        
    def _is_similar_name(self, search_name: str, area_name: str) -> bool:
        """
        地域名の類似性をチェック
        ひらがな・カタカナの違いを考慮した検索
        
        Args:
            search_name: 検索文字列
            area_name: 地域名
            
        Returns:
            類似している場合True
        """
        # ひらがな・カタカナの変換テーブル
        hiragana_to_katakana = str.maketrans(
            'あいうえおかきくけこさしすせそたちつてとなにぬねのはひふへほまみむめもやゆよらりるれろわをん',
            'アイウエオカキクケコサシスセソタチツテトナニヌネノハヒフヘホマミムメモヤユヨラリルレロワヲン'
        )
        
        # 検索文字列をカタカナに変換
        search_katakana = search_name.translate(hiragana_to_katakana)
        area_katakana = area_name.translate(hiragana_to_katakana)
        
        return search_katakana in area_katakana or search_name in area_name.lower()
        
    def validate_area_code(self, area_code: str) -> bool:
        """
        地域コードの妥当性を検証
        
        Args:
            area_code: 検証する地域コード
            
        Returns:
            有効な地域コードの場合True
        """
        # 気象庁の地域コードは通常6桁の数字
        if not area_code or not isinstance(area_code, str):
            return False
            
        # 数字のみで構成されているかチェック
        if not area_code.isdigit():
            return False
            
        # 長さをチェック（通常は6桁）
        if len(area_code) != 6:
            return False
            
        return True
        
    async def get_valid_area_code(self, area_name_or_code: str) -> Optional[str]:
        """
        地域名または地域コードから有効な地域コードを取得
        
        Args:
            area_name_or_code: 地域名または地域コード
            
        Returns:
            有効な地域コード、見つからない場合はNone
            
        Raises:
            WeatherAPIError: API呼び出しに失敗した場合
        """
        # 既に有効な地域コードの場合
        if self.validate_area_code(area_name_or_code):
            # 実際に存在するかチェック
            area_dict = await self.get_area_list()
            if area_name_or_code in area_dict:
                return area_name_or_code
                
        # 地域名で検索
        matches = await self.search_area_by_name(area_name_or_code)
        if matches:
            # 最初のマッチを返す（完全一致が優先されている）
            return matches[0].code
            
        return None
        
    async def get_current_weather(self, area_code: str) -> Optional[WeatherData]:
        """
        現在の天気情報を取得
        
        Args:
            area_code: 地域コード
            
        Returns:
            天気データ、取得できない場合はNone
            
        Raises:
            WeatherAPIError: API呼び出しに失敗した場合
        """
        if not self.validate_area_code(area_code):
            raise WeatherAPIError(f"無効な地域コードです: {area_code}")
            
        url = self._build_forecast_url(area_code)
        data = await self._make_request(url)
        
        try:
            # 気象庁APIのレスポンス構造を解析
            if not data or len(data) == 0:
                self.logger.warning(f"天気データが空です: {area_code}")
                return None
                
            # 最初の予報データを取得
            forecast_data = data[0]
            
            # 発表時刻
            publish_time_str = forecast_data.get('reportDatetime', '')
            publish_time = datetime.fromisoformat(publish_time_str.replace('Z', '+00:00')) if publish_time_str else datetime.now()
            
            # 地域情報
            area_info = forecast_data.get('timeSeries', [{}])[0].get('areas', [{}])[0]
            area_name = area_info.get('area', {}).get('name', '')
            
            # 天気情報
            weather_codes = area_info.get('weatherCodes', [''])
            weather_code = weather_codes[0] if weather_codes else ''
            
            weathers = area_info.get('weathers', [''])
            weather_description = weathers[0] if weathers else ''
            
            # 風情報
            winds = area_info.get('winds', [''])
            wind = winds[0] if winds else ''
            
            # 波情報
            waves = area_info.get('waves', [''])
            wave = waves[0] if waves else ''
            
            # 降水確率
            pops = area_info.get('pops', [0])
            precipitation_probability = int(pops[0]) if pops and pops[0] else 0
            
            # 気温情報（別のtimeSeriesから取得）
            temperature = None
            temp_series = None
            for series in forecast_data.get('timeSeries', []):
                if 'temps' in series.get('areas', [{}])[0]:
                    temp_series = series
                    break
                    
            if temp_series:
                temp_area = temp_series.get('areas', [{}])[0]
                temps = temp_area.get('temps', [])
                if temps and temps[0]:
                    try:
                        temperature = float(temps[0])
                    except (ValueError, TypeError):
                        temperature = None
            
            return WeatherData(
                area_name=area_name,
                area_code=area_code,
                weather_code=weather_code,
                weather_description=weather_description,
                wind=wind,
                wave=wave,
                temperature=temperature,
                precipitation_probability=precipitation_probability,
                timestamp=datetime.now(),
                publish_time=publish_time
            )
            
        except (KeyError, IndexError, ValueError) as e:
            self.logger.error(f"天気データの解析に失敗しました: {area_code} - {str(e)}")
            raise WeatherAPIError(f"天気データの解析に失敗しました: {str(e)}")
            
    async def get_forecast(self, area_code: str, days: int = 7) -> List[ForecastData]:
        """
        天気予報を取得（最大7日間）
        
        Args:
            area_code: 地域コード
            days: 予報日数（最大7日）
            
        Returns:
            天気予報データのリスト
            
        Raises:
            WeatherAPIError: API呼び出しに失敗した場合
        """
        if not self.validate_area_code(area_code):
            raise WeatherAPIError(f"無効な地域コードです: {area_code}")
            
        if days > 7:
            days = 7
            self.logger.warning("予報日数を7日に制限しました")
            
        url = self._build_forecast_url(area_code)
        data = await self._make_request(url)
        
        try:
            forecasts = []
            
            if not data or len(data) == 0:
                self.logger.warning(f"予報データが空です: {area_code}")
                return forecasts
            
            # 週間予報データは通常2番目の要素にある
            weekly_forecast_data = None
            if len(data) > 1:
                weekly_forecast_data = data[1]
            else:
                # フォールバック: 最初の要素を使用
                weekly_forecast_data = data[0]
            
            # 天気情報（weatherCodes）と降水確率を取得
            weather_pop_series = None
            temp_series = None
            
            # 各timeSeriesから必要なデータを探す
            for series in weekly_forecast_data.get('timeSeries', []):
                areas = series.get('areas', [])
                if areas:
                    area_data = areas[0]
                    
                    # 天気コードと降水確率があるシリーズ
                    if 'weatherCodes' in area_data and 'pops' in area_data:
                        weather_pop_series = series
                    
                    # 気温情報があるシリーズ
                    if 'tempsMin' in area_data or 'tempsMax' in area_data:
                        temp_series = series
            
            # 最低限、天気情報が必要
            if not weather_pop_series:
                self.logger.warning(f"週間予報データが見つかりません: {area_code}")
                return forecasts
            
            # 基準となるtimeDefinesを取得
            time_defines = weather_pop_series.get('timeDefines', [])
            
            # 各日の予報データを作成
            for i in range(min(len(time_defines), days)):
                try:
                    # 日付を解析
                    date_str = time_defines[i]
                    forecast_date = datetime.fromisoformat(date_str.replace('Z', '+00:00')).date()
                    
                    # 天気情報と降水確率を取得
                    weather_area = weather_pop_series.get('areas', [{}])[0]
                    
                    # 天気コードを取得
                    weather_codes = weather_area.get('weatherCodes', [])
                    weather_code = weather_codes[i] if i < len(weather_codes) else ''
                    
                    # 週間予報では天気の詳細説明は通常提供されないため、天気コードから判定
                    weather_description = self._get_weather_description_from_code(weather_code)
                    
                    # 降水確率を取得
                    pops = weather_area.get('pops', [])
                    pop = int(pops[i]) if i < len(pops) and pops[i] and pops[i] != '' else 0
                    
                    # 信頼度を取得
                    reliabilities = weather_area.get('reliabilities', [])
                    reliability = reliabilities[i] if i < len(reliabilities) else ''
                    
                    # 気温データを取得
                    temp_min = None
                    temp_max = None
                    temp_min_upper = None
                    temp_min_lower = None
                    temp_max_upper = None
                    temp_max_lower = None
                    
                    if temp_series:
                        temp_area = temp_series.get('areas', [{}])[0]
                        temps_min = temp_area.get('tempsMin', [])
                        temps_max = temp_area.get('tempsMax', [])
                        temps_min_upper = temp_area.get('tempsMinUpper', [])
                        temps_min_lower = temp_area.get('tempsMinLower', [])
                        temps_max_upper = temp_area.get('tempsMaxUpper', [])
                        temps_max_lower = temp_area.get('tempsMaxLower', [])
                        
                        temp_min = self._safe_float(temps_min[i] if i < len(temps_min) else None)
                        temp_max = self._safe_float(temps_max[i] if i < len(temps_max) else None)
                        temp_min_upper = self._safe_float(temps_min_upper[i] if i < len(temps_min_upper) else None)
                        temp_min_lower = self._safe_float(temps_min_lower[i] if i < len(temps_min_lower) else None)
                        temp_max_upper = self._safe_float(temps_max_upper[i] if i < len(temps_max_upper) else None)
                        temp_max_lower = self._safe_float(temps_max_lower[i] if i < len(temps_max_lower) else None)
                    
                    forecast = ForecastData(
                        date=forecast_date,
                        weather_code=weather_code,
                        weather_description=weather_description,
                        temp_min=temp_min,
                        temp_max=temp_max,
                        temp_min_upper=temp_min_upper,
                        temp_min_lower=temp_min_lower,
                        temp_max_upper=temp_max_upper,
                        temp_max_lower=temp_max_lower,
                        precipitation_probability=pop,
                        reliability=''  # 週間予報では信頼度情報は通常提供されない
                    )
                    
                    forecasts.append(forecast)
                    
                except (ValueError, TypeError) as e:
                    self.logger.warning(f"予報データの解析をスキップしました: {i}日目 - {str(e)}")
                    continue
                    
            self.logger.info(f"天気予報を取得しました: {area_code} - {len(forecasts)}日分")
            return forecasts
            
        except (KeyError, IndexError) as e:
            self.logger.error(f"予報データの解析に失敗しました: {area_code} - {str(e)}")
            raise WeatherAPIError(f"予報データの解析に失敗しました: {str(e)}")
            
    def _safe_float(self, value) -> Optional[float]:
        """安全にfloat値に変換"""
        if value is None or value == '':
            return None
        try:
            return float(value)
        except (ValueError, TypeError):
            return None
            
    def _get_weather_description_from_code(self, weather_code: str) -> str:
        """
        天気コードから天気説明を取得
        
        Args:
            weather_code: 天気コード
            
        Returns:
            天気説明
        """
        # 気象庁の天気コード対応表（主要なもの）
        weather_code_map = {
            '100': '晴れ',
            '101': '晴れ時々くもり',
            '102': '晴れ一時雨',
            '103': '晴れ時々雨',
            '104': '晴れ一時雪',
            '105': '晴れ時々雪',
            '106': '晴れ一時雨か雪',
            '107': '晴れ時々雨か雪',
            '108': '晴れ一時雨か雷雨',
            '110': '晴れ後時々くもり',
            '111': '晴れ後くもり',
            '112': '晴れ後一時雨',
            '113': '晴れ後時々雨',
            '114': '晴れ後雨',
            '115': '晴れ後一時雪',
            '116': '晴れ後時々雪',
            '117': '晴れ後雪',
            '118': '晴れ後雨か雪',
            '119': '晴れ後雨か雷雨',
            '120': '晴れ朝夕一時雨',
            '121': '晴れ朝の内一時雨',
            '122': '晴れ夕方一時雨',
            '123': '晴れ山沿い雷雨',
            '124': '晴れ山沿い雪',
            '125': '晴れ午後は雷雨',
            '126': '晴れ昼頃から雨',
            '127': '晴れ夕方から雨',
            '128': '晴れ夜は雨',
            '130': '朝の内霧後晴れ',
            '131': '晴れ明け方霧',
            '132': '晴れ朝夕くもり',
            '140': '晴れ時々雨と雷雨',
            '160': '晴れ一時雪か雨',
            '170': '晴れ時々雪か雨',
            '181': '晴れ後雪か雨',
            '200': 'くもり',
            '201': 'くもり時々晴れ',
            '202': 'くもり一時雨',
            '203': 'くもり時々雨',
            '204': 'くもり一時雪',
            '205': 'くもり時々雪',
            '206': 'くもり一時雨か雪',
            '207': 'くもり時々雨か雪',
            '208': 'くもり一時雨か雷雨',
            '209': '霧',
            '210': 'くもり後時々晴れ',
            '211': 'くもり後晴れ',
            '212': 'くもり後一時雨',
            '213': 'くもり後時々雨',
            '214': 'くもり後雨',
            '215': 'くもり後一時雪',
            '216': 'くもり後時々雪',
            '217': 'くもり後雪',
            '218': 'くもり後雨か雪',
            '219': 'くもり後雨か雷雨',
            '220': 'くもり朝夕一時雨',
            '221': 'くもり朝の内一時雨',
            '222': 'くもり夕方一時雨',
            '223': 'くもり日中時々晴れ',
            '224': 'くもり昼頃から雨',
            '225': 'くもり夕方から雨',
            '226': 'くもり夜は雨',
            '228': 'くもり昼頃から雪',
            '229': 'くもり夕方から雪',
            '230': 'くもり夜は雪',
            '231': 'くもり海上海岸は霧か霧雨',
            '240': 'くもり時々雨と雷雨',
            '250': 'くもり時々雪と雷雨',
            '260': 'くもり一時雪か雨',
            '270': 'くもり時々雪か雨',
            '281': 'くもり後雪か雨',
            '300': '雨',
            '301': '雨時々晴れ',
            '302': '雨時々止む',
            '303': '雨時々雪',
            '304': '雨か雪',
            '306': '大雨',
            '308': '雨で暴風を伴う',
            '309': '雨一時雪',
            '311': '雨後晴れ',
            '313': '雨後くもり',
            '314': '雨後時々雪',
            '315': '雨後雪',
            '316': '雨か雪後晴れ',
            '317': '雨か雪後くもり',
            '320': '朝の内雨後晴れ',
            '321': '朝の内雨後くもり',
            '322': '雨朝晩一時雪',
            '323': '雨昼頃から晴れ',
            '324': '雨夕方から晴れ',
            '325': '雨夜は晴',
            '326': '雨夕方から雪',
            '327': '雨夜は雪',
            '328': '雨一時強く降る',
            '329': '雨一時みぞれ',
            '340': '雪か雨',
            '350': '雨で雷を伴う',
            '361': '雪か雨後晴れ',
            '371': '雪か雨後くもり',
            '400': '雪',
            '401': '雪時々晴れ',
            '402': '雪時々止む',
            '403': '雪時々雨',
            '405': '大雪',
            '406': '風雪強い',
            '407': '暴風雪',
            '409': '雪一時雨',
            '411': '雪後晴れ',
            '413': '雪後くもり',
            '414': '雪後雨',
            '420': '朝の内雪後晴れ',
            '421': '朝の内雪後くもり',
            '422': '雪昼頃から晴れ',
            '423': '雪夕方から晴れ',
            '425': '雪一時強く降る',
            '426': '雪後みぞれ',
            '427': '雪一時みぞれ',
            '450': '雪で雷を伴う'
        }
        
        return weather_code_map.get(weather_code, f'天気コード: {weather_code}')
            
    async def get_weather_alerts(self, area_code: str) -> List[AlertData]:
        """
        気象警報・注意報を取得
        
        Args:
            area_code: 地域コード
            
        Returns:
            気象警報データのリスト
            
        Raises:
            WeatherAPIError: API呼び出しに失敗した場合
        """
        if not self.validate_area_code(area_code):
            raise WeatherAPIError(f"無効な地域コードです: {area_code}")
            
        url = self._build_warning_url(area_code)
        
        try:
            data = await self._make_request(url)
        except WeatherAPIError as e:
            # 警報データが存在しない場合は空のリストを返す
            if "404" in str(e) or "Not Found" in str(e):
                self.logger.info(f"警報データが存在しません: {area_code}")
                return []
            raise
            
        try:
            alerts = []
            
            if not data:
                return alerts
                
            # 警報データの構造を解析
            for alert_type, alert_info in data.items():
                if isinstance(alert_info, dict):
                    # 発表時刻
                    issued_at_str = alert_info.get('reportDatetime', '')
                    issued_at = datetime.fromisoformat(issued_at_str.replace('Z', '+00:00')) if issued_at_str else datetime.now()
                    
                    # 警報の詳細情報
                    areas = alert_info.get('areas', {})
                    for area_key, area_alert in areas.items():
                        if isinstance(area_alert, dict):
                            # 警報の種類と内容
                            warnings = area_alert.get('warnings', [])
                            for warning in warnings:
                                if isinstance(warning, dict):
                                    alert = AlertData(
                                        title=warning.get('name', alert_type),
                                        description=warning.get('status', ''),
                                        severity=self._determine_severity(warning.get('code', '')),
                                        issued_at=issued_at,
                                        area_codes=[area_code]
                                    )
                                    alerts.append(alert)
                                    
            self.logger.info(f"気象警報を取得しました: {area_code} - {len(alerts)}件")
            return alerts
            
        except (KeyError, ValueError) as e:
            self.logger.error(f"警報データの解析に失敗しました: {area_code} - {str(e)}")
            raise WeatherAPIError(f"警報データの解析に失敗しました: {str(e)}")
            
    def _determine_severity(self, warning_code: str) -> str:
        """
        警報コードから重要度を判定
        
        Args:
            warning_code: 警報コード
            
        Returns:
            重要度（'高', '中', '低'）
        """
        if not warning_code:
            return '低'
            
        # 特別警報
        if 'special' in warning_code.lower():
            return '高'
            
        # 警報
        if 'warning' in warning_code.lower():
            return '高'
            
        # 注意報
        if 'advisory' in warning_code.lower():
            return '中'
            
        return '低'