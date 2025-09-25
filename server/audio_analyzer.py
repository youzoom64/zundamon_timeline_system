import asyncio
import numpy as np
import threading
import queue
import logging
from pathlib import Path

try:
    import soundfile as sf
    import pyaudio
    AUDIO_AVAILABLE = True
except ImportError:
    AUDIO_AVAILABLE = False

class AudioPlayer:
    def __init__(self, volume_callback=None):
        self.volume_callback = volume_callback
        self.is_playing = False
        self.logger = logging.getLogger(__name__)
        
        if not AUDIO_AVAILABLE:
            self.logger.warning("音声ライブラリが見つかりません。音声再生は無効です。")
    
    def play_with_analysis(self, wav_file_path):
        """音声ファイルを再生しながら音量レベルを分析"""
        if not AUDIO_AVAILABLE:
            self.logger.info(f"[模擬] 音声再生: {wav_file_path}")
            # 模擬的な音量レベル送信（別スレッドで）
            self._simulate_audio_playback()
            return
        
        # 実際の音声再生処理
        wav_path = Path(wav_file_path)
        if not wav_path.exists():
            self.logger.error(f"音声ファイルが見つかりません: {wav_file_path}")
            return
        
        try:
            # 音声ファイル読み込み
            data, samplerate = sf.read(wav_file_path)
            
            # モノラルに変換
            if len(data.shape) > 1:
                data = np.mean(data, axis=1)
            
            p = pyaudio.PyAudio()
            
            # チャンクサイズ（音量分析の間隔）
            chunk_size = int(samplerate * 0.1)  # 0.1秒間隔
            
            stream = p.open(
                format=pyaudio.paFloat32,
                channels=1,
                rate=samplerate,
                output=True
            )
            
            self.is_playing = True
            self.logger.info(f"音声再生開始: {wav_file_path}")
            
            # チャンクごとに再生と音量分析
            for i in range(0, len(data), chunk_size):
                if not self.is_playing:
                    break
                
                chunk = data[i:i+chunk_size]
                
                # 音量レベル計算（RMS）
                if len(chunk) > 0:
                    volume_level = np.sqrt(np.mean(chunk**2))
                    # 0-1の範囲に正規化
                    normalized_volume = min(volume_level * 3, 1.0)
                    
                    # コールバックで音量レベルを送信
                    if self.volume_callback:
                        self.volume_callback(normalized_volume)
                
                # 音声出力
                if len(chunk) > 0:
                    stream.write(chunk.astype(np.float32).tobytes())
            
            # 再生終了
            self.is_playing = False
            if self.volume_callback:
                self.volume_callback(0.0)  # 音量0で終了
            
            stream.stop_stream()
            stream.close()
            p.terminate()
            
            self.logger.info(f"音声再生終了: {wav_file_path}")
            
        except Exception as e:
            self.logger.error(f"音声再生エラー: {e}")
            self.is_playing = False
            if self.volume_callback:
                self.volume_callback(0.0)
    
    def _simulate_audio_playback(self):
        """音声再生の模擬実行"""
        def simulate():
            if self.volume_callback:
                # 3秒間の模擬音量レベル送信
                import time
                for i in range(30):  # 0.1秒×30回 = 3秒
                    volume = 0.3 + 0.2 * (i % 10) / 10  # 0.3-0.5の範囲で変動
                    self.volume_callback(volume)
                    time.sleep(0.1)
                self.volume_callback(0.0)  # 終了
        
        # 別スレッドで実行
        thread = threading.Thread(target=simulate, daemon=True)
        thread.start()
    
    def stop(self):
        """再生停止"""
        self.is_playing = False
        self.logger.info("音声再生停止")
    
    def play_async(self, wav_file_path):
        """非同期音声再生"""
        thread = threading.Thread(
            target=self.play_with_analysis,
            args=(wav_file_path,),
            daemon=True
        )
        thread.start()
        return thread

class AudioAnalyzer:
    def __init__(self, config):
        self.config = config
        self.volume_queue = queue.Queue()
        self.logger = logging.getLogger(__name__)
    
    def volume_callback_sync(self, volume_level):
        """スレッドセーフな音量コールバック"""
        try:
            self.volume_queue.put_nowait(volume_level)
        except queue.Full:
            pass  # キューが満杯の場合は無視
    
    async def process_volume_queue(self, broadcast_callback):
        """音量キューを処理してブラウザに送信"""
        while True:
            try:
                volume_level = self.volume_queue.get_nowait()
                if volume_level == "END":
                    await broadcast_callback({"action": "speech_end"})
                elif isinstance(volume_level, (int, float)):
                    await broadcast_callback({
                        "action": "volume_level", 
                        "level": volume_level
                    })
            except queue.Empty:
                await asyncio.sleep(0.01)
            except Exception as e:
                self.logger.error(f"音量キュー処理エラー: {e}")
    
    def create_player(self):
        """音声プレイヤー作成"""
        return AudioPlayer(self.volume_callback_sync)