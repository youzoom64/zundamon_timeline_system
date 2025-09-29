#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
データベーススキーマ調査スクリプト
要約関連のテーブルやカラムを検索する
"""

import sqlite3
import os
import re

def check_database_schema(db_path):
    """データベースのスキーマを確認し、要約関連の情報を検索する"""

    if not os.path.exists(db_path):
        print(f"データベースファイルが見つかりません: {db_path}")
        return

    try:
        # データベースに接続
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()

        print(f"データベースファイル: {db_path}")
        print("=" * 50)

        # 1. テーブル一覧の表示
        print("\n1. テーブル一覧:")
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table';")
        tables = cursor.fetchall()

        if not tables:
            print("テーブルが見つかりませんでした。")
            return

        table_names = [table[0] for table in tables]
        for table_name in table_names:
            print(f"  - {table_name}")

        print(f"\n総テーブル数: {len(table_names)}")

        # 2. 各テーブルのスキーマ確認
        print("\n2. 各テーブルのスキーマ:")
        print("-" * 50)

        all_columns = {}

        for table_name in table_names:
            print(f"\n[テーブル名: {table_name}]")

            # テーブルのスキーマを取得
            cursor.execute(f"PRAGMA table_info({table_name});")
            columns = cursor.fetchall()

            all_columns[table_name] = []

            if columns:
                print("  カラム一覧:")
                for col in columns:
                    col_id, col_name, col_type, not_null, default_val, primary_key = col
                    all_columns[table_name].append(col_name)
                    pk_str = " (PRIMARY KEY)" if primary_key else ""
                    nn_str = " NOT NULL" if not_null else ""
                    default_str = f" DEFAULT {default_val}" if default_val is not None else ""
                    print(f"    {col_name}: {col_type}{pk_str}{nn_str}{default_str}")

                # レコード数も確認
                try:
                    cursor.execute(f"SELECT COUNT(*) FROM {table_name};")
                    count = cursor.fetchone()[0]
                    print(f"  レコード数: {count}")
                except:
                    print("  レコード数: 取得できませんでした")
            else:
                print("  カラムが見つかりませんでした")

        # 3. 要約関連のキーワード検索
        print("\n3. 要約関連のテーブル名・カラム名の検索:")
        print("-" * 50)

        # 検索するキーワード（日本語と英語）
        summary_keywords = [
            'summary', 'summaries', 'summarize', 'summarized',
            '要約', 'まとめ', '概要', '集約', 'digest',
            'abstract', 'overview', 'recap'
        ]

        found_items = []

        # テーブル名での検索
        print("\n要約関連のテーブル名:")
        for table_name in table_names:
            for keyword in summary_keywords:
                if keyword.lower() in table_name.lower():
                    found_items.append(f"テーブル名: {table_name} (キーワード: {keyword})")
                    print(f"  - {table_name} (キーワード: {keyword})")

        # カラム名での検索
        print("\n要約関連のカラム名:")
        for table_name, columns in all_columns.items():
            for col_name in columns:
                for keyword in summary_keywords:
                    if keyword.lower() in col_name.lower():
                        found_items.append(f"カラム名: {table_name}.{col_name} (キーワード: {keyword})")
                        print(f"  - {table_name}.{col_name} (キーワード: {keyword})")

        # 結果の要約
        print("\n4. 検索結果の要約:")
        print("-" * 50)

        if found_items:
            print(f"要約関連の項目が {len(found_items)} 件見つかりました:")
            for item in found_items:
                print(f"  - {item}")
        else:
            print("要約関連のテーブル名やカラム名は見つかりませんでした。")

        # 追加で全カラム名を出力（後で検索しやすいように）
        print("\n5. 全カラム名一覧（参考）:")
        print("-" * 50)
        for table_name, columns in all_columns.items():
            print(f"{table_name}:")
            for col_name in columns:
                print(f"  - {col_name}")

    except sqlite3.Error as e:
        print(f"SQLiteエラーが発生しました: {e}")
    except Exception as e:
        print(f"エラーが発生しました: {e}")
    finally:
        if conn:
            conn.close()

if __name__ == "__main__":
    # データベースファイルのパス
    db_path = "C:/project_root/app_workspaces/ncv_special_monitor/data/ncv_monitor.db"

    print("データベーススキーマ調査を開始します...")
    check_database_schema(db_path)
    print("\n調査完了しました。")