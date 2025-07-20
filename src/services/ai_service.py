"""
Google Gemini AIを使用したメッセージ生成サービス

このモジュールは天気情報に基づいてポジティブなメッセージを生成します。
"""

import asyncio
import logging
from typing import Optional, Dict, Any
from dataclasses import dataclass
from datetime import datetime

import google.generativeai as genai
from google.generativeai.types import HarmCategory, HarmBlockThreshold

try:
    from ..config import Config
except ImportError:
    from src.config import Config


@dataclass
class WeatherContext:
    """天気情報のコンテキスト"""
    area_name: str
    weather_description: str
    temperature: Optional[float]
    precipitation_probability: int
    wind: str
    timestamp: datetime
    is_alert: bool = False
    alert_description: Optional[str] = None


def weather_data_to_context(weather_data) -> WeatherContext:
    """
    WeatherDataオブジェクトをWeatherContextに変換
    
    Args:
        weather_data: WeatherDataオブジェクト（weather_serviceから）
    
    Returns:
        WeatherContext: AIサービス用のコンテキスト
    """
    return WeatherContext(
        area_name=weather_data.area_name,
        weather_description=weather_data.weather_description,
        temperature=weather_data.temperature,
        precipitation_probability=weather_data.precipitation_probability,
        wind=weather_data.wind,
        timestamp=weather_data.timestamp,
        is_alert=False,  # 警報情報は別途設定
        alert_description=None
    )


class AIMessageService:
    """Google Gemini AIを使用したメッセージ生成サービス"""
    
    def __init__(self, config: Config):
        self.config = config
        self.logger = logging.getLogger(__name__)
        self._client = None
        self._model = None
        self._initialize_client()
    
    def _initialize_client(self) -> None:
        """Gemini APIクライアントを初期化"""
        try:
            if not self.config.GEMINI_API_KEY:
                self.logger.warning("Gemini APIキーが設定されていません。フォールバック機能を使用します。")
                return
            
            genai.configure(api_key=self.config.GEMINI_API_KEY)
            
            # 安全設定を構成
            safety_settings = {
                HarmCategory.HARM_CATEGORY_HARASSMENT: HarmBlockThreshold.BLOCK_MEDIUM_AND_ABOVE,
                HarmCategory.HARM_CATEGORY_HATE_SPEECH: HarmBlockThreshold.BLOCK_MEDIUM_AND_ABOVE,
                HarmCategory.HARM_CATEGORY_SEXUALLY_EXPLICIT: HarmBlockThreshold.BLOCK_MEDIUM_AND_ABOVE,
                HarmCategory.HARM_CATEGORY_DANGEROUS_CONTENT: HarmBlockThreshold.BLOCK_MEDIUM_AND_ABOVE,
            }
            
            # モデルを初期化
            self._model = genai.GenerativeModel(
                model_name='gemini-1.5-flash',
                safety_settings=safety_settings
            )
            
            self.logger.info("Gemini AIクライアントが正常に初期化されました")
            
        except Exception as e:
            self.logger.error(f"Gemini AIクライアントの初期化に失敗しました: {e}")
            self._model = None
    
    async def generate_positive_message(
        self, 
        weather_context: WeatherContext,
        message_type: str = "general"
    ) -> str:
        """
        天気情報に基づいてポジティブなメッセージを生成
        
        Args:
            weather_context: 天気情報のコンテキスト
            message_type: メッセージタイプ（general, morning, evening, alert）
        
        Returns:
            生成されたポジティブメッセージ
        """
        if not self._model:
            return self._get_fallback_message(weather_context, message_type)
        
        try:
            prompt = self._create_prompt(weather_context, message_type)
            
            # 非同期でメッセージを生成
            response = await asyncio.get_event_loop().run_in_executor(
                None, 
                lambda: self._model.generate_content(prompt)
            )
            
            if response and response.text:
                generated_message = response.text.strip()
                self.logger.info(f"AIメッセージが正常に生成されました: {len(generated_message)}文字")
                return generated_message
            else:
                self.logger.warning("AIからの応答が空でした。フォールバックメッセージを使用します。")
                return self._get_fallback_message(weather_context, message_type)
                
        except Exception as e:
            # レート制限エラーの場合は特別にログ出力
            if "429" in str(e) or "quota" in str(e).lower():
                self.logger.warning(f"Gemini APIのレート制限に達しました。フォールバックメッセージを使用します。")
            else:
                self.logger.error(f"AIメッセージ生成中にエラーが発生しました: {e}")
            return self._get_fallback_message(weather_context, message_type)
    
    def _create_prompt(self, weather_context: WeatherContext, message_type: str) -> str:
        """AIメッセージ生成用のプロンプトを作成"""
        base_prompt = f"""
あなたは親しみやすい天気予報アシスタントです。以下の天気情報に基づいて、
ユーザーを励まし、前向きな気持ちにさせる短いメッセージを日本語で生成してください。

天気情報:
- 地域: {weather_context.area_name}
- 天気: {weather_context.weather_description}
- 気温: {weather_context.temperature}°C (情報がある場合)
- 降水確率: {weather_context.precipitation_probability}%
- 風: {weather_context.wind}
- 時刻: {weather_context.timestamp.strftime('%Y年%m月%d日 %H時')}
"""
        
        if weather_context.is_alert and weather_context.alert_description:
            base_prompt += f"\n- 気象警報: {weather_context.alert_description}"
        
        # メッセージタイプに応じてプロンプトを調整
        if message_type == "morning":
            base_prompt += "\n\n朝の挨拶として、今日一日を前向きに過ごせるようなメッセージをお願いします。"
        elif message_type == "evening":
            base_prompt += "\n\n夕方の挨拶として、一日お疲れ様の気持ちを込めたメッセージをお願いします。"
        elif message_type == "alert":
            base_prompt += "\n\n気象警報が出ていますが、安全に過ごすためのアドバイスと励ましのメッセージをお願いします。"
        else:
            base_prompt += "\n\n天気に関連した前向きで励ましのメッセージをお願いします。"
        
        base_prompt += """

要件:
- 100文字以内で簡潔に
- 親しみやすく温かい口調で
- 天気に応じた具体的なアドバイスや励ましを含める
- 絵文字を適度に使用して親しみやすさを演出
- ネガティブな表現は避け、常にポジティブな視点で
"""
        
        return base_prompt
    
    def _get_fallback_message(
        self, 
        weather_context: WeatherContext, 
        message_type: str
    ) -> str:
        """AIが利用できない場合のフォールバックメッセージ"""
        
        # 気象警報がある場合の特別なメッセージ
        if weather_context.is_alert:
            return f"⚠️ {weather_context.area_name}に気象警報が発表されています。安全第一で過ごしてくださいね！ 🙏"
        
        # 降水確率に基づくメッセージ
        if weather_context.precipitation_probability >= 70:
            messages = [
                f"☔ {weather_context.area_name}は雨の予報ですが、雨音を聞きながらゆっくり過ごすのも素敵ですね！ 🌧️✨",
                f"🌂 雨の日は読書や映画鑑賞にぴったり！{weather_context.area_name}での素敵な時間をお過ごしください 📚",
                f"☔ 雨の{weather_context.area_name}も美しいもの。傘を忘れずに、安全にお出かけくださいね！ 🌈"
            ]
        elif weather_context.precipitation_probability >= 30:
            messages = [
                f"🌤️ {weather_context.area_name}は少し雲が多めですが、きっと素敵な一日になりますよ！ ☁️✨",
                f"⛅ 曇り空の{weather_context.area_name}も趣があって良いですね。今日も頑張りましょう！ 💪",
                f"🌥️ お天気は変わりやすそうですが、{weather_context.area_name}での一日を楽しんでくださいね！ 🌟"
            ]
        else:
            messages = [
                f"☀️ {weather_context.area_name}は良いお天気！今日も素晴らしい一日になりそうですね！ 🌟",
                f"🌞 晴れの{weather_context.area_name}で、きっと気分も晴れやかになりますよ！ ✨",
                f"☀️ 青空の{weather_context.area_name}！外に出かけるのにぴったりの日ですね！ 🚶‍♀️"
            ]
        
        # メッセージタイプに応じて調整
        if message_type == "morning":
            prefix = "おはようございます！ "
        elif message_type == "evening":
            prefix = "お疲れ様です！ "
        else:
            prefix = ""
        
        # ランダムにメッセージを選択（実際にはハッシュベースで一貫性を保つ）
        import hashlib
        hash_input = f"{weather_context.area_name}{weather_context.timestamp.date()}"
        hash_value = int(hashlib.md5(hash_input.encode()).hexdigest(), 16)
        selected_message = messages[hash_value % len(messages)]
        
        return prefix + selected_message
    
    async def generate_weather_summary_message(
        self, 
        weather_context: WeatherContext,
        forecast_days: int = 3
    ) -> str:
        """
        天気予報の要約メッセージを生成
        
        Args:
            weather_context: 天気情報のコンテキスト
            forecast_days: 予報日数
        
        Returns:
            要約メッセージ
        """
        if not self._model:
            return self._get_summary_fallback_message(weather_context)
        
        try:
            prompt = f"""
以下の天気情報を基に、{forecast_days}日間の天気の傾向を簡潔にまとめてください。

地域: {weather_context.area_name}
現在の天気: {weather_context.weather_description}
気温: {weather_context.temperature}°C
降水確率: {weather_context.precipitation_probability}%

50文字以内で、今後の天気の傾向と過ごし方のアドバイスを含めてください。
親しみやすい口調で、絵文字も使用してください。
"""
            
            response = await asyncio.get_event_loop().run_in_executor(
                None, 
                lambda: self._model.generate_content(prompt)
            )
            
            if response and response.text:
                return response.text.strip()
            else:
                return self._get_summary_fallback_message(weather_context)
                
        except Exception as e:
            self.logger.error(f"要約メッセージ生成中にエラーが発生しました: {e}")
            return self._get_summary_fallback_message(weather_context)
    
    def _get_summary_fallback_message(self, weather_context: WeatherContext) -> str:
        """要約メッセージのフォールバック"""
        if weather_context.precipitation_probability >= 50:
            return f"🌧️ {weather_context.area_name}は雨の可能性が高めです。傘の準備をお忘れなく！"
        else:
            return f"☀️ {weather_context.area_name}は比較的良いお天気が続きそうです！"
    
    def is_available(self) -> bool:
        """AIサービスが利用可能かどうかを確認"""
        return self._model is not None
    
    async def health_check(self) -> Dict[str, Any]:
        """AIサービスのヘルスチェック"""
        if not self._model:
            return {
                "status": "unavailable",
                "message": "Gemini APIが設定されていません",
                "fallback_available": True
            }
        
        try:
            # 簡単なテストメッセージを生成
            test_context = WeatherContext(
                area_name="テスト地域",
                weather_description="晴れ",
                temperature=20.0,
                precipitation_probability=10,
                wind="北の風",
                timestamp=datetime.now()
            )
            
            test_message = await self.generate_positive_message(test_context)
            
            return {
                "status": "available",
                "message": "Gemini AIサービスは正常に動作しています",
                "test_message_length": len(test_message),
                "fallback_available": True
            }
            
        except Exception as e:
            return {
                "status": "error",
                "message": f"Gemini AIサービスでエラーが発生しました: {str(e)}",
                "fallback_available": True
            }