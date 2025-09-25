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

# ✅ グローバル変数を最初に初期化
browser_clients = set()
control_clients = set()
voicevox = None
audio_analyzer = None
obs_controller = None
plugin_manager = None
volume_queue = queue.Queue()

async def browser_handler(websocket, path):
    """ブラウザ用WebSocketハンドラー"""
    global browser_clients  # ✅ global宣言追加
    browser_clients.add(websocket)
    logging.info(f"[WebSocket] ブラウザ接続: {len(browser_clients)}台")
    
    try:
        async for message in websocket:
            try:
                data = json.loads(message)
                logging.debug(f"[ブラウザ] 受信: {data}")
                
                if data.get("action") == "speak_text":
                    await handle_speech_request(data.get("text", ""))
                elif data.get("action") == "change_expression":
                    await broadcast_to_browser(data)
                elif data.get("action") == "change_pose":
                    await broadcast_to_browser(data)
                elif data.get("action") == "change_outfit":
                    await broadcast_to_browser(data)
                    
            except json.JSONDecodeError as e:
                logging.error(f"[ブラウザ] JSONデコードエラー: {e}")
            except Exception as e:
                logging.error(f"[ブラウザ] メッセージ処理エラー: {e}")
                
    except websockets.exceptions.ConnectionClosed:
        logging.info("[WebSocket] ブラウザ切断")
    finally:
        browser_clients.discard(websocket)

async def control_handler(websocket, path):
    """外部制御用WebSocketハンドラー"""
    global control_clients  # ✅ global宣言追加
    control_clients.add(websocket)
    logging.info(f"[WebSocket] 制御クライアント接続: {len(control_clients)}台")
    
    try:
        async for message in websocket:
            try:
                data = json.loads(message)
                logging.debug(f"[制御] 受信: {data}")
                
                await process_control_command(data)
                
            except json.JSONDecodeError as e:
                logging.error(f"[制御] JSONデコードエラー: {e}")
            except Exception as e:
                logging.error(f"[制御] メッセージ処理エラー: {e}")
                
    except websockets.exceptions.ConnectionClosed:
        logging.info("[WebSocket] 制御クライアント切断")
    finally:
        control_clients.discard(websocket)

async def broadcast_to_browser(data: dict):
    """ブラウザクライアントに一斉送信"""
    global browser_clients  # ✅ global宣言追加
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

async def broadcast_to_control(data: dict):
    """制御クライアントに一斉送信"""
    global control_clients  # ✅ global宣言追加
    if control_clients:
        message = json.dumps(data, ensure_ascii=False)
        dead_clients = set()
        
        for client in control_clients:
            try:
                await client.send(message)
            except websockets.exceptions.ConnectionClosed:
                dead_clients.add(client)
            except Exception as e:
                logging.error(f"[制御送信エラー] {e}")
                dead_clients.add(client)
        
        # 切断クライアント削除
        control_clients -= dead_clients

# 以下、既存の関数をそのまま続ける...
async def process_control_command(data):
    """制御コマンド処理"""
    action = data.get("action")
    
    if action == "speak":
        await handle_speech_request(data.get("text", ""))
    elif action == "change_expression":
        await broadcast_to_browser(data)
    elif action == "change_pose":
        await broadcast_to_browser(data)
    elif action == "change_outfit":
        await broadcast_to_browser(data)
    elif action == "blink":
        await broadcast_to_browser(data)
    elif action == "comment_interrupt":
        await handle_comment_interrupt(data)
    else:
        await broadcast_to_browser(data)

async def handle_speech_request(text: str):
    """音声合成要求処理"""
    global voicevox, audio_analyzer, plugin_manager, volume_queue  # ✅ global宣言追加
    
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
    global plugin_manager  # ✅ global宣言追加
    
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

# 以下の関数も同様に global 宣言を追加して続ける...

async def volume_queue_processor():
    """音量キュー処理"""
    global volume_queue, plugin_manager  # ✅ global宣言追加
    
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
    
    control_port = config["servers"]["websocket_control_port"]
    control_server = await websockets.serve(
        control_handler, 
        "localhost", 
        control_port
    )
    logging.info(f"✅ 制御用WebSocket: ws://localhost:{control_port}")
    
    return browser_server, control_server

async def initialize_system(config):
    """システム初期化"""
    global voicevox, audio_analyzer, obs_controller, plugin_manager  # ✅ global宣言追加
    
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
    
    logging.basicConfig(
        level=getattr(logging, log_level),
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        handlers=[
            logging.StreamHandler(),
            logging.FileHandler(log_file) if log_file else logging.NullHandler()
        ]
    )

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