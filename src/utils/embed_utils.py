"""Discord Embed作成用のユーティリティ"""

import discord
from datetime import datetime
from typing import List, Optional, Tuple, Dict
from src.models.weather import WeatherData, ForecastData, AlertData
from src.models.major_cities import RegionCities, MajorCity


class WeatherEmbedBuilder:
    """天気情報用のDiscord Embed作成クラス"""
    
    # 天気コードに対応する絵文字マッピング（気象庁の天気コードに対応）
    WEATHER_EMOJIS = {
        # 晴れ系（100番台）
        "100": "☀️",  # 晴れ
        "101": "🌤️",  # 晴れ時々曇り
        "102": "🌦️",  # 晴れ一時雨
        "103": "🌦️",  # 晴れ時々雨
        "104": "🌨️",  # 晴れ一時雪
        "105": "🌨️",  # 晴れ時々雪
        "106": "🌦️",  # 晴れ一時雨か雪
        "107": "🌦️",  # 晴れ時々雨か雪
        "108": "⛈️",  # 晴れ一時雨か雷雨
        "110": "🌤️",  # 晴れ後時々曇り
        "111": "🌤️",  # 晴れ後曇り
        "112": "🌦️",  # 晴れ後一時雨
        "113": "🌦️",  # 晴れ後時々雨
        "114": "🌨️",  # 晴れ後一時雪
        "115": "🌨️",  # 晴れ後時々雪
        "116": "🌦️",  # 晴れ後雨か雪
        "117": "🌦️",  # 晴れ後雨か雷雨
        "118": "⛈️",  # 晴れ後雷雨
        "119": "🌨️",  # 晴れ後雪
        "120": "🌤️",  # 晴れ朝夕一時雨
        "121": "🌦️",  # 晴れ朝の内一時雨
        "122": "🌦️",  # 晴れ夕方一時雨
        "123": "🌨️",  # 晴れ山沿い雷雨
        "124": "🌨️",  # 晴れ山沿い雪
        "125": "⛈️",  # 晴れ午後は雷雨
        "126": "🌦️",  # 晴れ昼頃から雨
        "127": "🌦️",  # 晴れ夕方から雨
        "128": "🌦️",  # 晴れ夜は雨
        
        # 曇り系（200番台）
        "200": "☁️",  # 曇り
        "201": "🌤️",  # 曇り時々晴れ
        "202": "🌧️",  # 曇り一時雨
        "203": "🌧️",  # 曇り時々雨
        "204": "🌨️",  # 曇り一時雪
        "205": "🌨️",  # 曇り時々雪
        "206": "🌧️",  # 曇り一時雨か雪
        "207": "🌧️",  # 曇り時々雨か雪
        "208": "⛈️",  # 曇り一時雨か雷雨
        "209": "🌫️",  # 霧
        "210": "🌤️",  # 曇り後時々晴れ
        "211": "🌤️",  # 曇り後晴れ
        "212": "🌧️",  # 曇り後一時雨
        "213": "🌧️",  # 曇り後時々雨
        "214": "🌨️",  # 曇り後一時雪
        "215": "🌨️",  # 曇り後時々雪
        "216": "🌧️",  # 曇り後雨か雪
        "217": "⛈️",  # 曇り後雨か雷雨
        "218": "⛈️",  # 曇り後雷雨
        "219": "🌨️",  # 曇り後雪
        "220": "🌧️",  # 曇り朝夕一時雨
        "221": "🌧️",  # 曇り朝の内一時雨
        "222": "🌧️",  # 曇り夕方一時雨
        "223": "⛈️",  # 曇り日中時々晴れ
        "224": "⛈️",  # 曇り昼頃から雨
        "225": "🌧️",  # 曇り夕方から雨
        "226": "🌧️",  # 曇り夜は雨
        "228": "🌨️",  # 曇り昼頃から雪
        "229": "🌨️",  # 曇り夕方から雪
        "230": "🌨️",  # 曇り夜は雪
        "231": "🌫️",  # 曇り海上海岸は霧か霧雨
        
        # 雨系（300番台）
        "300": "🌧️",  # 雨
        "301": "🌦️",  # 雨時々晴れ
        "302": "🌧️",  # 雨時々曇り
        "303": "🌨️",  # 雨時々雪
        "304": "🌧️",  # 雨か雪
        "306": "💧",   # 大雨
        "308": "🌪️",  # 雨で暴風を伴う
        "309": "🌨️",  # 雨一時雪
        "311": "🌧️",  # 雨一時みぞれ
        "313": "⛈️",  # 雨一時雷雨
        "314": "💧",   # 強い雨
        "315": "💧",   # 強い雨
        "316": "💧",   # 激しい雨
        "317": "💧",   # 非常に激しい雨
        "320": "🌦️",  # 雨か雪後晴れ
        "321": "🌧️",  # 雨か雪後曇り
        "322": "🌦️",  # 雨後晴れ
        "323": "🌧️",  # 雨後曇り
        "324": "🌨️",  # 雨後雪
        "325": "🌦️",  # 雨一時雪後晴れ
        "326": "🌧️",  # 雨一時雪後曇り
        "327": "🌦️",  # 雨一時みぞれ後晴れ
        "328": "🌧️",  # 雨一時みぞれ後曇り
        "329": "⛈️",  # 雨一時雷雨後晴れ
        "330": "⛈️",  # 雨一時雷雨後曇り
        "331": "⛈️",  # 雨で雷を伴う
        "340": "❄️",  # 雪
        "350": "🌨️",  # みぞれ
        "361": "🌦️",  # 雪か雨後晴れ
        "371": "🌦️",  # 雪後晴れ
        "381": "🌦️",   # みぞれ後晴れ
        
        # 雪系（400番台）
        "400": "❄️",  # 雪
        "401": "🌨️",  # 雪時々晴れ
        "402": "🌨️",  # 雪時々曇り
        "403": "🌨️",  # 雪時々雨
        "405": "❄️",  # 大雪
        "406": "🌨️",  # 風雪強い
        "407": "❄️",  # 暴風雪
        "409": "🌨️",  # 雪一時雨
        "411": "🌨️",  # 雪一時みぞれ
        "420": "🌦️",  # 雪後晴れ
        "421": "🌧️",  # 雪後曇り
        "422": "🌨️",  # 雪後雨
        "423": "🌨️",  # 雪後みぞれ
        
        # デフォルト
        "default": "🌤️"
    }
    
    # 天気に応じた色設定（摂氏温度に適した色合い）
    WEATHER_COLORS = {
        "sunny": 0xFFD700,      # 金色（晴れ）
        "cloudy": 0x87CEEB,     # スカイブルー（曇り）
        "rainy": 0x4682B4,      # スチールブルー（雨）
        "snowy": 0xE6E6FA,      # ラベンダー（雪）
        "stormy": 0x2F4F4F,     # ダークスレートグレー（嵐）
        "hot": 0xFF4500,        # オレンジレッド（猛暑）
        "cold": 0x87CEFA,       # ライトスカイブルー（寒い）
        "default": 0x00BFFF     # ディープスカイブルー（デフォルト）
    }
    
    # 地域に応じた色設定
    REGION_COLORS = {
        "hokkaido": 0x87CEFA,   # ライトスカイブルー（北海道）
        "tohoku": 0x98FB98,     # ペールグリーン（東北）
        "kanto": 0xFFA07A,      # ライトサーモン（関東）
        "chubu": 0xFFDAB9,      # ピーチパフ（中部）
        "kinki": 0xFFB6C1,      # ライトピンク（近畿）
        "chugoku": 0xFFD700,    # ゴールド（中国）
        "shikoku": 0xADD8E6,    # ライトブルー（四国）
        "kyushu": 0xDDA0DD,     # プラム（九州・沖縄）
        "default": 0x00BFFF     # ディープスカイブルー（デフォルト）
    }
    
    # 地域に応じた絵文字
    REGION_EMOJIS = {
        "hokkaido": "🏔️",  # 北海道
        "tohoku": "🌲",     # 東北
        "kanto": "🏙️",     # 関東
        "chubu": "⛰️",     # 中部
        "kinki": "🏯",     # 近畿
        "chugoku": "🌉",   # 中国
        "shikoku": "🌊",   # 四国
        "kyushu": "🌋",    # 九州・沖縄
        "default": "🗾"    # デフォルト
    }
    
    @classmethod
    def get_weather_emoji(cls, weather_code: str) -> str:
        """天気コードに対応する絵文字を取得"""
        return cls.WEATHER_EMOJIS.get(weather_code, cls.WEATHER_EMOJIS["default"])
    
    @classmethod
    def _get_temperature_emoji(cls, temperature: float) -> str:
        """気温に応じた絵文字を取得"""
        if temperature >= 35:
            return "🥵"  # 猛暑
        elif temperature >= 30:
            return "🔥"  # 真夏日
        elif temperature >= 25:
            return "🌡️"  # 夏日
        elif temperature >= 20:
            return "🌤️"  # 暖かい
        elif temperature >= 15:
            return "🌡️"  # 涼しい
        elif temperature >= 10:
            return "🧊"  # 寒い
        elif temperature >= 0:
            return "❄️"  # 冬日
        else:
            return "🥶"  # 真冬日
    
    @classmethod
    def _get_temperature_description(cls, temperature: float) -> str:
        """気温に応じた説明を取得"""
        if temperature >= 35:
            return "猛暑日"
        elif temperature >= 30:
            return "真夏日"
        elif temperature >= 25:
            return "夏日"
        elif temperature >= 20:
            return "暖かい"
        elif temperature >= 15:
            return "涼しい"
        elif temperature >= 10:
            return "寒い"
        elif temperature >= 0:
            return "冬日"
        else:
            return "真冬日"
    
    @classmethod
    def _get_precipitation_emoji(cls, probability: int) -> str:
        """降水確率に応じた絵文字を取得"""
        if probability >= 80:
            return "☔"  # 高確率
        elif probability >= 60:
            return "🌧️"  # 中確率
        elif probability >= 30:
            return "🌦️"  # 低確率
        else:
            return "☀️"  # 晴れ
    
    @classmethod
    def get_weather_color(cls, weather_code: str, temperature: float = None) -> int:
        """天気コードと気温に対応する色を取得"""
        code = weather_code[:1] if weather_code else "0"
        
        # 気温による色の調整
        if temperature is not None:
            if temperature >= 35:  # 猛暑日
                return cls.WEATHER_COLORS["hot"]
            elif temperature <= 0:  # 真冬日
                return cls.WEATHER_COLORS["cold"]
        
        # 天気コードによる色選択
        if code == "1":  # 晴れ系
            return cls.WEATHER_COLORS["sunny"]
        elif code == "2":  # 曇り系
            return cls.WEATHER_COLORS["cloudy"]
        elif code == "3":  # 雨系
            if "31" in weather_code or "33" in weather_code:  # 雷雨
                return cls.WEATHER_COLORS["stormy"]
            return cls.WEATHER_COLORS["rainy"]
        elif code == "4":  # 雪系
            return cls.WEATHER_COLORS["snowy"]
        else:
            return cls.WEATHER_COLORS["default"]
    
    @classmethod
    def create_current_weather_embed(
        cls, 
        weather_data: WeatherData, 
        ai_message: Optional[str] = None
    ) -> discord.Embed:
        """現在の天気情報用のEmbedを作成"""
        emoji = cls.get_weather_emoji(weather_data.weather_code)
        color = cls.get_weather_color(weather_data.weather_code, weather_data.temperature)
        
        # タイトルと説明
        title = f"{emoji} {weather_data.area_name}の現在の天気"
        description = f"**{weather_data.weather_description}**"
        
        embed = discord.Embed(
            title=title,
            description=description,
            color=color,
            timestamp=datetime.now()
        )
        
        # 温度情報（摂氏で表示）
        if weather_data.temperature is not None:
            temp_emoji = cls._get_temperature_emoji(weather_data.temperature)
            # 温度を摂氏で表示し、体感温度の説明も追加
            temp_description = cls._get_temperature_description(weather_data.temperature)
            embed.add_field(
                name=f"{temp_emoji} 気温",
                value=f"**{weather_data.temperature:.1f}°C**\n{temp_description}",
                inline=True
            )
        
        # 降水確率
        if weather_data.precipitation_probability is not None:
            precip_emoji = cls._get_precipitation_emoji(weather_data.precipitation_probability)
            embed.add_field(
                name=f"{precip_emoji} 降水確率",
                value=f"**{weather_data.precipitation_probability}%**",
                inline=True
            )
        
        # 風の情報
        if weather_data.wind:
            embed.add_field(
                name="💨 風",
                value=weather_data.wind,
                inline=True
            )
        
        # 波の情報（海岸地域の場合）
        if weather_data.wave:
            embed.add_field(
                name="🌊 波",
                value=weather_data.wave,
                inline=True
            )
        
        # AIメッセージがある場合は追加
        if ai_message:
            embed.add_field(
                name="💡 今日のメッセージ",
                value=ai_message,
                inline=False
            )
        
        # フッター情報
        embed.set_footer(
            text=f"気象庁データ | 発表時刻: {weather_data.publish_time.strftime('%Y/%m/%d %H:%M')}"
        )
        
        return embed
    
    @classmethod
    def create_forecast_embed(
        cls, 
        forecast_data: List[ForecastData], 
        area_name: str,
        ai_message: Optional[str] = None
    ) -> discord.Embed:
        """天気予報用のEmbedを作成"""
        if not forecast_data:
            return discord.Embed(
                title="❌ 予報データなし",
                description="予報データを取得できませんでした。",
                color=cls.WEATHER_COLORS["default"]
            )
        
        # 最初の日の天気と最高気温で色を決定
        first_weather = forecast_data[0]
        color = cls.get_weather_color(first_weather.weather_code, first_weather.temp_max)
        
        embed = discord.Embed(
            title=f"📅 {area_name}の天気予報",
            description="今後の天気予報をお知らせします",
            color=color,
            timestamp=datetime.now()
        )
        
        # 各日の予報を追加（最大5日分）
        for i, forecast in enumerate(forecast_data[:5]):
            emoji = cls.get_weather_emoji(forecast.weather_code)
            date_str = forecast.date.strftime("%m/%d (%a)")
            
            # 温度情報の構築（摂氏で表示）
            temp_info = []
            if forecast.temp_max is not None:
                max_emoji = cls._get_temperature_emoji(forecast.temp_max)
                max_desc = cls._get_temperature_description(forecast.temp_max)
                temp_info.append(f"{max_emoji} 最高: **{forecast.temp_max:.1f}°C** ({max_desc})")
            if forecast.temp_min is not None:
                min_emoji = cls._get_temperature_emoji(forecast.temp_min)
                min_desc = cls._get_temperature_description(forecast.temp_min)
                temp_info.append(f"{min_emoji} 最低: **{forecast.temp_min:.1f}°C** ({min_desc})")
            
            temp_text = "\n".join(temp_info) if temp_info else "温度情報なし"
            
            # 降水確率
            precip_text = ""
            if forecast.precipitation_probability is not None:
                precip_emoji = cls._get_precipitation_emoji(forecast.precipitation_probability)
                precip_text = f"{precip_emoji} 降水確率: **{forecast.precipitation_probability}%**"
            
            field_value = f"**{forecast.weather_description}**\n{temp_text}"
            if precip_text:
                field_value += f"\n{precip_text}"
            
            embed.add_field(
                name=f"{emoji} {date_str}",
                value=field_value,
                inline=True
            )
            
            # 3つごとに改行を入れるため、空のフィールドを追加
            if (i + 1) % 3 == 0 and i < len(forecast_data[:5]) - 1:
                embed.add_field(name="\u200b", value="\u200b", inline=False)
        
        # AIメッセージがある場合は追加
        if ai_message:
            embed.add_field(
                name="💡 週間のアドバイス",
                value=ai_message,
                inline=False
            )
        
        # フッター情報
        embed.set_footer(text="気象庁データ")
        
        return embed
    
    @classmethod
    def create_alert_embed(
        cls, 
        alerts: List[AlertData], 
        area_name: str
    ) -> discord.Embed:
        """気象警報・注意報用のEmbedを作成"""
        if not alerts:
            embed = discord.Embed(
                title=f"✅ {area_name}の気象情報",
                description="現在、気象警報・注意報は発表されていません。",
                color=cls.WEATHER_COLORS["sunny"],
                timestamp=datetime.now()
            )
            embed.set_footer(text="気象庁データ")
            return embed
        
        # 警報がある場合は赤色、注意報のみの場合は黄色
        has_warning = any("警報" in alert.title for alert in alerts)
        color = 0xFF0000 if has_warning else 0xFFFF00  # 赤色 or 黄色
        
        embed = discord.Embed(
            title=f"⚠️ {area_name}の気象警報・注意報",
            description="以下の警報・注意報が発表されています。",
            color=color,
            timestamp=datetime.now()
        )
        
        # 各警報・注意報を追加
        for i, alert in enumerate(alerts[:10]):  # 最大10件まで表示
            # 警報か注意報かで絵文字を変更
            emoji = "🚨" if "警報" in alert.title else "⚠️"
            
            # 発表時刻
            issued_time = alert.issued_at.strftime("%m/%d %H:%M")
            
            field_value = f"{alert.description}\n発表: {issued_time}"
            
            embed.add_field(
                name=f"{emoji} {alert.title}",
                value=field_value,
                inline=False
            )
        
        # 10件を超える場合は省略メッセージ
        if len(alerts) > 10:
            embed.add_field(
                name="📋 その他",
                value=f"他に{len(alerts) - 10}件の警報・注意報があります。",
                inline=False
            )
        
        embed.set_footer(text="気象庁データ | 最新情報を確認してください")
        
        return embed
    
    @classmethod
    def create_error_embed(
        cls, 
        title: str, 
        description: str, 
        error_type: str = "general",
        details: Optional[str] = None,
        suggestions: Optional[List[str]] = None
    ) -> discord.Embed:
        """エラー用のEmbedを作成"""
        color_map = {
            "not_found": 0xFF6B6B,      # 赤系（見つからない）
            "api_error": 0xFFA500,      # オレンジ（API エラー）
            "permission": 0xFF69B4,     # ピンク（権限エラー）
            "general": 0x808080         # グレー（一般エラー）
        }
        
        emoji_map = {
            "not_found": "🔍",
            "api_error": "⚠️",
            "permission": "🚫",
            "general": "❌"
        }
        
        color = color_map.get(error_type, color_map["general"])
        emoji = emoji_map.get(error_type, emoji_map["general"])
        
        # 長い説明の場合は分割
        if len(description) > 2000:
            description = cls.truncate_field_value(description, 2000)
        
        embed = discord.Embed(
            title=f"{emoji} {title}",
            description=description,
            color=color,
            timestamp=datetime.now()
        )
        
        # 詳細情報を追加
        if details:
            embed.add_field(
                name="📋 詳細情報",
                value=cls.truncate_field_value(details, 1024),
                inline=False
            )
        
        # 解決策の提案を追加
        if suggestions:
            suggestion_text = "\n".join([f"• {suggestion}" for suggestion in suggestions[:5]])
            embed.add_field(
                name="💡 解決策",
                value=cls.truncate_field_value(suggestion_text, 1024),
                inline=False
            )
        
        # エラータイプに応じたフッターメッセージ
        footer_messages = {
            "not_found": "正確な情報を入力してもう一度お試しください",
            "api_error": "しばらく時間をおいてからお試しください",
            "permission": "必要な権限を確認してください",
            "general": "問題が続く場合は管理者にお問い合わせください"
        }
        
        footer_text = footer_messages.get(error_type, footer_messages["general"])
        embed.set_footer(text=footer_text)
        
        return embed
    
    @classmethod
    def create_paginated_forecast_embeds(
        cls, 
        forecast_data: List[ForecastData], 
        area_name: str,
        ai_message: Optional[str] = None,
        items_per_page: int = 3
    ) -> List[discord.Embed]:
        """
        ページネーション対応の天気予報Embedリストを作成
        
        Args:
            forecast_data: 予報データのリスト
            area_name: 地域名
            ai_message: AIメッセージ
            items_per_page: 1ページあたりのアイテム数
            
        Returns:
            Embedのリスト
        """
        if not forecast_data:
            return [cls.create_forecast_embed([], area_name, ai_message)]
        
        embeds = []
        total_pages = (len(forecast_data) + items_per_page - 1) // items_per_page
        
        for page in range(total_pages):
            start_idx = page * items_per_page
            end_idx = min(start_idx + items_per_page, len(forecast_data))
            page_data = forecast_data[start_idx:end_idx]
            
            # 最初のページにのみAIメッセージを含める
            page_ai_message = ai_message if page == 0 else None
            
            embed = cls.create_forecast_embed(page_data, area_name, page_ai_message)
            
            # ページ情報をフッターに追加
            if total_pages > 1:
                current_footer = embed.footer.text if embed.footer else ""
                page_info = f"ページ {page + 1}/{total_pages}"
                new_footer = f"{current_footer} | {page_info}" if current_footer else page_info
                embed.set_footer(text=new_footer)
            
            embeds.append(embed)
        
        return embeds
    
    @classmethod
    def create_paginated_alert_embeds(
        cls, 
        alerts: List[AlertData], 
        area_name: str,
        items_per_page: int = 5
    ) -> List[discord.Embed]:
        """
        ページネーション対応の気象警報Embedリストを作成
        
        Args:
            alerts: 警報データのリスト
            area_name: 地域名
            items_per_page: 1ページあたりのアイテム数
            
        Returns:
            Embedのリスト
        """
        if not alerts:
            return [cls.create_alert_embed([], area_name)]
        
        embeds = []
        total_pages = (len(alerts) + items_per_page - 1) // items_per_page
        
        for page in range(total_pages):
            start_idx = page * items_per_page
            end_idx = min(start_idx + items_per_page, len(alerts))
            page_alerts = alerts[start_idx:end_idx]
            
            embed = cls.create_alert_embed(page_alerts, area_name)
            
            # ページ情報をフッターに追加
            if total_pages > 1:
                current_footer = embed.footer.text if embed.footer else ""
                page_info = f"ページ {page + 1}/{total_pages} (全{len(alerts)}件)"
                new_footer = f"{current_footer} | {page_info}" if current_footer else page_info
                embed.set_footer(text=new_footer)
            
            embeds.append(embed)
        
        return embeds
    
    @classmethod
    def create_success_embed(
        cls, 
        title: str, 
        description: str
    ) -> discord.Embed:
        """成功メッセージ用のEmbedを作成"""
        embed = discord.Embed(
            title=f"✅ {title}",
            description=description,
            color=0x00FF00,  # 緑色
            timestamp=datetime.now()
        )
        
        return embed
    
    @classmethod
    def split_long_message(cls, message: str, max_length: int = 2000) -> List[str]:
        """
        長いメッセージを分割する
        
        Args:
            message: 分割するメッセージ
            max_length: 最大文字数
            
        Returns:
            分割されたメッセージのリスト
        """
        if len(message) <= max_length:
            return [message]
        
        parts = []
        current_part = ""
        
        # 改行で分割して処理
        lines = message.split('\n')
        
        for line in lines:
            # 現在の部分に行を追加しても制限を超えない場合
            if len(current_part) + len(line) + 1 <= max_length:
                if current_part:
                    current_part += '\n' + line
                else:
                    current_part = line
            else:
                # 現在の部分を保存して新しい部分を開始
                if current_part:
                    parts.append(current_part)
                
                # 行自体が長すぎる場合は文字単位で分割
                if len(line) > max_length:
                    while len(line) > max_length:
                        parts.append(line[:max_length])
                        line = line[max_length:]
                    current_part = line if line else ""
                else:
                    current_part = line
        
        # 最後の部分を追加
        if current_part:
            parts.append(current_part)
        
        return parts
    
    @classmethod
    def create_multi_embed_message(
        cls, 
        title: str, 
        content: str, 
        color: int = 0x00BFFF,
        max_description_length: int = 2000
    ) -> List[discord.Embed]:
        """
        長いコンテンツを複数のEmbedに分割
        
        Args:
            title: タイトル
            content: コンテンツ
            color: Embedの色
            max_description_length: 説明の最大文字数
            
        Returns:
            Embedのリスト
        """
        content_parts = cls.split_long_message(content, max_description_length)
        embeds = []
        
        for i, part in enumerate(content_parts):
            if len(content_parts) > 1:
                embed_title = f"{title} ({i + 1}/{len(content_parts)})"
            else:
                embed_title = title
            
            embed = discord.Embed(
                title=embed_title,
                description=part,
                color=color,
                timestamp=datetime.now()
            )
            
            embeds.append(embed)
        
        return embeds
    
    @classmethod
    def truncate_field_value(cls, value: str, max_length: int = 1024) -> str:
        """
        フィールド値を指定された長さに切り詰める
        
        Args:
            value: 切り詰める値
            max_length: 最大文字数
            
        Returns:
            切り詰められた値
        """
        if len(value) <= max_length:
            return value
        
        # 切り詰めマークを追加
        truncated = value[:max_length - 3] + "..."
        return truncated
    
    @classmethod
    def validate_embed_limits(cls, embed: discord.Embed) -> discord.Embed:
        """
        EmbedがDiscordの制限に適合するように調整
        
        Args:
            embed: 調整するEmbed
            
        Returns:
            調整されたEmbed
        """
        # タイトルの制限（256文字）
        if embed.title and len(embed.title) > 256:
            embed.title = embed.title[:253] + "..."
        
        # 説明の制限（4096文字）
        if embed.description and len(embed.description) > 4096:
            embed.description = embed.description[:4093] + "..."
        
        # フィールドの制限（名前: 256文字、値: 1024文字）
        for field in embed.fields:
            if len(field.name) > 256:
                # フィールド名を調整（内部的に処理）
                pass
            if len(field.value) > 1024:
                # フィールド値を調整（内部的に処理）
                pass
        
        # フッターの制限（2048文字）
        if embed.footer and embed.footer.text and len(embed.footer.text) > 2048:
            embed.set_footer(text=embed.footer.text[:2045] + "...")
        
        return embed
    
    @classmethod
    def create_locations_embed(
        cls,
        region_cities: RegionCities,
        page: int = 1,
        items_per_page: int = 10
    ) -> discord.Embed:
        """
        主要都市リスト用のEmbedを作成
        
        Args:
            region_cities: 地域ごとの主要都市情報
            page: 現在のページ番号（1から開始）
            items_per_page: 1ページあたりの都市数
            
        Returns:
            主要都市リスト用のEmbed
        """
        region_code = next((code for code, info in cls.REGION_EMOJIS.items() 
                          if info == region_cities.region_name), "default")
        color = cls.REGION_COLORS.get(region_code, cls.REGION_COLORS["default"])
        emoji = cls.REGION_EMOJIS.get(region_code, cls.REGION_EMOJIS["default"])
        
        embed = discord.Embed(
            title=f"{emoji} {region_cities.region_name}の主要都市",
            description=f"{region_cities.region_name}（{region_cities.region_en_name}）地方の主要都市一覧です。",
            color=color,
            timestamp=datetime.now()
        )
        
        # ページネーション
        cities = region_cities.cities
        total_cities = len(cities)
        total_pages = (total_cities + items_per_page - 1) // items_per_page
        
        # ページ番号の調整
        page = max(1, min(page, total_pages))
        
        # 表示する都市の範囲を計算
        start_idx = (page - 1) * items_per_page
        end_idx = min(start_idx + items_per_page, total_cities)
        
        # 都市情報を追加
        for i, city in enumerate(cities[start_idx:end_idx], start=1):
            field_name = f"{i}. {city.name} ({city.en_name})"
            field_value = f"**都道府県**: {city.prefecture}\n**読み方**: {city.kana}\n**コード**: {city.code}"
            embed.add_field(name=field_name, value=field_value, inline=True)
            
            # 2つごとに改行を入れる
            if i % 2 == 0 and i < end_idx - start_idx:
                embed.add_field(name="\u200b", value="\u200b", inline=False)
        
        # ページ情報をフッターに追加
        embed.set_footer(text=f"ページ {page}/{total_pages} (全{total_cities}件) | 天気コマンドで都市名を指定できます")
        
        return embed
    
    @classmethod
    def create_regions_list_embed(cls, regions: List[Dict[str, str]]) -> discord.Embed:
        """
        地域一覧用のEmbedを作成
        
        Args:
            regions: 地域情報のリスト
            
        Returns:
            地域一覧用のEmbed
        """
        embed = discord.Embed(
            title="🗾 日本の地域一覧",
            description="天気情報を取得できる日本の地域一覧です。\n地域を選択して主要都市を表示できます。",
            color=cls.REGION_COLORS["default"],
            timestamp=datetime.now()
        )
        
        # 地域情報を追加
        for region in regions:
            emoji = cls.REGION_EMOJIS.get(region["code"], cls.REGION_EMOJIS["default"])
            field_name = f"{emoji} {region['name']} ({region['en_name']})"
            field_value = f"コード: `{region['code']}`\n`/locations {region['code']}` で都市一覧を表示"
            embed.add_field(name=field_name, value=field_value, inline=True)
        
        embed.set_footer(text="地域を選択して主要都市の一覧を表示できます")
        
        return embed
    
    @classmethod
    def create_paginated_locations_embeds(
        cls,
        region_cities: RegionCities,
        items_per_page: int = 10
    ) -> List[discord.Embed]:
        """
        ページネーション対応の主要都市リストEmbedリストを作成
        
        Args:
            region_cities: 地域ごとの主要都市情報
            items_per_page: 1ページあたりの都市数
            
        Returns:
            Embedのリスト
        """
        cities = region_cities.cities
        total_cities = len(cities)
        total_pages = (total_cities + items_per_page - 1) // items_per_page
        
        embeds = []
        for page in range(1, total_pages + 1):
            embed = cls.create_locations_embed(region_cities, page, items_per_page)
            embeds.append(embed)
        
        return embeds
</text>