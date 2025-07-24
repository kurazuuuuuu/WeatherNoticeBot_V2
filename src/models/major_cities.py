"""
主要都市データモデル

日本の主要都市情報を地域別に管理するためのモデル
"""

from dataclasses import dataclass
from typing import Dict, List, Optional
from .weather import AreaInfo


@dataclass
class MajorCity(AreaInfo):
    """主要都市情報"""
    prefecture: Optional[str] = None
    region: Optional[str] = None


@dataclass
class RegionCities:
    """地域ごとの主要都市リスト"""
    region_name: str
    region_en_name: str
    cities: List[MajorCity]


# 日本の地域区分（8地方区分）
JAPAN_REGIONS = {
    "hokkaido": {
        "name": "北海道",
        "en_name": "Hokkaido"
    },
    "tohoku": {
        "name": "東北",
        "en_name": "Tohoku"
    },
    "kanto": {
        "name": "関東",
        "en_name": "Kanto"
    },
    "chubu": {
        "name": "中部",
        "en_name": "Chubu"
    },
    "kinki": {
        "name": "近畿",
        "en_name": "Kinki"
    },
    "chugoku": {
        "name": "中国",
        "en_name": "Chugoku"
    },
    "shikoku": {
        "name": "四国",
        "en_name": "Shikoku"
    },
    "kyushu": {
        "name": "九州・沖縄",
        "en_name": "Kyushu & Okinawa"
    }
}


# 都道府県と地域のマッピング
PREFECTURE_TO_REGION = {
    "北海道": "hokkaido",
    "青森県": "tohoku",
    "岩手県": "tohoku",
    "宮城県": "tohoku",
    "秋田県": "tohoku",
    "山形県": "tohoku",
    "福島県": "tohoku",
    "茨城県": "kanto",
    "栃木県": "kanto",
    "群馬県": "kanto",
    "埼玉県": "kanto",
    "千葉県": "kanto",
    "東京都": "kanto",
    "神奈川県": "kanto",
    "新潟県": "chubu",
    "富山県": "chubu",
    "石川県": "chubu",
    "福井県": "chubu",
    "山梨県": "chubu",
    "長野県": "chubu",
    "岐阜県": "chubu",
    "静岡県": "chubu",
    "愛知県": "chubu",
    "三重県": "kinki",
    "滋賀県": "kinki",
    "京都府": "kinki",
    "大阪府": "kinki",
    "兵庫県": "kinki",
    "奈良県": "kinki",
    "和歌山県": "kinki",
    "鳥取県": "chugoku",
    "島根県": "chugoku",
    "岡山県": "chugoku",
    "広島県": "chugoku",
    "山口県": "chugoku",
    "徳島県": "shikoku",
    "香川県": "shikoku",
    "愛媛県": "shikoku",
    "高知県": "shikoku",
    "福岡県": "kyushu",
    "佐賀県": "kyushu",
    "長崎県": "kyushu",
    "熊本県": "kyushu",
    "大分県": "kyushu",
    "宮崎県": "kyushu",
    "鹿児島県": "kyushu",
    "沖縄県": "kyushu"
}


# 主要都市データ（地域コードは実際のAPIから取得する必要があります）
# 実際の実装では、これらのデータは気象庁APIから取得した地域コードと紐づけられます
MAJOR_CITIES_DATA = [
    # 北海道
    {"name": "札幌", "en_name": "Sapporo", "kana": "さっぽろ", "prefecture": "北海道"},
    {"name": "函館", "en_name": "Hakodate", "kana": "はこだて", "prefecture": "北海道"},
    {"name": "旭川", "en_name": "Asahikawa", "kana": "あさひかわ", "prefecture": "北海道"},
    {"name": "釧路", "en_name": "Kushiro", "kana": "くしろ", "prefecture": "北海道"},
    {"name": "帯広", "en_name": "Obihiro", "kana": "おびひろ", "prefecture": "北海道"},
    
    # 東北
    {"name": "青森", "en_name": "Aomori", "kana": "あおもり", "prefecture": "青森県"},
    {"name": "仙台", "en_name": "Sendai", "kana": "せんだい", "prefecture": "宮城県"},
    {"name": "秋田", "en_name": "Akita", "kana": "あきた", "prefecture": "秋田県"},
    {"name": "山形", "en_name": "Yamagata", "kana": "やまがた", "prefecture": "山形県"},
    {"name": "盛岡", "en_name": "Morioka", "kana": "もりおか", "prefecture": "岩手県"},
    {"name": "福島", "en_name": "Fukushima", "kana": "ふくしま", "prefecture": "福島県"},
    {"name": "郡山", "en_name": "Koriyama", "kana": "こおりやま", "prefecture": "福島県"},
    
    # 関東
    {"name": "東京", "en_name": "Tokyo", "kana": "とうきょう", "prefecture": "東京都"},
    {"name": "横浜", "en_name": "Yokohama", "kana": "よこはま", "prefecture": "神奈川県"},
    {"name": "さいたま", "en_name": "Saitama", "kana": "さいたま", "prefecture": "埼玉県"},
    {"name": "千葉", "en_name": "Chiba", "kana": "ちば", "prefecture": "千葉県"},
    {"name": "水戸", "en_name": "Mito", "kana": "みと", "prefecture": "茨城県"},
    {"name": "宇都宮", "en_name": "Utsunomiya", "kana": "うつのみや", "prefecture": "栃木県"},
    {"name": "前橋", "en_name": "Maebashi", "kana": "まえばし", "prefecture": "群馬県"},
    {"name": "川崎", "en_name": "Kawasaki", "kana": "かわさき", "prefecture": "神奈川県"},
    {"name": "横須賀", "en_name": "Yokosuka", "kana": "よこすか", "prefecture": "神奈川県"},
    {"name": "八王子", "en_name": "Hachioji", "kana": "はちおうじ", "prefecture": "東京都"},
    
    # 中部
    {"name": "新潟", "en_name": "Niigata", "kana": "にいがた", "prefecture": "新潟県"},
    {"name": "富山", "en_name": "Toyama", "kana": "とやま", "prefecture": "富山県"},
    {"name": "金沢", "en_name": "Kanazawa", "kana": "かなざわ", "prefecture": "石川県"},
    {"name": "福井", "en_name": "Fukui", "kana": "ふくい", "prefecture": "福井県"},
    {"name": "甲府", "en_name": "Kofu", "kana": "こうふ", "prefecture": "山梨県"},
    {"name": "長野", "en_name": "Nagano", "kana": "ながの", "prefecture": "長野県"},
    {"name": "岐阜", "en_name": "Gifu", "kana": "ぎふ", "prefecture": "岐阜県"},
    {"name": "静岡", "en_name": "Shizuoka", "kana": "しずおか", "prefecture": "静岡県"},
    {"name": "名古屋", "en_name": "Nagoya", "kana": "なごや", "prefecture": "愛知県"},
    {"name": "浜松", "en_name": "Hamamatsu", "kana": "はままつ", "prefecture": "静岡県"},
    {"name": "豊橋", "en_name": "Toyohashi", "kana": "とよはし", "prefecture": "愛知県"},
    {"name": "松本", "en_name": "Matsumoto", "kana": "まつもと", "prefecture": "長野県"},
    
    # 近畿
    {"name": "大阪", "en_name": "Osaka", "kana": "おおさか", "prefecture": "大阪府"},
    {"name": "京都", "en_name": "Kyoto", "kana": "きょうと", "prefecture": "京都府"},
    {"name": "神戸", "en_name": "Kobe", "kana": "こうべ", "prefecture": "兵庫県"},
    {"name": "奈良", "en_name": "Nara", "kana": "なら", "prefecture": "奈良県"},
    {"name": "大津", "en_name": "Otsu", "kana": "おおつ", "prefecture": "滋賀県"},
    {"name": "和歌山", "en_name": "Wakayama", "kana": "わかやま", "prefecture": "和歌山県"},
    {"name": "津", "en_name": "Tsu", "kana": "つ", "prefecture": "三重県"},
    {"name": "堺", "en_name": "Sakai", "kana": "さかい", "prefecture": "大阪府"},
    {"name": "姫路", "en_name": "Himeji", "kana": "ひめじ", "prefecture": "兵庫県"},
    {"name": "西宮", "en_name": "Nishinomiya", "kana": "にしのみや", "prefecture": "兵庫県"},
    
    # 中国
    {"name": "鳥取", "en_name": "Tottori", "kana": "とっとり", "prefecture": "鳥取県"},
    {"name": "松江", "en_name": "Matsue", "kana": "まつえ", "prefecture": "島根県"},
    {"name": "岡山", "en_name": "Okayama", "kana": "おかやま", "prefecture": "岡山県"},
    {"name": "広島", "en_name": "Hiroshima", "kana": "ひろしま", "prefecture": "広島県"},
    {"name": "山口", "en_name": "Yamaguchi", "kana": "やまぐち", "prefecture": "山口県"},
    {"name": "福山", "en_name": "Fukuyama", "kana": "ふくやま", "prefecture": "広島県"},
    {"name": "下関", "en_name": "Shimonoseki", "kana": "しものせき", "prefecture": "山口県"},
    
    # 四国
    {"name": "徳島", "en_name": "Tokushima", "kana": "とくしま", "prefecture": "徳島県"},
    {"name": "高松", "en_name": "Takamatsu", "kana": "たかまつ", "prefecture": "香川県"},
    {"name": "松山", "en_name": "Matsuyama", "kana": "まつやま", "prefecture": "愛媛県"},
    {"name": "高知", "en_name": "Kochi", "kana": "こうち", "prefecture": "高知県"},
    {"name": "今治", "en_name": "Imabari", "kana": "いまばり", "prefecture": "愛媛県"},
    {"name": "新居浜", "en_name": "Niihama", "kana": "にいはま", "prefecture": "愛媛県"},
    
    # 九州・沖縄
    {"name": "福岡", "en_name": "Fukuoka", "kana": "ふくおか", "prefecture": "福岡県"},
    {"name": "佐賀", "en_name": "Saga", "kana": "さが", "prefecture": "佐賀県"},
    {"name": "長崎", "en_name": "Nagasaki", "kana": "ながさき", "prefecture": "長崎県"},
    {"name": "熊本", "en_name": "Kumamoto", "kana": "くまもと", "prefecture": "熊本県"},
    {"name": "大分", "en_name": "Oita", "kana": "おおいた", "prefecture": "大分県"},
    {"name": "宮崎", "en_name": "Miyazaki", "kana": "みやざき", "prefecture": "宮崎県"},
    {"name": "鹿児島", "en_name": "Kagoshima", "kana": "かごしま", "prefecture": "鹿児島県"},
    {"name": "那覇", "en_name": "Naha", "kana": "なは", "prefecture": "沖縄県"},
    {"name": "北九州", "en_name": "Kitakyushu", "kana": "きたきゅうしゅう", "prefecture": "福岡県"},
    {"name": "久留米", "en_name": "Kurume", "kana": "くるめ", "prefecture": "福岡県"},
    {"name": "沖縄", "en_name": "Okinawa", "kana": "おきなわ", "prefecture": "沖縄県"},
    {"name": "石垣", "en_name": "Ishigaki", "kana": "いしがき", "prefecture": "沖縄県"}
]

# 地域コードのキャッシュ（初期化時に設定される）
CITY_CODE_CACHE = {}
</text>