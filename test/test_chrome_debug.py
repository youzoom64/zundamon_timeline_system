#!/usr/bin/env python3
"""
デバッグモードChromeテストスクリプト
Profile 3, 4, 6, 7 のいずれかを指定して起動
"""
import sys
import subprocess
import time

def launch_chrome_debug(profile_number, debug_port=9223):
    """
    デバッグモードでChromeを起動

    Args:
        profile_number: プロファイル番号 (3, 4, 6, 7)
        debug_port: デバッグポート番号
    """
    chrome_exe = "C:/Program Files/Google/Chrome/Application/chrome.exe"
    user_data_dir = "C:/Users/youzo/AppData/Local/Google/Chrome/User Data"
    profile_dir = f"Profile {profile_number}"

    # コマンドライン引数
    args = [
        chrome_exe,
        f"--remote-debugging-port={debug_port}",
        f"--user-data-dir={user_data_dir}",
        f"--profile-directory={profile_dir}",
        "https://live.nicovideo.jp/create"
    ]

    print(f"🚀 Chrome起動中...")
    print(f"   プロファイル: {profile_dir}")
    print(f"   デバッグポート: {debug_port}")
    print(f"   URL: https://live.nicovideo.jp/create")
    print()

    try:
        # Chrome起動
        subprocess.Popen(args)

        print("✅ Chrome起動完了")
        print(f"   デバッグURL: http://localhost:{debug_port}")
        print()
        print("ニコニコ生放送のページが開いています。")
        print("「チック」アカウントかどうか確認してください。")

    except Exception as e:
        print(f"❌ Chrome起動エラー: {e}")
        return False

    return True


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("使用方法: python test_chrome_debug.py <profile_number>")
        print("  profile_number: 3, 4, 6, 7 のいずれか")
        print()
        print("例:")
        print("  python test_chrome_debug.py 3")
        print("  python test_chrome_debug.py 4")
        print("  python test_chrome_debug.py 6")
        print("  python test_chrome_debug.py 7")
        sys.exit(1)

    profile_number = int(sys.argv[1])

    if profile_number not in [3, 4, 6, 7]:
        print(f"❌ エラー: プロファイル番号は 3, 4, 6, 7 のいずれかを指定してください")
        sys.exit(1)

    # デバッグポート指定（オプション）
    debug_port = 9223
    if len(sys.argv) >= 3:
        debug_port = int(sys.argv[2])

    # Chrome起動
    launch_chrome_debug(profile_number, debug_port)