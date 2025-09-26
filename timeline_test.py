import asyncio
import websockets
import json
import random

class ComplexTimelineTest:
    def __init__(self):
        self.ws_uri = "ws://localhost:8768"
    
    async def scenario_opening(self):
        """配信開始シナリオ"""
        print("=== 配信開始シナリオ ===")
        
        timeline = [
            {"action": "speak", "text": "みなさんこんにちはなのだ！今日も配信を始めるのだ！", "wait": 5},
            {"action": "change_expression", "preset": "happy", "wait": 1},
            {"action": "change_pose", "preset": "raise_hand", "wait": 2},
            {"action": "speak", "text": "今日はいろんなことをしてみるのだ！", "wait": 4},
            {"action": "change_outfit", "preset": "casual", "wait": 1},
            {"action": "speak", "text": "水着に着替えたのだ！夏っぽいのだ！", "wait": 4},
            {"action": "change_pose", "preset": "basic", "wait": 1},
            {"action": "change_expression", "preset": "normal", "wait": 1},
            {"action": "speak", "text": "それでは質問コーナーを始めるのだ！", "wait": 4}
        ]
        
        await self.execute_timeline(timeline)
    
    async def scenario_qa_session(self):
        """質問応答シナリオ"""
        print("=== 質問応答シナリオ ===")
        
        questions = [
            {
                "question": "好きな食べ物は何ですか？",
                "response": "ずんだもちが一番好きなのだ！甘くて美味しいのだ！",
                "expression": "happy",
                "pose": "basic"
            },
            {
                "question": "今日の天気はどうですか？",
                "response": "今日は晴れていて気持ちがいいのだ！",
                "expression": "normal", 
                "pose": "point"
            },
            {
                "question": "疲れたりしませんか？",
                "response": "ちょっと疲れているのだ...でも頑張るのだ！",
                "expression": "sad",
                "pose": "think"
            }
        ]
        
        for i, qa in enumerate(questions):
            timeline = [
                {"action": "speak", "text": f"質問{i+1}：{qa['question']}", "wait": 4},
                {"action": "change_expression", "preset": qa["expression"], "wait": 1},
                {"action": "change_pose", "preset": qa["pose"], "wait": 1},
                {"action": "speak", "text": qa["response"], "wait": 5},
                {"action": "change_expression", "preset": "normal", "wait": 1}
            ]
            await self.execute_timeline(timeline)
    
    async def scenario_outfit_show(self):
        """衣装チェンジショー"""
        print("=== 衣装チェンジショー ===")
        
        outfits = [
            {"name": "usual", "description": "いつものお気に入りの服なのだ！"},
            {"name": "casual", "description": "水着で夏らしいのだ！"},
            {"name": "uniform", "description": "制服もかっこいいのだ！"}
        ]
        
        timeline = [
            {"action": "speak", "text": "それでは衣装ショーを始めるのだ！", "wait": 3},
            {"action": "change_expression", "preset": "happy", "wait": 1}
        ]
        
        for outfit in outfits:
            timeline.extend([
                {"action": "change_outfit", "preset": outfit["name"], "wait": 2},
                {"action": "change_pose", "preset": "raise_hand", "wait": 1},
                {"action": "speak", "text": outfit["description"], "wait": 4},
                {"action": "change_pose", "preset": "basic", "wait": 1}
            ])
        
        timeline.extend([
            {"action": "speak", "text": "どの衣装が一番好きだったのだ？", "wait": 4},
            {"action": "change_expression", "preset": "normal", "wait": 1}
        ])
        
        await self.execute_timeline(timeline)
    
    async def scenario_random_actions(self):
        """ランダムアクションテスト"""
        print("=== ランダムアクションテスト ===")
        
        expressions = ["normal", "happy", "angry", "sad"]
        poses = ["basic", "raise_hand", "point", "think"]
        outfits = ["usual", "casual", "uniform"]
        
        timeline = [
            {"action": "speak", "text": "今からランダムに動くのだ！", "wait": 3}
        ]
        
        for i in range(8):
            expr = random.choice(expressions)
            pose = random.choice(poses)
            outfit = random.choice(outfits)
            
            timeline.extend([
                {"action": "change_expression", "preset": expr, "wait": 0.5},
                {"action": "change_pose", "preset": pose, "wait": 0.5},
                {"action": "change_outfit", "preset": outfit, "wait": 1},
                {"action": "speak", "text": f"ランダム{i+1}回目なのだ！", "wait": 2}
            ])
        
        timeline.append({"action": "speak", "text": "ランダムテスト終了なのだ！", "wait": 3})
        
        await self.execute_timeline(timeline)
    
    async def scenario_ending(self):
        """配信終了シナリオ"""
        print("=== 配信終了シナリオ ===")
        
        timeline = [
            {"action": "change_outfit", "preset": "usual", "wait": 1},
            {"action": "change_expression", "preset": "happy", "wait": 1},
            {"action": "change_pose", "preset": "raise_hand", "wait": 1},
            {"action": "speak", "text": "今日の配信はこれで終了なのだ！", "wait": 4},
            {"action": "speak", "text": "見てくれてありがとうございましたなのだ！", "wait": 4},
            {"action": "change_expression", "preset": "normal", "wait": 1},
            {"action": "change_pose", "preset": "basic", "wait": 1},
            {"action": "speak", "text": "また明日も会えるといいのだ！バイバイなのだ！", "wait": 5}
        ]
        
        await self.execute_timeline(timeline)
    
    async def execute_timeline(self, timeline):
        """タイムライン実行"""
        try:
            async with websockets.connect(self.ws_uri) as ws:
                for step in timeline:
                    command = {k: v for k, v in step.items() if k != 'wait'}
                    
                    await ws.send(json.dumps(command))
                    print(f"実行: {command.get('action')} - {command.get('text', command.get('preset', ''))}")
                    
                    if step.get('wait', 0) > 0:
                        await asyncio.sleep(step['wait'])
                        
        except Exception as e:
            print(f"エラー: {e}")

async def main():
    print("複雑なタイムラインテスト")
    print("1: 配信開始シナリオ")
    print("2: 質問応答シナリオ") 
    print("3: 衣装チェンジショー")
    print("4: ランダムアクション")
    print("5: 配信終了シナリオ")
    print("6: 全シナリオ連続実行")
    
    choice = input("選択 (1-6): ").strip()
    
    tester = ComplexTimelineTest()
    
    if choice == "1":
        await tester.scenario_opening()
    elif choice == "2":
        await tester.scenario_qa_session()
    elif choice == "3":
        await tester.scenario_outfit_show()
    elif choice == "4":
        await tester.scenario_random_actions()
    elif choice == "5":
        await tester.scenario_ending()
    elif choice == "6":
        print("=== 全シナリオ連続実行開始 ===")
        await tester.scenario_opening()
        await asyncio.sleep(2)
        await tester.scenario_qa_session()
        await asyncio.sleep(2)
        await tester.scenario_outfit_show()
        await asyncio.sleep(2)
        await tester.scenario_random_actions()
        await asyncio.sleep(2)
        await tester.scenario_ending()
        print("=== 全シナリオ完了 ===")
    else:
        print("無効な選択")

if __name__ == "__main__":
    asyncio.run(main())