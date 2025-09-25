import tkinter as tk
from tkinter import ttk, messagebox
import json
from pathlib import Path

class ConfigEditor:
    def __init__(self, parent, config):
        self.parent = parent
        self.config = config.copy()  # 元の設定のコピーを作成
        
        # 子ウィンドウ作成
        self.window = tk.Toplevel(parent)
        self.window.title("設定編集")
        self.window.geometry("700x600")
        self.window.transient(parent)
        self.window.grab_set()
        
        self.setup_ui()
    
    def setup_ui(self):
        """UI初期化"""
        # メインフレーム
        main_frame = ttk.Frame(self.window, padding="10")
        main_frame.pack(fill=tk.BOTH, expand=True)
        
        # ノートブック（タブ）
        notebook = ttk.Notebook(main_frame)
        notebook.pack(fill=tk.BOTH, expand=True, pady=(0, 10))
        
        # 各タブ作成
        self.create_directories_tab(notebook)
        self.create_servers_tab(notebook)
        self.create_characters_tab(notebook)
        self.create_timeline_tab(notebook)
        self.create_plugins_tab(notebook)
        
        # ボタンフレーム
        button_frame = ttk.Frame(main_frame)
        button_frame.pack(fill=tk.X)
        
        ttk.Button(button_frame, text="OK", command=self.save_and_close).pack(side=tk.RIGHT, padx=(5, 0))
        ttk.Button(button_frame, text="キャンセル", command=self.cancel).pack(side=tk.RIGHT)
        ttk.Button(button_frame, text="適用", command=self.apply).pack(side=tk.RIGHT, padx=(0, 5))
        ttk.Button(button_frame, text="デフォルトに戻す", command=self.reset_to_default).pack(side=tk.LEFT)
    
    def create_directories_tab(self, notebook):
        """ディレクトリ設定タブ"""
        frame = ttk.Frame(notebook, padding="10")
        notebook.add(frame, text="ディレクトリ")
        
        directories = self.config.get("directories", {})
        self.dir_vars = {}
        
        entries = [
            ("import_dir", "インポートディレクトリ"),
            ("timeline_dir", "タイムラインディレクトリ"),
            ("obs_timeline_dir", "OBSタイムラインディレクトリ"),
            ("assets_dir", "アセットディレクトリ"),
            ("audio_temp_dir", "音声一時ディレクトリ"),
            ("logs_dir", "ログディレクトリ")
        ]
        
        for i, (key, label) in enumerate(entries):
            ttk.Label(frame, text=f"{label}:").grid(row=i, column=0, sticky=tk.W, pady=2)
            
            var = tk.StringVar(value=directories.get(key, ""))
            self.dir_vars[key] = var
            
            entry_frame = ttk.Frame(frame)
            entry_frame.grid(row=i, column=1, sticky=(tk.W, tk.E), padx=(10, 0), pady=2)
            entry_frame.columnconfigure(0, weight=1)
            
            ttk.Entry(entry_frame, textvariable=var).grid(row=0, column=0, sticky=(tk.W, tk.E))
            ttk.Button(entry_frame, text="参照", 
                      command=lambda k=key: self.browse_directory(k)).grid(row=0, column=1, padx=(5, 0))
        
        frame.columnconfigure(1, weight=1)
    
    def create_servers_tab(self, notebook):
        """サーバー設定タブ"""
        frame = ttk.Frame(notebook, padding="10")
        notebook.add(frame, text="サーバー")
        
        servers = self.config.get("servers", {})
        self.server_vars = {}
        
        entries = [
            ("http_port", "HTTPポート", "int"),
            ("websocket_browser_port", "WebSocket(ブラウザ)ポート", "int"),
            ("websocket_control_port", "WebSocket(制御)ポート", "int"),
            ("voicevox_host", "VOICEVOXホスト", "str"),
            ("voicevox_port", "VOICEVOXポート", "int"),
            ("obs_websocket_host", "OBS WebSocketホスト", "str"),
            ("obs_websocket_port", "OBS WebSocketポート", "int"),
            ("obs_password", "OBSパスワード", "str")
        ]
        
        for i, (key, label, type_) in enumerate(entries):
            ttk.Label(frame, text=f"{label}:").grid(row=i, column=0, sticky=tk.W, pady=2)
            
            var = tk.StringVar(value=str(servers.get(key, "")))
            self.server_vars[key] = (var, type_)
            
            if key == "obs_password":
                ttk.Entry(frame, textvariable=var, show="*").grid(row=i, column=1, sticky=(tk.W, tk.E), padx=(10, 0), pady=2)
            else:
                ttk.Entry(frame, textvariable=var).grid(row=i, column=1, sticky=(tk.W, tk.E), padx=(10, 0), pady=2)
        
        frame.columnconfigure(1, weight=1)
    
    def create_characters_tab(self, notebook):
        """キャラクター設定タブ"""
        frame = ttk.Frame(notebook, padding="10")
        notebook.add(frame, text="キャラクター")
        
        characters = self.config.get("characters", {})
        zundamon = characters.get("zundamon", {})
        
        self.char_vars = {}
        
        entries = [
            ("voice_id", "音声ID", "int"),
            ("default_expression", "デフォルト表情", "str"),
            ("default_outfit", "デフォルト衣装", "str"),
            ("default_pose", "デフォルトポーズ", "str"),
            ("default_position", "デフォルト位置", "str")
        ]
        
        ttk.Label(frame, text="ずんだもん設定", font=("Arial", 12, "bold")).grid(row=0, column=0, columnspan=2, pady=(0, 10))
        
        for i, (key, label, type_) in enumerate(entries, 1):
            ttk.Label(frame, text=f"{label}:").grid(row=i, column=0, sticky=tk.W, pady=2)
            
            var = tk.StringVar(value=str(zundamon.get(key, "")))
            self.char_vars[key] = (var, type_)
            
            if key in ["default_expression", "default_outfit", "default_pose", "default_position"]:
                combo = ttk.Combobox(frame, textvariable=var, state="readonly")
                
                if key == "default_expression":
                    combo['values'] = ["normal", "happy", "angry", "sad", "tired"]
                elif key == "default_outfit":
                    combo['values'] = ["usual", "uniform", "casual"]
                elif key == "default_pose":
                    combo['values'] = ["basic", "point", "raise_hand", "think", "mic"]
                elif key == "default_position":
                    combo['values'] = ["left", "center", "right"]
                
                combo.grid(row=i, column=1, sticky=(tk.W, tk.E), padx=(10, 0), pady=2)
            else:
                ttk.Entry(frame, textvariable=var).grid(row=i, column=1, sticky=(tk.W, tk.E), padx=(10, 0), pady=2)
        
        frame.columnconfigure(1, weight=1)
    
    def create_timeline_tab(self, notebook):
        """タイムライン設定タブ"""
        frame = ttk.Frame(notebook, padding="10")
        notebook.add(frame, text="タイムライン")
        
        timeline = self.config.get("timeline", {})
        self.timeline_vars = {}
        
        entries = [
            ("auto_blink_interval", "自動まばたき間隔(秒)", "float"),
            ("speech_end_wait", "発話終了待機時間(秒)", "float"),
            ("comment_response_timeout", "コメント応答タイムアウト(秒)", "float")
        ]
        
        for i, (key, label, type_) in enumerate(entries):
            ttk.Label(frame, text=f"{label}:").grid(row=i, column=0, sticky=tk.W, pady=2)
            
            var = tk.StringVar(value=str(timeline.get(key, "")))
            self.timeline_vars[key] = (var, type_)
            
            ttk.Entry(frame, textvariable=var).grid(row=i, column=1, sticky=(tk.W, tk.E), padx=(10, 0), pady=2)
        
        frame.columnconfigure(1, weight=1)
    
    def create_plugins_tab(self, notebook):
        """プラグイン設定タブ"""
        frame = ttk.Frame(notebook, padding="10")
        notebook.add(frame, text="プラグイン")
        
        plugins = self.config.get("plugins", {})
        
        # プラグインディレクトリ
        ttk.Label(frame, text="プラグインディレクトリ:").grid(row=0, column=0, sticky=tk.W, pady=2)
        self.plugin_dir_var = tk.StringVar(value=plugins.get("plugin_dir", ""))
        ttk.Entry(frame, textvariable=self.plugin_dir_var).grid(row=0, column=1, sticky=(tk.W, tk.E), padx=(10, 0), pady=2)
        
        # 有効プラグイン一覧
        ttk.Label(frame, text="有効なプラグイン:").grid(row=1, column=0, sticky=(tk.W, tk.N), pady=(10, 0))
        
        plugin_frame = ttk.Frame(frame)
        plugin_frame.grid(row=1, column=1, sticky=(tk.W, tk.E, tk.N, tk.S), padx=(10, 0), pady=(10, 0))
        plugin_frame.columnconfigure(0, weight=1)
        plugin_frame.rowconfigure(0, weight=1)
        
        self.plugin_listbox = tk.Listbox(plugin_frame, selectmode=tk.EXTENDED)
        plugin_scrollbar = ttk.Scrollbar(plugin_frame, orient=tk.VERTICAL, command=self.plugin_listbox.yview)
        self.plugin_listbox.configure(yscrollcommand=plugin_scrollbar.set)
        
        self.plugin_listbox.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))
        plugin_scrollbar.grid(row=0, column=1, sticky=(tk.N, tk.S))
        
        # プラグインリスト更新
        enabled_plugins = plugins.get("enabled", [])
        for plugin in enabled_plugins:
            self.plugin_listbox.insert(tk.END, plugin)
        
        # プラグイン操作ボタン
        plugin_btn_frame = ttk.Frame(plugin_frame)
        plugin_btn_frame.grid(row=1, column=0, columnspan=2, pady=(10, 0))
        
        ttk.Button(plugin_btn_frame, text="追加", command=self.add_plugin).pack(side=tk.LEFT, padx=(0, 5))
        ttk.Button(plugin_btn_frame, text="削除", command=self.remove_plugin).pack(side=tk.LEFT, padx=(0, 5))
        ttk.Button(plugin_btn_frame, text="上に移動", command=self.move_plugin_up).pack(side=tk.LEFT, padx=(0, 5))
        ttk.Button(plugin_btn_frame, text="下に移動", command=self.move_plugin_down).pack(side=tk.LEFT)
        
        frame.columnconfigure(1, weight=1)
        frame.rowconfigure(1, weight=1)
        
    def browse_directory(self, key):
        """ディレクトリ選択"""
        from tkinter import filedialog
        directory = filedialog.askdirectory(title=f"{key} ディレクトリを選択")
        if directory:
            self.dir_vars[key].set(directory)
    
    def add_plugin(self):
        """プラグイン追加"""
        from tkinter import simpledialog
        plugin_name = simpledialog.askstring("プラグイン追加", "プラグイン名を入力してください:")
        if plugin_name:
            self.plugin_listbox.insert(tk.END, plugin_name)
    
    def remove_plugin(self):
        """プラグイン削除"""
        selection = self.plugin_listbox.curselection()
        if selection:
            for index in reversed(selection):
                self.plugin_listbox.delete(index)
    
    def move_plugin_up(self):
        """プラグインを上に移動"""
        selection = self.plugin_listbox.curselection()
        if selection and selection[0] > 0:
            index = selection[0]
            item = self.plugin_listbox.get(index)
            self.plugin_listbox.delete(index)
            self.plugin_listbox.insert(index - 1, item)
            self.plugin_listbox.select_set(index - 1)
    
    def move_plugin_down(self):
        """プラグインを下に移動"""
        selection = self.plugin_listbox.curselection()
        if selection and selection[0] < self.plugin_listbox.size() - 1:
            index = selection[0]
            item = self.plugin_listbox.get(index)
            self.plugin_listbox.delete(index)
            self.plugin_listbox.insert(index + 1, item)
            self.plugin_listbox.select_set(index + 1)
    
    def collect_settings(self):
        """設定値を収集"""
        try:
            # ディレクトリ設定
            directories = {}
            for key, var in self.dir_vars.items():
                directories[key] = var.get()
            
            # サーバー設定
            servers = {}
            for key, (var, type_) in self.server_vars.items():
                value = var.get()
                if type_ == "int":
                    servers[key] = int(value) if value else 0
                else:
                    servers[key] = value
            
            # キャラクター設定
            characters = {"zundamon": {}}
            for key, (var, type_) in self.char_vars.items():
                value = var.get()
                if type_ == "int":
                    characters["zundamon"][key] = int(value) if value else 0
                else:
                    characters["zundamon"][key] = value
            
            # タイムライン設定
            timeline = {}
            for key, (var, type_) in self.timeline_vars.items():
                value = var.get()
                if type_ == "float":
                    timeline[key] = float(value) if value else 0.0
                else:
                    timeline[key] = value
            
            # プラグイン設定
            plugins = {
                "plugin_dir": self.plugin_dir_var.get(),
                "enabled": [self.plugin_listbox.get(i) for i in range(self.plugin_listbox.size())]
            }
            
            # ログ設定（既存の値を保持）
            logging = self.config.get("logging", {
                "level": "INFO",
                "file": "./logs/system.log"
            })
            
            # 設定統合
            new_config = {
                "directories": directories,
                "servers": servers,
                "characters": characters,
                "timeline": timeline,
                "plugins": plugins,
                "logging": logging
            }
            
            return new_config
            
        except ValueError as e:
            raise ValueError(f"設定値エラー: {e}")
        except Exception as e:
            raise Exception(f"設定収集エラー: {e}")
    
    def validate_settings(self, config):
        """設定値検証"""
        errors = []
        
        # ポート番号検証
        ports = ["http_port", "websocket_browser_port", "websocket_control_port", 
                "voicevox_port", "obs_websocket_port"]
        for port in ports:
            value = config["servers"].get(port, 0)
            if not (1 <= value <= 65535):
                errors.append(f"{port} は1-65535の範囲で設定してください")
        
        # ディレクトリ存在確認（必要に応じて作成）
        for key, path in config["directories"].items():
            if path:
                try:
                    Path(path).mkdir(parents=True, exist_ok=True)
                except Exception as e:
                    errors.append(f"{key} ディレクトリ作成失敗: {e}")
        
        # 数値範囲確認
        timeline_config = config["timeline"]
        if timeline_config.get("auto_blink_interval", 0) < 0.1:
            errors.append("自動まばたき間隔は0.1秒以上にしてください")
        
        return errors
    
    def apply(self):
        """設定適用"""
        try:
            new_config = self.collect_settings()
            errors = self.validate_settings(new_config)
            
            if errors:
                error_message = "設定エラーが見つかりました:\n\n" + "\n".join(errors)
                messagebox.showerror("設定エラー", error_message)
                return False
            
            self.config.clear()
            self.config.update(new_config)
            
            # 設定ファイルに保存
            from server.config_manager import ConfigManager
            config_manager = ConfigManager()
            config_manager.save_config(self.config)
            
            messagebox.showinfo("成功", "設定を適用しました")
            return True
            
        except Exception as e:
            messagebox.showerror("エラー", f"設定適用エラー: {e}")
            return False
    
    def save_and_close(self):
        """保存して閉じる"""
        if self.apply():
            self.window.destroy()
    
    def cancel(self):
        """キャンセル"""
        if messagebox.askokcancel("確認", "変更を破棄しますか？"):
            self.window.destroy()
    
    def reset_to_default(self):
        """デフォルト設定に戻す"""
        if messagebox.askokcancel("確認", "すべての設定をデフォルト値に戻しますか？"):
            from server.config_manager import ConfigManager
            config_manager = ConfigManager()
            default_config = config_manager.get_default_config()
            
            self.config.clear()
            self.config.update(default_config)
            
            # UIを更新
            self.update_ui_from_config()
    
    def update_ui_from_config(self):
        """設定からUIを更新"""
        # ディレクトリ
        directories = self.config.get("directories", {})
        for key, var in self.dir_vars.items():
            var.set(directories.get(key, ""))
        
        # サーバー
        servers = self.config.get("servers", {})
        for key, (var, type_) in self.server_vars.items():
            var.set(str(servers.get(key, "")))
        
        # キャラクター
        characters = self.config.get("characters", {})
        zundamon = characters.get("zundamon", {})
        for key, (var, type_) in self.char_vars.items():
            var.set(str(zundamon.get(key, "")))
        
        # タイムライン
        timeline = self.config.get("timeline", {})
        for key, (var, type_) in self.timeline_vars.items():
            var.set(str(timeline.get(key, "")))
        
        # プラグイン
        plugins = self.config.get("plugins", {})
        self.plugin_dir_var.set(plugins.get("plugin_dir", ""))
        
        self.plugin_listbox.delete(0, tk.END)
        for plugin in plugins.get("enabled", []):
            self.plugin_listbox.insert(tk.END, plugin)