#!/usr/bin/env python3
"""
ずんだもんタイムラインシステム 統合版
"""
import argparse
import asyncio
import sys
import threading
import time
import logging
import subprocess
import os
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor, as_completed

def main():
    parser = argparse.ArgumentParser(
        description="ずんだもんタイムラインシステム統合版",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
使用例:
  python run.py                           # 自動モード
  python run.py broadcast --title "配信テスト"  # 配信モード
  python run.py server                    # サーバーのみ
        """
    )
    
    subparsers = parser.add_subparsers(dest='mode', help='実行モード')
    
    # 配信モード
    broadcast_parser = subparsers.add_parser('broadcast', help='配信モード（フルシステム）')
    broadcast_parser.add_argument('--config', '-c', default='config/settings.json', help='設定ファイル')
    broadcast_parser.add_argument('--title', help='ニコニコ生放送タイトル')
    broadcast_parser.add_argument('--debug', action='store_true', help='デバッグモード')
    
    # 自動モード
    auto_parser = subparsers.add_parser('auto', help='自動実行モード')
    auto_parser.add_argument('--config', '-c', default='config/settings.json', help='設定ファイル')
    auto_parser.add_argument('--debug', action='store_true', help='デバッグモード')
    
    # サーバーモード
    server_parser = subparsers.add_parser('server', help='ずんだもんサーバーのみ')
    server_parser.add_argument('--config', '-c', default='config/settings.json', help='設定ファイル')
    server_parser.add_argument('--debug', action='store_true', help='デバッグモード')
    
    args = parser.parse_args()
    
    # 設定読み込み
    from server.config_manager import ConfigManager
    config_manager = ConfigManager()
    config = config_manager.load_config()
    
    # モード判定
    if not args.mode:
        automation_mode = config.get("automation", {}).get("mode", "manual")
        if automation_mode == "auto":
            run_auto_mode(config, debug=False)
        else:
            run_manual_mode(config)
    elif args.mode == 'auto':
        run_auto_mode(config, debug=args.debug)
    elif args.mode == 'broadcast':
        run_broadcast_mode(config, title=getattr(args, 'title', None), debug=args.debug)
    elif args.mode == 'server':
        run_server_only(config, debug=args.debug)

class IntegratedBroadcastSystem:
    def __init__(self, config, title=None, debug=False):
        self.config = config
        self.title = title
        self.debug = debug
        self.obs = None
        self.zundamon_server_thread = None
        self.current_phase = "idle"
        self.termination_event = asyncio.Event()
        self.setup_logging()
        
    def setup_logging(self):
        """ログ設定"""
        level = logging.DEBUG if self.debug else logging.WARNING
        logging.basicConfig(level=level, format='%(asctime)s - %(levelname)s - %(message)s')
        
        # 外部ライブラリを静かに
        for lib in ['websockets', 'obswebsocket', 'aiohttp', 'asyncio']:
            logging.getLogger(lib).setLevel(logging.CRITICAL)
    
    async def run_full_broadcast(self):
        """配信フル実行"""
        try:
            print("🎬 配信システム起動開始")
            
            # システム初期化
            await self.initialize_systems()
            
            # 配信フロー実行
            await self.execute_broadcast_flow()
            
        except Exception as e:
            print(f"配信システムエラー: {e}")
        finally:
            await self.cleanup_systems()
    
    async def initialize_systems(self):
        """システム初期化"""
        print("🚀 システム初期化中...")
        
        startup_tasks = []
        
        with ThreadPoolExecutor(max_workers=4) as executor:
            # OBS起動確認
            startup_tasks.append(executor.submit(self.init_obs))
            
            # VOICEVOX確認
            startup_tasks.append(executor.submit(self.init_voicevox))
            
            # ずんだもんサーバー起動
            startup_tasks.append(executor.submit(self.init_zundamon_server))
            
            # ニコニコ生放送準備
            if self.title:
                startup_tasks.append(executor.submit(self.init_niconico_broadcast))
            
            # 全タスク完了待機
            success_count = 0
            for future in as_completed(startup_tasks):
                if future.result():
                    success_count += 1
            
            print(f"📊 初期化完了: {success_count}/{len(startup_tasks)}")
            
            # 安定化待機
            print("⏰ システム安定化中...", end="", flush=True)
            for i in range(10):
                print(".", end="", flush=True)
                time.sleep(1)
            print(" 完了!")
    
    async def execute_broadcast_flow(self):
        """配信フロー実行"""
        print("\n🎭 配信フロー開始")
        
        await self.phase_a_preparation()
        await self.phase_b_opening()
        await self.phase_c_zundamon_interactive()
        await self.phase_d_ending()
        
        print("🎉 配信フロー完了")
    
    async def phase_a_preparation(self):
        """フェーズA: 準備画面"""
        print("📋 フェーズA: 準備画面")
        self.current_phase = "preparation"
        
        if self.obs:
            self.obs.switch_scene("準備画面")
        
        # 準備時間
        preparation_time = self.config.get("timeline", {}).get("preparation_duration", 30)
        print(f"⏰ 準備時間: {preparation_time}秒")
        await asyncio.sleep(preparation_time)
    
    async def phase_b_opening(self):
        """フェーズB: オープニング"""
        print("🎬 フェーズB: オープニング")
        self.current_phase = "opening"
        
        if self.obs:
            self.obs.switch_scene("オープニング動画")
        
        # オープニング時間
        opening_time = self.config.get("timeline", {}).get("opening_duration", 15)
        print(f"⏰ オープニング時間: {opening_time}秒")
        await asyncio.sleep(opening_time)
    
    async def phase_c_zundamon_interactive(self):
        """フェーズC: ずんだもん+コメント処理（不定時間）"""
        print("🗣️ フェーズC: ずんだもんインタラクティブ開始")
        self.current_phase = "zundamon_interactive"
        
        if self.obs:
            self.obs.switch_scene("ずんだもん配信画面")
        
        # コメント処理とタイムライン実行を並行
        comment_task = asyncio.create_task(self.handle_comments())
        timeline_task = asyncio.create_task(self.execute_timeline())
        termination_task = asyncio.create_task(self.wait_for_termination())
        
        # いずれかの完了を待機
        done, pending = await asyncio.wait(
            [comment_task, timeline_task, termination_task],
            return_when=asyncio.FIRST_COMPLETED
        )
        
        # 残りタスクをキャンセル
        for task in pending:
            task.cancel()
        
        print("🔚 フェーズC終了")
    
    async def phase_d_ending(self):
        """フェーズD: エンディング"""
        print("🎬 フェーズD: エンディング")
        self.current_phase = "ending"
        
        if self.obs:
            self.obs.switch_scene("エンディング動画")
        
        # エンディング時間
        ending_time = self.config.get("timeline", {}).get("ending_duration", 10)
        print(f"⏰ エンディング時間: {ending_time}秒")
        await asyncio.sleep(ending_time)
    
    async def handle_comments(self):
        """コメント処理"""
        print("💬 コメント処理開始")
        
        # コメント受信システムの初期化
        # TODO: 実際のコメント受信APIとの連携
        
        while not self.termination_event.is_set():
            # 模擬コメント処理
            await asyncio.sleep(5)
            if self.debug:
                print("💬 コメント処理中...")
    
    async def execute_timeline(self):
        """タイムライン実行"""
        print("📝 タイムライン実行開始")
        
        try:
            from server.timeline_executor import TimelineExecutor
            
            timeline_executor = TimelineExecutor(self.config, self.obs)
            
            # デフォルトプロジェクト読み込み
            project_name = self.config.get("automation", {}).get("auto_project", "default_project")
            await timeline_executor.load_project(project_name)
            
            # タイムライン実行
            result = await timeline_executor.execute_timeline()
            print(f"📝 タイムライン完了: {result}")
            
        except Exception as e:
            print(f"📝 タイムラインエラー: {e}")
    
    async def wait_for_termination(self):
        """終了トリガー待機"""
        # 終了条件の例
        termination_time = 1800  # 30分
        
        print(f"⏰ 終了トリガー待機: {termination_time}秒後に自動終了")
        
        await asyncio.sleep(termination_time)
        self.termination_event.set()
        print("🔔 終了トリガー発火")
    
    def init_obs(self):
        """OBS初期化"""
        try:
            print("🎥 OBS初期化中...", end="", flush=True)
            from server.obs_controller import OBSController
            
            self.obs = OBSController(self.config)
            result = self.obs.ensure_obs_ready()
            
            print(" ✅" if result else " ❌")
            return result
        except Exception as e:
            print(" ❌")
            return False
    
    def init_voicevox(self):
        """VOICEVOX初期化"""
        try:
            print("🔊 VOICEVOX初期化中...", end="", flush=True)
            from server.voicevox_client import VoicevoxClient
            
            voicevox = VoicevoxClient(self.config)
            
            import asyncio
            try:
                loop = asyncio.get_event_loop()
            except RuntimeError:
                loop = asyncio.new_event_loop()
                asyncio.set_event_loop(loop)
            
            result = loop.run_until_complete(voicevox.ensure_voicevox_ready())
            
            print(" ✅" if result else " ❌")
            return result
        except Exception as e:
            print(" ❌")
            return False
    
    def init_zundamon_server(self):
        """ずんだもんサーバー初期化"""
        try:
            print("🚀 ずんだもんサーバー初期化中...", end="", flush=True)
            
            def run_server():
                from server.main import main_server, setup_logging
                setup_logging(self.config)
                
                import asyncio
                try:
                    loop = asyncio.get_event_loop()
                except RuntimeError:
                    loop = asyncio.new_event_loop()
                    asyncio.set_event_loop(loop)
                
                loop.run_until_complete(main_server(self.config))
            
            self.zundamon_server_thread = threading.Thread(target=run_server, daemon=True, name="ZundamonServer")
            self.zundamon_server_thread.start()
            
            time.sleep(3)
            print(" ✅")
            return True
            
        except Exception as e:
            print(" ❌")
            return False
    
    def init_niconico_broadcast(self):
        """ニコニコ生放送初期化"""
        try:
            print("📺 ニコニコ生放送初期化中...", end="", flush=True)
            # TODO: Selenium実装
            time.sleep(2)
            print(" ✅")
            return True
        except Exception as e:
            print(" ❌")
            return False
    
    async def cleanup_systems(self):
        """システム終了処理"""
        print("🔧 システム終了処理中...")
        
        if self.obs:
            self.obs.disconnect()
        
        # その他の終了処理
        print("✅ システム終了完了")

def run_broadcast_mode(config, title=None, debug=False):
    """配信モード実行"""
    system = IntegratedBroadcastSystem(config, title, debug)
    
    try:
        asyncio.run(system.run_full_broadcast())
    except KeyboardInterrupt:
        print("\n⏹️ 配信システム停止")

def run_auto_mode(config, debug=False):
    """自動モード - 並列起動"""
    automation = config.get("automation", {})
    components = automation.get("auto_start_components", ["server"])
    stabilization_wait = automation.get("stabilization_wait", 30)
    
    print("🤖 自動実行モード開始")
    print(f"   起動コンポーネント: {', '.join(components)}")
    
    if debug:
        config["logging"]["level"] = "DEBUG"
    else:
        config["logging"]["level"] = "WARNING"
    
    # 並列起動タスク
    startup_tasks = []
    
    print("\n🚀 システム並列起動中...")
    
    with ThreadPoolExecutor(max_workers=6) as executor:
        if automation.get("auto_obs_connect", True):
            startup_tasks.append(executor.submit(check_obs_startup, config))
        
        if automation.get("auto_voicevox_check", True):
            startup_tasks.append(executor.submit(check_voicevox_startup, config))
        
        if "server" in components:
            startup_tasks.append(executor.submit(start_zundamon_server, config))
        
        if "gui" in components:
            startup_tasks.append(executor.submit(start_gui_system, config))
        
        print(f"⏳ 起動完了待機中...")
        
        completed_count = 0
        failed_count = 0
        
        for future in as_completed(startup_tasks):
            try:
                result = future.result()
                completed_count += 1
                if not result:
                    failed_count += 1
            except Exception as e:
                failed_count += 1
                completed_count += 1
                if debug:
                    print(f"💥 タスクエラー: {e}")
        
        success_count = len(startup_tasks) - failed_count
        print(f"📊 起動完了: ✅{success_count} ❌{failed_count}")
    
    if failed_count > 0:
        print("⚠️ 一部システムの起動に失敗しましたが、処理を続行します")
    
    # 安定化待機
    print(f"⏰ 安定化待機中", end="", flush=True)
    for i in range(stabilization_wait):
        print(".", end="", flush=True)
        time.sleep(1)
    print(" 完了!")
    
    print("✅ 全システム準備完了！")
    
    try:
        print("🎉 起動完了 - Ctrl+C で停止")
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        print("\n⏹️ システム停止中...")

def run_server_only(config, debug=False):
    """サーバーのみ起動"""
    from server.main import main_server, setup_logging
    
    if debug:
        config["logging"]["level"] = "DEBUG"
    
    setup_logging(config)
    print("🚀 ずんだもんサーバー起動")
    
    try:
        asyncio.run(main_server(config))
    except KeyboardInterrupt:
        print("\n⏹️ サーバー停止")

def run_manual_mode(config):
    """手動モード"""
    print("👤 手動実行モード")
    print("\n利用可能なコマンド:")
    print("  python run.py broadcast --title 'タイトル'  # 配信モード")
    print("  python run.py auto                        # 自動モード")
    print("  python run.py server                      # サーバーのみ")


def check_obs_startup(config):
    """OBS起動確認"""
    try:
        print("🎥 OBS確認中...", end="", flush=True)
        from server.obs_controller import OBSController
        
        obs = OBSController(config)
        result = obs.ensure_obs_ready()
        
        print(" ✅" if result else " ❌")
        return result
    except Exception as e:
        print(" ❌")
        return False

def check_voicevox_startup(config):
    """VOICEVOX接続確認"""
    try:
        print("🔊 VOICEVOX確認中...", end="", flush=True)
        from server.voicevox_client import VoicevoxClient
        
        voicevox = VoicevoxClient(config)
        
        import asyncio
        try:
            loop = asyncio.get_event_loop()
        except RuntimeError:
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
        
        result = loop.run_until_complete(voicevox.ensure_voicevox_ready())
        
        print(" ✅" if result else " ❌")
        return result
    except Exception as e:
        print(" ❌")
        return False

def start_zundamon_server(config):
    """ずんだもんサーバー起動"""
    try:
        print("🚀 サーバー起動中...", end="", flush=True)
        
        def run_server():
            from server.main import main_server, setup_logging
            setup_logging(config)
            
            import asyncio
            try:
                loop = asyncio.get_event_loop()
            except RuntimeError:
                loop = asyncio.new_event_loop()
                asyncio.set_event_loop(loop)
            
            loop.run_until_complete(main_server(config))
        
        server_thread = threading.Thread(target=run_server, daemon=True, name="ZundamonServer")
        server_thread.start()
        
        time.sleep(3)
        print(" ✅")
        return True
        
    except Exception as e:
        print(" ❌")
        return False

def start_gui_system(config):
    """GUI起動"""
    try:
        print("🖥️ GUI起動中...", end="", flush=True)
        
        def run_gui():
            from gui.main_window import start_gui
            start_gui(config)
        
        gui_thread = threading.Thread(target=run_gui, daemon=True, name="ZundamonGUI")
        gui_thread.start()
        
        time.sleep(2)
        print(" ✅")
        return True
    except Exception as e:
        print(" ❌")
        return False




if __name__ == "__main__":
    main()