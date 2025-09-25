import argparse
import asyncio
import websockets
import json
import signal
import os
import sys
from pathlib import Path

# サーバーモジュールインポート
sys.path.append(str(Path(__file__).parent))
from server.config_manager import ConfigManager
from server.timeline_executor import TimelineExecutor
from server.obs_controller import OBSController
from server.main import start_websocket_servers

class ZundamonSystem:
    def __init__(self, websocket_port, parent_pid):
        self.websocket_port = websocket_port
        self.parent_pid = parent_pid
        self.config = ConfigManager().load_config()
        self.timeline_executor = None
        self.obs_controller = None
        self.parent_ws = None
        self.is_running = True
        self.websocket_servers = None
        
    async def connect_to_parent(self):
        """統合システムに接続"""
        uri = f"ws://localhost:{self.websocket_port}"
        try:
            self.parent_ws = await websockets.connect(uri)
            await self.send_to_parent({"action": "system_ready"})
            print("[ずんだもん] 統合システムに接続完了")
        except Exception as e:
            print(f"[ずんだもん] 統合システム接続失敗: {e}")
            return False
        return True
    
    async def send_to_parent(self, data):
        """統合システムにメッセージ送信"""
        if self.parent_ws:
            try:
                await self.parent_ws.send(json.dumps(data))
                print(f"[ずんだもん] → 統合: {data}")
            except Exception as e:
                print(f"[ずんだもん] 送信エラー: {e}")
    
    async def handle_parent_message(self, websocket):
        """統合システムからのメッセージ処理"""
        async for message in websocket:
            try:
                data = json.loads(message)
                print(f"[ずんだもん] ← 統合: {data}")
                await self.process_command(data)
            except Exception as e:
                print(f"[ずんだもん] メッセージ処理エラー: {e}")
                await self.send_to_parent({
                    "action": "timeline_error", 
                    "error": str(e)
                })
    
    async def process_command(self, data):
        """コマンド処理"""
        action = data.get("action")
        
        if action == "ping":
            await self.send_to_parent({"action": "pong"})
            
        elif action == "start_timeline":
            project_name = data.get("project_name")
            await self.start_timeline(project_name)
            
        elif action == "comment_interrupt":
            await self.handle_comment_interrupt(data)
            
        elif action == "end_timeline":
            await self.end_timeline()
            
        elif action == "emergency_stop":
            await self.emergency_stop()
    
    async def start_timeline(self, project_name):
        """タイムライン開始"""
        try:
            print(f"[ずんだもん] タイムライン開始: {project_name}")
            
            # OBSコントローラー初期化
            self.obs_controller = OBSController(self.config)
            # self.obs_controller.connect()  # TODO: 実装後に有効化
            
            # タイムライン実行エンジン初期化
            self.timeline_executor = TimelineExecutor(self.config, self.obs_controller)
            await self.timeline_executor.load_project(project_name)
            
            await self.send_to_parent({
                "action": "timeline_started", 
                "project_name": project_name
            })
            
            # WebSocketサーバー開始
            self.websocket_servers = await start_websocket_servers(self.config)
            
            # タイムライン実行
            result = await self.timeline_executor.execute_timeline()
            
            await self.send_to_parent({
                "action": "timeline_completed",
                "duration": result.get("duration", 0),
                "actions_executed": result.get("actions_count", 0)
            })
            
        except Exception as e:
            print(f"[ずんだもん] タイムライン実行エラー: {e}")
            await self.send_to_parent({
                "action": "timeline_error",
                "error": str(e)
            })
    
    async def handle_comment_interrupt(self, data):
        """コメント割り込み処理"""
        print(f"[ずんだもん] コメント割り込み: {data}")
        
        await self.send_to_parent({"action": "comment_response_start"})
        
        # タイムライン一時停止
        if self.timeline_executor:
            self.timeline_executor.pause()
        
        # コメント対応処理（簡易実装）
        username = data.get("username", "unknown")
        text = data.get("text", "")
        response = f"{username}さん、コメントありがとうございます！「{text}」ですね。"
        
        # TODO: 実際のコメント応答処理
        await asyncio.sleep(3)  # 応答時間シミュレーション
        
        # コメント対応終了
        await self.send_to_parent({"action": "comment_response_end"})
        
        # タイムライン再開
        if self.timeline_executor:
            self.timeline_executor.resume()
    
    async def end_timeline(self):
        """タイムライン終了"""
        print("[ずんだもん] タイムライン終了処理")
        
        if self.timeline_executor:
            self.timeline_executor.stop()
        
        if self.websocket_servers:
            # WebSocketサーバー停止
            pass  # TODO: サーバー停止処理
        
        await self.send_to_parent({"action": "shutdown_ready"})
    
    async def emergency_stop(self):
        """緊急停止"""
        print("[ずんだもん] 緊急停止")
        await self.end_timeline()
    
    def check_parent_alive(self):
        """親プロセス生存確認"""
        try:
            os.kill(self.parent_pid, 0)
            return True
        except OSError:
            return False
    
    async def run(self):
        """メイン実行"""
        print("[ずんだもん] システム起動")
        
        # 統合システム接続
        if not await self.connect_to_parent():
            return
        
        # メインループ
        try:
            await self.handle_parent_message(self.parent_ws)
        except Exception as e:
            print(f"[ずんだもん] 実行エラー: {e}")
        finally:
            await self.send_to_parent({"action": "shutdown_ready"})
            print("[ずんだもん] システム終了")

def main():
    parser = argparse.ArgumentParser(description="ずんだもんタイムラインシステム")
    parser.add_argument("--websocket-port", type=int, required=True, help="統合システムとの通信ポート")
    parser.add_argument("--parent-pid", type=int, required=True, help="統合システムのプロセスID")
    args = parser.parse_args()
    
    system = ZundamonSystem(args.websocket_port, args.parent_pid)
    
    # シグナルハンドラー設定
    def signal_handler(signum, frame):
        print("\n[ずんだもん] 停止シグナル受信")
        system.is_running = False
    
    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)
    
    try:
        asyncio.run(system.run())
    except KeyboardInterrupt:
        print("[ずんだもん] キーボード割り込み")

if __name__ == "__main__":
    main()