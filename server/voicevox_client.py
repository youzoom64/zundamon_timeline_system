import aiohttp
import asyncio
import hashlib
from pathlib import Path
import logging

class VoicevoxClient:
    def __init__(self, config):
        self.config = config
        self.host = config["servers"]["voicevox_host"]
        self.port = config["servers"]["voicevox_port"]
        self.base_url = f"http://{self.host}:{self.port}"
        self.audio_dir = Path(config["directories"]["audio_temp_dir"])
        self.audio_dir.mkdir(exist_ok=True)
        self.logger = logging.getLogger(__name__)
    
    async def check_connection(self):
        """VOICEVOX接続確認"""
        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(f"{self.base_url}/version", timeout=5) as response:
                    if response.status == 200:
                        version_info = await response.json()
                        self.logger.info(f"VOICEVOX接続確認: {version_info}")
                        return True
                    else:
                        self.logger.warning(f"VOICEVOX応答異常: {response.status}")
                        return False
        except Exception as e:
            self.logger.error(f"VOICEVOX接続失敗: {e}")
            return False
    
    async def get_speakers(self):
        """話者一覧取得"""
        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(f"{self.base_url}/speakers") as response:
                    if response.status == 200:
                        speakers = await response.json()
                        return speakers
                    else:
                        self.logger.error(f"話者一覧取得失敗: {response.status}")
                        return []
        except Exception as e:
            self.logger.error(f"話者一覧取得エラー: {e}")
            return []
    
    async def synthesize_speech(self, text: str, speaker_id: int = None, speed: float = 1.0, pitch: float = 0.0, intonation: float = 1.0):
        """音声合成"""
        if speaker_id is None:
            speaker_id = self.config["characters"]["zundamon"]["voice_id"]
        
        try:
            # 音声クエリ生成
            query_params = {
                "text": text,
                "speaker": speaker_id
            }
            
            async with aiohttp.ClientSession() as session:
                # 音声クエリ取得
                async with session.post(f"{self.base_url}/audio_query", params=query_params) as response:
                    if response.status != 200:
                        self.logger.error(f"VOICEVOX クエリエラー: {response.status}")
                        return None
                    query_data = await response.json()
                
                # パラメータ調整
                query_data["speedScale"] = speed
                query_data["pitchScale"] = pitch
                query_data["intonationScale"] = intonation
                
                # 音声合成
                headers = {"Content-Type": "application/json"}
                synthesis_params = {"speaker": speaker_id}
                
                async with session.post(
                    f"{self.base_url}/synthesis",
                    params=synthesis_params,
                    json=query_data,
                    headers=headers
                ) as response:
                    if response.status != 200:
                        self.logger.error(f"VOICEVOX 合成エラー: {response.status}")
                        return None
                    
                    # ファイル名生成（テキストのハッシュ値を使用）
                    text_hash = hashlib.md5(text.encode()).hexdigest()[:8]
                    audio_filename = f"speech_{speaker_id}_{text_hash}.wav"
                    audio_path = self.audio_dir / audio_filename
                    
                    # 音声ファイル保存
                    with open(audio_path, "wb") as f:
                        f.write(await response.read())
                    
                    self.logger.info(f"音声ファイル生成: {audio_path}")
                    return str(audio_path)
        
        except Exception as e:
            self.logger.error(f"VOICEVOX エラー: {e}")
            return None
    
    async def synthesize_speech_stream(self, text: str, speaker_id: int = None):
        """ストリーミング音声合成（未実装）"""
        # TODO: リアルタイム音声合成実装
        pass
    
    def cleanup_old_files(self, max_age_hours: int = 24):
        """古い音声ファイル削除"""
        import time
        
        try:
            current_time = time.time()
            max_age_seconds = max_age_hours * 3600
            
            for file_path in self.audio_dir.glob("*.wav"):
                if current_time - file_path.stat().st_mtime > max_age_seconds:
                    file_path.unlink()
                    self.logger.debug(f"古い音声ファイル削除: {file_path}")
        except Exception as e:
            self.logger.error(f"ファイル削除エラー: {e}")