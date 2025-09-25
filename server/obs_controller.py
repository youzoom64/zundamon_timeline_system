import logging
from typing import Optional

try:
    import obswebsocket
    from obswebsocket import obsws, requests
    OBS_AVAILABLE = True
except ImportError:
    OBS_AVAILABLE = False

class OBSController:
    def __init__(self, config):
        self.config = config
        self.ws = None
        self.logger = logging.getLogger(__name__)
        self.host = config["servers"]["obs_websocket_host"]
        self.port = config["servers"]["obs_websocket_port"]
        self.password = config["servers"]["obs_password"]
        
        if not OBS_AVAILABLE:
            self.logger.warning("obs-websocket-py が見つかりません。OBS制御は無効です。")
    
    def connect(self):
        """OBSに接続"""
        if not OBS_AVAILABLE:
            self.logger.warning("OBS WebSocket無効: ライブラリが見つかりません")
            return False
        
        try:
            self.ws = obsws(self.host, self.port, self.password)
            self.ws.connect()
            self.logger.info(f"OBS WebSocket接続完了: {self.host}:{self.port}")
            return True
        except Exception as e:
            self.logger.error(f"OBS WebSocket接続失敗: {e}")
            return False
    
    def disconnect(self):
        """OBS接続切断"""
        if self.ws:
            try:
                self.ws.disconnect()
                self.logger.info("OBS WebSocket切断")
            except Exception as e:
                self.logger.error(f"OBS WebSocket切断エラー: {e}")
            finally:
                self.ws = None
    
    def is_connected(self):
        """接続状態確認"""
        return self.ws is not None
    
    def create_scene(self, scene_name: str):
        """新しいシーンを作成"""
        if not self.ws:
            self.logger.warning("OBS未接続")
            return False
        
        try:
            self.ws.call(requests.CreateScene(sceneName=scene_name))
            self.logger.info(f"シーン作成: {scene_name}")
            return True
        except Exception as e:
            self.logger.error(f"シーン作成エラー: {e}")
            return False
    
    def switch_scene(self, scene_name: str):
        """シーンを切り替え"""
        if not self.ws:
            self.logger.warning(f"OBS未接続 - シーン切り替え模擬: {scene_name}")
            return False
        
        try:
            self.ws.call(requests.SetCurrentProgramScene(sceneName=scene_name))
            self.logger.info(f"シーン切り替え: {scene_name}")
            return True
        except Exception as e:
            self.logger.error(f"シーン切り替えエラー: {e}")
            return False
    
    def add_browser_source(self, scene_name: str, source_name: str, url: str, width: int = 1200, height: int = 800):
        """ブラウザソースを追加"""
        if not self.ws:
            self.logger.warning("OBS未接続")
            return False
        
        source_settings = {
            "url": url,
            "width": width,
            "height": height
        }
        
        try:
            self.ws.call(requests.CreateInput(
                sceneName=scene_name,
                inputName=source_name,
                inputKind="browser_source",
                inputSettings=source_settings
            ))
            self.logger.info(f"ブラウザソース追加: {source_name} ({url})")
            return True
        except Exception as e:
            self.logger.error(f"ブラウザソース追加エラー: {e}")
            return False
    
    def add_image_source(self, scene_name: str, source_name: str, file_path: str):
        """画像ソースを追加"""
        if not self.ws:
            self.logger.warning("OBS未接続")
            return False
        
        source_settings = {
            "file": file_path
        }
        
        try:
            self.ws.call(requests.CreateInput(
                sceneName=scene_name,
                inputName=source_name,
                inputKind="image_source",
                inputSettings=source_settings
            ))
            self.logger.info(f"画像ソース追加: {source_name} ({file_path})")
            return True
        except Exception as e:
            self.logger.error(f"画像ソース追加エラー: {e}")
            return False
    
    def update_text_source(self, source_name: str, text: str):
        """テキストソースの内容更新"""
        if not self.ws:
            self.logger.warning(f"OBS未接続 - テキスト更新模擬: {source_name} = {text}")
            return False
        
        try:
            self.ws.call(requests.SetInputSettings(
                inputName=source_name,
                inputSettings={"text": text}
            ))
            self.logger.debug(f"テキスト更新: {source_name} = {text}")
            return True
        except Exception as e:
            self.logger.error(f"テキスト更新エラー: {e}")
            return False
    
    def set_source_visibility(self, source_name: str, visible: bool):
        """ソースの表示/非表示切り替え"""
        if not self.ws:
            self.logger.warning(f"OBS未接続 - 表示切替模擬: {source_name} = {visible}")
            return False
        
        try:
            # TODO: 実装 - ソースID取得が必要
            self.logger.info(f"表示切替: {source_name} = {visible}")
            return True
        except Exception as e:
            self.logger.error(f"表示切替エラー: {e}")
            return False
    
    def get_scene_list(self):
        """シーン一覧取得"""
        if not self.ws:
            return []
        
        try:
            response = self.ws.call(requests.GetSceneList())
            scenes = [scene["sceneName"] for scene in response.getScenes()]
            return scenes
        except Exception as e:
            self.logger.error(f"シーン一覧取得エラー: {e}")
            return []
    
    def get_current_scene(self):
        """現在のシーン取得"""
        if not self.ws:
            return None
        
        try:
            response = self.ws.call(requests.GetCurrentProgramScene())
            return response.getCurrentProgramScene()
        except Exception as e:
            self.logger.error(f"現在シーン取得エラー: {e}")
            return None