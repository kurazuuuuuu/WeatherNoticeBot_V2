"""
都市選択インタラクション用のビュークラス
"""

import discord
import json
from typing import List
from src.models.major_cities import MajorCity


class LocationSelectView(discord.ui.View):
    """都市選択用のビュークラス"""
    
    def __init__(self, cities: List[MajorCity], timeout: int = 180):
        """
        都市選択ビューを初期化
        
        Args:
            cities: 都市リスト
            timeout: タイムアウト時間（秒）
        """
        super().__init__(timeout=timeout)
        self.cities = cities
        self.add_city_dropdown()
    
    def add_city_dropdown(self):
        """都市選択ドロップダウンを追加"""
        # 都市が25個を超える場合は制限（Discordの制限）
        cities_to_show = self.cities[:25] if len(self.cities) > 25 else self.cities
        
        # ドロップダウンを作成
        select = LocationSelect(cities_to_show)
        self.add_item(select)


class LocationSelect(discord.ui.Select):
    """都市選択用のドロップダウンクラス"""
    
    def __init__(self, cities: List[MajorCity]):
        """
        都市選択ドロップダウンを初期化
        
        Args:
            cities: 都市リスト
        """
        # 選択肢を作成
        options = []
        for city in cities:
            option = discord.SelectOption(
                label=f"{city.name} ({city.prefecture})",
                description=f"{city.en_name} - {city.kana}",
                value=json.dumps({"code": city.code, "name": city.name})
            )
            options.append(option)
        
        super().__init__(
            placeholder="都市を選択してください",
            min_values=1,
            max_values=1,
            options=options
        )
    
    async def callback(self, interaction: discord.Interaction):
        """
        ドロップダウン選択時のコールバック
        
        Args:
            interaction: インタラクション
        """
        # 選択された都市の情報を取得
        selected_value = json.loads(self.values[0])
        city_code = selected_value["code"]
        city_name = selected_value["name"]
        
        # 天気情報を取得するためのボタンを作成
        view = CityActionView(city_code, city_name)
        
        # レスポンスを送信
        await interaction.response.send_message(
            f"**{city_name}** を選択しました。以下のボタンから天気情報を取得できます。",
            view=view,
            ephemeral=True
        )


class CityActionView(discord.ui.View):
    """都市アクション用のビュークラス"""
    
    def __init__(self, city_code: str, city_name: str, timeout: int = 180):
        """
        都市アクションビューを初期化
        
        Args:
            city_code: 都市コード
            city_name: 都市名
            timeout: タイムアウト時間（秒）
        """
        super().__init__(timeout=timeout)
        self.city_code = city_code
        self.city_name = city_name
        
        # 天気情報ボタン
        self.add_item(discord.ui.Button(
            style=discord.ButtonStyle.primary,
            label="現在の天気",
            custom_id=f"weather:{city_code}:{city_name}",
            emoji="☀️"
        ))
        
        # 天気予報ボタン
        self.add_item(discord.ui.Button(
            style=discord.ButtonStyle.secondary,
            label="天気予報",
            custom_id=f"forecast:{city_code}:{city_name}",
            emoji="📅"
        ))
        
        # 気象警報ボタン
        self.add_item(discord.ui.Button(
            style=discord.ButtonStyle.danger,
            label="気象警報",
            custom_id=f"alerts:{city_code}:{city_name}",
            emoji="⚠️"
        ))
        
        # 位置設定ボタン
        self.add_item(discord.ui.Button(
            style=discord.ButtonStyle.success,
            label="この都市を設定",
            custom_id=f"set_location:{city_code}:{city_name}",
            emoji="📍"
        ))
</text>