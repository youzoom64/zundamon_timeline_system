import asyncio
import logging
import random
from datetime import datetime

class CommentHandler:
    def __init__(self, config, timeline_executor=None, obs_controller=None):
        self.config = config
        self.timeline_executor = timeline_executor
        self.obs_controller = obs_controller
        self.logger = logging.getLogger(__name__)
        self.response_templates = self.load_response_templates()
        
    def load_response_templates(self):
        """コメント応答テンプレート読み込み"""
        return {
            "greeting": [
                "{username}さん、こんにちはなのだ！",
                "やっほー、{username}さん！",
                "{username}さん、いらっしゃいなのだ！"
            ],
            "question": [
                "{username}さん、質問ありがとうございます！",
                "うーん、{username}さんの質問は難しいのだ...",
                "{username}さん、いい質問なのだ！"
            ],
            "compliment": [
                "{username}さん、ありがとうございます！",
                "えへへ、{username}さんに褒められて嬉しいのだ！",
                "{username}さん、そんなこと言われると照れるのだ..."
            ],
            "default": [
                "{username}さん、コメントありがとうございます！",
                "{username}さんのコメント、読ませてもらったのだ！",
                "{username}さん、いつもありがとうございます！"
            ]
        }
    
    async def handle_comment_interrupt(self, comment_data, broadcast_callback):
        """コメント割り込み処理"""
        username = comment_data.get("username", "名無しさん")
        text = comment_data.get("text", "")
        
        self.logger.info(f"コメント割り込み: {username} - {text}")
        
        try:
            # タイムライン一時停止
            if self.timeline_executor:
                self.timeline_executor.pause()
            
            # コメント表示更新（OBS）
            await self.update_comment_display(username, text)
            
            # コメント応答生成
            response_text = self.generate_response(username, text)
            
            # ずんだもんに喋らせる
            await broadcast_callback({
                "action": "speak",
                "text": response_text
            })
            
            # 応答時間待機
            response_duration = self.estimate_speech_duration(response_text)
            await asyncio.sleep(response_duration)
            
            # コメント表示クリア
            await self.clear_comment_display()
            
            # タイムライン再開
            if self.timeline_executor:
                self.timeline_executor.resume()
                
        except Exception as e:
            self.logger.error(f"コメント処理エラー: {e}")
            # エラー時もタイムライン再開
            if self.timeline_executor:
                self.timeline_executor.resume()
    
    def generate_response(self, username: str, text: str):
        """コメント応答生成"""
        text_lower = text.lower()
        
        # コメント内容による分類
        if any(word in text_lower for word in ["こんにちは", "おはよう", "こんばんは", "はじめまして"]):
            template_key = "greeting"
        elif any(word in text_lower for word in ["?", "？", "どう", "なぜ", "教えて"]):
            template_key = "question"
        elif any(word in text_lower for word in ["かわいい", "すごい", "いいね", "素晴らしい"]):
            template_key = "compliment"
        else:
            template_key = "default"
        
        # テンプレートからランダム選択
        templates = self.response_templates.get(template_key, self.response_templates["default"])
        template = random.choice(templates)
        
        # プレースホルダー置換
        response = template.format(username=username)
        
        return response
    
    def estimate_speech_duration(self, text: str):
        """音声長さ推定"""
        # 日本語の場合、文字数×0.15秒程度
        base_duration = len(text) * 0.15
        # 最小2秒、最大10秒
        return max(2.0, min(base_duration, 10.0))
    
    async def update_comment_display(self, username: str, text: str):
        """コメント表示更新"""
        if self.obs_controller:
            self.obs_controller.update_text_source("comment_username", username)
            self.obs_controller.update_text_source("comment_text", text)
            self.obs_controller.update_text_source("comment_timestamp", datetime.now().strftime("%H:%M"))
    
    async def clear_comment_display(self):
        """コメント表示クリア"""
        if self.obs_controller:
            self.obs_controller.update_text_source("comment_username", "")
            self.obs_controller.update_text_source("comment_text", "")
            self.obs_controller.update_text_source("comment_timestamp", "")
    
    def add_response_template(self, category: str, template: str):
        """応答テンプレート追加"""
        if category not in self.response_templates:
            self.response_templates[category] = []
        self.response_templates[category].append(template)
    
    def set_timeline_executor(self, timeline_executor):
        """タイムライン実行エンジン設定"""
        self.timeline_executor = timeline_executor
    
    def set_obs_controller(self, obs_controller):
        """OBSコントローラー設定"""
        self.obs_controller = obs_controller