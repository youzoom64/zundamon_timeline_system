"""
安全な音声停止テスト
"""
import asyncio
import threading
import time
import queue
from pathlib import Path
import sys

# パッケージパスを追加
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from server.config_manager import ConfigManager
from server.audio_analyzer import AudioAnalyzer
from server.voicevox_client import VoicevoxClient

class SafeAudioTest:
    def __init__(self):
        self.config = ConfigManager().load_config()
        self.voicevox = VoicevoxClient(self.config)
        self.audio_analyzer = AudioAnalyzer(self.config)
        self.current_player = None

    async def test_player_methods(self):
        """playerメソッドの詳細調査"""
        print("🔍 AudioPlayerクラス詳細調査")

        # 短いテキストで安全にテスト
        text = "テスト"
        audio_file = await self.voicevox.synthesize_speech(text)

        if not audio_file:
            print("❌ 音声合成失敗")
            return

        player = self.audio_analyzer.create_player()
        self.current_player = player

        print(f"📊 playerタイプ: {type(player)}")

        # メソッドの詳細調査
        for attr_name in dir(player):
            if not attr_name.startswith('_'):
                attr = getattr(player, attr_name)
                attr_type = type(attr).__name__
                print(f"  {attr_name}: {attr_type}")

        # is_playingの詳細確認
        print(f"\n🎯 is_playing詳細:")
        is_playing_attr = getattr(player, 'is_playing')
        print(f"  タイプ: {type(is_playing_attr)}")
        print(f"  値: {is_playing_attr}")

        if callable(is_playing_attr):
            try:
                result = is_playing_attr()
                print(f"  呼び出し結果: {result}")
            except Exception as e:
                print(f"  呼び出しエラー: {e}")

        # play_asyncの詳細確認
        print(f"\n🎯 play_async詳細:")
        try:
            print("play_async実行中...")
            result = player.play_async(audio_file)
            print(f"  戻り値: {result}")
            print(f"  戻り値タイプ: {type(result)}")

            # 少し待機
            time.sleep(1)

            # 停止テスト
            print("停止テスト...")
            player.stop()
            print("停止完了")

        except Exception as e:
            print(f"  play_asyncエラー: {e}")

async def main():
    test = SafeAudioTest()

    # VOICEVOX接続確認
    if not await test.voicevox.check_connection():
        print("❌ VOICEVOX接続失敗")
        return

    print("✅ VOICEVOX接続成功")
    await test.test_player_methods()

if __name__ == "__main__":
    asyncio.run(main())