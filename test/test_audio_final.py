"""
最終音声停止テスト - 正しい実装
"""
import asyncio
import time
from pathlib import Path
import sys

# パッケージパスを追加
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from server.config_manager import ConfigManager
from server.audio_analyzer import AudioAnalyzer
from server.voicevox_client import VoicevoxClient

class FinalAudioTest:
    def __init__(self):
        self.config = ConfigManager().load_config()
        self.voicevox = VoicevoxClient(self.config)
        self.audio_analyzer = AudioAnalyzer(self.config)
        self.current_player = None
        self.audio_thread = None

    async def test_interruptible_audio(self):
        """割り込み可能音声テスト"""
        print("🎵 割り込み可能音声テスト開始")

        # 長いテキストで音声合成
        text = "これは非常に長いテストメッセージです。音声再生中に停止機能をテストします。" * 3
        audio_file = await self.voicevox.synthesize_speech(text)

        if not audio_file:
            print("❌ 音声合成失敗")
            return

        print(f"🎵 音声再生開始: {audio_file}")

        # 正しい非同期再生
        player = self.audio_analyzer.create_player()
        self.current_player = player

        # play_asyncで非ブロッキング再生開始
        self.audio_thread = player.play_async(audio_file)
        print(f"🔊 再生スレッド開始: {self.audio_thread}")

        # 3秒後に停止テスト
        print("⏰ 3秒後に停止テストを実行...")
        await asyncio.sleep(3)

        print(f"📊 停止前の状態: is_playing={player.is_playing}")

        if player.is_playing:
            print("🛑 音声停止実行")
            player.stop()

            # 停止確認
            await asyncio.sleep(0.5)
            print(f"📊 停止後の状態: is_playing={player.is_playing}")

            if not player.is_playing:
                print("✅ 音声停止成功！")
            else:
                print("❌ 音声停止失敗")
        else:
            print("⚠️ 音声が既に停止していました")

        # スレッド完了まで待機
        print("🔄 スレッド完了待機...")
        if self.audio_thread and self.audio_thread.is_alive():
            self.audio_thread.join(timeout=2)

        if self.audio_thread and self.audio_thread.is_alive():
            print("⚠️ スレッドがまだ生きています")
        else:
            print("✅ スレッド完了")

        print("🏁 テスト完了")

async def main():
    test = FinalAudioTest()

    # VOICEVOX接続確認
    if not await test.voicevox.check_connection():
        print("❌ VOICEVOX接続失敗")
        return

    print("✅ VOICEVOX接続成功")
    await test.test_interruptible_audio()

if __name__ == "__main__":
    asyncio.run(main())