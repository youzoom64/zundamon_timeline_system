# ずんだもんタイムラインシステム プラグインパッケージ
"""
プラグインシステム

プラグインは以下のフック関数を実装できます:
- on_system_start(): システム開始時
- on_system_stop(): システム終了時  
- on_timeline_start(): タイムライン開始時
- on_timeline_end(): タイムライン終了時
- on_speech_start(text): 音声合成開始時
- on_speech_end(): 音声合成終了時
- on_scene_change(scene_name): OBSシーン変更時
- on_comment_received(comment_data): コメント受信時
- on_comment_response(response): コメント応答時
- on_character_change(character_data): キャラクター状態変更時
- on_error(error): エラー発生時
"""

class BasePlugin:
    """プラグインベースクラス"""
    
    def __init__(self, config):
        self.config = config
        self.name = self.__class__.__name__
    
    async def on_system_start(self):
        """システム開始時フック"""
        pass
    
    async def on_system_stop(self):
        """システム終了時フック"""
        pass
    
    async def on_timeline_start(self):
        """タイムライン開始時フック"""
        pass
    
    async def on_timeline_end(self):
        """タイムライン終了時フック"""
        pass
    
    async def on_speech_start(self, text):
        """音声合成開始時フック"""
        pass
    
    async def on_speech_end(self):
        """音声合成終了時フック"""
        pass
    
    async def on_scene_change(self, scene_name):
        """OBSシーン変更時フック"""
        pass
    
    async def on_comment_received(self, comment_data):
        """コメント受信時フック"""
        pass
    
    async def on_comment_response(self, response):
        """コメント応答時フック"""
        pass
    
    async def on_character_change(self, character_data):
        """キャラクター状態変更時フック"""
        pass
    
    async def on_error(self, error):
        """エラー発生時フック"""
        pass