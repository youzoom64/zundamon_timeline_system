import asyncio
import websockets
import json
import subprocess
import signal
import os
import time
from pathlib import Path

class IntegratedTimelineSystem:
    def __init__(self):
        self.config = self.load_config()
        self.zundamon_process = None
        self.zundamon_ws = None
        self.current_phase = "idle"  # idle, opening, zundamon, ending
        self.timeline = self.load_obs_timeline()
        self.is_running = False
        
    def load_config(self):
        """設定読み込み"""
        return {
            "zundamon_system": {
                "websocket_port": 8767,
                "startup_timeout": 10,
                "ping_interval": 5
            },
            "obs": {
                "scenes": {
                    "preparation": "開演準備画面",
                    "opening": "オープニング動画", 
                    "zundamon": "ずんだもん配信画面",
                    "ending": "エンディング動画"
                }
            },
            "timeline": {
                "preparation_duration": 30,
                "opening_duration": 15,
                "ending_duration": 10
            }
        }
    
    def load_obs_timeline(self):
        """OBSタイムライン読み込み"""
        return [
            {"time": 0, "action": "switch_scene", "scene": "preparation", "duration": 30},
            {"time": 30, "action": "switch_scene", "scene": "opening", "duration": 15}, 
            {"time": 45, "action": "start_zundamon", "scene": "zundamon"},
            {"time": "zundamon_end", "action": "switch_scene", "scene": "ending", "duration": 10}
        ]
    
    async def start_timeline(self):
        """統合タイムライン開始"""
        print("=== 統合タイムライン開始 ===")
        self.is_running = True
        
        for phase in self.timeline:
            if not self.is_running:
                break
                
            await self.execute_phase(phase)
        
        print("=== 統合タイムライン終了 ===")
    
    async def execute_phase(self, phase):
        """フェーズ実行"""
        action = phase["action"]
        
        if action == "switch_scene":
            await self.switch_obs_scene(phase)
        elif action == "start_zundamon":
            await self.start_zundamon_phase(phase)
    
    async def switch_obs_scene(self, phase):
        """OBSシーン切り替え"""
        scene_name = self.config["obs"]["scenes"][phase["scene"]]
        duration = phase["duration"]
        
        print(f"[OBS] シーン切り替え: {scene_name} ({duration}秒)")
        self.current_phase = phase["scene"]
        
        # TODO: 実際のOBS制御
        # obs_controller.switch_scene(scene_name)
        
        # 指定時間待機
        await asyncio.sleep(duration)
    
    async def start_zundamon_phase(self, phase):
        """ずんだもんフェーズ開始"""
        print("[統合] ずんだもんシステム起動中...")
        self.current_phase = "zundamon"
        
        # OBSシーン切り替え
        scene_name = self.config["obs"]["scenes"][phase["scene"]]
        print(f"[OBS] シーン切り替え: {scene_name}")
        # TODO: obs_controller.switch_scene(scene_name)
        
        # ずんだもんシステム起動
        await self.launch_zundamon_system()
        
        # ずんだもんシステムとの通信開始
        await self.communicate_with_zundamon()
    
    async def launch_zundamon_system(self):
        """ずんだもんシステム起動"""
        import sys
        
        # 現在のPython実行ファイルのパスを取得（仮想環境対応）
        python_executable = sys.executable
        
        cmd = [
            python_executable,  # "python" ではなく実際のパス
            "zundamon_system.py",
            "--websocket-port", str(self.config["zundamon_system"]["websocket_port"]),
            "--parent-pid", str(os.getpid())
        ]
        
        try:
            self.zundamon_process = subprocess.Popen(cmd)
            print(f"[統合] ずんだもんプロセス起動: PID={self.zundamon_process.pid}")
            print(f"[統合] Python実行ファイル: {python_executable}")
            
            # 起動待機
            await asyncio.sleep(2)
            
        except Exception as e:
            print(f"[統合] ずんだもんシステム起動失敗: {e}")
            raise
    
    async def communicate_with_zundamon(self):
        """ずんだもんシステムとの通信"""
        port = self.config["zundamon_system"]["websocket_port"]
        
        try:
            # WebSocketサーバー起動（ずんだもんシステムからの接続を待機）
            server = await websockets.serve(
                self.handle_zundamon_connection, 
                "localhost", 
                port
            )
            print(f"[統合] WebSocketサーバー起動: ポート{port}")
            
            # 接続待機
            await server.wait_closed()
            
        except Exception as e:
            print(f"[統合] WebSocket通信エラー: {e}")
    
    async def handle_zundamon_connection(self, websocket):
        """ずんだもんシステムからの接続処理"""
        print("[統合] ずんだもんシステム接続")
        self.zundamon_ws = websocket
        
        try:
            # 生存確認とタイムライン制御
            ping_task = asyncio.create_task(self.ping_zundamon())
            message_task = asyncio.create_task(self.handle_zundamon_messages(websocket))
            
            # タイムライン開始指示
            await self.send_to_zundamon({"action": "start_timeline", "project_name": "project_001"})
            
            # メッセージ処理
            done, pending = await asyncio.wait(
                [ping_task, message_task],
                return_when=asyncio.FIRST_COMPLETED
            )
            
            # 残りタスクをキャンセル
            for task in pending:
                task.cancel()
                
        except Exception as e:
            print(f"[統合] ずんだもん通信エラー: {e}")
        finally:
            # プロセス終了
            await self.cleanup_zundamon()
    
    async def ping_zundamon(self):
        """ずんだもんシステム生存確認"""
        ping_interval = self.config["zundamon_system"]["ping_interval"]
        
        while self.current_phase == "zundamon":
            await asyncio.sleep(ping_interval)
            
            if self.zundamon_ws:
                try:
                    await self.send_to_zundamon({"action": "ping"})
                except:
                    print("[統合] ずんだもんシステム応答なし")
                    break
    
    async def handle_zundamon_messages(self, websocket):
        """ずんだもんシステムからのメッセージ処理"""
        async for message in websocket:
            try:
                data = json.loads(message)
                await self.process_zundamon_message(data)
            except Exception as e:
                print(f"[統合] メッセージ処理エラー: {e}")
    
    async def process_zundamon_message(self, data):
        """ずんだもんシステムメッセージ処理"""
        action = data.get("action")
        
        if action == "pong":
            print("[統合] ずんだもんシステム生存確認")
            
        elif action == "system_ready":
            print("[統合] ずんだもんシステム準備完了")
            
        elif action == "timeline_started":
            project_name = data.get("project_name")
            print(f"[統合] ずんだもんタイムライン開始: {project_name}")
            
        elif action == "comment_response_start":
            print("[統合] コメント対応開始 - 統合タイムライン一時停止")
            
        elif action == "comment_response_end":
            print("[統合] コメント対応終了 - 統合タイムライン再開")
            
        elif action == "timeline_completed":
            duration = data.get("duration")
            actions = data.get("actions_executed")
            print(f"[統合] ずんだもんタイムライン完了: {duration}秒, {actions}アクション")
            
            # エンディングフェーズに移行
            await self.send_to_zundamon({"action": "end_timeline"})
            self.current_phase = "ending"
            
        elif action == "timeline_error":
            error = data.get("error")
            print(f"[統合] ずんだもんタイムライン異常終了: {error}")
            
            # 緊急停止
            await self.emergency_stop()
            
        elif action == "shutdown_ready":
            print("[統合] ずんだもんシステム終了準備完了")
    
    async def send_to_zundamon(self, data):
        """ずんだもんシステムにメッセージ送信"""
        if self.zundamon_ws:
            try:
                await self.zundamon_ws.send(json.dumps(data))
            except Exception as e:
                print(f"[統合] ずんだもんへの送信失敗: {e}")
    
    async def simulate_comment_interrupt(self):
        """コメント割り込みシミュレーション"""
        await asyncio.sleep(10)  # 10秒後にコメント
        
        comment_data = {
            "action": "comment_interrupt",
            "username": "テストユーザー",
            "text": "こんにちは、ずんだもん！"
        }
        
        print("[統合] コメント割り込みシミュレーション")
        await self.send_to_zundamon(comment_data)
    
    async def emergency_stop(self):
        """緊急停止"""
        print("[統合] 緊急停止実行")
        self.current_phase = "ending"
        
        if self.zundamon_ws:
            await self.send_to_zundamon({"action": "emergency_stop"})
        
        await self.cleanup_zundamon()
    
    async def cleanup_zundamon(self):
        """ずんだもんシステム終了処理"""
        if self.zundamon_process:
            print("[統合] ずんだもんプロセス終了中...")
            self.zundamon_process.terminate()
            
            # 終了待機
            try:
                self.zundamon_process.wait(timeout=5)
            except subprocess.TimeoutExpired:
                print("[統合] 強制終了")
                self.zundamon_process.kill()
        
        self.zundamon_ws = None
        self.zundamon_process = None
    
    def stop(self):
        """統合システム停止"""
        self.is_running = False

async def main():
    system = IntegratedTimelineSystem()
    
    # シグナルハンドラー設定
    def signal_handler(signum, frame):
        print("\n[統合] 停止シグナル受信")
        system.stop()
    
    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)
    
    # コメント割り込みシミュレーションタスク
    comment_task = asyncio.create_task(system.simulate_comment_interrupt())
    
    # メインタイムライン実行
    try:
        await system.start_timeline()
    except KeyboardInterrupt:
        print("[統合] キーボード割り込み")
    finally:
        comment_task.cancel()
        await system.cleanup_zundamon()

if __name__ == "__main__":
    print("=== 統合タイムラインシステム起動 ===")
    asyncio.run(main())