"""天気データ用のモデル定義"""

from dataclasses import dataclass
from datetime import datetime, date
from typing import List, Optional


@dataclass
class AreaInfo:
    """地域情報"""
    code: str
    name: str
    en_name: str
    kana: str
    parent: str
    prefecture: Optional[str] = None
    region: Optional[str] = None


@dataclass
class WeatherData:
    """現在の天気データ"""
    area_name: str
    area_code: str
    weather_code: str
    weather_description: str
    wind: str
    wave: str
    temperature: Optional[float]
    precipitation_probability: Optional[int]
    timestamp: datetime
    publish_time: datetime


@dataclass
class ForecastData:
    """天気予報データ"""
    date: date
    weather_code: str
    weather_description: str
    temp_min: Optional[float]
    temp_max: Optional[float]
    temp_min_upper: Optional[float]
    temp_min_lower: Optional[float]
    temp_max_upper: Optional[float]
    temp_max_lower: Optional[float]
    precipitation_probability: Optional[int]
    reliability: str


@dataclass
class AlertData:
    """気象警報・注意報データ"""
    title: str
    description: str
    severity: str
    issued_at: datetime
    area_codes: List[str]