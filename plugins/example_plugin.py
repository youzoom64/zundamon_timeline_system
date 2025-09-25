import logging
from . import BasePlugin

class ExamplePlugin(BasePlugin):
    """プラグイン実装例"""
    
    def __init__(self, config):
        super().__init__(config)
        self.logger = logging.getLogger(__name__)
        self.speech_count = 0
    
    async def on_system_start(self):
        """システム開始時"""
        self.logger.info(f"[{self.name}] システム開始")
    
    async def on_system_stop(self):
        """システム終了時"""
        self.logger.info(f"[{self.name}] システム終了 - 総発話数: {self.speech_count}")
    
    async def on_timeline_start(self):
        """タイムライン開始時"""
        self.logger.info(f"[{self.name}] タイムライン開始")
        self.speech_count = 0
    
    async def on_speech_start(self, text):
        """音声合成開始時"""
        self.speech_count += 1
        self.logger.info(f"[{self.name}] 発話開始 #{self.speech_count}: {text[:20]}...")
        
        # 特定の単語に反応
        if "こんにちは" in text:
            self.logger.info(f"[{self.name}] 挨拶を検出しました")
        
        if self.speech_count % 10 == 0:
            self.logger.info(f"[{self.name}] 発話数が{self.speech_count}回に達しました")
    
    async def on_comment_received(self, comment_data):
        """コメント受信時"""
        username = comment_data.get("username", "unknown")
        text = comment_data.get("text", "")
        self.logger.info(f"[{self.name}] コメント受信: {username} - {text}")
        
        # 特定のコメントに反応
        if "プラグイン" in text:
            self.logger.info(f"[{self.name}] プラグインについて言及されました")
    
    async def on_scene_change(self, scene_name):
        """シーン変更時"""
        self.logger.info(f"[{self.name}] シーン変更: {scene_name}")
    
    async def on_error(self, error):
        """エラー発生時"""
        self.logger.error(f"[{self.name}] エラー検出: {error}")

# プラグインクラスのエイリアス（互換性のため）
Plugin = ExamplePlugin