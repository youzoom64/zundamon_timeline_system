import tkinter as tk
from tkinter import ttk, messagebox, filedialog
import json
from pathlib import Path
import datetime

class TimelineEditor:
    def __init__(self, parent):
        self.parent = parent
        self.timeline_data = None
        self.obs_timeline_data = None
        self.project_dir = None
        
        # 子ウィンドウ作成
        self.window = tk.Toplevel(parent)
        self.window.title("タイムライン編集")
        self.window.geometry("1200x800")
        self.window.transient(parent)
        self.window.grab_set()
        
        self.setup_ui()
        self.load_presets()
    
    def setup_ui(self):
        """UI初期化"""
        # メインフレーム
        main_frame = ttk.Frame(self.window, padding="10")
        main_frame.pack(fill=tk.BOTH, expand=True)
        
        # ツールバー
        toolbar = ttk.Frame(main_frame)
        toolbar.pack(fill=tk.X, pady=(0, 10))
        
        ttk.Button(toolbar, text="新規", command=self.new_timeline).pack(side=tk.LEFT, padx=(0, 5))
        ttk.Button(toolbar, text="開く", command=self.open_timeline).pack(side=tk.LEFT, padx=(0, 5))
        ttk.Button(toolbar, text="保存", command=self.save_timeline).pack(side=tk.LEFT, padx=(0, 5))
        ttk.Button(toolbar, text="名前を付けて保存", command=self.save_as_timeline).pack(side=tk.LEFT, padx=(0, 15))
        
        ttk.Button(toolbar, text="アクション追加", command=self.add_action).pack(side=tk.LEFT, padx=(0, 5))
        ttk.Button(toolbar, text="アクション削除", command=self.delete_action).pack(side=tk.LEFT, padx=(0, 5))
        ttk.Button(toolbar, text="上に移動", command=self.move_action_up).pack(side=tk.LEFT, padx=(0, 5))
        ttk.Button(toolbar, text="下に移動", command=self.move_action_down).pack(side=tk.LEFT)
        
        # メイン領域
        paned_window = ttk.PanedWindow(main_frame, orient=tk.HORIZONTAL)
        paned_window.pack(fill=tk.BOTH, expand=True)
        
        # 左パネル（プロジェクト情報）
        left_frame = ttk.LabelFrame(paned_window, text="プロジェクト情報", padding="10")
        paned_window.add(left_frame, weight=1)
        
        self.setup_project_info_panel(left_frame)
        
        # 右パネル（タイムライン）
        right_frame = ttk.LabelFrame(paned_window, text="タイムライン", padding="10")
        paned_window.add(right_frame, weight=2)
        
        self.setup_timeline_panel(right_frame)
    
    def setup_project_info_panel(self, parent):
        """プロジェクト情報パネル設定"""
        self.project_vars = {}
        
        # 基本情報
        info_frame = ttk.LabelFrame(parent, text="基本情報", padding="10")
        info_frame.pack(fill=tk.X, pady=(0, 10))
        
        fields = [
            ("title", "タイトル"),
            ("listener_name", "リスナー名"),
            ("nickname", "ニックネーム"),
            ("other_text", "その他テキスト")
        ]
        
        for i, (key, label) in enumerate(fields):
            ttk.Label(info_frame, text=f"{label}:").grid(row=i, column=0, sticky=tk.W, pady=2)
            
            var = tk.StringVar()
            self.project_vars[key] = var
            
            if key == "other_text":
                text_widget = tk.Text(info_frame, height=3, width=30)
                text_widget.grid(row=i, column=1, sticky=(tk.W, tk.E), padx=(10, 0), pady=2)
                self.project_vars[key] = text_widget
            else:
                ttk.Entry(info_frame, textvariable=var, width=30).grid(row=i, column=1, sticky=(tk.W, tk.E), padx=(10, 0), pady=2)
        
        info_frame.columnconfigure(1, weight=1)
        
        # プレビュー
        preview_frame = ttk.LabelFrame(parent, text="プレビュー", padding="10")
        preview_frame.pack(fill=tk.BOTH, expand=True)
        
        ttk.Button(preview_frame, text="プレビュー実行", command=self.preview_timeline).pack(pady=5)
        
        self.preview_text = tk.Text(preview_frame, height=10, wrap=tk.WORD)
        preview_scrollbar = ttk.Scrollbar(preview_frame, orient=tk.VERTICAL, command=self.preview_text.yview)
        self.preview_text.configure(yscrollcommand=preview_scrollbar.set)
        
        self.preview_text.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        preview_scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
    
    def setup_timeline_panel(self, parent):
        """タイムラインパネル設定"""
        # タブ
        notebook = ttk.Notebook(parent)
        notebook.pack(fill=tk.BOTH, expand=True)
        
        # ずんだもんタイムライン
        zundamon_frame = ttk.Frame(notebook, padding="5")
        notebook.add(zundamon_frame, text="ずんだもん")
        
        self.setup_zundamon_timeline(zundamon_frame)
        
        # OBSタイムライン
        obs_frame = ttk.Frame(notebook, padding="5")
        notebook.add(obs_frame, text="OBS")
        
        self.setup_obs_timeline(obs_frame)
    
    def setup_zundamon_timeline(self, parent):
        """ずんだもんタイムライン設定"""
        # ツリービュー
        columns = ("time", "character", "position", "expression", "pose", "outfit", "text", "blink")
        self.zundamon_tree = ttk.Treeview(parent, columns=columns, show="headings", height=15)
        
        # ヘッダー設定
        headers = {
            "time": ("時間", 60),
            "character": ("キャラ", 80),
            "position": ("位置", 60),
            "expression": ("表情", 80),
            "pose": ("ポーズ", 80),
            "outfit": ("衣装", 80),
            "text": ("テキスト", 200),
            "blink": ("まばたき", 80)
        }
        
        for col, (heading, width) in headers.items():
            self.zundamon_tree.heading(col, text=heading)
            self.zundamon_tree.column(col, width=width, minwidth=50)
        
        # スクロールバー
        zundamon_scrollbar = ttk.Scrollbar(parent, orient=tk.VERTICAL, command=self.zundamon_tree.yview)
        self.zundamon_tree.configure(yscrollcommand=zundamon_scrollbar.set)
        
        self.zundamon_tree.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        zundamon_scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        
        # ダブルクリックでアクション編集
        self.zundamon_tree.bind("<Double-1>", self.edit_zundamon_action)
    
    def setup_obs_timeline(self, parent):
        """OBSタイムライン設定"""
        # ツリービュー
        columns = ("time", "action", "target", "value", "duration")
        self.obs_tree = ttk.Treeview(parent, columns=columns, show="headings", height=15)
        
        # ヘッダー設定
        headers = {
            "time": ("時間", 60),
            "action": ("アクション", 120),
            "target": ("対象", 150),
            "value": ("値", 150),
            "duration": ("持続時間", 80)
        }
        
        for col, (heading, width) in headers.items():
            self.obs_tree.heading(col, text=heading)
            self.obs_tree.column(col, width=width, minwidth=50)
        
        # スクロールバー
        obs_scrollbar = ttk.Scrollbar(parent, orient=tk.VERTICAL, command=self.obs_tree.yview)
        self.obs_tree.configure(yscrollcommand=obs_scrollbar.set)
        
        self.obs_tree.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        obs_scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        
        # ダブルクリックでアクション編集
        self.obs_tree.bind("<Double-1>", self.edit_obs_action)
    
    def load_presets(self):
        """プリセット読み込み"""
        try:
            preset_path = Path("config/presets.json")
            if preset_path.exists():
                with open(preset_path, 'r', encoding='utf-8') as f:
                    self.presets = json.load(f)
            else:
                self.presets = self.get_default_presets()
        except Exception as e:
            messagebox.showerror("エラー", f"プリセット読み込みエラー: {e}")
            self.presets = self.get_default_presets()
    
    def get_default_presets(self):
        """デフォルトプリセット"""
        return {
            "expressions": {
                "normal": {"name": "通常"},
                "happy": {"name": "喜び"},
                "angry": {"name": "怒り"},
                "sad": {"name": "悲しみ"},
                "tired": {"name": "疲れ"}
            },
            "poses": {
                "basic": {"name": "基本"},
                "point": {"name": "指差し"},
                "raise_hand": {"name": "手上げ"},
                "think": {"name": "考える"},
                "mic": {"name": "マイク"}
            },
            "outfits": {
                "usual": {"name": "いつもの服"},
                "uniform": {"name": "制服"},
                "casual": {"name": "水着"}
            }
        }
    
    def new_timeline(self):
        """新規タイムライン作成"""
        if self.confirm_unsaved_changes():
            self.timeline_data = {
                "title": "新しいタイムライン",
                "listener_name": "リスナー名",
                "nickname": "ニックネーム", 
                "other_text": "その他テキスト",
                "timeline": []
            }
            
            self.obs_timeline_data = {
                "timeline": []
            }
            
            self.project_dir = None
            self.update_ui_from_data()
    
    def open_timeline(self):
        """タイムライン読み込み"""
        if not self.confirm_unsaved_changes():
            return
        
        project_dir = filedialog.askdirectory(title="プロジェクトフォルダを選択")
        if not project_dir:
            return
        
        try:
            self.project_dir = Path(project_dir)
            
            # ずんだもんタイムライン読み込み
            timeline_file = self.project_dir / "timeline.json"
            if timeline_file.exists():
                with open(timeline_file, 'r', encoding='utf-8') as f:
                    self.timeline_data = json.load(f)
            else:
                messagebox.showerror("エラー", "timeline.json が見つかりません")
                return
            
            # OBSタイムライン読み込み
            obs_timeline_file = self.project_dir / "obs_timeline.json"
            if obs_timeline_file.exists():
                with open(obs_timeline_file, 'r', encoding='utf-8') as f:
                    self.obs_timeline_data = json.load(f)
            else:
                self.obs_timeline_data = {"timeline": []}
            
            self.update_ui_from_data()
            messagebox.showinfo("成功", f"プロジェクト読み込み完了: {self.project_dir.name}")
            
        except Exception as e:
            messagebox.showerror("エラー", f"タイムライン読み込みエラー: {e}")
    
    def save_timeline(self):
        """タイムライン保存"""
        if not self.project_dir:
            self.save_as_timeline()
            return
        
        try:
            self.update_data_from_ui()
            
            # ずんだもんタイムライン保存
            timeline_file = self.project_dir / "timeline.json"
            with open(timeline_file, 'w', encoding='utf-8') as f:
                json.dump(self.timeline_data, f, indent=2, ensure_ascii=False)
            
            # OBSタイムライン保存
            obs_timeline_file = self.project_dir / "obs_timeline.json"
            with open(obs_timeline_file, 'w', encoding='utf-8') as f:
                json.dump(self.obs_timeline_data, f, indent=2, ensure_ascii=False)
            
            messagebox.showinfo("成功", "タイムライン保存完了")
            
        except Exception as e:
            messagebox.showerror("エラー", f"タイムライン保存エラー: {e}")
    
    def save_as_timeline(self):
        """名前を付けてタイムライン保存"""
        project_dir = filedialog.askdirectory(title="保存先フォルダを選択")
        if not project_dir:
            return
        
        self.project_dir = Path(project_dir)
        
        # 必要なサブディレクトリ作成
        for subdir in ["backgrounds", "videos", "audio", "texts"]:
            (self.project_dir / subdir).mkdir(exist_ok=True)
        
        self.save_timeline()
    
    def add_action(self):
        """アクション追加"""
        notebook = self.window.nametowidget(self.window.winfo_children()[0].winfo_children()[1].winfo_children()[1])
        current_tab = notebook.index(notebook.select())
        
        if current_tab == 0:  # ずんだもんタブ
            self.add_zundamon_action()
        elif current_tab == 1:  # OBSタブ
            self.add_obs_action()
    
    def add_zundamon_action(self):
        """ずんだもんアクション追加"""
        dialog = ZundamonActionDialog(self.window, self.presets)
        if dialog.result:
            action = dialog.result
            
            # ツリーに追加
            item_id = self.zundamon_tree.insert("", "end", values=(
                action["time"],
                action["character"],
                action["position"],
                action["expression"],
                action["pose"],
                action["outfit"],
                action["text"],
                "Yes" if action["blink"] else "No"
            ))
            
            # データ追加
            if not self.timeline_data:
                self.timeline_data = {"timeline": []}
            self.timeline_data["timeline"].append(action)
            
            # 時間順ソート
            self.sort_timeline_by_time()
    
    def delete_action(self):
        """アクション削除"""
        notebook = self.window.nametowidget(self.window.winfo_children()[0].winfo_children()[1].winfo_children()[1])
        current_tab = notebook.index(notebook.select())
        
        if current_tab == 0:  # ずんだもんタブ
            selection = self.zundamon_tree.selection()
            if selection:
                for item in selection:
                    index = self.zundamon_tree.index(item)
                    self.zundamon_tree.delete(item)
                    if self.timeline_data and index < len(self.timeline_data["timeline"]):
                        del self.timeline_data["timeline"][index]
        
        elif current_tab == 1:  # OBSタブ
            selection = self.obs_tree.selection()
            if selection:
                for item in selection:
                    index = self.obs_tree.index(item)
                    self.obs_tree.delete(item)
                    if self.obs_timeline_data and index < len(self.obs_timeline_data["timeline"]):
                        del self.obs_timeline_data["timeline"][index]
    
    def move_action_up(self):
        """アクション上移動"""
        notebook = self.window.nametowidget(self.window.winfo_children()[0].winfo_children()[1].winfo_children()[1])
        current_tab = notebook.index(notebook.select())
        
        if current_tab == 0:
            self.move_zundamon_action_up()
        elif current_tab == 1:
            self.move_obs_action_up()
    
    def move_action_down(self):
        """アクション下移動"""
        notebook = self.window.nametowidget(self.window.winfo_children()[0].winfo_children()[1].winfo_children()[1])
        current_tab = notebook.index(notebook.select())
        
        if current_tab == 0:
            self.move_zundamon_action_down()
        elif current_tab == 1:
            self.move_obs_action_down()
    
    def move_zundamon_action_up(self):
        """ずんだもんアクション上移動"""
        selection = self.zundamon_tree.selection()
        if not selection:
            return
        
        item = selection[0]
        index = self.zundamon_tree.index(item)
        if index > 0:
            self.zundamon_tree.move(item, "", index - 1)
            if self.timeline_data and len(self.timeline_data["timeline"]) > index:
                actions = self.timeline_data["timeline"]
                actions[index], actions[index - 1] = actions[index - 1], actions[index]
    
    def move_zundamon_action_down(self):
        """ずんだもんアクション下移動"""
        selection = self.zundamon_tree.selection()
        if not selection:
            return
        
        item = selection[0]
        index = self.zundamon_tree.index(item)
        if index < len(self.zundamon_tree.get_children()) - 1:
            self.zundamon_tree.move(item, "", index + 1)
            if self.timeline_data and len(self.timeline_data["timeline"]) > index + 1:
                actions = self.timeline_data["timeline"]
                actions[index], actions[index + 1] = actions[index + 1], actions[index]
    
    def move_obs_action_up(self):
        """OBSアクション上移動"""
        selection = self.obs_tree.selection()
        if not selection:
            return
        
        item = selection[0]
        index = self.obs_tree.index(item)
        if index > 0:
            self.obs_tree.move(item, "", index - 1)
            if self.obs_timeline_data and len(self.obs_timeline_data["timeline"]) > index:
                actions = self.obs_timeline_data["timeline"]
                actions[index], actions[index - 1] = actions[index - 1], actions[index]
    
    def move_obs_action_down(self):
        """OBSアクション下移動"""
        selection = self.obs_tree.selection()
        if not selection:
            return
        
        item = selection[0]
        index = self.obs_tree.index(item)
        if index < len(self.obs_tree.get_children()) - 1:
            self.obs_tree.move(item, "", index + 1)
            if self.obs_timeline_data and len(self.obs_timeline_data["timeline"]) > index + 1:
                actions = self.obs_timeline_data["timeline"]
                actions[index], actions[index + 1] = actions[index + 1], actions[index]
    
    def edit_zundamon_action(self, event):
        """ずんだもんアクション編集"""
        selection = self.zundamon_tree.selection()
        if not selection:
            return
        
        item = selection[0]
        index = self.zundamon_tree.index(item)
        
        if self.timeline_data and index < len(self.timeline_data["timeline"]):
            action = self.timeline_data["timeline"][index]
            dialog = ZundamonActionDialog(self.window, self.presets, action)
            
            if dialog.result:
                new_action = dialog.result
                self.timeline_data["timeline"][index] = new_action
                
                # ツリー更新
                self.zundamon_tree.item(item, values=(
                    new_action["time"],
                    new_action["character"],
                    new_action["position"],
                    new_action["expression"],
                    new_action["pose"],
                    new_action["outfit"],
                    new_action["text"],
                    "Yes" if new_action["blink"] else "No"
                ))
    
    def edit_obs_action(self, event):
        """OBSアクション編集"""
        selection = self.obs_tree.selection()
        if not selection:
            return
        
        item = selection[0]
        index = self.obs_tree.index(item)
        
        if self.obs_timeline_data and index < len(self.obs_timeline_data["timeline"]):
            action = self.obs_timeline_data["timeline"][index]
            dialog = OBSActionDialog(self.window, action)
            
            if dialog.result:
                new_action = dialog.result
                self.obs_timeline_data["timeline"][index] = new_action
                
                # ツリー更新
                self.obs_tree.item(item, values=(
                    new_action["time"],
                    new_action["action"],
                    new_action.get("target", ""),
                    new_action.get("value", ""),
                    new_action.get("duration", "")
                ))
    
    def sort_timeline_by_time(self):
        """タイムラインを時間順ソート"""
        if self.timeline_data and "timeline" in self.timeline_data:
            self.timeline_data["timeline"].sort(key=lambda x: x.get("time", 0))
            self.update_zundamon_tree()
    
    def sort_obs_timeline_by_time(self):
        """OBSタイムラインを時間順ソート"""
        if self.obs_timeline_data and "timeline" in self.obs_timeline_data:
            self.obs_timeline_data["timeline"].sort(key=lambda x: x.get("time", 0))
            self.update_obs_tree()
    
    def update_ui_from_data(self):
        """データからUI更新"""
        if self.timeline_data:
            # プロジェクト情報更新
            for key in ["title", "listener_name", "nickname"]:
                if key in self.timeline_data:
                    self.project_vars[key].set(self.timeline_data[key])
            
            # その他テキスト更新
            if "other_text" in self.timeline_data:
                other_text_widget = self.project_vars["other_text"]
                other_text_widget.delete(1.0, tk.END)
                other_text_widget.insert(1.0, self.timeline_data["other_text"])
            
            # ずんだもんタイムライン更新
            self.update_zundamon_tree()
        
        if self.obs_timeline_data:
            # OBSタイムライン更新
            self.update_obs_tree()
    
    def update_data_from_ui(self):
        """UIからデータ更新"""
        if not self.timeline_data:
            self.timeline_data = {}
        
        # プロジェクト情報更新
        for key in ["title", "listener_name", "nickname"]:
            if key in self.project_vars:
                self.timeline_data[key] = self.project_vars[key].get()
        
        # その他テキスト更新
        other_text_widget = self.project_vars["other_text"]
        self.timeline_data["other_text"] = other_text_widget.get(1.0, tk.END).strip()
    
    def update_zundamon_tree(self):
        """ずんだもんツリー更新"""
        # 既存アイテム削除
        for item in self.zundamon_tree.get_children():
            self.zundamon_tree.delete(item)
        
        # 新しいアイテム追加
        if self.timeline_data and "timeline" in self.timeline_data:
            for action in self.timeline_data["timeline"]:
                self.zundamon_tree.insert("", "end", values=(
                    action.get("time", 0),
                    action.get("character", "zundamon"),
                    action.get("position", "center"),
                    action.get("expression", "normal"),
                    action.get("pose", "basic"),
                    action.get("outfit", "usual"),
                    action.get("text", ""),
                    "Yes" if action.get("blink", True) else "No"
                ))
    
    def update_obs_tree(self):
        """OBSツリー更新"""
        # 既存アイテム削除
        for item in self.obs_tree.get_children():
            self.obs_tree.delete(item)
        
        # 新しいアイテム追加
        if self.obs_timeline_data and "timeline" in self.obs_timeline_data:
            for action in self.obs_timeline_data["timeline"]:
                self.obs_tree.insert("", "end", values=(
                    action.get("time", 0),
                    action.get("action", ""),
                    action.get("target", ""),
                    action.get("value", ""),
                    action.get("duration", "")
                ))
    
    def preview_timeline(self):
        """タイムラインプレビュー"""
        self.update_data_from_ui()
        
        preview_text = "=== タイムラインプレビュー ===\n\n"
        preview_text += f"タイトル: {self.timeline_data.get('title', '')}\n"
        preview_text += f"リスナー名: {self.timeline_data.get('listener_name', '')}\n"
        preview_text += f"ニックネーム: {self.timeline_data.get('nickname', '')}\n"
        preview_text += f"その他テキスト: {self.timeline_data.get('other_text', '')}\n\n"
        
        preview_text += "=== ずんだもんタイムライン ===\n"
        if self.timeline_data and "timeline" in self.timeline_data:
            for i, action in enumerate(self.timeline_data["timeline"]):
                preview_text += f"{i+1:2d}. [{action.get('time', 0):6.1f}s] "
                preview_text += f"{action.get('character', 'zundamon')} - "
                preview_text += f"{action.get('expression', 'normal')}/{action.get('pose', 'basic')} - "
                preview_text += f'"{action.get('text', '')}"\n'
        
        preview_text += "\n=== OBSタイムライン ===\n"
        if self.obs_timeline_data and "timeline" in self.obs_timeline_data:
            for i, action in enumerate(self.obs_timeline_data["timeline"]):
                preview_text += f"{i+1:2d}. [{action.get('time', 0):6.1f}s] "
                preview_text += f"{action.get('action', '')} - "
                preview_text += f"{action.get('target', '')} = {action.get('value', '')}\n"
        
        self.preview_text.delete(1.0, tk.END)
        self.preview_text.insert(1.0, preview_text)
    
    def confirm_unsaved_changes(self):
        """未保存変更確認"""
        # 簡易実装：常にTrueを返す
        return True

# ダイアログクラス
class ZundamonActionDialog:
    def __init__(self, parent, presets, action=None):
        self.parent = parent
        self.presets = presets
        self.result = None
        
        # ダイアログウィンドウ作成
        self.dialog = tk.Toplevel(parent)
        self.dialog.title("ずんだもんアクション編集")
        self.dialog.geometry("500x400")
        self.dialog.transient(parent)
        self.dialog.grab_set()
        
        self.setup_ui(action)
    
    def setup_ui(self, action):
        """UI設定"""
        main_frame = ttk.Frame(self.dialog, padding="20")
        main_frame.pack(fill=tk.BOTH, expand=True)
        
        self.vars = {}
        
        # フォームフィールド
        fields = [
            ("time", "時間(秒)", "float", 0.0),
            ("character", "キャラクター", "str", "zundamon"),
            ("position", "位置", "combo", ["left", "center", "right"], "center"),
            ("expression", "表情", "combo", list(self.presets.get("expressions", {}).keys()), "normal"),
            ("pose", "ポーズ", "combo", list(self.presets.get("poses", {}).keys()), "basic"),
            ("outfit", "衣装", "combo", list(self.presets.get("outfits", {}).keys()), "usual"),
            ("blink", "まばたき", "bool", True)
        ]
        
        for i, field_info in enumerate(fields):
            if len(field_info) == 4:
                key, label, type_, default = field_info
                values = None
            else:
                key, label, type_, values, default = field_info
            
            ttk.Label(main_frame, text=f"{label}:").grid(row=i, column=0, sticky=tk.W, pady=5)
            
            if type_ == "combo":
                var = tk.StringVar(value=action.get(key, default) if action else default)
                combo = ttk.Combobox(main_frame, textvariable=var, values=values, state="readonly")
                combo.grid(row=i, column=1, sticky=(tk.W, tk.E), padx=(10, 0), pady=5)
                self.vars[key] = var
            elif type_ == "bool":
                var = tk.BooleanVar(value=action.get(key, default) if action else default)
                ttk.Checkbutton(main_frame, variable=var).grid(row=i, column=1, sticky=tk.W, padx=(10, 0), pady=5)
                self.vars[key] = var
            else:
                var = tk.StringVar(value=str(action.get(key, default)) if action else str(default))
                ttk.Entry(main_frame, textvariable=var).grid(row=i, column=1, sticky=(tk.W, tk.E), padx=(10, 0), pady=5)
                self.vars[key] = var
        
        # テキストフィールド
        ttk.Label(main_frame, text="テキスト:").grid(row=len(fields), column=0, sticky=(tk.W, tk.N), pady=5)
        self.text_widget = tk.Text(main_frame, height=5, width=40)
        self.text_widget.grid(row=len(fields), column=1, sticky=(tk.W, tk.E, tk.N, tk.S), padx=(10, 0), pady=5)
        
        if action and "text" in action:
            self.text_widget.insert(1.0, action["text"])
        
        # ボタン
        button_frame = ttk.Frame(main_frame)
        button_frame.grid(row=len(fields)+1, column=0, columnspan=2, pady=(20, 0))
        
        ttk.Button(button_frame, text="OK", command=self.ok_clicked).pack(side=tk.RIGHT, padx=(5, 0))
        ttk.Button(button_frame, text="キャンセル", command=self.cancel_clicked).pack(side=tk.RIGHT)
        
        main_frame.columnconfigure(1, weight=1)
        main_frame.rowconfigure(len(fields), weight=1)
    
    def ok_clicked(self):
        """OK押下"""
        try:
            result = {}
            
            for key, var in self.vars.items():
                if key == "time":
                    result[key] = float(var.get())
                elif isinstance(var, tk.BooleanVar):
                    result[key] = var.get()
                else:
                    result[key] = var.get()
            
            result["text"] = self.text_widget.get(1.0, tk.END).strip()
            
            self.result = result
            self.dialog.destroy()
            
        except ValueError as e:
            messagebox.showerror("エラー", f"入力値エラー: {e}")
    
    def cancel_clicked(self):
        """キャンセル押下"""
        self.dialog.destroy()

class OBSActionDialog:
    def __init__(self, parent, action=None):
        self.parent = parent
        self.result = None
        
        # ダイアログウィンドウ作成
        self.dialog = tk.Toplevel(parent)
        self.dialog.title("OBSアクション編集")
        self.dialog.geometry("400x300")
        self.dialog.transient(parent)
        self.dialog.grab_set()
        
        self.setup_ui(action)
    
    def setup_ui(self, action):
        """UI設定"""
        main_frame = ttk.Frame(self.dialog, padding="20")
        main_frame.pack(fill=tk.BOTH, expand=True)
        
        self.vars = {}
        
        # フォームフィールド
        fields = [
            ("time", "時間(秒)", "float", 0.0),
            ("action", "アクション", "combo", ["switch_scene", "update_text", "set_source_visibility"], "switch_scene"),
            ("target", "対象", "str", ""),
            ("value", "値", "str", ""),
            ("duration", "持続時間(秒)", "float", 0.0)
        ]
        
        for i, (key, label, type_, default_or_values) in enumerate(fields):
            ttk.Label(main_frame, text=f"{label}:").grid(row=i, column=0, sticky=tk.W, pady=5)
            
            if type_ == "combo":
                var = tk.StringVar(value=action.get(key, default_or_values[0]) if action else default_or_values[0])
                combo = ttk.Combobox(main_frame, textvariable=var, values=default_or_values, state="readonly")
                combo.grid(row=i, column=1, sticky=(tk.W, tk.E), padx=(10, 0), pady=5)
                self.vars[key] = var
            else:
                default = action.get(key, default_or_values) if action else default_or_values
                var = tk.StringVar(value=str(default))
                ttk.Entry(main_frame, textvariable=var).grid(row=i, column=1, sticky=(tk.W, tk.E), padx=(10, 0), pady=5)
                self.vars[key] = var
        
        # ボタン
        button_frame = ttk.Frame(main_frame)
        button_frame.grid(row=len(fields), column=0, columnspan=2, pady=(20, 0))
        
        ttk.Button(button_frame, text="OK", command=self.ok_clicked).pack(side=tk.RIGHT, padx=(5, 0))
        ttk.Button(button_frame, text="キャンセル", command=self.cancel_clicked).pack(side=tk.RIGHT)
        
        main_frame.columnconfigure(1, weight=1)
    
    def ok_clicked(self):
        """OK押下"""
        try:
            result = {}
            
            for key, var in self.vars.items():
                if key in ["time", "duration"]:
                    value = var.get().strip()
                    result[key] = float(value) if value else 0.0
                else:
                    result[key] = var.get()
            
            self.result = result
            self.dialog.destroy()
            
        except ValueError as e:
            messagebox.showerror("エラー", f"入力値エラー: {e}")
    
    def cancel_clicked(self):
        """キャンセル押下"""
        self.dialog.destroy()