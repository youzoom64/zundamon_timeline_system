import asyncio
import json
from pathlib import Path
from datetime import datetime
import logging

class TimelineExecutor:
    def __init__(self, config, obs_controller, broadcast_callback=None):
        self.config = config
        self.obs_controller = obs_controller
        self.broadcast_callback = broadcast_callback
        self.zundamon_timeline = None
        self.obs_timeline = None
        self.project_dir = None
        self.is_running = False
        self.is_paused = False
        self.start_time = None
        self.current_action_index = 0
        self.logger = logging.getLogger(__name__)
        
    async def load_project(self, project_name):
        """プロジェクト読み込み"""
        import_dir = Path(self.config["directories"]["import_dir"])
        self.project_dir = import_dir / "timeline_projects" / project_name
        
        if not self.project_dir.exists():
            raise FileNotFoundError(f"プロジェクトが見つかりません: {project_name}")
        
        # ずんだもんタイムライン読み込み
        timeline_file = self.project_dir / "timeline.json"
        if timeline_file.exists():
            with open(timeline_file, 'r', encoding='utf-8') as f:
                self.zundamon_timeline = json.load(f)
                self.logger.info(f"ずんだもんタイムライン読み込み: {timeline_file}")
        
        # OBSタイムライン読み込み
        obs_timeline_file = self.project_dir / "obs_timeline.json"
        if obs_timeline_file.exists():
            with open(obs_timeline_file, 'r', encoding='utf-8') as f:
                self.obs_timeline = json.load(f)
                self.logger.info(f"OBSタイムライン読み込み: {obs_timeline_file}")
        
        self.logger.info(f"プロジェクト読み込み完了: {project_name}")
    
    def get_latest_project(self):
        """最新プロジェクト取得"""
        import_dir = Path(self.config["directories"]["import_dir"])
        projects_dir = import_dir / "timeline_projects"
        
        if not projects_dir.exists():
            return None
        
        project_dirs = [d for d in projects_dir.iterdir() if d.is_dir()]
        if not project_dirs:
            return None
        
        # 更新時間でソート
        latest_project = max(project_dirs, key=lambda d: d.stat().st_mtime)
        return latest_project.name
    
    async def execute_timeline_from_json(self, timeline_json):
        """JSON形式のタイムラインを直接実行"""
        self.zundamon_timeline = timeline_json
        self.obs_timeline = None
        self.project_dir = None

        return await self.execute_timeline()

    async def execute_timeline(self):
        """タイムライン実行"""
        if not self.zundamon_timeline:
            raise ValueError("タイムラインが読み込まれていません")

        self.is_running = True
        self.start_time = asyncio.get_event_loop().time()
        actions_executed = 0

        try:
            # 統合タイムライン作成
            combined_timeline = self.merge_timelines()

            # OBSにテキスト情報送信
            await self.send_text_to_obs()

            # タイムライン実行
            for i, action in enumerate(combined_timeline):
                if not self.is_running:
                    break

                self.current_action_index = i

                # 一時停止待機
                while self.is_paused and self.is_running:
                    await asyncio.sleep(0.1)

                if not self.is_running:
                    break

                # 時間待機
                await self.wait_for_action_time(action["time"])

                # アクション実行
                await self.execute_action(action)
                actions_executed += 1

            # 実行結果
            end_time = asyncio.get_event_loop().time()
            duration = end_time - self.start_time

            return {
                "duration": duration,
                "actions_count": actions_executed,
                "status": "completed" if self.is_running else "stopped"
            }

        except Exception as e:
            self.logger.error(f"タイムライン実行エラー: {e}")
            raise
        finally:
            self.is_running = False
    
    def merge_timelines(self):
        """ずんだもんとOBSのタイムラインを統合"""
        combined = []
        
        # ずんだもんタイムライン
        if self.zundamon_timeline and "timeline" in self.zundamon_timeline:
            for action in self.zundamon_timeline["timeline"]:
                action["type"] = "zundamon"
                combined.append(action)
        
        # OBSタイムライン
        if self.obs_timeline and "timeline" in self.obs_timeline:
            for action in self.obs_timeline["timeline"]:
                action["type"] = "obs"
                combined.append(action)
        
        # 時間順ソート
        return sorted(combined, key=lambda x: x.get("time", 0))
    
    async def wait_for_action_time(self, target_time):
        """アクション実行時間まで待機"""
        if not self.start_time:
            return
        
        current_time = asyncio.get_event_loop().time()
        elapsed = current_time - self.start_time
        wait_time = target_time - elapsed
        
        if wait_time > 0:
            await asyncio.sleep(wait_time)
    
    async def execute_action(self, action):
        """アクション実行"""
        action_type = action.get("type", "zundamon")
        
        if action_type == "zundamon":
            await self.execute_zundamon_action(action)
        elif action_type == "obs":
            await self.execute_obs_action(action)
        
        self.logger.debug(f"アクション実行: {action}")
    
    async def execute_zundamon_action(self, action):
        """ずんだもんアクション実行"""
        if not self.broadcast_callback:
            self.logger.warning("broadcast_callbackが設定されていません")
            return

        character = action.get("character", "zundamon")
        text = action.get("text", "")

        # 音声合成して喋る
        if text:
            await self.broadcast_callback({
                "action": "speak_text",
                "text": text,
                "character": character
            })

            # 喋り終わるまで待つ（簡易実装: 1文字0.15秒として計算）
            wait_time = len(text) * 0.15 + 1.0
            await asyncio.sleep(wait_time)
    
    async def execute_obs_action(self, action):
        """OBSアクション実行"""
        obs_action = action.get("action")
        
        if obs_action == "switch_scene":
            scene_name = action.get("scene_name")
            if self.obs_controller:
                self.obs_controller.switch_scene(scene_name)
        
        elif obs_action == "update_text":
            source_name = action.get("source_name")
            text = action.get("text")
            if self.obs_controller:
                self.obs_controller.update_text_source(source_name, text)
        
        elif obs_action == "set_source_visibility":
            source_name = action.get("source_name")
            visible = action.get("visible", True)
            if self.obs_controller:
                self.obs_controller.set_source_visibility(source_name, visible)
    
    async def send_text_to_obs(self):
        """OBSにテキスト情報送信"""
        if not self.zundamon_timeline or not self.obs_controller:
            return
        
        timeline_data = self.zundamon_timeline
        
        if "title" in timeline_data:
            self.obs_controller.update_text_source("title_text", timeline_data["title"])
        if "listener_name" in timeline_data:
            self.obs_controller.update_text_source("listener_text", timeline_data["listener_name"])
        if "nickname" in timeline_data:
            self.obs_controller.update_text_source("nickname_text", timeline_data["nickname"])
        if "other_text" in timeline_data:
            self.obs_controller.update_text_source("other_text", timeline_data["other_text"])
    
    def pause(self):
        """タイムライン一時停止"""
        self.is_paused = True
        self.logger.info("タイムライン一時停止")
    
    def resume(self):
        """タイムライン再開"""
        self.is_paused = False
        self.logger.info("タイムライン再開")
    
    def stop(self):
        """タイムライン停止"""
        self.is_running = False
        self.is_paused = False
        self.logger.info("タイムライン停止")
    
    def get_status(self):
        """実行状態取得"""
        if not self.start_time:
            return {"status": "idle"}
        
        current_time = asyncio.get_event_loop().time()
        elapsed = current_time - self.start_time if self.start_time else 0
        
        return {
            "status": "running" if self.is_running else "stopped",
            "paused": self.is_paused,
            "elapsed_time": elapsed,
            "current_action": self.current_action_index,
            "project_dir": str(self.project_dir) if self.project_dir else None
        }