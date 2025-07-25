"""
主要都市の地域コード定義

気象庁APIで使用する主要都市の地域コードを定義します。
"""

# 主要都市の地域コード（気象庁API用）
CITY_CODES = {
    # 北海道
    "札幌": "016000",  # 札幌管区気象台
    "函館": "017000",  # 函館地方気象台
    "旭川": "012000",  # 旭川地方気象台
    "帯広": "013000",  # 網走地方気象台（帯広を含む地域）
    "釧路": "014100",  # 釧路地方気象台
    
    # 東北
    "青森": "020000",  # 青森地方気象台
    "仙台": "040000",  # 仙台管区気象台
    "秋田": "050000",  # 秋田地方気象台
    "山形": "060000",  # 山形地方気象台
    "盛岡": "030000",  # 盛岡地方気象台
    "福島": "070000",  # 福島地方気象台
    "郡山": "070000",  # 福島地方気象台（郡山を含む地域）
    
    # 関東
    "東京": "130000",  # 気象庁
    "横浜": "140000",  # 横浜地方気象台
    "さいたま": "110000",  # 熊谷地方気象台（さいたまを含む地域）
    "千葉": "120000",  # 銚子地方気象台（千葉を含む地域）
    "水戸": "080000",  # 水戸地方気象台
    "宇都宮": "090000",  # 宇都宮地方気象台
    "前橋": "100000",  # 前橋地方気象台
    "川崎": "140000",  # 横浜地方気象台（川崎を含む地域）
    "横須賀": "140000",  # 横浜地方気象台（横須賀を含む地域）
    "八王子": "130000",  # 気象庁（八王子を含む地域）
    
    # 中部
    "新潟": "150000",  # 新潟地方気象台
    "富山": "160000",  # 富山地方気象台
    "金沢": "170000",  # 金沢地方気象台
    "福井": "180000",  # 福井地方気象台
    "甲府": "190000",  # 甲府地方気象台
    "長野": "200000",  # 長野地方気象台
    "岐阜": "210000",  # 岐阜地方気象台
    "静岡": "220000",  # 静岡地方気象台
    "名古屋": "230000",  # 名古屋地方気象台
    "浜松": "220000",  # 静岡地方気象台（浜松を含む地域）
    "豊橋": "230000",  # 名古屋地方気象台（豊橋を含む地域）
    "松本": "200000",  # 長野地方気象台（松本を含む地域）
    
    # 近畿
    "大阪": "270000",  # 大阪管区気象台
    "京都": "260000",  # 京都地方気象台
    "神戸": "280000",  # 神戸地方気象台
    "奈良": "290000",  # 奈良地方気象台
    "大津": "250000",  # 彦根地方気象台（大津を含む地域）
    "和歌山": "300000",  # 和歌山地方気象台
    "津": "240000",  # 津地方気象台
    "堺": "270000",  # 大阪管区気象台（堺を含む地域）
    "姫路": "280000",  # 神戸地方気象台（姫路を含む地域）
    "西宮": "280000",  # 神戸地方気象台（西宮を含む地域）
    
    # 中国
    "鳥取": "310000",  # 鳥取地方気象台
    "松江": "320000",  # 松江地方気象台
    "岡山": "330000",  # 岡山地方気象台
    "広島": "340000",  # 広島地方気象台
    "山口": "350000",  # 下関地方気象台（山口を含む地域）
    "福山": "330000",  # 岡山地方気象台（福山を含む地域）
    "下関": "350000",  # 下関地方気象台
    
    # 四国
    "徳島": "360000",  # 徳島地方気象台
    "高松": "370000",  # 高松地方気象台
    "松山": "380000",  # 松山地方気象台
    "高知": "390000",  # 高知地方気象台
    "今治": "380000",  # 松山地方気象台（今治を含む地域）
    "新居浜": "380000",  # 松山地方気象台（新居浜を含む地域）
    
    # 九州・沖縄
    "福岡": "400000",  # 福岡管区気象台
    "佐賀": "410000",  # 佐賀地方気象台
    "長崎": "420000",  # 長崎地方気象台
    "熊本": "430000",  # 熊本地方気象台
    "大分": "440000",  # 大分地方気象台
    "宮崎": "450000",  # 宮崎地方気象台
    "鹿児島": "460100",  # 鹿児島地方気象台
    "那覇": "471000",  # 沖縄気象台
    "北九州": "400000",  # 福岡管区気象台（北九州を含む地域）
    "久留米": "400000",  # 福岡管区気象台（久留米を含む地域）
    "沖縄": "471000",  # 沖縄気象台
    "石垣": "474000"   # 石垣島地方気象台
}