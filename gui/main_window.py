import tkinter as tk
from tkinter import ttk, messagebox, filedialog
import json
import asyncio
import threading
from pathlib import Path
import sys

# 親ディレクトリをパスに追加
sys.path.append(str(Path(__file__).parent.parent))
from server.config_manager import ConfigManager

class MainWindow:
    def __init__(self):
        self.root = tk.Tk()
        self.root.title("ずんだもんタイムラインシステム - 管理画面")
        self.root.geometry("1000x700")
        
        self.config_manager = ConfigManager()
        self.config = self.config_manager.load_config()
        
        self.setup_ui()
        self.setup_menu()
        
    def setup_ui(self):
        """UI初期化"""
        # メインフレーム
        main_frame = ttk.Frame(self.root, padding="10")
        main_frame.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))
        
        # グリッド設定
        self.root.columnconfigure(0, weight=1)
        self.root.rowconfigure(0, weight=1)
        main_frame.columnconfigure(1, weight=1)
        main_frame.rowconfigure(1, weight=1)
        
        # タイトル
        title_label = ttk.Label(main_frame, text="ずんだもんタイムラインシステム", 
                               font=("Arial", 16, "bold"))
        title_label.grid(row=0, column=0, columnspan=2, pady=(0, 20))
        
        # 左パネル（制御）
        self.setup_control_panel(main_frame)
        
        # 右パネル（ログ・ステータス）
        self.setup_status_panel(main_frame)
        
    def setup_control_panel(self, parent):
        """制御パネル設定"""
        control_frame = ttk.LabelFrame(parent, text="システム制御", padding="10")
        control_frame.grid(row=1, column=0, sticky=(tk.W, tk.E, tk.N, tk.S), padx=(0, 10))
        
        # サーバー制御
        server_frame = ttk.LabelFrame(control_frame, text="サーバー", padding="10")
        server_frame.grid(row=0, column=0, sticky=(tk.W, tk.E), pady=(0, 10))
        server_frame.columnconfigure(0, weight=1)
        
        self.server_status_var = tk.StringVar(value="停止中")
        status_label = ttk.Label(server_frame, textvariable=self.server_status_var)
        status_label.grid(row=0, column=0, pady=(0, 10))
        
        button_frame = ttk.Frame(server_frame)
        button_frame.grid(row=1, column=0)
        
        self.start_btn = ttk.Button(button_frame, text="サーバー起動", 
                                   command=self.start_server)
        self.start_btn.grid(row=0, column=0, padx=(0, 5))
        
        self.stop_btn = ttk.Button(button_frame, text="サーバー停止", 
                                  command=self.stop_server, state="disabled")
        self.stop_btn.grid(row=0, column=1, padx=(5, 0))
        
        # タイムライン制御
        timeline_frame = ttk.LabelFrame(control_frame, text="タイムライン", padding="10")
        timeline_frame.grid(row=1, column=0, sticky=(tk.W, tk.E), pady=(0, 10))
        timeline_frame.columnconfigure(0, weight=1)
        
        project_frame = ttk.Frame(timeline_frame)
        project_frame.grid(row=0, column=0, sticky=(tk.W, tk.E), pady=(0, 10))
        project_frame.columnconfigure(1, weight=1)
        
        ttk.Label(project_frame, text="プロジェクト:").grid(row=0, column=0, sticky=tk.W)
        self.project_var = tk.StringVar()
        project_combo = ttk.Combobox(project_frame, textvariable=self.project_var, state="readonly")
        project_combo.grid(row=0, column=1, sticky=(tk.W, tk.E), padx=(10, 0))
        self.project_combo = project_combo
        self.refresh_projects()
        
        timeline_buttons = ttk.Frame(timeline_frame)
        timeline_buttons.grid(row=1, column=0)
        
        ttk.Button(timeline_buttons, text="タイムライン開始", 
                  command=self.start_timeline).grid(row=0, column=0, padx=(0, 5))
        ttk.Button(timeline_buttons, text="一時停止", 
                  command=self.pause_timeline).grid(row=0, column=1, padx=(5, 0))
        ttk.Button(timeline_buttons, text="停止", 
                  command=self.stop_timeline).grid(row=0, column=2, padx=(5, 0))
        
        # 設定
        settings_frame = ttk.LabelFrame(control_frame, text="設定", padding="10")
        settings_frame.grid(row=2, column=0, sticky=(tk.W, tk.E))
        
        ttk.Button(settings_frame, text="設定編集", 
                  command=self.open_config_editor).grid(row=0, column=0, padx=(0, 5))
        ttk.Button(settings_frame, text="タイムライン編集", 
                  command=self.open_timeline_editor).grid(row=0, column=1, padx=(5, 0))
    
    def setup_status_panel(self, parent):
        """ステータスパネル設定"""
        status_frame = ttk.LabelFrame(parent, text="ステータス・ログ", padding="10")
        status_frame.grid(row=1, column=1, sticky=(tk.W, tk.E, tk.N, tk.S))
        status_frame.columnconfigure(0, weight=1)
        status_frame.rowconfigure(1, weight=1)
        
        # ステータス表示
        status_info_frame = ttk.Frame(status_frame)
        status_info_frame.grid(row=0, column=0, sticky=(tk.W, tk.E), pady=(0, 10))
        status_info_frame.columnconfigure(1, weight=1)
        
        # WebSocket接続状態
        ttk.Label(status_info_frame, text="WebSocket:").grid(row=0, column=0, sticky=tk.W)
        self.websocket_status_var = tk.StringVar(value="切断中")
        ttk.Label(status_info_frame, textvariable=self.websocket_status_var).grid(row=0, column=1, sticky=tk.W, padx=(10, 0))
        
        # VOICEVOX接続状態
        ttk.Label(status_info_frame, text="VOICEVOX:").grid(row=1, column=0, sticky=tk.W)
        self.voicevox_status_var = tk.StringVar(value="未確認")
        ttk.Label(status_info_frame, textvariable=self.voicevox_status_var).grid(row=1, column=1, sticky=tk.W, padx=(10, 0))
        
        # OBS接続状態
        ttk.Label(status_info_frame, text="OBS:").grid(row=2, column=0, sticky=tk.W)
        self.obs_status_var = tk.StringVar(value="未接続")
        ttk.Label(status_info_frame, textvariable=self.obs_status_var).grid(row=2, column=1, sticky=tk.W, padx=(10, 0))
        
        # ログ表示
        log_frame = ttk.Frame(status_frame)
        log_frame.grid(row=1, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))
        log_frame.columnconfigure(0, weight=1)
        log_frame.rowconfigure(0, weight=1)
        
        self.log_text = tk.Text(log_frame, wrap=tk.WORD, height=20)
        scrollbar = ttk.Scrollbar(log_frame, orient=tk.VERTICAL, command=self.log_text.yview)
        self.log_text.configure(yscrollcommand=scrollbar.set)
        
        self.log_text.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))
        scrollbar.grid(row=0, column=1, sticky=(tk.N, tk.S))
        
        # ログクリアボタン
        ttk.Button(status_frame, text="ログクリア", 
                  command=self.clear_log).grid(row=2, column=0, pady=(10, 0))
    
    def setup_menu(self):
        """メニューバー設定"""
        menubar = tk.Menu(self.root)
        self.root.config(menu=menubar)
        
        # ファイルメニュー
        file_menu = tk.Menu(menubar, tearoff=0)
        menubar.add_cascade(label="ファイル", menu=file_menu)
        file_menu.add_command(label="設定を開く", command=self.open_config)
        file_menu.add_command(label="設定を保存", command=self.save_config)
        file_menu.add_separator()
        file_menu.add_command(label="終了", command=self.on_closing)
        
        # プロジェクトメニュー
        project_menu = tk.Menu(menubar, tearoff=0)
        menubar.add_cascade(label="プロジェクト", menu=project_menu)
        project_menu.add_command(label="新規プロジェクト", command=self.new_project)
        project_menu.add_command(label="プロジェクト読み込み", command=self.load_project)
        project_menu.add_separator()
        project_menu.add_command(label="プロジェクト更新", command=self.refresh_projects)
        
        # ツールメニュー
        tools_menu = tk.Menu(menubar, tearoff=0)
        menubar.add_cascade(label="ツール", menu=tools_menu)
        tools_menu.add_command(label="設定編集", command=self.open_config_editor)
        tools_menu.add_command(label="タイムライン編集", command=self.open_timeline_editor)
        tools_menu.add_separator()
        tools_menu.add_command(label="ログフォルダを開く", command=self.open_log_folder)
        
        # ヘルプメニュー
        help_menu = tk.Menu(menubar, tearoff=0)
        menubar.add_cascade(label="ヘルプ", menu=help_menu)
        help_menu.add_command(label="について", command=self.show_about)
    
    def log(self, message):
        """ログ追加"""
        import datetime
        timestamp = datetime.datetime.now().strftime("%H:%M:%S")
        log_message = f"[{timestamp}] {message}\n"
        
        self.log_text.insert(tk.END, log_message)
        self.log_text.see(tk.END)
    
    def clear_log(self):
        """ログクリア"""
        self.log_text.delete(1.0, tk.END)
    
    def refresh_projects(self):
        """プロジェクト一覧更新"""
        try:
            import_dir = Path(self.config["directories"]["import_dir"])
            projects_dir = import_dir / "timeline_projects"
            
            projects = []
            if projects_dir.exists():
                for project_dir in projects_dir.iterdir():
                    if project_dir.is_dir():
                        projects.append(project_dir.name)
            
            self.project_combo['values'] = projects
            if projects:
                self.project_combo.set(projects[0])
            
            self.log(f"プロジェクト一覧更新: {len(projects)}件")
            
        except Exception as e:
            self.log(f"プロジェクト一覧更新エラー: {e}")
    
    # サーバー制御
    def start_server(self):
        """サーバー起動"""
        self.log("サーバー起動中...")
        self.server_status_var.set("起動中...")
        self.start_btn.config(state="disabled")
        
        # TODO: 実際のサーバー起動処理
        # 現在はモックアップ
        self.root.after(2000, self._server_started)
    
    def _server_started(self):
        """サーバー起動完了"""
        self.server_status_var.set("稼働中")
        self.start_btn.config(state="disabled")
        self.stop_btn.config(state="normal")
        self.log("サーバー起動完了")
    
    def stop_server(self):
        """サーバー停止"""
        self.log("サーバー停止中...")
        self.server_status_var.set("停止中...")
        self.stop_btn.config(state="disabled")
        
        # TODO: 実際のサーバー停止処理
        self.root.after(1000, self._server_stopped)
    
    def _server_stopped(self):
        """サーバー停止完了"""
        self.server_status_var.set("停止中")
        self.start_btn.config(state="normal")
        self.stop_btn.config(state="disabled")
        self.log("サーバー停止完了")
    
    # タイムライン制御
    def start_timeline(self):
        """タイムライン開始"""
        project = self.project_var.get()
        if not project:
            messagebox.showwarning("警告", "プロジェクトを選択してください")
            return
        
        self.log(f"タイムライン開始: {project}")
        # TODO: 実際のタイムライン開始処理
    
    def pause_timeline(self):
        """タイムライン一時停止"""
        self.log("タイムライン一時停止")
        # TODO: 実際のタイムライン一時停止処理
    
    def stop_timeline(self):
        """タイムライン停止"""
        self.log("タイムライン停止")
        # TODO: 実際のタイムライン停止処理
    
    # 設定関連
    def open_config(self):
        """設定ファイルを開く"""
        filename = filedialog.askopenfilename(
            title="設定ファイルを選択",
            filetypes=[("JSON files", "*.json"), ("All files", "*.*")]
        )
        if filename:
            try:
                with open(filename, 'r', encoding='utf-8') as f:
                    self.config = json.load(f)
                self.log(f"設定ファイル読み込み: {filename}")
            except Exception as e:
                messagebox.showerror("エラー", f"設定ファイル読み込みエラー: {e}")
    
    def save_config(self):
        """設定ファイルを保存"""
        filename = filedialog.asksaveasfilename(
            title="設定ファイルを保存",
            defaultextension=".json",
            filetypes=[("JSON files", "*.json"), ("All files", "*.*")]
        )
        if filename:
            try:
                with open(filename, 'w', encoding='utf-8') as f:
                    json.dump(self.config, f, indent=2, ensure_ascii=False)
                self.log(f"設定ファイル保存: {filename}")
            except Exception as e:
                messagebox.showerror("エラー", f"設定ファイル保存エラー: {e}")
    
    def open_config_editor(self):
        """設定編集画面を開く"""
        try:
            from .config_editor import ConfigEditor
            config_editor = ConfigEditor(self.root, self.config)
            self.log("設定編集画面を開きました")
        except Exception as e:
            messagebox.showerror("エラー", f"設定編集画面エラー: {e}")
    
    def open_timeline_editor(self):
        """タイムライン編集画面を開く"""
        try:
            from .timeline_editor import TimelineEditor
            timeline_editor = TimelineEditor(self.root)
            self.log("タイムライン編集画面を開きました")
        except Exception as e:
            messagebox.showerror("エラー", f"タイムライン編集画面エラー: {e}")
    
    # プロジェクト関連
    def new_project(self):
        """新規プロジェクト作成"""
        project_name = tk.simpledialog.askstring("新規プロジェクト", "プロジェクト名を入力してください:")
        if project_name:
            try:
                import_dir = Path(self.config["directories"]["import_dir"])
                project_dir = import_dir / "timeline_projects" / project_name
                project_dir.mkdir(parents=True, exist_ok=True)
                
                # 必要なサブディレクトリ作成
                for subdir in ["backgrounds", "videos", "audio", "texts"]:
                    (project_dir / subdir).mkdir(exist_ok=True)
                
                # デフォルトタイムラインファイル作成
                default_timeline = {
                    "title": f"{project_name}のタイトル",
                    "listener_name": "リスナー名",
                    "nickname": "ニックネーム",
                    "other_text": "その他テキスト",
                    "timeline": [
                        {
                            "time": 0,
                            "character": "zundamon",
                            "position": "center",
                            "expression": "normal",
                            "outfit": "usual",
                            "pose": "basic",
                            "text": "こんにちはなのだ！",
                            "blink": True
                        }
                    ]
                }
                
                with open(project_dir / "timeline.json", 'w', encoding='utf-8') as f:
                    json.dump(default_timeline, f, indent=2, ensure_ascii=False)
                
                # デフォルトOBSタイムライン作成
                default_obs_timeline = {
                    "timeline": []
                }
                
                with open(project_dir / "obs_timeline.json", 'w', encoding='utf-8') as f:
                    json.dump(default_obs_timeline, f, indent=2, ensure_ascii=False)
                
                self.refresh_projects()
                self.project_combo.set(project_name)
                self.log(f"新規プロジェクト作成: {project_name}")
                
            except Exception as e:
                messagebox.showerror("エラー", f"プロジェクト作成エラー: {e}")
    
    def load_project(self):
        """プロジェクト読み込み"""
        project_dir = filedialog.askdirectory(title="プロジェクトフォルダを選択")
        if project_dir:
            try:
                # プロジェクトフォルダを timeline_projects にコピー
                # 簡易実装のため省略
                self.log(f"プロジェクト読み込み: {project_dir}")
            except Exception as e:
                messagebox.showerror("エラー", f"プロジェクト読み込みエラー: {e}")
    
    def open_log_folder(self):
        """ログフォルダを開く"""
        import subprocess
        import platform
        
        try:
            log_dir = Path(self.config["directories"]["logs_dir"])
            log_dir.mkdir(parents=True, exist_ok=True)
            
            if platform.system() == "Windows":
                subprocess.run(["explorer", str(log_dir)])
            elif platform.system() == "Darwin":  # macOS
                subprocess.run(["open", str(log_dir)])
            else:  # Linux
                subprocess.run(["xdg-open", str(log_dir)])
                
            self.log(f"ログフォルダを開きました: {log_dir}")
            
        except Exception as e:
            messagebox.showerror("エラー", f"ログフォルダオープンエラー: {e}")
    
    def show_about(self):
        """アバウト画面"""
        about_text = """ずんだもんタイムラインシステム
バージョン: 1.0.0

統合タイムラインシステムと連携する
ずんだもん制御システムです。

機能:
- VOICEVOX音声合成
- OBS制御
- タイムライン自動実行
- コメント割り込み対応
- プラグインシステム

開発: 2024年"""
        
        messagebox.showinfo("について", about_text)
    
    def on_closing(self):
        """終了処理"""
        if messagebox.askokcancel("終了", "アプリケーションを終了しますか？"):
            self.log("アプリケーション終了")
            self.root.destroy()
    
    def run(self):
        """GUI実行"""
        self.root.protocol("WM_DELETE_WINDOW", self.on_closing)
        self.log("ずんだもんタイムラインシステム GUI起動")
        self.root.mainloop()

def start_gui(config=None):
    """GUI起動関数"""
    import tkinter.simpledialog
    app = MainWindow()
    if config:
        app.config = config
    app.run()

if __name__ == "__main__":
    start_gui()