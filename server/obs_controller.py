import logging
import subprocess
import time
import os
import psutil
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
        self.obs_config = config.get("obs", {})
        
        if not OBS_AVAILABLE:
            self.logger.warning("obs-websocket-py が見つかりません。OBS制御は無効です。")
    
    def is_obs_running(self):
        """OBSプロセスが起動しているかチェック"""
        try:
            for proc in psutil.process_iter(['pid', 'name']):
                if 'obs' in proc.info['name'].lower():
                    self.logger.info(f"OBSプロセス発見: {proc.info['name']} (PID: {proc.info['pid']})")
                    return True
            return False
        except Exception as e:
            self.logger.error(f"OBSプロセス確認エラー: {e}")
            return False
     
    def start_obs(self):
        """OBSを起動"""
        obs_path = self.obs_config.get("executable_path", "")
        
        if not obs_path or not os.path.exists(obs_path):
            self.logger.error(f"OBS実行ファイルが見つかりません: {obs_path}")
            return False
        
        try:
            self.logger.info(f"OBS起動中: {obs_path}")
            subprocess.Popen([obs_path], shell=True)
            
            # 起動待機
            startup_wait = self.obs_config.get("startup_wait", 10)
            self.logger.info(f"OBS起動待機: {startup_wait}秒")
            time.sleep(startup_wait)
            
            return True
        except Exception as e:
            self.logger.error(f"OBS起動エラー: {e}")
            return False
    
    def ensure_obs_ready(self):
        """OBSが準備完了状態になるまで確認"""
        retry_attempts = self.obs_config.get("retry_attempts", 3)
        retry_delay = self.obs_config.get("retry_delay", 5)
        
        for attempt in range(retry_attempts):
            self.logger.info(f"OBS接続確認 {attempt + 1}/{retry_attempts}")
            
            # プロセス確認
            if not self.is_obs_running():
                self.logger.warning("OBSプロセスが見つかりません。起動を試行します...")
                if not self.start_obs():
                    self.logger.error("OBS起動失敗")
                    if attempt < retry_attempts - 1:
                        time.sleep(retry_delay)
                        continue
                    else:
                        return False
            
            # WebSocket接続確認
            if self.connect():
                self.logger.info("OBS WebSocket接続成功")
                self.disconnect()
                return True
            else:
                self.logger.warning(f"OBS WebSocket接続失敗。{retry_delay}秒後にリトライ...")
                if attempt < retry_attempts - 1:
                    time.sleep(retry_delay)
        
        self.logger.error("OBS準備完了に失敗しました")
        return False
        
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

    # 他の既存メソッドはそのまま...
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

    def add_media_source(self, scene_name: str, source_name: str, file_path: str):
        """メディアソース（動画）を追加"""
        if not self.ws:
            self.logger.warning("OBS未接続")
            return False

        # 絶対パスに変換し、Windowsパスの場合はスラッシュに統一
        import os
        abs_path = os.path.abspath(file_path)
        # Windowsパスをスラッシュに変換（OBS互換性）
        normalized_path = abs_path.replace('\\', '/')

        source_settings = {
            "local_file": normalized_path,
            "looping": False,
            "restart_on_activate": True,
            "hw_decode": True,
            "clear_on_media_end": False
        }

        try:
            self.ws.call(requests.CreateInput(
                sceneName=scene_name,
                inputName=source_name,
                inputKind="ffmpeg_source",
                inputSettings=source_settings
            ))
            self.logger.info(f"メディアソース追加: {source_name} ({normalized_path})")
            return True
        except Exception as e:
            self.logger.error(f"メディアソース追加エラー: {e}")
            return False

    def play_media_source(self, source_name: str):
        """メディアソースを再生"""
        if not self.ws:
            self.logger.warning(f"OBS未接続 - メディア再生模擬: {source_name}")
            return False

        try:
            self.ws.call(requests.TriggerMediaInputAction(
                inputName=source_name,
                mediaAction="OBS_WEBSOCKET_MEDIA_INPUT_ACTION_RESTART"
            ))
            self.logger.info(f"メディア再生: {source_name}")
            return True
        except Exception as e:
            self.logger.error(f"メディア再生エラー: {e}")
            return False

    def get_media_duration(self, source_name: str) -> Optional[float]:
        """メディアソースの再生時間を取得（ミリ秒）"""
        if not self.ws:
            return None

        try:
            response = self.ws.call(requests.GetMediaInputStatus(inputName=source_name))
            duration = response.getMediaDuration()
            self.logger.debug(f"メディア再生時間: {source_name} = {duration}ms")
            return duration / 1000.0  # 秒に変換
        except Exception as e:
            self.logger.error(f"メディア時間取得エラー: {e}")
            return None

    def wait_for_media_end(self, source_name: str, timeout: float = 600.0):
        """メディアソースの再生終了を待機"""
        if not self.ws:
            self.logger.warning(f"OBS未接続 - 待機模擬: {source_name}")
            return False

        try:
            duration = self.get_media_duration(source_name)
            if duration:
                self.logger.info(f"メディア再生待機: {source_name} ({duration:.1f}秒)")
                time.sleep(min(duration, timeout))
                return True
            else:
                self.logger.warning(f"メディア時間取得失敗。タイムアウト待機: {timeout}秒")
                time.sleep(timeout)
                return False
        except Exception as e:
            self.logger.error(f"メディア待機エラー: {e}")
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
        
    def find_obs_executable(self):
        """OBS実行ファイルを自動検出"""
        possible_paths = [
            "C:/Program Files/obs-studio/bin/64bit/obs64.exe",
            "C:/Program Files (x86)/obs-studio/bin/64bit/obs64.exe", 
            "C:/Program Files/OBS Studio/bin/64bit/obs64.exe",
            "C:/Program Files (x86)/OBS Studio/bin/64bit/obs64.exe",
            "obs64.exe",  # PATH環境変数から
            "obs.exe"     # PATH環境変数から
        ]
        
        for path in possible_paths:
            if path.endswith('.exe'):
                if os.path.exists(path):
                    self.logger.info(f"OBS実行ファイル発見: {path}")
                    return path
            else:
                # PATH環境変数から検索
                try:
                    result = subprocess.run(['where', path], 
                                        capture_output=True, text=True, shell=True)
                    if result.returncode == 0:
                        found_path = result.stdout.strip().split('\n')[0]
                        self.logger.info(f"OBS実行ファイル発見(PATH): {found_path}")
                        return found_path
                except:
                    continue
        
        self.logger.error("OBS実行ファイルが見つかりません")
        return None

    def start_obs(self):
        """OBSを起動"""
        obs_path = self.obs_config.get("executable_path", "")
        
        # パス自動検出
        if not obs_path or not os.path.exists(obs_path):
            self.logger.warning("設定されたOBSパスが無効です。自動検出を試行...")
            obs_path = self.find_obs_executable()
        
        if not obs_path:
            self.logger.error("OBS実行ファイルが見つかりません")
            return False
        
        try:
            self.logger.info(f"OBS起動中: {obs_path}")
            
            # 作業ディレクトリをOBSのディレクトリに設定
            obs_dir = os.path.dirname(obs_path)
            
            # プロセス起動（作業ディレクトリ指定）
            subprocess.Popen([obs_path], 
                            cwd=obs_dir,  # 作業ディレクトリ指定
                            shell=False)  # shell=Falseに変更
            
            # 起動待機
            startup_wait = self.obs_config.get("startup_wait", 15)
            self.logger.info(f"OBS起動待機: {startup_wait}秒")
            time.sleep(startup_wait)
            
            return True
        except Exception as e:
            self.logger.error(f"OBS起動エラー: {e}")
            return False
        



if __name__ == "__main__":
    # ログ設定
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    
    print("🔧 OBSコントローラー テスト開始")
    
    # テスト用設定（正しいパス）
    test_config = {
        "servers": {
            "obs_websocket_host": "localhost",
            "obs_websocket_port": 4455,
            "obs_password": ""
        },
        "obs": {
            "executable_path": "C:/utility/OBS/bin/64bit/obs64.exe",  # ← 正しいパス
            "startup_wait": 15,
            "retry_attempts": 3,
            "retry_delay": 5
        }
    }
    
    obs = OBSController(test_config)
    
    print("1. OBSプロセス確認...")
    if obs.is_obs_running():
        print("✅ OBSプロセス稼働中")
    else:
        print("❌ OBSプロセス未稼働")
    
    print("\n2. OBS準備完了確認...")
    if obs.ensure_obs_ready():
        print("✅ OBS準備完了")
    else:
        print("❌ OBS準備失敗")
    
    print("\n🔧 テスト終了")