import asyncio
import websockets
import datetime

class RawDataMonitor:
    def __init__(self):
        self.port = 8766
        self.message_count = 0
        self.is_monitoring = False
        
    async def start_monitoring(self):
        """完全生データ監視（一切の処理なし）"""
        uri = f"ws://localhost:{self.port}"
        self.is_monitoring = True
        
        try:
            async with websockets.connect(uri) as ws:
                print("="*80)
                print(f"ポート{self.port} 完全生データ監視開始")
                print(f"開始時刻: {datetime.datetime.now()}")
                print("="*80)
                print("受信した全データを出力します（一切の加工なし）\n")
                
                async for message in ws:
                    if not self.is_monitoring:
                        break
                    
                    self.message_count += 1
                    timestamp = datetime.datetime.now().strftime("%H:%M:%S.%f")[:-3]
                    
                    print(f"[{timestamp}] データ #{self.message_count}")
                    print(f"データ型: {type(message)}")
                    print(f"データサイズ: {len(message) if message else 0} bytes")
                    
                    # バイナリデータかテキストデータかを判定
                    if isinstance(message, bytes):
                        print("バイナリデータ:")
                        print(f"HEX: {message.hex()}")
                        try:
                            decoded = message.decode('utf-8', errors='replace')
                            print(f"UTF-8デコード試行: {decoded}")
                        except:
                            print("UTF-8デコード失敗")
                    elif isinstance(message, str):
                        print("テキストデータ:")
                        print(f"内容: {repr(message)}")  # エスケープ文字も表示
                        print(f"実際の内容: {message}")
                    else:
                        print(f"未知のデータ型: {type(message)}")
                        print(f"内容: {message}")
                    
                    print("-" * 80)
                    print()
                        
        except websockets.exceptions.ConnectionRefused:
            print(f"接続失敗: ポート{self.port}にサーバーが見つかりません")
        except Exception as e:
            print(f"監視エラー: {e}")
            import traceback
            traceback.print_exc()
    
    def stop_monitoring(self):
        """監視停止"""
        self.is_monitoring = False
        print(f"\n監視停止 - 総受信データ数: {self.message_count}")

async def main():
    monitor = RawDataMonitor()
    
    print("ポート8766 完全生データ監視")
    print("JSON、テキスト、バイナリ問わず全て表示")
    print("Ctrl+C で停止\n")
    
    try:
        await monitor.start_monitoring()
    except KeyboardInterrupt:
        print("\nキーボード割り込み")
    finally:
        monitor.stop_monitoring()

if __name__ == "__main__":
    asyncio.run(main())