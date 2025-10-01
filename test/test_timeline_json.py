#!/usr/bin/env python3
"""
生成されたタイムラインJSONを直接テストするスクリプト
"""
import asyncio
import json
import sys
import logging
from pathlib import Path

# プロジェクトルートをパスに追加
sys.path.insert(0, str(Path(__file__).parent.parent))

from server.config_manager import ConfigManager
from server.timeline_executor import TimelineExecutor
from server.obs_controller import OBSController
from server.voicevox_client import VoicevoxClient

async def test_timeline_json(json_file_path: str):
    """タイムラインJSONをテスト実行"""

    # 設定読み込み
    config_manager = ConfigManager()
    config = config_manager.load_config()

    # ロギング設定
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )

    print(f"[テスト] タイムラインJSON読み込み: {json_file_path}")

    # JSONファイル読み込み
    json_path = Path(json_file_path)
    if not json_path.exists():
        print(f"[エラー] ファイルが見つかりません: {json_file_path}")
        return

    with open(json_path, 'r', encoding='utf-8') as f:
        timeline_json = json.load(f)

    print(f"[テスト] タイムライン項目数: {len(timeline_json.get('timeline', []))}")
    print(f"[テスト] タイトル: {timeline_json.get('title')}")

    # VOICEVOX初期化
    voicevox = VoicevoxClient(config)
    if await voicevox.check_connection():
        print("[テスト] VOICEVOX接続成功")
    else:
        print("[警告] VOICEVOX接続失敗")
        return

    # OBSコントローラー初期化
    obs_controller = OBSController(config)

    # OBS接続確認
    if obs_controller.ensure_obs_ready():
        print("[テスト] OBS接続成功")
        obs_controller.connect()

        # ずんだもんシーンに切り替え
        obs_controller.switch_scene("ずんだもんシーン")
        await asyncio.sleep(1.0)
    else:
        print("[警告] OBS接続失敗 - OBS操作なしで続行")

    # 音声合成コールバック（簡易版）
    async def simple_speech_callback(action_data):
        """簡易音声合成コールバック"""
        text = action_data.get("text", "")
        character = action_data.get("character", "zundamon")

        print(f"[音声合成] {character}: {text[:50]}...")

        # キャラクター別の音声ID
        voice_id = 2 if character == "metan" else 3

        # 音声合成
        try:
            audio_file = await voicevox.synthesize_speech(text, speaker_id=voice_id)

            if audio_file:
                print(f"[再生] {audio_file}")
                # 実際の再生は省略（音声ファイルは生成される）
                # 再生時間推定
                wait_time = len(text) * 0.15 + 1.0
                await asyncio.sleep(wait_time)
            else:
                print("[エラー] 音声合成失敗 - スキップ")
        except Exception as e:
            print(f"[エラー] 音声合成例外: {e} - スキップ")

    print("\n[テスト] タイムライン実行開始...")
    print("=" * 60)

    # タイムライン実行
    timeline_executor = TimelineExecutor(config, obs_controller, broadcast_callback=simple_speech_callback)

    try:
        result = await timeline_executor.execute_timeline_from_json(timeline_json)

        print("=" * 60)
        print(f"[テスト] タイムライン実行完了")
        print(f"  実行時間: {result['duration']:.2f}秒")
        print(f"  実行項目数: {result['actions_count']}")
        print(f"  ステータス: {result['status']}")

    except Exception as e:
        print(f"[エラー] タイムライン実行エラー: {e}")
        import traceback
        traceback.print_exc()

    finally:
        # OBS切断
        if obs_controller:
            obs_controller.disconnect()

        print("\n[テスト] テスト完了")

def main():
    """メイン関数"""
    if len(sys.argv) < 2:
        print("使用方法: python test_timeline_json.py <timeline.json>")
        print("\n例:")
        print("  python test/test_timeline_json.py test/generated_timelines/timeline_21639740_lv348821409.json")
        sys.exit(1)

    json_file_path = sys.argv[1]

    print("=" * 60)
    print("タイムラインJSONテストスクリプト")
    print("=" * 60)
    print()
    print("必要な準備:")
    print("  1. VOICEVOX が起動していること (localhost:50021)")
    print("  2. OBS が起動していること (WebSocket有効)")
    print("  3. OBSに「ずんだもんシーン」が存在すること")
    print()
    print("実行準備ができたらEnterキーを押してください...")
    input()

    asyncio.run(test_timeline_json(json_file_path))

if __name__ == "__main__":
    main()
