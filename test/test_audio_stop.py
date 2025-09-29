"""
音声再生途中停止テスト
"""
import asyncio
import threading
import time
import queue
from pathlib import Path
import sys

# パッケージパスを追加
project_root = Path(__file__).parent.parent  # test/の親ディレクトリ
sys.path.insert(0, str(project_root))

from server.config_manager import ConfigManager
from server.audio_analyzer import AudioAnalyzer
from server.voicevox_client import VoicevoxClient

class AudioStopTest:
    def __init__(self):
        self.config = ConfigManager().load_config()
        self.voicevox = VoicevoxClient(self.config)
        self.audio_analyzer = AudioAnalyzer(self.config)
        self.volume_queue = queue.Queue()
        self.audio_thread = None
        self.stop_flag = False
        self.current_player = None  # 再生中のplayerインスタンス保存

    async def test_audio_stop(self):
        """音声停止テスト"""
        print("🎵 音声合成開始...")

        # 長いテキストで音声合成
        text = "これは非常に長いテストメッセージです。音声再生中に停止機能をテストします。" * 3
        audio_file = await self.voicevox.synthesize_speech(text)

        if not audio_file:
            print("❌ 音声合成失敗")
            return

        print(f"🎵 音声再生開始: {audio_file}")

        # 音声再生スレッド開始
        self.start_audio_playback(audio_file)

        # 3秒後に停止テスト
        await asyncio.sleep(3)
        print("⏹️ 停止テスト実行")
        self.stop_audio()

        # 結果確認
        await asyncio.sleep(2)
        if self.audio_thread and self.audio_thread.is_alive():
            print("❌ スレッド停止失敗")
            time.sleep(10)
        else:
            print("✅ スレッド停止成功")

    def start_audio_playback(self, audio_file):
        """音声再生開始"""
        self.stop_flag = False

        def play_audio():
            try:
                print("🔊 再生スレッド開始")
                player = self.audio_analyzer.create_player()

                # playerインスタンスを保存
                self.current_player = player
                print(f"🎯 playerインスタンス保存: {type(player)}")

                # playerの利用可能メソッドを調査
                methods = [method for method in dir(player) if not method.startswith('_')]
                print(f"🔍 playerメソッド一覧: {methods}")

                # 停止フラグをチェックしながら再生
                if not self.stop_flag:
                    print("🎵 play_async開始")
                    # play_asyncを試行（非ブロッキングの可能性）
                    try:
                        result = player.play_async(audio_file)
                        print(f"🎵 play_async結果: {result}")

                        # play_asyncが非同期の場合、待機ループで停止チェック
                        # is_playingがプロパティかメソッドかチェック
                        while True:
                            try:
                                # プロパティとして試行
                                playing_status = player.is_playing
                                if callable(playing_status):
                                    playing = playing_status()
                                else:
                                    playing = playing_status

                                if not playing or self.stop_flag:
                                    break

                            except Exception as e:
                                print(f"⚠️ is_playing確認エラー: {e}")
                                break

                            time.sleep(0.1)

                        if self.stop_flag:
                            print("🛑 停止フラグによる中断")
                        else:
                            print("🎵 自然終了")

                    except Exception as e:
                        print(f"❌ play_async エラー: {e}")
                        # フォールバック: 元のメソッド
                        print("🔄 play_with_analysisにフォールバック")
                        player.play_with_analysis(audio_file)

                    print("🎵 音声処理完了")

                print("🔊 再生完了")
                self.volume_queue.put("END")

            except Exception as e:
                print(f"❌ 再生エラー: {e}")
                self.volume_queue.put("END")
            finally:
                self.current_player = None

        self.audio_thread = threading.Thread(target=play_audio, daemon=True)
        self.audio_thread.start()

    def stop_audio(self):
        """音声停止"""
        print("⏹️ 停止フラグ設定")
        self.stop_flag = True

        # current_playerインスタンスで停止を試行
        if self.current_player:
            print(f"🎯 current_player発見: {type(self.current_player)}")

            # 停止系メソッドを探して実行
            stop_methods = ['stop', 'pause', 'close', 'terminate', 'abort', 'cancel']
            for method_name in stop_methods:
                if hasattr(self.current_player, method_name):
                    try:
                        method = getattr(self.current_player, method_name)
                        print(f"🛑 {method_name}() 実行")
                        method()
                        break
                    except Exception as e:
                        print(f"❌ {method_name}() エラー: {e}")
            else:
                print("⚠️ playerに停止メソッドなし")
        else:
            print("⚠️ current_playerが見つからない")

        # audio_analyzerに停止メソッドがあるかチェック
        if hasattr(self.audio_analyzer, 'stop'):
            print("⏹️ audio_analyzer.stop() 実行")
            self.audio_analyzer.stop()
        else:
            print("⚠️ audio_analyzer.stop() メソッドなし")

async def main():
    test = AudioStopTest()

    # VOICEVOX接続確認
    if not await test.voicevox.check_connection():
        print("❌ VOICEVOX接続失敗")
        return

    print("✅ VOICEVOX接続成功")
    await test.test_audio_stop()

if __name__ == "__main__":
    asyncio.run(main())