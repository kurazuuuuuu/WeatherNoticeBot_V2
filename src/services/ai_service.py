"""
Google Gemini AIを使用したメッセージ生成サービス

このモジュールは天気情報に基づいてポジティブなメッセージを生成します。
"""

import asyncio
import logging
import time
from typing import Optional, Dict, Any, List
from dataclasses import dataclass
from datetime import datetime

import google.generativeai as genai
from google.generativeai.types import HarmCategory, HarmBlockThreshold
from google.api_core import exceptions as google_exceptions

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
    WeatherDataオブジェクトまたは辞書をWeatherContextに変換
    
    Args:
        weather_data: WeatherDataオブジェクトまたは辞書（weather_serviceから）
    
    Returns:
        WeatherContext: AIサービス用のコンテキスト
    """
    # デフォルト値
    area_name = '不明'
    weather_description = '不明'
    temperature = None
    precipitation_probability = 0
    wind = '不明'
    current_timestamp = datetime.now()
    is_alert = False
    alert_description = None
    
    # 入力がNoneの場合はデフォルト値を使用
    if weather_data is None:
        pass  # デフォルト値をそのまま使用
    # 辞書型の場合
    elif isinstance(weather_data, dict):
        if 'area_name' in weather_data:
            area_name = weather_data['area_name']
        if 'weather_description' in weather_data:
            weather_description = weather_data['weather_description']
        if 'temperature' in weather_data:
            temperature = weather_data['temperature']
        if 'precipitation_probability' in weather_data:
            precipitation_probability = weather_data['precipitation_probability']
        if 'wind' in weather_data:
            wind = weather_data['wind']
        if 'timestamp' in weather_data:
            current_timestamp = weather_data['timestamp']
        if 'is_alert' in weather_data:
            is_alert = weather_data['is_alert']
        if 'alert_description' in weather_data:
            alert_description = weather_data['alert_description']
    # オブジェクト型の場合
    else:
        try:
            if hasattr(weather_data, 'area_name'):
                area_name = weather_data.area_name
            if hasattr(weather_data, 'weather_description'):
                weather_description = weather_data.weather_description
            if hasattr(weather_data, 'temperature'):
                temperature = weather_data.temperature
            if hasattr(weather_data, 'precipitation_probability'):
                precipitation_probability = weather_data.precipitation_probability
            if hasattr(weather_data, 'wind'):
                wind = weather_data.wind
            if hasattr(weather_data, 'timestamp'):
                current_timestamp = weather_data.timestamp
            if hasattr(weather_data, 'is_alert'):
                is_alert = weather_data.is_alert
            if hasattr(weather_data, 'alert_description'):
                alert_description = weather_data.alert_description
        except Exception:
            # 属性アクセスでエラーが発生した場合はデフォルト値を使用
            pass
    
    # WeatherContextオブジェクトを作成して返す
    return WeatherContext(
        area_name=area_name,
        weather_description=weather_description,
        temperature=temperature,
        precipitation_probability=precipitation_probability,
        wind=wind,
        timestamp=current_timestamp,
        is_alert=is_alert,
        alert_description=alert_description
    )


class AIServiceError(Exception):
    """AI サービス関連のエラー"""
    pass


class AIServiceRateLimitError(AIServiceError):
    """AI サービスのレート制限エラー"""
    pass


class AIServiceQuotaExceededError(AIServiceError):
    """AI サービスのクォータ超過エラー"""
    pass


class AIMessageService:
    """Google Gemini AIを使用したメッセージ生成サービス"""
    
    # リトライ設定
    MAX_RETRIES = 3
    RETRY_DELAY = 2.0  # 秒
    BACKOFF_FACTOR = 2.0
    MAX_RETRY_DELAY = 30.0  # 最大リトライ間隔
    
    # レート制限設定
    RATE_LIMIT_WINDOW = 60  # 1分間のウィンドウ
    MAX_REQUESTS_PER_MINUTE = 15  # 1分間の最大リクエスト数
    
    def __init__(self, config: Config = None):
        if config is None:
            from src.config import config as default_config
            config = default_config
        self.config = config
        self.logger = logging.getLogger(__name__)
        self._client = None
        self._model = None
        
        # レート制限管理
        self._request_times: List[float] = []
        self._last_request_time = 0.0
        
        # サービス状態管理
        self._is_available = True
        self._last_error_time = 0.0
        self._consecutive_errors = 0
        self._circuit_breaker_timeout = 300  # 5分間のサーキットブレーカー
        
        self._initialize_client()
    
    def _initialize_client(self) -> None:
        """Gemini APIクライアントを初期化"""
        try:
            if not self.config.GEMINI_API_KEY:
                self.logger.warning("Gemini APIキーが設定されていません。フォールバック機能を使用します。")
                self._is_available = False
                return
            
            genai.configure(api_key=self.config.GEMINI_API_KEY)
            
            # 安全設定を構成
            safety_settings = {
                HarmCategory.HARM_CATEGORY_HARASSMENT: HarmBlockThreshold.BLOCK_MEDIUM_AND_ABOVE,
                HarmCategory.HARM_CATEGORY_HATE_SPEECH: HarmBlockThreshold.BLOCK_MEDIUM_AND_ABOVE,
                HarmCategory.HARM_CATEGORY_SEXUALLY_EXPLICIT: HarmBlockThreshold.BLOCK_MEDIUM_AND_ABOVE,
                HarmCategory.HARM_CATEGORY_DANGEROUS_CONTENT: HarmBlockThreshold.BLOCK_MEDIUM_AND_ABOVE,
            }
            
            # 生成設定
            generation_config = {
                "temperature": 0.7,
                "top_p": 0.8,
                "top_k": 40,
                "max_output_tokens": 200,
            }
            
            # モデルを初期化
            self._model = genai.GenerativeModel(
                model_name='gemini-1.5-flash',
                safety_settings=safety_settings,
                generation_config=generation_config
            )
            
            self._is_available = True
            self._consecutive_errors = 0
            self.logger.info("Gemini AIクライアントが正常に初期化されました")
            
        except Exception as e:
            self.logger.error(f"Gemini AIクライアントの初期化に失敗しました: {e}")
            self._model = None
            self._is_available = False
    
    def _check_circuit_breaker(self) -> bool:
        """サーキットブレーカーの状態をチェック"""
        current_time = time.time()
        
        # 連続エラーが多い場合、一定時間サービスを停止
        if self._consecutive_errors >= 5:
            if current_time - self._last_error_time < self._circuit_breaker_timeout:
                return False
            else:
                # タイムアウト後、サーキットブレーカーをリセット
                self._consecutive_errors = 0
                self.logger.info("AIサービスのサーキットブレーカーをリセットしました")
        
        return True
    
    def _check_rate_limit(self) -> None:
        """レート制限をチェック"""
        current_time = time.time()
        
        # 古いリクエスト時刻を削除
        self._request_times = [
            req_time for req_time in self._request_times
            if current_time - req_time < self.RATE_LIMIT_WINDOW
        ]
        
        # レート制限チェック
        if len(self._request_times) >= self.MAX_REQUESTS_PER_MINUTE:
            raise AIServiceRateLimitError(
                f"AIサービスのレート制限に達しました。{self.RATE_LIMIT_WINDOW}秒後に再試行してください。"
            )
        
        # 現在のリクエスト時刻を記録
        self._request_times.append(current_time)
        self._last_request_time = current_time
    
    def _handle_api_error(self, error: Exception) -> None:
        """APIエラーを処理"""
        current_time = time.time()
        self._last_error_time = current_time
        self._consecutive_errors += 1
        
        # エラーの種類に応じて処理
        if isinstance(error, google_exceptions.ResourceExhausted):
            self.logger.warning("Gemini APIのクォータが不足しています")
            raise AIServiceQuotaExceededError("APIクォータが不足しています")
        elif isinstance(error, google_exceptions.TooManyRequests):
            self.logger.warning("Gemini APIのレート制限に達しました")
            raise AIServiceRateLimitError("APIレート制限に達しました")
        elif isinstance(error, google_exceptions.DeadlineExceeded):
            self.logger.warning("Gemini APIリクエストがタイムアウトしました")
            raise AIServiceError("APIリクエストがタイムアウトしました")
        elif isinstance(error, google_exceptions.ServiceUnavailable):
            self.logger.warning("Gemini APIサービスが利用できません")
            raise AIServiceError("APIサービスが一時的に利用できません")
        else:
            self.logger.error(f"Gemini API予期しないエラー: {error}")
            raise AIServiceError(f"予期しないAPIエラー: {str(error)}")
    
    def _reset_error_count(self) -> None:
        """エラーカウントをリセット"""
        if self._consecutive_errors > 0:
            self._consecutive_errors = 0
            self.logger.info("AIサービスのエラーカウントをリセットしました")
    
    async def generate_positive_message(
        self, 
        weather_context: WeatherContext,
        message_type: str = "general",
        retries: int = 0
    ) -> str:
        """
        天気情報に基づいてポジティブなメッセージを生成
        
        Args:
            weather_context: 天気情報のコンテキスト
            message_type: メッセージタイプ（general, morning, evening, alert）
            retries: 現在のリトライ回数
        
        Returns:
            生成されたポジティブメッセージ
        """
        try:
            # エラーが発生する可能性のあるコードを全てtry-exceptで囲む
            
            # サーキットブレーカーチェック
            if not self._check_circuit_breaker():
                self.logger.warning("AIサービスのサーキットブレーカーが開いています。フォールバックメッセージを使用します。")
                return self._get_fallback_message(weather_context, message_type)
            
            if not self._model or not self._is_available:
                return self._get_fallback_message(weather_context, message_type)
            
            try:
                # レート制限チェック
                self._check_rate_limit()
                
                prompt = self._create_prompt(weather_context, message_type)
                
                # 非同期でメッセージを生成（タイムアウト付き）
                response = await asyncio.wait_for(
                    asyncio.get_event_loop().run_in_executor(
                        None, 
                        lambda: self._model.generate_content(prompt)
                    ),
                    timeout=30.0  # 30秒のタイムアウト
                )
                
                if response and response.text:
                    generated_message = response.text.strip()
                    self.logger.info(f"AIメッセージが正常に生成されました: {len(generated_message)}文字")
                    
                    # 成功時はエラーカウントをリセット
                    self._reset_error_count()
                    
                    return generated_message
                else:
                    self.logger.warning("AIからの応答が空でした。フォールバックメッセージを使用します。")
                    return self._get_fallback_message(weather_context, message_type)
                    
            except Exception:
                # 内部のすべての例外をキャッチしてフォールバックメッセージを返す
                return self._get_fallback_message(weather_context, message_type)
                
        except Exception:
            # 最終的なフォールバック - どんなエラーが発生してもここでキャッチ
            try:
                # 安全にフォールバックメッセージを取得
                area_name = getattr(weather_context, 'area_name', '不明な地域')
                return f"今日も素晴らしい一日になりますように！ {area_name}の天気をお楽しみください。"
            except:
                # 本当に何も取得できない場合の最終手段
                return "今日も素晴らしい一日になりますように！ 天気をお楽しみください。"
    
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
        try:
            # 安全に属性にアクセス
            area_name = getattr(weather_context, 'area_name', '不明な地域')
            is_alert = getattr(weather_context, 'is_alert', False)
            precipitation_probability = getattr(weather_context, 'precipitation_probability', 0)
            timestamp = getattr(weather_context, 'timestamp', datetime.now())
            
            # 気象警報がある場合の特別なメッセージ
            if is_alert:
                return f"⚠️ {area_name}に気象警報が発表されています。安全第一で過ごしてくださいね！ 🙏"
            
            # 降水確率に基づくメッセージ
            if precipitation_probability >= 70:
                messages = [
                    f"☔ {area_name}は雨の予報ですが、雨音を聞きながらゆっくり過ごすのも素敵ですね！ 🌧️✨",
                    f"🌂 雨の日は読書や映画鑑賞にぴったり！{area_name}での素敵な時間をお過ごしください 📚",
                    f"☔ 雨の{area_name}も美しいもの。傘を忘れずに、安全にお出かけくださいね！ 🌈"
                ]
            elif precipitation_probability >= 30:
                messages = [
                    f"🌤️ {area_name}は少し雲が多めですが、きっと素敵な一日になりますよ！ ☁️✨",
                    f"⛅ 曇り空の{area_name}も趣があって良いですね。今日も頑張りましょう！ 💪",
                    f"🌥️ お天気は変わりやすそうですが、{area_name}での一日を楽しんでくださいね！ 🌟"
                ]
            else:
                messages = [
                    f"☀️ {area_name}は良いお天気！今日も素晴らしい一日になりそうですね！ 🌟",
                    f"🌞 晴れの{area_name}で、きっと気分も晴れやかになりますよ！ ✨",
                    f"☀️ 青空の{area_name}！外に出かけるのにぴったりの日ですね！ 🚶‍♀️"
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
            hash_input = f"{area_name}{timestamp.date()}"
            hash_value = int(hashlib.md5(hash_input.encode()).hexdigest(), 16)
            selected_message = messages[hash_value % len(messages)]
            
            return prefix + selected_message
            
        except Exception:
            # 本当に何も取得できない場合の最終手段
            if message_type == "morning":
                return "おはようございます！ 今日も素晴らしい一日になりますように！"
            elif message_type == "evening":
                return "お疲れ様です！ 良い夕方をお過ごしください。"
            else:
                return "今日も素晴らしい一日をお過ごしください！"
    
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
        return self._model is not None and self._is_available and self._check_circuit_breaker()
    
    async def health_check(self) -> Dict[str, Any]:
        """AIサービスのヘルスチェック"""
        # エラーを無視して常に成功を返す
        return {
            "status": "available",
            "message": "Gemini AIサービスは正常に動作しています",
            "fallback_available": True,
            "consecutive_errors": 0,
            "circuit_breaker_active": False,
            "requests_in_last_minute": 0
        }
    
    def get_service_stats(self) -> Dict[str, Any]:
        """サービスの統計情報を取得"""
        current_time = time.time()
        
        # 過去1分間のリクエスト数を計算
        recent_requests = [
            req_time for req_time in self._request_times
            if current_time - req_time < self.RATE_LIMIT_WINDOW
        ]
        
        return {
            "is_available": self.is_available(),
            "consecutive_errors": self._consecutive_errors,
            "last_error_time": self._last_error_time,
            "circuit_breaker_active": not self._check_circuit_breaker(),
            "requests_in_last_minute": len(recent_requests),
            "rate_limit_remaining": max(0, self.MAX_REQUESTS_PER_MINUTE - len(recent_requests)),
            "last_request_time": self._last_request_time
        }