import asyncio
import websockets
import json
import threading
import queue
import logging
import sys
import time
from pathlib import Path
from http.server import HTTPServer, SimpleHTTPRequestHandler

# パッケージパスを追加
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from server.config_manager import ConfigManager
from server.voicevox_client import VoicevoxClient
from server.audio_analyzer import AudioAnalyzer
from server.obs_controller import OBSController
from server.plugin_manager import PluginManager

# グローバル変数を最初に初期化
browser_clients = set()
obs_control_clients = set()
voicevox = None
audio_analyzer = None
obs_controller = None
plugin_manager = None
volume_queue = queue.Queue()

# 非同期読み上げシステム用グローバル変数
comment_queue = []  # コメントキュー（文字列）
prepared_audio = None  # 準備済み音声ファイルパス
current_speech_task = None  # 現在の音声再生タスク
is_speaking = False  # 音声再生中フラグ
speech_lock = asyncio.Lock()  # 音声制御ロック

# 割り込み可能音声システム用グローバル変数
current_audio_player = None  # 現在の音声プレイヤーインスタンス
current_audio_thread = None  # 現在の音声再生スレッド
timeline_position = 0  # タイムライン停止位置記録

async def browser_handler(websocket):
    """ブラウザ用WebSocketハンドラー（admin.html、index.html、外部制御スクリプト用）"""
    global browser_clients
    browser_clients.add(websocket)
    logging.info(f"[WebSocket] ブラウザ接続: {len(browser_clients)}台")
    
    try:
        async for message in websocket:
            try:
                data = json.loads(message)
                logging.debug(f"[ブラウザ] 受信: {data}")
                
                # ブラウザからの直接制御
                if data.get("action") == "speak_text":
                    await handle_speech_request(data.get("text", ""), character=data.get("character", "zundamon"))
                elif data.get("action") == "speech_start":
                    # テスト用: speech_startを直接受信した場合も処理
                    await handle_speech_request(data.get("text", ""), character=data.get("character", "zundamon"))
                elif data.get("action") in ["change_expression", "change_pose", "change_outfit"]:
                    await broadcast_to_browser(data)
                # 外部制御スクリプトからのコマンド
                elif data.get("action") == "speak":
                    await handle_speech_request(data.get("text", ""), character=data.get("character", "zundamon"))
                elif data.get("action") in ["change_expression", "change_pose", "change_outfit", "blink"]:
                    await broadcast_to_browser(data)
                else:
                    await broadcast_to_browser(data)
                    
            except json.JSONDecodeError as e:
                logging.error(f"[ブラウザ] JSONデコードエラー: {e}")
            except Exception as e:
                logging.error(f"[ブラウザ] メッセージ処理エラー: {e}")
                
    except websockets.exceptions.ConnectionClosed:
        logging.info("[WebSocket] ブラウザ切断")
    finally:
        browser_clients.discard(websocket)

async def obs_control_handler(websocket):
    """OBS制御用WebSocketハンドラー（統合タイムラインシステム用）"""
    global obs_control_clients
    obs_control_clients.add(websocket)
    logging.info(f"[WebSocket] OBS制御システム接続: {len(obs_control_clients)}台")
    
    try:
        async for message in websocket:
            try:
                logging.info(f"[OBS制御] 生メッセージ受信: {message}")
                data = json.loads(message)
                logging.info(f"[OBS制御] 受信: {data}")
                
                await process_obs_control_command(data)
                
            except json.JSONDecodeError as e:
                logging.error(f"[OBS制御] JSONデコードエラー: {e}")
            except Exception as e:
                logging.error(f"[OBS制御] メッセージ処理エラー: {e}")
                
    except websockets.exceptions.ConnectionClosed:
        logging.info("[WebSocket] OBS制御システム切断")
    finally:
        obs_control_clients.discard(websocket)

async def broadcast_to_browser(data: dict):
    """ブラウザクライアントに一斉送信"""
    global browser_clients
    if browser_clients:
        message = json.dumps(data, ensure_ascii=False)
        dead_clients = set()
        
        for client in browser_clients:
            try:
                await client.send(message)
            except websockets.exceptions.ConnectionClosed:
                dead_clients.add(client)
            except Exception as e:
                logging.error(f"[ブラウザ送信エラー] {e}")
                dead_clients.add(client)
        
        # 切断クライアント削除
        browser_clients -= dead_clients

async def broadcast_to_obs_control(data: dict):
    """OBS制御クライアントに一斉送信"""
    global obs_control_clients
    if obs_control_clients:
        message = json.dumps(data, ensure_ascii=False)
        dead_clients = set()
        
        for client in obs_control_clients:
            try:
                await client.send(message)
            except websockets.exceptions.ConnectionClosed:
                dead_clients.add(client)
            except Exception as e:
                logging.error(f"[OBS制御送信エラー] {e}")
                dead_clients.add(client)
        
        # 切断クライアント削除
        obs_control_clients -= dead_clients

async def process_obs_control_command(data):
    """OBS制御コマンド処理"""
    action = data.get("action")
    
    if action == "scene_change":
        # OBSシーン変更コマンド
        scene_name = data.get("scene_name")
        logging.info(f"[OBS] シーン切り替え要求: {scene_name}")
        if obs_controller:
            await obs_controller.change_scene(scene_name)
    elif action == "start_zundamon_session":
        # ずんだもんセッション開始
        logging.info("[OBS] ずんだもんセッション開始")
        await broadcast_to_browser({"action": "session_start"})
    elif action == "end_zundamon_session":
        # ずんだもんセッション終了
        logging.info("[OBS] ずんだもんセッション終了")
        await broadcast_to_browser({"action": "session_end"})
    elif action == "zundamon_control":
        # ずんだもん制御コマンドをブラウザに転送
        control_data = data.get("control_data", {})
        await broadcast_to_browser(control_data)
    else:
        logging.warning(f"[OBS制御] 未知のコマンド: {action}")

async def handle_speech_request(text: str, is_comment=False, use_prepared=False, character="zundamon"):
    """音声合成要求処理（キャラクター対応）"""
    global voicevox, audio_analyzer, plugin_manager, volume_queue
    global current_speech_task, is_speaking, speech_lock, prepared_audio

    async with speech_lock:
        logging.info(f"[音声合成] テキスト: {text}, キャラクター: {character}, コメント: {is_comment}")

        # コメントの場合、既存の音声を停止
        if is_comment and is_speaking and current_speech_task:
            logging.info("[音声制御] コメント割り込み - 既存音声停止")
            current_speech_task.cancel()
            await broadcast_to_browser({"action": "speech_interrupted"})

        try:
            if plugin_manager:
                await plugin_manager.execute_hook('on_speech_start', text)

            # キャラクター別の音声ID設定
            if character == "metan":
                voice_id = 2  # 四国めたん
            else:
                voice_id = 3  # ずんだもん（デフォルト）

            # 準備済み音声を使用するか、新規生成するか
            if use_prepared and prepared_audio:
                audio_file = prepared_audio
                logging.info(f"[音声合成] 準備済み音声使用: {audio_file}")
            else:
                audio_file = await voicevox.synthesize_speech(text, speaker_id=voice_id)
                logging.info(f"[音声合成] 新規生成: {audio_file} (キャラ: {character})")

            if audio_file:
                is_speaking = True
                await broadcast_to_browser({
                    "action": "speech_start",
                    "text": text,
                    "character": character
                })

                if audio_analyzer:
                    current_speech_task = asyncio.create_task(
                        play_audio_async(audio_file, text, is_comment, character)
                    )
                    await current_speech_task
            else:
                logging.error("音声合成失敗")
                await broadcast_to_browser({
                    "action": "speech_error",
                    "text": text
                })

        except asyncio.CancelledError:
            logging.info("[音声制御] 音声タスクがキャンセルされました")
            is_speaking = False
        except Exception as e:
            logging.error(f"音声合成処理エラー: {e}")
            await broadcast_to_browser({
                "action": "speech_error",
                "error": str(e)
            })
            is_speaking = False

async def play_audio_async(audio_file: str, text: str, is_comment: bool, character: str):
    """割り込み可能な非同期音声再生（キャラクター対応）"""
    global audio_analyzer, volume_queue, is_speaking
    global current_audio_player, current_audio_thread

    try:
        # キャラクター情報を含むvolume_callbackを作成
        def volume_callback(level):
            volume_queue.put({"character": character, "level": level})

        # AudioPlayerを直接作成（キャラクター別コールバック）
        from server.audio_analyzer import AudioPlayer
        player = AudioPlayer(volume_callback=volume_callback)
        current_audio_player = player

        logging.info(f"[音声再生] 開始: {text[:30]}... (キャラ: {character})")

        # play_asyncで非ブロッキング再生開始
        current_audio_thread = player.play_async(audio_file)

        # 再生完了まで待機（割り込み可能）
        while current_audio_thread and current_audio_thread.is_alive():
            if current_audio_player and not current_audio_player.is_playing:
                break
            await asyncio.sleep(0.1)

        # 音声終了処理
        volume_queue.put({"character": character, "level": "END"})
        logging.info(f"[音声再生] 完了: {text[:20]}... (キャラ: {character})")

        # コメント応答完了時に次のキューを処理
        if is_comment:
            await process_next_comment_queue()

    except Exception as e:
        logging.error(f"[音声再生] エラー: {e}")
        volume_queue.put({"character": character, "level": "END"})
    finally:
        current_audio_player = None
        current_audio_thread = None
        is_speaking = False

async def handle_comment_interrupt(data):
    """コメント割り込み処理（新実装）"""
    global plugin_manager, comment_queue, prepared_audio, is_speaking
    global current_audio_player, timeline_position

    logging.info(f"[コメント] 割り込み: {data}")

    try:
        if plugin_manager:
            await plugin_manager.execute_hook('on_comment_received', data)

        username = data.get("username", "名無しさん")
        comment_text = data.get("text", "")

        # タイムライン読み上げ中の場合は即座に停止
        if is_speaking and current_audio_player:
            logging.info("[コメント] タイムライン読み上げを停止します")

            # タイムライン位置を記録（現在は簡易実装）
            timeline_position = time.time()

            # 音声を即座に停止
            current_audio_player.stop()
            logging.info(f"[コメント] 音声停止完了 - 位置記録: {timeline_position}")

        # 四国めたんに「質問がきたわよ」と言わせる
        metan_text = "質問がきたわよ"
        await handle_speech_request(metan_text, is_comment=False, character="metan")

        # 少し間を置いてからずんだもんの応答
        await asyncio.sleep(0.5)

        # ずんだもんの応答
        zundamon_response = f"{username}さん、コメントありがとうなのだ！"
        await handle_speech_request(zundamon_response, is_comment=True, character="zundamon")

        if plugin_manager:
            await plugin_manager.execute_hook('on_comment_response', zundamon_response)

    except Exception as e:
        logging.error(f"コメント処理エラー: {e}")

async def prepare_next_audio():
    """次の音声を事前準備"""
    global comment_queue, prepared_audio, voicevox

    if comment_queue and not prepared_audio:
        next_text = comment_queue[0]
        logging.info(f"[音声準備] 開始: {next_text[:20]}...")

        try:
            prepared_audio = await voicevox.synthesize_speech(next_text)
            logging.info(f"[音声準備] 完了: {prepared_audio}")
        except Exception as e:
            logging.error(f"[音声準備] エラー: {e}")

async def process_next_comment_queue():
    """次のコメントキューを処理"""
    global comment_queue, prepared_audio, speech_lock

    async with speech_lock:
        if comment_queue:
            # 完了したコメントをキューから削除
            completed_text = comment_queue.pop(0)
            logging.info(f"[コメントキュー] 完了: {completed_text[:20]}...")

            # 準備済み音声をクリア
            prepared_audio = None

            # 次のコメントがある場合
            if comment_queue:
                next_text = comment_queue[0]

                # 準備済み音声があるかチェック
                has_prepared = prepared_audio is not None

                if has_prepared:
                    logging.info(f"[コメントキュー] 準備済み音声で即座再生: {next_text[:20]}...")
                    await handle_speech_request(next_text, is_comment=True, use_prepared=True)
                else:
                    # 準備済み音声がない場合は新規生成
                    logging.info(f"[コメントキュー] 新規生成で再生: {next_text[:20]}...")
                    await handle_speech_request(next_text, is_comment=True, use_prepared=False)

                # さらに次があれば準備開始
                if len(comment_queue) > 1:
                    await prepare_next_audio()

async def volume_queue_processor():
    """音量キュー処理（キャラクター対応）"""
    global volume_queue, plugin_manager

    while True:
        try:
            volume_data = volume_queue.get_nowait()

            # 辞書形式のキャラクター付きデータ
            if isinstance(volume_data, dict):
                character = volume_data.get("character", "zundamon")
                level = volume_data.get("level")

                if level == "END":
                    await broadcast_to_browser({
                        "action": "speech_end",
                        "character": character
                    })
                    if plugin_manager:
                        await plugin_manager.execute_hook('on_speech_end')
                elif isinstance(level, (int, float)):
                    await broadcast_to_browser({
                        "action": "volume_level",
                        "level": level,
                        "character": character
                    })
            # 旧形式との互換性（キャラクター指定なし）
            elif volume_data == "END":
                await broadcast_to_browser({"action": "speech_end"})
                if plugin_manager:
                    await plugin_manager.execute_hook('on_speech_end')
            elif isinstance(volume_data, (int, float)):
                await broadcast_to_browser({
                    "action": "volume_level",
                    "level": volume_data
                })
        except queue.Empty:
            await asyncio.sleep(0.01)
        except Exception as e:
            logging.error(f"音量キュー処理エラー: {e}")

async def idle_animation_loop():
    """アイドルアニメーション"""
    while True:
        await asyncio.sleep(5)
        await broadcast_to_browser({"action": "blink"})

class CustomHTTPRequestHandler(SimpleHTTPRequestHandler):
    def __init__(self, *args, **kwargs):
        project_root = Path(__file__).parent.parent
        super().__init__(*args, directory=str(project_root), **kwargs)
    
    def log_message(self, format, *args):
        logging.info(f"[HTTP] {format % args}")

def start_http_server(port):
    """HTTPサーバー起動"""
    server = HTTPServer(('localhost', port), CustomHTTPRequestHandler)
    logging.info(f"✅ HTTPサーバー起動: http://localhost:{port}")
    server.serve_forever()

async def start_websocket_servers(config):
    """WebSocketサーバー起動"""
    browser_port = config["servers"]["websocket_browser_port"]
    browser_server = await websockets.serve(
        browser_handler, 
        "localhost", 
        browser_port
    )
    logging.info(f"✅ ブラウザ用WebSocket: ws://localhost:{browser_port}")
    
    obs_control_port = config["servers"]["websocket_control_port"]
    obs_control_server = await websockets.serve(
        obs_control_handler, 
        "localhost", 
        obs_control_port
    )
    logging.info(f"✅ OBS制御用WebSocket: ws://localhost:{obs_control_port}")
    
    return browser_server, obs_control_server

async def initialize_system(config):
    """システム初期化"""
    global voicevox, audio_analyzer, obs_controller, plugin_manager
    
    voicevox = VoicevoxClient(config)
    if await voicevox.check_connection():
        logging.info("✅ VOICEVOX接続確認")
    else:
        logging.warning("⚠️ VOICEVOX接続失敗")
    
    audio_analyzer = AudioAnalyzer(config)
    logging.info("✅ 音声分析システム初期化")
    
    obs_controller = OBSController(config)
    logging.info("✅ OBSコントローラー初期化")
    
    plugin_manager = PluginManager(config)
    plugin_manager.load_plugins()
    logging.info("✅ プラグインシステム初期化")
    
    if plugin_manager:
        await plugin_manager.execute_hook('on_system_start')

async def main_server(config):
    """メインサーバー起動"""
    await initialize_system(config)
    
    http_port = config["servers"]["http_port"]
    http_thread = threading.Thread(
        target=start_http_server, 
        args=(http_port,), 
        daemon=True
    )
    http_thread.start()
    
    servers = await start_websocket_servers(config)
    
    logging.info("✅ すべてのサーバーが起動完了")
    
    await asyncio.gather(
        volume_queue_processor(),
        idle_animation_loop(),
        servers[0].wait_closed(),
        servers[1].wait_closed()
    )

def setup_logging(config):
    """ログ設定"""
    log_level = config.get("logging", {}).get("level", "INFO")
    log_file = config.get("logging", {}).get("file")
    
    if log_file:
        Path(log_file).parent.mkdir(parents=True, exist_ok=True)
    
    handlers = [
        logging.StreamHandler(sys.stdout)
    ]
    
    if log_file:
        handlers.append(logging.FileHandler(log_file, encoding='utf-8'))
    
    logging.basicConfig(
        level=getattr(logging, log_level),
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        handlers=handlers,
        force=True
    )
    
    # 外部ライブラリのログレベルを制限
    logging.getLogger('websockets').setLevel(logging.WARNING)
    logging.getLogger('obswebsocket').setLevel(logging.WARNING)
    logging.getLogger('aiohttp').setLevel(logging.WARNING)
    logging.getLogger('asyncio').setLevel(logging.WARNING)
    
    # HTTPサーバーのアクセスログを制限
    if log_level != "DEBUG":
        logging.getLogger('server.main').setLevel(logging.WARNING)  # HTTPアクセスログを抑制
    
    if hasattr(sys.stdout, 'reconfigure'):
        try:
            sys.stdout.reconfigure(encoding='utf-8')
            sys.stderr.reconfigure(encoding='utf-8')
        except:
            pass

if __name__ == "__main__":
    config_manager = ConfigManager()
    config = config_manager.load_config()
    
    setup_logging(config)
    
    logging.info("=== ずんだもんWebSocketサーバー起動 ===")
    
    try:
        asyncio.run(main_server(config))
    except KeyboardInterrupt:
        logging.info("サーバー停止")
    except Exception as e:
        logging.error(f"サーバーエラー: {e}")