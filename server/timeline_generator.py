"""
データベースからタイムライン生成システム
"""
import sqlite3
import logging
from typing import List, Dict
from datetime import datetime

class TimelineGenerator:
    def __init__(self):
        self.logger = logging.getLogger(__name__)
        # Aシステムのデータベースパス
        self.db_path = "C:/project_root/app_workspaces/ncv_special_monitor/data/ncv_monitor.db"

    def generate_from_broadcasts(self, broadcast_ids: List[str], user_id: str = None, title: str = "データベース生成タイムライン") -> Dict:
        """
        データベースから放送IDリストに基づいてタイムライン生成

        Args:
            broadcast_ids: 放送IDリスト（例: ["lv348354633", "lv348354634"]）
            user_id: フィルタリング対象のユーザーID（指定時は該当ユーザーのコメントのみ取得）
            title: タイムラインタイトル

        Returns:
            timeline_executor互換のJSONデータ
        """
        self.logger.info(f"タイムライン生成開始: {len(broadcast_ids)}件の放送, user_id={user_id or '全ユーザー'}")

        try:
            # データベースからデータ取得
            comments_data = self._fetch_comments_from_db(broadcast_ids, user_id)
            ai_analyses_data = self._fetch_ai_analyses_from_db(broadcast_ids, user_id)

            # データ統合・ソート
            combined_data = self._combine_and_sort_data(comments_data, ai_analyses_data)

            if not combined_data:
                self.logger.warning("データが見つかりませんでした")
                return self._create_empty_timeline(title)

            # タイムライン生成
            timeline_json = self._build_timeline_json(combined_data, title, broadcast_ids)

            self.logger.info(f"タイムライン生成完了: {len(combined_data)}項目")
            return timeline_json

        except Exception as e:
            self.logger.error(f"タイムライン生成エラー: {e}")
            return self._create_empty_timeline(title)

    def _fetch_comments_from_db(self, broadcast_ids: List[str], user_id: str = None) -> List[Dict]:
        """commentsテーブルからデータ取得（user_idでフィルタリング可能）"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                placeholders = ",".join("?" for _ in broadcast_ids)

                if user_id:
                    # 特定ユーザーのみ
                    cursor.execute(f"""
                        SELECT comment_text, user_name, broadcast_title, broadcast_lv_id,
                               timestamp, elapsed_time
                        FROM comments
                        WHERE broadcast_lv_id IN ({placeholders}) AND user_id = ?
                        ORDER BY timestamp
                    """, broadcast_ids + [user_id])
                else:
                    # 全ユーザー
                    cursor.execute(f"""
                        SELECT comment_text, user_name, broadcast_title, broadcast_lv_id,
                               timestamp, elapsed_time
                        FROM comments
                        WHERE broadcast_lv_id IN ({placeholders})
                        ORDER BY timestamp
                    """, broadcast_ids)

                rows = cursor.fetchall()
                return [{
                    "type": "comment",
                    "text": row[0],
                    "user_name": row[1] or "名無し",
                    "broadcast_title": row[2],
                    "broadcast_lv_id": row[3],
                    "timestamp": row[4],
                    "elapsed_time": row[5]
                } for row in rows]

        except Exception as e:
            self.logger.error(f"コメント取得エラー: {e}")
            return []

    def _fetch_ai_analyses_from_db(self, broadcast_ids: List[str], user_id: str = None) -> List[Dict]:
        """ai_analysesテーブルからデータ取得（user_idでフィルタリング可能）"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                placeholders = ",".join("?" for _ in broadcast_ids)

                if user_id:
                    # 特定ユーザーのみ
                    cursor.execute(f"""
                        SELECT analysis_result, broadcast_title, broadcast_lv_id,
                               broadcast_start_time, 'summary'
                        FROM ai_analyses
                        WHERE broadcast_lv_id IN ({placeholders}) AND user_id = ?
                        ORDER BY broadcast_start_time
                    """, broadcast_ids + [user_id])
                else:
                    # 全ユーザー
                    cursor.execute(f"""
                        SELECT analysis_result, broadcast_title, broadcast_lv_id,
                               broadcast_start_time, 'summary'
                        FROM ai_analyses
                        WHERE broadcast_lv_id IN ({placeholders})
                        ORDER BY broadcast_start_time
                    """, broadcast_ids)

                rows = cursor.fetchall()
                return [{
                    "type": "ai_analysis",
                    "text": row[0],
                    "user_name": "システム",
                    "broadcast_title": row[1],
                    "broadcast_lv_id": row[2],
                    "timestamp": row[3],
                    "analysis_type": row[4]
                } for row in rows]

        except Exception as e:
            self.logger.error(f"AI分析取得エラー: {e}")
            return []

    def _combine_and_sort_data(self, comments: List[Dict], ai_analyses: List[Dict]) -> List[Dict]:
        """データ統合・時系列ソート"""
        combined = comments + ai_analyses
        # timestampで昇順ソート
        combined.sort(key=lambda x: x.get("timestamp", 0))
        return combined

    def _build_timeline_json(self, data: List[Dict], title: str, broadcast_ids: List[str]) -> Dict:
        """timeline_executor互換のJSON構造生成"""
        # 放送タイトルを統合
        broadcast_titles = list(set([item.get("broadcast_title", "") for item in data if item.get("broadcast_title")]))
        combined_title = f"{title} ({', '.join(broadcast_titles[:2])}{'...' if len(broadcast_titles) > 2 else ''})"

        timeline_items = []
        current_time = 0.0

        for item in data:
            # 読み上げ時間推定（文字数ベース：5文字/秒）
            text = item.get("text", "")
            estimated_duration = max(len(text) / 5.0, 2.0)  # 最低2秒

            # 表情・ポーズをタイプに応じて設定
            if item["type"] == "ai_analysis":
                expression = "normal"
                pose = "think"
                prefix = "[AI分析]"
            else:
                expression = "happy"
                pose = "basic"
                prefix = f"[{item['user_name']}]"

            timeline_items.append({
                "time": current_time,
                "character": "zundamon",
                "position": "center",
                "expression": expression,
                "outfit": "usual",
                "pose": pose,
                "text": f"{prefix} {text}",
                "blink": True
            })

            current_time += estimated_duration

        return {
            "title": combined_title,
            "listener_name": "視聴者さん",
            "nickname": "みんな",
            "other_text": f"放送ID: {', '.join(broadcast_ids)}",
            "timeline": timeline_items
        }

    def _create_empty_timeline(self, title: str) -> Dict:
        """エラー時の空タイムライン生成"""
        return {
            "title": title,
            "listener_name": "視聴者さん",
            "nickname": "みんな",
            "other_text": "データ取得に失敗しました",
            "timeline": [{
                "time": 0.0,
                "character": "zundamon",
                "position": "center",
                "expression": "normal",
                "outfit": "usual",
                "pose": "basic",
                "text": "データベースからの読み込みに失敗したのだ...",
                "blink": True
            }]
        }

    def estimate_total_duration(self, broadcast_ids: List[str], user_id: str = None) -> float:
        """タイムライン総実行時間推定"""
        try:
            comments_data = self._fetch_comments_from_db(broadcast_ids, user_id)
            ai_analyses_data = self._fetch_ai_analyses_from_db(broadcast_ids, user_id)
            combined_data = self._combine_and_sort_data(comments_data, ai_analyses_data)

            total_duration = 0.0
            for item in combined_data:
                text = item.get("text", "")
                total_duration += max(len(text) / 5.0, 2.0)

            return total_duration

        except Exception as e:
            self.logger.error(f"時間推定エラー: {e}")
            return 0.0


if __name__ == "__main__":
    # テスト用
    logging.basicConfig(level=logging.INFO)

    generator = TimelineGenerator()

    # サンプル放送ID
    test_broadcast_ids = ["lv348354633"]

    # タイムライン生成テスト
    timeline = generator.generate_from_broadcasts(test_broadcast_ids, "テストタイムライン")

    print("生成されたタイムライン:")
    print(f"タイトル: {timeline['title']}")
    print(f"項目数: {len(timeline['timeline'])}")
    print(f"推定時間: {generator.estimate_total_duration(test_broadcast_ids):.1f}秒")