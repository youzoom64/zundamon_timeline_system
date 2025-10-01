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
    broadcast_parser.add_argument('--debug', action='store_true', help='デバッグモード')
    broadcast_parser.add_argument('username', help='配信者ユーザー名')
    broadcast_parser.add_argument('prep_video', help='開演準備動画パス')
    broadcast_parser.add_argument('opening_video', help='オープニング動画パス')
    broadcast_parser.add_argument('db_range_json', help='DB範囲指示JSONファイルパス')
    broadcast_parser.add_argument('ending_video', help='エンディング動画パス')
    
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
        run_broadcast_mode(
            config,
            username=args.username,
            prep_video=args.prep_video,
            opening_video=args.opening_video,
            db_range_json=args.db_range_json,
            ending_video=args.ending_video,
            debug=args.debug
        )
    elif args.mode == 'server':
        run_server_only(config, debug=args.debug)

class IntegratedBroadcastSystem:
    def __init__(self, config, username=None, prep_video=None, opening_video=None, db_range_json=None, ending_video=None, debug=False):
        self.config = config
        self.username = username
        self.prep_video = prep_video
        self.opening_video = opening_video
        self.db_range_json = db_range_json
        self.ending_video = ending_video
        self.debug = debug
        self.obs = None
        self.zundamon_server_thread = None
        self.zundamon_server_loop = None
        self.current_phase = "idle"
        self.termination_event = asyncio.Event()
        self.db_range_data = None
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
            print("[配信] 配信システム起動開始")

            # DB範囲JSON読み込み
            if self.db_range_json:
                self.load_db_range_json()

            # システム初期化
            await self.initialize_systems()

            # 配信フロー実行
            await self.execute_broadcast_flow()

        except Exception as e:
            print(f"配信システムエラー: {e}")
            import traceback
            traceback.print_exc()
        finally:
            await self.cleanup_systems()

    def load_db_range_json(self):
        """DB範囲JSON読み込み"""
        try:
            import json
            import os

            # 動画パスを絶対パスに変換
            if self.prep_video:
                self.prep_video = os.path.abspath(self.prep_video)
            if self.opening_video:
                self.opening_video = os.path.abspath(self.opening_video)
            if self.ending_video:
                self.ending_video = os.path.abspath(self.ending_video)

            # DB範囲JSON読み込み
            with open(self.db_range_json, 'r', encoding='utf-8') as f:
                self.db_range_data = json.load(f)
            print(f"[処理] DB範囲読み込み: user_id={self.db_range_data.get('user_id')}, broadcasts={len(self.db_range_data.get('broadcast_ids', []))}件")
        except Exception as e:
            print(f"[処理] DB範囲JSON読み込みエラー: {e}")
            self.db_range_data = None
    
    async def initialize_systems(self):
        """システム初期化"""
        print("[処理] システム初期化中...")
        
        startup_tasks = []
        
        with ThreadPoolExecutor(max_workers=4) as executor:
            # OBS起動確認
            startup_tasks.append(executor.submit(self.init_obs))
            
            # VOICEVOX確認
            startup_tasks.append(executor.submit(self.init_voicevox))
            
            # ずんだもんサーバー起動
            startup_tasks.append(executor.submit(self.init_zundamon_server))
            
            # ニコニコ生放送準備
            if self.username:
                startup_tasks.append(executor.submit(self.init_niconico_broadcast))
            
            # 全タスク完了待機
            success_count = 0
            for future in as_completed(startup_tasks):
                if future.result():
                    success_count += 1
            
            print(f"[統計] 初期化完了: {success_count}/{len(startup_tasks)}")
            
            # 安定化待機
            wait_time = self.config.get("niconico", {}).get("wait_before_start", 30)
            print(f"[タイマー] システム安定化中 ({wait_time}秒)...", end="", flush=True)
            for i in range(wait_time):
                print(".", end="", flush=True)
                time.sleep(1)
            print(" 完了!")

            # 30秒経過後、ニコニコ生放送開始
            if self.username and hasattr(self, 'chrome_driver'):
                self.start_niconico_broadcast()
    
    async def execute_broadcast_flow(self):
        """配信フロー実行"""
        print("\n[配信] 配信フロー開始")

        # OBS接続
        if self.obs:
            print("[処理] OBS接続中...")
            self.obs.connect()
            print("[待機] OBS接続安定化待機（3秒）...")
            await asyncio.sleep(3)
            print("[処理] OBS接続完了")

        await self.phase_a_preparation()
        await self.phase_b_opening()
        await self.phase_c_zundamon_interactive()
        await self.phase_d_ending()

        print("[完了] 配信フロー完了")
    
    async def phase_a_preparation(self):
        """フェーズA: 開演準備動画"""
        print("\n[データ] フェーズA: 開演準備動画")
        self.current_phase = "preparation"

        if self.obs and self.prep_video:
            print(f"   動画パス: {self.prep_video}")

            # 準備画面シーン作成
            print("   [処理] シーン作成中...")
            self.obs.create_scene(scene_name := "開演準備")
            await asyncio.sleep(1.0)

            # 動画ソース追加
            print("   [フェーズ] メディアソース追加中...")
            self.obs.add_media_source(scene_name, "準備動画", self.prep_video)
            await asyncio.sleep(2.0)  # メディアソースの読み込み待機

            # シーン切り替え
            print("   [切替] シーン切り替え中...")
            self.obs.switch_scene(scene_name)
            await asyncio.sleep(1.0)

            # 動画再生開始
            print("   [再生] 動画再生開始...")
            self.obs.play_media_source("準備動画")
            await asyncio.sleep(1.0)  # 再生開始待機

            # 動画再生時間取得
            duration = self.obs.get_media_duration("準備動画")
            if duration:
                print(f"   [時間]  再生時間: {duration:.1f}秒")
                await asyncio.sleep(duration + 1.0)
            else:
                print("   [警告] 動画長さ取得失敗、10秒待機")
                await asyncio.sleep(10)

        print("[処理] フェーズA完了")
    
    async def phase_b_opening(self):
        """フェーズB: オープニング動画"""
        print("\n[フェーズ] フェーズB: オープニング動画")
        self.current_phase = "opening"

        if self.obs and self.opening_video:
            print(f"   動画パス: {self.opening_video}")

            # オープニングシーン作成
            print("   [処理] シーン作成中...")
            self.obs.create_scene(scene_name := "オープニング")
            await asyncio.sleep(1.0)

            # 動画ソース追加
            print("   [フェーズ] メディアソース追加中...")
            self.obs.add_media_source(scene_name, "オープニング動画", self.opening_video)
            await asyncio.sleep(2.0)

            # シーン切り替え
            print("   [切替] シーン切り替え中...")
            self.obs.switch_scene(scene_name)
            await asyncio.sleep(1.0)

            # 動画再生開始
            print("   [再生] 動画再生開始...")
            self.obs.play_media_source("オープニング動画")
            await asyncio.sleep(1.0)

            # 動画再生時間取得
            duration = self.obs.get_media_duration("オープニング動画")
            if duration:
                print(f"   [時間]  再生時間: {duration:.1f}秒")
                await asyncio.sleep(duration + 1.0)
            else:
                print("   [警告] 動画長さ取得失敗、5秒待機")
                await asyncio.sleep(5)

        print("[処理] フェーズB完了")
    
    async def phase_c_zundamon_interactive(self):
        """フェーズC: ずんだもん+めたんタイムライン実行"""
        print("[発話] フェーズC: ずんだもん+めたんタイムライン実行")
        self.current_phase = "zundamon_interactive"

        if self.obs:
            self.obs.switch_scene("ずんだもんシーン")

        # DB範囲データからタイムライン生成・実行
        if self.db_range_data:
            await self.execute_timeline_from_db()
        else:
            print("[警告] DB範囲データが未設定です")

        print("[処理] フェーズC完了")
    
    async def phase_d_ending(self):
        """フェーズD: エンディング動画"""
        print("\n[フェーズ] フェーズD: エンディング動画")
        self.current_phase = "ending"

        if self.obs and self.ending_video:
            print(f"   動画パス: {self.ending_video}")

            # エンディングシーン作成
            print("   [処理] シーン作成中...")
            self.obs.create_scene(scene_name := "エンディング")
            await asyncio.sleep(1.0)

            # 動画ソース追加
            print("   [フェーズ] メディアソース追加中...")
            self.obs.add_media_source(scene_name, "エンディング動画", self.ending_video)
            await asyncio.sleep(2.0)

            # シーン切り替え
            print("   [切替] シーン切り替え中...")
            self.obs.switch_scene(scene_name)
            await asyncio.sleep(1.0)

            # 動画再生開始
            print("   [再生] 動画再生開始...")
            self.obs.play_media_source("エンディング動画")
            await asyncio.sleep(1.0)

            # 動画再生時間取得
            duration = self.obs.get_media_duration("エンディング動画")
            if duration:
                print(f"   [時間]  再生時間: {duration:.1f}秒")
                await asyncio.sleep(duration + 1.0)
            else:
                print("   [警告] 動画長さ取得失敗、5秒待機")
                await asyncio.sleep(5)

        print("[処理] フェーズD完了")
    
    async def handle_comments(self):
        """コメント処理"""
        print("[処理] コメント処理開始")
        
        # コメント受信システムの初期化
        # TODO: 実際のコメント受信APIとの連携
        
        while not self.termination_event.is_set():
            # 模擬コメント処理
            await asyncio.sleep(5)
            if self.debug:
                print("[処理] コメント処理中...")
    
    async def execute_timeline_from_db(self):
        """DB範囲データからタイムライン生成・実行"""
        print("[処理] タイムライン生成・実行開始")

        try:
            from server.timeline_generator import TimelineGenerator
            from server.timeline_executor import TimelineExecutor
            from server.main import broadcast_to_browser

            # DB範囲データ取得
            user_id = self.db_range_data.get("user_id")
            broadcast_ids = self.db_range_data.get("broadcast_ids", [])

            if not user_id or not broadcast_ids:
                print("[処理] DB範囲データ不正: user_idまたはbroadcast_idsが未設定")
                return

            # タイムライン生成
            generator = TimelineGenerator()
            timeline_json = generator.generate_from_broadcasts(
                broadcast_ids=broadcast_ids,
                user_id=user_id,
                title=f"{self.username}さんのコメント読み上げ"
            )

            print(f"[処理] タイムライン生成完了: {len(timeline_json.get('timeline', []))}項目")

            # タイムラインデータをコンソール出力
            print(f"[処理] タイムライン内容:")
            for i, action in enumerate(timeline_json.get('timeline', [])[:5]):
                print(f"   {i+1}. {action.get('text', '')[:50]}")
            if len(timeline_json.get('timeline', [])) > 5:
                print(f"   ... 他 {len(timeline_json.get('timeline', [])) - 5} 項目")

            # JSONファイルに出力
            import json
            from pathlib import Path
            output_dir = Path("test/generated_timelines")
            output_dir.mkdir(parents=True, exist_ok=True)
            output_file = output_dir / f"timeline_{user_id}_{'-'.join(broadcast_ids)}.json"
            with open(output_file, 'w', encoding='utf-8') as f:
                json.dump(timeline_json, f, indent=2, ensure_ascii=False)
            print(f"[処理] タイムライン保存: {output_file}")

            # タイムライン実行（broadcast_to_browserをcallbackとして渡す）
            timeline_executor = TimelineExecutor(self.config, self.obs, broadcast_callback=broadcast_to_browser)
            await timeline_executor.execute_timeline_from_json(timeline_json)

            print("[処理] タイムライン実行完了")

        except Exception as e:
            print(f"[処理] タイムライン生成・実行エラー: {e}")
            import traceback
            traceback.print_exc()

    async def execute_timeline(self):
        """タイムライン実行（デフォルトプロジェクト）"""
        print("[処理] タイムライン実行開始")

        try:
            from server.timeline_executor import TimelineExecutor

            timeline_executor = TimelineExecutor(self.config, self.obs)

            # デフォルトプロジェクト読み込み
            project_name = self.config.get("automation", {}).get("auto_project", "default_project")
            await timeline_executor.load_project(project_name)

            # タイムライン実行
            result = await timeline_executor.execute_timeline()
            print(f"[処理] タイムライン完了: {result}")

        except Exception as e:
            print(f"[処理] タイムラインエラー: {e}")
    
    async def wait_for_termination(self):
        """終了トリガー待機"""
        # 終了条件の例
        termination_time = 1800  # 30分
        
        print(f"[タイマー] 終了トリガー待機: {termination_time}秒後に自動終了")
        
        await asyncio.sleep(termination_time)
        self.termination_event.set()
        print("[通知] 終了トリガー発火")
    
    def init_obs(self):
        """OBS初期化"""
        try:
            print("[処理] OBS初期化中...", end="", flush=True)
            from server.obs_controller import OBSController
            
            self.obs = OBSController(self.config)
            result = self.obs.ensure_obs_ready()
            
            print(" [OK]" if result else " [NG]")
            return result
        except Exception as e:
            print(" [NG]")
            return False
    
    def init_voicevox(self):
        """VOICEVOX初期化"""
        try:
            print("[音声] VOICEVOX初期化中...", end="", flush=True)
            from server.voicevox_client import VoicevoxClient
            
            voicevox = VoicevoxClient(self.config)
            
            import asyncio
            try:
                loop = asyncio.get_event_loop()
            except RuntimeError:
                loop = asyncio.new_event_loop()
                asyncio.set_event_loop(loop)
            
            result = loop.run_until_complete(voicevox.ensure_voicevox_ready())
            
            print(" [OK]" if result else " [NG]")
            return result
        except Exception as e:
            print(" [NG]")
            return False
    
    def init_zundamon_server(self):
        """ずんだもんサーバー初期化"""
        try:
            print("[処理] ずんだもんサーバー初期化中...", end="", flush=True)

            def run_server():
                from server.main import main_server, setup_logging
                setup_logging(self.config)

                import asyncio
                try:
                    loop = asyncio.get_event_loop()
                except RuntimeError:
                    loop = asyncio.new_event_loop()
                    asyncio.set_event_loop(loop)

                # イベントループを保存
                self.zundamon_server_loop = loop

                try:
                    loop.run_until_complete(main_server(self.config))
                except asyncio.CancelledError:
                    print("[処理] WebSocketサーバー停止")

            self.zundamon_server_thread = threading.Thread(target=run_server, daemon=False, name="ZundamonServer")
            self.zundamon_server_thread.start()

            time.sleep(3)
            print(" [OK]")
            return True

        except Exception as e:
            print(" [NG]")
            return False
    
    def init_niconico_broadcast(self):
        """ニコニコ生放送初期化"""
        try:
            print("[処理] ニコニコ生放送初期化中...", end="", flush=True)

            from selenium import webdriver
            from selenium.webdriver.chrome.options import Options
            from selenium.webdriver.common.by import By
            from selenium.webdriver.support.ui import WebDriverWait
            from selenium.webdriver.support import expected_conditions as EC

            niconico_config = self.config.get("niconico", {})
            debug_port = niconico_config.get('chrome_debug_port', 9223)

            # 既存のChromeデバッグセッションに接続を試行
            chrome_options = Options()
            chrome_options.add_experimental_option("debuggerAddress", f"127.0.0.1:{debug_port}")

            try:
                # 既存セッションに接続
                self.chrome_driver = webdriver.Chrome(options=chrome_options)
                print(f" [既存Chrome使用: ポート{debug_port}]", end="")
            except Exception:
                # 既存セッションがない場合は新規起動
                chrome_options = Options()
                chrome_options.add_argument(f"--remote-debugging-port={debug_port}")
                chrome_options.add_argument(f"--user-data-dir={niconico_config.get('user_data_dir', './chrome_profile_niconico')}")

                # プロファイル指定
                if niconico_config.get('profile_directory'):
                    chrome_options.add_argument(f"--profile-directory={niconico_config.get('profile_directory')}")

                # Chrome起動
                chrome_options.binary_location = niconico_config.get('chrome_exe_path', 'C:/Program Files/Google/Chrome/Application/chrome.exe')
                self.chrome_driver = webdriver.Chrome(options=chrome_options)
                print(f" [新規Chrome起動: ポート{debug_port}]", end="")

            # ニコニコ生放送ページに移動
            broadcast_url = niconico_config.get('broadcast_url', 'https://live.nicovideo.jp/create')
            self.chrome_driver.get(broadcast_url)

            # タイトル設定
            title_preset = niconico_config.get('title_preset', '【ずんだもん配信】')
            broadcast_title = f"{self.username}{title_preset}"

            # タイトル入力欄を待機して入力
            wait = WebDriverWait(self.chrome_driver, 10)
            title_input = wait.until(EC.presence_of_element_located((By.CSS_SELECTOR, "input[name='title'], input[placeholder*='タイトル']")))
            title_input.clear()
            title_input.send_keys(broadcast_title)

            print(f" [OK] (タイトル: {broadcast_title})")
            return True

        except Exception as e:
            print(f" [NG] ({e})")
            return False

    def start_niconico_broadcast(self):
        """ニコニコ生放送開始ボタンをクリック"""
        try:
            print("[処理] ニコニコ生放送開始中...", end="", flush=True)

            from selenium.webdriver.common.by import By
            from selenium.webdriver.support.ui import WebDriverWait
            from selenium.webdriver.support import expected_conditions as EC

            wait = WebDriverWait(self.chrome_driver, 10)

            # 放送開始ボタンを探してクリック
            start_button = wait.until(EC.element_to_be_clickable((By.CSS_SELECTOR, "button[type='submit'], button:contains('放送開始'), button:contains('配信開始')")))
            start_button.click()

            print(" [OK]")
            return True

        except Exception as e:
            print(f" [NG] ({e})")
            return False
    
    async def cleanup_systems(self):
        """システム終了処理"""
        print("[処理] システム終了処理中...")

        # WebSocketサーバー停止
        if self.zundamon_server_loop:
            print("[処理] WebSocketサーバー停止中...")
            try:
                # イベントループの全タスクをキャンセル
                for task in asyncio.all_tasks(self.zundamon_server_loop):
                    task.cancel()

                # ループを停止
                self.zundamon_server_loop.call_soon_threadsafe(self.zundamon_server_loop.stop)
            except Exception as e:
                print(f"[警告] サーバー停止エラー: {e}")

        # スレッド終了待機
        if self.zundamon_server_thread and self.zundamon_server_thread.is_alive():
            print("[待機] サーバースレッド終了待機中...")
            self.zundamon_server_thread.join(timeout=3)

        # Chrome終了
        if hasattr(self, 'chrome_driver'):
            try:
                print("[ブラウザ] Chrome終了中...")
                self.chrome_driver.quit()
            except Exception as e:
                print(f"[警告] Chrome終了エラー: {e}")

        # OBS切断
        if self.obs:
            self.obs.disconnect()

        print("[処理] システム終了完了")

def run_broadcast_mode(config, username=None, prep_video=None, opening_video=None, db_range_json=None, ending_video=None, debug=False):
    """配信モード実行"""
    system = IntegratedBroadcastSystem(config, username, prep_video, opening_video, db_range_json, ending_video, debug)

    try:
        asyncio.run(system.run_full_broadcast())
    except KeyboardInterrupt:
        print("\n[停止] Ctrl+C検出 - システム停止中...")
        # cleanup_systemsを同期的に実行
        try:
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            loop.run_until_complete(system.cleanup_systems())
            loop.close()
        except Exception as e:
            print(f"[警告] 終了処理エラー: {e}")
        print("[処理] システム停止完了")

def run_auto_mode(config, debug=False):
    """自動モード - 並列起動"""
    automation = config.get("automation", {})
    components = automation.get("auto_start_components", ["server"])
    stabilization_wait = automation.get("stabilization_wait", 30)
    
    print("[自動] 自動実行モード開始")
    print(f"   起動コンポーネント: {', '.join(components)}")
    
    if debug:
        config["logging"]["level"] = "DEBUG"
    else:
        config["logging"]["level"] = "WARNING"
    
    # 並列起動タスク
    startup_tasks = []
    
    print("\n[起動] システム並列起動中...")
    
    with ThreadPoolExecutor(max_workers=6) as executor:
        if automation.get("auto_obs_connect", True):
            startup_tasks.append(executor.submit(check_obs_startup, config))
        
        if automation.get("auto_voicevox_check", True):
            startup_tasks.append(executor.submit(check_voicevox_startup, config))
        
        if "server" in components:
            startup_tasks.append(executor.submit(start_zundamon_server, config))
        
        if "gui" in components:
            startup_tasks.append(executor.submit(start_gui_system, config))
        
        print(f"[待機] 起動完了待機中...")
        
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
                    print(f"[処理] タスクエラー: {e}")
        
        success_count = len(startup_tasks) - failed_count
        print(f"[統計] 起動完了: [OK]{success_count} [NG]{failed_count}")
    
    if failed_count > 0:
        print("[警告] 一部システムの起動に失敗しましたが、処理を続行します")
    
    # 安定化待機
    print(f"[タイマー] 安定化待機中", end="", flush=True)
    for i in range(stabilization_wait):
        print(".", end="", flush=True)
        time.sleep(1)
    print(" 完了!")
    
    print("[処理] 全システム準備完了！")
    
    try:
        print("[完了] 起動完了 - Ctrl+C で停止")
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        print("\n[停止] システム停止中...")

def run_server_only(config, debug=False):
    """サーバーのみ起動"""
    from server.main import main_server, setup_logging
    
    if debug:
        config["logging"]["level"] = "DEBUG"
    
    setup_logging(config)
    print("[処理] ずんだもんサーバー起動")
    
    try:
        asyncio.run(main_server(config))
    except KeyboardInterrupt:
        print("\n[停止] サーバー停止")

def run_manual_mode(config):
    """手動モード"""
    print("[手動] 手動実行モード")
    print("\n利用可能なコマンド:")
    print("  python run.py broadcast --title 'タイトル'  # 配信モード")
    print("  python run.py auto                        # 自動モード")
    print("  python run.py server                      # サーバーのみ")


def check_obs_startup(config):
    """OBS起動確認"""
    try:
        print("[処理] OBS確認中...", end="", flush=True)
        from server.obs_controller import OBSController
        
        obs = OBSController(config)
        result = obs.ensure_obs_ready()
        
        print(" [OK]" if result else " [NG]")
        return result
    except Exception as e:
        print(" [NG]")
        return False

def check_voicevox_startup(config):
    """VOICEVOX接続確認"""
    try:
        print("[音声] VOICEVOX確認中...", end="", flush=True)
        from server.voicevox_client import VoicevoxClient
        
        voicevox = VoicevoxClient(config)
        
        import asyncio
        try:
            loop = asyncio.get_event_loop()
        except RuntimeError:
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
        
        result = loop.run_until_complete(voicevox.ensure_voicevox_ready())
        
        print(" [OK]" if result else " [NG]")
        return result
    except Exception as e:
        print(" [NG]")
        return False

def start_zundamon_server(config):
    """ずんだもんサーバー起動"""
    try:
        print("[処理] サーバー起動中...", end="", flush=True)
        
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
        print(" [OK]")
        return True
        
    except Exception as e:
        print(" [NG]")
        return False

def start_gui_system(config):
    """GUI起動"""
    try:
        print("[処理] ️ GUI起動中...", end="", flush=True)
        
        def run_gui():
            from gui.main_window import start_gui
            start_gui(config)
        
        gui_thread = threading.Thread(target=run_gui, daemon=True, name="ZundamonGUI")
        gui_thread.start()
        
        time.sleep(2)
        print(" [OK]")
        return True
    except Exception as e:
        print(" [NG]")
        return False




if __name__ == "__main__":
    main()