import asyncio
import websockets
import json
import threading
import queue
import logging
import sys
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
                    await handle_speech_request(data.get("text", ""))
                elif data.get("action") in ["change_expression", "change_pose", "change_outfit"]:
                    await broadcast_to_browser(data)
                # 外部制御スクリプトからのコマンド
                elif data.get("action") == "speak":
                    await handle_speech_request(data.get("text", ""))
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

async def handle_speech_request(text: str):
    """音声合成要求処理"""
    global voicevox, audio_analyzer, plugin_manager, volume_queue
    
    logging.info(f"[音声合成] テキスト: {text}")
    
    try:
        if plugin_manager:
            await plugin_manager.execute_hook('on_speech_start', text)
        
        audio_file = await voicevox.synthesize_speech(text)
        
        if audio_file:
            await broadcast_to_browser({
                "action": "speech_start",
                "text": text
            })
            
            if audio_analyzer:
                player = audio_analyzer.create_player()
                
                def play_audio():
                    try:
                        player.play_with_analysis(audio_file)
                        volume_queue.put("END")
                    except Exception as e:
                        logging.error(f"音声再生エラー: {e}")
                        volume_queue.put("END")
                
                audio_thread = threading.Thread(target=play_audio, daemon=True)
                audio_thread.start()
        else:
            logging.error("音声合成失敗")
            await broadcast_to_browser({
                "action": "speech_error",
                "text": text
            })
            
    except Exception as e:
        logging.error(f"音声合成処理エラー: {e}")
        await broadcast_to_browser({
            "action": "speech_error", 
            "error": str(e)
        })

async def handle_comment_interrupt(data):
    """コメント割り込み処理"""
    global plugin_manager
    
    logging.info(f"[コメント] 割り込み: {data}")
    
    try:
        if plugin_manager:
            await plugin_manager.execute_hook('on_comment_received', data)
        
        username = data.get("username", "名無しさん")
        comment_text = data.get("text", "")
        response = f"{username}さん、コメントありがとうございます！"
        
        await handle_speech_request(response)
        
        if plugin_manager:
            await plugin_manager.execute_hook('on_comment_response', response)
            
    except Exception as e:
        logging.error(f"コメント処理エラー: {e}")

async def volume_queue_processor():
    """音量キュー処理"""
    global volume_queue, plugin_manager
    
    while True:
        try:
            volume_level = volume_queue.get_nowait()
            if volume_level == "END":
                await broadcast_to_browser({"action": "speech_end"})
                if plugin_manager:
                    await plugin_manager.execute_hook('on_speech_end')
            elif isinstance(volume_level, (int, float)):
                await broadcast_to_browser({
                    "action": "volume_level", 
                    "level": volume_level
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