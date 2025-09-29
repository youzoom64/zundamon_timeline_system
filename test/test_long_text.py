"""
長文テキスト読み上げ・停止テスト
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

class LongTextTest:
    def __init__(self):
        self.config = ConfigManager().load_config()
        self.voicevox = VoicevoxClient(self.config)
        self.audio_analyzer = AudioAnalyzer(self.config)
        self.current_player = None
        self.audio_thread = None

    async def test_long_text_interruption(self):
        """長文読み上げ・割り込みテスト"""
        print("📧 長文読み上げテスト開始")

        # 指定されたテキスト
        text = """メールサービスやセキュリティソフトの設定により、弊社からの返信メールが迷惑メールとして処理されている可能性がございますが、迷惑メールフォルダ等にメールが届いていないかどうかご確認くださいと言いたいところですが、上記の点をご確認いただいても弊社からの返信が届いていない場合は、
お手数ではございますが、ご連絡先のメールアドレスをご確認の上
再度お問合せをお願いいたします。"""

        print(f"📝 読み上げテキスト: {len(text)}文字")

        # 音声合成
        print("🎵 音声合成中...")
        audio_file = await self.voicevox.synthesize_speech(text)

        if not audio_file:
            print("❌ 音声合成失敗")
            return

        print(f"🎵 音声ファイル生成完了: {audio_file}")

        # 再生開始
        player = self.audio_analyzer.create_player()
        self.current_player = player

        print("🔊 音声再生開始")
        self.audio_thread = player.play_async(audio_file)

        # 実際の読み上げ時間を確認
        start_time = time.time()

        # 10秒後に停止テスト
        print("⏰ 10秒後に停止テストを実行...")
        await asyncio.sleep(10)

        elapsed_time = time.time() - start_time
        print(f"📊 経過時間: {elapsed_time:.1f}秒")
        print(f"📊 停止前の状態: is_playing={player.is_playing}")

        if player.is_playing:
            print("🛑 音声停止実行")
            player.stop()

            # 停止確認
            await asyncio.sleep(0.5)
            print(f"📊 停止後の状態: is_playing={player.is_playing}")

            if not player.is_playing:
                print("✅ 音声停止成功！")
                stop_time = time.time() - start_time
                print(f"🎯 停止タイミング: {stop_time:.1f}秒地点")
            else:
                print("❌ 音声停止失敗")
        else:
            print("⚠️ 音声が既に自然終了していました")
            natural_end_time = time.time() - start_time
            print(f"🏁 自然終了時間: {natural_end_time:.1f}秒")

        # スレッド完了まで待機
        print("🔄 スレッド完了待機...")
        if self.audio_thread and self.audio_thread.is_alive():
            self.audio_thread.join(timeout=2)

        print("🏁 テスト完了")

async def main():
    test = LongTextTest()

    # VOICEVOX接続確認
    if not await test.voicevox.check_connection():
        print("❌ VOICEVOX接続失敗")
        return

    print("✅ VOICEVOX接続成功")
    await test.test_long_text_interruption()

if __name__ == "__main__":
    asyncio.run(main())